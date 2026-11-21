"""Normalización de texto y comparación aproximada para extractores y cruces."""

import re
import unicodedata
from datetime import date

from rapidfuzz import fuzz

_ABBREVIATIONS: tuple[tuple[str, str], ...] = (
    (r"\bs\s*\.?\s*a\s*\.?\s*de\s*c\s*\.?\s*v\b\.?", "sa de cv"),
    (r"\bs\s*\.?\s*de\s*r\s*\.?\s*l\b\.?", "s de rl"),
    (r"\bc\s*\.?\s*p\b\.?", "codigo postal"),
    (r"\bav\b\.?", "avenida"),
    (r"\bcol\b\.?", "colonia"),
    (r"\bfracc?\b\.?", "fraccionamiento"),
    (r"\bblvd?\b\.?", "boulevard"),
    (r"\bcalz\b\.?", "calzada"),
    (r"\bc\b\.?", "calle"),
    (r"\b(?:no|num|nro)\s*\.", "numero "),  # "No." sí; "no compatible" no
    (r"\bno\s+(?=\d)", "numero "),
    (r"\b(?:num|nro)\b", "numero"),
    (r"\bs\s*/\s*n\b", "sin numero"),
    (r"\bmz\b\.?", "manzana"),
    (r"\blt\b\.?", "lote"),
    (r"\bmpio\b\.?", "municipio"),
    (r"\bedo\b\.?", "estado"),
)


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize(text: str) -> str:
    """Minúsculas, sin acentos, sin puntuación y con abreviaturas expandidas."""
    text = strip_accents(text.lower())
    text = text.replace("#", " numero ")
    for pattern, replacement in _ABBREVIATIONS:
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"[^a-z0-9ñ ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_id(text: str) -> str:
    """Para claves catastrales, cuentas y números oficiales: solo letras y dígitos."""
    return re.sub(r"[^a-z0-9]", "", strip_accents(text.lower()))


def similarity(a: str, b: str) -> float:
    """0–100. Ignora orden de palabras (útil para 'Pérez Juan' vs 'Juan Pérez')."""
    return float(fuzz.token_sort_ratio(normalize(a), normalize(b)))


def parse_number(text: str) -> float | None:
    """Primer número del texto: '1,250.50 m2' → 1250.5."""
    match = re.search(r"\d[\d,]*(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group().replace(",", ""))
    except ValueError:
        return None


_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def find_dates(text: str) -> list[date]:
    """Fechas en formatos comunes de documentos mexicanos, en orden de aparición."""
    found: list[tuple[int, date]] = []
    plain = strip_accents(text.lower())
    patterns = (
        (r"(\d{1,2})\s+de\s+([a-z]+)\s+(?:de|del)\s+(\d{4})", "dmy_text"),
        (r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", "dmy"),
        (r"(\d{4})-(\d{1,2})-(\d{1,2})", "ymd"),
    )
    for pattern, kind in patterns:
        for m in re.finditer(pattern, plain):
            try:
                if kind == "dmy_text":
                    month = _MONTHS.get(m.group(2))
                    if month is None:
                        continue
                    value = date(int(m.group(3)), month, int(m.group(1)))
                elif kind == "dmy":
                    value = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                else:
                    value = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
            found.append((m.start(), value))
    return [value for _, value in sorted(found)]


def quote_in_text(quote: str, text: str, threshold: float = 90.0) -> bool:
    """¿La cita aparece (casi) literal en el texto? Evita evidencia inventada por el LLM."""
    if not quote.strip():
        return False
    q, t = normalize(quote), normalize(text)
    if q in t:
        return True
    return bool(fuzz.partial_ratio(q, t) >= threshold)
