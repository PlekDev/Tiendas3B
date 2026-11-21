"""Visor de documentos: páginas como imagen y dónde está cada dato en ellas.

Para que la interfaz subraye lo que se encontró. La posición de cada palabra sale
de la capa de texto del PDF o, si la página es un escaneo, del OCR (tesseract con
cajas por palabra). Luego cada marca (valor + cita) se busca con coincidencia
difusa, tolerante a acentos y errores de OCR.

No se guarda nada: todo vive en memoria durante la petición.
"""

import base64
import io
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from tiendas3b.config import get_settings
from tiendas3b.ingestion.pdf_loader import MIN_TEXT_CHARS, ocr_dpi

logger = logging.getLogger(__name__)

VIEW_DPI = 144  # 2x de la página: nítido en pantallas retina sin pesar demasiado
MAX_IMAGE_PX = 1800
MAX_MARKS = 300
MIN_SCORE = 72.0  # 0-100; menos que esto se considera "no encontrado"


class MarkIn(BaseModel):
    """Lo que la interfaz quiere ubicar en el documento."""

    id: str
    texto: str | None = None  # el valor (lo que se subraya)
    contexto: str | None = None  # la cita completa, para ubicar el renglón correcto
    pagina: int | None = None


class MarkOut(BaseModel):
    id: str
    page: int
    rects: list[tuple[float, float, float, float]]  # x0, y0, x1, y1 en 0..1
    score: float
    exact: bool  # True si se encontró el valor; False si solo la cita


class PageOut(BaseModel):
    page: int
    width: int
    height: int
    image: str  # data:image/jpeg;base64,...
    source: str  # "pdf" (capa de texto) | "ocr" | "vacia"


class VisorResponse(BaseModel):
    document_name: str
    pages: list[PageOut]
    marks: list[MarkOut]
    missing: list[str] = Field(default_factory=list)  # ids que no se encontraron


@dataclass(frozen=True)
class _Word:
    norm: str
    line: tuple[int, ...]
    box: tuple[float, float, float, float]  # normalizada 0..1


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^0-9a-zñ]+", "", text)


def _tokens(text: str | None) -> list[str]:
    return [t for t in (_norm(w) for w in (text or "").split()) if t]


def _jpeg(image: object) -> tuple[str, int, int]:
    from PIL import Image

    assert isinstance(image, Image.Image)
    img = image.convert("RGB")
    if max(img.size) > MAX_IMAGE_PX:
        img.thumbnail((MAX_IMAGE_PX, MAX_IMAGE_PX))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82, optimize=True)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{data}", img.width, img.height


def _ocr_words(image: object) -> list[_Word]:
    """Palabras con caja a partir de una imagen (OCR)."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning("Visor sin OCR: instala el extra [ocr].")
        return []
    assert isinstance(image, Image.Image)
    try:
        data = pytesseract.image_to_data(
            image, lang=get_settings().ocr_lang, output_type=pytesseract.Output.DICT
        )
    except Exception as exc:  # noqa: BLE001 - binario o idioma ausente
        logger.warning("OCR del visor falló: %s", exc)
        return []
    w, h = image.size
    words: list[_Word] = []
    for i, raw in enumerate(data["text"]):
        norm = _norm(str(raw))
        if not norm or float(data["conf"][i]) < 0:
            continue
        x, y, bw, bh = (int(data[k][i]) for k in ("left", "top", "width", "height"))
        line = (int(data["block_num"][i]), int(data["par_num"][i]), int(data["line_num"][i]))
        words.append(_Word(norm, line, (x / w, y / h, (x + bw) / w, (y + bh) / h)))
    return words


def _pdf_words(page: pymupdf.Page) -> list[_Word]:
    """Palabras de la capa de texto, en coordenadas de la página ya rotada."""
    rect = page.rect
    matrix = page.rotation_matrix
    words: list[_Word] = []
    for x0, y0, x1, y1, text, block, line, _ in page.get_text("words"):  # type: ignore[no-untyped-call]
        norm = _norm(text)
        if not norm:
            continue
        r = pymupdf.Rect(x0, y0, x1, y1) * matrix  # type: ignore[no-untyped-call]
        box = (r.x0 / rect.width, r.y0 / rect.height, r.x1 / rect.width, r.y1 / rect.height)
        words.append(_Word(norm, (int(block), int(line)), box))
    return words


def _digit_score(expected: str, found: str) -> float:
    """Las cifras mandan: 960 m2 no es 850 m2 aunque el texto se parezca.

    Cifras cortas deben ser idénticas; en las largas (folios, claves) se tolera
    un error de OCR.
    """
    if expected == found:
        return 100.0
    if len(expected) >= 8 and len(found) >= 8:
        score = float(fuzz.ratio(expected, found))
        return score if score >= 85 else 0.0
    return 0.0


def _best_window(words: list[_Word], tokens: list[str]) -> tuple[int, int, float]:
    """Ventana contigua de palabras más parecida a `tokens`: (inicio, fin, puntaje 0-100)."""
    n = len(tokens)
    best = (0, 0, 0.0)
    if not n or not words:
        return best
    target = " ".join(tokens)
    digits = re.sub(r"\D", "", target)
    for size in {max(1, n - 1), n, n + 1}:
        for start in range(0, max(1, len(words) - size + 1)):
            window = words[start : start + size]
            text = " ".join(w.norm for w in window)
            score = fuzz.ratio(target, text)
            if digits and score > best[2]:
                score = min(score, _digit_score(digits, re.sub(r"\D", "", text)))
            if score > best[2]:
                best = (start, start + len(window), score)
    return best


def _rects(words: list[_Word]) -> list[tuple[float, float, float, float]]:
    """Une las cajas por renglón: un rectángulo por línea del texto marcado."""
    lines: dict[tuple[int, ...], list[float]] = {}
    for w in words:
        r = lines.setdefault(w.line, [*w.box])
        r[0], r[1] = min(r[0], w.box[0]), min(r[1], w.box[1])
        r[2], r[3] = max(r[2], w.box[2]), max(r[3], w.box[3])
    return [(round(a, 4), round(b, 4), round(c, 4), round(d, 4)) for a, b, c, d in lines.values()]


def locate(pages: dict[int, list[_Word]], mark: MarkIn) -> MarkOut | None:
    """Busca la cita para hallar el renglón y, dentro de ella, el valor exacto."""
    value, context = _tokens(mark.texto), _tokens(mark.contexto)
    order = sorted(pages, key=lambda p: (p != mark.pagina, p))
    best: MarkOut | None = None
    for page in order:
        words = pages[page]

        def hit(span: list[_Word], score: float, exact: bool, page: int = page) -> MarkOut:
            return MarkOut(id=mark.id, page=page, rects=_rects(span), score=score, exact=exact)

        found: MarkOut | None = None
        if context:
            s, e, score = _best_window(words, context)
            if score >= MIN_SCORE:
                span = words[s:e]
                vs, ve, vscore = _best_window(span, value)
                found = hit(span[vs:ve], vscore, True) if vscore >= MIN_SCORE else None
                found = found or hit(span, score, False)
        if found is None and value:
            s, e, score = _best_window(words, value)
            found = hit(words[s:e], score, True) if score >= MIN_SCORE else None
        if found and (best is None or found.score > best.score):
            best = found
        if best and best.score >= 95 and page == mark.pagina:
            break  # en la página de la cita y casi idéntico: no hace falta seguir
    return best


def _pages_of_pdf(path: Path) -> tuple[list[PageOut], dict[int, list[_Word]]]:
    from PIL import Image

    out: list[PageOut] = []
    words: dict[int, list[_Word]] = {}
    with pymupdf.open(path) as doc:  # type: ignore[no-untyped-call]
        for idx, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=VIEW_DPI)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            data, w, h = _jpeg(image)
            source = "pdf"
            page_words = _pdf_words(page)
            if len(page.get_text("text").strip()) < MIN_TEXT_CHARS:
                ocr_pix = page.get_pixmap(dpi=ocr_dpi())
                ocr_img = Image.frombytes("RGB", (ocr_pix.width, ocr_pix.height), ocr_pix.samples)
                ocr = _ocr_words(ocr_img)
                if len(ocr) > len(page_words):
                    page_words, source = ocr, "ocr"
            source = source if page_words else "vacia"
            out.append(PageOut(page=idx, width=w, height=h, image=data, source=source))
            words[idx] = page_words
    return out, words


def _pages_of_image(path: Path) -> tuple[list[PageOut], dict[int, list[_Word]]]:
    from PIL import Image

    with Image.open(path) as image:
        image.load()
        words = _ocr_words(image.convert("RGB"))
        data, w, h = _jpeg(image)
    page = PageOut(page=1, width=w, height=h, image=data, source="ocr" if words else "vacia")
    return [page], {1: words}


def build_view(path: Path, marks: list[MarkIn]) -> VisorResponse:
    """Páginas del documento y la ubicación de cada marca."""
    if path.suffix.lower() == ".pdf":
        pages, words = _pages_of_pdf(path)
    else:
        pages, words = _pages_of_image(path)
    found: list[MarkOut] = []
    missing: list[str] = []
    for mark in marks[:MAX_MARKS]:
        hit = locate(words, mark)
        if hit and hit.rects:
            found.append(hit)
        else:
            missing.append(mark.id)
    return VisorResponse(document_name=path.name, pages=pages, marks=found, missing=missing)
