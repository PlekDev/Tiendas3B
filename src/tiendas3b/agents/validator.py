"""Agente validador normativo por tipo documental.

Aplica el cartucho de reglas del tipo (data/rules/*.json). Si no hay cartucho,
revisa al menos que estén los campos requeridos.
"""

from tiendas3b.models.schemas import DocumentAnalysis, DocumentType, RuleEvaluation
from tiendas3b.rules.criteria import REQUIRED_FIELDS_BY_TYPE
from tiendas3b.rules.engine import Cartucho, evaluate_rules


def _completeness(analysis: DocumentAnalysis) -> RuleEvaluation:
    required = REQUIRED_FIELDS_BY_TYPE.get(analysis.document_type, ())
    missing = [name for name in required if name in analysis.missing_fields]
    return RuleEvaluation(
        rule_id="COMPLETITUD_CAMPOS",
        description="Todos los campos requeridos para el tipo documental deben existir.",
        passed=not missing,
        details=(
            f"Campos faltantes: {', '.join(missing)}"
            if missing
            else "Todos los campos requeridos fueron localizados."
        ),
    )


def validate_document(
    analysis: DocumentAnalysis,
    cartuchos: dict[DocumentType, Cartucho] | None = None,
) -> list[RuleEvaluation]:
    """Evalúa los criterios normativos aplicables al documento."""
    if analysis.document_type == DocumentType.DESCONOCIDO:
        return [
            RuleEvaluation(
                rule_id="TIPO_DOCUMENTO",
                description="El documento corresponde a uno de los tipos esperados.",
                passed=False,
                details="No se pudo identificar el tipo de documento; requiere revisión manual.",
            )
        ]
    cartucho = (cartuchos or {}).get(analysis.document_type)
    if cartucho is None:
        return [_completeness(analysis)]
    return evaluate_rules(analysis, cartucho)
