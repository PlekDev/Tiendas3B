"""Capa LLM sobre LangChain, adaptada del evaluador de TrustNode.

Mismo patrón que TrustNode: prompt que exige JSON estricto, temperatura 0,
validación con Pydantic, un reintento y, si falla, devolver None para que el
agente use su ruta heurística. Así el sistema nunca se cae por el LLM.
"""

import itertools
import json
import logging
import os
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError

from tiendas3b.config import PROJECT_ROOT, Settings, get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_CALL_COUNTER = itertools.count(1)
_TRACE_LOCK = threading.Lock()

_RETRY_SUFFIX = (
    "\n\nTu respuesta anterior no fue JSON válido con el esquema pedido. "
    "Responde SOLO con un objeto JSON, sin texto antes ni después."
)


def get_chat_model(settings: Settings | None = None) -> BaseChatModel | None:
    """Crea el modelo de chat según LLM_PROVIDER. Devuelve None en modo heurístico."""
    settings = settings or get_settings()
    if not settings.llm_enabled:
        return None
    try:
        if settings.llm_provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                base_url=settings.ollama_base_url,
                format="json",
                num_ctx=settings.llm_num_ctx,  # Ollama usa 2048 por defecto: no cabe un documento
                client_kwargs={"timeout": settings.llm_timeout_s},
            )
        if settings.llm_provider == "openai":
            from langchain_openai import ChatOpenAI

            openai_model: BaseChatModel = ChatOpenAI(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                timeout=settings.llm_timeout_s,
                model_kwargs={"response_format": {"type": "json_object"}},
            )
            return openai_model
    except ImportError as exc:
        logger.warning("Proveedor %s sin paquete instalado (%s).", settings.llm_provider, exc)
        return None
    logger.warning("LLM_PROVIDER desconocido: %r. Se usa modo heurístico.", settings.llm_provider)
    return None


def llm_parallel() -> int:
    """Documentos que se mandan al LLM a la vez. Ollama atiende varios según OLLAMA_NUM_PARALLEL."""
    return max(1, int(os.getenv("LLM_PARALLEL") or "2"))


def describe_mode(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if not settings.llm_enabled:
        return "heuristico"
    return f"{settings.llm_provider}:{settings.llm_model}"


def is_reachable(settings: Settings | None = None) -> bool:
    """Revisa que el LLM responda. Solo verifica Ollama; otros proveedores se asumen vivos."""
    settings = settings or get_settings()
    if settings.llm_provider != "ollama":
        return settings.llm_enabled
    try:
        with urllib.request.urlopen(f"{settings.ollama_base_url}/api/tags", timeout=3) as resp:
            return bool(resp.status == 200)
    except OSError:
        return False


def _parse_json_object(text: str) -> object:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise json.JSONDecodeError("Sin objeto JSON", text, 0)
    return json.loads(text[start : end + 1])


def _emit_llm_trace(block: str) -> None:
    """Traza de llamadas LLM (deshabilitada por defecto).

    LLM_TRACE=0 (por defecto): no imprime ni escribe nada.
    LLM_TRACE=1 | true: imprime en terminal y guarda en logs/llm_calls.log.
    LLM_TRACE=file: solo guarda en logs/llm_calls.log sin imprimir en terminal.
    """
    trace_mode = os.getenv("LLM_TRACE", "0").strip().lower()
    if trace_mode in ("", "0", "false", "no") or os.getenv("PYTEST_CURRENT_TEST"):
        return
    with _TRACE_LOCK:
        if trace_mode in ("1", "true", "yes", "console", "all"):
            print(block, file=sys.stderr, flush=True)
        if trace_mode in ("1", "true", "yes", "file", "all"):
            log_dir = Path(os.getenv("LOG_DIR") or (PROJECT_ROOT / "logs"))
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                with (log_dir / "llm_calls.log").open("a", encoding="utf-8") as fh:
                    fh.write(block + "\n")
            except OSError:
                pass


def invoke_json(
    model: BaseChatModel,
    system: str,
    user: str,
    schema: type[T],
    call_name: str = "",
) -> T | None:
    """Pide al modelo un JSON que cumpla `schema`. Un reintento; None si no lo logra."""
    call_id = next(_CALL_COUNTER)
    label = call_name or schema.__name__
    messages: list[BaseMessage] = [SystemMessage(content=system), HumanMessage(content=user)]
    for attempt in (1, 2):
        prompt_sent = str(messages[-1].content)
        _emit_llm_trace(
            f"\n{'=' * 72}\n"
            f"[LLM #{call_id} · Intento {attempt}/2] ENVIANDO → {label}\n"
            f"{'-' * 72}\n"
            f"[SYSTEM]\n{system}\n"
            f"{'-' * 72}\n"
            f"[USER ({len(prompt_sent)} chars)]\n{prompt_sent}\n"
            f"{'=' * 72}"
        )
        t0 = time.perf_counter()
        try:
            response = model.invoke(messages)
            elapsed = time.perf_counter() - t0
            meta = response.response_metadata
            raw_content = str(response.content)
            _emit_llm_trace(
                f"\n{'=' * 72}\n"
                f"[LLM #{call_id} · Intento {attempt}/2] RECIBIDO ← {label} ({elapsed:.2f}s)\n"
                f"tokens_entrada={meta.get('prompt_eval_count')} · "
                f"tokens_salida={meta.get('eval_count')} · "
                f"motivo_fin={meta.get('done_reason')}\n"
                f"{'-' * 72}\n"
                f"{raw_content}\n"
                f"{'=' * 72}"
            )
            logger.info(
                "LLM #%d (%s) intento %d: %.1fs entrada=%s salida=%s fin=%s",
                call_id,
                label,
                attempt,
                elapsed,
                meta.get("prompt_eval_count"),
                meta.get("eval_count"),
                meta.get("done_reason"),
            )
            return schema.model_validate(_parse_json_object(raw_content))
        except (json.JSONDecodeError, ValidationError) as exc:
            _emit_llm_trace(
                f"[LLM #{call_id} · Intento {attempt}/2] ERROR PARSEO ← {label}: "
                f"{type(exc).__name__}: {exc}"
            )
            logger.warning("LLM intento %d: respuesta inválida (%s).", attempt, type(exc).__name__)
            messages = [SystemMessage(content=system), HumanMessage(content=user + _RETRY_SUFFIX)]
        except Exception as exc:  # noqa: BLE001 - red, timeout o modelo no descargado
            elapsed = time.perf_counter() - t0
            _emit_llm_trace(
                f"[LLM #{call_id} · Intento {attempt}/2] ERROR RED/MODELO ← {label} "
                f"({elapsed:.2f}s): {exc}"
            )
            logger.warning("LLM intento %d: error al invocar (%s).", attempt, exc)
            return None
    return None
