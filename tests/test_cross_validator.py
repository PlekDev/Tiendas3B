"""Cruces entre documentos con normalización, tolerancias y detección de inmueble distinto."""

from tiendas3b.agents.cross_validator import cross_validate, cross_validate_detailed
from tiendas3b.models.schemas import DocumentAnalysis, DocumentType, ExtractedField


def _doc(name: str, doc_type: DocumentType, **values: str) -> DocumentAnalysis:
    return DocumentAnalysis(
        document_name=name,
        document_type=doc_type,
        extracted_fields=[
            ExtractedField(name=k, value=v, confidence=0.9) for k, v in values.items()
        ],
    )


def test_equivalent_addresses_and_owners_match() -> None:
    issues = cross_validate(
        [
            _doc(
                "e.pdf",
                DocumentType.ESCRITURAS,
                propietario="Inmobiliaria Demo, S.A. de C.V.",
                direccion="Av. Juárez No. 120, Col. Centro, Puebla",
            ),
            _doc(
                "p.pdf",
                DocumentType.PREDIAL,
                propietario="INMOBILIARIA DEMO SA DE CV",
                direccion="AVENIDA JUAREZ 120 COLONIA CENTRO",
            ),
        ]
    )
    assert issues == []


def test_area_within_tolerance_passes_and_outside_fails() -> None:
    close = [
        _doc("e.pdf", DocumentType.ESCRITURAS, superficie_terreno="250.00 m2"),
        _doc("p.pdf", DocumentType.PREDIAL, superficie_registrada="252 m²"),
    ]
    far = [
        _doc("e.pdf", DocumentType.ESCRITURAS, superficie_terreno="280 m2"),
        _doc("p.pdf", DocumentType.PREDIAL, superficie_registrada="250 m2"),
    ]
    assert cross_validate(close) == []
    issues = cross_validate(far)
    assert [i.field_name for i in issues] == ["superficie"]
    assert issues[0].severity == "warning"


def test_numero_oficial_must_appear_in_other_addresses() -> None:
    issues = cross_validate(
        [
            _doc(
                "a.pdf",
                DocumentType.ALINEAMIENTO,
                numero_oficial="1520",
                direccion_oficial="Reforma 1520",
            ),
            _doc("p.pdf", DocumentType.PREDIAL, direccion="Reforma 1250"),
        ]
    )
    assert "numero_oficial" in {i.field_name for i in issues}


def test_different_property_is_critical() -> None:
    issues, summary = cross_validate_detailed(
        [
            _doc(
                "p.pdf",
                DocumentType.PREDIAL,
                direccion="Calle Uno 10, Col. Norte",
                cuenta_predial="111-222",
            ),
            _doc(
                "a.pdf",
                DocumentType.ALINEAMIENTO,
                direccion_oficial="Boulevard Sur 999",
                identificacion_predio="999-888",
            ),
        ]
    )
    assert any(i.field_name == "mismo_inmueble" and i.severity == "critical" for i in issues)
    assert len(summary) == 5


def _issue(issues: list, key: str):  # type: ignore[no-untyped-def]
    return next((i for i in issues if i.field_name == key), None)


def test_propietario_parecido_es_revision_y_distinto_es_critico() -> None:
    parecido = cross_validate(
        [
            _doc("e.pdf", DocumentType.ESCRITURAS, propietario="Juan Carlos Pérez López"),
            _doc("p.pdf", DocumentType.PREDIAL, propietario="Juana Peres Lopes"),
        ]
    )
    issue = _issue(parecido, "propietario")
    assert issue is not None and issue.severity == "warning"

    distinto = cross_validate(
        [
            _doc("e.pdf", DocumentType.ESCRITURAS, propietario="Inmobiliaria Demo SA de CV"),
            _doc("p.pdf", DocumentType.PREDIAL, propietario="María Ejemplo Distinta"),
        ]
    )
    issue = _issue(distinto, "propietario")
    assert issue is not None and issue.severity == "critical"


def test_superficie_usa_el_numero_junto_a_la_unidad_y_hectareas() -> None:
    issues = cross_validate(
        [
            _doc("e.pdf", DocumentType.ESCRITURAS, superficie_terreno="Lote 5, 1,200.00 m2"),
            _doc("p.pdf", DocumentType.PREDIAL, superficie_registrada="0.12 ha"),
        ]
    )
    assert _issue(issues, "superficie") is None


def test_clave_contenida_en_identificacion_coincide() -> None:
    issues = cross_validate(
        [
            _doc("p.pdf", DocumentType.PREDIAL, cuenta_predial="098-123-45-000"),
            _doc(
                "a.pdf",
                DocumentType.ALINEAMIENTO,
                identificacion_predio="Clave catastral 0981234500 0, lote 5",
            ),
        ]
    )
    assert _issue(issues, "identificacion_predio") is None


def test_clave_distinta_o_muy_corta_no_coincide() -> None:
    issues = cross_validate(
        [
            _doc("p.pdf", DocumentType.PREDIAL, cuenta_predial="098-123-45-000"),
            _doc("a.pdf", DocumentType.ALINEAMIENTO, identificacion_predio="77-555-10"),
        ]
    )
    assert _issue(issues, "identificacion_predio") is not None
    corta = cross_validate(
        [
            _doc("p.pdf", DocumentType.PREDIAL, cuenta_predial="5"),
            _doc("a.pdf", DocumentType.ALINEAMIENTO, identificacion_predio="Lote 15"),
        ]
    )
    assert _issue(corta, "identificacion_predio") is not None
