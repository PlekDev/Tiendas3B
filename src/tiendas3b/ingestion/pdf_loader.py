"""Cargador de documentos con trazabilidad por página (PyMuPDF + OCR de respaldo).

Basado en `ingestion.py` de TrustNode, sin chunking ni ChromaDB: los documentos
de un expediente son cortos y se leen completos, página por página.

El OCR es lento (≈20 s por documento escaneado), así que el texto de cada archivo se
guarda en una caché local identificada por la huella del archivo (`data/cache/ocr/`,
ignorada por git). La API no la usa: ahí no se guarda nada de los documentos subidos.
"""

import hashlib
import json
import logging
import os
import re
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from tiendas3b.config import PROJECT_ROOT, get_settings

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff")
MIN_TEXT_CHARS = 25  # Menos que esto en una página = probablemente escaneo
CACHE_VERSION = 1  # Súbelo si cambia la forma de extraer texto: invalida la caché


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


def ocr_dpi() -> int:
    """300 lee mejor; 200 es casi el doble de rápido. Configurable con OCR_DPI."""
    return int(os.getenv("OCR_DPI") or "300")


def ocr_workers() -> int:
    """Páginas que se pasan por OCR a la vez. Por defecto, un tesseract por núcleo."""
    return max(1, min(8, int(os.getenv("OCR_WORKERS") or os.cpu_count() or 1)))


def _render_page(page: pymupdf.Page) -> object | None:
    try:
        from PIL import Image
    except ImportError:
        logger.warning("OCR no disponible: falta Pillow (extra [ocr]).")
        return None
    pix = page.get_pixmap(dpi=ocr_dpi())
    image: object = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return image  # sin Pillow tipado (CI sin el extra [ocr]) esto sería Any


def load_pdf(file_path: Path) -> LoadedDocument:
    """Extrae el texto página por página; las páginas sin texto pasan por OCR en paralelo.

    PyMuPDF no es seguro entre hilos, así que las páginas se dibujan en este hilo y solo
    tesseract (un proceso aparte) corre en paralelo. Hay a lo más 2 imágenes en espera
    por worker, para no llenar la memoria con documentos largos.
    """
    lang = get_settings().ocr_lang
    workers = ocr_workers()
    if workers > 1:
        os.environ.setdefault("OMP_THREAD_LIMIT", "1")  # los workers ya reparten los núcleos
    texts: dict[int, str] = {}
    ocr: dict[int, Future[str]] = {}
    with (
        ThreadPoolExecutor(max_workers=workers) as pool,
        pymupdf.open(file_path) as doc,  # type: ignore[no-untyped-call]
    ):
        for idx, page in enumerate(doc, start=1):
            texts[idx] = clean_text(page.get_text("text"))
            if len(texts[idx]) >= MIN_TEXT_CHARS:
                continue
            image = _render_page(page)
            if image is None:
                continue
            while (running := [f for f in ocr.values() if not f.done()]) and len(
                running
            ) >= 2 * workers:
                wait(running, return_when=FIRST_COMPLETED)
            ocr[idx] = pool.submit(_ocr_image, image, lang)
    pages: list[LoadedPage] = []
    for idx, text in texts.items():
        source = "pdf"
        if idx in ocr:
            ocr_text = clean_text(ocr[idx].result())
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


def is_document_file(path: Path) -> bool:
    """PDF o imagen real: descarta ocultos y los `__MACOSX/._*` que deja macOS al comprimir."""
    return (
        path.is_file()
        and path.suffix.lower() in SUPPORTED_SUFFIXES
        and not path.name.startswith(".")
        and "__MACOSX" not in path.parts
    )


def ocr_cache_dir() -> Path | None:
    """Carpeta de la caché, o None si OCR_CACHE=0."""
    if (os.getenv("OCR_CACHE") or "1").strip().lower() in ("0", "no", "false"):
        return None
    path = Path(os.getenv("OCR_CACHE_DIR") or "data/cache/ocr")
    return path if path.is_absolute() else PROJECT_ROOT / path


def _cache_key(file_path: Path) -> str:
    digest = hashlib.sha256(file_path.read_bytes())
    digest.update(f"|v{CACHE_VERSION}|{get_settings().ocr_lang}|{ocr_dpi()}".encode())
    return digest.hexdigest()


def _read_cache(path: Path) -> list[LoadedPage] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [LoadedPage(p["page_number"], p["text"], p["source"]) for p in data["pages"]]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _write_cache(path: Path, pages: list[LoadedPage]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    payload = {"pages": [p.__dict__ for p in pages]}
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)  # escritura atómica: una corrida interrumpida no deja basura


def load_document(file_path: Path, use_cache: bool = True) -> LoadedDocument:
    """Lee un PDF o imagen. Con caché, el OCR de cada archivo se hace una sola vez."""
    cache_dir = ocr_cache_dir() if use_cache else None
    cache_file = cache_dir / f"{_cache_key(file_path)}.json" if cache_dir else None
    if cache_file and cache_file.exists():
        pages = _read_cache(cache_file)
        if pages is not None:
            return LoadedDocument(filename=file_path.name, path=file_path, pages=pages)
    if file_path.suffix.lower() == ".pdf":
        doc = load_pdf(file_path)
    else:
        doc = load_image(file_path)
    if cache_file:
        _write_cache(cache_file, doc.pages)
    return doc


def load_expediente_dir(directory: Path, use_cache: bool = True) -> list[LoadedDocument]:
    """Carga todos los PDFs e imágenes de una carpeta (un expediente por carpeta)."""
    paths = sorted(p for p in directory.iterdir() if is_document_file(p))
    return [load_document(path, use_cache) for path in paths]


def load_text_document(filename: str, pages: list[str]) -> LoadedDocument:
    """Documento en memoria a partir de texto. Para fixtures y pruebas sin PDF."""
    return LoadedDocument(
        filename=filename,
        path=Path(filename),
        pages=[LoadedPage(page_number=i, text=t) for i, t in enumerate(pages, start=1)],
    )
