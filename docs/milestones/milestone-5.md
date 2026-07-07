# Milestone 5 - Inventory Intelligence And Optimisation

## Objective

Build a deterministic, governed, local-first inventory intelligence and constrained
allocation pipeline from accepted inventory, supplier, warehouse-movement, sales,
and demand-forecast evidence.

## Scope Delivered

- Governed input loading and upstream evidence verification.
- Warehouse-level demand allocation from product-region forecast outputs.
- Supplier lead-time, delivery, fill, quality, rejection, and risk metrics.
- Item-location policy inputs at `warehouse_id` plus `item_id` grain.
- Inventory position, coverage, safety-stock, reorder-point, reorder-quantity,
  stockout, excess, expiry, working-capital, supplier-risk, and priority scoring.
- Deterministic constrained allocation by configured budget and replenishment
  capacity.
- Aggregate scenario results for `baseline`, `high_demand`, `supplier_delay`,
  `budget_constrained`, and `capacity_constrained`.
- Machine-readable outputs under `outputs/inventory/` and
  `outputs/inventory_scores.csv`.
- Human-readable reports under `reports/`.
- Inventory manifest, diagnostics, and lineage records.
- CLI entry point via `python3 -m manufacturing_intelligence.inventory`.
- Make targets for `make inventory`, `make inventory-ci`, and
  `make validate-inventory`.
- Tests for governed input use, determinism, policy math, allocation totals,
  scenario evidence, existing-run validation, overwrite protection, raw-input
  rejection, and CLI execution outside the repository root.

## Scope Boundaries

Milestone 5 does not implement production scheduling, manufacturing-line
optimisation services, quality analytics, predictive maintenance, dashboards,
Power BI files, GenAI, live optimisation services, databases, Azure SDK clients,
Terraform, Bicep, or cloud deployment.

## Evidence

- Governed inventory input: `data/interim/accepted/inventory_levels.csv`
- Governed supplier input: `data/interim/accepted/supplier_performance.csv`
- Governed warehouse input: `data/interim/accepted/warehouse_movements.csv`
- Governed sales input: `data/interim/accepted/sales_orders.csv`
- Governed forecast input: `outputs/demand_forecast.csv`
- Upstream ingestion run ID: `INGEST-da9a11a67abc6a18`
- Upstream forecast run ID: `FORECAST-6357daf22de3ea43`
- Inventory run ID: `INVENTORY-5a5cc7e83afe8502`
- Inventory grain: warehouse ID and item ID
- Scored item-location rows: 72
- Warehouse demand allocation rows: 112
- Supplier risk metric rows: 10
- Recommendation rows: 72
- Scenario rows: 5
- Policy type: rules-based inventory policy
- Allocation boundary: deterministic greedy constrained allocation, no external solver
- Total working-capital exposure: 1,077,719.70 synthetic currency
- Total unconstrained reorder quantity: 23,120
- Total constrained reorder quantity: 9,285
- Total recommended reorder value: 999,972.00 synthetic currency
- Budget utilisation: 0.999972
- Capacity utilisation: 0.09285
- High-risk rows: 5
- Critical-risk rows: 0

## Controlled Output Hashes

| Output | Rows | SHA-256 |
| --- | ---: | --- |
| `outputs/inventory_scores.csv` | 72 | `c982dcaf7cd034148c08d3f4f5f4a64f8d117e771b49fc750a7047c00b7cc859` |
| `outputs/inventory/warehouse_demand_forecast.csv` | 112 | `46176ec3a7dea809d4b5d9972adce1c7cf57c44c60b196c2f205d11d9b3be32c` |
| `outputs/inventory/supplier_risk_metrics.csv` | 10 | `af1e0e7af7e7bf66862cf8f6596a91cad65f71e5e248beeeba17a62cb75ddc1a` |
| `outputs/inventory/inventory_policy_inputs.csv` | 72 | `99358e24d7f45a2aec3314c362594cb7fe5f98a29d44c81d4f025ad26168cd09` |
| `outputs/inventory/inventory_position.csv` | 72 | `bf23ae94b33b25022c5e6da79de89d52b1844d385767287120dfa42c8fd6e46e` |
| `outputs/inventory/inventory_scores.csv` | 72 | `c982dcaf7cd034148c08d3f4f5f4a64f8d117e771b49fc750a7047c00b7cc859` |
| `outputs/inventory/reorder_recommendations.csv` | 72 | `5c6cba1d1d05ee26f94c5f95f8e3df00faeec99446395f06ffc05336b530d746` |
| `outputs/inventory/scenario_results.csv` | 5 | `6e10ef97bf3fabae62ca83daf1ed15fd84023b69a758d9972ba09dddd3c3b306` |
| `outputs/inventory/inventory_summary.json` | n/a | `709a6ae7688f99b78bd6163290db89c440abb15b66cf2225188ff5a6ea976af4` |
| `outputs/inventory/inventory_diagnostics.json` | n/a | `2d57a725209edfa1aaaeb33cecffa5f1d43b2c8ad3d5e14604ecfdf728a6daec` |
| `outputs/inventory/inventory-manifest.json` | n/a | `0583c861e5c832323d62e404204f27ae23d052dad56b441e6be86c4cb5d022ee` |
| `outputs/inventory/lineage-records.json` | n/a | `6caeda1ffb886344b7b2f98226d5319d0c9dc2b2c96a27f6b5563ee23cdc4bdc` |
| `reports/inventory_intelligence_report.md` | n/a | `e7a5a3147666fc8da523fc86a5778b1d8bfb07a83e7b8710d8c950dd307c817f` |
| `reports/inventory_scenario_summary.md` | n/a | `0b60d83907e33f873d26a7e4ddc60f5188457cda6b3a0d96a4911e1d1b6d08fe` |

## Commands Executed

- `git fetch origin main`
- `git status --short --branch`
- `git rev-list --left-right --count origin/main...HEAD`
- `git log -5 --oneline`
- `make quality`
- `make validate-generation`
- `make validate-ingestion`
- `make validate-forecast`
- `make validate-inventory`
- `python3 -m pytest tests/unit/test_inventory_pipeline.py`
- `make inventory`

## Repository-State Note

Before implementation, the worktree contained uncommitted Milestone 5 changes from
the previous pass and `main` was ahead of `origin/main` by one local commit after
fetching. The local-only commit was Milestone 4
(`1aca74b Add governed demand forecasting and evaluation`). Milestone 5 was
corrected on top of that local state without committing or pushing.

## Acceptance Checklist

- [x] Governed accepted inputs are used.
- [x] Validated forecast outputs are used.
- [x] Direct raw-zone inventory input is rejected.
- [x] Upstream input hashes are verified.
- [x] Upstream tracked inputs are preserved.
- [x] Warehouse demand allocation preserves forecast totals.
- [x] Inventory scores and reorder recommendations are deterministic.
- [x] Risk scores are bounded 0-100 and reorder quantities are non-negative.
- [x] Constrained recommendations do not exceed unconstrained quantities.
- [x] Scenario results are deterministic and documented.
- [x] Manifest, lineage, diagnostics, and reports are written.
- [x] Existing-run validation is available.
- [x] CLI, Makefile, tests, and CI integration are available.
- [x] No Milestone 6 quality analytics are implemented.

## Synthetic-Data Confirmation

All data remains synthetic and must not represent real customers, suppliers,
employees, plants, products, or commercial operations.

## Azure Deployment Confirmation

No Azure resources are deployed, configured, called, or required in Milestone 5.
