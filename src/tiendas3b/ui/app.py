"""Punto de entrada CLI/UI base para ejecutar análisis de un expediente."""

from pathlib import Path

from tiendas3b.agents.orchestrator import analyze_expediente
from tiendas3b.ingestion.pdf_loader import load_pdf


def run_from_directory(expediente_dir: Path) -> str:
    """Carga los PDFs de un directorio y devuelve el dictamen en JSON."""
    pdf_paths = sorted(expediente_dir.glob("*.pdf"))
    loaded_docs = [load_pdf(path) for path in pdf_paths]
    report = analyze_expediente(expediente_id=expediente_dir.name, documents=loaded_docs)
    return report.model_dump_json(indent=2)
