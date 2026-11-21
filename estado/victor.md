# Estado de Victor

**Última actualización:** 21 nov 2026

- **Listo:**
  - Ambiente, logs y bitácora, `diagnostico` y `agrupar` (V1, V5, V6, V7) · ya en `dev`
  - **V2 y V3 medidos** con `tiendas3b diagnostico data/raw` sobre los 4 ZIP oficiales:
    - 63 documentos, 250 páginas. **86 % de las páginas necesitó OCR** (casi todo son escaneos); 2 % quedó vacío aun con OCR
    - **Clasificador: 61/63 (97 %)**. Escrituras 12/12, Uso de Suelo 16/16, Alineamiento 17/18 (1 confundido con Predial), Predial 16/17 (1 confundido con Escrituras). 2 con confianza < 0.6
    - **≈20 s por documento** (lectura + OCR + clasificación); 21 min para los 63
  - **Conectado al modelo de Andrés** (`ollama:llama3.1:8b` en `192.168.137.13`): los 4 casos ficticios dan el veredicto esperado con LLM, **25.5 s por expediente**, 23 de 23 campos extraídos por el LLM con cita verificada en el texto
  - Caché de OCR: cada documento se lee una vez (`data/cache/ocr/`, ignorada por git); `OCR_DPI` para cambiar velocidad/calidad · rama `feature/victor-cache-ocr`
- **En curso:** `agrupar data/raw --simular` para proponer los expedientes (V5) y revisar los 2 documentos mal clasificados
- **Bloqueado por:** nada
- **Para el equipo:**
  - Carlos y Andrés: el texto de casi todo viene de OCR, así que esperen errores de lectura (acentos, 0/O, 1/l); conviene comparar con tolerancia
  - Al descomprimir los ZIP, borrar `__MACOSX`. Andrés: el filtro que pediste para `agrupar` ya está en el PR #14
- **Cambio de interfaz:** `load_document(path, use_cache=True)` y `load_expediente_dir(dir, use_cache=True)`: parámetro nuevo opcional. La API llama con `use_cache=False`
