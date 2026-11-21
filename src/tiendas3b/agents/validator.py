"""Agente validador normativo por tipo documental."""

from tiendas3b.models.schemas import DocumentAnalysis, RuleEvaluation


def validate_document(analysis: DocumentAnalysis) -> list[RuleEvaluation]:
    """Evalúa los criterios normativos aplicables al documento."""
    evaluations: list[RuleEvaluation] = []
    if analysis.missing_fields:
        evaluations.append(
            RuleEvaluation(
                rule_id="COMPLETITUD_CAMPOS",
                description="Todos los campos requeridos para el tipo documental deben existir.",
                passed=False,
                details=f"Campos faltantes: {', '.join(analysis.missing_fields)}",
            )
        )
    else:
        evaluations.append(
            RuleEvaluation(
                rule_id="COMPLETITUD_CAMPOS",
                description="Todos los campos requeridos para el tipo documental deben existir.",
                passed=True,
                details="Todos los campos requeridos fueron localizados.",
            )
        )
    return evaluations
