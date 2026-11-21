"""Grafo completo sobre los expedientes ficticios, con y sin LLM."""

import json

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from tiendas3b.agents.orchestrator import analyze_expediente, graph_mermaid
from tiendas3b.demo import DEMO_CASES, demo_documents, write_demo_pdfs
from tiendas3b.ingestion.pdf_loader import load_expediente_dir
from tiendas3b.models.schemas import Recommendation


@pytest.mark.parametrize("case", sorted(DEMO_CASES))
def test_demo_cases_get_expected_verdict(case: str) -> None:
    spec = DEMO_CASES[case]
    report = analyze_expediente(spec.expediente_id, demo_documents(case), use_llm=False)
    assert report.recommendation == spec.expected
    assert report.reasons
    assert report.llm_mode == "heuristico"


def test_trace_records_every_agent() -> None:
    report = analyze_expediente("X", demo_documents("cumple"), use_llm=False)
    agents = [step.agent for step in report.trace]
    assert agents[0] == "clasificador"
    assert agents[-1] == "dictaminador"
    for name in ("extractor_predial", "validador_normativo", "validacion_cruzada"):
        assert name in agents


def test_supervisor_retries_only_when_needed() -> None:
    ok = analyze_expediente("X", demo_documents("cumple"), use_llm=False)
    incomplete = analyze_expediente("Y", demo_documents("incompleto"), use_llm=False)
    assert "supervisor_reintento" not in [s.agent for s in ok.trace]
    assert "supervisor_reintento" in [s.agent for s in incomplete.trace]


def test_every_finding_cites_evidence() -> None:
    report = analyze_expediente("X", demo_documents("no_cumple"), use_llm=False)
    for issue in report.cross_validation_issues:
        assert issue.evidence and all(ev.snippet and ev.page for ev in issue.evidence)


def test_pipeline_survives_a_broken_llm() -> None:
    llm = FakeListChatModel(responses=["basura"] * 20)
    report = analyze_expediente("X", demo_documents("cumple"), llm=llm)
    assert report.recommendation == Recommendation.CUMPLE


def test_pipeline_uses_llm_extraction_when_valid() -> None:
    from tiendas3b.ingestion.pdf_loader import LoadedDocument, LoadedPage

    docs = demo_documents("cumple")
    # Reemplazar la etiqueta 'Cuenta predial:' por prosa sin etiqueta para que entre el LLM
    prose_docs = [
        LoadedDocument(
            filename=d.filename,
            path=d.path,
            pages=[
                LoadedPage(
                    page_number=p.page_number,
                    text=p.text.replace(
                        "Cuenta predial: 114-002-007-000",
                        "Inscrito bajo el padrón municipal número 114-002-007-000 vigente",
                    ),
                    source=p.source,
                )
                for p in d.pages
            ],
        )
        if d.filename == "predial.pdf"
        else d
        for d in docs
    ]
    answer = json.dumps(
        {
            "campos": {
                "cuenta_predial": {
                    "valor": "114-002-007-000",
                    "pagina": 1,
                    "cita": "Inscrito bajo el padrón municipal número 114-002-007-000 vigente",
                }
            }
        }
    )
    llm = FakeListChatModel(responses=[answer] * 10)
    report = analyze_expediente("X", prose_docs, llm=llm)
    predial = next(a for a in report.document_analyses if a.document_name == "predial.pdf")
    cuenta = next(f for f in predial.extracted_fields if f.name == "cuenta_predial")
    assert cuenta.method == "llm"


def test_pdfs_round_trip(tmp_path: object) -> None:
    from pathlib import Path

    folder = next(f for f in write_demo_pdfs(Path(str(tmp_path))) if f.name == "DEMO-REVISION")
    report = analyze_expediente(folder.name, load_expediente_dir(folder), use_llm=False)
    assert report.recommendation == Recommendation.REQUIERE_REVISION


def test_graph_diagram_lists_agents() -> None:
    diagram = graph_mermaid()
    for node in ("clasificador", "extractores", "reintento", "validacion_cruzada", "dictaminador"):
        assert node in diagram


def test_retry_recovers_multiline_field_with_llm_active() -> None:
    """Cuando el LLM está activo y falta un campo crítico, reintento usa heurística amplia."""
    from pathlib import Path

    from tiendas3b.ingestion.pdf_loader import LoadedDocument, LoadedPage

    # 'propietario' viene en el renglón debajo de la etiqueta (requiere heuristica_amplia)
    multiline_predial = LoadedDocument(
        filename="predial_multiline.pdf",
        path=Path("predial_multiline.pdf"),
        pages=[
            LoadedPage(
                page_number=1,
                text=(
                    "BOLETA PREDIAL\n"
                    "Contribuyente\n"
                    "Inmobiliaria Reforma S.A. de C.V.\n"
                    "Ubicación del predio: Av. Reforma 100\n"
                    "Cuenta predial: 114-002-007-000\n"
                    "Superficie de terreno: 850 m2\n"
                ),
            )
        ],
    )
    # El LLM devuelve JSON vacío, obligando al supervisor a activar reintento
    llm = FakeListChatModel(responses=['{"campos": {}}'] * 5)
    report = analyze_expediente("EXP-RETRY-LLM", [multiline_predial], llm=llm)
    assert "supervisor_reintento" in [s.agent for s in report.trace]
    predial_analysis = report.document_analyses[0]
    extracted_names = {f.name for f in predial_analysis.extracted_fields}
    assert "propietario" in extracted_names
