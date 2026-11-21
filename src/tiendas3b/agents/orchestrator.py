"""Orquestador del flujo multiagente de análisis de expedientes (LangGraph).

    clasificador → extractores → supervisor ─┬─→ validador → validacion_cruzada → dictaminador
                                             └─→ reintento (una vez) ─┘

El supervisor manda a reintentar cuando un documento salió DESCONOCIDO o le falta
un campo crítico: reclasifica leyendo todo el documento y re-extrae con otra
estrategia. Cada nodo deja su paso (agente, ms, conclusión) en la traza.
"""

import contextvars
import logging
import operator
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, Any, TypedDict, TypeVar

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from tiendas3b.agents.classifier import Classification, classify
from tiendas3b.agents.cross_validator import cross_validate_detailed
from tiendas3b.agents.extractor import Strategy, critical_fields, extract_fields
from tiendas3b.agents.synthesizer import synthesize_report
from tiendas3b.agents.validator import validate_document
from tiendas3b.ingestion.pdf_loader import LoadedDocument
from tiendas3b.llm import describe_mode, get_chat_model, llm_parallel
from tiendas3b.logs import register_sensitive
from tiendas3b.models.schemas import (
    AgentStep,
    CrossValidationIssue,
    DocumentAnalysis,
    DocumentType,
    ExpedienteReport,
)
from tiendas3b.rules.criteria import REQUIRED_DOCUMENT_TYPES
from tiendas3b.rules.engine import Cartucho, load_cartuchos

logger = logging.getLogger(__name__)


class ExpedienteState(TypedDict, total=False):
    expediente_id: str
    documents: list[LoadedDocument]
    classifications: dict[str, Classification]
    analyses: list[DocumentAnalysis]
    retried: bool
    missing_types: list[DocumentType]
    cross_issues: list[CrossValidationIssue]
    report: ExpedienteReport
    trace: Annotated[list[AgentStep], operator.add]


NodeResult = tuple[dict[str, Any], str]


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _timed(
    agent: str, fn: Callable[[ExpedienteState], NodeResult]
) -> Any:  # Any: el tipo de nodo de LangGraph es un Protocol que Callable no satisface
    def node(state: ExpedienteState) -> dict[str, Any]:
        start = time.perf_counter()
        update, detail = fn(state)
        steps = [*update.pop("trace", []), AgentStep(agent=agent, ms=_ms(start), detail=detail)]
        for step in steps:  # solo agente y tiempo: el detalle puede traer datos del expediente
            logger.info(
                "paso %s", step.agent, extra={"event": "agente", "agent": step.agent, "ms": step.ms}
            )
        return {**update, "trace": steps}

    return node


T = TypeVar("T")
R = TypeVar("R")


def _parallel_map(fn: Callable[[T], R], items: Sequence[T], workers: int) -> list[R]:
    """Aplica fn a cada elemento en hilos, en orden y con el contexto de logs del expediente."""
    if workers <= 1 or len(items) <= 1:
        return [fn(item) for item in items]
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
        futures = [pool.submit(contextvars.copy_context().run, fn, item) for item in items]
        return [future.result() for future in futures]


def _needs_retry(state: ExpedienteState) -> bool:
    for analysis in state.get("analyses", []):
        if analysis.document_type == DocumentType.DESCONOCIDO:
            return True
        if critical_fields(analysis.document_type) & set(analysis.missing_fields):
            return True
    return False


def build_graph(
    llm: BaseChatModel | None,
    cartuchos: dict[DocumentType, Cartucho],
) -> CompiledStateGraph[ExpedienteState, Any, ExpedienteState, ExpedienteState]:
    """Arma el grafo. `llm=None` corre todo por la ruta heurística."""

    workers = llm_parallel() if llm is not None else 1

    def clasificador(state: ExpedienteState) -> NodeResult:
        docs = state["documents"]
        found = _parallel_map(lambda doc: classify(doc, llm), docs, workers)
        result = {doc.filename: c for doc, c in zip(docs, found, strict=True)}
        detail = ", ".join(
            f"{name} → {c.document_type.value} ({c.confidence:.0%})" for name, c in result.items()
        )
        return {"classifications": result}, detail or "Sin documentos"

    def _analyze(doc: LoadedDocument, c: Classification, strategy: Strategy) -> DocumentAnalysis:
        fields, missing = extract_fields(doc, c.document_type, llm, strategy)
        register_sensitive(f.value for f in fields)
        return DocumentAnalysis(
            document_name=doc.filename,
            document_type=c.document_type,
            extracted_fields=fields,
            missing_fields=missing,
            classification_confidence=c.confidence,
            classification_method=c.method,
        )

    def extractores(state: ExpedienteState) -> NodeResult:
        def extract_one(doc: LoadedDocument) -> tuple[DocumentAnalysis, AgentStep]:
            start = time.perf_counter()
            c = state["classifications"][doc.filename]
            analysis = _analyze(doc, c, "auto")
            step = AgentStep(
                agent=f"extractor_{c.document_type.value}",
                ms=_ms(start),
                detail=(
                    f"{doc.filename}: {len(analysis.extracted_fields)} campos, "
                    f"faltan {len(analysis.missing_fields)}"
                ),
            )
            return analysis, step

        # Un extractor por documento, en paralelo: el LLM es lo que más tarda.
        results = _parallel_map(extract_one, state["documents"], workers)
        analyses = [analysis for analysis, _ in results]
        steps = [step for _, step in results]
        for analysis in analyses:  # en este hilo, para que la redacción de logs los conozca
            register_sensitive(f.value for f in analysis.extracted_fields)
        total = sum(len(a.extracted_fields) for a in analyses)
        return {"analyses": analyses, "trace": steps}, f"{total} campos con evidencia"

    def reintento(state: ExpedienteState) -> NodeResult:
        docs = {d.filename: d for d in state["documents"]}
        updated: list[DocumentAnalysis] = []
        recovered: list[str] = []
        for analysis in state["analyses"]:
            doc = docs[analysis.document_name]
            c = state["classifications"][doc.filename]
            needs_type = analysis.document_type == DocumentType.DESCONOCIDO
            needs_fields = bool(
                critical_fields(analysis.document_type) & set(analysis.missing_fields)
            )
            if not (needs_type or needs_fields):
                updated.append(analysis)
                continue
            if needs_type:
                c = classify(doc, llm, all_pages=True)
            retry = _analyze(doc, c, "heuristica_amplia" if llm is None else "auto")
            merged = {f.name: f for f in analysis.extracted_fields}
            if retry.document_type == analysis.document_type:
                for f in retry.extracted_fields:
                    if f.name not in merged or merged[f.name].confidence < f.confidence:
                        merged[f.name] = f
                retry.extracted_fields = list(merged.values())
                retry.missing_fields = [m for m in retry.missing_fields if m not in merged]
            gained = len(retry.extracted_fields) - len(analysis.extracted_fields)
            recovered.append(f"{doc.filename}: +{max(gained, 0)} campos")
            updated.append(retry)
        return {"analyses": updated, "retried": True}, "; ".join(recovered)

    def validador(state: ExpedienteState) -> NodeResult:
        analyses = [a.model_copy(deep=True) for a in state["analyses"]]
        failed = 0
        for analysis in analyses:
            analysis.rule_evaluations = validate_document(analysis, cartuchos)
            failed += sum(not r.passed for r in analysis.rule_evaluations)
        found = {a.document_type for a in analyses}
        missing = [t for t in REQUIRED_DOCUMENT_TYPES if t not in found]
        total = sum(len(a.rule_evaluations) for a in analyses)
        detail = f"{total} reglas evaluadas, {failed} no cumplidas"
        if missing:
            detail += f"; faltan {len(missing)} tipos de documento"
        return {"analyses": analyses, "missing_types": missing}, detail

    def validacion_cruzada(state: ExpedienteState) -> NodeResult:
        issues, summary = cross_validate_detailed(state["analyses"])
        return {"cross_issues": issues}, " · ".join(summary)

    def dictaminador(state: ExpedienteState) -> NodeResult:
        report = synthesize_report(
            expediente_id=state["expediente_id"],
            documents_received=[d.filename for d in state["documents"]],
            missing_document_types=state.get("missing_types", []),
            document_analyses=state["analyses"],
            cross_validation_issues=state.get("cross_issues", []),
        )
        return {"report": report}, f"{report.recommendation.value} ({report.confidence:.0%})"

    def supervisor(state: ExpedienteState) -> str:
        if not state.get("retried") and _needs_retry(state):
            return "reintento"
        return "validador"

    graph = StateGraph(ExpedienteState)
    graph.add_node("clasificador", _timed("clasificador", clasificador))
    graph.add_node("extractores", _timed("extractores", extractores))
    graph.add_node("reintento", _timed("supervisor_reintento", reintento))
    graph.add_node("validador", _timed("validador_normativo", validador))
    graph.add_node("validacion_cruzada", _timed("validacion_cruzada", validacion_cruzada))
    graph.add_node("dictaminador", _timed("dictaminador", dictaminador))
    graph.add_edge(START, "clasificador")
    graph.add_edge("clasificador", "extractores")
    graph.add_conditional_edges("extractores", supervisor, ["reintento", "validador"])
    graph.add_edge("reintento", "validador")
    graph.add_edge("validador", "validacion_cruzada")
    graph.add_edge("validacion_cruzada", "dictaminador")
    graph.add_edge("dictaminador", END)
    return graph.compile()


def graph_mermaid() -> str:
    """Diagrama del grafo en Mermaid, para el README y el pitch."""
    return str(build_graph(None, {}).get_graph().draw_mermaid())


def analyze_expediente(
    expediente_id: str,
    documents: list[LoadedDocument],
    llm: BaseChatModel | None = None,
    cartuchos: dict[DocumentType, Cartucho] | None = None,
    use_llm: bool = True,
) -> ExpedienteReport:
    """Ejecuta el flujo multiagente de principio a fin sobre un expediente.

    Sin `llm`, usa el configurado en .env (o ninguno si LLM_PROVIDER=none).
    `use_llm=False` fuerza la ruta heurística (pruebas, demo sin red).
    """
    start = time.perf_counter()
    if llm is None and use_llm:
        llm = get_chat_model()
    if cartuchos is None:
        cartuchos = load_cartuchos()
    graph = build_graph(llm, cartuchos)
    state: ExpedienteState = {"expediente_id": expediente_id, "documents": documents, "trace": []}
    final = graph.invoke(state)
    report: ExpedienteReport = final["report"]
    return report.model_copy(
        update={
            "trace": final["trace"],
            "processing_ms": _ms(start),
            "llm_mode": describe_mode() if llm is not None else "heuristico",
        }
    )
