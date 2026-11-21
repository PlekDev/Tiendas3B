"""Arma expedientes a partir de documentos sueltos (tarea V5).

Los ZIP del reto vienen por tipo de documento, no por inmueble. Aquí se clasifica cada
documento, se extraen sus llaves (clave catastral, cuenta predial, folio, dirección) y se
juntan los que comparten una llave o tienen la misma dirección con el mismo número.

Es una propuesta automática: si el comité da una convención de nombres o una lista de
expedientes, esa manda. Revisa siempre el plan con `--simular` antes de copiar.
"""

import filecmp
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from rapidfuzz import fuzz

from tiendas3b.agents.classifier import classify
from tiendas3b.agents.extractor import extract_fields
from tiendas3b.ingestion.pdf_loader import LoadedDocument
from tiendas3b.models.schemas import DocumentType
from tiendas3b.rules.criteria import DOCUMENT_LABELS, REQUIRED_DOCUMENT_TYPES
from tiendas3b.text import normalize, normalize_id

ID_FIELDS = ("cuenta_predial", "identificacion_predio", "referencia_cruzada")
ADDRESS_FIELDS = ("direccion", "direccion_oficial")
MIN_ID_CHARS = 6  # evita unir por "12" o "A1"
ADDRESS_THRESHOLD = 92.0


@dataclass(frozen=True)
class DocKeys:
    path: Path
    document_type: DocumentType
    ids: frozenset[str]
    address: str | None
    number: str | None


@dataclass
class Group:
    expediente_id: str
    documents: list[DocKeys] = field(default_factory=list)

    @property
    def types(self) -> set[DocumentType]:
        return {d.document_type for d in self.documents}

    @property
    def missing(self) -> list[DocumentType]:
        return [t for t in REQUIRED_DOCUMENT_TYPES if t not in self.types]


def _street_number(text: str | None) -> str | None:
    match = re.search(r"\d+", text or "")
    return match.group() if match else None


def document_keys(
    document: LoadedDocument, path: Path, llm: BaseChatModel | None = None
) -> DocKeys:
    """Clasifica el documento y saca las llaves que sirven para emparejarlo con otros."""
    doc_type = classify(document, llm).document_type
    fields, _ = extract_fields(document, doc_type, llm)
    values = {f.name: (f.value or "").strip() for f in fields}
    ids = frozenset(
        key
        for name in ID_FIELDS
        if (key := normalize_id(values.get(name, ""))) and len(key) >= MIN_ID_CHARS
    )
    address = next((values[n] for n in ADDRESS_FIELDS if values.get(n)), None)
    number = _street_number(values.get("numero_oficial")) or _street_number(address)
    return DocKeys(path, doc_type, ids, address, number)


def _same_property(a: DocKeys, b: DocKeys, threshold: float) -> bool:
    if a.ids & b.ids:
        return True
    if not (a.address and b.address):
        return False
    if a.number and b.number and a.number != b.number:
        return False
    return bool(fuzz.token_set_ratio(normalize(a.address), normalize(b.address)) >= threshold)


def group_documents(keys: list[DocKeys], threshold: float = ADDRESS_THRESHOLD) -> list[Group]:
    """Une documentos del mismo inmueble (unión de conjuntos sobre llaves y direcciones)."""
    ordered = sorted(keys, key=lambda k: str(k.path))
    parent = list(range(len(ordered)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(ordered):
        for j in range(i + 1, len(ordered)):
            if _same_property(a, ordered[j], threshold):
                parent[find(j)] = find(i)

    clusters: dict[int, list[DocKeys]] = {}
    for i, key in enumerate(ordered):
        clusters.setdefault(find(i), []).append(key)
    groups = sorted(clusters.values(), key=lambda docs: (-len(docs), str(docs[0].path)))
    return [Group(f"EXP-{n:03d}", docs) for n, docs in enumerate(groups, start=1)]


def write_groups(groups: list[Group], destination: Path) -> list[Path]:
    """Copia (no mueve) cada documento a destination/<EXP-xxx>/. Los originales no se tocan."""
    folders: list[Path] = []
    for group in groups:
        folder = destination / group.expediente_id
        folder.mkdir(parents=True, exist_ok=True)
        for doc in group.documents:
            target, n = folder / doc.path.name, 1
            while target.exists() and not filecmp.cmp(target, doc.path, shallow=False):
                n += 1  # mismo nombre, otro contenido: escritura.pdf, escritura_2.pdf…
                target = folder / f"{doc.path.stem}_{n}{doc.path.suffix}"
            shutil.copy2(doc.path, target)
        folders.append(folder)
    return folders


def format_plan(groups: list[Group], root: Path) -> str:
    """Plan legible. Trae nombres de archivo: es para uso local del equipo."""
    complete = sum(1 for g in groups if not g.missing)
    lines = [f"{len(groups)} expedientes propuestos · {complete} completos", ""]
    for group in groups:
        missing = ", ".join(DOCUMENT_LABELS[t] for t in group.missing) or "ninguno"
        lines.append(
            f"{group.expediente_id} · {len(group.documents)} documentos · faltan: {missing}"
        )
        for doc in group.documents:
            try:
                name = doc.path.relative_to(root)
            except ValueError:
                name = doc.path
            lines.append(f"    {DOCUMENT_LABELS[doc.document_type]:<32} {name}")
    return "\n".join(lines)
