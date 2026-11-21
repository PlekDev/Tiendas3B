"""Agente clasificador de tipo documental.

Primero puntúa palabras clave (rápido, sin LLM). Si la evidencia es débil o hay
empate y hay LLM, le pregunta al LLM. Si nada convence, devuelve DESCONOCIDO.
"""

from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from tiendas3b.ingestion.pdf_loader import LoadedDocument
from tiendas3b.llm import invoke_json
from tiendas3b.models.schemas import DocumentType
from tiendas3b.text import normalize

_KEYWORDS: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.ESCRITURAS: (
        "escritura",
        "escritura publica",
        "notario",
        "notaria",
        "notario publico",
        "registro publico",
        "comprador",
        "vendedor",
        "compraventa",
        "protocolo",
        "instrumento notarial",
        "fedatario",
        "ante mi",
        "protocolizo",
        "se protocoliza",
        "escrituracion",
        "ante el notario",
        "libro de protocolo",
    ),
    DocumentType.PREDIAL: (
        "predial",
        "boleta predial",
        "pago predial",
        "clave predial",
        "cuenta predial",
        "impuesto predial",
        "contribuyente",
        "impuesto",
        "tesoreria",
        "tesoreria municipal",
        "recibo",
        "catastro",
        "clave catastral",
        "valor catastral",
        "superficie terreno",
        "h ayuntamiento",
        "municipio",
    ),
    DocumentType.ALINEAMIENTO: (
        "alineamiento",
        "numero oficial",
        "constancia de alineamiento",
        "constancia de numero oficial",
        "alineamiento y numero oficial",
        "desarrollo urbano",
        "obras publicas",
        "restriccion de construccion",
        "frente a la calle",
        "seccion de vialidad",
        "alineamiento oficial",
        "direccion de obras",
    ),
    DocumentType.USO_DE_SUELO: (
        "uso de suelo",
        "uso del suelo",
        "zonificacion",
        "compatibilidad",
        "licencia de uso",
        "constancia de uso",
        "uso autorizado",
        "uso permitido",
        "dictamen de uso",
        "uso del predio",
        "giro comercial",
        "densidad de construccion",
        "constancia de zonificacion",
        "cambio de uso",
    ),
}

HEURISTIC_MIN_SCORE = 2  # coincidencias mínimas para confiar sin LLM
FILENAME_WEIGHT = 3  # el nombre del archivo pesa más que una mención suelta
CLASSIFY_PAGES = 2  # el tipo casi siempre se ve en las primeras páginas


@dataclass(frozen=True)
class Classification:
    document_type: DocumentType
    confidence: float
    method: str  # "heuristica" | "llm"


class _LLMClassification(BaseModel):
    tipo: str
    confianza: float = 0.5


def _scores(document: LoadedDocument, pages: int | None) -> dict[DocumentType, int]:
    name = normalize(document.filename.replace("_", " "))
    body = normalize(" ".join(p.text for p in document.pages[:pages]))
    scores: dict[DocumentType, int] = {}
    for doc_type, keywords in _KEYWORDS.items():
        score = sum(FILENAME_WEIGHT for k in keywords if k in name)
        score += sum(body.count(k) for k in keywords)
        scores[doc_type] = score
    return scores


def _heuristic(document: LoadedDocument, pages: int | None) -> Classification:
    ranked = sorted(_scores(document, pages).items(), key=lambda kv: kv[1], reverse=True)
    (best, top), (_, second) = ranked[0], ranked[1]
    if top == 0:
        return Classification(DocumentType.DESCONOCIDO, 0.0, "heuristica")
    margin = (top - second) / top
    confidence = round(min(0.95, 0.5 + 0.1 * min(top, 4) + 0.2 * margin), 2)
    if top < HEURISTIC_MIN_SCORE or margin < 0.25:
        confidence = min(confidence, 0.55)
    return Classification(best, confidence, "heuristica")


def _llm(document: LoadedDocument, llm: BaseChatModel) -> Classification | None:
    options = ", ".join(t.value for t in DocumentType)
    text = "\n".join(p.text for p in document.pages[:CLASSIFY_PAGES])[:1200]
    system = (
        "Clasificas documentos de expedientes inmobiliarios en México. "
        f'Responde SOLO JSON: {{"tipo": uno de [{options}], "confianza": 0 a 1}}.'
    )
    user = f"Archivo: {document.filename}\n\nTexto:\n{text}"
    result = invoke_json(llm, system, user, _LLMClassification)
    if result is None:
        return None
    try:
        doc_type = DocumentType(result.tipo.strip().lower())
    except ValueError:
        return None
    return Classification(doc_type, max(0.0, min(1.0, result.confianza)), "llm")


def classify(
    document: LoadedDocument,
    llm: BaseChatModel | None = None,
    all_pages: bool = False,
) -> Classification:
    """Tipo documental con confianza. Usa el LLM solo cuando la heurística duda.

    all_pages=True lee todo el documento (lo usa el supervisor al reintentar).
    """
    heuristic = _heuristic(document, None if all_pages else CLASSIFY_PAGES)
    if llm is None or heuristic.confidence >= 0.75:
        return heuristic
    from_llm = _llm(document, llm)
    if from_llm is None:
        return heuristic
    if from_llm.document_type == heuristic.document_type:
        confidence = max(heuristic.confidence, from_llm.confidence)
        return Classification(heuristic.document_type, confidence, "llm")
    return from_llm


def classify_document(document: LoadedDocument) -> DocumentType:
    """Clasifica el tipo documental combinando heurística base y futura integración LLM."""
    return classify(document).document_type
