# Demand Allocation

The demand forecast is produced at product and distribution-region grain in
Milestone 4. Milestone 5 allocates that demand to warehouse-product rows before
inventory scoring so totals are not duplicated across warehouses.

For each forecast row:

```text
allocated_point_forecast = point_forecast * allocation_weight
allocated_lower_bound = lower_bound * allocation_weight
allocated_upper_bound = upper_bound * allocation_weight
```

Allocation weights are derived from recent accepted warehouse movements for the
same product where possible. If no movement evidence is available for a product,
the pipeline falls back to equal allocation across warehouses carrying that product
in accepted inventory.

The generated `outputs/inventory/warehouse_demand_forecast.csv` preserves the
forecast run ID, product ID, distribution region, forecast date, horizon day,
selected model, allocation method, allocation weight, and allocated forecast
intervals. Tests verify allocated point forecast totals match the upstream demand
forecast total.
