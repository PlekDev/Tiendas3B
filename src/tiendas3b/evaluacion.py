"""Mide la precisión del dictamen contra veredictos esperados (criterio de 30 %).

Etiquetas: JSON {"<carpeta del expediente>": "Cumple" | "Requiere revisión" | "No cumple"}.
Cada carpeta de `expedientes_dir` con etiqueta se analiza y se compara.
"""

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from tiendas3b.agents.orchestrator import analyze_expediente
from tiendas3b.demo import DEMO_CASES, demo_documents
from tiendas3b.ingestion.pdf_loader import LoadedDocument, load_expediente_dir
from tiendas3b.models.schemas import Recommendation


@dataclass(frozen=True)
class EvalRow:
    expediente: str
    expected: Recommendation
    got: Recommendation
    confidence: float
    seconds: float

    @property
    def ok(self) -> bool:
        return self.expected == self.got

    @property
    def false_cumple(self) -> bool:
        """El error más grave: aprobar un expediente que no debía pasar."""
        return self.got == Recommendation.CUMPLE and self.expected != Recommendation.CUMPLE


def _run(expediente: str, docs: list[LoadedDocument], expected: str, use_llm: bool) -> EvalRow:
    start = time.perf_counter()
    report = analyze_expediente(expediente, docs, use_llm=use_llm)
    return EvalRow(
        expediente=expediente,
        expected=Recommendation(expected),
        got=report.recommendation,
        confidence=report.confidence,
        seconds=time.perf_counter() - start,
    )


def evaluate_dirs(labels_path: Path, expedientes_dir: Path, use_llm: bool = True) -> list[EvalRow]:
    labels: dict[str, str] = json.loads(labels_path.read_text(encoding="utf-8"))
    rows: list[EvalRow] = []
    items = [(name, exp) for name, exp in labels.items() if (expedientes_dir / name).is_dir()]
    for idx, (name, expected) in enumerate(items, start=1):
        print(f"\r[{idx}/{len(items)}] evaluando {name}…", end="", file=sys.stderr, flush=True)
        folder = expedientes_dir / name
        rows.append(_run(name, load_expediente_dir(folder), expected, use_llm))
    if items:
        print(file=sys.stderr)
    return rows


def evaluate_demo(use_llm: bool = False) -> list[EvalRow]:
    rows: list[EvalRow] = []
    items = list(DEMO_CASES.items())
    for idx, (key, case) in enumerate(items, start=1):
        print(
            f"\r[{idx}/{len(items)}] evaluando {case.expediente_id}…",
            end="",
            file=sys.stderr,
            flush=True,
        )
        rows.append(_run(case.expediente_id, demo_documents(key), case.expected.value, use_llm))
    if items:
        print(file=sys.stderr)
    return rows


def format_rows(rows: list[EvalRow]) -> str:
    if not rows:
        return "No hubo expedientes con etiqueta. Revisa la ruta y el archivo de etiquetas."
    width = max(len(r.expediente) for r in rows)
    lines = [f"{'Expediente':<{width}}  {'Esperado':<18} {'Obtenido':<18} Conf.  Seg.  ¿OK?"]
    for r in rows:
        mark = "sí" if r.ok else ("NO · FALSO CUMPLE" if r.false_cumple else "no")
        lines.append(
            f"{r.expediente:<{width}}  {r.expected.value:<18} {r.got.value:<18} "
            f"{r.confidence:.2f}  {r.seconds:4.1f}  {mark}"
        )
    hits = sum(r.ok for r in rows)
    avg = sum(r.seconds for r in rows) / len(rows)
    lines.append("")
    lines.append(f"Aciertos: {hits}/{len(rows)} ({hits / len(rows):.0%})")
    lines.append(f"Falsos 'Cumple': {sum(r.false_cumple for r in rows)}")
    lines.append(f"Tiempo promedio por expediente: {avg:.1f} s")
    return "\n".join(lines)
