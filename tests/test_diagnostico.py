"""Diagnóstico: mide OCR y clasificador sin exponer nombres ni contenido en el resumen."""

import shutil
from pathlib import Path

from tiendas3b.demo import write_demo_pdfs
from tiendas3b.ingestion.diagnostico import (
    diagnose,
    expected_type,
    find_documents,
    format_details,
    format_summary,
)
from tiendas3b.models.schemas import DocumentType


def _raw_by_type(tmp_path: Path) -> Path:
    """Simula data/raw/ con una carpeta por tipo; la escritura queda en la carpeta equivocada."""
    demo = next(f for f in write_demo_pdfs(tmp_path / "demo") if f.name == "DEMO-CUMPLE")
    raw = tmp_path / "raw"
    placement = {
        "escritura.pdf": "Uso_de_suelo",
        "predial.pdf": "Predial",
        "alineamiento.pdf": "Alineamiento_y_Numero_Oficial",
        "uso_de_suelo.pdf": "Uso_de_suelo",
    }
    for name, folder in placement.items():
        (raw / folder).mkdir(parents=True, exist_ok=True)
        shutil.copy(demo / name, raw / folder / name)
    return raw


def test_expected_type_from_folder_name() -> None:
    assert expected_type(Path("raw/Predial/a.pdf")) == DocumentType.PREDIAL
    assert (
        expected_type(Path("raw/Alineamiento_y_Numero_Oficial/a.pdf")) == DocumentType.ALINEAMIENTO
    )
    assert expected_type(Path("raw/Uso_de_suelo/a.pdf")) == DocumentType.USO_DE_SUELO
    assert expected_type(Path("raw/otros/a.pdf")) is None


def test_summary_measures_accuracy_without_file_names(tmp_path: Path) -> None:
    raw = _raw_by_type(tmp_path)
    rows = [diagnose(p) for p in find_documents(raw)]
    summary = format_summary(rows)
    assert "Documentos: 4" in summary
    assert "Acierto contra la carpeta: 3/4" in summary
    assert ".pdf" not in summary
    assert "escritura.pdf" in format_details(rows, raw)


def test_text_pdfs_do_not_need_ocr(tmp_path: Path) -> None:
    rows = [diagnose(p) for p in find_documents(_raw_by_type(tmp_path))]
    assert all(r.ocr_pages == 0 and r.empty_pages == 0 and r.chars > 0 for r in rows)


def test_empty_folder() -> None:
    assert "No encontré" in format_summary([])
