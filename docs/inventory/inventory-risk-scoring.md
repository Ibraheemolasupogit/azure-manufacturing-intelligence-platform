# Inventory Risk Scoring

Inventory risk scores are deterministic 0-100 measures written in
`outputs/inventory/inventory_scores.csv`.

The scoring dimensions are:

- Stockout risk, driven by projected shortage under the upper forecast bound and
  supplier risk exposure.
- Excess risk, driven by inventory position above configured excess coverage days.
- Supplier risk, driven by observed supplier delay, fill, quality, rejection, and
  lead-time variability metrics.
- Expiry risk, driven by expiry date, projected demand before expiry, and remaining
  quantity at expiry.
- Working capital risk, driven by on-hand quantity times unit cost.

Overall priority combines those dimensions:

```text
overall_priority_score =
  stockout_risk_score * 0.50
  + supplier_risk_score * 0.15
  + expiry_risk_score * 0.10
  + working_capital_risk_score * 0.15
  + excess_risk_score * 0.10
```

Priority labels are:

- `critical`: score greater than or equal to 75
- `high`: score greater than or equal to 50 and below 75
- `medium`: score greater than or equal to 25 and below 50
- `low`: score below 25
