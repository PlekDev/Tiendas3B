PY ?= $(shell command -v python3.11 || command -v python3.12 || command -v python3)
VENV := .venv
BIN := $(VENV)/bin

.PHONY: setup check test ejemplo demo-pdfs evaluar api

setup:  ## Crea el entorno e instala todo (incluye OCR y herramientas de desarrollo)
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -e ".[dev,ocr]"
	test -f .env || cp .env.example .env

check:  ## Lo mismo que corre el CI
	$(BIN)/ruff check src tests
	$(BIN)/ruff format --check src tests
	$(BIN)/mypy src
	$(BIN)/pytest

test:
	$(BIN)/pytest

ejemplo:  ## Expediente ficticio de punta a punta, sin LLM
	$(BIN)/tiendas3b ejemplo revision

demo-pdfs:  ## Escribe los expedientes ficticios como PDFs en data/expedientes/
	$(BIN)/tiendas3b demo-pdfs

evaluar:  ## Precisión contra evaluacion/etiquetas.json
	$(BIN)/tiendas3b evaluar

api:  ## API en http://127.0.0.1:8000 (docs en /docs)
	$(BIN)/tiendas3b api --reload
