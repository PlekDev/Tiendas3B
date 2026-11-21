# Chamba · Reto 1 Expedientes (Hackatón 3B)

Sistema multiagente con LangChain/LangGraph que revisa el expediente de un inmueble, detecta faltantes e inconsistencias y emite **Cumple / Requiere revisión / No cumple** con evidencia citada (archivo, página y cita).

Este archivo dice **qué ya existe**, **quién hace qué**, **qué interfaz entrega cada quien** y **cómo trabajamos sin esperar a nadie**.

**Equipo:** Aaron (líder técnico) · Diego · Carlos · Andrés · Victor

---

## 0. Alcance del MVP (confirmado con el comité)

- **Tipos de documento mínimos:** Escrituras, Predial, Alineamiento y Número Oficial, Uso de Suelo.
- **Reglas básicas obligatorias:**
  1. **Completitud:** cada documento tiene los datos que pide su guía.
  2. **Congruencia entre documentos:** dirección, propietario, superficie, clave catastral o cuenta predial, y número oficial coinciden.
- **Reglas específicas:** no son obligatorias. Si las definimos, suman (por ejemplo, la compatibilidad con el uso comercial).
- **Veredicto:** Cumple / Requiere revisión / No cumple, con evidencia citada.
- **Lo que no esté en la guía o en este alcance no cuenta como falla.** Si un dato falta o no se puede citar, va a "duda" → Requiere revisión.
- **Pendiente de confirmar con la guía oficial:** vigencia del alineamiento y del uso de suelo. Las reglas están escritas pero apagadas (`activa: false`).

---

## 1. Qué ya existe: el bosquejo

Hay un bosquejo que corre de punta a punta. Ya está en `main` (PR #1); falta llevarlo a `dev` (tarea A1). Toma ideas de TrustNode: ingesta con PyMuPDF, el LLM con JSON estricto y un reintento, reglas en cartuchos JSON y la API con FastAPI. Es un **punto de partida**: cada quien lo mejora en su parte.

### Arranque en 3 comandos

```bash
make setup     # entorno Python 3.11 + dependencias + .env
make ejemplo   # expediente ficticio de punta a punta, sin LLM
make check     # lo mismo que corre el CI: ruff, mypy, pytest
```

Más: `make api` (API en http://127.0.0.1:8000/docs), `make evaluar`, `make demo-pdfs`, `.venv/bin/tiendas3b --help`.

### Estado por pieza

| Pieza | Estado | Dónde | Dueño |
|---|---|---|---|
| Ingesta PyMuPDF + OCR de respaldo | Funciona con PDFs de texto. **OCR sin probar con escaneos reales** | `ingestion/pdf_loader.py` | Victor |
| Clasificador | Palabras clave + LLM cuando duda. Confianza y `desconocido` | `agents/classifier.py` | Victor |
| Extractores | Heurística por encabezados + LLM con **cita verificada contra el texto**. Encabezados genéricos, sin afinar con documentos reales | `agents/extractor.py`, `agents/extractor_fields.py` | Carlos |
| Reglas | Cartuchos JSON por tipo, 6 tipos de regla, sin tocar código | `data/rules/*.json`, `rules/engine.py` | Andrés |
| Cruces | Los 5 cruces + "posible inmueble diferente". Umbrales provisionales | `agents/cross_validator.py`, `rules/criteria.py` | Andrés |
| Dictamen | Política provisional (critical → No cumple, warning → Revisión) | `agents/synthesizer.py` | Andrés |
| Grafo LangGraph | Supervisor que reintenta una vez + traza por agente (ms) | `agents/orchestrator.py` | Aaron |
| API | `status`, `casos`, `ejemplo`, `analizar`, `grafo`. Borra los archivos al terminar | `api/main.py` | Aaron |
| CLI y evaluación | `analizar`, `ejemplo`, `evaluar`, `estado`, `grafo`, `api` | `cli.py`, `evaluacion.py` | Aaron / Andrés |
| Expedientes ficticios | 4 casos (cumple, revisión, no cumple, incompleto) para trabajar sin datos de 3B | `demo.py` | Todos |
| Interfaz (dashboard) | **Pendiente**. Guía lista en [docs/GUIA_DASHBOARD.md](docs/GUIA_DASHBOARD.md) | `frontend/` | Diego |
| Logs y bitácora de auditoría | Listo (V6, V7): JSON por línea con `expediente_id` y `request_id`, valores del expediente redactados, bitácora por dictamen y `GET /api/v1/bitacora` | `logs.py` | Victor |
| Cola de trabajos / modo servidor | **Pendiente** | `api/` | Aaron |
| CI/CD y seguridad | CI actual pasa. Mejoras **pendientes** | `.github/workflows/` | Aaron |

**Lo que no se ha probado:** el LLM real (en la laptop donde se armó no hay Ollama), el OCR en español y los documentos reales. Hoy todo está validado solo con los expedientes ficticios y con un LLM falso en las pruebas.

---

## 2. Roles y archivos

| Persona | Responsable de | Archivos (bajo `src/tiendas3b/` salvo indicación) |
|---|---|---|
| **Aaron** | Contrato de datos, grafo, LLM, API, modo servidor, CI/CD, seguridad, integración | `models/schemas.py`, `agents/orchestrator.py`, `llm.py`, `config.py`, `api/`, `cli.py`, `pyproject.toml`, `.github/`, `README.md`, `docs/` |
| **Diego** (autor de TrustNode) | Interfaz: el dashboard a partir del frontend de TrustNode | `frontend/` (por crear), `ui/`, `docs/GUIA_DASHBOARD.md` |
| **Carlos** | Los 4 extractores y sus prompts | `agents/extractor.py`, `agents/extractor_fields.py` |
| **Andrés** | Reglas, cruces, dictamen, medición de precisión | `rules/`, `data/rules/`, `agents/validator.py`, `agents/cross_validator.py`, `agents/synthesizer.py`, `evaluacion.py`, `evaluacion/` |
| **Victor** | Ingesta + OCR, clasificador, armar expedientes desde los ZIP, ambiente de las laptops, sistema de logs, pitch y video | `ingestion/`, `agents/classifier.py`, `logs.py` (por crear), `pitch/` |

Archivos compartidos (avisa antes de tocarlos): `text.py` (normalización), `demo.py` (fixtures), `tests/`.

---

## 3. Tareas por persona

**P0** = antes del Hito 1 (H+3) · **P1** = antes del Hito 2 (H+5) · **P2** = solo si sobra tiempo.
Cada tarea dice cuándo está hecha y de qué depende. Si depende de alguien, la columna dice qué usar mientras tanto.

### Aaron · integración, servidor, CI/CD, seguridad

| # | Prioridad | Tarea | Hecha cuando | Mientras tanto |
|---|---|---|---|---|
| A1 | P0 | Fusionar `main` en `dev`: el bosquejo entró a `main` por el PR #1 y `dev` tiene tus pruebas nuevas (`conftest.py`, `test_real_expedientes.py`), que usan las mismas firmas. Revisar los **cambios aditivos** a `schemas.py`: `confidence`, `method`, `severity`, `trace`, `reasons`, `processing_ms`, `llm_mode` | `main` y `dev` iguales, con el CI en verde | — |
| A2 | P0 | Ollama en la PC "cerebro". Comparar `llama3.1:8b` contra `qwen2.5:14b` con `tiendas3b evaluar` | `tiendas3b estado` dice "LLM responde: sí" y ya hay un tiempo medido por expediente | El modo heurístico (`LLM_PROVIDER=none`) |
| A3 | P0 | Decidir con Diego el idioma del contrato (hoy en inglés: `recommendation`, `document_analyses`). Se decide una vez y no se cambia | Anotado en `estado/aaron.md` | — |
| A4 | P1 | **Cola de trabajos**: `POST /api/v1/trabajos` → id; `GET /api/v1/trabajos/{id}` → estado, posición y resultado. `ThreadPoolExecutor` con `MAX_WORKERS` (2) y resultados en memoria con caducidad | 3 navegadores suben expedientes a la vez y los tres terminan | `POST /api/v1/analizar` (síncrono) |
| A5 | P1 | **CI/CD**: proteger `main` y `dev` (PR + CI verde), job que compile `frontend/`, `pip-audit` y Dependabot, tag `v0.1-demo` para la demo | Rama protegida y CI con 2 jobs | — |
| A6 | P1 | **Seguridad**: `API_KEY` opcional (header `X-API-Key`) y `CORS_ORIGINS` por variable. Los límites de tamaño ya existen. Que los logs no lleven datos sensibles es V7 (Victor) | Sin la llave, la API responde 401 | — |
| A7 | P2 | `docker compose` (API + Ollama) y dictamen en PDF (`latex_report.py` de TrustNode) | — | — |

### Diego · interfaz (dashboard)

Sigue la guía [docs/GUIA_DASHBOARD.md](docs/GUIA_DASHBOARD.md): pantallas, de dónde sale cada dato, textos, colores, estados y flujo de la demo.

| # | Prioridad | Tarea | Hecha cuando | Mientras tanto |
|---|---|---|---|---|
| D1 | P0 | `frontend/` con Vite + React + TS a partir de TrustNode. Reutilizar `ScoreRing`, `FindingsCard`, `ComplianceHeatmap`, `UploadModal`, `ExecutiveSummary` y los tokens de `index.css`. Pantalla de **dictamen**: veredicto, razones, documentos, hallazgos con cita y matriz documento × regla | Los 4 casos de ejemplo se ven completos | `GET /api/v1/ejemplo?caso=…` (no necesita LLM ni documentos) |
| D2 | P1 | **Comparación entre documentos** (los 5 cruces lado a lado) y datos extraídos con su confianza | Se ve en el caso "revisión" la superficie 960 vs 850 m² | — |
| D3 | P1 | Subida real (`POST /api/v1/analizar`) y **visor de evidencia**: abrir el PDF en `#page=N` con una URL local del archivo, sin guardar nada en el servidor | Clic en un hallazgo → la página del PDF | — |
| D4 | P1 | **Bandeja** de expedientes con contadores, y "Cómo se decidió" (traza + `GET /api/v1/grafo`) | Varios expedientes en la bandeja, ordenados por prioridad | Estado en el navegador hasta que existan A4 y V7 |
| D5 | P1 | Conectar la bandeja a la cola (A4) y a la bitácora (V7) | Cada auditor ve su posición en la fila | — |

### Carlos · extractores

| # | Prioridad | Tarea | Hecha cuando | Mientras tanto |
|---|---|---|---|---|
| C1 | P0 | Afinar encabezados y descripciones de Escrituras y Predial en `extractor_fields.py` con documentos reales, **en local** | `tiendas3b analizar` saca los campos críticos en ≥ 80 % de esos documentos | — |
| C2 | P0 | Probar la ruta LLM con Ollama y ajustar `SYSTEM_PROMPT` | Campos con `method: llm` y cita verificada | `FakeListChatModel` en las pruebas (ver `tests/test_extractor.py`) |
| C3 | P1 | Lo mismo para Alineamiento y Uso de Suelo | Igual que C1 | — |
| C4 | P1 | Bajar los "datos en duda" (confianza < 0.6): revisar caso por caso por qué no se verifica la cita | Menos casos de "Requiere revisión" por dudas | — |

### Andrés · reglas, cruces, dictamen, precisión

| # | Prioridad | Tarea | Hecha cuando | Mientras tanto |
|---|---|---|---|---|
| N1 | P0 | Etiquetas reales en `evaluacion/etiquetas.json` (carpeta → veredicto), del comité o 5 hechas a mano. Solo IDs y veredictos, nunca contenido | `tiendas3b evaluar` corre sobre expedientes reales | Las 4 etiquetas ficticias |
| N2 | P0 | Calibrar umbrales y severidades en `CROSS_CHECKS` y en los cartuchos con resultados reales | **0 falsos "Cumple"** en la evaluación | — |
| N3 | P1 | Reglas específicas: vigencias (cuando la guía las confirme) y compatibilidad comercial | Reglas activas con su prueba | — |
| N4 | P1 | Reporte de precisión para el pitch: aciertos, falsos Cumple y segundos por expediente | Números en `estado/andres.md` para Victor | — |
| N5 | P1 | Revisar la política del dictamen (¿que falte la escritura debe ser No cumple?) | Decisión anotada en `synthesizer.py` | — |

### Victor · ingesta, OCR, clasificador, ambiente, logs, pitch

| # | Prioridad | Tarea | Hecha cuando | Mientras tanto |
|---|---|---|---|---|
| V1 | P0 | Ambiente de las 5 laptops: Python 3.11, `make setup`, `tesseract-ocr-spa` (y Node para Diego) | `make check` en verde en todas | — |
| V2 | P0 | Con los documentos reales **en local**: cuántas páginas son escaneo (`LoadedPage.source == "ocr"`) y qué tan bueno sale el OCR | Números en `estado/victor.md` | — |
| V3 | P0 | Correr el clasificador sobre los PDFs reales y ajustar `_KEYWORDS` | ≥ 95 % de acierto, o lista de los que fallan | — |
| V4 | P0 | Guion del pitch v1 (`pitch/guion_v1.md`) | Leído en voz alta en 3:00 | Cifras en corchetes hasta tener N4 |
| V5 | P1 | **Armar expedientes**: los ZIP vienen por tipo de documento, no por inmueble. Comando `tiendas3b agrupar` que junte por clave catastral o dirección, o por la convención de nombres que diga el comité | Carpetas `data/expedientes/<ID>/` con sus documentos | Los expedientes ficticios |
| V6 | P1 | **Logs estructurados** (`logs.py`): una línea JSON por evento en `logs/tiendas3b.jsonl` con `expediente_id`, `request_id`, agente, ms y resultado; consola legible; nivel con `LOG_LEVEL`. Agregar `logs/` al `.gitignore` | Cada análisis deja su rastro completo por agente | — |
| V7 | P1 | **Bitácora de auditoría y confidencialidad**: un registro por dictamen (fecha, expediente, veredicto, confianza, modelo, huella de los cartuchos de reglas, duración) y `GET /api/v1/bitacora` para el dashboard. Filtro con prueba que impida escribir texto de documentos o nombres de propietarios en los logs | Se puede reconstruir qué se dictaminó, cuándo y con qué reglas | — |
| V8 | P1 | Video de respaldo (con Diego) y 3 ensayos con la demo real | Video guardado en 2 laptops | — |
| V9 | P2 | Preprocesar imágenes para el OCR (escala de grises, binarizar) si la calidad es baja | — | — |

---

## 4. Diferenciadores

| Diferenciador | Por qué le importa a 3B | Dueño | Prioridad |
|---|---|---|---|
| **PC cerebro + auditores en el navegador** | Una sola máquina con GPU y modelo. Los demás abren la interfaz por la red local y no instalan nada. Los documentos no salen de esa PC | Aaron (A4) + Diego (D5) | P1 |
| **Bitácora auditable** | Cada dictamen queda registrado con fecha, modelo y versión de las reglas. El equipo legal puede explicar cualquier decisión después | Victor (V6, V7) | P1 |
| **Dashboard pensado para el equipo legal** | Veredicto en 3 segundos y cada hallazgo a un clic de su cita | Diego (D1–D4) | P0–P1 |
| **Cola de trabajos** | Varios auditores a la vez sin saturar el LLM, que es el cuello de botella. Cada quien ve su posición en la fila | Aaron (A4) | P1 |
| **Seguridad y confidencialidad** | LLM local, archivos temporales que se borran, llave de API, CORS cerrado, logs sin contenido, dependencias auditadas | Aaron (A6) | P1 |
| **CI/CD** | Cada cambio pasa lint, tipos y pruebas antes de entrar. La demo sale de un tag estable | Aaron (A5) | P1 |
| **Evidencia verificada** | El sistema comprueba que la cita del LLM exista en el documento. Si no existe, el dato queda en duda | Ya está | — |
| **Reglas sin programar** | El equipo legal agrega una regla editando un JSON | Ya está | — |

**Recomendación sobre la cola:** para la demo, una cola en memoria con `ThreadPoolExecutor` y pocos workers alcanza: sin Redis y sin nada extra que instalar. Hilos sin límite no conviene, porque Ollama atiende pocas peticiones a la vez (`OLLAMA_NUM_PARALLEL`) y las demás esperarían igual pero sin orden. Si 3B lo lleva a producción, se cambia por una cola persistente (RQ o Celery con Redis) sin tocar los agentes.

---

## 5. Interfaces entre módulos

Firmas estables. Si cambias una, avisa en tu archivo de `estado/` antes del PR.

| Módulo | Dueño | Función | Devuelve |
|---|---|---|---|
| `ingestion/pdf_loader.py` | Victor | `load_document(path)`, `load_expediente_dir(dir)` | `LoadedDocument` con páginas (`text`, `source`: pdf/ocr/vacia) |
| `agents/classifier.py` | Victor | `classify(doc, llm=None, all_pages=False)` | `Classification(document_type, confidence, method)` |
| `agents/extractor.py` | Carlos | `extract_fields(doc, doc_type, llm=None, strategy="auto")` | `(list[ExtractedField], faltantes)`; cada campo con `evidence` y `confidence` |
| `agents/validator.py` | Andrés | `validate_document(analysis, cartuchos)` | `list[RuleEvaluation]` con `severity` |
| `agents/cross_validator.py` | Andrés | `cross_validate_detailed(analyses)` | `(issues, resumen por cruce)` |
| `agents/synthesizer.py` | Andrés | `synthesize_report(...)` | `ExpedienteReport` |
| `agents/orchestrator.py` | Aaron | `analyze_expediente(id, documents, llm=None, use_llm=True)` | `ExpedienteReport` con `trace` |
| `api/main.py` | Aaron | `GET /api/v1/ejemplo?caso=` · `POST /api/v1/analizar` | JSON de `ExpedienteReport` |

**Reglas del contrato**
- **Solo Aaron cambia `models/schemas.py`.** Si necesitas un campo nuevo, pídelo en `estado/`.
- Toda salida con dato lleva **evidencia**: documento, página y cita textual.
- **Python decide; el LLM extrae y clasifica.** Fechas, superficies, vigencias y coincidencias se calculan en código.

---

## 6. Cómo trabajamos sin depender de nadie

1. **Tu archivo es tuyo.** Edita solo lo de tu fila. Para tocar otro módulo, abre un PR pequeño y menciona a su dueño.
2. **Ramas y PRs pequeños.** `feature/<nombre>-<tema>` → PR a `dev`. `main` queda para lo que se entrega.
3. **Fixtures antes que integración.** Todo corre con los expedientes ficticios de `demo.py`. Si tu parte depende de otra, usa el fixture y sigue.
4. **Antes de cada PR:** `make check`.
5. **Medir siempre:** `tiendas3b evaluar` antes y después de cambiar un prompt, una regla o un umbral.
6. **Temperatura 0**, JSON validado con Pydantic y un reintento (ya está en `llm.py`).
7. **En la duda, pedir revisión.** Es peor dar "Cumple" a un expediente malo que mandar a revisión uno bueno.

## 7. Sincronización asíncrona

- Cada persona actualiza su archivo en `estado/` (`aaron.md`, `diego.md`, `carlos.md`, `andres.md`, `victor.md`): **Listo**, **En curso**, **Bloqueado por** (y qué fixture usas mientras tanto), **Cambio de interfaz**.
- No esperes respuesta para avanzar. Revisa `estado/` al inicio de cada bloque.

---

## 8. Datos y restricciones

- **Los datos de 3B solo se usan dentro del reto.** No se suben a ningún servicio externo.
- **Nada de documentos de 3B en ChatGPT, Claude u otros servicios** sin autorización del comité. Esto incluye usar `LLM_PROVIDER=openai` con documentos reales.
- Los ZIP oficiales se descomprimen en `data/raw/` y los expedientes armados van en `data/expedientes/`. Ambas carpetas, `*.pdf` y `*.zip` están en `.gitignore`: **nunca se suben al repo**.
- En el repo solo van datos ficticios (`demo.py`) y etiquetas (ID → veredicto).
- El veredicto lo da la solución, no una persona. Toda conclusión sale de los documentos originales.
- Si algo de este archivo no coincide con los documentos oficiales del comité, mandan los documentos oficiales.

---

## 9. Cronograma

| Bloque | Qué pasa | Quién |
|---|---|---|
| H+0:00 – 0:30 | Leer bases y guías. Preguntar al comité (sección 10). `make setup` en todas las laptops | Todos |
| H+0:30 – 1:00 | Fusionar el bosquejo a `dev` (A1). Cerrar el contrato (A3) | Aaron dirige |
| H+1:00 – 3:00 | Tareas P0 en paralelo | Cada quien lo suyo |
| **H+3:00 · Hito 1** | Un expediente real pasa de punta a punta con el LLM y se ve en la interfaz | Aaron integra |
| H+3:00 – 5:00 | Tareas P1: precisión, cola, seguridad, interfaz completa | Todos |
| **H+5:00 · Hito 2** | Ya no se agregan funciones; solo arreglos | Todos |
| H+5:00 – cierre −0:45 | Estabilizar, grabar el video, ensayar el pitch ×3 midiendo 3:00 | Victor dirige el pitch |
| Últimos 45 min | No se toca código. Laptop de la demo cargada, ensayo final | Todos |

---

## 10. Preguntas para el comité

Respondida: **reglas** → para el MVP, reglas básicas de datos y congruencia (sección 0).

Pendientes:
- ¿Cómo se relacionan los documentos de los 4 ZIP con cada inmueble? (¿hay una convención de nombres o una lista?)
- ¿Hay expedientes con el veredicto esperado para medir la precisión?
- ¿Se permite un LLM externo o tiene que ser local?
- ¿Qué vigencia tienen el alineamiento y el uso de suelo según la guía?
- ¿A qué hora cierra la entrega y en qué formato? (Hay una nota que dice presentaciones a las 5:00 PM)

---

## 11. Riesgos

| Riesgo | Mitigación |
|---|---|
| `llama3.1:8b` se queda corto en precisión | Probar `qwen2.5:14b` (A2). Más reglas en Python. La heurística siempre queda de respaldo |
| Escaneos de mala calidad | `tesseract-ocr-spa` (V1), preprocesado (V9). Confianza baja → "Requiere revisión" |
| Los ZIP no traen cómo armar expedientes | Preguntar al comité. Agrupar por clave catastral o dirección (V5) |
| Varios auditores saturan el LLM | Cola con pocos workers (A4) |
| La integración se atrasa | El bosquejo ya integra todo. Cada quien mejora su pieza sin romper la firma |
| La demo falla en vivo | Video grabado (V8) y `GET /api/v1/ejemplo` como respaldo |

---

## 12. Fuentes

- Retos oficiales: https://hackaton3b.com/ · https://hackaton3b.com/expedientes.html
- TrustNode (base reutilizada): https://github.com/Diego-do-na/TrustNode
- Due diligence con IA en México (Loma Alta Capital): https://ecosistemastartup.com/?p=116057
- Garrigues, due diligence inmobiliario en México: https://www.garrigues.com/es_ES/noticia/due-diligence-inmobiliario-mexico-claves-proceso-seguro
- ICSC sobre Orbital: https://www.icsc.com/news-and-views/icsc-exchange/how-purpose-built-ai-could-reshape-real-estate-due-diligence
- V7 Go, análisis de compromisos de título: https://www.v7labs.com/automations/title-commitment-analysis/new-by-ben
- First American: https://nationalmortgageprofessional.com/news/first-american-launches-ai-tool-analyze-title-documents-targeting-closing-delays
- Landeed: https://landeed.com/ai-title-reports
- Requisitos municipales: San Andrés Cholula (alineamiento) https://sach.gob.mx/wp-content/uploads/2025/01/ALINEAMIENTO-Y-NUMERO-OFICIAL.pdf · Santa Isabel Cholula (uso de suelo) https://santaisabelcholula.gob.mx/wp-content/uploads/2025/02/B.-CONSTANCIA-DE-USO-DE-SUELO.pdf
- Tiendas 3B, resultados 3T26: https://www.morningstar.com/news/business-wire/20261030251364/tiendas-3b-3q26-earnings-release
- Patrón supervisor en LangGraph: https://fareedkhan-dev.github.io/all-agentic-architectures/architectures/05_multi_agent/
