"""Motor de reglas por cartuchos JSON (idea de los standards/*.json de TrustNode).

Cada archivo en RULES_DIR describe las reglas de un tipo de documento. Agregar
una regla = agregar un objeto JSON; no hay que tocar este código mientras se use
uno de los tipos de regla de `RULE_TYPES`. Todas se calculan en Python.
"""

import json
import logging
import re
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from tiendas3b.config import get_settings
from tiendas3b.models.schemas import (
    DocumentAnalysis,
    DocumentType,
    ExtractedField,
    RuleEvaluation,
    Severity,
)
from tiendas3b.text import find_dates, normalize, parse_number

logger = logging.getLogger(__name__)


class Rule(BaseModel):
    id: str
    tipo: str = Field(description="Uno de RULE_TYPES.")
    campo: str
    descripcion: str
    severidad: Severity = "warning"
    activa: bool = True
    parametros: dict[str, Any] = Field(default_factory=dict)


class Cartucho(BaseModel):
    tipo_documento: DocumentType
    nombre: str
    reglas: list[Rule] = Field(default_factory=list)


def load_cartuchos(rules_dir: Path | None = None) -> dict[DocumentType, Cartucho]:
    """Lee todos los cartuchos. Un archivo inválido se reporta y se salta: nunca tumba el flujo."""
    rules_dir = rules_dir or get_settings().rules_dir
    cartuchos: dict[DocumentType, Cartucho] = {}
    for path in sorted(rules_dir.glob("*.json")):
        try:
            cartucho = Cartucho.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Cartucho inválido %s: %s", path.name, exc)
            continue
        cartuchos[cartucho.tipo_documento] = cartucho
    return cartuchos


Outcome = tuple[bool, str]
RuleCheck = Callable[[Rule, ExtractedField | None, date], Outcome]


def _has_value(field: ExtractedField | None) -> bool:
    return field is not None and bool((field.value or "").strip())


def _check_presente(rule: Rule, field: ExtractedField | None, today: date) -> Outcome:
    if not _has_value(field):
        return False, f"No se encontró '{rule.campo}' en el documento."
    assert field is not None
    min_conf = float(rule.parametros.get("confianza_minima", get_settings().min_field_confidence))
    if field.confidence < min_conf:
        return False, f"Dato en duda (confianza {field.confidence:.2f}): '{field.value}'."
    return True, f"Encontrado: '{field.value}'."


def _matches(rule: Rule, field: ExtractedField) -> tuple[list[str], list[str]]:
    """(términos que aparecen en el valor, todos los términos), en su forma original."""
    terms = [str(v) for v in rule.parametros.get("valores", [])]
    value = normalize(field.value or "")
    return [t for t in terms if normalize(t) and normalize(t) in value], terms


def _check_contiene_alguno(rule: Rule, field: ExtractedField | None, today: date) -> Outcome:
    if not _has_value(field):
        return False, f"No hay valor de '{rule.campo}' para revisar."
    assert field is not None
    hits, terms = _matches(rule, field)
    if hits:
        return True, f"'{field.value}' incluye: {', '.join(hits)}."
    return False, f"'{field.value}' no incluye ninguno de: {', '.join(terms)}."


def _check_no_contiene(rule: Rule, field: ExtractedField | None, today: date) -> Outcome:
    if not _has_value(field):
        return True, f"Sin valor de '{rule.campo}'; no hay términos prohibidos."
    assert field is not None
    hits, _ = _matches(rule, field)
    if hits:
        return False, f"'{field.value}' menciona: {', '.join(hits)}."
    return True, "No menciona términos que lo impidan."


def _check_alerta_si_presente(rule: Rule, field: ExtractedField | None, today: date) -> Outcome:
    """Para condicionantes: si el documento los menciona, se marca para que alguien los lea."""
    if not _has_value(field):
        return True, "No se reportan condicionantes."
    assert field is not None
    ignorar = [normalize(str(v)) for v in rule.parametros.get("ignorar", [])]
    value = normalize(field.value or "")
    if any(value == v or value.startswith(v) for v in ignorar if v):
        return True, f"'{field.value}'."
    return False, f"Condicionante a revisar: '{field.value}'."


def _check_fecha_vigente(rule: Rule, field: ExtractedField | None, today: date) -> Outcome:
    if not _has_value(field):
        return False, f"No se encontró fecha en '{rule.campo}'."
    assert field is not None
    dates = find_dates(field.value or "")
    if not dates:
        return False, f"No se pudo leer una fecha en '{field.value}'."
    if "vigen" in normalize(field.value or "") and len(dates) > 1:
        expires = max(dates)
    else:
        expires = min(dates) + timedelta(days=int(rule.parametros.get("vigencia_dias", 365)))
    if expires < today:
        return False, f"Vencido desde {expires.isoformat()}."
    return True, f"Vigente hasta {expires.isoformat()}."


def _check_fecha_anio_actual(rule: Rule, field: ExtractedField | None, today: date) -> Outcome:
    """El documento es del año en curso. El año sale de `today` (date.today() al correr).

    Pasa si la fecha más reciente cae en el año actual (o dentro de `anios_tolerancia`),
    o si el documento declara una vigencia que todavía no vence. Una fecha en el futuro
    se marca: casi siempre es un error de lectura (OCR) que alguien debe ver.
    """
    if not _has_value(field):
        return False, f"No se encontró fecha en '{rule.campo}'."
    assert field is not None
    dates = find_dates(field.value or "")
    if not dates:
        return False, f"No se pudo leer una fecha en '{field.value}'."
    tolerance = int(rule.parametros.get("anios_tolerancia", 0))
    issued, latest = min(dates), max(dates)
    if issued > today + timedelta(days=31):  # la emisión no puede ser futura; la vigencia sí
        return False, f"Fecha de emisión en el futuro ({issued.isoformat()}): revisar la lectura."
    if len(dates) > 1 and latest >= today:  # emisión + vencimiento que no ha pasado
        return True, f"Vigente hasta {latest.isoformat()} (año en curso: {today.year})."
    if latest.year >= today.year - tolerance:
        return True, f"Fecha {latest.isoformat()} corresponde al año en curso ({today.year})."
    return False, (
        f"La fecha más reciente es {latest.isoformat()}; no es del año en curso ({today.year})."
    )


def _check_anio_permitido(rule: Rule, field: ExtractedField | None, today: date) -> Outcome:
    """El documento es de alguno de los años permitidos (`parametros.anios`).

    Se usa el año más reciente que aparezca en el valor: sirve igual para "2026",
    "Ejercicio fiscal 2025" o "15/03/2026". Fuera de esos años: "Predial fuera de tiempo".
    """
    anios = {int(a) for a in rule.parametros.get("anios", [])}
    if not _has_value(field):
        return False, f"No se encontró la fecha en '{rule.campo}'."
    assert field is not None
    years = {d.year for d in find_dates(field.value or "")}
    years |= {int(y) for y in re.findall(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", field.value or "")}
    if not years:
        return False, f"No se pudo leer un año en '{field.value}'."
    if max(years) in anios:
        return True, f"Año {max(years)} dentro de lo permitido."
    return False, rule.parametros.get("mensaje", "Fuera de tiempo.")


def _check_numero_positivo(rule: Rule, field: ExtractedField | None, today: date) -> Outcome:
    number = parse_number(field.value or "") if field else None
    if number is None or number <= 0:
        return False, f"'{rule.campo}' no tiene un número válido."
    return True, f"Valor numérico: {number:g}."


RULE_TYPES: dict[str, RuleCheck] = {
    "campo_presente": _check_presente,
    "contiene_alguno": _check_contiene_alguno,
    "no_contiene": _check_no_contiene,
    "alerta_si_presente": _check_alerta_si_presente,
    "fecha_vigente": _check_fecha_vigente,
    "fecha_anio_actual": _check_fecha_anio_actual,
    "anio_permitido": _check_anio_permitido,
    "numero_positivo": _check_numero_positivo,
}


def evaluate_rules(
    analysis: DocumentAnalysis,
    cartucho: Cartucho,
    today: date | None = None,
) -> list[RuleEvaluation]:
    today = today or date.today()
    fields = {f.name: f for f in analysis.extracted_fields}
    evaluations: list[RuleEvaluation] = []
    for rule in cartucho.reglas:
        if not rule.activa:
            continue
        check = RULE_TYPES.get(rule.tipo)
        if check is None:
            logger.warning("Regla %s: tipo desconocido %r, se omite.", rule.id, rule.tipo)
            continue
        field = fields.get(rule.campo)
        passed, details = check(rule, field, today)
        evaluations.append(
            RuleEvaluation(
                rule_id=rule.id,
                description=rule.descripcion,
                passed=passed,
                details=details,
                evidence=[field.evidence] if field and field.evidence else [],
                severity=rule.severidad,
            )
        )
    return evaluations
