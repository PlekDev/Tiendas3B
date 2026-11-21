"""Capa LLM sobre LangChain, adaptada del evaluador de TrustNode.

Mismo patrón que TrustNode: prompt que exige JSON estricto, temperatura 0,
validación con Pydantic, un reintento y, si falla, devolver None para que el
agente use su ruta heurística. Así el sistema nunca se cae por el LLM.
"""
import time
import json
import logging
import os
import re
import urllib.request
from typing import TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError

from tiendas3b.config import Settings, get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

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


def invoke_json(model: BaseChatModel, system: str, user: str, schema: type[T]) -> T | None:
    """Pide al modelo un JSON que cumpla `schema`. Un reintento; None si no lo logra."""
    messages: list[BaseMessage] = [SystemMessage(content=system), HumanMessage(content=user)]
    for attempt in (1, 2):
        try:
            t0 = time.perf_counter()
            response = model.invoke(messages)
            meta = response.response_metadata
            logger.info(
                "LLM intento %d: %.1fs entrada=%s salida=%s fin=%s",
                attempt, time.perf_counter() - t0,
                meta.get("prompt_eval_count"), meta.get("eval_count"), meta.get("done_reason"),
            )
            return schema.model_validate(_parse_json_object(str(response.content)))
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("LLM intento %d: respuesta inválida (%s).", attempt, type(exc).__name__)
            messages = [SystemMessage(content=system), HumanMessage(content=user + _RETRY_SUFFIX)]
        except Exception as exc:  # noqa: BLE001 - red, timeout o modelo no descargado
            logger.warning("LLM intento %d: error al invocar (%s).", attempt, exc)
    return None
