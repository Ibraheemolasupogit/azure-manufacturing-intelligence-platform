# Milestone 6 - Quality Analytics And Anomaly Detection

## Objective

Build a deterministic, governed, local-first quality analytics and anomaly
detection pipeline from accepted quality checks and production events.

## Scope Delivered

- Governed quality and production input loading.
- Upstream ingestion manifest, validation summary, data-quality report, lineage,
  hash, and row-count verification.
- Specification compliance and source-result consistency checks.
- Quality KPIs, production-yield metrics, scrap rate, and labelled first-pass-yield
  proxy.
- Defect Pareto analysis by category, severity, product, plant, line, machine,
  batch, and metric.
- Process capability diagnostics where comparable groups have sufficient history.
- Expanding prior-observation control-chart baselines.
- SPC rules `SPC_RULE_1` through `SPC_RULE_4`.
- Robust z-score anomaly scoring.
- Deterministic Isolation Forest batch anomaly diagnostics.
- Quality-risk scoring, deterministic quality alerts, and investigation context.
- Quality manifest, diagnostics, lineage, reports, CLI, Makefile targets, CI
  integration, and existing-run validation.

## Scope Boundaries

Milestone 6 does not implement predictive maintenance, equipment failure
prediction, maintenance scheduling, production optimisation, GenAI, dashboards,
Power BI files, live streaming, databases, Azure SDK clients, Terraform, Bicep, or
cloud deployment.

## Governed Inputs

| Input | Rows | SHA-256 |
| --- | ---: | --- |
| `data/interim/accepted/quality_checks.csv` | 168 | `7aa6d5f6bbd0b21c0065ee4452008a93eff82d9f9cc572d0b836df18b94422de` |
| `data/interim/accepted/production_events.jsonl` | 168 | `d080144473f757c435a5f2f1151001f1cd7de3b1ed44a7ed53680b074d975483` |

- Upstream ingestion run ID: `INGEST-da9a11a67abc6a18`
- Quality run ID: `QUALITY-ea15caf8c05763b0`
- Principal alert grain: `inspection_id`
- Trend grain: `product_id + quality_metric + inspection_date`
- Control/anomaly grain: `machine_id + quality_metric + measurement_unit`

## Methods

- Specification: compare measured value to record-level lower and upper limits.
- Yield: `accepted_quantity / produced_quantity`; first-pass yield is labelled as a
  proxy because explicit rework fields are unavailable.
- Pareto: failed inspections or rows with defective units only, with stable
  descending ordering and deterministic ties.
- Capability: Cp and Cpk only for comparable product, metric, unit, plant, and line
  groups with stable limits and at least 10 observations.
- Control charts: expanding historical prior-observation mean and standard
  deviation; operational alert baselines avoid future observations.
- SPC: rules 1-4 implemented with stable rule codes and triggering windows.
- Robust z-score: `0.6745 * (x - median) / MAD` with insufficient-history and
  zero-MAD fallback statuses.
- Isolation Forest: deterministic `random_state`, 50 estimators, configured
  contamination, numeric quality/production context features, retrospective batch
  diagnostic score, not a probability.
- Risk scoring: 0-100 deterministic weighted score from specification failure,
  SPC signal, anomaly score, and defect severity.

## Controlled Results

- Quality records processed: 168
- Specification failures: 26
- Near-limit observations: 5
- SPC signals by rule: `SPC_RULE_1=5`, `SPC_RULE_2=1`, `SPC_RULE_3=1`
- Robust-z anomaly count: 2
- Isolation Forest anomaly count: 12
- Alert rows: 38
- High-risk alert count: 6
- Critical-risk alert count: 4
- Top alert context: deterministic investigation context only; no root-cause claim.

## Controlled Output Hashes

| Output | Rows | SHA-256 |
| --- | ---: | --- |
| `outputs/quality_alerts.csv` | 38 | `36a15ebb31519685fa717e5581af27ca246f1ced09ebf50001b7d05873b2b89f` |
| `outputs/quality/quality_observations.csv` | 168 | `d2b694a9f88650216bca0533efcf887c3be98d5560c7c1e00f830ba7818a9515` |
| `outputs/quality/quality_kpis.csv` | 27 | `88b905775e39fa508f03687d3ce99ffe09e27846d0c2dc89148c5d8321dba947` |
| `outputs/quality/defect_pareto.csv` | 51 | `469ddfea42f5b53cf9cbdeedfde331778859eeddec80b6b119e2b5dc09d1ac52` |
| `outputs/quality/process_capability.csv` | 48 | `03c236178389d6886caf5f30848ce6df6e31ed4eb84cd3964e60b768d598dd52` |
| `outputs/quality/control_chart_points.csv` | 168 | `c5c0b9f4e244e4a47be6f9f97c6a029b384c47f05730aca8cdd0563ee73c070b` |
| `outputs/quality/spc_signals.csv` | 168 | `3eed8cf7a2312fc2c42a5f3a79dcd227e8ba3da1d7b6c95bdb3d77c72c62fe87` |
| `outputs/quality/anomaly_scores.csv` | 168 | `3f903706b8e0e47bb2c3af7792a0eedc7867e57ca35b374bd69ce390b07d6a0a` |
| `outputs/quality/quality_alerts.csv` | 38 | `36a15ebb31519685fa717e5581af27ca246f1ced09ebf50001b7d05873b2b89f` |
| `outputs/quality/quality_risk_summary.csv` | 4 | `e42b49cafeb118107991611d0d5a7e82f82289437ba75abe032d97f66a0ea87c` |
| `outputs/quality/quality_diagnostics.json` | n/a | `cd3b7f05c11cedfa5cf0710477a643bcf095a277ca087fad1d7418a5a0f574e8` |
| `outputs/quality/quality-manifest.json` | n/a | `43513e01d755a6c861e0a53fd414baef88b6580bc0aaa480d41a6c446d7958bf` |
| `outputs/quality/lineage-records.json` | n/a | `6478cf8dc97c95c54a216df9f70dd77a27970f2e182b80e281ad7da7624064d6` |
| `reports/quality_analytics_report.md` | n/a | `21a4617fd8186ac74d34e228a41a4149db80a5ef3a6caf0fc3362187a2a41a5a` |
| `reports/quality_alert_summary.md` | n/a | `fb08a509d28f67d8dd3119c1b5fd2f2ad44a291d03fdd9f4d560d0d71f05943d` |

## Manifest And Lineage

The manifest records relative paths, governed input hashes, input row counts,
upstream ingestion run ID, analysis grains, specification settings, SPC settings,
capability settings, anomaly settings, risk settings, output evidence, KPI
summary, alert summary, warnings, synthetic classification, Git commit, and
reference-only Azure mapping.

Lineage records show governed quality checks and production events flowing into
quality observations, KPIs, Pareto, capability, control charts, SPC, anomaly
scores, risk summary, alerts, reports, diagnostics, and portfolio alert output. No
Microsoft Purview registration is claimed.

## Commands Executed

- `git fetch origin main`
- `git status --short --branch`
- `git log -5 --oneline`
- `make quality`
- `make validate-generation`
- `make validate-ingestion`
- `make validate-forecast`
- `make validate-inventory`
- `python3 -m manufacturing_intelligence.quality --config configs/quality_ci.yaml --overwrite`
- `python3 -m manufacturing_intelligence.quality --config configs/quality_ci.yaml --validate-existing-run --output-directory .generated/ci/quality`
- `make quality-analytics`
- `make validate-quality-analytics`
- `make quality-analytics-ci`
- `python3 -m manufacturing_intelligence.quality --config configs/quality_ci.yaml --validate-config-only`
- `python3 -m manufacturing_intelligence.quality --config configs/quality_ci.yaml --validate-existing-run --output-directory .generated/ci/quality`
- `python3 -m ruff check src/manufacturing_intelligence/quality tests/unit/test_quality_pipeline.py`
- `python3 -m pytest tests/unit/test_quality_pipeline.py`
- `python3 -m mypy src/manufacturing_intelligence/quality`

## Current Validation Results

- Structure check baseline: `Repository structure check passed.`
- Ruff baseline: `All checks passed!`
- Formatting result: `99 files already formatted`
- Mypy result: `Success: no issues found in 89 source files`
- Pytest result: `77 passed in 18.95s`
- Coverage result: 83%
- Focused quality Ruff: `All checks passed!`
- Focused quality mypy: `Success: no issues found in 18 source files`
- Focused quality pytest: `8 passed in 7.17s`
- Local quality analytics: `Quality QUALITY-ea15caf8c05763b0 processed 168 rows and wrote 38 alerts`
- Existing-run validation: `Existing quality analytics run is valid.`
- CI quality analytics: `Quality QUALITY-ea15caf8c05763b0 processed 168 rows and wrote 38 alerts`
- CI config validation: `Quality config valid`
- CI existing-run validation: `Existing quality analytics run is valid.`

## Known Limitations

- First-pass yield is a proxy because rework fields are unavailable.
- Isolation Forest scores are retrospective diagnostics, not probabilities.
- Robust z-score, capability, and SPC require sufficient comparable history.
- Investigation context does not prove root cause.

## Acceptance Checklist

- [x] Governed quality data is used.
- [x] Governed production context is used.
- [x] Upstream manifests, hashes, and row counts are verified.
- [x] Upstream inputs are preserved.
- [x] Analysis grains are documented.
- [x] Specification compliance, KPIs, Pareto, capability, control charts, SPC,
  anomaly scores, risk scores, and alerts are produced.
- [x] Existing-run validation detects tampering.
- [x] CLI, Makefile, CI, tests, docs, manifest, lineage, and reports are present.
- [x] Milestone 7 predictive maintenance is deferred.
- [x] All data remains synthetic.
- [x] No Azure resources are deployed or called.
- [x] No commit or push occurred.
