# Data Zones

The local data layout mirrors governed lakehouse zones without requiring Azure storage.

| Zone | Purpose | Milestone 1 status |
| --- | --- | --- |
| `data/raw/` | Immutable synthetic source extracts and event files. | Directory scaffold only |
| `data/interim/` | Intermediate validated or transformed data. | Directory scaffold only |
| `data/processed/` | Analytics-ready local outputs for later pipelines. | Directory scaffold only |

No datasets are generated in Milestone 1. Future data must be synthetic and must not represent real employees, customers, suppliers, or commercially sensitive operations.
