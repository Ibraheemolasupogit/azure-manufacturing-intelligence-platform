# Milestone 2 - Deterministic Synthetic Manufacturing Datasets

## Objective

Create deterministic, configurable, local-first synthetic raw datasets for the seven manufacturing and supply-chain domains defined in Milestone 1.

## Scope delivered

- Local synthetic data configuration in `configs/synthetic_data.yaml`.
- Smaller CI synthetic data configuration in `configs/synthetic_data_ci.yaml`.
- Cross-domain entity catalog for plants, lines, machines, products, materials, warehouses, suppliers, customer segments, and regions.
- Deterministic generators for production events, inventory levels, sales orders, quality checks, equipment health, warehouse movements, and supplier performance.
- Reproducible JSONL and CSV file creation under `data/raw/`.
- Schema metadata, generation manifest, and generation summary files.
- CLI/script entry point via `python -m manufacturing_intelligence.data_generation`, `make generate-data`, `make generate-data-ci`, and `make validate-generation`.
- Overwrite protection that refuses to replace managed generated files unless overwrite is explicitly enabled.
- Unit tests for deterministic output, seed changes, schema shape, manifest integrity, cross-dataset consistency, overwrite behaviour, invalid configuration, and domain invariants.

## Scope boundaries

Milestone 2 does not implement ingestion, accepted or quarantined data zones, external schema enforcement, forecasting, optimisation, anomaly detection, predictive maintenance, dashboards, GenAI, Azure SDK integration, databases, orchestration services, or cloud deployment.

## Commands executed

- `git status --short --branch`
- `rg --files -uu`
- `find . -maxdepth 3 -type d -print`
- `git log --oneline --decorate -5`
- `sed -n '1,260p' README.md`
- `sed -n '1,240p' configs/platform.yaml`
- `sed -n '1,220p' configs/environments/local.yaml`
- `sed -n '1,220p' configs/environments/ci.yaml`
- `sed -n '1,260p' docs/business/business-context.md`
- `sed -n '1,260p' docs/business/manufacturing-use-cases.md`
- `sed -n '1,320p' docs/business/kpi-catalogue.md`
- `sed -n '1,280p' docs/engineering/data-contracts.md`
- `sed -n '1,420p' docs/roadmap.md`
- `sed -n '1,320p' docs/milestones/milestone-1.md`
- `find src/manufacturing_intelligence -type f -maxdepth 4 -print | sort`
- `find tests -type f -maxdepth 4 -print | sort`
- `sed -n '1,280p' Makefile`
- `sed -n '1,320p' pyproject.toml`
- `sed -n '1,260p' .github/workflows/ci.yml`
- `sed -n '1,260p' src/manufacturing_intelligence/common/config.py`
- `make quality` before implementation
- `make generate-data`
- `head -n 3 data/raw/production_events.jsonl`
- `head -n 5 data/raw/inventory_levels.csv`
- `head -n 5 data/raw/sales_orders.csv`
- `sed -n '1,120p' data/raw/generation_manifest.json`
- `python3 -m ruff format .`
- `python3 -m ruff check --fix scripts/generate_synthetic_data.py src/manufacturing_intelligence/data_generation/__main__.py`
- `make quality` after implementation
- `git diff --check`
- `make validate-generation`
- `python3 scripts/generate_synthetic_data.py --config configs/synthetic_data_ci.yaml --validate-config-only`
- `make generate-data-ci`
- `sed -n '1,220p' data/raw/generation_summary.md`
- `sed -n '1,180p' data/raw/generation_manifest.json`
- `sed -n '1,160p' .generated/ci/raw/generation_manifest.json`

## Test and quality results

- Pre-implementation `make quality`: passed with 11 tests and 73% total coverage.
- `make generate-data`: succeeded.
  - `production_events`: 168 rows
  - `inventory_levels`: 72 rows
  - `sales_orders`: 180 rows
  - `quality_checks`: 168 rows
  - `equipment_health`: 504 rows
  - `warehouse_movements`: 220 rows
  - `supplier_performance`: 120 rows
- `make validate-generation`: passed and validated the existing `data/raw/` run without regenerating it.
- CI config dry run: `Synthetic data config valid: 2026.07-milestone-2-ci, ci_smoke, seed 20260703`.
- `make generate-data-ci`: succeeded and wrote to ignored `.generated/ci/raw/`.
  - `production_events`: 4 rows
  - `inventory_levels`: 14 rows
  - `sales_orders`: 12 rows
  - `quality_checks`: 4 rows
  - `equipment_health`: 8 rows
  - `warehouse_movements`: 16 rows
  - `supplier_performance`: 10 rows
- Final `make quality`: passed.
  - `python3 scripts/check_structure.py`: `Repository structure check passed.`
  - `python3 -m ruff check .`: `All checks passed!`
  - `python3 -m ruff format --check .`: `26 files already formatted`
  - `python3 -m mypy`: `Success: no issues found in 21 source files`
  - `python3 -m pytest`: `27 passed in 0.89s`
  - Coverage summary from the final test run: 84% total line coverage.
- `git diff --check`: passed with no whitespace errors.

## Configuration profiles

| Profile | Config | Mode | Seed | Date range | Scale |
| --- | --- | --- | ---: | --- | --- |
| Local sample | `configs/synthetic_data.yaml` | `local_sample` | 20260702 | 2026-01-01 to 2026-01-14 | 3 plants, 6 lines, 18 machines, 8 products, 10 materials, 4 warehouses, 6 suppliers |
| CI smoke | `configs/synthetic_data_ci.yaml` | `ci_smoke` | 20260703 | 2026-01-01 to 2026-01-02 | 1 plant, 1 line, 2 machines, 3 products, 4 materials, 2 warehouses, 3 suppliers |

## Controlled local sample hashes

| Dataset | Rows | SHA-256 |
| --- | ---: | --- |
| `production_events.jsonl` | 168 | `d080144473f757c435a5f2f1151001f1cd7de3b1ed44a7ed53680b074d975483` |
| `inventory_levels.csv` | 72 | `dcf350befc3fd06b3545b23c852230eacb2b82b870dd17a60de4111af4dc63eb` |
| `sales_orders.csv` | 180 | `2c6042fca0499c01b8a810b340dc9571f2a8b8e5a9c89a8d5ca2cacd806274c9` |
| `quality_checks.csv` | 168 | `7aa6d5f6bbd0b21c0065ee4452008a93eff82d9f9cc572d0b836df18b94422de` |
| `equipment_health.jsonl` | 504 | `b40760fcbc55ea3864d65c486b93717958e702ee975041296a6d1c28368c44b1` |
| `warehouse_movements.csv` | 220 | `a431b9f39b1136dec1514db7710ad36990f21b89e1e066566b6611b9e5768b61` |
| `supplier_performance.csv` | 120 | `8f4746a5169034cc1803f855e7be607c48c04dac9b7f4a28a837159371a590f3` |

## Generated-data tracking policy

The small deterministic local sample under `data/raw/` is intentionally tracked as portfolio evidence. Larger, run-specific, CI, and temporary generated runs are excluded through `.gitignore`; the CI profile writes to `.generated/ci/raw/`.

## Overwrite behaviour

Generator calls refuse to overwrite managed generated files by default. `make generate-data` and `make generate-data-ci` pass explicit overwrite flags for controlled regeneration. Unrelated files in an output directory are not deleted by overwrite.

## Deterministic timestamp strategy

Generation timestamps are read from configuration rather than wall-clock time. This keeps controlled local and CI outputs reproducible.

## Acceptance-criteria checklist

- [x] Seven required raw datasets are generated.
- [x] Generation is deterministic from configuration.
- [x] Cross-dataset entity identifiers are consistent.
- [x] Schema metadata is produced.
- [x] Generation manifest is produced.
- [x] Generation summary is produced.
- [x] CLI/script entry point is available.
- [x] Dedicated CI generation profile is available.
- [x] Existing-run validation is available and does not regenerate data.
- [x] Overwrite protection is implemented and tested.
- [x] Manifest integrity is independently tested.
- [x] Schema registry completeness is tested.
- [x] Documentation distinguishes generated raw data from future ingestion and analytics.
- [x] Structure checks pass.
- [x] Unit tests pass.
- [x] Linting passes.
- [x] Formatting checks pass.
- [x] Static type checking passes.
- [x] Git diff whitespace check passes.

## Synthetic-data confirmation

All generated records are synthetic and must not represent real people, customers, suppliers, employees, plants, products, or commercial operations.

## Azure deployment confirmation

No Azure resources are deployed, configured, called, or required in Milestone 2.

## Commit and push confirmation

No commit or push was performed during the Milestone 2 review corrections.
