"""Agente dictaminador que consolida hallazgos y emite recomendación inicial.

Política provisional (ajustar con las bases oficiales):
- No cumple: falla al menos una regla o cruce de severidad "critical".
- Requiere revisión: falta un documento, falla algo "warning", hay documentos sin
  clasificar o la clasificación es dudosa.
- Cumple: todo lo anterior pasa.
Fallas "info" no cambian el veredicto, pero se reportan como notas.
"""

from statistics import mean

from tiendas3b.models.schemas import (
    CrossValidationIssue,
    DocumentAnalysis,
    DocumentType,
    ExpedienteReport,
    Recommendation,
)
from tiendas3b.rules.criteria import DOCUMENT_LABELS

MIN_CLASSIFICATION_CONFIDENCE = 0.6
MAX_REASONS_PER_GROUP = 6


def _evidence_quality(analyses: list[DocumentAnalysis]) -> float:
    """Promedio de confianza de clasificación y de datos extraídos (0–1)."""
    field_conf = [f.confidence for a in analyses for f in a.extracted_fields]
    class_conf = [a.classification_confidence for a in analyses]
    parts = [mean(field_conf) if field_conf else 0.0, mean(class_conf) if class_conf else 0.0]
    return mean(parts)


def synthesize_report(
    expediente_id: str,
    documents_received: list[str],
    missing_document_types: list[DocumentType],
    document_analyses: list[DocumentAnalysis],
    cross_validation_issues: list[CrossValidationIssue],
) -> ExpedienteReport:
    """Genera el dictamen inicial sustentado en las validaciones previas."""
    critical: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    if missing_document_types:
        names = ", ".join(DOCUMENT_LABELS[t] for t in missing_document_types)
        warnings.append(f"Faltan tipos documentales mínimos: {names}.")

    for issue in cross_validation_issues:
        bucket = critical if issue.severity == "critical" else warnings
        bucket.append(issue.description)

    for doc in document_analyses:
        if doc.document_type == DocumentType.DESCONOCIDO:
            warnings.append(f"{doc.document_name}: no se pudo identificar el tipo de documento.")
            continue
        if doc.classification_confidence and (
            doc.classification_confidence < MIN_CLASSIFICATION_CONFIDENCE
        ):
            warnings.append(
                f"{doc.document_name}: clasificación dudosa como "
                f"{DOCUMENT_LABELS[doc.document_type]} ({doc.classification_confidence:.0%})."
            )
        for rule in doc.rule_evaluations:
            if rule.passed:
                continue
            text = f"{doc.document_name} · {rule.rule_id}: {rule.details}"
            {"critical": critical, "warning": warnings, "info": notes}[rule.severity].append(text)

    quality = _evidence_quality(document_analyses)
    if critical:
        recommendation = Recommendation.NO_CUMPLE
        confidence = 0.6 + 0.35 * quality
    elif warnings:
        recommendation = Recommendation.REQUIERE_REVISION
        confidence = 0.5 + 0.35 * quality
    else:
        recommendation = Recommendation.CUMPLE
        confidence = min(0.95, 0.4 + 0.55 * quality)

    reasons = critical[:MAX_REASONS_PER_GROUP] + warnings[:MAX_REASONS_PER_GROUP]
    hidden = max(0, len(critical) - MAX_REASONS_PER_GROUP) + max(
        0, len(warnings) - MAX_REASONS_PER_GROUP
    )
    if hidden:
        reasons.append(f"Y {hidden} hallazgo(s) más en el detalle por documento.")
    if not reasons:
        reasons.append("Expediente completo y consistente en las validaciones realizadas.")
    reasons += [f"Nota: {n}" for n in notes[:MAX_REASONS_PER_GROUP]]

    return ExpedienteReport(
        expediente_id=expediente_id,
        documents_received=documents_received,
        missing_document_types=missing_document_types,
        document_analyses=document_analyses,
        cross_validation_issues=cross_validation_issues,
        confidence=round(confidence, 2),
        recommendation=recommendation,
        explanation=" ".join(reasons),
        reasons=reasons,
    )
