# Inventory Lineage And Manifest

The inventory run writes:

- `outputs/inventory/inventory-manifest.json`
- `outputs/inventory/lineage-records.json`
- `outputs/inventory/inventory_summary.json`
- `outputs/inventory/inventory_diagnostics.json`

The manifest records the inventory run ID, software version, semantic
configuration hash, input paths, governed input hashes, governed input row counts,
upstream ingestion run ID, upstream forecast run ID, upstream manifest hashes,
decision grain, planning horizon, policy parameters, scenario parameters,
constrained allocation settings, output file evidence, metrics summary, warnings,
synthetic classification, git commit, and Azure reference mapping.

Lineage records are local evidence only. Each record includes the inventory run ID,
upstream run IDs, governed source inputs with hashes and row counts, target path,
target hash, target row count, transformation name, transformation type,
configuration hash, validation status, synthetic classification, and reference-only
Azure mapping.

`make validate-inventory` validates existing outputs without rescoring.
