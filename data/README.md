# Data Zones

The local data layout mirrors governed lakehouse zones without requiring Azure storage.

| Zone | Purpose | Milestone 1 status |
| --- | --- | --- |
| `data/raw/` | Immutable synthetic source extracts and event files. | Deterministic Milestone 2 synthetic files |
| `data/interim/` | Intermediate validated or transformed data. | Directory scaffold only |
| `data/processed/` | Analytics-ready local outputs for later pipelines. | Directory scaffold only |

Milestone 2 generates synthetic raw files only:

- `production_events.jsonl`
- `inventory_levels.csv`
- `sales_orders.csv`
- `quality_checks.csv`
- `equipment_health.jsonl`
- `warehouse_movements.csv`
- `supplier_performance.csv`
- `schema_metadata.json`
- `generation_manifest.json`
- `generation_summary.md`

These files are generated from `configs/synthetic_data.yaml` using `make generate-data`. The local sample is intentionally committed because it is small, deterministic, and useful as portfolio evidence. Larger or run-specific outputs should be written outside `data/raw/`, preferably under ignored `.generated/`.

`configs/synthetic_data_ci.yaml` is a deliberately smaller profile for fast CI and tests. It writes to `.generated/ci/raw/` through `make generate-data-ci`.

Useful commands:

- `make generate-data`: regenerate the tracked local sample with explicit overwrite.
- `make generate-data-ci`: generate the smaller ignored CI sample.
- `make validate-generation`: validate the existing tracked sample without regenerating it.

Direct generator calls refuse to overwrite existing managed files unless `--overwrite` is provided. They must remain synthetic and must not represent real employees, customers, suppliers, or commercially sensitive operations.
