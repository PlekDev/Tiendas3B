"""Logs estructurados y bitácora: IDs en cada línea y nada de datos personales."""

import json
import logging
from pathlib import Path

import pytest

from tiendas3b.agents.orchestrator import analyze_expediente
from tiendas3b.demo import demo_documents
from tiendas3b.logs import (
    APP_LOG,
    AUDIT_LOG,
    REDACTED,
    log_context,
    read_bitacora,
    record_dictamen,
    register_sensitive,
    rules_fingerprint,
    setup_logging,
)


@pytest.fixture
def log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    return tmp_path


def _lines(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_json_lines_carry_ids_and_redact_sensitive_values(log_dir: Path) -> None:
    logger = setup_logging("INFO")
    with log_context("EXP-1", request_id="abc123"):
        register_sensitive(["JUAN EJEMPLO FICTICIO"])
        logger.info("propietario %s", "JUAN EJEMPLO FICTICIO", extra={"event": "prueba"})
    logger.info("fuera de contexto")
    for handler in logger.handlers:
        handler.flush()

    first, second = _lines(log_dir / APP_LOG)
    assert first["expediente_id"] == "EXP-1"
    assert first["request_id"] == "abc123"
    assert first["event"] == "prueba"
    assert "JUAN" not in str(first["msg"]) and REDACTED in str(first["msg"])
    assert second["expediente_id"] is None


def test_long_messages_are_truncated(log_dir: Path) -> None:
    logger = setup_logging("INFO")
    logger.info("x" * 5000)
    for handler in logger.handlers:
        handler.flush()
    assert len(str(_lines(log_dir / APP_LOG)[0]["msg"])) <= 300


def test_setup_is_idempotent(log_dir: Path) -> None:
    setup_logging()
    logger = setup_logging()
    assert len(logger.handlers) == 2


def test_graph_steps_are_logged(log_dir: Path) -> None:
    logger = setup_logging("INFO")
    with log_context("DEMO-CUMPLE"):
        analyze_expediente("DEMO-CUMPLE", demo_documents("cumple"), use_llm=False)
    for handler in logger.handlers:
        handler.flush()
    agents = [line.get("agent") for line in _lines(log_dir / APP_LOG)]
    assert "clasificador" in agents and "dictaminador" in agents


def test_bitacora_has_no_personal_data(log_dir: Path) -> None:
    report = analyze_expediente("DEMO-NO-CUMPLE", demo_documents("no_cumple"), use_llm=False)
    entry = record_dictamen(report, origin="prueba", request_id="r1")
    raw = (log_dir / AUDIT_LOG).read_text(encoding="utf-8")
    assert entry["recommendation"] == "No cumple"
    assert entry["critical"] >= 1
    assert "INMOBILIARIA" not in raw and "MARÍA" not in raw and "Reforma" not in raw


def test_read_bitacora_newest_first_and_skips_broken_lines(log_dir: Path) -> None:
    report = analyze_expediente("A", demo_documents("cumple"), use_llm=False)
    record_dictamen(report, origin="prueba")
    with (log_dir / AUDIT_LOG).open("a", encoding="utf-8") as fh:
        fh.write("{línea rota\n")
    record_dictamen(report.model_copy(update={"expediente_id": "B"}), origin="prueba")
    assert [e["expediente_id"] for e in read_bitacora()] == ["B", "A"]


def test_rules_fingerprint_changes_with_rules(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text('{"x": 1}', encoding="utf-8")
    before = rules_fingerprint(tmp_path)
    (tmp_path / "a.json").write_text('{"x": 2}', encoding="utf-8")
    assert rules_fingerprint(tmp_path) != before


@pytest.fixture(autouse=True)
def _reset_logger() -> None:
    yield
    logger = logging.getLogger("tiendas3b")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
