# Anomaly Detection

Milestone 6 implements two deterministic anomaly methods.

Robust z-score uses prior historical observations in comparable groups:

```text
robust_z = 0.6745 * (x - median) / MAD
```

If history or MAD is insufficient, the row records a fallback status and no robust
z-score alert is emitted.

Isolation Forest uses deterministic `random_state`, modest model size, and numeric
features derived from measurement position, specification margins, sample size,
defective-unit rate, cycle-time ratio, and production yield. Scores are
retrospective batch diagnostics, not probabilities.

Anomaly scores are kept separate from specification failures and SPC signals.
