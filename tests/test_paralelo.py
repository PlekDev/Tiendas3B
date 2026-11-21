"""Paralelismo: OCR por página y LLM por documento, sin perder orden ni contexto de logs."""

import contextvars
import threading
import time
from pathlib import Path

import pymupdf
import pytest

from tiendas3b.agents.orchestrator import _parallel_map
from tiendas3b.ingestion import pdf_loader


def _blank_pdf(path: Path, pages: int) -> Path:
    with pymupdf.open() as pdf:  # type: ignore[no-untyped-call]
        for _ in range(pages):
            pdf.new_page()
        pdf.save(path)
    return path


def test_ocr_runs_pages_in_parallel_and_keeps_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("PIL")
    pdf = _blank_pdf(tmp_path / "escaneo.pdf", pages=6)
    active, peak, lock = 0, 0, threading.Lock()
    seen: list[int] = []

    def fake_ocr(image: object, lang: str) -> str:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            seen.append(len(seen) + 1)
            n = len(seen)
        time.sleep(0.05)
        with lock:
            active -= 1
        return f"texto reconocido de la página número {n} con suficiente largo"

    monkeypatch.setattr(pdf_loader, "_ocr_image", fake_ocr)
    monkeypatch.setenv("OCR_WORKERS", "3")
    monkeypatch.setenv("OCR_DPI", "20")  # imágenes chicas: la prueba no mide calidad
    doc = pdf_loader.load_pdf(pdf)
    assert [p.page_number for p in doc.pages] == [1, 2, 3, 4, 5, 6]
    assert all(p.source == "ocr" for p in doc.pages)
    assert peak > 1


def test_parallel_map_keeps_order_and_context() -> None:
    var: contextvars.ContextVar[str] = contextvars.ContextVar("expediente", default="")
    var.set("EXP-1")

    def work(n: int) -> tuple[int, str]:
        time.sleep(0.01 * (5 - n))
        return n, var.get()

    assert _parallel_map(work, [1, 2, 3, 4], workers=3) == [(n, "EXP-1") for n in (1, 2, 3, 4)]


def test_parallel_map_sequential_when_one_worker() -> None:
    assert _parallel_map(lambda n: n * 2, [1, 2, 3], workers=1) == [2, 4, 6]
