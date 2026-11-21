"""Clasificador: el encabezado decide cuando el cuerpo menciona otros tipos de documento."""

from tiendas3b.agents.classifier import TITLE_CHARS, classify
from tiendas3b.demo import demo_documents
from tiendas3b.ingestion.pdf_loader import LoadedDocument, load_text_document
from tiendas3b.models.schemas import DocumentType

# Membrete y datos generales: en los documentos reales el cuerpo empieza después.
_MEMBRETE = (
    "H. AYUNTAMIENTO DEL MUNICIPIO DE EJEMPLO\nDIRECCIÓN GENERAL DE GOBIERNO\n"
    "Folio de control interno asignado por la oficina de atención ciudadana, "
    "con fecha y hora de recepción del trámite y sello de la ventanilla única. "
    "Se expide a solicitud de la parte interesada para los fines que convengan. "
)


def _doc(title: str, body: str) -> LoadedDocument:
    text = f"{title}\n{_MEMBRETE}\n{body}"
    assert text.find(body) >= TITLE_CHARS, "el cuerpo debe empezar después del encabezado"
    return load_text_document("documento.pdf", [text])


def test_header_breaks_ties_with_body_mentions() -> None:
    # Sin peso al encabezado gana Predial (6 menciones contra 3); con el título, Alineamiento.
    body = "Pago de derechos en tesorería, recibo de impuesto predial y cuenta predial."
    doc = _doc("CONSTANCIA DE ALINEAMIENTO Y NÚMERO OFICIAL", body)
    assert classify(doc).document_type == DocumentType.ALINEAMIENTO


def test_predial_receipt_citing_the_deed_stays_predial() -> None:
    body = "Escritura número 123 ante notario. " * 3
    doc = _doc("RECIBO OFICIAL DE PAGO DEL IMPUESTO PREDIAL", body)
    assert classify(doc).document_type == DocumentType.PREDIAL


def test_demo_documents_keep_their_type() -> None:
    expected = {
        "escritura.pdf": DocumentType.ESCRITURAS,
        "predial.pdf": DocumentType.PREDIAL,
        "alineamiento.pdf": DocumentType.ALINEAMIENTO,
        "uso_de_suelo.pdf": DocumentType.USO_DE_SUELO,
    }
    for doc in demo_documents("cumple"):
        assert classify(doc).document_type == expected[doc.filename]


def test_unknown_document() -> None:
    doc = load_text_document("anexo.pdf", ["Fotografías del inmueble."])
    assert classify(doc).document_type == DocumentType.DESCONOCIDO
