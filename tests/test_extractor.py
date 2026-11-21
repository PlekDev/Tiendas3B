"""Extractor: ruta heurística, ruta LLM con verificación de citas y coherencia con la guía."""

import json

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from tiendas3b.agents.extractor import CONF_LLM_UNVERIFIED, CONF_LLM_VERIFIED, extract_fields
from tiendas3b.agents.extractor_fields import FIELD_SPECS
from tiendas3b.demo import demo_documents
from tiendas3b.ingestion.pdf_loader import load_text_document
from tiendas3b.models.schemas import DocumentType
from tiendas3b.rules.criteria import REQUIRED_FIELDS_BY_TYPE


def _doc(name: str) -> object:
    return next(d for d in demo_documents("cumple") if d.filename == name)


def test_every_required_field_has_a_spec() -> None:
    for doc_type, required in REQUIRED_FIELDS_BY_TYPE.items():
        assert set(required) == set(FIELD_SPECS[doc_type]), doc_type


def test_heuristic_extracts_predial_with_evidence() -> None:
    doc = next(d for d in demo_documents("cumple") if d.filename == "predial.pdf")
    fields, missing = extract_fields(doc, DocumentType.PREDIAL)
    by_name = {f.name: f for f in fields}
    assert missing == []
    assert by_name["cuenta_predial"].value == "114-002-007-000"
    assert by_name["superficie_registrada"].evidence is not None
    assert by_name["superficie_registrada"].evidence.page == 1


def test_heuristic_ignores_titles() -> None:
    doc = load_text_document("a.pdf", ["CONSTANCIA DE ALINEAMIENTO Y NÚMERO OFICIAL\nALINEAMIENTO"])
    fields, _ = extract_fields(doc, DocumentType.ALINEAMIENTO)
    assert fields == []


def test_wide_strategy_reads_value_on_next_line() -> None:
    doc = load_text_document("p.pdf", ["CUENTA PREDIAL\n114-002-007-000"])
    strict, _ = extract_fields(doc, DocumentType.PREDIAL, strategy="heuristica")
    wide, _ = extract_fields(doc, DocumentType.PREDIAL, strategy="heuristica_amplia")
    assert not any(f.name == "cuenta_predial" for f in strict)
    assert any(f.name == "cuenta_predial" and f.value == "114-002-007-000" for f in wide)


def test_llm_quotes_are_verified_against_the_text() -> None:
    doc = load_text_document("p.pdf", ["SUP. TERRENO 250.00 M2\nCONTRIBUYENTE JUAN EJEMPLO"])
    answer = {
        "campos": {
            "superficie_registrada": {
                "valor": "250.00 m2",
                "pagina": 1,
                "cita": "SUP. TERRENO 250.00 M2",
            },
            "propietario": {
                "valor": "PEDRO INVENTADO",
                "pagina": 1,
                "cita": "Propietario: PEDRO INVENTADO",
            },
        }
    }
    llm = FakeListChatModel(responses=[json.dumps(answer)])
    fields, _ = extract_fields(doc, DocumentType.PREDIAL, llm=llm, strategy="llm")
    by_name = {f.name: f for f in fields}
    assert by_name["superficie_registrada"].confidence == CONF_LLM_VERIFIED
    assert by_name["propietario"].confidence == CONF_LLM_UNVERIFIED
    assert by_name["propietario"].evidence is None


def test_invalid_llm_json_falls_back_to_heuristics() -> None:
    doc = next(d for d in demo_documents("cumple") if d.filename == "predial.pdf")
    llm = FakeListChatModel(responses=["no es json", "tampoco"])
    fields, missing = extract_fields(doc, DocumentType.PREDIAL, llm=llm)
    assert missing == []
    assert all(f.method == "heuristica" for f in fields)
