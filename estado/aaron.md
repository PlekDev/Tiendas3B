# Estado de Aaron

**Última actualización:** 2026-11-21 11:11

- **Listo:**
  - **A1:** `main` y `dev` sincronizadas con el bosquejo e integración de pruebas; `Makefile` compatible con Python 3.11/3.12/3; `pytest` configurado con `-m 'not real_data'` por defecto y `make check` en verde.
  - **A3:** Contrato de datos en `models/schemas.py` confirmado sin cambios (se mantienen nombres de campos en inglés).
- **En curso:**
  - **A4:** Cola de trabajos (`POST /api/v1/trabajos`, `GET /api/v1/trabajos/{id}`) con `ThreadPoolExecutor` (`MAX_WORKERS=2`) y caducidad en memoria.
  - **A2:** Conexión y evaluación con Ollama en la PC de Andrés (`llama3.1:8b` vs `qwen2.5:14b`).
- **Bloqueado por:**
  - **A2:** Descarga de modelos en Ollama de Andrés (mientras tanto se trabaja con modo heurístico y fixtures de `demo.py`).
- **Cambio de interfaz:**
  - Ninguno en `schemas.py` (contrato congelado en inglés). Se agregan endpoints aditivos `/api/v1/trabajos` y `/api/v1/trabajos/{job_id}`.
