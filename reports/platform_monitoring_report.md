# Platform Monitoring Report

Monitoring run ID: `MONITOR-6a22c0e7c78c0641`
Platform health score: 98.666667
Platform health label: `healthy`

These are deterministic local observability checks over synthetic governed evidence. They are not live Azure Monitor telemetry or formal SLA measurements.

## Domain health

| domain | health_score | health_label | deductions |
| --- | --- | --- | --- |
| forecasting | 100.0 | healthy |  |
| generation | 100.0 | healthy |  |
| ingestion | 100.0 | healthy |  |
| inventory | 100.0 | healthy |  |
| maintenance | 100.0 | healthy |  |
| quality | 92.0 | healthy | quality_critical_alerts=4 |

## Monitoring alerts

| severity | domain | alert_type | affected_artifact | message |
| --- | --- | --- | --- | --- |
| info | platform | monitoring_completed | all_domains | All required monitoring checks completed without warning or critical alerts. |
