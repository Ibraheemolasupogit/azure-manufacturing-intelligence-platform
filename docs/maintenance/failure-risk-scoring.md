# Failure Risk Scoring

Failure-risk scoring is a transparent 0-100 heuristic. It combines threshold breach, anomaly, degradation, runtime/service proxy, maintenance-state, and production-context component scores using configured weights that sum to 1.0.

Equipment-health score is `100 - failure_risk_score`, clipped to 0-100. Risk levels are `low`, `medium`, `high`, and `critical`; high begins at 60 and critical begins at 80 in the controlled configuration.

Scores are deterministic decision-support indicators. They are not calibrated probabilities, safety certifications, or operationally binding maintenance instructions.
