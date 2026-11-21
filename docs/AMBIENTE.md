# Ambiente de trabajo

**Dueño:** Victor (tarea V1) · **Modelo:** corre en la PC de **Andrés**

```
                ┌─────────────────────────────┐
                │  PC de Andrés ("cerebro")   │
                │  Ollama :11434 (modelo LLM) │
                └──────────────▲──────────────┘
                               │ red local (wifi de la hackatón)
      ┌──────────────┬─────────┴─────┬──────────────┐
   Aaron          Carlos          Diego          Victor
   código local + OLLAMA_BASE_URL=http://<IP de Andrés>:11434
```

Cada quien corre el código en su laptop y usa el modelo de Andrés por la red. Cuando exista la
cola de trabajos (A4), la API también vivirá en la PC de Andrés y los demás solo usarán el
navegador.

---

## 1. PC de Andrés: servir el modelo

1. Instalar Ollama: https://ollama.com/download
2. Descargar los modelos a comparar (tarea A2):
   ```bash
   ollama pull llama3.1:8b
   ollama pull qwen2.5:14b
   ```
3. Exponerlo en la red local (por defecto solo escucha en `localhost`):

   | Sistema | Cómo |
   |---|---|
   | Linux (systemd) | `sudo systemctl edit ollama` → agregar `[Service]` y `Environment="OLLAMA_HOST=0.0.0.0:11434"` → `sudo systemctl restart ollama` |
   | Windows | `setx OLLAMA_HOST 0.0.0.0:11434` y reiniciar Ollama desde la bandeja |
   | macOS | `launchctl setenv OLLAMA_HOST 0.0.0.0:11434` y reiniciar la app de Ollama |

4. Recomendadas, con el mismo método:
   - `OLLAMA_KEEP_ALIVE=30m`: el modelo se queda cargado y la primera respuesta no tarda.
   - `OLLAMA_NUM_PARALLEL=2`: atiende dos peticiones a la vez. Súbelo solo si la GPU aguanta.
5. Saber la IP: `ip -4 addr` (Linux), `ipconfig` (Windows), `ipconfig getifaddr en0` (macOS).
   Publicarla en `estado/andres.md`.
6. Permitir el puerto 11434 en el firewall **solo en la red local**.

> **Seguridad:** Ollama no tiene contraseña. Solo exponlo en la red del equipo durante la
> hackatón, nunca en una red pública, y apágalo (`OLLAMA_HOST` de vuelta a `127.0.0.1`) al terminar.

---

## 2. Cada laptop

### Requisitos

| | Linux (Arch) | Linux (Ubuntu/Debian) | macOS | Windows |
|---|---|---|---|---|
| Python 3.11 | `uv python install 3.11` | `sudo apt install python3.11 python3.11-venv` | `brew install python@3.11` | python.org (marcar "Add to PATH") |
| OCR | `sudo pacman -S tesseract tesseract-data-spa` | `sudo apt install tesseract-ocr tesseract-ocr-spa` | `brew install tesseract tesseract-lang` | Instalador de UB Mannheim con idioma español, agregado al PATH |
| Node 20+ (solo Diego) | `sudo pacman -S nodejs npm` | nodesource o `nvm` | `brew install node` | nodejs.org |

`uv` (https://docs.astral.sh/uv/) sirve en los cuatro sistemas y es lo más rápido.

### Instalar el proyecto

```bash
make setup
```

Sin `make` (Windows):

```bash
uv venv -p 3.11 .venv
uv pip install -p .venv -e ".[dev,ocr]"
copy .env.example .env
```

### Conectar al modelo de Andrés

En tu `.env`:

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://<IP de Andrés>:11434
```

Verificar:

```bash
.venv/bin/tiendas3b estado
```

Debe decir `LLM responde: sí`. Después:

```bash
.venv/bin/tiendas3b demo-pdfs
.venv/bin/tiendas3b analizar data/expedientes/DEMO-REVISION
```

En la última línea del encabezado debe decir `modo ollama:llama3.1:8b`, no `heuristico`.

Si el modelo no está disponible, cambia a `LLM_PROVIDER=none` y sigue trabajando: todo corre por la
ruta heurística.

---

## 3. Documentos del reto

- Descomprime los ZIP en `data/raw/` (una carpeta por tipo: `data/raw/escrituras/`, `data/raw/predial/`…).
- `data/raw/`, `data/expedientes/`, `*.pdf` y `*.zip` están en `.gitignore`. **Nunca se suben.**
- No los pegues en servicios externos (ChatGPT, Claude, etc.) sin autorización del comité.
- Compartirlos con la PC de Andrés por la red local está bien: no salen del equipo.

---

## 4. Problemas comunes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `LLM responde: NO` | IP equivocada, Ollama solo en localhost o firewall | `curl http://<IP>:11434/api/tags` desde tu laptop. Si no responde, revisar el paso 3 y el firewall en la PC de Andrés |
| El análisis tarda mucho la primera vez | El modelo se está cargando | `OLLAMA_KEEP_ALIVE=30m` en la PC de Andrés |
| Campos con `method: heuristica` aunque hay LLM | El LLM devolvió JSON inválido dos veces | Ver el log; probar `qwen2.5:14b` |
| `OCR falló … tesseract-ocr-spa` | Falta el idioma español | Instalar el paquete de idioma de la tabla de requisitos |
| `python3.11: command not found` al hacer `make setup` | Python 3.11 no está en el PATH | `make setup PY=python3` si tu versión es ≥ 3.11, o usar `uv` |
