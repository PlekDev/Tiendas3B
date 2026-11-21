"""Línea de comandos:  tiendas3b <comando>   (o  python -m tiendas3b <comando>)

analizar <carpeta|archivos…>   Dictamina un expediente y guarda el JSON
ejemplo [caso]                 Expediente ficticio: cumple, revision, no_cumple, incompleto
evaluar                        Precisión contra veredictos esperados
agrupar [origen]               Arma expedientes desde documentos sueltos (ZIP por tipo)
demo-pdfs                      Escribe los expedientes ficticios como PDFs
estado                         Configuración, LLM y cartuchos de reglas
diagnostico [carpeta]          OCR y clasificador sobre documentos reales (solo conteos)
grafo                          Diagrama Mermaid del grafo de agentes
api                            Levanta la API para la interfaz
"""

import argparse
import sys
from pathlib import Path

from tiendas3b.agents.orchestrator import analyze_expediente, graph_mermaid
from tiendas3b.config import PROJECT_ROOT, get_settings
from tiendas3b.demo import DEMO_CASES, demo_documents, write_demo_pdfs
from tiendas3b.evaluacion import evaluate_demo, evaluate_dirs, format_rows
from tiendas3b.ingestion.diagnostico import (
    diagnose,
    find_documents,
    format_details,
    format_summary,
)
from tiendas3b.ingestion.pdf_loader import (
    is_document_file,
    load_document,
    load_expediente_dir,
)
from tiendas3b.llm import describe_mode, is_reachable
from tiendas3b.logs import log_context, record_dictamen, setup_logging
from tiendas3b.models.schemas import ExpedienteReport
from tiendas3b.rules.criteria import DOCUMENT_LABELS
from tiendas3b.rules.engine import load_cartuchos

_ICON = {"Cumple": "[OK]", "Requiere revisión": "[REVISAR]", "No cumple": "[NO]"}


def render_report(report: ExpedienteReport) -> str:
    """Resumen legible para la terminal: veredicto, razones, hallazgos con cita y traza."""
    out = [
        f"Expediente {report.expediente_id}",
        f"{_ICON[report.recommendation.value]} {report.recommendation.value}"
        f"  ·  confianza {report.confidence:.0%}  ·  {report.processing_ms} ms"
        f"  ·  modo {report.llm_mode}",
        "",
        "Razones:",
        *[f"  - {r}" for r in report.reasons],
        "",
        "Documentos:",
    ]
    for doc in report.document_analyses:
        failed = [r for r in doc.rule_evaluations if not r.passed]
        out.append(
            f"  {doc.document_name}: {DOCUMENT_LABELS[doc.document_type]}"
            f" ({doc.classification_confidence:.0%}) · {len(doc.extracted_fields)} campos"
            f" · {len(failed)} reglas no cumplidas"
        )
        for field in doc.extracted_fields:
            where = f"p.{field.evidence.page}" if field.evidence else "sin cita"
            out.append(f"      {field.name}: {field.value}  [{where}, {field.confidence:.2f}]")
    if report.missing_document_types:
        names = ", ".join(DOCUMENT_LABELS[t] for t in report.missing_document_types)
        out += ["", f"Faltan: {names}"]
    if report.cross_validation_issues:
        out += ["", "Cruces con discrepancia:"]
        for issue in report.cross_validation_issues:
            out.append(f"  [{issue.severity}] {issue.description}")
            for ev in issue.evidence:
                out.append(f"      {ev.document_name} p.{ev.page}: «{ev.snippet}»")
    out += ["", "Traza del grafo:"]
    out += [f"  {s.agent:<40} {s.ms:>6} ms  {s.detail}" for s in report.trace]
    return "\n".join(out)


def _cmd_analizar(args: argparse.Namespace) -> int:
    targets = [Path(p) for p in args.rutas]
    if len(targets) == 1 and targets[0].is_dir():
        documents = load_expediente_dir(targets[0])
        expediente_id = args.id or targets[0].name
    else:
        documents = [load_document(p) for p in targets if is_document_file(p)]
        expediente_id = args.id or "EXP-CLI"
    if not documents:
        print("No encontré PDFs ni imágenes en esa ruta.", file=sys.stderr)
        return 1
    with log_context(expediente_id) as request_id:
        report = analyze_expediente(expediente_id, documents, use_llm=not args.sin_llm)
        record_dictamen(report, "cli", request_id)
    _emit(report, args)
    return 0


def _cmd_ejemplo(args: argparse.Namespace) -> int:
    case = DEMO_CASES[args.caso]
    report = analyze_expediente(case.expediente_id, demo_documents(args.caso), use_llm=False)
    _emit(report, args)
    return 0


def _emit(report: ExpedienteReport, args: argparse.Namespace) -> None:
    print(report.model_dump_json(indent=2) if args.json else render_report(report))
    if args.salida:
        Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
        Path(args.salida).write_text(report.model_dump_json(indent=2), encoding="utf-8")
        print(f"\nJSON guardado en {args.salida}", file=sys.stderr)


def _cmd_evaluar(args: argparse.Namespace) -> int:
    if args.demo:
        rows = evaluate_demo(use_llm=not args.sin_llm)
    else:
        rows = evaluate_dirs(Path(args.etiquetas), Path(args.expedientes), not args.sin_llm)
    print(format_rows(rows))
    return 0


def _cmd_agrupar(args: argparse.Namespace) -> int:
    from tiendas3b.ingestion.agrupar import (
        document_keys,
        format_plan,
        group_documents,
        write_groups,
    )
    from tiendas3b.llm import get_chat_model

    root = Path(args.origen)
    paths = sorted(p for p in root.rglob("*") if is_document_file(p))
    if not paths:
        print(f"No encontré PDFs ni imágenes en {root}.", file=sys.stderr)
        return 1
    llm = None if args.sin_llm else get_chat_model()
    keys = []
    for i, path in enumerate(paths, start=1):
        print(f"\r[{i}/{len(paths)}] clasificando…", end="", file=sys.stderr, flush=True)
        keys.append(document_keys(load_document(path), path, llm))
    print(file=sys.stderr)
    groups = group_documents(keys)
    print(format_plan(groups, root))
    if args.simular:
        print("\nSimulación: no se copió nada. Quita --simular para crear las carpetas.")
        return 0
    write_groups(groups, Path(args.destino))
    print(f"\nCopiados a {args.destino} (los originales no se tocaron).")
    return 0


def _cmd_demo_pdfs(args: argparse.Namespace) -> int:
    for folder in write_demo_pdfs(Path(args.destino)):
        print(f"Escrito: {folder}")
    return 0


def _cmd_diagnostico(args: argparse.Namespace) -> int:
    root = Path(args.carpeta)
    paths = find_documents(root)
    rows = []
    for i, path in enumerate(paths, start=1):
        print(f"\r[{i}/{len(paths)}] leyendo…", end="", file=sys.stderr, flush=True)
        rows.append(diagnose(path))
    print(file=sys.stderr)
    if args.detalle:
        print(format_details(rows, root) + "\n")
    print(format_summary(rows))
    return 0


def _cmd_estado(_: argparse.Namespace) -> int:
    settings = get_settings()
    cartuchos = load_cartuchos()
    print(f"Modo LLM:     {describe_mode()}")
    if settings.llm_enabled:
        print(f"LLM responde: {'sí' if is_reachable() else 'NO (se usará la ruta heurística)'}")
    print(f"Reglas en:    {settings.rules_dir}")
    for cartucho in sorted(cartuchos.values(), key=lambda c: c.nombre):
        active = sum(r.activa for r in cartucho.reglas)
        print(f"  {cartucho.nombre}: {active} reglas activas de {len(cartucho.reglas)}")
    print(f"OCR idioma:   {settings.ocr_lang}")
    return 0


def _cmd_grafo(_: argparse.Namespace) -> int:
    print(graph_mermaid())
    return 0


def _cmd_api(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("tiendas3b.api.main:app", host=args.host, port=args.puerto, reload=args.reload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tiendas3b", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="comando", required=True)

    def output_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument("--json", action="store_true", help="Imprime el JSON completo.")
        p.add_argument("--salida", help="Guarda el JSON en este archivo.")

    p = sub.add_parser("analizar", help="Dictamina un expediente.")
    p.add_argument("rutas", nargs="+", help="Carpeta del expediente o lista de archivos.")
    p.add_argument(
        "--id", help="Identificador del expediente (por defecto, el nombre de la carpeta)."
    )
    p.add_argument("--sin-llm", action="store_true", help="Solo ruta heurística.")
    output_flags(p)
    p.set_defaults(func=_cmd_analizar)

    p = sub.add_parser("ejemplo", help="Corre un expediente ficticio.")
    p.add_argument("caso", nargs="?", default="revision", choices=sorted(DEMO_CASES))
    output_flags(p)
    p.set_defaults(func=_cmd_ejemplo)

    p = sub.add_parser("evaluar", help="Precisión contra veredictos esperados.")
    p.add_argument("--etiquetas", default=str(PROJECT_ROOT / "evaluacion" / "etiquetas.json"))
    p.add_argument("--expedientes", default=str(PROJECT_ROOT / "data" / "expedientes"))
    p.add_argument("--demo", action="store_true", help="Usa los casos ficticios en memoria.")
    p.add_argument("--sin-llm", action="store_true")
    p.set_defaults(func=_cmd_evaluar)

    p = sub.add_parser("agrupar", help="Arma expedientes desde documentos sueltos.")
    p.add_argument("origen", nargs="?", default=str(PROJECT_ROOT / "data" / "raw"))
    p.add_argument("--destino", default=str(PROJECT_ROOT / "data" / "expedientes"))
    p.add_argument("--simular", action="store_true", help="Muestra el plan sin copiar nada.")
    p.add_argument("--sin-llm", action="store_true")
    p.set_defaults(func=_cmd_agrupar)

    p = sub.add_parser("demo-pdfs", help="Escribe los casos ficticios como PDFs.")
    p.add_argument("--destino", default=str(PROJECT_ROOT / "data" / "expedientes"))
    p.set_defaults(func=_cmd_demo_pdfs)

    sub.add_parser("estado", help="Configuración y salud.").set_defaults(func=_cmd_estado)

    p = sub.add_parser("diagnostico", help="OCR y clasificador sobre documentos reales.")
    p.add_argument("carpeta", nargs="?", default=str(PROJECT_ROOT / "data" / "raw"))
    p.add_argument(
        "--detalle",
        action="store_true",
        help="Una línea por archivo (trae nombres de archivo: no la compartas fuera del equipo).",
    )
    p.set_defaults(func=_cmd_diagnostico)
    sub.add_parser("grafo", help="Diagrama Mermaid del grafo.").set_defaults(func=_cmd_grafo)

    p = sub.add_parser("api", help="Levanta la API.")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--puerto", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    p.set_defaults(func=_cmd_api)
    return parser


def main(argv: list[str] | None = None) -> int:
    setup_logging(console_level="WARNING")
    args = build_parser().parse_args(argv)
    code: int = args.func(args)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
