PYTHON ?= python3

.PHONY: install format lint type-check test structure-check quality clean

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

quality: structure-check lint type-check test

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
