# Anomaly Detection

Maintenance anomaly detection implements robust z-score and deterministic Isolation Forest diagnostics. Robust z-score uses:

```text
0.6745 * (x - median) / MAD
```

The baseline is evaluated within comparable `machine_id + sensor_type + measurement_unit` groups. Zero-MAD and insufficient-history cases are labelled explicitly. Isolation Forest uses a fixed random seed and modest model size. Its score is a relative anomaly diagnostic, not a calibrated failure probability.

The controlled run produced 0 robust-z anomalies and 0 Isolation Forest anomalies. This reflects the configured threshold and synthetic sample distribution, not a claim of operational normality.
