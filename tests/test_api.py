"""API de la demo: salud, casos de ejemplo y análisis de archivos subidos."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tiendas3b.api.jobs import JobQueue
from tiendas3b.api.main import app
from tiendas3b.demo import write_demo_pdfs

client = TestClient(app)


@pytest.fixture(autouse=True)
def _logs_en_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))


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


def test_bitacora_records_uploaded_analysis(tmp_path: Path) -> None:
    folder = next(f for f in write_demo_pdfs(tmp_path) if f.name == "DEMO-NO-CUMPLE")
    files = [
        ("files", (p.name, p.read_bytes(), "application/pdf")) for p in sorted(folder.iterdir())
    ]
    client.post("/api/v1/analizar", files=files, data={"expediente_id": "B-1", "usar_llm": "false"})
    entries = client.get("/api/v1/bitacora").json()
    assert entries[0]["expediente_id"] == "B-1"
    assert entries[0]["recommendation"] == "No cumple"
    assert entries[0]["origin"] == "api"


def test_job_queue_three_concurrent_submissions(tmp_path: Path) -> None:
    """Criterio de aceptación A4: 3 envíos simultáneos se encolan y los tres terminan."""
    folder = next(f for f in write_demo_pdfs(tmp_path) if f.name == "DEMO-CUMPLE")
    pdf_payloads = [(p.name, p.read_bytes()) for p in sorted(folder.iterdir())]

    job_ids: list[str] = []
    for idx in range(1, 4):
        files = [("files", (name, data, "application/pdf")) for name, data in pdf_payloads]
        resp = client.post(
            "/api/v1/trabajos",
            files=files,
            data={"expediente_id": f"EXP-COLA-{idx}", "usar_llm": "false"},
        )
        assert resp.status_code == 202, resp.text
        body = resp.json()
        assert body["id"] == body["job_id"]
        assert body["expediente_id"] == f"EXP-COLA-{idx}"
        job_ids.append(body["id"])

    # Esperar hasta que los 3 trabajos terminen
    deadline = time.monotonic() + 15.0
    completed: dict[str, dict[str, object]] = {}
    while len(completed) < 3 and time.monotonic() < deadline:
        for jid in job_ids:
            if jid in completed:
                continue
            status_resp = client.get(f"/api/v1/trabajos/{jid}")
            assert status_resp.status_code == 200
            data = status_resp.json()
            if data["status"] in ("completed", "failed"):
                completed[jid] = data
        if len(completed) < 3:
            time.sleep(0.05)

    assert len(completed) == 3
    for idx, jid in enumerate(job_ids, start=1):
        job_data = completed[jid]
        assert job_data["status"] == "completed"
        assert job_data["position"] == 0
        result = job_data["result"]
        assert isinstance(result, dict)
        assert result["expediente_id"] == f"EXP-COLA-{idx}"
        assert result["recommendation"] == "Cumple"

    list_resp = client.get("/api/v1/trabajos")
    assert list_resp.status_code == 200
    listed_ids = {item["id"] for item in list_resp.json()}
    assert set(job_ids) <= listed_ids


def test_job_queue_not_found_and_ttl_expiration(tmp_path: Path) -> None:
    assert client.get("/api/v1/trabajos/inexistente").status_code == 404

    folder = next(f for f in write_demo_pdfs(tmp_path) if f.name == "DEMO-CUMPLE")
    short_queue = JobQueue(max_workers=1, ttl_s=1)
    tmp_job_dir = tmp_path / "job_tmp"
    tmp_job_dir.mkdir()
    copied: list[Path] = []
    for p in sorted(folder.iterdir()):
        dest = tmp_job_dir / p.name
        dest.write_bytes(p.read_bytes())
        copied.append(dest)

    submitted = short_queue.submit("EXP-TTL", tmp_job_dir, copied, usar_llm=False)
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        current = short_queue.get(submitted.id)
        if current and current.status == "completed":
            break
        time.sleep(0.05)

    assert not tmp_job_dir.exists(), "El directorio temporal debe borrarse al terminar el trabajo."
    time.sleep(1.1)
    assert short_queue.get(submitted.id) is None
