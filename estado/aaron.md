# Estado de Aaron

**Última actualización:** 2026-11-21 12:05

- **Listo:**
  - **A1:** `main` y `dev` sincronizadas con el bosquejo e integración de pruebas; `Makefile` compatible con Python 3.11/3.12/3; `pytest` configurado con `-m 'not real_data'` por defecto y `make check` en verde.
  - **A2:** Conectado al Ollama de Andrés (`OLLAMA_BASE_URL=http://192.168.137.13:11434`, `llama3.1:8b`). `tiendas3b estado` → `LLM responde: sí`. `tiendas3b evaluar --demo` con LLM real → **4/4 aciertos (100%), 0 falsos Cumple, 30.9 s promedio por expediente**.
  - **A3:** Contrato de datos en `models/schemas.py` confirmado sin cambios (se mantienen nombres de campos en inglés).
  - **A4:** Cola de trabajos en memoria (`src/tiendas3b/api/jobs.py` + endpoints `POST /api/v1/trabajos`, `GET /api/v1/trabajos` y `GET /api/v1/trabajos/{job_id}`) con `ThreadPoolExecutor` (`MAX_WORKERS=2`), posición en fila, integración con bitácora, limpieza automática del directorio temporal y caducidad por TTL (`JOB_TTL_S=3600`).
  - **A5:** CI con 2 jobs (`lint-and-test` con `pip-audit` + `frontend-build` para Vite/React/TS), `.github/dependabot.yml` y protección de ramas.
  - **A6:** Seguridad en la API (`API_KEY` opcional validada por header `X-API-Key` con `hmac.compare_digest` respondiendo `401` si falta, y `CORS_ORIGINS` configurable por variable de entorno).
- **En curso:**
  - Integración del Hito 1 con expedientes reales una vez agrupados en `data/expedientes/`.
- **Bloqueado por:**
  - Nada. Todas las tareas P0 y P1 de Aaron (A1–A6) están completadas.
- **Cambio de interfaz:**
  - Ninguno que rompa compatibilidad. Si `API_KEY` está vacía en `.env` (valor por defecto), la API no exige `X-API-Key`.
