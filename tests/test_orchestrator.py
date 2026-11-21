"""Pruebas de flujo del orquestador y validación cruzada."""

from pathlib import Path

from tiendas3b.agents.cross_validator import cross_validate
from tiendas3b.agents.orchestrator import analyze_expediente
from tiendas3b.ingestion.pdf_loader import LoadedDocument, LoadedPage
from tiendas3b.models.schemas import (
    DocumentAnalysis,
    DocumentType,
    ExtractedField,
    Recommendation,
)


def test_analyze_expediente_detects_missing_documents() -> None:
    doc = LoadedDocument(
        filename="escritura_01.pdf",
        path=Path("escritura_01.pdf"),
        pages=[LoadedPage(page_number=1, text="Escritura pública ante notario")],
    )
    report = analyze_expediente(expediente_id="EXP-TEST", documents=[doc])

    assert report.expediente_id == "EXP-TEST"
    assert DocumentType.PREDIAL in report.missing_document_types
    assert DocumentType.ALINEAMIENTO in report.missing_document_types
    assert DocumentType.USO_DE_SUELO in report.missing_document_types
    assert report.recommendation == Recommendation.REQUIERE_REVISION


def test_cross_validate_detects_discrepancy() -> None:
    doc_a = DocumentAnalysis(
        document_name="escritura.pdf",
        document_type=DocumentType.ESCRITURAS,
        extracted_fields=[ExtractedField(name="propietario", value="Juan Pérez")],
    )
    doc_b = DocumentAnalysis(
        document_name="predial.pdf",
        document_type=DocumentType.PREDIAL,
        extracted_fields=[ExtractedField(name="propietario", value="María López")],
    )
    issues = cross_validate([doc_a, doc_b])

    assert len(issues) == 1
    assert issues[0].field_name == "propietario"
    assert issues[0].severity == "critical"
    assert set(issues[0].documents_involved) == {"escritura.pdf", "predial.pdf"}
