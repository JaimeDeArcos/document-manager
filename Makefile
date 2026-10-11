.PHONY: help setup models doctor run test demo-pdf

UV ?= uv
PYTHON ?= python3.11
PORT ?= 8501

help:
	@printf '%s\n' 'make setup       Install locked Python dependencies' 'make models      Pull the two local Ollama models' 'make doctor      Check Ollama and model availability' 'make demo-pdf    Create a small PDF to upload' 'make run         Start the local chat UI (PORT=8501)' 'make test        Run automated tests'

setup:
	$(UV) sync --locked --python $(PYTHON) --extra dev

models:
	@command -v ollama >/dev/null || (echo "Install Ollama first: https://ollama.com/download"; exit 1)
	ollama pull embeddinggemma
	ollama pull gemma3:4b

doctor:
	$(UV) run python -m document_manager.doctor

run:
	$(UV) run streamlit run src/document_manager/app.py --server.address 127.0.0.1 --server.port $(PORT) --server.headless true

test:
	$(UV) run pytest -q

demo-pdf:
	$(UV) run python -m document_manager.demo
