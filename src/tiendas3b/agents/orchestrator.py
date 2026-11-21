"""Orquestador del flujo multiagente de análisis de expedientes."""

from tiendas3b.agents.classifier import classify_document
from tiendas3b.agents.cross_validator import cross_validate
from tiendas3b.agents.extractor import extract_fields
from tiendas3b.agents.synthesizer import synthesize_report
from tiendas3b.agents.validator import validate_document
from tiendas3b.ingestion.pdf_loader import LoadedDocument
from tiendas3b.models.schemas import DocumentAnalysis, ExpedienteReport
from tiendas3b.rules.criteria import REQUIRED_DOCUMENT_TYPES


def analyze_expediente(
    expediente_id: str,
    documents: list[LoadedDocument],
) -> ExpedienteReport:
    """Ejecuta el flujo multiagente de principio a fin sobre un expediente."""
    analyses: list[DocumentAnalysis] = []
    found_types = set()

    for doc in documents:
        doc_type = classify_document(doc)
        found_types.add(doc_type)
        extracted_fields, missing_fields = extract_fields(doc, doc_type)
        analysis = DocumentAnalysis(
            document_name=doc.filename,
            document_type=doc_type,
            extracted_fields=extracted_fields,
            missing_fields=missing_fields,
        )
        analysis.rule_evaluations = validate_document(analysis)
        analyses.append(analysis)

    missing_types = [req for req in REQUIRED_DOCUMENT_TYPES if req not in found_types]
    cross_issues = cross_validate(analyses)

    return synthesize_report(
        expediente_id=expediente_id,
        documents_received=[doc.filename for doc in documents],
        missing_document_types=missing_types,
        document_analyses=analyses,
        cross_validation_issues=cross_issues,
    )
