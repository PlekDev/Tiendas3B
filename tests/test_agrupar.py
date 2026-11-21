"""Armado de expedientes: une por llaves compartidas o por la misma dirección y número."""

from pathlib import Path

from tiendas3b.ingestion.agrupar import (
    DocKeys,
    document_keys,
    format_plan,
    group_documents,
    write_groups,
)
from tiendas3b.ingestion.pdf_loader import load_text_document
from tiendas3b.models.schemas import DocumentType

# Dos inmuebles FICTICIOS mezclados, como vendrían de los ZIP por tipo.
_DOCS = {
    "escrituras/e1.pdf": "ESCRITURA PÚBLICA\nNOTARÍA 3\nComprador: DEMO UNO SA DE CV\n"
    "Domicilio del inmueble: Av. Uno No. 100, Col. Centro\nClave catastral: 111-222-333",
    "predial/p1.pdf": "RECIBO DEL IMPUESTO PREDIAL\nCuenta predial: 111-222-333\n"
    "Ubicación del predio: Avenida Uno 100, Colonia Centro",
    "alineamiento/a1.pdf": "CONSTANCIA DE ALINEAMIENTO Y NÚMERO OFICIAL\n"
    "Dirección oficial: Av. Uno 100\nNúmero oficial asignado: 100\nClave catastral: 111-222-333",
    "uso/u1.pdf": "CONSTANCIA DE USO DE SUELO\nDomicilio del predio: Av. Uno 100, Col. Centro\n"
    "Uso de suelo autorizado: Comercial",
    "predial/p2.pdf": "RECIBO DEL IMPUESTO PREDIAL\nCuenta predial: 999-888-777\n"
    "Ubicación del predio: Calle Dos 50, Col. Norte",
    "alineamiento/a2.pdf": "CONSTANCIA DE ALINEAMIENTO Y NÚMERO OFICIAL\n"
    "Dirección oficial: Calle Dos 50\nNúmero oficial asignado: 50\nClave catastral: 999-888-777",
}


def _keys() -> list[DocKeys]:
    return [
        document_keys(load_text_document(Path(name).name, [text]), Path(name))
        for name, text in _DOCS.items()
    ]


def test_groups_two_properties() -> None:
    groups = group_documents(_keys())
    assert len(groups) == 2
    first, second = groups
    assert first.types == set(DocumentType) - {DocumentType.DESCONOCIDO}
    assert first.missing == []
    assert {d.path.name for d in second.documents} == {"p2.pdf", "a2.pdf"}
    assert second.missing == [DocumentType.ESCRITURAS, DocumentType.USO_DE_SUELO]


def test_same_street_different_number_is_not_merged() -> None:
    a = DocKeys(Path("a.pdf"), DocumentType.PREDIAL, frozenset(), "Calle Dos 50", "50")
    b = DocKeys(Path("b.pdf"), DocumentType.USO_DE_SUELO, frozenset(), "Calle Dos 52", "52")
    assert len(group_documents([a, b])) == 2


def test_write_groups_copies_without_touching_originals(tmp_path: Path) -> None:
    src = tmp_path / "raw"
    src.mkdir()
    (src / "p.pdf").write_bytes(b"uno")
    (src / "otra").mkdir()
    (src / "otra" / "p.pdf").write_bytes(b"dos")
    keys = [
        DocKeys(src / "p.pdf", DocumentType.PREDIAL, frozenset({"111222"}), None, None),
        DocKeys(src / "otra" / "p.pdf", DocumentType.ESCRITURAS, frozenset({"111222"}), None, None),
    ]
    groups = group_documents(keys)
    [folder] = write_groups(groups, tmp_path / "exp")
    write_groups(groups, tmp_path / "exp")  # correrlo dos veces no duplica
    assert sorted(p.name for p in folder.iterdir()) == ["p.pdf", "p_2.pdf"]
    assert (src / "p.pdf").read_bytes() == b"uno"
    assert "EXP-001" in format_plan(groups, src)
