# Quality Lineage And Manifest

Milestone 6 writes:

- `outputs/quality/quality-manifest.json`
- `outputs/quality/lineage-records.json`
- `outputs/quality/quality_diagnostics.json`

The manifest records the quality run ID, semantic configuration hash, governed
input paths, hashes, row counts, upstream ingestion run ID, analysis grains,
specification settings, SPC settings, capability settings, anomaly settings, risk
settings, output evidence, KPI summary, alert summary, warnings, synthetic
classification, git commit, and reference-only Azure mapping.

Lineage records show accepted quality checks and production events flowing into
specification evaluation, KPIs, Pareto analysis, capability diagnostics, control
charts, SPC, anomaly scores, risk scores, alerts, reports, and portfolio output.

No Microsoft Purview registration is claimed.
