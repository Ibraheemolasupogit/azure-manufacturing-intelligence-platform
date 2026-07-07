# Scenario Analysis

Milestone 5 writes aggregate deterministic scenario results to
`outputs/inventory/scenario_results.csv` and a Markdown summary to
`reports/inventory_scenario_summary.md`.

The supported scenarios are:

- `baseline`
- `high_demand`
- `supplier_delay`
- `budget_constrained`
- `capacity_constrained`

`high_demand` applies the configured demand multiplier. `supplier_delay` applies
the configured lead-time multiplier. `budget_constrained` and
`capacity_constrained` apply configured fractions to available budget or
replenishment capacity.

Scenario outputs include total unconstrained quantity, constrained quantity,
working-capital requirement, projected shortage, projected excess, service-level
risk, high-risk item count, critical-risk item count, utilisation metrics, and
constraint-binding count.
