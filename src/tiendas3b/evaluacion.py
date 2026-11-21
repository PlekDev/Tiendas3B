"""Mide la precisión del dictamen contra veredictos esperados (criterio de 30 %).

Etiquetas: JSON {"<carpeta del expediente>": "Cumple" | "Requiere revisión" | "No cumple"}.
Cada carpeta de `expedientes_dir` con etiqueta se analiza y se compara.

Los dos errores que más importan, y por eso se cuentan aparte:
- Falso "Cumple": se aprueba un expediente que no debía pasar (riesgo legal).
- Falso "No cumple": se descarta un expediente que sí podía continuar (el jurado lo
  penaliza explícitamente: "sin descartar expedientes que sí podían continuar").
"""

import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from tiendas3b.agents.orchestrator import analyze_expediente
from tiendas3b.demo import DEMO_CASES, demo_documents
from tiendas3b.ingestion.pdf_loader import LoadedDocument, load_expediente_dir
from tiendas3b.models.schemas import Recommendation

logger = logging.getLogger(__name__)

VERDICTS: tuple[Recommendation, ...] = (
    Recommendation.CUMPLE,
    Recommendation.REQUIERE_REVISION,
    Recommendation.NO_CUMPLE,
)


@dataclass(frozen=True)
class EvalRow:
    expediente: str
    expected: Recommendation
    got: Recommendation | None  # None: el análisis falló
    confidence: float
    seconds: float
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.expected == self.got

    @property
    def false_cumple(self) -> bool:
        """El error más grave: aprobar un expediente que no debía pasar."""
        return self.got == Recommendation.CUMPLE and self.expected != Recommendation.CUMPLE

    @property
    def false_no_cumple(self) -> bool:
        """Descartar un expediente que sí podía continuar."""
        return self.got == Recommendation.NO_CUMPLE and self.expected != Recommendation.NO_CUMPLE


@dataclass(frozen=True)
class EvalSummary:
    """Números para el pitch y para decidir si un cambio de prompt o umbral mejora."""

    total: int
    aciertos: int
    falsos_cumple: int
    falsos_no_cumple: int
    errores: int
    segundos_promedio: float
    confianza_promedio_aciertos: float
    confianza_promedio_fallos: float
    # matriz[esperado][obtenido] = conteo; "Error" cuando el análisis falló
    matriz: dict[str, dict[str, int]] = field(default_factory=dict)
    # Por veredicto esperado: de los que eran X, cuántos se dictaminaron X
    recall: dict[str, float] = field(default_factory=dict)
    sin_carpeta: list[str] = field(default_factory=list)

    @property
    def exactitud(self) -> float:
        return self.aciertos / self.total if self.total else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize(rows: list[EvalRow], sin_carpeta: list[str] | None = None) -> EvalSummary:
    columns = [v.value for v in VERDICTS] + ["Error"]
    matriz = {v.value: {c: 0 for c in columns} for v in VERDICTS}
    for r in rows:
        matriz[r.expected.value][r.got.value if r.got else "Error"] += 1
    recall = {
        v.value: matriz[v.value][v.value] / n
        for v in VERDICTS
        if (n := sum(matriz[v.value].values()))
    }
    return EvalSummary(
        total=len(rows),
        aciertos=sum(r.ok for r in rows),
        falsos_cumple=sum(r.false_cumple for r in rows),
        falsos_no_cumple=sum(r.false_no_cumple for r in rows),
        errores=sum(r.got is None for r in rows),
        segundos_promedio=_mean([r.seconds for r in rows]),
        confianza_promedio_aciertos=_mean([r.confidence for r in rows if r.ok]),
        confianza_promedio_fallos=_mean([r.confidence for r in rows if not r.ok and r.got]),
        matriz=matriz,
        recall=recall,
        sin_carpeta=list(sin_carpeta or []),
    )


def _run(expediente: str, docs: list[LoadedDocument], expected: str, use_llm: bool) -> EvalRow:
    start = time.perf_counter()
    try:
        report = analyze_expediente(expediente, docs, use_llm=use_llm)
    except Exception as exc:  # noqa: BLE001 - un expediente roto no tumba la evaluación
        logger.exception("Falló el análisis de %s", expediente)
        return EvalRow(
            expediente=expediente,
            expected=Recommendation(expected),
            got=None,
            confidence=0.0,
            seconds=time.perf_counter() - start,
            error=type(exc).__name__,
        )
    return EvalRow(
        expediente=expediente,
        expected=Recommendation(expected),
        got=report.recommendation,
        confidence=report.confidence,
        seconds=time.perf_counter() - start,
    )


def _progress(idx: int, total: int, name: str) -> None:
    """Avance en stderr (para no ensuciar la tabla de stdout)."""
    print(f"\r[{idx}/{total}] evaluando {name}…", end="", file=sys.stderr, flush=True)


def load_labels(labels_path: Path) -> dict[str, str]:
    """Lee y valida las etiquetas: un veredicto mal escrito se reporta antes de correr nada."""
    labels: dict[str, str] = json.loads(labels_path.read_text(encoding="utf-8"))
    valid = {v.value for v in VERDICTS}
    invalid = {k: v for k, v in labels.items() if v not in valid}
    if invalid:
        raise ValueError(
            f"Veredictos inválidos en {labels_path.name}: {invalid}. "
            f"Usa exactamente: {', '.join(sorted(valid))}."
        )
    return labels


def evaluate_dirs(
    labels_path: Path, expedientes_dir: Path, use_llm: bool = True
) -> tuple[list[EvalRow], list[str]]:
    """(filas evaluadas, etiquetas cuya carpeta no existe)."""
    labels = load_labels(labels_path)
    rows: list[EvalRow] = []
    missing: list[str] = []
    items: list[tuple[str, str]] = []
    for name, expected in labels.items():
        if (expedientes_dir / name).is_dir():
            items.append((name, expected))
        else:
            missing.append(name)
    for idx, (name, expected) in enumerate(items, start=1):
        _progress(idx, len(items), name)
        rows.append(_run(name, load_expediente_dir(expedientes_dir / name), expected, use_llm))
    if items:
        print(file=sys.stderr)
    return rows, missing


def evaluate_demo(use_llm: bool = False) -> list[EvalRow]:
    rows: list[EvalRow] = []
    items = list(DEMO_CASES.items())
    for idx, (key, case) in enumerate(items, start=1):
        _progress(idx, len(items), case.expediente_id)
        rows.append(_run(case.expediente_id, demo_documents(key), case.expected.value, use_llm))
    if items:
        print(file=sys.stderr)
    return rows


_SHORT = {"Cumple": "Cumple", "Requiere revisión": "Revisión", "No cumple": "No cumple"}


def _format_matrix(summary: EvalSummary) -> list[str]:
    columns = [v.value for v in VERDICTS]
    if any(row["Error"] for row in summary.matriz.values()):
        columns.append("Error")
    head = f"{'Esperado ↓ / Obtenido →':<24}" + "".join(f"{_SHORT.get(c, c):>11}" for c in columns)
    lines = [head]
    for expected, row in summary.matriz.items():
        if not sum(row.values()):
            continue
        lines.append(f"{_SHORT[expected]:<24}" + "".join(f"{row[c]:>11}" for c in columns))
    return lines


def format_rows(rows: list[EvalRow], sin_carpeta: list[str] | None = None) -> str:
    if not rows:
        msg = "No hubo expedientes con etiqueta. Revisa la ruta y el archivo de etiquetas."
        if sin_carpeta:
            msg += f"\nEtiquetas sin carpeta: {', '.join(sin_carpeta)}"
        return msg
    width = max(len(r.expediente) for r in rows)
    lines = [f"{'Expediente':<{width}}  {'Esperado':<18} {'Obtenido':<18} Conf.  Seg.  ¿OK?"]
    for r in rows:
        if r.got is None:
            mark = f"ERROR ({r.error})"
        elif r.ok:
            mark = "sí"
        elif r.false_cumple:
            mark = "NO · FALSO CUMPLE"
        elif r.false_no_cumple:
            mark = "NO · FALSO NO CUMPLE"
        else:
            mark = "no"
        got = r.got.value if r.got else "—"
        lines.append(
            f"{r.expediente:<{width}}  {r.expected.value:<18} {got:<18} "
            f"{r.confidence:.2f}  {r.seconds:4.1f}  {mark}"
        )
    s = summarize(rows, sin_carpeta)
    lines += ["", *_format_matrix(s), ""]
    lines.append(f"Aciertos: {s.aciertos}/{s.total} ({s.exactitud:.0%})")
    lines.append(f"Falsos 'Cumple': {s.falsos_cumple}  (aprobar uno que no debía pasar)")
    lines.append(f"Falsos 'No cumple': {s.falsos_no_cumple}  (descartar uno que sí podía seguir)")
    if s.errores:
        lines.append(f"Errores de análisis: {s.errores}")
    lines.append(
        "Acierto por veredicto: " + ", ".join(f"{_SHORT[k]} {v:.0%}" for k, v in s.recall.items())
    )
    lines.append(
        f"Confianza promedio: {s.confianza_promedio_aciertos:.2f} en aciertos · "
        f"{s.confianza_promedio_fallos:.2f} en fallos"
    )
    lines.append(f"Tiempo promedio por expediente: {s.segundos_promedio:.1f} s")
    if s.sin_carpeta:
        lines.append(f"Etiquetas sin carpeta (no evaluadas): {', '.join(s.sin_carpeta)}")
    return "\n".join(lines)


def report_json(rows: list[EvalRow], sin_carpeta: list[str] | None = None) -> dict[str, Any]:
    """Resumen + filas, para guardar y para el pitch. Solo IDs y veredictos, nunca contenido."""
    s = summarize(rows, sin_carpeta)
    return {
        "resumen": {**asdict(s), "exactitud": round(s.exactitud, 4)},
        "expedientes": [
            {
                "expediente": r.expediente,
                "esperado": r.expected.value,
                "obtenido": r.got.value if r.got else None,
                "confianza": r.confidence,
                "segundos": round(r.seconds, 2),
                "falso_cumple": r.false_cumple,
                "falso_no_cumple": r.false_no_cumple,
                "error": r.error,
            }
            for r in rows
        ],
    }
