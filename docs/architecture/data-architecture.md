# Data Architecture

Reference architecture only. No Azure resource, Power BI workspace, Fabric item, credential, deployment, or live service validation is created by this repository.

- Raw, accepted, curated, dashboard, evidence, and manifest zones map to ADLS Gen2, Synapse/Fabric, Power BI, and Purview responsibilities.
- Schema evolution, retention, lineage, and data-quality gates are local documentation boundaries.
- No external data source or production customer data is used.
