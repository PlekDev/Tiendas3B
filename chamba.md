# Chamba · Reto 1 Expedientes (Hackatón 3B)

Sistema multiagente con LangChain/LangGraph que revisa el expediente de un inmueble, detecta faltantes e inconsistencias y emite **Cumple / Requiere revisión / No cumple** con evidencia citada (archivo, página y cita).

Este archivo dice **quién hace qué**, **qué interfaz entrega cada quien** y **cómo trabajamos sin esperar a nadie**. El código base ya existe en `src/tiendas3b/` (ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)); aquí solo se reparte.

---

## 1. Roles y archivos

| Persona | Responsable de | Archivos | Lista a H+3 (punta a punta) | Lista al cierre de código |
|---|---|---|---|---|
| **Aaron** (líder técnico, dueño del repo) | Contrato de datos, orquestador, LLM y configuración, integración | `src/tiendas3b/models/schemas.py`, `src/tiendas3b/agents/orchestrator.py`, `pyproject.toml`, `.env.example`, `.github/workflows/ci.yml`, `README.md`, `docs/` | Grafo corriendo con agentes provisionales y el análisis devuelve el JSON del contrato | Grafo final, reintento del supervisor, manejo de errores, README para correrlo |
| **Diego** (autor de TrustNode) | Ingesta + OCR, Agente Clasificador, ambiente de las laptops | `src/tiendas3b/ingestion/pdf_loader.py`, `src/tiendas3b/agents/classifier.py` | Texto por página con OCR de respaldo; el clasificador acierta en los expedientes de ejemplo | Clasificador robusto: marca `DESCONOCIDO` y detecta tipos faltantes |
| **Carlos** | Los 4 Agentes Extractores, un modelo por tipo sacado de cada guía, con evidencia por campo | `src/tiendas3b/agents/extractor.py` (y los módulos por tipo que cree) | Extractores de Escrituras y Predial funcionando | Los 4 extractores con citas; prompts afinados con `evaluacion/` |
| **Andrés** | Cartuchos de reglas, Agente Validador Normativo, Agente de Validación Cruzada, Dictaminador, medición de precisión | `src/tiendas3b/rules/criteria.py`, `src/tiendas3b/agents/validator.py`, `src/tiendas3b/agents/cross_validator.py`, `src/tiendas3b/agents/synthesizer.py`, `evaluacion/` | Reglas de una guía + cruce de dirección y superficie + dictamen básico | Todas las reglas y los 5 cruces; reporte de precisión para el pitch |
| **Victor** | Interfaz de la demo (a partir del frontend de TrustNode), pitch, video de respaldo | `src/tiendas3b/ui/app.py`, `interfaz/`, `pitch/` | Pantalla de carga + veredicto conectada al JSON de ejemplo; guion del pitch v1 | Demo pulida (veredicto, matriz, hallazgos con cita, traza del grafo); pitch ensayado ×3; video |

> `evaluacion/` y `pitch/` todavía no existen en el repo: quien los necesite los crea en su PR.

Si cambias de rol o alguien se atora, lo dices en `estado/` (sección 4), no en un chat que se pierde.

---

## 2. Interfaces entre módulos

Cada módulo expone una función con firma fija. Mientras el módulo real no esté listo, su dueño (o Aaron) devuelve **datos falsos de `tests/fixtures/`**, así nadie espera a nadie.

| Módulo | Dueño | Función | Entrada | Salida |
|---|---|---|---|---|
| `ingestion/pdf_loader.py` | Diego | `load_pdf(path) -> LoadedDocument` | PDF del expediente | Páginas con `page_number` y `text` (OCR de respaldo para escaneos) |
| `agents/classifier.py` | Diego | `classify_document(doc) -> DocumentType` | Documento cargado | Tipo, o `DESCONOCIDO` |
| `agents/extractor.py` | Carlos | `extract_fields(doc, doc_type) -> (campos, faltantes)` | Documento y su tipo | Campos con evidencia (archivo, página, cita) |
| `agents/validator.py` | Andrés | `validate_document(...)` | Análisis del documento | Evaluación de reglas de la guía |
| `agents/cross_validator.py` | Andrés | `cross_validate(analyses)` | Análisis de todos los documentos | Hallazgos de dirección, propietario, superficie, clave catastral y número oficial |
| `agents/synthesizer.py` | Andrés | `synthesize_report(...)` | Todo lo anterior | Recomendación, confianza y razones |
| `agents/orchestrator.py` | Aaron | `analyze_expediente(id, documents) -> ExpedienteReport` | Expediente completo | JSON del contrato |

### Reglas del contrato
- **Solo Aaron cambia `models/schemas.py`.** Si necesitas un campo nuevo, avisa en `estado/` o pide un PR a Aaron.
- Si cambias la firma de una función de tu módulo, avisa en tu archivo de `estado/` antes de hacer el PR.
- Toda salida con dato debe llevar **evidencia**: documento, página y cita textual. Si el LLM no puede citar el texto, el dato queda en duda y no cuenta como hecho.
- Criterio de decisión: **Python decide, el LLM extrae y clasifica.** Fechas, montos, superficies, vigencias y coincidencias se calculan en código.

---

## 3. Cómo trabajamos sin depender de nadie

1. **Tu archivo es tuyo.** Edita solo lo de tu fila de la tabla. Si necesitas tocar otro módulo, abre un PR pequeño y menciona a su dueño.
2. **Ramas y PRs pequeños.** Rama `feature/<nombre>-<tema>` (por ejemplo `feature/carlos-extractor-predial`). Un PR = una cosa. Se integra a `dev` (la rama de integración); `main` queda para la versión entregable.
3. **Fixtures antes que integración.** Tu módulo debe correr solo, con datos de `tests/fixtures/` (falsos). Si tu parte depende de otra, usa el fixture y sigue.
4. **Antes de cada PR:** `ruff check src tests`, `ruff format --check src tests` y `pytest`. El CI corre lo mismo.
5. **Medir desde la hora 3.** La medición de precisión corre todos los expedientes de ejemplo y compara contra el veredicto esperado. Cada cambio a un prompt se mide antes de subirlo.
6. **Normalizar antes de comparar.** Quitar acentos y mayúsculas, unificar `Av.`/`Avenida`, `Col.`/`Colonia`, `S/N`, `No.`/`Núm.`. Nombres con `rapidfuzz` y umbral; superficies con tolerancia en %.
7. **Temperatura 0 y salida estructurada** con Pydantic, con un reintento.
8. **En la duda, pedir revisión.** Es más grave dar "Cumple" a un expediente malo que mandar a revisión uno bueno.

---

## 4. Sincronización asíncrona

- **Cada persona actualiza su archivo en `estado/`**: `aaron.md`, `diego.md`, `carlos.md`, `andres.md`, `victor.md`. Un archivo por persona evita conflictos de merge.
- Formato corto, una vez por bloque de sincronización (5 min):
  - **Listo:** qué terminé, con enlace a PR o commit.
  - **En curso:** qué hago ahora.
  - **Bloqueado por:** de quién necesito algo y qué fixture uso mientras tanto.
  - **Cambio de interfaz:** si lo hay.
- No esperes respuesta para avanzar. Si estás bloqueado, usa el fixture y sigue. Revisa `estado/` al inicio de cada bloque.

---

## 5. Datos y restricciones

- **Los datos de 3B solo se usan dentro del reto.** No se suben a ningún servicio externo.
- **Nada de documentos de 3B en ChatGPT, Claude u otros servicios**, a menos que el comité lo autorice.
- Los expedientes reales van en `data/raw/` o `data/expedientes/`. Ya están en `.gitignore` (también `*.pdf` y `*.zip`): **nunca se suben al repo**.
- Los fixtures (datos falsos) sí van al repo, en `tests/fixtures/`.
- El veredicto lo da la solución, no una persona.
- Toda conclusión sale de los documentos originales.
- Si algo de este archivo no coincide con los documentos oficiales del comité, mandan los documentos oficiales.

---

## 6. Cronograma

| Bloque | Qué pasa | Quién |
|---|---|---|
| H+0:00 – 0:30 | Leer bases, guías y datos. Preguntar al comité (sección 7) | Todos |
| H+0:30 – 1:00 | Cerrar contrato (`models/schemas.py`). Fixtures falsos en `tests/fixtures/` | Aaron dirige; todos |
| H+1:00 – 3:00 | Construir en paralelo | Cada quien lo suyo |
| **H+3:00 · Hito 1** | Un expediente real pasa de punta a punta, aunque salga feo | Aaron integra |
| H+3:00 – 5:00 | Afinar precisión, completar reglas y cruces, conectar la interfaz | Carlos, Andrés, Diego / Victor, Aaron |
| **H+5:00 · Hito 2** | Ya no se agregan funciones; solo arreglos | Todos |
| H+5:00 – cierre −0:45 | Estabilizar, grabar video, ensayar pitch ×3 midiendo 3:00 | Victor dirige el pitch; los demás prueban |
| Últimos 45 min | No se toca código. Laptop de la demo cargada, ensayo final | Todos |

---

## 7. Preguntas para el comité (primeros 30 min)

- ¿Qué LLM o endpoint podemos usar? ¿Se permiten APIs externas o tiene que ser local?
- ¿A qué hora cierra la entrega? ¿Cómo y en qué formato?
- ¿Hay expedientes con el veredicto esperado para medir precisión?
- ¿Los documentos son PDF con texto, escaneos o fotos?
- ¿Las guías dicen qué reglas son críticas?

---

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Solo se permite un modelo local y `llama3.1:8b` se queda corto | Probar `qwen2.5:14b` o el más grande que aguanten las laptops. Pasar más reglas a Python |
| Escaneos de mala calidad | Tesseract en español (`tesseract-ocr-spa`). Confianza baja → "Requiere revisión" |
| La integración se atrasa | Contrato en el minuto 30, fixtures y Hito 1 a la hora 3 |
| La demo falla en vivo | Video grabado y resultados guardados de los expedientes de la demo |

---

## 9. Fuentes

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
