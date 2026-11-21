"""Cargador de documentos PDF con trazabilidad por página."""

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class LoadedPage:
    """Representa una página extraída de un PDF."""

    page_number: int
    text: str


@dataclass(frozen=True)
class LoadedDocument:
    """Representa un documento PDF cargado con sus páginas."""

    filename: str
    path: Path
    pages: list[LoadedPage]

    @property
    def full_text(self) -> str:
        """Devuelve el texto completo concatenado con marcadores de página."""
        return "\n\n".join(
            f"[Página {page.page_number}]\n{page.text}" for page in self.pages
        )


def load_pdf(file_path: Path) -> LoadedDocument:
    """Extrae el texto página por página de un archivo PDF."""
    reader = PdfReader(str(file_path))
    pages = [
        LoadedPage(page_number=idx, text=(page.extract_text() or "").strip())
        for idx, page in enumerate(reader.pages, start=1)
    ]
    return LoadedDocument(filename=file_path.name, path=file_path, pages=pages)
