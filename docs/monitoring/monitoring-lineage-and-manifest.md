# Monitoring Lineage and Manifest

`outputs/monitoring/monitoring-manifest.json` records the monitoring run ID, configuration hash, monitored domains, input hashes, output evidence, domain scores, platform score, alert counts, warnings, Git commit, synthetic classification, and upstream immutability confirmation.

`outputs/monitoring/lineage-records.json` records local lineage from generation, ingestion, forecast, inventory, quality, and maintenance evidence into monitoring outputs.

The manifest and lineage use relative paths and deterministic hashes. No Azure registration or cloud deployment is claimed.
