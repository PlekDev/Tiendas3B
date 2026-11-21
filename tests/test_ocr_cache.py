"""Caché de OCR: cada archivo se lee una vez y los metadatos de macOS se ignoran."""

from pathlib import Path

import pytest

from tiendas3b.demo import write_demo_pdfs
from tiendas3b.ingestion import pdf_loader
from tiendas3b.ingestion.pdf_loader import is_document_file, load_document, load_expediente_dir


@pytest.fixture
def cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "cache"
    monkeypatch.setenv("OCR_CACHE_DIR", str(path))
    monkeypatch.delenv("OCR_CACHE", raising=False)
    return path


def _pdf(tmp_path: Path) -> Path:
    folder = next(f for f in write_demo_pdfs(tmp_path / "demo") if f.name == "DEMO-CUMPLE")
    return folder / "predial.pdf"


def test_second_read_comes_from_cache(
    tmp_path: Path, cache_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf = _pdf(tmp_path)
    first = load_document(pdf)
    assert len(list(cache_dir.glob("*.json"))) == 1

    def boom(_: Path) -> None:
        raise AssertionError("no debió volver a leer el PDF")

    monkeypatch.setattr(pdf_loader, "load_pdf", boom)
    second = load_document(pdf)
    assert second.pages == first.pages
    assert second.filename == "predial.pdf"


def test_cache_follows_file_content_not_name(tmp_path: Path, cache_dir: Path) -> None:
    pdf = _pdf(tmp_path)
    copy = tmp_path / "otro_nombre.pdf"
    copy.write_bytes(pdf.read_bytes())
    load_document(pdf)
    doc = load_document(copy)
    assert len(list(cache_dir.glob("*.json"))) == 1
    assert doc.filename == "otro_nombre.pdf"


def test_cache_can_be_disabled(
    tmp_path: Path, cache_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    load_document(_pdf(tmp_path), use_cache=False)
    monkeypatch.setenv("OCR_CACHE", "0")
    load_document(_pdf(tmp_path))
    assert not cache_dir.exists()


def test_corrupt_cache_is_regenerated(tmp_path: Path, cache_dir: Path) -> None:
    pdf = _pdf(tmp_path)
    load_document(pdf)
    [entry] = cache_dir.glob("*.json")
    entry.write_text("{roto", encoding="utf-8")
    assert load_document(pdf).pages
    assert entry.read_text(encoding="utf-8").startswith("{")


def test_macos_metadata_and_hidden_files_are_skipped(tmp_path: Path, cache_dir: Path) -> None:
    folder = tmp_path / "exp"
    (folder / "__MACOSX").mkdir(parents=True)
    pdf = _pdf(tmp_path)
    (folder / "predial.pdf").write_bytes(pdf.read_bytes())
    (folder / "._predial.pdf").write_bytes(b"basura de macOS")
    (folder / "__MACOSX" / "._predial.pdf").write_bytes(b"basura de macOS")
    assert not is_document_file(folder / "._predial.pdf")
    assert not is_document_file(folder / "__MACOSX" / "._predial.pdf")
    assert [d.filename for d in load_expediente_dir(folder)] == ["predial.pdf"]
