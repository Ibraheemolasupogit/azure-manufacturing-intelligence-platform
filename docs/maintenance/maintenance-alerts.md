# Maintenance Alerts

Alerts are generated for high or critical risk records and for notable threshold, anomaly, degradation, or near-threshold conditions. Alert IDs are deterministic hashes of the maintenance run ID and `sensor_event_id`.

Each alert includes source and calculated threshold status, consistency flag, warning and critical breach flags, near-threshold flag, robust-z score, Isolation Forest score, anomaly flags, degradation score, runtime risk, maintenance state, failure-risk score, equipment-health score, priority, recommended action, recommendation reason, investigation context, and synthetic-data flag.

Investigation context is analytical context only. It may include repeated breaches, sensor anomalies, trend signals, runtime/service proxies, production downtime, and quality alerts, but it does not claim proven root cause.
