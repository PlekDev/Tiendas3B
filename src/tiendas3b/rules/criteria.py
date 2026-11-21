"""Definición base de tipos documentales mínimos y campos requeridos por el reto."""

from dataclasses import dataclass
from typing import Literal

from tiendas3b.models.schemas import DocumentType, Severity

REQUIRED_DOCUMENT_TYPES: tuple[DocumentType, ...] = (
    DocumentType.ESCRITURAS,
    DocumentType.PREDIAL,
    DocumentType.ALINEAMIENTO,
    DocumentType.USO_DE_SUELO,
)

DOCUMENT_LABELS: dict[DocumentType, str] = {
    DocumentType.ESCRITURAS: "Escrituras",
    DocumentType.PREDIAL: "Predial",
    DocumentType.ALINEAMIENTO: "Alineamiento y Número Oficial",
    DocumentType.USO_DE_SUELO: "Uso de Suelo",
    DocumentType.DESCONOCIDO: "Desconocido",
}

REQUIRED_FIELDS_BY_TYPE: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.ESCRITURAS: (
        "propietario",
        "direccion",
        "superficie_terreno",
        "datos_inmueble",
        "referencia_cruzada",
    ),
    DocumentType.PREDIAL: (
        "propietario",
        "direccion",
        "cuenta_predial",
        "superficie_registrada",
        "referencia_cruzada",
    ),
    DocumentType.ALINEAMIENTO: (
        "direccion_oficial",
        "numero_oficial",
        "identificacion_predio",
        "alineamiento",
        "fecha_emision_vigencia",
        "autoridad_emisora",
    ),
    DocumentType.USO_DE_SUELO: (
        "direccion",
        "uso_autorizado",
        "compatibilidad_comercial",
        "restricciones",
        "superficie_aplicable",
        "fecha_emision_vigencia",
        "autoridad_emisora",
    ),
}

Comparator = Literal["texto", "superficie", "identificador"]


@dataclass(frozen=True)
class CrossCheck:
    """Un cruce entre documentos: qué campo de cada tipo representa el mismo dato."""

    key: str
    label: str
    fields: dict[DocumentType, str]
    comparator: Comparator
    severity: Severity
    threshold: float  # texto: similitud mínima 0–100 · superficie: diferencia máx. en %
    # Escalamiento opcional a "critical" cuando la diferencia es grande:
    # texto: similitud por debajo de esto · superficie: diferencia en % por encima de esto.
    critical_threshold: float | None = None


# Los 5 cruces del reto. Severidad provisional: ajústala aquí, no en el código del agente.
CROSS_CHECKS: tuple[CrossCheck, ...] = (
    CrossCheck(
        key="propietario",
        label="Propietario o titular",
        fields={
            DocumentType.ESCRITURAS: "propietario",
            DocumentType.PREDIAL: "propietario",
        },
        comparator="texto",
        # Entre 50 y 85 % de similitud es "Requiere revisión": el predial suele quedarse con
        # el dueño anterior, abreviar razones sociales o traer errores de captura.
        # Debajo de 50 % es otra persona: "critical".
        severity="warning",
        threshold=85.0,
        critical_threshold=50.0,
    ),
    CrossCheck(
        key="direccion",
        label="Dirección del inmueble",
        fields={
            DocumentType.ESCRITURAS: "direccion",
            DocumentType.PREDIAL: "direccion",
            DocumentType.ALINEAMIENTO: "direccion_oficial",
            DocumentType.USO_DE_SUELO: "direccion",
        },
        comparator="texto",
        severity="warning",
        threshold=80.0,
    ),
    CrossCheck(
        key="superficie",
        label="Superficie del terreno",
        fields={
            DocumentType.ESCRITURAS: "superficie_terreno",
            DocumentType.PREDIAL: "superficie_registrada",
            DocumentType.USO_DE_SUELO: "superficie_aplicable",
        },
        comparator="superficie",
        severity="warning",
        threshold=5.0,
    ),
    CrossCheck(
        key="identificacion_predio",
        label="Clave catastral o cuenta predial",
        fields={
            DocumentType.PREDIAL: "cuenta_predial",
            DocumentType.ALINEAMIENTO: "identificacion_predio",
        },
        comparator="identificador",
        severity="warning",
        threshold=0.0,
    ),
    CrossCheck(
        key="numero_oficial",
        label="Número oficial",
        fields={DocumentType.ALINEAMIENTO: "numero_oficial"},
        comparator="identificador",
        severity="warning",
        threshold=0.0,
    ),
)
