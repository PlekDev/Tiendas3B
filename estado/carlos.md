# Estado de Carlos

**Última actualización:** 21/11/2026 - Sprint Hackatón Tiendas 3B

- **Listo:**
  - **C1 (P0):** Afinados encabezados y descripciones de Escrituras y Predial en `extractor_fields.py`.
  - **C3 (P1):** Afinados encabezados de Alineamiento y Uso de Suelo con soporte para redacción en prosa municipal (`con ubicación en...`, etc.).
  - **Mejora del motor de extracción heurística en `extractor.py`:**
    - Soporte de delimitadores flexibles (`:`, `.-`, `/`, `-`, espacios múltiples).
    - Extracción de superficies de terreno bidireccionales (`(M2) 300.00`, `TERRENO M2: 500`, etc.).
    - Limpieza automática de prefijos residuales (`POSEEDOR`, etc.) y separación de columnas adyacentes (`Régimen:`, `Periodo:`).
    - Soporte para etiquetas incrustadas en frases de prosa legal municipal.
    - Suite de pruebas de extractores (`tests/test_extractor.py`) y linting (`ruff`) al 100% verde.
  - **C4 (P1):** Mejorada la verificación de citas en `_verify` para validar contra el texto continuo de la página (eliminando rechazos falsos por saltos de línea de OCR).

- **En curso:**
  - **C2 (P0):** Pruebas de integración con el modelo LLM local (Ollama) una vez configurado en la PC cerebro (coordinación con Aaron). Mientras tanto, validado con `FakeListChatModel` en las pruebas unitarias.

- **Recién completado:**
  - **Classifier (performance):** Enriquecidos `_KEYWORDS` en `classifier.py` con vocabulario real de docs 3B (Predial, Alineamiento, Uso de Suelo, Escrituras). Reducido texto enviado al LLM de 6 000 → 1 200 chars. Objetivo: aumentar confianza heurística ≥ 0.75 para evitar llamadas al LLM y reducir latencia de 10-20 s a < 1 s por doc.

- **Bloqueado por:**
  - Ninguno. La extracción corre tanto de forma heurística como con LLM falso.

- **Cambio de interfaz:**
  - Ninguno. Se mantiene intacto el contrato de `extract_fields` y `critical_fields` para integración con el orquestador de Aaron y las reglas de Andrés.
