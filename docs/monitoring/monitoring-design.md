# Monitoring Design

Milestone 8 implements deterministic local monitoring over governed evidence from Milestones 2 through 7. It reads tracked manifests, outputs, diagnostics, reports, and lineage metadata, then produces platform health summaries, domain health scores, evidence integrity checks, lineage completeness checks, monitoring alerts, reports, manifest, and monitoring lineage.

The controlled monitoring run is `MONITOR-6a22c0e7c78c0641`. It scored platform health at `98.666667` with a `healthy` label. Monitoring is local portfolio evidence only; it does not deploy Azure Monitor, Log Analytics, Application Insights, Azure Data Explorer, Azure ML monitoring, Microsoft Purview, or Power BI.
