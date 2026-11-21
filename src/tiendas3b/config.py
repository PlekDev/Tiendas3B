"""Configuración leída de variables de entorno (.env). Ver .env.example."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Parámetros de ejecución. Todo tiene un valor por defecto que corre sin LLM."""

    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_timeout_s: float
    llm_num_ctx: int
    ollama_base_url: str
    rules_dir: Path
    ocr_lang: str
    min_field_confidence: float
    max_workers: int = 2
    job_ttl_s: int = 3600
    api_key: str = ""
    cors_origins: tuple[str, ...] = ("*",)

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider not in ("", "none", "heuristico")


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "none").strip().lower(),
        llm_model=os.getenv("LLM_MODEL", "llama3.1:8b"),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
        llm_timeout_s=float(os.getenv("LLM_TIMEOUT_S", "120")),
        llm_num_ctx=int(os.getenv("LLM_NUM_CTX", "8192")),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        rules_dir=_path(os.getenv("RULES_DIR", "data/rules")),
        ocr_lang=os.getenv("OCR_LANG", "spa"),
        min_field_confidence=float(os.getenv("MIN_FIELD_CONFIDENCE", "0.6")),
        max_workers=max(1, int(os.getenv("MAX_WORKERS", "2"))),
        job_ttl_s=max(60, int(os.getenv("JOB_TTL_S", "3600"))),
        api_key=os.getenv("API_KEY", "").strip(),
        cors_origins=tuple(
            o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
        )
        or ("*",),
    )
