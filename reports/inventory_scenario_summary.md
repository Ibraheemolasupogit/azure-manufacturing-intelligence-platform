# Inventory Scenario Summary

- Inventory run ID: `INVENTORY-5a5cc7e83afe8502`
- Scenario count: 5

| Scenario | Shortage qty | Excess qty | Recommended qty | Working capital | Budget use | Capacity use |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 11813.69 | 12740.00 | 8598.00 | 999987.00 | 1.0000 | 0.0860 |
| budget_constrained | 11813.69 | 12740.00 | 4433.00 | 349952.00 | 0.9999 | 0.0443 |
| capacity_constrained | 11813.69 | 12740.00 | 8598.00 | 999987.00 | 1.0000 | 0.1720 |
| high_demand | 14509.86 | 12740.00 | 8598.00 | 999987.00 | 1.0000 | 0.0860 |
| supplier_delay | 11813.69 | 12740.00 | 8598.00 | 999987.00 | 1.0000 | 0.0860 |

## Interpretation

- Baseline uses the configured demand, supplier, budget, and capacity assumptions.
- High-demand, supplier-delay, budget, and capacity scenarios apply deterministic multipliers to the same synthetic governed inputs.
