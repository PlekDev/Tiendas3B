# Pitch de 3 minutos · guion v1

> Borrador. Los números entre corchetes se llenan con datos reales de la corrida de `evaluacion/` y de la medición de tiempos. **No inventar cifras.**

**Tiempo objetivo:** 3:00 · **Responsable:** Victor · **Ensayos:** 0 de 3

---

## 1. El problema · 0:00–0:25

> Tiendas 3B abrió 603 tiendas netas en los últimos 12 meses, y solo en el tercer trimestre abrió 4 CEDIS. Cada apertura lleva un expediente legal de inmueble, y hoy cada documento se revisa a mano.

- Escrituras, predial, alineamiento y número oficial, uso de suelo: cuatro documentos por inmueble, cada uno con su guía.
- Revisar uno toma [X] minutos de una persona. Dato del equipo de 3B: [tiempo manual que nos den].

**Cierre del bloque:** "Cada expediente que revisamos a mano es un local que no evaluamos a tiempo."

---

## 2. La solución · 0:25–0:50

> Cinco agentes coordinados en LangGraph: clasifican, extraen, validan, cruzan y dictaminan.

- **Clasificador:** identifica cada documento y marca lo desconocido.
- **Extractores:** sacan los campos con página y cita textual.
- **Validador normativo y cruces:** Python calcula las reglas y las comparaciones. El LLM no decide.
- **Dictaminador:** emite *Cumple*, *Requiere revisión* o *No cumple*, con razones.

**Mostrar:** diagrama del grafo (la traza de agentes de la demo).

**Frase clave:** "El LLM lee. Python juzga. Y cada conclusión tiene una cita."

---

## 3. Demo en vivo · 0:50–2:10

Dos expedientes cargados antes de la presentación, para no depender del tiempo de carga en vivo.

| Tiempo | Acción | Qué decir |
|---|---|---|
| 0:50 | Cargar el expediente A (Cumple o Requiere revisión) | "Ingresamos un expediente completo. El sistema arranca." |
| 1:05 | Mostrar la traza de agentes corriendo | "Cada agente deja registro de lo que hizo y cuánto tardó." |
| 1:20 | Veredicto y confianza | "Este expediente [resultado]. La confianza es [X]." |
| 1:35 | Hacer clic en un hallazgo | "Aquí está la superficie: 280 m² en la escritura, 250 m² en el predial." |
| 1:50 | Abrir la cita en el documento original | "Esta es la página y el texto exacto. Nadie tiene que buscarlo." |
| 2:00 | Cargar el expediente B (No cumple) y mostrar el motivo | "Aquí el sistema detiene el proceso y explica por qué." |

**Plan B:** si la demo falla, reproducir el video grabado (ver sección 6).

---

## 4. Resultados · 2:10–2:40

- **Precisión:** [Y]% de aciertos contra los [N] expedientes de ejemplo.
- **Tiempo:** [S] segundos por expediente, contra [M] minutos de revisión manual.
- **Seguridad:** lo que tiene confianza alta sale como *Cumple*; lo dudoso va a *Requiere revisión*, nunca a *Cumple*.

**Frase clave:** "Preferimos mandar a revisión a un expediente bueno que aprobar uno malo."

---

## 5. Cómo se usa en 3B · 2:40–3:00

- Sale un JSON auditable por expediente, con evidencia de cada hallazgo.
- Los datos no salen de la infraestructura de 3B. Es por diseño, igual que en TrustNode.
- El equipo legal decide; el sistema prioriza.

**Cierre (frase final):** "No reemplazamos al equipo legal. Le damos más expedientes revisados en menos tiempo y los que no cumplen salen primero."

---

## Pendientes antes del ensayo

- [ ] Llenar cada [corchete] con datos reales (no antes).
- [ ] Confirmar con el comité las cifras de 3B que usamos (603 tiendas netas, 4 CEDIS en 3T26).
- [ ] Decidir qué expediente es el A y cuál el B, según la corrida real.
- [ ] Cronometrar: meta 3:00, tolerancia ±10 s por bloque.
- [ ] Ensayo 1, 2 y 3 con la demo real. Anotar qué bloque se pasó.
