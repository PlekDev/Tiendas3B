"""Definición base de tipos documentales mínimos y campos requeridos por el reto."""

from tiendas3b.models.schemas import DocumentType

REQUIRED_DOCUMENT_TYPES: tuple[DocumentType, ...] = (
    DocumentType.ESCRITURAS,
    DocumentType.PREDIAL,
    DocumentType.ALINEAMIENTO,
    DocumentType.USO_DE_SUELO,
)

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
