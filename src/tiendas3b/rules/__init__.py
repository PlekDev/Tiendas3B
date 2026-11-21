"""Criterios y reglas normativas por tipo documental."""

from tiendas3b.rules.criteria import (
    CROSS_CHECKS,
    REQUIRED_DOCUMENT_TYPES,
    REQUIRED_FIELDS_BY_TYPE,
    CrossCheck,
)
from tiendas3b.rules.engine import RULE_TYPES, Cartucho, Rule, evaluate_rules, load_cartuchos

__all__ = [
    "CROSS_CHECKS",
    "RULE_TYPES",
    "REQUIRED_DOCUMENT_TYPES",
    "REQUIRED_FIELDS_BY_TYPE",
    "Cartucho",
    "CrossCheck",
    "Rule",
    "evaluate_rules",
    "load_cartuchos",
]
