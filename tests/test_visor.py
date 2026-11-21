"""Visor: ubica cada dato en la página (capa de texto del PDF)."""

from pathlib import Path

from fastapi.testclient import TestClient

from tiendas3b.api.main import app
from tiendas3b.demo import write_demo_pdf
from tiendas3b.visor import MarkIn, build_view

PAGES = [
    "Cuenta predial: 114-002-007-000\n"
    "Superficie de terreno: 850.00 m2\n"
    "Superficie construida: 0.00 m2"
]


def test_locates_value_inside_its_quote(tmp_path: Path) -> None:
    pdf = write_demo_pdf(tmp_path / "predial.pdf", PAGES)
    marks = [
        MarkIn(id="sup", texto="850.00 m2", contexto="Superficie de terreno: 850.00 m2", pagina=1),
        MarkIn(id="clave", texto="114-002-007-000", pagina=1),
    ]
    view = build_view(pdf, marks)
    assert [p.source for p in view.pages] == ["pdf"]
    assert view.pages[0].image.startswith("data:image/jpeg;base64,")
    found = {m.id: m for m in view.marks}
    assert found.keys() == {"sup", "clave"} and view.missing == []
    x0, y0, x1, y1 = found["sup"].rects[0]
    assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1
    assert found["sup"].exact


def test_numbers_must_match(tmp_path: Path) -> None:
    """960 m2 no debe marcarse sobre 850 m2 ni sobre 0.00 m2 aunque el texto se parezca."""
    pdf = write_demo_pdf(tmp_path / "predial.pdf", PAGES)
    view = build_view(pdf, [MarkIn(id="x", texto="960.00 m2", pagina=1)])
    assert view.marks == [] and view.missing == ["x"]


def test_visor_ejemplo_endpoint() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/v1/visor/ejemplo",
        data={
            "expediente_id": "DEMO-CUMPLE",
            "documento": "predial.pdf",
            "marcas": '[{"id": "a", "texto": "FR-998877"}]',
        },
    )
    assert res.status_code == 200
    assert [m["id"] for m in res.json()["marks"]] == ["a"]
    bad = client.post("/api/v1/visor/ejemplo", data={"expediente_id": "NO", "documento": "x.pdf"})
    assert bad.status_code == 404
