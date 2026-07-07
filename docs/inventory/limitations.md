# Inventory Limitations

Inventory recommendations are deterministic decision-support evidence from
synthetic data. They are not operational instructions for a real manufacturer.

The tracked demand forecast is based on a 14-day synthetic sample, so inventory
coverage and reorder recommendations are smoke evidence. Product demand is sourced
from allocated governed forecasts. Material demand is inferred from
issue-to-production warehouse movements because no material forecast or
bill-of-materials model exists in Milestone 5.

Known limitations:

- Supplier risk is inferred from synthetic supplier performance rows and does not
  represent real suppliers.
- Constrained allocation is deterministic greedy prioritisation, not mixed-integer
  optimisation.
- Demand allocation uses recent warehouse movement shares or equal warehouse
  fallback when movement evidence is unavailable.
- Forecast history is intentionally small because Milestone 4 uses a synthetic
  smoke portfolio.
- Azure services are mapped as future responsibilities only.

Milestone 5 does not implement production scheduling, manufacturing-line
optimisation, quality analytics, predictive maintenance, dashboards, GenAI, live
optimisation services, databases, Azure SDK clients, Terraform, Bicep, or cloud
deployment.
