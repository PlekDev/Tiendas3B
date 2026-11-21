# Estado de Aaron

**Última actualización:** 2026-11-21 11:28

- **Listo:**
  - **A1:** `main` y `dev` sincronizadas con el bosquejo e integración de pruebas; `Makefile` compatible con Python 3.11/3.12/3; `pytest` configurado con `-m 'not real_data'` por defecto y `make check` en verde.
  - **A3:** Contrato de datos en `models/schemas.py` confirmado sin cambios (se mantienen nombres de campos en inglés).
  - **A4:** Cola de trabajos en memoria (`src/tiendas3b/api/jobs.py` + endpoints `POST /api/v1/trabajos`, `GET /api/v1/trabajos` y `GET /api/v1/trabajos/{job_id}`) con `ThreadPoolExecutor` (`MAX_WORKERS=2`), posición en fila, integración con bitácora, limpieza automática del directorio temporal y caducidad por TTL (`JOB_TTL_S=3600`).
  - **A5:** CI con 2 jobs (`lint-and-test` con `pip-audit` + `frontend-build` para Vite/React/TS) y `.github/dependabot.yml`.
- **En curso:**
  - **A6:** Seguridad en la API (`API_KEY` opcional por header `X-API-Key` y `CORS_ORIGINS` por variable de entorno).
  - **A2:** Conexión y evaluación con Ollama en la PC de Andrés (`llama3.1:8b` vs `qwen2.5:14b`).
- **Bloqueado por:**
  - **A2:** Descarga de modelos en Ollama de Andrés (mientras tanto se trabaja con modo heurístico y fixtures de `demo.py`).
- **Cambio de interfaz:**
  - Ninguno en `schemas.py` (contrato congelado en inglés).
  - Endpoints de cola en `api/main.py` ya integrados en `dev` (`POST /api/v1/trabajos`, `GET /api/v1/trabajos`, `GET /api/v1/trabajos/{job_id}`).
