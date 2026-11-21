# Guía de la demo en vivo

**Responsable:** Victor · **Va con:** [guion_v1.md](guion_v1.md) (bloque 0:50–2:10) · **Probada:** 21 nov, sobre `dev`

---

## 1. Antes (30 minutos)

- [ ] Laptop de la demo **cargada** y con el cargador a la mano.
- [ ] Conectada al **hotspot de Andrés** (el modelo corre en su PC: `192.168.137.13`).
- [ ] Código al día: `git checkout dev && git pull`.
- [ ] Python listo: `make setup` (solo la primera vez).
- [ ] Dashboard listo: `cd frontend && npm ci` (solo la primera vez).
- [ ] `.env` con `LLM_PROVIDER=ollama` y `OLLAMA_BASE_URL=http://192.168.137.13:11434`.
- [ ] **`API_KEY` vacío en el `.env`**. El dashboard todavía no manda la llave; con `API_KEY` definido, todo responde 401.
- [ ] `.venv/bin/tiendas3b estado` dice **`LLM responde: sí`**.
- [ ] Nadie más usa la GPU de Andrés durante la demo. Con otra prueba corriendo, un expediente pasa de ~1 a ~3.5 minutos.

## 2. Arranque (2 terminales)

```bash
.venv/bin/tiendas3b api
```

```bash
cd frontend && npm run dev
```

Abrir **http://localhost:5173**. Arriba a la derecha debe decir **"IA conectada"**.

Si el puerto 8000 está ocupado: `.venv/bin/tiendas3b api --puerto 8001` y `API_URL=http://localhost:8001 npm run dev`.

## 3. Qué mostrar (sigue el guion)

Los ejemplos corren **sin IA**: salen al instante y no dependen de la red ni de la GPU. Es lo más seguro para el escenario.

| Tiempo | Clic | Qué se ve |
|---|---|---|
| 0:50 | **Nuevo expediente** → tarjeta **Revisión** | Dictamen "Requiere revisión", confianza 80 %, "23 de 23 datos leídos tienen cita" |
| 1:05 | Bajar a **Cómo se decidió** | Clasificador → Extractores → Validador → Cruces → Dictamen, con los ms de cada uno |
| 1:20 | Hallazgo **Superficie del terreno** | Tabla: Escritura 960 m², Predial 850 m², Uso de suelo 850 m² |
| 1:35 | **Ver en el documento →** (escritura) | La página 2 con el renglón resaltado en amarillo |
| 1:50 | **Bandeja** → **Nuevo expediente** → tarjeta **No cumple** | Propietario distinto (44 % de similitud) y uso habitacional |
| 2:05 | **Bandeja** | Los dos expedientes con su veredicto, confianza y bloqueantes |

**Si sobra tiempo o el jurado pregunta "¿y con IA?":** sube los PDF de `data/expedientes/DEMO-REVISION/` con **Usar el modelo de IA** encendido. Tarda ~1 minuto (4 documentos con el LLM). Mejor **súbelo antes de empezar**: la bandeja se guarda en el navegador y queda listo para abrirlo.

## 4. Plan B

| Si falla… | Hacer |
|---|---|
| La red o la GPU de Andrés | Apagar **Usar el modelo de IA**. Los ejemplos funcionan igual |
| La API no arranca | `.venv/bin/tiendas3b ejemplo revision` muestra el dictamen en la terminal |
| El dashboard no carga | Reproducir el **video de respaldo** (V8) |
| Todo | Video de respaldo y seguir con el guion |

## 5. Detalles encontrados al probar (21 nov)

Para pulir antes de la presentación:

- **Diego:** el logo "ir a la bandeja" no regresa desde el dictamen; la pestaña **Bandeja** sí.
- **Diego:** el dashboard no manda `X-API-Key`. Con la seguridad de Aaron activa (`API_KEY`), no carga nada.
- **Diego / Andrés:** algunas razones muestran el mensaje técnico de la regla, p. ej. *"'No compatible con comercio al por menor' menciona: no compatible"*. Mejor algo como "El uso de suelo declara que no es compatible con comercio".
- **Diego:** la bandeja pone *No cumple* antes que *Requiere revisión*; la guía del dashboard pide primero lo que necesita a una persona.
- **Diego (D5):** el dashboard analiza en una sola petición; todavía no usa la cola (`/api/v1/trabajos`) ni la bitácora (`/api/v1/bitacora`). La cola sí funciona: se probó directo contra la API.

Lo que se probó y funciona: bandeja con contadores, los 4 ejemplos, dictamen con razones y pruebas, comparación entre documentos, visor con la cita resaltada, "Cómo se decidió", subida por la cola de trabajos y registro en la bitácora.
