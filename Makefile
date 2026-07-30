# Convenience targets for local development. Mirrors what CI runs so
# `make lint && make test` locally is a reliable predictor of CI status.

PYTHON ?= python
VENV ?= .venv
BIN := $(VENV)/bin
ifeq ($(OS),Windows_NT)
	BIN := $(VENV)/Scripts
endif

.PHONY: install test lint format run docker-build compose-up compose-down clean

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt -r requirements-dev.txt
	$(BIN)/pip install -e .

test:
	$(BIN)/pytest -v --cov=fraud_crew --cov-report=term-missing

lint:
	$(BIN)/ruff check src tests
	$(BIN)/mypy src

format:
	$(BIN)/ruff format src tests
	$(BIN)/ruff check --fix src tests

run:
	$(BIN)/uvicorn fraud_crew.api.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker build -t fraud-aml-investigation-crew:local .

compose-up:
	docker compose up --build

compose-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
