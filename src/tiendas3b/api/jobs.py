"""Cola de trabajos en memoria con ThreadPoolExecutor y caducidad (tarea A4).

Permite que múltiples auditores suban expedientes simultáneamente sin saturar
el servidor Ollama (limitado por MAX_WORKERS). Los archivos subidos viven en un
directorio temporal que se borra en cuanto el worker termina.
"""

from __future__ import annotations

import logging
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from tiendas3b.agents.orchestrator import analyze_expediente
from tiendas3b.config import get_settings
from tiendas3b.ingestion.pdf_loader import load_document
from tiendas3b.logs import log_context, record_dictamen
from tiendas3b.models.schemas import ExpedienteReport

logger = logging.getLogger("tiendas3b.api.jobs")

JobState = Literal["queued", "running", "completed", "failed"]


class JobStatusResponse(BaseModel):
    """Estado de un trabajo en la cola para el dashboard."""

    id: str = Field(..., description="Identificador único del trabajo.")
    job_id: str = Field(..., description="Alias de id para compatibilidad con el frontend.")
    expediente_id: str
    status: JobState
    position: int = Field(
        default=0,
        ge=0,
        description="Posición en la fila (1 = siguiente en pasar; 0 si ya corre o terminó).",
    )
    created_at: str
    result: ExpedienteReport | None = None
    error: str | None = None


@dataclass
class _JobRecord:
    job_id: str
    expediente_id: str
    usar_llm: bool
    tmp_dir: Path
    file_paths: list[Path]
    status: JobState = "queued"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))
    finished_monotonic: float | None = None
    result: ExpedienteReport | None = None
    error: str | None = None


class JobQueue:
    """Cola FIFO en memoria respaldada por ThreadPoolExecutor."""

    def __init__(self, max_workers: int | None = None, ttl_s: int | None = None) -> None:
        settings = get_settings()
        self._max_workers = max_workers or settings.max_workers
        self._ttl_s = ttl_s or settings.job_ttl_s
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="tiendas3b-worker",
        )
        self._lock = threading.Lock()
        self._jobs: dict[str, _JobRecord] = {}
        self._queue_order: list[str] = []

    def _purge_expired_locked(self) -> None:
        now = time.monotonic()
        expired = [
            jid
            for jid, rec in self._jobs.items()
            if rec.finished_monotonic is not None and (now - rec.finished_monotonic) > self._ttl_s
        ]
        for jid in expired:
            self._jobs.pop(jid, None)

    def _to_response_locked(self, record: _JobRecord) -> JobStatusResponse:
        position = 0
        if record.status == "queued" and record.job_id in self._queue_order:
            position = self._queue_order.index(record.job_id) + 1
        return JobStatusResponse(
            id=record.job_id,
            job_id=record.job_id,
            expediente_id=record.expediente_id,
            status=record.status,
            position=position,
            created_at=record.created_at,
            result=record.result,
            error=record.error,
        )

    def submit(
        self,
        expediente_id: str,
        tmp_dir: Path,
        file_paths: list[Path],
        usar_llm: bool = True,
    ) -> JobStatusResponse:
        """Registra un trabajo en la cola y lo envía al pool de workers."""
        job_id = uuid.uuid4().hex[:12]
        record = _JobRecord(
            job_id=job_id,
            expediente_id=expediente_id,
            usar_llm=usar_llm,
            tmp_dir=tmp_dir,
            file_paths=file_paths,
        )
        with self._lock:
            self._purge_expired_locked()
            self._jobs[job_id] = record
            self._queue_order.append(job_id)
            response = self._to_response_locked(record)

        self._executor.submit(self._run_job, job_id)
        return response

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            record.status = "running"
            if job_id in self._queue_order:
                self._queue_order.remove(job_id)

        try:
            with log_context(record.expediente_id) as request_id:
                documents = [load_document(path) for path in record.file_paths]
                logger.info(
                    "Trabajo %s: analizando %s (%d documentos)…",
                    job_id,
                    record.expediente_id,
                    len(documents),
                )
                report = analyze_expediente(
                    record.expediente_id,
                    documents,
                    None,
                    None,
                    record.usar_llm,
                )
                record_dictamen(report, "cola", request_id)
            with self._lock:
                record.result = report
                record.status = "completed"
                record.finished_monotonic = time.monotonic()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Trabajo %s falló al analizar %s", job_id, record.expediente_id)
            with self._lock:
                record.error = str(exc)
                record.status = "failed"
                record.finished_monotonic = time.monotonic()
        finally:
            shutil.rmtree(record.tmp_dir, ignore_errors=True)

    def get(self, job_id: str) -> JobStatusResponse | None:
        """Devuelve el estado actual del trabajo o None si no existe / caducó."""
        with self._lock:
            self._purge_expired_locked()
            record = self._jobs.get(job_id)
            if record is None:
                return None
            return self._to_response_locked(record)

    def list_jobs(self) -> list[JobStatusResponse]:
        """Lista todos los trabajos activos y recientes en orden inverso de creación."""
        with self._lock:
            self._purge_expired_locked()
            records = list(self._jobs.values())
            return [self._to_response_locked(rec) for rec in reversed(records)]
