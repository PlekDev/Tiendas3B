"""Normalización y comparaciones usadas por extractores y cruces."""

from datetime import date

from tiendas3b.text import (
    find_dates,
    normalize,
    normalize_id,
    parse_number,
    quote_in_text,
    similarity,
)


def test_normalize_expands_abbreviations() -> None:
    assert (
        normalize("Av. Juárez No. 120, Col. Centro") == "avenida juarez numero 120 colonia centro"
    )
    assert normalize("S.A. de C.V.") == "sa de cv"


def test_normalize_keeps_negations() -> None:
    assert normalize("No compatible con comercio") == "no compatible con comercio"


def test_similarity_ignores_word_order() -> None:
    assert similarity("Pérez López Juan", "JUAN PEREZ LOPEZ") == 100


def test_normalize_id_and_numbers() -> None:
    assert normalize_id("114-002-007-000") == normalize_id("114 002 007 000")
    assert parse_number("1,250.50 m2") == 1250.5
    assert parse_number("sin dato") is None


def test_find_dates_in_spanish_formats() -> None:
    text = "Fecha de emisión: 10 de marzo de 2026; vigencia 10/03/2027"
    assert find_dates(text) == [date(2026, 3, 10), date(2027, 3, 10)]


def test_quote_in_text_detects_fabricated_quotes() -> None:
    page = "Superficie de terreno: 850.00 m2\nCuenta predial: 114-002"
    assert quote_in_text("SUPERFICIE DE TERRENO: 850.00 M2", page)
    assert not quote_in_text("Superficie de terreno: 999 m2 según avalúo", page)
