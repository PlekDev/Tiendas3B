"""Agente clasificador de tipo documental."""

from tiendas3b.ingestion.pdf_loader import LoadedDocument
from tiendas3b.models.schemas import DocumentType

_KEYWORDS: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.ESCRITURAS: ("escritura", "notario", "registro público", "comprador", "vendedor"),
    DocumentType.PREDIAL: ("predial", "clave predial", "cuenta predial", "contribuyente"),
    DocumentType.ALINEAMIENTO: ("alineamiento", "número oficial", "numero oficial"),
    DocumentType.USO_DE_SUELO: ("uso de suelo", "zonificación", "zonificacion", "compatibilidad"),
}


def classify_document(document: LoadedDocument) -> DocumentType:
    """Clasifica el tipo documental combinando heurística base y futura integración LLM."""
    text = f"{document.filename} {document.full_text}".lower()
    for doc_type, keywords in _KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return doc_type
    return DocumentType.DESCONOCIDO
