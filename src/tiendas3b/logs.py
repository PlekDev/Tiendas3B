"""Logs estructurados y bitácora de auditoría (tareas V6 y V7).

- `setup_logging()`: consola legible + archivo JSON por línea (`logs/tiendas3b.jsonl`).
- `log_context(...)`: agrega `expediente_id` y `request_id` a todo lo que se registre dentro.
- `register_sensitive(...)`: valores del expediente (propietarios, direcciones) que nunca deben
  aparecer en un log; el filtro los reemplaza por [REDACTADO].
- `record_dictamen(...)`: una línea por dictamen en `logs/bitacora.jsonl`, sin datos personales,
  con la huella de los cartuchos de reglas para saber con qué reglas se decidió.

Regla de oro: en los logs van IDs, conteos, tiempos y veredictos; nunca texto de documentos.
"""

import hashlib
import json
import logging
import os
import uuid
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from tiendas3b import __version__
from tiendas3b.config import PROJECT_ROOT, get_settings
from tiendas3b.models.schemas import ExpedienteReport

LOGGER_NAME = "tiendas3b"
APP_LOG = "tiendas3b.jsonl"
AUDIT_LOG = "bitacora.jsonl"
MAX_MESSAGE_CHARS = 300
REDACTED = "[REDACTADO]"
EXTRA_FIELDS = ("event", "agent", "ms", "count", "status", "origin")

_expediente_id: ContextVar[str | None] = ContextVar("expediente_id", default=None)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_sensitive: ContextVar[frozenset[str]] = ContextVar("sensitive", default=frozenset())


def log_dir() -> Path:
    """Se lee en cada llamada para que las pruebas puedan cambiar LOG_DIR."""
    path = Path(os.getenv("LOG_DIR", "logs"))
    return path if path.is_absolute() else PROJECT_ROOT / path


@contextmanager
def log_context(expediente_id: str, request_id: str | None = None) -> Iterator[str]:
    """Todo lo que se registre dentro lleva estos IDs. Devuelve el request_id usado."""
    rid = request_id or uuid.uuid4().hex[:12]
    tokens = (
        _expediente_id.set(expediente_id),
        _request_id.set(rid),
        _sensitive.set(frozenset()),
    )
    try:
        yield rid
    finally:
        _expediente_id.reset(tokens[0])
        _request_id.reset(tokens[1])
        _sensitive.reset(tokens[2])


def register_sensitive(values: Iterable[str | None]) -> None:
    """Marca valores que no deben salir en los logs del expediente actual."""
    clean = {v.strip() for v in values if v and len(v.strip()) >= 4}
    _sensitive.set(_sensitive.get() | clean)


def redact(text: str) -> str:
    for value in sorted(_sensitive.get(), key=len, reverse=True):
        text = text.replace(value, REDACTED)
    if len(text) > MAX_MESSAGE_CHARS:
        text = text[: MAX_MESSAGE_CHARS - 1] + "…"
    return text


class ContextFilter(logging.Filter):
    """Agrega los IDs del contexto y redacta el mensaje antes de que llegue a cualquier salida."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.expediente_id = _expediente_id.get()
        record.request_id = _request_id.get()
        record.msg = redact(record.getMessage())
        record.args = None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "expediente_id": getattr(record, "expediente_id", None),
            "request_id": getattr(record, "request_id", None),
        }
        for key in EXTRA_FIELDS:
            if hasattr(record, key):
                data[key] = getattr(record, key)
        if record.exc_info:
            data["error"] = redact(self.formatException(record.exc_info).splitlines()[-1])
        return json.dumps(data, ensure_ascii=False)


_CONSOLE_FORMAT = "%(asctime)s %(levelname)-7s %(name)s [%(expediente_id)s] %(message)s"


def setup_logging(
    level: str | None = None, to_file: bool = True, console_level: str | None = None
) -> logging.Logger:
    """Configura el logger `tiendas3b`. Se puede llamar varias veces sin duplicar salidas.

    `console_level` permite una terminal más callada que el archivo (la CLI usa WARNING).
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel((level or os.getenv("LOG_LEVEL") or "INFO").upper())
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_CONSOLE_FORMAT, datefmt="%H:%M:%S"))
    console.addFilter(ContextFilter())
    if console_level:
        console.setLevel(console_level.upper())
    logger.addHandler(console)

    if to_file:
        log_dir().mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir() / APP_LOG, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(JsonFormatter())
        file_handler.addFilter(ContextFilter())
        logger.addHandler(file_handler)
    return logger


# --------------------------------------------------------------------------- bitácora


def rules_fingerprint(rules_dir: Path | None = None) -> str:
    """Huella de los cartuchos: si alguien cambia una regla, cambia la huella."""
    rules_dir = rules_dir or get_settings().rules_dir
    digest = hashlib.sha256()
    for path in sorted(rules_dir.glob("*.json")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def audit_entry(report: ExpedienteReport, origin: str, request_id: str | None) -> dict[str, Any]:
    """Lo que se guarda de cada dictamen. Sin nombres, direcciones ni citas."""
    severities = [i.severity for i in report.cross_validation_issues] + [
        r.severity for d in report.document_analyses for r in d.rule_evaluations if not r.passed
    ]
    return {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "expediente_id": report.expediente_id,
        "request_id": request_id,
        "origin": origin,
        "recommendation": report.recommendation.value,
        "confidence": report.confidence,
        "documents": len(report.documents_received),
        "missing_types": [t.value for t in report.missing_document_types],
        "critical": severities.count("critical"),
        "warning": severities.count("warning"),
        "processing_ms": report.processing_ms,
        "llm_mode": report.llm_mode,
        "rules": rules_fingerprint(),
        "version": __version__,
    }


def record_dictamen(
    report: ExpedienteReport, origin: str, request_id: str | None = None
) -> dict[str, Any]:
    entry = audit_entry(report, origin, request_id or _request_id.get())
    log_dir().mkdir(parents=True, exist_ok=True)
    with (log_dir() / AUDIT_LOG).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_bitacora(limit: int = 50) -> list[dict[str, Any]]:
    """Los dictámenes más recientes primero. Líneas dañadas se ignoran."""
    path = log_dir() / AUDIT_LOG
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(entries) >= limit:
            break
    return entries
