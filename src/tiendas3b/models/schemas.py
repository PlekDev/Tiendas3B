"""Esquemas Pydantic para trazabilidad, extracción y dictamen de expedientes."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["info", "warning", "critical"]


class DocumentType(StrEnum):
    """Tipos documentales mínimos esperados en un expediente."""

    ESCRITURAS = "escrituras"
    PREDIAL = "predial"
    ALINEAMIENTO = "alineamiento_y_numero_oficial"
    USO_DE_SUELO = "uso_de_suelo"
    DESCONOCIDO = "desconocido"


class Recommendation(StrEnum):
    """Recomendación inicial emitida para el equipo legal."""

    CUMPLE = "Cumple"
    REQUIERE_REVISION = "Requiere revisión"
    NO_CUMPLE = "No cumple"


class Evidence(BaseModel):
    """Referencia exacta al documento y fragmento que sustenta un hallazgo."""

    document_name: str = Field(..., description="Nombre del archivo PDF origen.")
    page: int | None = Field(default=None, description="Número de página (1-indexado).")
    snippet: str = Field(..., description="Fragmento literal o cita del documento.")


class ExtractedField(BaseModel):
    """Dato relevante extraído de un documento con su evidencia asociada."""

    name: str
    value: str | None = None
    evidence: Evidence | None = None
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="0 = sin sustento; baja si la cita no aparece literal en el documento.",
    )
    method: str = Field(default="", description="llm | heuristica | manual")


class RuleEvaluation(BaseModel):
    """Resultado de evaluar una regla o criterio normativo."""

    rule_id: str
    description: str
    passed: bool
    details: str
    evidence: list[Evidence] = Field(default_factory=list)
    severity: Severity = Field(
        default="warning",
        description="Peso si falla: critical → No cumple, warning → Requiere revisión.",
    )


class DocumentAnalysis(BaseModel):
    """Resultado del análisis individual de un documento del expediente."""

    document_name: str
    document_type: DocumentType
    extracted_fields: list[ExtractedField] = Field(default_factory=list)
    rule_evaluations: list[RuleEvaluation] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    classification_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    classification_method: str = Field(default="", description="llm | heuristica")


class CrossValidationIssue(BaseModel):
    """Inconsistencia detectada al cruzar información entre documentos."""

    field_name: str
    description: str
    severity: str = Field(default="warning", description="info | warning | critical")
    documents_involved: list[str] = Field(default_factory=list)
    values_found: dict[str, str] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)


class AgentStep(BaseModel):
    """Registro de un paso del grafo: qué agente actuó, cuánto tardó y qué concluyó."""

    agent: str
    ms: int = Field(ge=0)
    detail: str = ""


class ExpedienteReport(BaseModel):
    """Dictamen completo del expediente para presentación al equipo legal."""

    expediente_id: str
    documents_received: list[str] = Field(default_factory=list)
    missing_document_types: list[DocumentType] = Field(default_factory=list)
    document_analyses: list[DocumentAnalysis] = Field(default_factory=list)
    cross_validation_issues: list[CrossValidationIssue] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    recommendation: Recommendation
    explanation: str
    reasons: list[str] = Field(default_factory=list)
    trace: list[AgentStep] = Field(default_factory=list)
    processing_ms: int = Field(default=0, ge=0)
    llm_mode: str = Field(default="", description="Modelo usado o 'heuristico' si no hubo LLM.")
