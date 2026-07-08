# Health Scoring

Monitoring health scores are deterministic 0-100 heuristics. Domains start at 100 and receive transparent deductions for failed integrity checks, lineage gaps, validation failures, quarantine rate issues, or excessive warning and high-risk alert counts.

Labels are:

- `healthy`
- `watch`
- `degraded`
- `critical`

The controlled domain scores are generation 100, ingestion 100, forecasting 100, inventory 100, quality 92, maintenance 100. The overall platform score is the mean domain score. Scores are not formal SLA measurements.
