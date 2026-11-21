# Pitch de 3 minutos · guion v2

> Los números salen de mediciones reales del equipo (21 nov). Junto a cada uno dice de dónde viene.
> Lo que sigue entre corchetes **todavía no se mide: no inventar cifras.**

**Tiempo objetivo:** 3:00 · **Responsable:** Victor · **Ensayos:** 0 de 3

---

## 1. El problema · 0:00–0:25

> Tiendas 3B abrió 603 tiendas netas en los últimos 12 meses, y solo en el tercer trimestre abrió 4 CEDIS. Cada apertura lleva un expediente legal de inmueble, y hoy cada documento se revisa a mano.

- Escrituras, predial, alineamiento y número oficial, uso de suelo: cuatro documentos por inmueble, cada uno con su guía.
- Y no son PDFs limpios: **el 86 % de las páginas que nos dieron son escaneos.** *(diagnóstico sobre los 63 documentos oficiales)*
- Revisar un expediente toma [M] minutos de una persona. *(dato que debe darnos 3B)*

**Cierre del bloque:** "Cada expediente que revisamos a mano es un local que no evaluamos a tiempo."

---

## 2. La solución · 0:25–0:50

> Cinco agentes coordinados en LangGraph: clasifican, extraen, validan, cruzan y dictaminan. Un supervisor reintenta cuando algo sale incompleto.

- **Clasificador:** identifica cada documento y marca lo desconocido.
- **Extractores:** sacan los campos con página y cita textual, y **el sistema verifica que esa cita exista en el documento**.
- **Validador y cruces:** Python calcula las reglas y las comparaciones. El LLM no decide.
- **Dictaminador:** emite *Cumple*, *Requiere revisión* o *No cumple*, con razones.

**Mostrar:** diagrama del grafo (pantalla "Cómo se decidió" del dashboard).

**Frase clave:** "El LLM lee. Python juzga. Y cada conclusión tiene una cita."

---

## 3. Demo en vivo · 0:50–2:10

Dos expedientes cargados antes de empezar, para no depender del tiempo de carga en vivo. Por defecto, los casos de prueba del sistema (datos ficticios).

| Tiempo | Acción | Qué decir |
|---|---|---|
| 0:50 | Bandeja → abrir el expediente "revisión" | "Ingresamos un expediente completo: cuatro documentos." |
| 1:05 | Mostrar la traza de agentes | "Cada agente deja registro de lo que hizo y cuánto tardó." |
| 1:20 | Veredicto y confianza | "Requiere revisión, con confianza de [X] %." |
| 1:35 | Clic en el hallazgo → comparación entre documentos | "La escritura dice 960 m², el predial 850: una diferencia de 11.5 %." |
| 1:50 | **Ver en el documento** | "Esta es la página y el texto exacto. Nadie tiene que buscarlo." |
| 2:00 | Abrir el expediente "no cumple" | "Aquí el propietario no coincide y el uso de suelo es habitacional: el sistema lo detiene y explica por qué." |

**Plan B:** si la demo falla, reproducir el video grabado (V8).

---

## 4. Resultados · 2:10–2:40

- **Clasificación: 63 de 63 documentos oficiales.** *(diagnóstico con OCR en español)*
- **Lectura:** aun con 86 % de escaneos, extraemos **el 83 % de los datos** y **el 98 % trae su cita verificada** en el texto. *(LLM local llama3.1:8b sobre los 63 documentos)*
- **Dictamen:** [Y] de [N] expedientes reales coinciden con la referencia. *(pendiente: etiquetas de Andrés, N1)*. En los casos de prueba: 4 de 4 y **cero aprobados por error**.
- **Tiempo:** alrededor de **25 s por expediente** en los casos de prueba, con el modelo en una laptop con GPU de 8 GB. Un expediente real escaneado: [S] la primera vez. *(estimado por documento: ~20 s de OCR + ~17 s de LLM; medir uno completo)*. Contra [M] minutos a mano.
- **Seguridad:** lo dudoso va a *Requiere revisión*, nunca a *Cumple*.

**Frase clave:** "Preferimos mandar a revisión a un expediente bueno que aprobar uno malo."

---

## 5. Cómo se usa en 3B · 2:40–3:00

- **Una PC con el modelo y los auditores entran desde el navegador.** Cola de trabajos para que varios revisen a la vez. *(A4)*
- **Los datos no salen de 3B:** el modelo corre en su propia red, y lo que se sube no se queda guardado en el servidor.
- **Todo queda registrado:** cada dictamen guarda fecha, modelo y la versión de las reglas que se usó. *(bitácora)*
- El equipo legal agrega reglas editando un archivo, sin programar.

**Cierre (frase final):** "No reemplazamos al equipo legal. Le damos más expedientes revisados en menos tiempo, y los que no cumplen salen primero."

---

## Pendientes antes del ensayo

- [ ] **[M]** Tiempo de revisión manual por expediente: pedirlo al comité de 3B.
- [ ] **[Y]/[N]** Precisión en expedientes reales: cuando Andrés tenga las etiquetas (N1) y `agrupar` arme los expedientes.
- [ ] **[S]** Medir un expediente real completo con LLM (primera vez y con caché).
- [ ] **[X]** Confianza del caso que se muestre en la demo.
- [ ] Confirmar con el comité las cifras de 3B (603 tiendas netas, 4 CEDIS en 3T26).
- [ ] Decidir si la demo usa los casos de prueba o un expediente real.
- [ ] Cronometrar: meta 3:00, tolerancia ±10 s por bloque. Ensayar 3 veces con la demo real.

## De dónde sale cada número

| Número | Fuente | Fecha |
|---|---|---|
| 86 % de páginas escaneadas | `tiendas3b diagnostico data/raw` (63 docs, 250 págs) | 21 nov |
| 63/63 clasificación | `diagnostico` después del ajuste de títulos (PR #14) | 21 nov |
| 83 % de datos, 98 % con cita | Extracción con `llama3.1:8b` en la PC de Andrés, 63 docs | 21 nov |
| 25 s por expediente, 4/4, 0 aprobados por error | Casos de prueba con LLM (Victor: 25.5 s; Andrés: 25.0 s) | 21 nov |
| ~20 s de OCR y ~17 s de LLM por documento | `diagnostico` y la medición con LLM | 21 nov |
