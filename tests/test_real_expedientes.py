"""Pruebas de integración locales con los documentos reales del reto.

Los PDFs reales deben colocarse en `data/expedientes/<id_expediente>/*.pdf`
(o directamente en `data/expedientes/*.pdf`). Esta carpeta está en `.gitignore`
para no subir documentos confidenciales al repositorio ni a CI.
"""

from pathlib import Path

import pytest

from tiendas3b.agents.orchestrator import analyze_expediente
from tiendas3b.ingestion.pdf_loader import load_pdf
from tiendas3b.models.schemas import Recommendation

EXPEDIENTES_DIR = Path(__file__).resolve().parent.parent / "data" / "expedientes"


def _discover_expediente_dirs() -> list[Path]:
    if not EXPEDIENTES_DIR.exists():
        return []
    subdirs = [p for p in sorted(EXPEDIENTES_DIR.iterdir()) if p.is_dir() and list(p.glob("*.pdf"))]
    if subdirs:
        return subdirs
    if list(EXPEDIENTES_DIR.glob("*.pdf")):
        return [EXPEDIENTES_DIR]
    return []


_REAL_EXPEDIENTES = _discover_expediente_dirs()


@pytest.mark.real_data
@pytest.mark.skipif(
    not _REAL_EXPEDIENTES,
    reason="No hay PDFs reales en data/expedientes/ (ejecución omitida en CI).",
)
@pytest.mark.parametrize(
    "expediente_dir",
    _REAL_EXPEDIENTES,
    ids=[p.name for p in _REAL_EXPEDIENTES],
)
def test_real_expediente_pipeline(expediente_dir: Path) -> None:
    """Ejecuta el pipeline completo sobre cada expediente real colocado en local."""
    pdf_paths = sorted(expediente_dir.glob("*.pdf"))
    loaded_docs = [load_pdf(path) for path in pdf_paths]

    report = analyze_expediente(expediente_id=expediente_dir.name, documents=loaded_docs)

    assert report.documents_received == [p.name for p in pdf_paths]
    assert report.recommendation in {
        Recommendation.CUMPLE,
        Recommendation.REQUIERE_REVISION,
        Recommendation.NO_CUMPLE,
    }
    assert report.explanation.strip() != ""
