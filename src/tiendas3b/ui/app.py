"""Punto de entrada CLI/UI base para ejecutar análisis de un expediente.

La interfaz visual vive en `frontend/` (React) y consume la API de `tiendas3b.api`.
"""

from pathlib import Path

from tiendas3b.agents.orchestrator import analyze_expediente
from tiendas3b.ingestion.pdf_loader import load_expediente_dir


def run_from_directory(expediente_dir: Path) -> str:
    """Carga los PDFs de un directorio y devuelve el dictamen en JSON."""
    loaded_docs = load_expediente_dir(expediente_dir)
    report = analyze_expediente(expediente_id=expediente_dir.name, documents=loaded_docs)
    return report.model_dump_json(indent=2)
