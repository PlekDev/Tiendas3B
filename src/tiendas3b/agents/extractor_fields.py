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
    exclude: tuple[str, ...] = field(default=())  # la heurística salta líneas con estas palabras


_CONSTRUCCION = ("construccion", "construida", "edificada")

_FECHA = FieldSpec(
    description="Fecha de emisión del documento y, si la indica, fecha o plazo de vigencia.",
    labels=("fecha de emision", "fecha de expedicion", "expedido el", "fecha"),
    extra_labels=("vigencia", "vigente hasta"),
)
_AUTORIDAD = FieldSpec(
    description="Autoridad u oficina que emite el documento.",
    labels=("autoridad emisora", "emitido por", "expide", "dependencia"),
)

FIELD_SPECS: dict[DocumentType, dict[str, FieldSpec]] = {
    DocumentType.ESCRITURAS: {
        "propietario": FieldSpec(
            "Adquirente ACTUAL del inmueble (quien compra o a quien se adjudica), no el "
            "vendedor. Si hay varios, sepáralos con ' ; '.",
            ("adquirente", "propietario", "titular", "comprador", "a favor de"),
            critical=True,
        ),
        "direccion": FieldSpec(
            "Dirección del INMUEBLE objeto de la escritura (calle, número, colonia, "
            "municipio), no el domicilio de las partes.",
            ("domicilio del inmueble", "ubicacion del inmueble"),
            critical=True,
        ),
        "superficie_terreno": FieldSpec(
            "Superficie del TERRENO con unidades (por ejemplo, '250.00 m2'), no de construcción.",
            ("superficie del terreno", "superficie de terreno", "superficie total", "superficie"),
            critical=True,
            exclude=_CONSTRUCCION,
        ),
        "datos_inmueble": FieldSpec(
            "Datos que describen el inmueble: lote, manzana, medidas o colindancias.",
            ("descripcion del inmueble", "medidas y colindancias", "colindancias", "lote"),
        ),
        "referencia_cruzada": FieldSpec(
            "Dato que lo liga a otros documentos: folio real, clave catastral o cuenta predial.",
            ("clave catastral", "cuenta predial", "folio real", "folio"),
        ),
    },
    DocumentType.PREDIAL: {
        "propietario": FieldSpec(
            "Nombre del propietario o contribuyente.",
            ("nombre del contribuyente", "contribuyente", "propietario", "titular"),
            critical=True,
        ),
        "direccion": FieldSpec(
            "Dirección o ubicación del predio.",
            ("ubicacion del predio", "domicilio del predio", "domicilio", "ubicacion", "ubicación"),
            critical=True,
        ),
        "cuenta_predial": FieldSpec(
            "Cuenta predial o clave catastral del predio.",
            ("cuenta predial", "clave predial", "clave catastral", "cuenta"),
            critical=True,
        ),
        "superficie_registrada": FieldSpec(
            "Superficie de TERRENO registrada, con unidades, no de construcción.",
            ("superficie de terreno", "superficie del terreno", "sup terreno", "superficie"),
            critical=True,
            exclude=_CONSTRUCCION,
        ),
        "referencia_cruzada": FieldSpec(
            "Dato que lo liga a otros documentos: folio real o número de escritura.",
            ("folio real", "numero de escritura", "escritura"),
        ),
        "fecha_emision_vigencia": FieldSpec(
            "Ejercicio fiscal (año) o fecha de pago o emisión del recibo de predial.",
            (
                "ejercicio fiscal",
                "periodo",
                "fecha de pago",
                "fecha de emision",
                "recibo de pago del impuesto predial",
                "impuesto predial",
                "ejercicio",
                "fecha",
            ),
        ),
    },
    DocumentType.ALINEAMIENTO: {
        "direccion_oficial": FieldSpec(
            "Dirección oficial del inmueble según la autoridad.",
            ("direccion oficial", "domicilio oficial", "domicilio", "ubicacion"),
            critical=True,
        ),
        "numero_oficial": FieldSpec(
            "Número oficial asignado al inmueble.",
            ("numero oficial asignado", "numero oficial"),
            critical=True,
        ),
        "identificacion_predio": FieldSpec(
            "Identificación del predio: clave catastral, cuenta predial o lote.",
            ("clave catastral", "cuenta predial", "identificacion del predio"),
        ),
        "alineamiento": FieldSpec(
            "Alineamiento o restricción determinada por la autoridad.",
            ("alineamiento", "restriccion"),
        ),
        "fecha_emision_vigencia": _FECHA,
        "autoridad_emisora": _AUTORIDAD,
    },
    DocumentType.USO_DE_SUELO: {
        "direccion": FieldSpec(
            "Dirección o identificación del inmueble.",
            ("domicilio del predio", "ubicacion del predio", "domicilio", "ubicacion"),
            critical=True,
        ),
        "uso_autorizado": FieldSpec(
            "Uso de suelo autorizado o permitido, tal como lo dice el documento.",
            ("uso de suelo autorizado", "uso autorizado", "uso permitido", "uso de suelo", "giro"),
            critical=True,
        ),
        "compatibilidad_comercial": FieldSpec(
            "Si el uso es compatible con comercio o servicios, tal como lo dice el documento.",
            ("compatibilidad", "compatible", "dictamen"),
        ),
        "restricciones": FieldSpec(
            "Restricciones o condicionantes que impone la autoridad.",
            ("restricciones", "condicionantes", "condiciones", "observaciones"),
        ),
        "superficie_aplicable": FieldSpec(
            "Superficie a la que aplica el uso de suelo, con unidades.",
            ("superficie aplicable", "superficie del predio", "superficie"),
        ),
        "fecha_emision_vigencia": _FECHA,
        "autoridad_emisora": _AUTORIDAD,
    },
}
