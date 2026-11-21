"""Agente de validación cruzada entre documentos del mismo expediente."""

from tiendas3b.models.schemas import CrossValidationIssue, DocumentAnalysis

_CROSS_CHECK_FIELDS = ("propietario", "direccion", "superficie", "numero_oficial", "cuenta_predial")


def cross_validate(analyses: list[DocumentAnalysis]) -> list[CrossValidationIssue]:
    """Contrasta valores clave entre documentos para detectar discrepancias."""
    issues: list[CrossValidationIssue] = []

    for field_key in _CROSS_CHECK_FIELDS:
        values_by_doc: dict[str, str] = {}
        for doc in analyses:
            for field in doc.extracted_fields:
                if field_key in field.name and field.value:
                    values_by_doc[doc.document_name] = field.value.strip()

        unique_normalized = {val.lower() for val in values_by_doc.values()}
        if len(unique_normalized) > 1:
            issues.append(
                CrossValidationIssue(
                    field_name=field_key,
                    description=f"Discrepancia detectada en '{field_key}' entre documentos.",
                    severity="critical",
                    documents_involved=list(values_by_doc.keys()),
                    values_found=values_by_doc,
                )
            )

    return issues
