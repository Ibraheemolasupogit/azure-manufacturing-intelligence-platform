# Governed Dashboard Inputs

Dashboard outputs consume tracked governed evidence from ingestion, forecasting, inventory, quality, maintenance, monitoring, and GenAI. Required manifests are parsed, validation status is checked, hashes are verified where manifests expose them, lineage files are required, and upstream inputs are treated as immutable.

The dashboard layer does not read directly from unvalidated raw data.
