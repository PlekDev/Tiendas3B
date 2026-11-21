"""Agente dictaminador que consolida hallazgos y emite recomendación inicial."""

from tiendas3b.models.schemas import (
    CrossValidationIssue,
    DocumentAnalysis,
    DocumentType,
    ExpedienteReport,
    Recommendation,
)


def synthesize_report(
    expediente_id: str,
    documents_received: list[str],
    missing_document_types: list[DocumentType],
    document_analyses: list[DocumentAnalysis],
    cross_validation_issues: list[CrossValidationIssue],
) -> ExpedienteReport:
    """Genera el dictamen inicial sustentado en las validaciones previas."""
    has_critical_cross = any(i.severity == "critical" for i in cross_validation_issues)
    failed_rules = sum(
        1 for doc in document_analyses for rule in doc.rule_evaluations if not rule.passed
    )

    if missing_document_types or has_critical_cross:
        recommendation = Recommendation.NO_CUMPLE if has_critical_cross else Recommendation.REQUIERE_REVISION
        confidence = 0.75 if has_critical_cross else 0.65
    elif failed_rules > 0:
        recommendation = Recommendation.REQUIERE_REVISION
        confidence = 0.7
    else:
        recommendation = Recommendation.CUMPLE
        confidence = 0.9

    reasons: list[str] = []
    if missing_document_types:
        missing_str = ", ".join(doc_type.value for doc_type in missing_document_types)
        reasons.append(f"Faltan tipos documentales mínimos: {missing_str}.")
    if cross_validation_issues:
        reasons.append(
            f"Se detectaron {len(cross_validation_issues)} inconsistencia(s) cruzada(s) entre documentos."
        )
    if failed_rules:
        reasons.append(f"Se encontraron {failed_rules} criterio(s) normativo(s) no cumplido(s).")
    if not reasons:
        reasons.append("Expediente completo y consistente en las validaciones realizadas.")

    return ExpedienteReport(
        expediente_id=expediente_id,
        documents_received=documents_received,
        missing_document_types=missing_document_types,
        document_analyses=document_analyses,
        cross_validation_issues=cross_validation_issues,
        confidence=confidence,
        recommendation=recommendation,
        explanation=" ".join(reasons),
    )
