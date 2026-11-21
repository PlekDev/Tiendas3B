"""Métricas del reporte de precisión (N4): falsos Cumple, falsos No cumple, matriz."""

import json
from pathlib import Path

import pytest

from tiendas3b.evaluacion import (
    EvalRow,
    evaluate_demo,
    evaluate_dirs,
    format_rows,
    report_json,
    summarize,
)
from tiendas3b.models.schemas import Recommendation as R


def _row(name: str, expected: R, got: R | None, conf: float = 0.8) -> EvalRow:
    return EvalRow(name, expected, got, conf, 1.0, None if got else "RuntimeError")


ROWS = [
    _row("A", R.CUMPLE, R.CUMPLE, 0.9),
    _row("B", R.CUMPLE, R.NO_CUMPLE, 0.6),  # falso No cumple
    _row("C", R.NO_CUMPLE, R.CUMPLE, 0.5),  # falso Cumple
    _row("D", R.REQUIERE_REVISION, R.REQUIERE_REVISION, 0.7),
    _row("E", R.NO_CUMPLE, None),  # error de análisis
]


def test_resumen_cuenta_cada_tipo_de_error() -> None:
    s = summarize(ROWS)
    assert (s.total, s.aciertos, s.falsos_cumple, s.falsos_no_cumple, s.errores) == (
        5,
        2,
        1,
        1,
        1,
    )
    assert s.exactitud == pytest.approx(0.4)
    assert s.matriz["Cumple"]["No cumple"] == 1
    assert s.matriz["No cumple"]["Error"] == 1
    assert s.recall == {"Cumple": 0.5, "Requiere revisión": 1.0, "No cumple": 0.0}
    assert s.confianza_promedio_aciertos == pytest.approx(0.8)
    assert s.confianza_promedio_fallos == pytest.approx(0.55)  # el error no cuenta


def test_formato_marca_errores_y_lista_carpetas_faltantes() -> None:
    text = format_rows(ROWS, ["SIN-CARPETA"])
    assert "NO · FALSO NO CUMPLE" in text
    assert "NO · FALSO CUMPLE" in text
    assert "ERROR (RuntimeError)" in text
    assert "Falsos 'No cumple': 1" in text
    assert "SIN-CARPETA" in text


def test_json_solo_trae_ids_y_veredictos() -> None:
    data = report_json(ROWS)
    assert data["resumen"]["falsos_no_cumple"] == 1
    assert set(data["expedientes"][0]) == {
        "expediente",
        "esperado",
        "obtenido",
        "confianza",
        "segundos",
        "falso_cumple",
        "falso_no_cumple",
        "error",
    }
    json.dumps(data)  # serializable


def test_etiqueta_mal_escrita_falla_antes_de_correr(tmp_path: Path) -> None:
    labels = tmp_path / "etiquetas.json"
    labels.write_text(json.dumps({"EXP-1": "Requiere revision"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Veredictos inválidos"):
        evaluate_dirs(labels, tmp_path)


def test_etiqueta_sin_carpeta_se_reporta(tmp_path: Path) -> None:
    labels = tmp_path / "etiquetas.json"
    labels.write_text(json.dumps({"NO-EXISTE": "Cumple"}), encoding="utf-8")
    rows, missing = evaluate_dirs(labels, tmp_path)
    assert rows == [] and missing == ["NO-EXISTE"]


def test_demo_sin_llm_sigue_perfecto() -> None:
    s = summarize(evaluate_demo(use_llm=False))
    assert s.aciertos == s.total == 4
    assert s.falsos_cumple == s.falsos_no_cumple == 0
