"""Expedientes de demostración con datos 100 % FICTICIOS.

Sirven para trabajar sin los documentos de 3B: pruebas, la interfaz, el endpoint
/api/v1/ejemplo y la evaluación. Nunca copies aquí datos reales.
"""

from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from tiendas3b.ingestion.pdf_loader import LoadedDocument, load_text_document
from tiendas3b.models.schemas import Recommendation


@dataclass(frozen=True)
class DemoCase:
    expediente_id: str
    description: str
    expected: Recommendation
    documents: dict[str, list[str]] = field(default_factory=dict)


_DIR_OK = "Av. Reforma Ficticia No. 1520, Col. Centro, San Andrés Cholula, Puebla"


def _escritura(owner: str, address: str, area: str) -> list[str]:
    return [
        "ESCRITURA PÚBLICA NÚMERO 45,821\n"
        "NOTARÍA PÚBLICA NÚMERO 12 DE PUEBLA, PUE.\n"
        "CONTRATO DE COMPRAVENTA\n"
        "Vendedor: JUAN EJEMPLO FICTICIO\n"
        f"Comprador: {owner}\n",
        f"Domicilio del inmueble: {address}\n"
        f"Superficie del terreno: {area}\n"
        "Descripción del inmueble: Lote 7, Manzana 3, con medidas y colindancias según plano.\n"
        "Clave catastral: 114-002-007-000\n"
        "Folio real: FR-998877\n"
        "Inscrita en el Registro Público de la Propiedad.",
    ]


def _predial(owner: str, address: str, area: str) -> list[str]:
    return [
        "TESORERÍA MUNICIPAL DE SAN ANDRÉS CHOLULA\n"
        "RECIBO DE PAGO DEL IMPUESTO PREDIAL 2026\n"
        "Cuenta predial: 114-002-007-000\n"
        f"Nombre del contribuyente: {owner}\n"
        f"Ubicación del predio: {address}\n"
        f"Superficie de terreno: {area}\n"
        "Superficie construida: 0.00 m2\n"
        "Folio real: FR-998877\n"
        "Estado del pago: PAGADO"
    ]


def _alineamiento(address: str, number: str) -> list[str]:
    return [
        "H. AYUNTAMIENTO DE SAN ANDRÉS CHOLULA\n"
        "DIRECCIÓN DE DESARROLLO URBANO\n"
        "CONSTANCIA DE ALINEAMIENTO Y NÚMERO OFICIAL\n"
        "Folio: DU-ALI-2026-0451\n"
        f"Dirección oficial: {address}\n"
        f"Número oficial asignado: {number}\n"
        "Clave catastral: 114-002-007-000\n"
        "Alineamiento: 5.00 m al paramento, sin afectación vial\n"
        "Fecha de emisión: 10 de marzo de 2026\n"
        "Vigencia: 10 de marzo de 2027\n"
        "Autoridad emisora: Dirección de Desarrollo Urbano, San Andrés Cholula"
    ]


def _uso_suelo(address: str, use: str, compat: str, restrictions: str, area: str) -> list[str]:
    return [
        "H. AYUNTAMIENTO DE SAN ANDRÉS CHOLULA\n"
        "CONSTANCIA DE USO DE SUELO\n"
        f"Domicilio del predio: {address}\n"
        f"Uso de suelo autorizado: {use}\n"
        f"Compatibilidad: {compat}\n"
        f"Restricciones: {restrictions}\n"
        f"Superficie aplicable: {area}\n"
        "Fecha de expedición: 2 de abril de 2026\n"
        "Autoridad emisora: Dirección de Desarrollo Urbano"
    ]


_OWNER = "INMOBILIARIA DEMO DEL CENTRO, S.A. DE C.V."

DEMO_CASES: dict[str, DemoCase] = {
    "cumple": DemoCase(
        expediente_id="DEMO-CUMPLE",
        description="Expediente completo y congruente.",
        expected=Recommendation.CUMPLE,
        documents={
            "escritura.pdf": _escritura(_OWNER, _DIR_OK, "850.00 m2"),
            "predial.pdf": _predial(
                "INMOBILIARIA DEMO DEL CENTRO SA DE CV",
                "Avenida Reforma Ficticia 1520, Colonia Centro, San Andrés Cholula",
                "850.00 m2",
            ),
            "alineamiento.pdf": _alineamiento("Av. Reforma Ficticia No. 1520, Col. Centro", "1520"),
            "uso_de_suelo.pdf": _uso_suelo(
                _DIR_OK,
                "Comercial y de servicios (CS)",
                "Compatible con tienda de autoservicio",
                "Ninguna",
                "850.00 m2",
            ),
        },
    ),
    "revision": DemoCase(
        expediente_id="DEMO-REVISION",
        description="La superficie de la escritura no cuadra con el predial (12 %).",
        expected=Recommendation.REQUIERE_REVISION,
        documents={
            "escritura.pdf": _escritura(_OWNER, _DIR_OK, "960.00 m2"),
            "predial.pdf": _predial(_OWNER, _DIR_OK, "850.00 m2"),
            "alineamiento.pdf": _alineamiento(_DIR_OK, "1520"),
            "uso_de_suelo.pdf": _uso_suelo(
                _DIR_OK,
                "Comercial y de servicios (CS)",
                "Compatible con tienda de autoservicio",
                "Horario de carga y descarga de 22:00 a 06:00",
                "850.00 m2",
            ),
        },
    ),
    "no_cumple": DemoCase(
        expediente_id="DEMO-NO-CUMPLE",
        description="El propietario no coincide y el uso de suelo es habitacional.",
        expected=Recommendation.NO_CUMPLE,
        documents={
            "escritura.pdf": _escritura(_OWNER, _DIR_OK, "850.00 m2"),
            "predial.pdf": _predial("MARÍA EJEMPLO DISTINTA", _DIR_OK, "850.00 m2"),
            "alineamiento.pdf": _alineamiento(_DIR_OK, "1520"),
            "uso_de_suelo.pdf": _uso_suelo(
                _DIR_OK,
                "Habitacional unifamiliar (H2)",
                "No compatible con comercio al por menor",
                "Ninguna",
                "850.00 m2",
            ),
        },
    ),
    "incompleto": DemoCase(
        expediente_id="DEMO-INCOMPLETO",
        description="Faltan alineamiento y uso de suelo; trae un anexo sin clasificar.",
        expected=Recommendation.REQUIERE_REVISION,
        documents={
            "escritura.pdf": _escritura(_OWNER, _DIR_OK, "850.00 m2"),
            "predial.pdf": _predial(_OWNER, _DIR_OK, "850.00 m2"),
            "anexo.pdf": ["Fotografías del inmueble tomadas durante la visita.\nSin más datos."],
        },
    ),
}


def demo_documents(case: str) -> list[LoadedDocument]:
    return [load_text_document(name, pages) for name, pages in DEMO_CASES[case].documents.items()]


def write_demo_pdfs(out_dir: Path) -> list[Path]:
    """Escribe cada caso como carpeta de PDFs (para probar la carga real y la interfaz)."""
    folders: list[Path] = []
    for case in DEMO_CASES.values():
        folder = out_dir / case.expediente_id
        folder.mkdir(parents=True, exist_ok=True)
        for name, pages in case.documents.items():
            write_demo_pdf(folder / name, pages)
        folders.append(folder)
    return folders


def write_demo_pdf(path: Path, pages: list[str]) -> Path:
    """Un documento ficticio como PDF con capa de texto (una página por elemento)."""
    with pymupdf.open() as pdf:  # type: ignore[no-untyped-call]
        for text in pages:
            page = pdf.new_page()
            box = pymupdf.Rect(56, 56, 556, 786)  # type: ignore[no-untyped-call]
            page.insert_textbox(box, text, fontsize=11)
        pdf.save(path)
    return path


def find_demo_case(expediente_id: str) -> DemoCase | None:
    """El caso de ejemplo con ese id (DEMO-CUMPLE, …), si existe."""
    return next((c for c in DEMO_CASES.values() if c.expediente_id == expediente_id), None)
