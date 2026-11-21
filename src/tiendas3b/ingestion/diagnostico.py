"""Diagnóstico de ingesta y clasificación sobre documentos reales (tareas V2 y V3).

Se corre en local sobre `data/raw/`. El resumen solo trae conteos y porcentajes, así que
se puede compartir con el equipo sin exponer el contenido de los documentos.

Si los archivos están en carpetas por tipo (`data/raw/predial/…`), el nombre de la carpeta
se toma como el tipo esperado y se mide el acierto del clasificador.
"""

import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from tiendas3b.agents.classifier import classify
from tiendas3b.ingestion.pdf_loader import is_document_file, load_document
from tiendas3b.models.schemas import DocumentType
from tiendas3b.rules.criteria import DOCUMENT_LABELS
from tiendas3b.text import normalize

_FOLDER_HINTS: tuple[tuple[str, DocumentType], ...] = (
    ("escritura", DocumentType.ESCRITURAS),
    ("predial", DocumentType.PREDIAL),
    ("alineamiento", DocumentType.ALINEAMIENTO),
    ("numero oficial", DocumentType.ALINEAMIENTO),
    ("uso de suelo", DocumentType.USO_DE_SUELO),
    ("uso suelo", DocumentType.USO_DE_SUELO),
)


@dataclass(frozen=True)
class DocDiagnosis:
    path: Path
    expected: DocumentType | None
    got: DocumentType
    confidence: float
    pages: int
    ocr_pages: int
    empty_pages: int
    chars: int
    seconds: float

    @property
    def correct(self) -> bool | None:
        return None if self.expected is None else self.expected == self.got


def expected_type(path: Path) -> DocumentType | None:
    """Tipo esperado según la carpeta que contiene al archivo, si su nombre lo indica."""
    folder = normalize(path.parent.name.replace("_", " "))
    for hint, doc_type in _FOLDER_HINTS:
        if hint in folder:
            return doc_type
    return None


def find_documents(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if is_document_file(p))


def diagnose(path: Path) -> DocDiagnosis:
    start = time.perf_counter()
    doc = load_document(path)
    result = classify(doc)
    return DocDiagnosis(
        path=path,
        expected=expected_type(path),
        got=result.document_type,
        confidence=result.confidence,
        pages=len(doc.pages),
        ocr_pages=doc.ocr_pages,
        empty_pages=sum(1 for p in doc.pages if p.source == "vacia"),
        chars=sum(len(p.text) for p in doc.pages),
        seconds=time.perf_counter() - start,
    )


def format_details(rows: list[DocDiagnosis], root: Path) -> str:
    """Una línea por archivo. Trae nombres de archivo: no la compartas fuera del equipo."""
    lines = ["Archivo | Esperado | Clasificado | Conf. | Págs | OCR | Vacías | ¿OK?"]
    for r in rows:
        expected = DOCUMENT_LABELS[r.expected] if r.expected else "—"
        ok = {True: "sí", False: "NO", None: "—"}[r.correct]
        lines.append(
            f"{r.path.relative_to(root)} | {expected} | {DOCUMENT_LABELS[r.got]} | "
            f"{r.confidence:.2f} | {r.pages} | {r.ocr_pages} | {r.empty_pages} | {ok}"
        )
    return "\n".join(lines)


def format_summary(rows: list[DocDiagnosis]) -> str:
    """Solo conteos y porcentajes: se puede pegar en estado/victor.md."""
    if not rows:
        return "No encontré PDFs ni imágenes en esa carpeta."
    pages = sum(r.pages for r in rows)
    ocr = sum(r.ocr_pages for r in rows)
    empty = sum(r.empty_pages for r in rows)
    avg = sum(r.seconds for r in rows) / len(rows)
    lines = [
        f"Documentos: {len(rows)} · páginas: {pages}",
        f"Páginas leídas con OCR: {ocr} ({ocr / pages:.0%})" if pages else "Páginas: 0",
        f"Páginas sin texto aun con OCR: {empty} ({empty / pages:.0%})" if pages else "",
        f"Tiempo promedio de lectura + clasificación: {avg:.1f} s",
        "",
        "Clasificación:",
    ]
    by_type = Counter(r.got for r in rows)
    for doc_type, count in sorted(by_type.items(), key=lambda kv: kv[0].value):
        lines.append(f"  {DOCUMENT_LABELS[doc_type]}: {count}")
    labeled = [r for r in rows if r.correct is not None]
    if labeled:
        hits = sum(1 for r in labeled if r.correct)
        lines += [
            "",
            f"Acierto contra la carpeta: {hits}/{len(labeled)} ({hits / len(labeled):.0%})",
        ]
        for doc_type in sorted({r.expected for r in labeled if r.expected}, key=lambda t: t.value):
            group = [r for r in labeled if r.expected == doc_type]
            ok = sum(1 for r in group if r.correct)
            confused = Counter(DOCUMENT_LABELS[r.got] for r in group if not r.correct)
            extra = f" · confundidos con: {dict(confused)}" if confused else ""
            lines.append(f"  {DOCUMENT_LABELS[doc_type]}: {ok}/{len(group)}{extra}")
    low = sum(1 for r in rows if r.confidence < 0.6)
    lines.append(f"Clasificaciones con confianza < 0.6: {low}")
    return "\n".join(line for line in lines if line is not None)
