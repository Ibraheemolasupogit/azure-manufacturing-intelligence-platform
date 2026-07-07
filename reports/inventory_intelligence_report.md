# Inventory Intelligence Report

- Inventory run ID: `INVENTORY-5a5cc7e83afe8502`
- Evaluated item-location rows: 72
- Recommendation rows: 72
- Total working-capital exposure: 1077719.70
- Total recommended reorder value: 999972.00
- Projected shortage quantity: 11813.69
- Projected excess quantity: 12740.00
- Budget utilisation: 1.0000
- Capacity utilisation: 0.0929

## Top Recommendations

| Priority | Item | Warehouse | Action | Recommended qty | Risk score | Constraint |
| --- | --- | --- | --- | ---: | ---: | --- |
| high | MAT-004 | WH-02 | expedite_replenishment | 510 | 57.73 | fully_allocated |
| high | MAT-002 | WH-02 | expedite_replenishment | 450 | 57.67 | fully_allocated |
| high | MAT-010 | WH-02 | expedite_replenishment | 560 | 57.32 | fully_allocated |
| high | MAT-008 | WH-02 | expedite_replenishment | 680 | 57.12 | fully_allocated |
| high | MAT-006 | WH-02 | expedite_replenishment | 800 | 56.98 | fully_allocated |
| medium | PROD-008 | WH-02 | expedite_replenishment | 635 | 44.28 | partially_allocated_constraint_binding |
| medium | PROD-004 | WH-02 | expedite_replenishment | 1920 | 43.47 | fully_allocated |
| medium | PROD-006 | WH-02 | expedite_replenishment | 2130 | 42.99 | fully_allocated |
| medium | PROD-002 | WH-02 | expedite_replenishment | 1600 | 41.31 | fully_allocated |
| medium | PROD-003 | WH-03 | place_replenishment_order | 0 | 39.69 | not_allocated_constraint_binding |
| medium | PROD-008 | WH-04 | place_replenishment_order | 0 | 38.06 | not_allocated_constraint_binding |
| medium | PROD-006 | WH-04 | place_replenishment_order | 0 | 36.11 | not_allocated_constraint_binding |
| medium | PROD-007 | WH-03 | place_replenishment_order | 0 | 35.87 | not_allocated_constraint_binding |
| medium | PROD-004 | WH-04 | place_replenishment_order | 0 | 35.85 | not_allocated_constraint_binding |
| medium | PROD-002 | WH-04 | place_replenishment_order | 0 | 34.42 | not_allocated_constraint_binding |
| medium | PROD-001 | WH-03 | place_replenishment_order | 0 | 34.05 | not_allocated_constraint_binding |
| medium | PROD-005 | WH-03 | place_replenishment_order | 0 | 33.17 | not_allocated_constraint_binding |
| medium | MAT-009 | WH-01 | rebalance_or_reduce_excess_stock | 0 | 25.83 | fully_allocated |
| medium | MAT-009 | WH-03 | rebalance_or_reduce_excess_stock | 0 | 25.00 | fully_allocated |
| low | MAT-003 | WH-01 | rebalance_or_reduce_excess_stock | 0 | 24.57 | fully_allocated |

## Assumptions

- Outputs are deterministic local recommendations from synthetic governed data.
- Demand is allocated to warehouses before inventory policy scoring.
- Constrained allocation is deterministic greedy prioritisation, not a cloud solver.
- No Azure services are deployed or called by this milestone.
