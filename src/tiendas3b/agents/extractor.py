"""Agente extractor de campos relevantes con trazabilidad.

Dos rutas que se complementan:
- LLM (LangChain): extrae por campo con página y cita literal. La cita se verifica
  contra el texto; si no aparece, el dato queda en duda (confianza baja).
- Heurística: busca encabezados "Etiqueta: valor" renglón por renglón. Corre sin
  LLM, sirve de respaldo y llena huecos que el LLM deje.
"""

import logging
import re
from typing import Literal

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field, field_validator

from tiendas3b.agents.extractor_fields import FIELD_SPECS, FieldSpec
from tiendas3b.ingestion.pdf_loader import LoadedDocument, LoadedPage
from tiendas3b.llm import invoke_json
from tiendas3b.models.schemas import DocumentType, Evidence, ExtractedField
from tiendas3b.rules.criteria import REQUIRED_FIELDS_BY_TYPE
from tiendas3b.text import normalize, quote_in_text

logger = logging.getLogger(__name__)

Strategy = Literal["auto", "heuristica", "heuristica_amplia", "llm"]

MAX_PROMPT_CHARS = 18_000  # ~6k tokens: cabe en llama3.1:8b con num_ctx=8192
MAX_SNIPPET_CHARS = 240

CONF_LLM_VERIFIED = 0.9
CONF_LLM_VALUE_ONLY = 0.6
CONF_LLM_UNVERIFIED = 0.3
CONF_LABEL_SAME_LINE = 0.75
CONF_LABEL_NEXT_LINE = 0.65

SYSTEM_PROMPT = """Eres un analista legal que revisa expedientes de inmuebles en México.
Extrae SOLO información escrita en el documento. No supongas ni completes datos.
Para cada campo devuelve:
- "valor": el dato tal como aparece (texto), o null si no aparece.
- "pagina": número de página donde aparece (los marcadores [Página N] la indican), o null.
- "cita": fragmento LITERAL copiado del documento que contiene el dato (máx. 200 caracteres).
Si no estás seguro, usa null. Responde SOLO con JSON:
{"campos": {"<campo>": {"valor": "...", "pagina": 1, "cita": "..."}}}"""


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
    norm = normalize(line)
    label_norm = normalize(label)

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
                if normalize(parts[0]) == label_norm:
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
    return normalize(line) == label


def _find_label(
    doc: LoadedDocument, labels: tuple[str, ...], wide: bool
) -> tuple[str, LoadedPage, str, float] | None:
    for label in labels:
        for page in doc.pages:
            lines = page.text.splitlines()
            for i, line in enumerate(lines):
                value = _value_after_label(line, label)
                if value:
                    return value, page, line, CONF_LABEL_SAME_LINE
                if wide and _is_bare_label(line, label) and i + 1 < len(lines):
                    nxt = lines[i + 1].strip()
                    if nxt:
                        return nxt, page, f"{line} {nxt}", CONF_LABEL_NEXT_LINE
    return None


_AREA_SUFFIX = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*(m2|m²|m\?|m'|mts2|mts\.?|metros cuadrados)", re.IGNORECASE
)
_AREA_PREFIX = re.compile(
    r"(?:terreno|superficie|sup\.?)\s*(?:\(m[2²\?]\)|m[2²\?]|propio)?\s*[:.-]?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:m2|m²|m\?|mts2|metros)?",
    re.IGNORECASE,
)


def _find_area(doc: LoadedDocument) -> tuple[str, LoadedPage, str, float] | None:
    for page in doc.pages:
        for line in page.text.splitlines():
            norm = normalize(line)
            if not any(k in norm for k in ("superficie", "terreno", "sup")):
                continue
            # Priorizar terreno sobre construcción
            if "construccion" in norm and "terreno" not in norm:
                continue
            m_suf = _AREA_SUFFIX.search(line)
            if m_suf:
                val = f"{m_suf.group(1)} m2"
                return val, page, line, CONF_LABEL_NEXT_LINE
            m_pre = _AREA_PREFIX.search(line)
            if m_pre:
                num = m_pre.group(1).replace(",", "")
                try:
                    if float(num) > 0:
                        return f"{num} m2", page, line, CONF_LABEL_NEXT_LINE
                except ValueError:
                    pass
    return None


def _extract_heuristic(
    doc: LoadedDocument, specs: dict[str, FieldSpec], wide: bool
) -> dict[str, ExtractedField]:
    found: dict[str, ExtractedField] = {}
    for name, spec in specs.items():
        hit = _find_label(doc, spec.labels, wide)
        if hit is None and name.startswith("superficie"):
            hit = _find_area(doc)
        if hit is None:
            continue
        value, page, line, conf = hit
        extra = _find_label(doc, spec.extra_labels, wide) if spec.extra_labels else None
        if extra and extra[0] not in value:
            value = f"{value}; {spec.extra_labels[0]}: {extra[0]}"
        found[name] = _field(name, value, doc, page.page_number, line, conf, "heuristica")
    return found


# --------------------------------------------------------------------------- LLM


def _select_pages(doc: LoadedDocument, specs: dict[str, FieldSpec]) -> str:
    """Si el documento no cabe en el prompt, prioriza páginas con encabezados conocidos."""
    if len(doc.full_text) <= MAX_PROMPT_CHARS:
        return doc.full_text
    keywords = {label for spec in specs.values() for label in spec.labels}
    ranked = sorted(
        doc.pages,
        key=lambda p: (-sum(k in normalize(p.text) for k in keywords), p.page_number),
    )
    chosen: list[LoadedPage] = []
    budget = MAX_PROMPT_CHARS
    for page in ranked:
        if len(page.text) + 20 > budget:
            continue
        chosen.append(page)
        budget -= len(page.text) + 20
    chosen.sort(key=lambda p: p.page_number)
    return "\n\n".join(f"[Página {p.page_number}]\n{p.text}" for p in chosen)


def _verify(name: str, raw: _LLMField, doc: LoadedDocument) -> ExtractedField | None:
    if raw.valor is None:
        return None
    pages = {p.page_number: p for p in doc.pages}
    if raw.cita:
        if raw.pagina in pages and quote_in_text(raw.cita, pages[raw.pagina].text):
            return _field(name, raw.valor, doc, raw.pagina, raw.cita, CONF_LLM_VERIFIED, "llm")
        for page in doc.pages:  # cita real, página equivocada
            if quote_in_text(raw.cita, page.text):
                conf = CONF_LLM_VERIFIED - 0.05
                return _field(name, raw.valor, doc, page.page_number, raw.cita, conf, "llm")
    for page in doc.pages:  # sin cita verificable, pero el valor sí está en el texto
        if quote_in_text(raw.valor, page.text):
            snippet_line = page.text
            for line in page.text.splitlines():
                if quote_in_text(raw.valor, line):
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
    result = invoke_json(llm, SYSTEM_PROMPT, user, _LLMExtraction)
    if result is None:
        return {}
    found: dict[str, ExtractedField] = {}
    for name in specs:
        raw = result.campos.get(name)
        verified = _verify(name, raw, doc) if raw else None
        if verified:
            found[name] = verified
    return found


# --------------------------------------------------------------------------- API pública


def extract_fields(
    document: LoadedDocument,
    document_type: DocumentType,
    llm: BaseChatModel | None = None,
    strategy: Strategy = "auto",
) -> tuple[list[ExtractedField], list[str]]:
    """Extrae campos clave del documento y reporta los faltantes.

    strategy="auto": LLM si hay, y la heurística llena lo que falte.
    strategy="heuristica_amplia": también acepta el valor en el renglón siguiente a la etiqueta.
    """
    specs = FIELD_SPECS.get(document_type, {})
    found: dict[str, ExtractedField] = {}
    if llm is not None and strategy in ("auto", "llm"):
        found = _extract_llm(document, document_type, specs, llm)
    if strategy != "llm":
        wide = strategy == "heuristica_amplia"
        for name, value in _extract_heuristic(document, specs, wide).items():
            current = found.get(name)
            if current is None or current.confidence < value.confidence:
                found[name] = value
    required = REQUIRED_FIELDS_BY_TYPE.get(document_type, ())
    ordered = [found[name] for name in required if name in found]
    missing = [name for name in required if name not in found]
    return ordered, missing


def critical_fields(document_type: DocumentType) -> set[str]:
    return {name for name, spec in FIELD_SPECS.get(document_type, {}).items() if spec.critical}
