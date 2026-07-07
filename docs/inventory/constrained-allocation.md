# Constrained Allocation

Milestone 5 applies a deterministic constrained allocation pass after
unconstrained policy recommendations are calculated.

The configured limits are:

- `optimisation.available_budget`
- `optimisation.available_replenishment_capacity`

Rows are sorted by priority level, objective score, warehouse ID, and item ID. The
allocation then greedily approves reorder quantities while respecting remaining
budget and capacity.

```text
approved_quantity <= unconstrained_reorder_quantity
approved_quantity * unit_cost <= remaining_budget
approved_quantity <= remaining_capacity
```

The output `outputs/inventory/reorder_recommendations.csv` records unconstrained
quantity, recommended constrained quantity, recommended value, unmet quantity,
unmet value, constraint status, objective score, action, reason, and priority.

The manifest explicitly labels this method as deterministic greedy allocation and
does not claim exact global optimisation.
