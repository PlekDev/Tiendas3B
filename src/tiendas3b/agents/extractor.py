"""Agente extractor de campos relevantes con trazabilidad."""

from tiendas3b.ingestion.pdf_loader import LoadedDocument
from tiendas3b.models.schemas import DocumentType, ExtractedField
from tiendas3b.rules.criteria import REQUIRED_FIELDS_BY_TYPE


def extract_fields(
    document: LoadedDocument,
    document_type: DocumentType,
) -> tuple[list[ExtractedField], list[str]]:
    """Extrae campos clave del documento y reporta los faltantes.

    Nota: Esta implementación base prepara la estructura de salida; la extracción
    semántica con LangChain (structured output) se conecta aquí.
    """
    _ = document
    required = REQUIRED_FIELDS_BY_TYPE.get(document_type, ())
    extracted: list[ExtractedField] = []
    missing = list(required)
    return extracted, missing
