"""API de la demo: salud, casos de ejemplo y análisis de archivos subidos."""

from pathlib import Path

from fastapi.testclient import TestClient

from tiendas3b.api.main import app
from tiendas3b.demo import write_demo_pdfs

client = TestClient(app)


def test_status() -> None:
    data = client.get("/api/v1/status").json()
    assert data["api"] == "ok"
    assert len(data["cartuchos"]) == 4


def test_demo_cases_and_example() -> None:
    cases = client.get("/api/v1/casos").json()
    assert {c["caso"] for c in cases} >= {"cumple", "revision", "no_cumple"}
    report = client.get("/api/v1/ejemplo", params={"caso": "no_cumple"}).json()
    assert report["recommendation"] == "No cumple"
    assert report["trace"]
    assert client.get("/api/v1/ejemplo", params={"caso": "x"}).status_code == 404


def test_analyze_uploaded_pdfs(tmp_path: Path) -> None:
    folder = next(f for f in write_demo_pdfs(tmp_path) if f.name == "DEMO-CUMPLE")
    files = [
        ("files", (p.name, p.read_bytes(), "application/pdf")) for p in sorted(folder.iterdir())
    ]
    response = client.post(
        "/api/v1/analizar", files=files, data={"expediente_id": "SUBIDO", "usar_llm": "false"}
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["expediente_id"] == "SUBIDO"
    assert report["recommendation"] == "Cumple"


def test_rejects_unsupported_files() -> None:
    response = client.post("/api/v1/analizar", files=[("files", ("a.docx", b"x", "text/plain"))])
    assert response.status_code == 415
