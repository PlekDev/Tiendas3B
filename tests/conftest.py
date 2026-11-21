"""Fixtures compartidas para pruebas unitarias (datos sintéticos)."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from tiendas3b.config import get_settings
from tiendas3b.ingestion.pdf_loader import LoadedDocument, LoadedPage


@pytest.fixture(autouse=True)
def _ocr_cache_en_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Las pruebas no escriben en data/cache del repo."""
    monkeypatch.setenv("OCR_CACHE_DIR", str(tmp_path / "ocr-cache"))


@pytest.fixture(autouse=True)
def _sin_llm(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Las pruebas no dependen del .env local ni de la red: sin LLM salvo que la prueba lo pase."""
    monkeypatch.setenv("LLM_PROVIDER", "none")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
