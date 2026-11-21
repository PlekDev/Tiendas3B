# Estado de Andrés

**Última actualización:** 21/11/2026

- **Listo:**
  - N0: Ollama en mi PC (RTX 4060, 8 GB) con `llama3.1:8b`, `qwen2.5:7b` y `nomic-embed-text`. Se sirve como dice `docs/AMBIENTE.md` §1.
    **IP (hotspot): `172.31.13.101`** → `OLLAMA_BASE_URL=http://172.31.13.101:11434`. Si cambia de red, la actualizo aquí.
  - Comparación de modelos (casos ficticios, con LLM):

    | Modelo | Aciertos | Falsos Cumple | Seg./expediente |
    |---|---|---|---|
    | `llama3.1:8b` | 4/4 | 0 | 25.0 |
    | `qwen2.5:7b` | 1/4 | 0 | 26.4 |

    Se queda **`llama3.1:8b`**. `qwen2.5:7b` toma al **vendedor** como propietario en la escritura → falso "No cumple" por cruce de propietario. `qwen2.5:14b` no cabe en 8 GB de VRAM.
  - `feature/andres-calibrar-cruces` (N2): propietario parecido (50–85 %) → revisión, muy distinto (<50 %) → crítico; superficies con unidad y hectáreas; claves catastrales contenidas una en otra ya no cuentan como discrepancia. Demo 4/4.
- **En curso:** N1 (etiquetas) en cuanto `tiendas3b agrupar` arme los expedientes reales.
- **Bloqueado por:** veredictos de referencia del comité (N1). Mientras: casos ficticios.
- **Para Carlos:** en `extractor_fields.py`, la descripción de `propietario` en Escrituras debería decir "el comprador o adquirente actual, **no el vendedor**". Con eso qwen deja de fallar y llama gana margen.
- **Para Victor:** `agrupar` recorre `__MACOSX/._*.pdf` (basura de Mac que traen los ZIP); conviene filtrarlos.
- **Cambio de interfaz:** `CrossCheck` tiene el campo opcional `critical_threshold` (no rompe nada).
