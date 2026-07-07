# Quality Analytics Design

Milestone 6 adds deterministic, governed, local-first quality analytics over
accepted quality checks and production events. It consumes only Milestone 3
accepted data and ingestion evidence, then writes quality observations, KPIs,
Pareto summaries, process capability diagnostics, control-chart points, SPC
signals, anomaly scores, quality alerts, manifests, lineage, and Markdown reports.

Run locally with:

```bash
python -m manufacturing_intelligence.quality --config configs/quality.yaml --overwrite
```

The pipeline sequence is:

1. Verify governed input hashes, row counts, manifests, validation summaries, data
   quality evidence, lineage, synthetic classification, timestamps, specification
   limits, and reference resolution.
2. Evaluate specification compliance per `inspection_id`.
3. Join production context by `batch_id`.
4. Calculate quality KPIs and first-pass-yield proxy metrics.
5. Build defect Pareto summaries.
6. Calculate process capability only for comparable product, metric, unit, plant,
   and line groups with enough observations.
7. Calculate expanding historical control-chart baselines and SPC signals.
8. Score robust z-score and deterministic Isolation Forest anomaly diagnostics.
9. Score quality risk and produce deterministic investigation alerts.
10. Write manifests, lineage, diagnostics, reports, and portfolio alert output.

No Azure SDKs, databases, dashboards, GenAI, live streaming, deployment templates,
or predictive-maintenance logic are included.
