# Monitoring Alerts

Monitoring alerts are deterministic and include run ID, alert ID, domain, severity, alert type, artifact, observed value, threshold, message, recommended action, and synthetic-data flag.

Alert severities are `info`, `warning`, and `critical`. Alert IDs are stable hashes of run ID, domain, severity, alert type, and affected artifact.

The controlled run generated one informational alert: all required monitoring checks completed without warning or critical alerts.
