PYTHON ?= python3

.PHONY: install format lint type-check test structure-check generate-data generate-data-ci validate-generation ingest ingest-ci validate-ingestion prepare-forecast-data forecast forecast-ci validate-forecast inventory inventory-ci validate-inventory quality-analytics quality-analytics-ci validate-quality-analytics maintenance maintenance-ci validate-maintenance monitoring monitoring-ci validate-monitoring genai genai-ci validate-genai dashboard dashboard-ci validate-dashboard quality clean

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

prepare-forecast-data:
	$(PYTHON) scripts/prepare_forecasting_data.py --overwrite

forecast:
	$(PYTHON) -m manufacturing_intelligence.forecasting --config configs/forecasting.yaml --overwrite

forecast-ci:
	$(PYTHON) -m manufacturing_intelligence.forecasting --config configs/forecasting_ci.yaml --overwrite

validate-forecast:
	$(PYTHON) -m manufacturing_intelligence.forecasting --config configs/forecasting.yaml --validate-existing-run

inventory:
	$(PYTHON) -m manufacturing_intelligence.inventory --config configs/inventory.yaml --overwrite

inventory-ci:
	$(PYTHON) -m manufacturing_intelligence.inventory --config configs/inventory_ci.yaml --overwrite

validate-inventory:
	$(PYTHON) -m manufacturing_intelligence.inventory --config configs/inventory.yaml --validate-existing-run

quality-analytics:
	$(PYTHON) -m manufacturing_intelligence.quality --config configs/quality.yaml --overwrite

quality-analytics-ci:
	$(PYTHON) -m manufacturing_intelligence.quality --config configs/quality_ci.yaml --overwrite

validate-quality-analytics:
	$(PYTHON) -m manufacturing_intelligence.quality --config configs/quality.yaml --validate-existing-run

maintenance:
	$(PYTHON) -m manufacturing_intelligence.maintenance --config configs/maintenance.yaml --overwrite

maintenance-ci:
	$(PYTHON) -m manufacturing_intelligence.maintenance --config configs/maintenance_ci.yaml --overwrite
	$(PYTHON) -m manufacturing_intelligence.maintenance --config configs/maintenance_ci.yaml --validate-existing-run --output-directory .generated/ci/maintenance

validate-maintenance:
	$(PYTHON) -m manufacturing_intelligence.maintenance --config configs/maintenance.yaml --validate-existing-run

monitoring:
	$(PYTHON) -m manufacturing_intelligence.monitoring --config configs/monitoring.yaml --overwrite

monitoring-ci:
	$(PYTHON) -m manufacturing_intelligence.monitoring --config configs/monitoring_ci.yaml --overwrite
	$(PYTHON) -m manufacturing_intelligence.monitoring --config configs/monitoring_ci.yaml --validate-existing-run --output-directory .generated/ci/monitoring

validate-monitoring:
	$(PYTHON) -m manufacturing_intelligence.monitoring --config configs/monitoring.yaml --validate-existing-run

genai:
	$(PYTHON) -m manufacturing_intelligence.genai --config configs/genai.yaml --overwrite

genai-ci:
	$(PYTHON) -m manufacturing_intelligence.genai --config configs/genai_ci.yaml --overwrite
	$(PYTHON) -m manufacturing_intelligence.genai --config configs/genai_ci.yaml --validate-existing-run --output-directory .generated/ci/genai

validate-genai:
	$(PYTHON) -m manufacturing_intelligence.genai --config configs/genai.yaml --validate-existing-run

dashboard:
	$(PYTHON) -m manufacturing_intelligence.dashboard --config configs/dashboard.yaml --overwrite

dashboard-ci:
	$(PYTHON) -m manufacturing_intelligence.dashboard --config configs/dashboard_ci.yaml --overwrite
	$(PYTHON) -m manufacturing_intelligence.dashboard --config configs/dashboard_ci.yaml --validate-existing-run --output-directory .generated/ci/dashboard

validate-dashboard:
	$(PYTHON) -m manufacturing_intelligence.dashboard --config configs/dashboard.yaml --validate-existing-run

quality: structure-check lint type-check test

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
