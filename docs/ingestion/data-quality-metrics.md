# Data-Quality Metrics

Milestone 3 emits machine-readable and human-readable data-quality evidence for every run.

## Metadata outputs

- `validation-summary.json`: source, accepted, and quarantine counts by dataset; quarantine rate; severity and rule-code counts; source hash verification status.
- `quarantine-summary.json`: quarantine threshold evidence and rule distribution.
- `data-quality-report.json`: dataset-level completeness, acceptance, quarantine, duplicate, and issue metrics.
- `reports/data_quality_report.md`: compact Markdown summary for portfolio review.

## Interpreting the tracked run

The committed local sample is expected to produce zero quarantined records. A non-zero quarantine count in strict mode indicates either raw-data drift, schema drift, or an ingestion-rule regression.

## Limitations

These metrics are validation evidence for synthetic local data. They are not production service-level indicators and do not claim real manufacturing quality, supplier performance, or operational health.
