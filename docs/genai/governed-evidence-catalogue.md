# Governed Evidence Catalogue

The evidence catalogue is written to `outputs/genai/evidence_catalog.json` and `outputs/genai/evidence_catalog.csv`.

Each item includes an evidence ID, domain, evidence type, relative path, title, description, row count where applicable, file size, SHA-256 hash, synthetic-data flag, upstream run ID where available, related manifest, related lineage, freshness label, supported question types, and key metrics.

Required domains are generation, ingestion, forecasting, inventory, quality, maintenance, and monitoring. Missing required evidence fails the run. Temporary `.generated` artefacts are excluded from the tracked catalogue.
