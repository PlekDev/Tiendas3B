"""Módulo de ingesta y extracción de texto por página desde PDFs."""

from tiendas3b.ingestion.pdf_loader import LoadedDocument, LoadedPage, load_pdf

__all__ = ["LoadedDocument", "LoadedPage", "load_pdf"]
