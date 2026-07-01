PYTHON ?= python3

.PHONY: install format lint type-check test structure-check generate-data generate-data-ci validate-generation ingest ingest-ci validate-ingestion quality clean

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

format:
	$(PYTHON) -m ruff format .

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

type-check:
	$(PYTHON) -m mypy

test:
	$(PYTHON) -m pytest

structure-check:
	$(PYTHON) scripts/check_structure.py

generate-data:
	$(PYTHON) scripts/generate_synthetic_data.py --config configs/synthetic_data.yaml --overwrite

generate-data-ci:
	$(PYTHON) scripts/generate_synthetic_data.py --config configs/synthetic_data_ci.yaml --output-dir .generated/ci/raw --overwrite

validate-generation:
	$(PYTHON) scripts/generate_synthetic_data.py --validate-existing --output-dir data/raw

ingest:
	$(PYTHON) -m manufacturing_intelligence.ingestion --config configs/ingestion.yaml --overwrite

ingest-ci:
	$(PYTHON) -m manufacturing_intelligence.ingestion --config configs/ingestion_ci.yaml --overwrite

validate-ingestion:
	$(PYTHON) -m manufacturing_intelligence.ingestion --config configs/ingestion.yaml --validate-existing-run

quality: structure-check lint type-check test

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
