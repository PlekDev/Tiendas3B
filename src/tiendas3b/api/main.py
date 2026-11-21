"""API de la demo. Esqueleto tomado del main.py de TrustNode (CORS, errores uniformes,
trabajo pesado en threadpool). Correr con:  tiendas3b api   (o make api)

Los archivos subidos se procesan en una carpeta temporal y se borran al terminar:
ningún documento queda guardado en el servidor.
"""

import logging
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from tiendas3b import __version__
from tiendas3b.agents.orchestrator import analyze_expediente, graph_mermaid
from tiendas3b.demo import DEMO_CASES, demo_documents
from tiendas3b.ingestion.pdf_loader import SUPPORTED_SUFFIXES, load_document
from tiendas3b.llm import describe_mode, is_reachable
from tiendas3b.models.schemas import ExpedienteReport
from tiendas3b.rules.engine import load_cartuchos

logger = logging.getLogger("tiendas3b.api")

MAX_FILE_MB = 60
MAX_FILES = 40

app = FastAPI(
    title="Tiendas 3B · Análisis de expedientes",
    version=__version__,
    description="Sistema multiagente (LangChain + LangGraph) para dictaminar expedientes.",
)
app.add_middleware(  # Permisivo para la hackatón. Restringir orígenes en producción.
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
    path: str = ""


class StatusResponse(BaseModel):
    api: str
    version: str
    llm_mode: str
    llm_reachable: bool
    cartuchos: list[str]
    reglas_activas: int


class DemoCaseInfo(BaseModel):
    caso: str
    expediente_id: str
    descripcion: str
    esperado: str
    documentos: list[str]


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=str(exc.detail), path=request.url.path).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado en %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Error interno", detail=str(exc), path=request.url.path
        ).model_dump(),
    )


@app.get("/api/v1/status", response_model=StatusResponse, tags=["sistema"])
async def status_endpoint() -> StatusResponse:
    cartuchos = await run_in_threadpool(load_cartuchos)
    reachable = await run_in_threadpool(is_reachable)
    return StatusResponse(
        api="ok",
        version=__version__,
        llm_mode=describe_mode(),
        llm_reachable=reachable,
        cartuchos=sorted(t.value for t in cartuchos),
        reglas_activas=sum(1 for c in cartuchos.values() for r in c.reglas if r.activa),
    )


@app.get("/api/v1/casos", response_model=list[DemoCaseInfo], tags=["demo"])
async def casos_endpoint() -> list[DemoCaseInfo]:
    return [
        DemoCaseInfo(
            caso=key,
            expediente_id=case.expediente_id,
            descripcion=case.description,
            esperado=case.expected.value,
            documentos=list(case.documents),
        )
        for key, case in DEMO_CASES.items()
    ]


@app.get("/api/v1/ejemplo", response_model=ExpedienteReport, tags=["demo"])
async def ejemplo_endpoint(caso: Annotated[str, Query()] = "revision") -> ExpedienteReport:
    """Analiza un expediente ficticio. Sirve para la interfaz aunque no haya LLM ni PDFs."""
    if caso not in DEMO_CASES:
        raise HTTPException(status_code=404, detail=f"Caso desconocido: {caso}")
    case = DEMO_CASES[caso]
    return await run_in_threadpool(
        analyze_expediente, case.expediente_id, demo_documents(caso), None, None, False
    )


@app.get("/api/v1/grafo", tags=["sistema"])
async def grafo_endpoint() -> dict[str, str]:
    return {"mermaid": await run_in_threadpool(graph_mermaid)}


@app.post("/api/v1/analizar", response_model=ExpedienteReport, tags=["analisis"])
async def analizar_endpoint(
    files: Annotated[list[UploadFile], File(description="PDFs o imágenes del expediente.")],
    expediente_id: Annotated[str, Form()] = "EXP-SUBIDO",
    usar_llm: Annotated[bool, Form()] = True,
) -> ExpedienteReport:
    """Recibe los documentos de UN expediente y devuelve el dictamen completo."""
    if not files:
        raise HTTPException(status_code=400, detail="No se recibieron archivos.")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Máximo {MAX_FILES} archivos por expediente.")
    with tempfile.TemporaryDirectory(prefix="tiendas3b-") as tmp:
        paths: list[Path] = []
        for upload in files:
            name = Path(upload.filename or "documento.pdf").name
            if Path(name).suffix.lower() not in SUPPORTED_SUFFIXES:
                raise HTTPException(
                    status_code=415,
                    detail=f"{name}: tipo no soportado ({', '.join(SUPPORTED_SUFFIXES)}).",
                )
            payload = await upload.read()
            if len(payload) > MAX_FILE_MB * 1024 * 1024:
                raise HTTPException(status_code=413, detail=f"{name} excede {MAX_FILE_MB} MB.")
            path = Path(tmp) / name
            path.write_bytes(payload)
            paths.append(path)
        documents = [await run_in_threadpool(load_document, p) for p in paths]
        logger.info("Analizando %s (%d documentos)…", expediente_id, len(documents))
        return await run_in_threadpool(
            analyze_expediente, expediente_id, documents, None, None, usar_llm
        )
