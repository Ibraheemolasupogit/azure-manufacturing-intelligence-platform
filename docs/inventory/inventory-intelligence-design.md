# Inventory Intelligence Design

Milestone 5 provides a deterministic, local-first inventory intelligence layer over
the governed Milestone 3 accepted inputs and Milestone 4 demand forecast outputs.
It does not ingest external files, deploy cloud services, run dashboards, or start
Milestone 6 optimisation services.

The pipeline runs from `configs/inventory.yaml` through:

```bash
python -m manufacturing_intelligence.inventory --config configs/inventory.yaml --overwrite
```

The core calculation sequence is:

1. Load accepted inventory, supplier, warehouse movement, sales order, and demand
   forecast files.
2. Verify upstream ingestion and forecast manifests, lineage, metadata, hashes, and
   row counts.
3. Allocate product-region forecast demand to warehouses.
4. Build supplier lead-time and risk metrics for material records.
5. Build item-location policy inputs at the configured decision grain.
6. Calculate inventory position, safety stock, reorder point, target stock, risk
   scores, recommendations, constrained allocation, and scenarios.
7. Write CSV, JSON, manifest, lineage, and Markdown report artifacts.

All outputs are deterministic for the same configuration and upstream file hashes.
The manifest records the input hashes, upstream run IDs, semantic configuration
hash, scenario assumptions, constrained allocation settings, and Azure reference
mapping.
