# Estado de Andrés

**Última actualización:** 21/11/2026

- **Listo:**
  - `feature/andres-servidor-llm`: PC cerebro (mi laptop, RTX 4060) con gateway autenticado a Ollama + RAG. Guía en `docs/SERVIDOR.md`. Incluye un cambio pequeño a `llm.py`/`config.py` (OLLAMA_API_KEY, OLLAMA_CA_CERT) → **Aaron, revísalo**.
  - `feature/andres-calibrar-cruces` (N2, sin datos reales aún): propietario parecido (50–85 %) → revisión, muy distinto (<50 %) → crítico; superficies con unidad y hectáreas; claves catastrales contenidas una en otra ya no cuentan como discrepancia. Demo 4/4, 0 falsos Cumple.
- **En curso:** descarga de `llama3.1:8b` (internet lento, ~1 h). N1: etiquetas reales.
- **Bloqueado por:** veredictos de referencia del comité (N1) y convención para agrupar expedientes (V5). Mientras: casos ficticios de `demo.py`.
- **Cambio de interfaz:** `CrossCheck` tiene el campo opcional `critical_threshold` (no rompe nada).
