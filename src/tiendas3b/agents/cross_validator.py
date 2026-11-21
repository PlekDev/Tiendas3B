"""Agente de validación cruzada entre documentos del mismo expediente.

Los 5 cruces y sus umbrales viven en `rules/criteria.py` (CROSS_CHECKS). Aquí solo
se compara, siempre en Python: texto normalizado + similitud aproximada para
nombres y direcciones, tolerancia en % para superficies, igualdad exacta para claves.
"""

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from tiendas3b.models.schemas import (
    CrossValidationIssue,
    DocumentAnalysis,
    Evidence,
    ExtractedField,
    Severity,
)
from tiendas3b.rules.criteria import CROSS_CHECKS, CrossCheck
from tiendas3b.text import normalize, normalize_id, parse_number


@dataclass(frozen=True)
class _Entry:
    document: str
    field: ExtractedField

    @property
    def value(self) -> str:
        return (self.field.value or "").strip()


def _entries(check: CrossCheck, analyses: list[DocumentAnalysis]) -> list[_Entry]:
    entries: list[_Entry] = []
    for doc in analyses:
        field_name = check.fields.get(doc.document_type)
        if field_name is None:
            continue
        for field in doc.extracted_fields:
            if field.name == field_name and (field.value or "").strip():
                entries.append(_Entry(doc.document_name, field))
                break
    return entries


def _text_similarity(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    return float(max(fuzz.token_sort_ratio(na, nb), fuzz.token_set_ratio(na, nb)))


_AREA = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*"
    r"(m\s*2|m²|mts?\.?\s*2?|metros?\s+cuadrados?|ha\b|has\b|hectareas?|hectáreas?)",
    re.IGNORECASE,
)


def _area_m2(text: str) -> float | None:
    """Superficie en m². Prefiere el número junto a la unidad ('Lote 5, 250 m2' → 250)."""
    match = _AREA.search(text)
    if match is None:
        return parse_number(text)
    number = parse_number(match.group(1))
    if number is None:
        return None
    unit = match.group(2).lower()
    return number * 10_000 if unit.startswith("h") else number


def _same_id(a: str, b: str) -> bool:
    """Misma clave aunque una venga dentro de la otra ('Clave 098-123' vs '098123')."""
    if a == b:
        return True
    shorter, longer = sorted((a, b), key=len)
    return len(shorter) >= 6 and shorter in longer


def _escalate(check: CrossCheck, critical: bool) -> Severity:
    return "critical" if critical else check.severity


def _mismatch(check: CrossCheck, entries: list[_Entry]) -> tuple[str, Severity] | None:
    """Explicación y severidad si los valores no cuadran; None si coinciden."""
    if check.comparator == "texto":
        worst = min(
            (
                (_text_similarity(a.value, b.value), a, b)
                for i, a in enumerate(entries)
                for b in entries[i + 1 :]
            ),
            key=lambda t: t[0],
        )
        score, a, b = worst
        if score < check.threshold:
            critical = check.critical_threshold is not None and score < check.critical_threshold
            return (
                f"{check.label}: '{a.value}' ({a.document}) vs '{b.value}' ({b.document}), "
                f"similitud {score:.0f}%.",
                _escalate(check, critical),
            )
        return None
    if check.comparator == "superficie":
        numbers = [(_area_m2(e.value), e) for e in entries]
        valid = [(n, e) for n, e in numbers if n is not None and n > 0]
        if len(valid) < 2:
            return None
        (low, e_low), (high, e_high) = (
            min(valid, key=lambda t: t[0]),
            max(valid, key=lambda t: t[0]),
        )
        diff = (high - low) / high * 100
        if diff > check.threshold:
            critical = check.critical_threshold is not None and diff > check.critical_threshold
            return (
                f"{check.label}: {high:g} m² ({e_high.document}) vs {low:g} m² ({e_low.document}), "
                f"diferencia de {diff:.1f}% (tolerancia {check.threshold:g}%).",
                _escalate(check, critical),
            )
        return None
    ids = [normalize_id(e.value) for e in entries]
    if all(_same_id(a, b) for i, a in enumerate(ids) for b in ids[i + 1 :]):
        return None
    detail = ", ".join(f"'{e.value}' ({e.document})" for e in entries)
    return f"{check.label} distinta entre documentos: {detail}.", check.severity


def _numero_oficial_vs_direcciones(analyses: list[DocumentAnalysis]) -> CrossValidationIssue | None:
    """El número oficial del alineamiento debe aparecer en las direcciones de los demás."""
    numero_check = next(c for c in CROSS_CHECKS if c.key == "numero_oficial")
    direccion_check = next(c for c in CROSS_CHECKS if c.key == "direccion")
    numeros = _entries(numero_check, analyses)
    if not numeros:
        return None
    numero = numeros[0]
    digits = re.findall(r"\d+", numero.value)
    if not digits:
        return None
    target = digits[0]
    mismatched: list[_Entry] = []
    for entry in _entries(direccion_check, analyses):
        if entry.document == numero.document:
            continue
        address_numbers = re.findall(r"\d+", entry.value)
        if address_numbers and target not in address_numbers:
            mismatched.append(entry)
    if not mismatched:
        return None
    involved = [numero, *mismatched]
    return CrossValidationIssue(
        field_name="numero_oficial",
        description=(
            f"Número oficial {target} ({numero.document}) no aparece en: "
            + ", ".join(f"'{e.value}' ({e.document})" for e in mismatched)
            + "."
        ),
        severity=numero_check.severity,
        documents_involved=[e.document for e in involved],
        values_found={e.document: e.value for e in involved},
        evidence=[e.field.evidence for e in involved if e.field.evidence],
    )


def cross_validate_detailed(
    analyses: list[DocumentAnalysis],
) -> tuple[list[CrossValidationIssue], list[str]]:
    """Issues encontrados + una línea por cruce evaluado (para la traza y la demo)."""
    issues: list[CrossValidationIssue] = []
    summary: list[str] = []
    for check in CROSS_CHECKS:
        if check.key == "numero_oficial":
            issue = _numero_oficial_vs_direcciones(analyses)
            if issue:
                issues.append(issue)
            summary.append(f"{check.label}: {'discrepancia' if issue else 'sin discrepancias'}")
            continue
        entries = _entries(check, analyses)
        if len(entries) < 2:
            summary.append(f"{check.label}: no evaluable ({len(entries)} documento con el dato)")
            continue
        mismatch = _mismatch(check, entries)
        if mismatch is None:
            summary.append(f"{check.label}: coincide en {len(entries)} documentos")
            continue
        detail, severity = mismatch
        summary.append(f"{check.label}: discrepancia")
        issues.append(
            CrossValidationIssue(
                field_name=check.key,
                description=detail,
                severity=severity,
                documents_involved=[e.document for e in entries],
                values_found={e.document: e.value for e in entries},
                evidence=[e.field.evidence for e in entries if e.field.evidence],
            )
        )
    keys = {i.field_name for i in issues}
    if {"direccion", "identificacion_predio"} <= keys:
        related = [i for i in issues if i.field_name in ("direccion", "identificacion_predio")]
        documents = sorted({d for i in related for d in i.documents_involved})
        evidence: list[Evidence] = [ev for i in related for ev in i.evidence]
        issues.append(
            CrossValidationIssue(
                field_name="mismo_inmueble",
                description=(
                    "Dirección e identificación del predio no coinciden: los documentos "
                    "posiblemente corresponden a inmuebles diferentes."
                ),
                severity="critical",
                documents_involved=documents,
                evidence=evidence,
            )
        )
    return issues, summary


def cross_validate(analyses: list[DocumentAnalysis]) -> list[CrossValidationIssue]:
    """Contrasta valores clave entre documentos para detectar discrepancias."""
    return cross_validate_detailed(analyses)[0]
