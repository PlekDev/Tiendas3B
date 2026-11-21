"""Módulo de ingesta y extracción de texto por página desde PDFs."""

from tiendas3b.ingestion.pdf_loader import (
    LoadedDocument,
    LoadedPage,
    load_document,
    load_expediente_dir,
    load_pdf,
    load_text_document,
)

__all__ = [
    "LoadedDocument",
    "LoadedPage",
    "load_document",
    "load_expediente_dir",
    "load_pdf",
    "load_text_document",
]
