# Quality Limitations

Milestone 6 is synthetic-only, deterministic, and local-first.

Known limitations:

- First-pass yield is a proxy because explicit rework fields are unavailable.
- Isolation Forest scores are retrospective diagnostics, not operational
  probabilities.
- Robust z-score and SPC signals require sufficient comparable history.
- Capability metrics are calculated only where group size and specification-limit
  stability support them.
- Investigation context is not root-cause analysis.
- No dashboards, Power BI files, GenAI, predictive maintenance, live streaming,
  Azure SDK clients, databases, Terraform, Bicep, or cloud deployments are
  implemented.

Milestone 7 predictive maintenance remains deferred.
