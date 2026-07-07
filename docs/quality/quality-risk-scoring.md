# Quality Risk Scoring

Quality-risk scores are deterministic 0-100 heuristic scores. They are not
calibrated probabilities.

Configured components:

```text
quality_risk_score =
  specification_failure_component * 0.40
  + spc_signal_component * 0.25
  + anomaly_component * 0.20
  + defect_severity_component * 0.15
```

Risk labels:

- `critical`: score greater than or equal to configured critical threshold.
- `high`: score greater than or equal to configured high threshold.
- `medium`: score greater than or equal to 30.
- `low`: score below 30.

Alerts include deterministic recommended actions and investigation context. The
context highlights repeated failures, affected product, machine, batch, defect
category, near-limit state, and downtime presence where available. It is not a
root-cause claim.
