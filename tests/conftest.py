"""Fixtures compartidas para pruebas unitarias (datos sintéticos)."""

from pathlib import Path

import pytest

from tiendas3b.ingestion.pdf_loader import LoadedDocument, LoadedPage


@pytest.fixture(autouse=True)
def _ocr_cache_en_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Las pruebas no escriben en data/cache del repo."""
    monkeypatch.setenv("OCR_CACHE_DIR", str(tmp_path / "ocr-cache"))


@pytest.fixture
def expediente_completo_docs() -> list[LoadedDocument]:
    """Genera un expediente sintético con los 4 tipos documentales mínimos."""
    return [
        LoadedDocument(
            filename="escritura_01.pdf",
            path=Path("escritura_01.pdf"),
            pages=[
                LoadedPage(
                    page_number=1,
                    text="Escritura pública ante notario. Propietario: Comercializadora Norte S.A.",
                )
            ],
        ),
        LoadedDocument(
            filename="predial_01.pdf",
            path=Path("predial_01.pdf"),
            pages=[
                LoadedPage(
                    page_number=1,
                    text=(
                        "Boleta predial. Cuenta predial 12345. "
                        "Contribuyente: Comercializadora Norte S.A."
                    ),
                )
            ],
        ),
        LoadedDocument(
            filename="alineamiento_01.pdf",
            path=Path("alineamiento_01.pdf"),
            pages=[
                LoadedPage(
                    page_number=1,
                    text="Constancia de alineamiento y número oficial 120. Autoridad municipal.",
                )
            ],
        ),
        LoadedDocument(
            filename="uso_suelo_01.pdf",
            path=Path("uso_suelo_01.pdf"),
            pages=[
                LoadedPage(
                    page_number=1,
                    text="Certificado de uso de suelo comercial permitido.",
                )
            ],
        ),
    ]
