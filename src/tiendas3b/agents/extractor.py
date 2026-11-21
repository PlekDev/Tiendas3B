"""Agente extractor de campos relevantes con trazabilidad.

Dos rutas que se complementan:
- Heurística: busca encabezados "Etiqueta: valor" renglón por renglón. Corre sin LLM.
- LLM (LangChain): extrae por campo con página y cita literal. La cita se verifica
  contra el texto; si no aparece, el dato queda en duda (confianza baja).

Orden: primero la heurística. El LLM solo se pregunta por lo que la heurística no
resolvió con confianza (siempre completo en Escrituras). Si ambas rutas coinciden
sube la confianza; si discrepan, el dato queda en duda.
"""

import logging
import re
from functools import lru_cache
from typing import Literal

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field, field_validator
from rapidfuzz import fuzz

from tiendas3b.agents.extractor_fields import FIELD_SPECS, FieldSpec
from tiendas3b.ingestion.pdf_loader import LoadedDocument, LoadedPage
from tiendas3b.llm import invoke_json
from tiendas3b.models.schemas import DocumentType, Evidence, ExtractedField
from tiendas3b.rules.criteria import REQUIRED_FIELDS_BY_TYPE
from tiendas3b.text import normalize, normalize_id, parse_number, similarity

logger = logging.getLogger(__name__)

Strategy = Literal["auto", "heuristica", "heuristica_amplia", "llm"]

MAX_PROMPT_CHARS = 2_500  # ~3.5k tokens: holgado con num_ctx=8192 (OCR tokeniza mal)
MAX_SNIPPET_CHARS = 240
MIN_AREA_M2 = 20.0  # un local o terreno comercial no mide menos

CONF_LLM_VERIFIED = 0.9
CONF_LLM_VALUE_ONLY = 0.6
CONF_LLM_UNVERIFIED = 0.3
CONF_LABEL_SAME_LINE = 0.75
CONF_LABEL_NEXT_LINE = 0.65
CONF_DISCREPANCY = 0.55  # heurística y LLM dicen cosas distintas → dato en duda
FAST_HEURISTIC_MIN = CONF_LABEL_NEXT_LINE  # con esta confianza no se le pregunta al LLM

SYSTEM_PROMPT = """Eres un analista legal que revisa expedientes de inmuebles en México.
Extrae SOLO información escrita en el documento. No supongas ni completes datos.
Para cada campo devuelve:
- "valor": el dato tal como aparece (texto), o null si no aparece.
- "pagina": número de página donde aparece (los marcadores [Página N] la indican), o null.
Si no estás seguro, usa null. Responde SOLO con JSON:
{"campos": {"<campo>": {"valor": "...", "pagina": 1, "cita": "..."}}}"""


# --------------------------------------------------------------------------- utilidades


@lru_cache(maxsize=20000)
def _norm(text: str) -> str:
    """normalize() con caché: la heurística lo llama miles de veces sobre las mismas líneas."""
    return normalize(text)


def _quote_in(quote: str, text: str, threshold: float = 90.0) -> bool:
    """¿La cita aparece (casi) literal en el texto? Igual que text.quote_in_text, con caché."""
    if not quote.strip():
        return False
    q, t = _norm(quote), _norm(text)
    return q in t or float(fuzz.partial_ratio(q, t)) >= threshold


_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numbers(text: str) -> list[float]:
    out: list[float] = []
    for raw in _NUM.findall(text):
        try:
            out.append(float(raw.replace(",", "")))
        except ValueError:
            continue
    return out


def _excluded(line: str, exclude: tuple[str, ...]) -> bool:
    if not exclude:
        return False
    norm = _norm(line)
    return any(word in norm for word in exclude)


_ALL_LABELS = {
    label
    for specs in FIELD_SPECS.values()
    for spec in specs.values()
    for label in (*spec.labels, *spec.extra_labels)
}


def _looks_like_label(line: str) -> bool:
    """Para no tomar como valor la siguiente etiqueta ('Propietario' / 'Domicilio: ...')."""
    norm = _norm(line)
    return any(norm == lb or (norm.startswith(lb + " ") and ":" in line) for lb in _ALL_LABELS)


class _LLMField(BaseModel):
    valor: str | None = None
    pagina: int | None = None
    cita: str | None = None

    @field_validator("valor", "cita", mode="before")
    @classmethod
    def _to_text(cls, value: object) -> str | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return str(value)


class _LLMExtraction(BaseModel):
    campos: dict[str, _LLMField] = Field(default_factory=dict)


def _snippet(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= MAX_SNIPPET_CHARS else text[: MAX_SNIPPET_CHARS - 1] + "…"


def _field(
    name: str, value: str, doc: LoadedDocument, page: int, quote: str, conf: float, method: str
) -> ExtractedField:
    return ExtractedField(
        name=name,
        value=value.strip(" :;.-"),
        evidence=Evidence(document_name=doc.filename, page=page, snippet=_snippet(quote)),
        confidence=conf,
        method=method,
    )


# --------------------------------------------------------------------------- heurística


_NEXT_FIELD = re.compile(
    r"\s+(?:r\.?f\.?c|regimen|periodo(?:\s+de\s+pago)?|valor(?:\s+catastral)?|ubicacion|domicilio|clave|cuenta|superficie|uso\s*cfdi|c\.?p\.?|fecha|subsidio|observaciones)\s*[:.-]",
    re.IGNORECASE,
)
_TITLE_WORDS = {
    "y",
    "de",
    "del",
    "o",
    "constancia",
    "licencia",
    "dictamen",
    "oficial",
    "predial",
    "catastral",
}


def _clean_value(raw: str) -> str:
    m = _NEXT_FIELD.search(raw)
    if m:
        raw = raw[: m.start()]
    val = raw.strip(" :;.-|/")
    # Quitar residuos de etiquetas compuestas como "PROPIETARIO / POSEEDOR"
    val = re.sub(r"^(?:poseedor|propietario|contribuyente)\s+", "", val, flags=re.IGNORECASE)
    return val.strip(" :;.-|/")


# funcion que permite diferentes delimitadores
def _value_after_label(line: str, label: str) -> str | None:
    norm = _norm(line)
    label_norm = _norm(label)

    # Coincidencia al inicio de línea
    if norm.startswith(label_norm + " ") or norm == label_norm:
        if norm == label_norm:
            return None
        if ":" in line:
            value = line.split(":", 1)[1]
            cleaned = _clean_value(value)
            return cleaned or None

        # Delimitadores frecuentes sin dos puntos: ".-", " - ", " / ", " | "
        for sep in (" .- ", ".-", " - ", " / ", " | "):
            if sep in line:
                parts = line.split(sep, 1)
                if _norm(parts[0]) == label_norm:
                    cleaned = _clean_value(parts[1])
                    if cleaned:
                        return cleaned

        words = line.split()
        label_words = label_norm.split()
        if len(words) <= len(label_words):
            return None

        remainder_words = words[len(label_words) :]
        # Evita confundir títulos como "ALINEAMIENTO Y NÚMERO OFICIAL" con datos
        if len(label_words) < 2 and remainder_words[0].lower() in _TITLE_WORDS:
            return None

        value = " ".join(remainder_words)
        cleaned = _clean_value(value)
        return cleaned or None

    # Coincidencia de etiqueta en medio de la línea con dos puntos (ej. en prosa legal)
    pattern = rf"(?:^|\s){re.escape(label_norm)}\s*[:.-]\s*(.+)$"
    match = re.search(pattern, norm)
    if match:
        # Extraer desde la línea original para conservar mayúsculas y acentos
        raw_match = re.search(rf"(?:^|\s){re.escape(label)}\s*[:.-]\s*(.+)$", line, re.IGNORECASE)
        val = raw_match.group(1) if raw_match else match.group(1)
        cleaned = _clean_value(val)
        return cleaned or None

    return None


def _is_bare_label(line: str, label: str) -> bool:
    return _norm(line) == label


def _find_label(
    doc: LoadedDocument,
    labels: tuple[str, ...],
    wide: bool,
    exclude: tuple[str, ...] = (),
) -> tuple[str, LoadedPage, str, float] | None:
    for label in labels:
        for page in doc.pages:
            lines = page.text.splitlines()
            for i, line in enumerate(lines):
                if _excluded(line, exclude):
                    continue
                value = _value_after_label(line, label)
                if value:
                    return value, page, line, CONF_LABEL_SAME_LINE
                if wide and _is_bare_label(line, label) and i + 1 < len(lines):
                    nxt = lines[i + 1].strip()
                    if nxt and not _looks_like_label(nxt) and not _excluded(nxt, exclude):
                        return nxt, page, f"{line} {nxt}", CONF_LABEL_NEXT_LINE
    return None


_AREA_SUFFIX = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*(m2|m²|m\?|m'|mts2|mts\.?|metros cuadrados)", re.IGNORECASE
)
_AREA_PREFIX = re.compile(
    r"(?:terreno|superficie|sup\.?)\s*(?:\(m[2²\?]\)|m[2²\?]|propio)?\s*[:.-]?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:m2|m²|m\?|mts2|metros)?",
    re.IGNORECASE,
)
_AREA_WORDS = re.compile(r"\b(superficie|terreno|sup)\b")


def _area_ok(num: str) -> bool:
    try:
        return float(num.replace(",", "")) >= MIN_AREA_M2
    except ValueError:
        return False


def _find_area(
    doc: LoadedDocument, exclude: tuple[str, ...] = ()
) -> tuple[str, LoadedPage, str, float] | None:
    for page in doc.pages:
        for line in page.text.splitlines():
            norm = _norm(line)
            if not _AREA_WORDS.search(norm) or _excluded(line, exclude):
                continue
            # Priorizar terreno sobre construcción
            if "construccion" in norm and "terreno" not in norm:
                continue
            m_suf = _AREA_SUFFIX.search(line)
            if m_suf and _area_ok(m_suf.group(1)):
                return f"{m_suf.group(1)} m2", page, line, CONF_LABEL_NEXT_LINE
            m_pre = _AREA_PREFIX.search(line)
            if m_pre and _area_ok(m_pre.group(1)):
                return f"{m_pre.group(1).replace(',', '')} m2", page, line, CONF_LABEL_NEXT_LINE
    return None


def _extract_heuristic(
    doc: LoadedDocument, specs: dict[str, FieldSpec], wide: bool
) -> dict[str, ExtractedField]:
    found: dict[str, ExtractedField] = {}
    for name, spec in specs.items():
        hit = _find_label(doc, spec.labels, wide, spec.exclude)
        if hit is None and name.startswith("superficie"):
            hit = _find_area(doc, spec.exclude)
        if hit is None:
            continue
        value, page, line, conf = hit
        extra = (
            _find_label(doc, spec.extra_labels, wide, spec.exclude) if spec.extra_labels else None
        )
        if extra and extra[0] not in value:
            value = f"{value}; {spec.extra_labels[0]}: {extra[0]}"
        found[name] = _field(name, value, doc, page.page_number, line, conf, "heuristica")
    return found


# --------------------------------------------------------------------------- LLM


def _render(pages: list[LoadedPage]) -> str:
    """Siempre con marcadores [Página N]: el LLM los necesita para llenar 'pagina'."""
    return "\n\n".join(f"[Página {p.page_number}]\n{p.text}" for p in pages)


def _select_pages(doc: LoadedDocument, specs: dict[str, FieldSpec]) -> str:
    """Si el documento no cabe en el prompt: página 1 + páginas con más encabezados clave."""
    full = _render(doc.pages)
    if len(full) <= MAX_PROMPT_CHARS:
        return full
    weights: dict[str, int] = {}
    for spec in specs.values():
        for label in spec.labels:
            weights[label] = max(weights.get(label, 0), 2 if spec.critical else 1)

    def score(page: LoadedPage) -> int:
        norm = _norm(page.text)
        return sum(w for label, w in weights.items() if label in norm)

    first = doc.pages[0].page_number if doc.pages else None
    ranked = sorted(doc.pages, key=lambda p: (p.page_number != first, -score(p), p.page_number))
    chosen: list[LoadedPage] = []
    budget = MAX_PROMPT_CHARS
    for page in ranked:
        cost = len(page.text) + 20
        if cost > budget:
            continue
        chosen.append(page)
        budget -= cost
    chosen.sort(key=lambda p: p.page_number)
    return _render(chosen)


def _value_supported(name: str, valor: str, cita: str | None) -> bool:
    """¿El valor sale de la cita? Evita que una cita real avale un valor inventado."""
    if not cita:
        return False
    if len(_norm(valor)) >= 3 and _quote_in(valor, cita):
        return True
    if name.startswith("superficie"):
        nv = parse_number(valor)  # 960 m2 vs 960.00 M2
        return nv is not None and any(abs(nv - n) < 0.01 for n in _numbers(cita))
    return False


def _verify(name: str, raw: _LLMField, doc: LoadedDocument) -> ExtractedField | None:
    if raw.valor is None:
        return None
    pages = {p.page_number: p for p in doc.pages}
    verified = (
        CONF_LLM_VERIFIED if _value_supported(name, raw.valor, raw.cita) else CONF_LLM_VALUE_ONLY
    )
    if raw.cita:
        if (
            raw.pagina is not None
            and raw.pagina in pages
            and _quote_in(raw.cita, pages[raw.pagina].text)
        ):
            return _field(name, raw.valor, doc, raw.pagina, raw.cita, verified, "llm")
        for page in doc.pages:  # cita real, página equivocada
            if _quote_in(raw.cita, page.text):
                conf = verified - 0.05
                return _field(name, raw.valor, doc, page.page_number, raw.cita, conf, "llm")
    if len(_norm(raw.valor)) >= 4:  # valores cortos ("1", "SI") coinciden con cualquier línea
        for page in doc.pages:  # sin cita verificable, pero el valor sí está en el texto
            if _quote_in(raw.valor, page.text):
                snippet_line = page.text
                for line in page.text.splitlines():
                    if _quote_in(raw.valor, line):
                        snippet_line = line
                        break
                return _field(
                    name, raw.valor, doc, page.page_number, snippet_line, CONF_LLM_VALUE_ONLY, "llm"
                )
    return ExtractedField(name=name, value=raw.valor, confidence=CONF_LLM_UNVERIFIED, method="llm")


def _extract_llm(
    doc: LoadedDocument,
    doc_type: DocumentType,
    specs: dict[str, FieldSpec],
    llm: BaseChatModel,
) -> dict[str, ExtractedField]:
    fields_desc = "\n".join(f'- "{name}": {spec.description}' for name, spec in specs.items())
    user = (
        f"Tipo de documento: {doc_type.value}\nArchivo: {doc.filename}\n\n"
        f"Campos a extraer:\n{fields_desc}\n\nTEXTO DEL DOCUMENTO:\n{_select_pages(doc, specs)}"
    )
    campos_str = ", ".join(specs.keys())
    result = invoke_json(
        llm,
        SYSTEM_PROMPT,
        user,
        _LLMExtraction,
        call_name=f"extractor:{doc_type.value} | archivo={doc.filename} | campos=[{campos_str}]",
    )
    if result is None:
        return {}
    found: dict[str, ExtractedField] = {}
    for name in specs:
        raw = result.campos.get(name)
        verified = _verify(name, raw, doc) if raw else None
        if verified:
            found[name] = verified
    return found


# --------------------------------------------------------------------------- fusión


def _same(name: str, a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    if na in nb or nb in na or similarity(a, b) >= 90:
        return True
    if name.startswith("superficie"):
        pa, pb = parse_number(a), parse_number(b)
        return pa is not None and pa == pb
    ia, ib = normalize_id(a), normalize_id(b)
    return len(ia) >= 4 and (ia in ib or ib in ia)


def _merge(
    name: str, llm_f: ExtractedField | None, heu_f: ExtractedField | None
) -> ExtractedField | None:
    if llm_f is None or heu_f is None:
        return llm_f or heu_f
    if llm_f.value is None or heu_f.value is None:
        return llm_f if llm_f.value is not None else heu_f
    if _same(name, llm_f.value, heu_f.value):  # dos rutas independientes coinciden
        return llm_f.model_copy(
            update={"confidence": min(0.97, llm_f.confidence + 0.07), "method": "llm"}
        )
    best = max((llm_f, heu_f), key=lambda f: f.confidence)  # discrepancia → dato en duda
    return best.model_copy(update={"confidence": min(best.confidence, CONF_DISCREPANCY)})


# --------------------------------------------------------------------------- API pública


def extract_fields(
    document: LoadedDocument,
    document_type: DocumentType,
    llm: BaseChatModel | None = None,
    strategy: Strategy = "auto",
) -> tuple[list[ExtractedField], list[str]]:
    """Extrae campos clave del documento y reporta los faltantes.

    strategy="auto": heurística primero; el LLM solo cubre lo que la heurística no resolvió
        con confianza (en Escrituras siempre pregunta por todos los campos).
    strategy="llm": solo LLM. strategy="heuristica": sin LLM, valor en la misma línea.
    strategy="heuristica_amplia": sin LLM, acepta también el renglón siguiente a la etiqueta.
    """
    specs = FIELD_SPECS.get(document_type, {})
    wide = strategy in ("auto", "heuristica_amplia")
    heuristic = _extract_heuristic(document, specs, wide) if strategy != "llm" else {}

    llm_found: dict[str, ExtractedField] = {}
    if llm is not None and strategy in ("auto", "llm"):
        fast = strategy == "auto"
        pending = {
            name: spec
            for name, spec in specs.items()
            if not fast or name not in heuristic or heuristic[name].confidence < FAST_HEURISTIC_MIN
        }
        if pending:
            llm_found = _extract_llm(document, document_type, pending, llm)

    found: dict[str, ExtractedField] = {}
    for name in specs:
        merged = _merge(name, llm_found.get(name), heuristic.get(name))
        if merged is not None:
            found[name] = merged
    required = REQUIRED_FIELDS_BY_TYPE.get(document_type, ())
    ordered = [found[name] for name in required if name in found]
    missing = [name for name in required if name not in found]
    return ordered, missing


def critical_fields(document_type: DocumentType) -> set[str]:
    return {name for name, spec in FIELD_SPECS.get(document_type, {}).items() if spec.critical}
