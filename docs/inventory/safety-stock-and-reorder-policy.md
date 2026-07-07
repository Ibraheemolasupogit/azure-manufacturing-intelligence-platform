# Safety Stock And Reorder Policy

The policy is rules-based and deterministic. It is intended as a governed local
decision-support layer, not an exact optimisation solver.

The main formulas are:

```text
z = service_factor(default_service_level)
safety_stock = ceil(z * demand_std * sqrt(lead_time_days) * supplier_multiplier)
lead_time_demand = average_daily_demand * lead_time_days
reorder_point = ceil(lead_time_demand + safety_stock)
target_stock_level = reorder_point + average_daily_demand * review_period_days
inventory_position = on_hand + inbound - reserved - committed_outbound
raw_reorder_gap = target_stock_level - inventory_position
```

The reorder quantity clips negative gaps to zero, applies minimum order quantity,
rounds to the configured order multiple, and caps by maximum reorder quantity.

Product demand uses allocated forecast demand. Material demand uses accepted
`issue_to_production` warehouse movements because no bill-of-materials model is in
scope for Milestone 5.
