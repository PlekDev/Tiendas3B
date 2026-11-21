"""Cartuchos de reglas: que todos carguen y que cada tipo de regla haga lo que dice."""

from datetime import date
from pathlib import Path

from tiendas3b.models.schemas import DocumentAnalysis, DocumentType, ExtractedField
from tiendas3b.rules.criteria import REQUIRED_FIELDS_BY_TYPE
from tiendas3b.rules.engine import RULE_TYPES, Cartucho, Rule, evaluate_rules, load_cartuchos


def test_all_cartuchos_load_and_use_known_rule_types() -> None:
    cartuchos = load_cartuchos()
    assert set(cartuchos) == set(REQUIRED_FIELDS_BY_TYPE)
    for doc_type, cartucho in cartuchos.items():
        ids = [r.id for r in cartucho.reglas]
        assert len(ids) == len(set(ids)), f"IDs repetidos en {doc_type}"
        for rule in cartucho.reglas:
            assert rule.tipo in RULE_TYPES, rule.id
            assert rule.campo in REQUIRED_FIELDS_BY_TYPE[doc_type], rule.id


def test_invalid_cartucho_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "roto.json").write_text("{ esto no es json", encoding="utf-8")
    assert load_cartuchos(tmp_path) == {}


def _analysis(**values: str) -> DocumentAnalysis:
    return DocumentAnalysis(
        document_name="d.pdf",
        document_type=DocumentType.USO_DE_SUELO,
        extracted_fields=[
            ExtractedField(name=k, value=v, confidence=0.9) for k, v in values.items()
        ],
    )


def _run(rule: Rule, analysis: DocumentAnalysis, today: date = date(2026, 11, 21)) -> bool:
    cartucho = Cartucho(tipo_documento=DocumentType.USO_DE_SUELO, nombre="t", reglas=[rule])
    return evaluate_rules(analysis, cartucho, today)[0].passed


def test_campo_presente_flags_low_confidence() -> None:
    rule = Rule(id="R", tipo="campo_presente", campo="direccion", descripcion="d")
    doubtful = DocumentAnalysis(
        document_name="d.pdf",
        document_type=DocumentType.USO_DE_SUELO,
        extracted_fields=[ExtractedField(name="direccion", value="Calle 1", confidence=0.3)],
    )
    assert _run(rule, _analysis(direccion="Calle 1"))
    assert not _run(rule, doubtful)
    assert not _run(rule, _analysis())


def test_contiene_and_no_contiene() -> None:
    contiene = Rule(
        id="R",
        tipo="contiene_alguno",
        campo="uso_autorizado",
        descripcion="d",
        parametros={"valores": ["comercial", "servicios"]},
    )
    no_contiene = Rule(
        id="R",
        tipo="no_contiene",
        campo="compatibilidad_comercial",
        descripcion="d",
        parametros={"valores": ["no compatible"]},
    )
    assert _run(contiene, _analysis(uso_autorizado="Comercial y de Servicios"))
    assert not _run(contiene, _analysis(uso_autorizado="Habitacional"))
    assert _run(no_contiene, _analysis(compatibilidad_comercial="Compatible con comercio"))
    assert not _run(no_contiene, _analysis(compatibilidad_comercial="No compatible"))


def test_fecha_vigente() -> None:
    rule = Rule(
        id="R",
        tipo="fecha_vigente",
        campo="fecha_emision_vigencia",
        descripcion="d",
        parametros={"vigencia_dias": 365},
    )
    assert _run(rule, _analysis(fecha_emision_vigencia="1 de marzo de 2026"))
    assert not _run(rule, _analysis(fecha_emision_vigencia="1 de marzo de 2024"))
    expired = "10/01/2025; vigencia: 10/01/2026"
    assert not _run(rule, _analysis(fecha_emision_vigencia=expired))


def test_inactive_and_unknown_rules_are_skipped() -> None:
    cartucho = Cartucho(
        tipo_documento=DocumentType.USO_DE_SUELO,
        nombre="t",
        reglas=[
            Rule(id="A", tipo="campo_presente", campo="direccion", descripcion="d", activa=False),
            Rule(id="B", tipo="tipo_que_no_existe", campo="direccion", descripcion="d"),
        ],
    )
    assert evaluate_rules(_analysis(), cartucho) == []


def _anio(value: str, today: date, tolerancia: int = 0) -> bool:
    rule = Rule(
        id="R",
        tipo="fecha_anio_actual",
        campo="fecha_emision_vigencia",
        descripcion="d",
        parametros={"anios_tolerancia": tolerancia},
    )
    return _run(rule, _analysis(fecha_emision_vigencia=value), today)


def test_fecha_anio_actual_usa_el_anio_del_dia_de_analisis() -> None:
    hoy = date(2026, 11, 21)
    assert _anio("2 de abril de 2026", hoy)
    assert not _anio("2 de abril de 2025", hoy)
    # El mismo documento es "actual" si se analiza en 2025: el año no está fijo en el código.
    assert _anio("2 de abril de 2025", date(2025, 12, 1))


def test_fecha_anio_actual_tolerancia_y_vigencia() -> None:
    hoy = date(2026, 11, 21)
    assert _anio("15/03/2025", hoy, tolerancia=1)
    assert _anio("Expedida 10 de marzo de 2025, vigente hasta 10 de marzo de 2027", hoy)
    assert not _anio("Expedida 10 de marzo de 2024, vigente hasta 10 de marzo de 2025", hoy)


def test_fecha_anio_actual_falla_sin_fecha_o_en_el_futuro() -> None:
    hoy = date(2026, 11, 21)
    assert not _anio("sin fecha legible", hoy)
    assert not _anio("3 de enero de 2062", hoy)  # error típico de OCR


def test_fecha_anio_actual_sin_today_usa_la_fecha_real() -> None:
    rule = Rule(id="R", tipo="fecha_anio_actual", campo="fecha_emision_vigencia", descripcion="d")
    cartucho = Cartucho(tipo_documento=DocumentType.USO_DE_SUELO, nombre="t", reglas=[rule])
    actual = f"1 de enero de {date.today().year}"
    assert evaluate_rules(_analysis(fecha_emision_vigencia=actual), cartucho)[0].passed


def _predial(value: str) -> tuple[bool, str]:
    rule = Rule(
        id="PRE-07",
        tipo="anio_permitido",
        campo="fecha_emision_vigencia",
        descripcion="d",
        parametros={"anios": [2025, 2026], "mensaje": "Predial fuera de tiempo."},
    )
    cartucho = Cartucho(tipo_documento=DocumentType.PREDIAL, nombre="t", reglas=[rule])
    ev = evaluate_rules(_analysis(fecha_emision_vigencia=value), cartucho, date(2026, 11, 21))[0]
    return ev.passed, ev.details


def test_predial_2025_y_2026_pasan() -> None:
    assert _predial("2026")[0]
    assert _predial("Ejercicio fiscal 2025")[0]
    assert _predial("15/03/2026")[0]


def test_predial_de_otro_anio_dice_fuera_de_tiempo() -> None:
    passed, details = _predial("12 de enero de 2023")
    assert not passed
    assert details == "Predial fuera de tiempo."
    assert not _predial("2024")[0]


def test_predial_sin_fecha_legible_no_pasa() -> None:
    assert not _predial("sin fecha")[0]
