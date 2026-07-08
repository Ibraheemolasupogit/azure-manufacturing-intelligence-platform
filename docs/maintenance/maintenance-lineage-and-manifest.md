# Maintenance Lineage and Manifest

`outputs/maintenance/maintenance-manifest.json` records the deterministic run ID, configuration hash, governed input paths and hashes, row counts, upstream ingestion run ID, optional quality run ID, settings, output evidence, KPI summary, warnings, synthetic-data classification, Git commit, and upstream immutability confirmation.

`outputs/maintenance/lineage-records.json` records the transformation chain:

```text
governed equipment health + governed production events + optional quality context
-> threshold evaluation
-> equipment health KPIs
-> degradation signals
-> anomaly scores
-> failure-risk scores
-> maintenance alerts
-> machine and sensor summaries
-> reports and lineage
```

The lineage is local metadata. No Microsoft Purview registration is claimed.
