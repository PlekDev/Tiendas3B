# Guía para construir el dashboard

**Para:** Diego (dueño de `frontend/`) · **Consume:** la API de `src/tiendas3b/api/main.py`

El objetivo no es mostrar todo lo que calcula el sistema, sino que el equipo legal de 3B
**decida rápido y con evidencia**: qué expedientes siguen, cuáles se caen y en cuáles tiene
que meter la mano una persona.

---

## 1. Para quién es

| Usuario | Qué necesita | Pregunta que trae |
|---|---|---|
| Abogado o analista legal de expansión | Revisar muchos expedientes y concentrarse en los dudosos | "¿Este sigue? Si no, ¿por qué y dónde está la prueba?" |
| Gerente de expansión | Ver el avance de la cartera de locales | "¿Cuántos están listos, cuántos atorados y por qué?" |
| Jurado de la hackatón | Ver que hay agentes, evidencia y criterio | "¿Cómo llegó a esa conclusión?" |

---

## 2. Siete principios

1. **Veredicto en 3 segundos.** Al abrir un expediente se ve primero el veredicto (palabra + color + ícono), la razón principal y la confianza. Sin hacer scroll.
2. **Toda afirmación a un clic de su prueba.** Cada hallazgo muestra la cita, el documento y la página, con un botón para abrir el PDF en esa página.
3. **Lo que pide acción va arriba.** Primero lo bloqueante, luego lo que hay que revisar, después las notas. Lo que cumple va colapsado.
4. **Lenguaje del equipo legal, no del código.** "El propietario no coincide entre Escritura y Predial", no `cross_validation_issue: propietario (critical)`.
5. **Honestidad con la incertidumbre.** Un dato "en duda" (sin cita verificable) se ve distinto a un dato que falla. La confianza siempre visible, explicada en una línea.
6. **Nunca solo color.** Cada estado lleva ícono y texto. Debe funcionar en blanco y negro y para daltónicos.
7. **Rápido y sin depender del LLM.** "Probar con un ejemplo" funciona siempre (`GET /api/v1/ejemplo`), aunque no haya modelo ni documentos.

---

## 3. Pantallas

### A. Bandeja (inicio)

La lista de expedientes, pensada para varios auditores trabajando a la vez.

- **Contadores arriba:** Cumple · Requiere revisión · No cumple · En cola, y el tiempo promedio por expediente.
- **Tabla:** ID, fecha, veredicto (chip), confianza, número de hallazgos bloqueantes y estado (en cola #2 / procesando / listo / error).
- **Orden por defecto:** primero lo que necesita a una persona (Requiere revisión), luego No cumple y al final Cumple.
- **Filtros:** veredicto y fecha. Búsqueda por ID.
- Botón principal: **Nuevo expediente**.

Mientras no existan la cola (tarea A4) ni la bitácora (logs de Victor), la bandeja guarda en el navegador los expedientes de la sesión.

### B. Nuevo expediente

- Arrastrar y soltar PDFs o imágenes, más un campo para el ID del expediente.
- Lista de lo que se espera: Escrituras, Predial, Alineamiento y Número Oficial, Uso de Suelo.
- Botón **Analizar**. Mientras corre, muestra los pasos del grafo (clasificador → extractores → validador → cruces → dictamen) y, con la cola, la posición en la fila.
- Botón secundario: **Probar con un ejemplo** (los 4 casos de `GET /api/v1/casos`).

### C. Dictamen (la pantalla de la demo)

De arriba hacia abajo:

1. **Encabezado:** veredicto grande, anillo de confianza (`ScoreRing`), las 3 primeras razones, fecha, duración y modo del modelo. Botón **Descargar JSON**.
2. **Documentos:** 4 tarjetas, una por tipo esperado. Cada tarjeta dice si se recibió o falta, el archivo, la confianza de clasificación y cuántas reglas no cumplió. Los documentos que faltan se marcan claramente: "Falta".
3. **Hallazgos:** ordenados por severidad. Cada uno se expande para ver qué pasó, los valores que encontró en cada documento y la evidencia (cita + documento + página + **Ver en el documento**).
4. **Comparación entre documentos:** la vista más útil para el equipo legal. Una fila por cruce y una columna por documento:

   | Dato | Escritura | Predial | Alineamiento | Uso de suelo | Resultado |
   |---|---|---|---|---|---|
   | Propietario | Inmobiliaria Demo | María Ejemplo | — | — | No coincide |
   | Superficie | 960 m² | 850 m² | — | 850 m² | Difiere 11.5 % |

   Los valores salen de `document_analyses[].extracted_fields`. Qué campo corresponde a cada cruce está en `CROSS_CHECKS` (`src/tiendas3b/rules/criteria.py`); copia ese mapeo al frontend.
5. **Matriz documento × regla:** adaptación de `ComplianceHeatmap`. Filas = documentos, celdas = reglas (`rule_id`), con su color y la descripción al pasar el cursor.
6. **Datos extraídos:** tabla con campo, valor, página, confianza (barra) y método. Los datos en duda van resaltados.
7. **Cómo se decidió (colapsable):** la traza del grafo (`trace`), con los ms por agente y el diagrama (`GET /api/v1/grafo`). Para el jurado y para auditoría.

### D. Visor de evidencia

Panel lateral que se abre desde cualquier hallazgo: la cita arriba y el PDF abajo, en la página indicada. El archivo subido se abre en el navegador con una URL local del archivo y `#page=N`. **No se guarda nada en el servidor.**

---

## 4. De dónde sale cada dato

| En pantalla | Campo del JSON (`ExpedienteReport`) |
|---|---|
| Veredicto | `recommendation` (`Cumple` · `Requiere revisión` · `No cumple`) |
| Confianza | `confidence` (0–1) |
| Razones | `reasons[]`. Las que empiezan con "Nota:" son avisos que no cambian el veredicto |
| Documentos faltantes | `missing_document_types[]` |
| Tarjeta de documento | `document_analyses[]`: `document_name`, `document_type`, `classification_confidence` |
| Reglas por documento | `document_analyses[].rule_evaluations[]`: `rule_id`, `description`, `passed`, `details`, `severity`, `evidence[]` |
| Datos extraídos | `document_analyses[].extracted_fields[]`: `name`, `value`, `confidence`, `method`, `evidence` |
| Hallazgos entre documentos | `cross_validation_issues[]`: `description`, `severity`, `values_found`, `evidence[]` |
| Evidencia | `evidence`: `document_name`, `page`, `snippet` |
| Traza | `trace[]`: `agent`, `ms`, `detail` · total en `processing_ms` |
| Modo del modelo | `llm_mode` (`heuristico` u `ollama:<modelo>`) |

| Endpoint | Para qué |
|---|---|
| `GET /api/v1/status` | Badge de salud: modelo conectado o modo heurístico |
| `GET /api/v1/casos` · `GET /api/v1/ejemplo?caso=` | Ejemplos sin documentos reales |
| `POST /api/v1/analizar` (multipart `files`, `expediente_id`) | Analizar un expediente subido |
| `GET /api/v1/grafo` | Diagrama Mermaid del grafo |
| `POST /api/v1/trabajos` · `GET /api/v1/trabajos/{id}` | Cola (cuando Aaron la tenga, tarea A4) |

---

## 5. Textos y colores

| Interno | En pantalla | Color | Ícono |
|---|---|---|---|
| `Cumple` | Cumple | Verde | ✓ |
| `Requiere revisión` | Requiere revisión | Ámbar | ! |
| `No cumple` | No cumple | Rojo | ✕ |
| severidad `critical` | Bloqueante | Rojo | ✕ |
| severidad `warning` | Revisar | Ámbar | ! |
| severidad `info` | Nota | Gris o azul | i |
| confianza < 0.6 en un dato | Dato en duda | Contorno punteado | ? |

| `document_type` | En pantalla |
|---|---|
| `escrituras` | Escrituras |
| `predial` | Predial |
| `alineamiento_y_numero_oficial` | Alineamiento y Número Oficial |
| `uso_de_suelo` | Uso de Suelo |
| `desconocido` | Sin identificar |

Nombres de campo legibles: `superficie_terreno` → "Superficie del terreno", `cuenta_predial` → "Cuenta predial", etcétera. Haz un diccionario en el frontend y nunca muestres el nombre interno.

La confianza se explica en una línea: "Qué tan respaldado está el dictamen por citas verificadas en los documentos".

---

## 6. Estados que no se pueden olvidar

| Estado | Qué mostrar |
|---|---|
| Vacío | "Sube un expediente o prueba con un ejemplo" y los dos botones |
| Cargando o en cola | Pasos del grafo y posición en la fila. Nunca una pantalla congelada |
| Error | Mensaje humano ("No pudimos leer `predial.pdf`") y **Reintentar**. El detalle técnico, colapsado |
| Sin modelo | Badge "Modo sin IA (reglas y patrones)". El análisis sigue funcionando |
| Documento escaneado | Etiqueta "Leído con OCR" en la tarjeta, para que se entienda una confianza baja |

---

## 7. Reutilizar de TrustNode

| TrustNode | Aquí |
|---|---|
| `ScoreRing` | Confianza del dictamen |
| `FindingsCard` | Lista de hallazgos con evidencia expandible |
| `ComplianceHeatmap` | Matriz documento × regla |
| `UploadModal` | Nuevo expediente |
| `ExecutiveSummary` | Bloque de razones |
| `styles/index.css` (tokens claro/oscuro) | Paleta base, más los 3 colores de veredicto |
| `ThemeContext` | Tema claro/oscuro |

Quitar: remotion, ChromaDB, standards, easter eggs y animaciones que retrasen la lectura.
Stack: Vite + React + TypeScript, igual que TrustNode. El proxy `/api` → `http://localhost:8000`.

---

## 8. Lo que no hay que hacer

- Mostrar el JSON crudo como pantalla principal (sí como descarga).
- Esconder la evidencia detrás de varios clics.
- Mostrar porcentajes sin decir qué significan.
- Usar jerga técnica en la vista principal: "LLM", "cross validation", "pipeline".
- Animaciones largas antes de mostrar el veredicto.
- Guardar documentos en el servidor o en `localStorage`. En el navegador solo IDs y resultados.

---

## 9. Flujo de la demo (pitch 0:50–2:10)

1. Bandeja → **Nuevo expediente** → subir el caso "revisión".
2. Mientras analiza, se ven los pasos de los agentes.
3. Dictamen: **Requiere revisión**. Razón principal: la superficie difiere 11.5 %.
4. Clic en el hallazgo → comparación entre documentos → **Ver en el documento** → la página con la cita.
5. Volver a la bandeja y abrir el caso "no cumple": propietario distinto y uso habitacional.
6. Abrir "Cómo se decidió": traza del grafo con los ms por agente.

---

## 10. Hecho cuando

- [ ] Los 4 casos de ejemplo se ven completos, sin errores en la consola.
- [ ] Veredicto, razón principal y confianza visibles sin scroll en una laptop de 13".
- [ ] Cada hallazgo muestra cita, documento y página, y abre el PDF en esa página.
- [ ] La comparación entre documentos muestra los 5 cruces.
- [ ] Funciona en modo sin IA y lo indica.
- [ ] Estados vacío, cargando, error y sin modelo implementados.
- [ ] Una persona que no conoce el proyecto entiende el veredicto de un expediente en menos de 30 segundos (pruébalo con alguien del equipo).
