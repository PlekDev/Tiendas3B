"""Cargador de documentos con trazabilidad por página (PyMuPDF + OCR de respaldo).

Basado en `ingestion.py` de TrustNode, sin chunking ni ChromaDB: los documentos
de un expediente son cortos y se leen completos, página por página.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from tiendas3b.config import get_settings

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff")
MIN_TEXT_CHARS = 25  # Menos que esto en una página = probablemente escaneo
OCR_DPI = 300


@dataclass(frozen=True)
class LoadedPage:
    """Representa una página extraída de un PDF."""

    page_number: int
    text: str
    source: str = "pdf"  # "pdf" (capa de texto) | "ocr" | "vacia"


@dataclass(frozen=True)
class LoadedDocument:
    """Representa un documento PDF cargado con sus páginas."""

    filename: str
    path: Path
    pages: list[LoadedPage]

    @property
    def full_text(self) -> str:
        """Devuelve el texto completo concatenado con marcadores de página."""
        return "\n\n".join(f"[Página {page.page_number}]\n{page.text}" for page in self.pages)

    @property
    def ocr_pages(self) -> int:
        return sum(1 for page in self.pages if page.source == "ocr")


def clean_text(raw: str) -> str:
    """Une palabras cortadas con guion y colapsa espacios, conservando los renglones."""
    text = raw.replace("-\n", "")
    lines = (re.sub(r"[ \t ]+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _ocr_image(image: object, lang: str) -> str:
    try:
        import pytesseract
    except ImportError:
        logger.warning("OCR no disponible: instala el extra [ocr] y tesseract-ocr-%s.", lang)
        return ""
    try:
        return str(pytesseract.image_to_string(image, lang=lang))
    except Exception as exc:  # noqa: BLE001 - idioma no instalado, binario ausente, etc.
        logger.warning("OCR falló (%s). ¿Está instalado tesseract-ocr-%s?", exc, lang)
        return ""


def _ocr_page(page: pymupdf.Page, lang: str) -> str:
    try:
        from PIL import Image
    except ImportError:
        logger.warning("OCR no disponible: falta Pillow (extra [ocr]).")
        return ""
    pix = page.get_pixmap(dpi=OCR_DPI)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return _ocr_image(image, lang)


def load_pdf(file_path: Path) -> LoadedDocument:
    """Extrae el texto página por página; si una página no tiene texto, intenta OCR."""
    lang = get_settings().ocr_lang
    pages: list[LoadedPage] = []
    with pymupdf.open(file_path) as doc:  # type: ignore[no-untyped-call]
        for idx, page in enumerate(doc, start=1):
            text = clean_text(page.get_text("text"))
            source = "pdf"
            if len(text) < MIN_TEXT_CHARS:
                ocr_text = clean_text(_ocr_page(page, lang))
                if len(ocr_text) > len(text):
                    text, source = ocr_text, "ocr"
            pages.append(LoadedPage(page_number=idx, text=text, source=source if text else "vacia"))
    return LoadedDocument(filename=file_path.name, path=file_path, pages=pages)


def load_image(file_path: Path) -> LoadedDocument:
    """Fotos o escaneos sueltos: una sola página por OCR."""
    try:
        from PIL import Image
    except ImportError:
        logger.warning("No se puede leer %s: falta Pillow (extra [ocr]).", file_path.name)
        return LoadedDocument(file_path.name, file_path, [LoadedPage(1, "", "vacia")])
    with Image.open(file_path) as image:
        text = clean_text(_ocr_image(image, get_settings().ocr_lang))
    page = LoadedPage(page_number=1, text=text, source="ocr" if text else "vacia")
    return LoadedDocument(filename=file_path.name, path=file_path, pages=[page])


def load_document(file_path: Path) -> LoadedDocument:
    if file_path.suffix.lower() == ".pdf":
        return load_pdf(file_path)
    return load_image(file_path)


def load_expediente_dir(directory: Path) -> list[LoadedDocument]:
    """Carga todos los PDFs e imágenes de una carpeta (un expediente por carpeta)."""
    paths = sorted(
        p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    )
    return [load_document(path) for path in paths]


def load_text_document(filename: str, pages: list[str]) -> LoadedDocument:
    """Documento en memoria a partir de texto. Para fixtures y pruebas sin PDF."""
    return LoadedDocument(
        filename=filename,
        path=Path(filename),
        pages=[LoadedPage(page_number=i, text=t) for i, t in enumerate(pages, start=1)],
    )
