"""Qué buscar en cada tipo de documento. Sale de la guía oficial de cada tipo.

`description` va en el prompt del LLM. `labels` son los encabezados que usa la ruta
heurística (sin LLM), del más específico al más genérico, ya normalizados
(minúsculas, sin acentos, abreviaturas expandidas: "No." → "numero").
"""

from dataclasses import dataclass, field

from tiendas3b.models.schemas import DocumentType


@dataclass(frozen=True)
class FieldSpec:
    description: str
    labels: tuple[str, ...]
    extra_labels: tuple[str, ...] = field(default=())  # se agregan al valor si aparecen
    critical: bool = False  # si falta, el supervisor reintenta la extracción


_FECHA = FieldSpec(
    description="Fecha de emisión del documento y, si la indica, fecha o plazo de vigencia.",
    labels=(
        "fecha de emision",
        "fecha de expedicion",
        "fecha de pago",
        "fecha de alta",
        "expedido el",
        "fecha",
    ),
    extra_labels=("vigencia", "vigente hasta", "fecha de vencimiento"),
)
_AUTORIDAD = FieldSpec(
    description="Autoridad u oficina que emite el documento.",
    labels=(
        "autoridad emisora",
        "emitido por",
        "expide",
        "dependencia",
        "tesoreria municipal",
        "direccion de desarrollo urbano",
        "h ayuntamiento",
    ),
)

FIELD_SPECS: dict[DocumentType, dict[str, FieldSpec]] = {
    DocumentType.ESCRITURAS: {
        "propietario": FieldSpec(
            "Nombre del propietario, titular, comprador o adquirente del inmueble.",
            (
                "propietario",
                "titular",
                "adquirente",
                "comprador",
                "la parte compradora",
                "a favor de",
                "adquiere",
                "adjudicatario",
                "nombre",
            ),
            critical=True,
        ),
        "direccion": FieldSpec(
            "Dirección o ubicación del inmueble (calle, número, colonia, municipio, estado).",
            (
                "domicilio del inmueble",
                "ubicacion del inmueble",
                "inmueble ubicado en",
                "predio ubicado en",
                "finca marcada",
                "domicilio",
                "ubicacion",
                "calle y numero",
                "sito en",
            ),
            critical=True,
        ),
        "superficie_terreno": FieldSpec(
            "Superficie del terreno, con unidades (por ejemplo, '250.00 m2' o 'metros cuadrados').",
            (
                "superficie del terreno",
                "superficie de terreno",
                "superficie total",
                "superficie de",
                "superficie",
                "sup terreno",
                "area de terreno",
                "area total",
            ),
            critical=True,
        ),
        "datos_inmueble": FieldSpec(
            "Datos que describen el inmueble: lote, manzana, medidas o colindancias.",
            (
                "descripcion del inmueble",
                "medidas y colindancias",
                "colindancias",
                "lote",
                "manzana",
            ),
        ),
        "referencia_cruzada": FieldSpec(
            "Dato que lo liga a otros documentos: folio real, clave catastral o escritura.",
            (
                "clave catastral",
                "cuenta predial",
                "folio real",
                "folio",
                "numero de escritura",
                "escritura numero",
                "instrumento numero",
            ),
        ),
    },
    DocumentType.PREDIAL: {
        "propietario": FieldSpec(
            "Nombre del propietario, contribuyente o sujeto pasivo del predial.",
            (
                "propietario / poseedor",
                "propietario poseedor",
                "nombre del contribuyente",
                "c contribuyente",
                "contribuyente",
                "nombre del receptor",
                "nombre o razon social",
                "razon social",
                "registrado a nombre de",
                "a nombre de",
                "como propietario de",
                "propietario",
                "titular",
                "usuario",
                "nombre",
            ),
            critical=True,
        ),
        "direccion": FieldSpec(
            "Dirección o ubicación del predio registrado ante tesorería o catastro.",
            (
                "direccion del predio",
                "ubicacion del predio",
                "domicilio del predio",
                "ubicacion del inmueble",
                "domicilio del receptor",
                "domicilio fiscal",
                "ubicado en",
                "domicilio",
                "ubicacion",
                "direccion",
                "calle y numero",
            ),
            critical=True,
        ),
        "cuenta_predial": FieldSpec(
            "Cuenta predial, clave catastral o número de predio.",
            (
                "clave catastral",
                "cve catastral",
                "clave catastral estandarizada",
                "cuenta predial",
                "cta predial",
                "clave predial",
                "numero de cuenta predial",
                "numero de cuenta",
                "no de cuenta",
                "no cuenta",
                "predio",
                "clave",
                "cuenta",
            ),
            critical=True,
        ),
        "superficie_registrada": FieldSpec(
            "Superficie de terreno registrada, con unidades métricas.",
            (
                "superficie terreno propio",
                "superficie de terreno",
                "superficie del terreno",
                "superficie terreno",
                "sup terreno propio",
                "sup terreno",
                "sup terr",
                "sup de terreno",
                "terreno m2",
                "superficie total",
                "superficie",
                "area",
            ),
            critical=True,
        ),
        "referencia_cruzada": FieldSpec(
            "Dato que lo liga a otros documentos: folio real, escritura o antecedente.",
            ("folio real", "numero de escritura", "escritura", "contrato de compraventa", "folio"),
        ),
    },
    DocumentType.ALINEAMIENTO: {
        "direccion_oficial": FieldSpec(
            "Dirección oficial del inmueble según la constancia de alineamiento.",
            (
                "direccion oficial",
                "domicilio oficial",
                "con ubicacion en",
                "con ubicacion",
                "ubicacion en",
                "ubicado en",
                "domicilio del predio",
                "domicilio",
                "ubicacion",
                "calle y numero",
                "calle",
            ),
            critical=True,
        ),
        "numero_oficial": FieldSpec(
            "Número oficial asignado al inmueble.",
            (
                "numero oficial asignado",
                "numero oficial",
                "no oficial asignado",
                "no oficial",
                "se asigna el numero oficial",
                "le corresponde el numero oficial",
            ),
            critical=True,
        ),
        "identificacion_predio": FieldSpec(
            "Identificación del predio: clave catastral, cuenta predial o lote.",
            (
                "clave catastral",
                "cve catastral",
                "clave predial",
                "cuenta predial",
                "identificacion del predio",
                "lote",
                "manzana",
            ),
        ),
        "alineamiento": FieldSpec(
            "Alineamiento o restricción determinada por la autoridad.",
            ("alineamiento oficial", "alineamiento", "restriccion de construccion", "restriccion"),
        ),
        "fecha_emision_vigencia": _FECHA,
        "autoridad_emisora": _AUTORIDAD,
    },
    DocumentType.USO_DE_SUELO: {
        "direccion": FieldSpec(
            "Dirección o identificación del inmueble en la licencia o constancia de uso de suelo.",
            (
                "domicilio del predio",
                "ubicacion del predio",
                "con ubicacion en",
                "con ubicacion",
                "ubicado en",
                "domicilio",
                "ubicacion",
                "direccion",
                "calle y numero",
            ),
            critical=True,
        ),
        "uso_autorizado": FieldSpec(
            "Uso de suelo autorizado o permitido.",
            (
                "uso de suelo autorizado",
                "uso autorizado",
                "uso permitido",
                "uso de suelo",
                "zonificacion",
                "clasificacion",
                "uso del predio",
                "giro",
            ),
            critical=True,
        ),
        "compatibilidad_comercial": FieldSpec(
            "Si el uso es compatible con comercio o servicios, tal como lo dice el documento.",
            ("compatibilidad comercial", "compatibilidad", "compatible", "dictamen"),
        ),
        "restricciones": FieldSpec(
            "Restricciones o condicionantes que impone la autoridad.",
            ("restricciones", "condicionantes", "condiciones", "observaciones"),
        ),
        "superficie_aplicable": FieldSpec(
            "Superficie a la que aplica el uso de suelo, con unidades.",
            ("superficie aplicable", "superficie del predio", "superficie total", "superficie"),
        ),
        "fecha_emision_vigencia": _FECHA,
        "autoridad_emisora": _AUTORIDAD,
    },
}
