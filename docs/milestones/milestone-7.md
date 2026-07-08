# Milestone 7 - Predictive Maintenance and Equipment Failure Risk

## Objective

Build a deterministic, governed, local-first predictive-maintenance pipeline using synthetic accepted equipment-health and production-context data.

## Delivered scope

Implemented governed input loading, upstream manifest/hash checks, threshold compliance, runtime/service proxies, degradation features, robust z-score, deterministic Isolation Forest diagnostics, failure-risk scoring, equipment-health scoring, maintenance alerts, summaries, reports, diagnostics, manifest, lineage, existing-run validation, CLI, Make targets, CI hooks, tests, documentation, and tracked portfolio evidence.

## Governed inputs

- Equipment health: `data/interim/accepted/equipment_health.jsonl`
- Production events: `data/interim/accepted/production_events.jsonl`
- Optional quality checks: `data/interim/accepted/quality_checks.csv`
- Optional quality alerts: `outputs/quality/quality_alerts.csv`
- Upstream ingestion run ID: `INGEST-da9a11a67abc6a18`
- Upstream quality run ID: `QUALITY-ea15caf8c05763b0`

## Input hashes and row counts

- Equipment health: 504 rows, `b40760fcbc55ea3864d65c486b93717958e702ee975041296a6d1c28368c44b1`
- Production events: 168 rows, `d080144473f757c435a5f2f1151001f1cd7de3b1ed44a7ed53680b074d975483`
- Quality checks: 168 rows, `7aa6d5f6bbd0b21c0065ee4452008a93eff82d9f9cc572d0b836df18b94422de`
- Quality alerts: 38 rows, `36a15ebb31519685fa717e5581af27ca246f1ced09ebf50001b7d05873b2b89f`

## Results

- Maintenance run ID: `MAINT-f281a27e7d014de8`
- Equipment records processed: 504
- Warning breach count: 60
- Critical breach count: 9
- Degradation signal count: 59
- Robust-z anomaly count: 0
- Isolation Forest anomaly count: 0
- High-risk alert count: 7
- Critical-risk alert count: 0
- Total alert count: 135

Top alert: `MA-743563a7e40b` for `EH-000477` on `MACH-01-02-02` vibration, high risk score `76.370676`. Investigation context includes repeated machine breaches, degradation signal, high runtime/service proxy, maintenance state, recent production downtime, and quality context; it is explicitly investigative and not causal proof.

## Output hashes

- `outputs/maintenance/equipment_health_features.csv`: `9bc11958eb1935c4f60cc976db9db355bb42cca794b03deae6c9119ec3e3bfbb`
- `outputs/maintenance/equipment_health_scores.csv`: `c56e02d876633fa6b951ffeb0a5e10ba0f15a471a6cd83dff3a110bbf2a383a0`
- `outputs/maintenance/maintenance_alerts.csv`: `4726b4d5fd0f7adc50178e5339c9b97df748192680050fa5fdcbdb622e3253d7`
- `outputs/maintenance/machine_health_summary.csv`: `b4ad807679ddb29d1067dacefd3b5764d8c2f03c47c5df1d0e40f4968d50f284`
- `outputs/maintenance/sensor_health_summary.csv`: `910008d252e5405b6cc1f2ae7016004930c3f3f4d3bc1ab23a5eaea0cda25816`
- `outputs/maintenance/degradation_signals.csv`: `586c40a1bd5d60c45b383173909e3f071a39c2d035d382fc47fa46f6fe5e27ae`
- `outputs/maintenance/anomaly_scores.csv`: `393d8c3a59243c0795df34911b5e7c45f5376b1c6bd9b7106758fb4add7b6a4a`
- `outputs/maintenance/maintenance_risk_summary.csv`: `e4efeee4a7afeb781fe752d0119dd2ca7a6f7172ad8f24fe88853330737e9b49`
- `outputs/maintenance_predictions.json`: `40fe283cd2cabc7f1acddccf8ebd0605dddfcee0de9deefa4ffe5cefec8807e9`

## Commands executed

- `git fetch origin main`: passed
- `git status --short --branch`: `## main...origin/main`
- `git log -6 --oneline`: top commit `685ad8e Add governed quality analytics and anomaly detection`
- Initial `make quality`: passed before implementation; 77 tests passed with 83% coverage
- `make validate-generation`: passed
- `make validate-ingestion`: passed
- `make validate-forecast`: passed
- `make validate-inventory`: passed
- `make validate-quality-analytics`: passed
- Final `make quality`: passed; structure check passed; Ruff passed; format check reported 115 files already formatted; mypy reported success across 104 source files; pytest reported 87 passed with 82% coverage
- Final `python3 -m manufacturing_intelligence.maintenance --config configs/maintenance.yaml --overwrite`: passed; `MAINT-f281a27e7d014de8` processed 504 rows and wrote 135 alerts
- Final `make validate-maintenance`: passed; existing maintenance run is valid
- Final `make maintenance-ci`: passed; `MAINT-a304b3cda3e547f8` processed 504 rows and wrote 135 alerts under `.generated/ci/maintenance`, then existing CI run validation passed
- `python3 -m manufacturing_intelligence.maintenance --config configs/maintenance_ci.yaml --validate-config-only`: passed
- `git diff --check`: passed

## Acceptance notes

Upstream inputs were not modified. All data is synthetic. No Azure resource was deployed or called. No dashboard, GenAI, streaming, database, or Milestone 8 monitoring work was started. No commit or push occurred.
