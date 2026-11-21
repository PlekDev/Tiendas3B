"""Pruebas unitarias para los esquemas de datos del sistema."""

from tiendas3b.models.schemas import (
    DocumentType,
    Evidence,
    ExpedienteReport,
    Recommendation,
)


def test_expediente_report_serialization() -> None:
    report = ExpedienteReport(
        expediente_id="EXP-001",
        documents_received=["escritura.pdf"],
        missing_document_types=[DocumentType.PREDIAL],
        confidence=0.85,
        recommendation=Recommendation.REQUIERE_REVISION,
        explanation="Falta el comprobante predial.",
    )
    data = report.model_dump()
    assert data["expediente_id"] == "EXP-001"
    assert data["recommendation"] == Recommendation.REQUIERE_REVISION
    assert DocumentType.PREDIAL in data["missing_document_types"]


def test_evidence_model() -> None:
    ev = Evidence(document_name="uso_suelo.pdf", page=2, snippet="Uso permitido: Comercial")
    assert ev.page == 2
    assert "Comercial" in ev.snippet
