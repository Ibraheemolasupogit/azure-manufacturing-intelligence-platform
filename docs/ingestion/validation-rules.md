# Validation Rules

Validation is deterministic and dataset-aware. The rules are intended to create governed local evidence for later milestones, not to enforce external customer inputs.

## File-level checks

- Required metadata files must exist.
- All expected source datasets must exist.
- Source file size and SHA-256 values must match `generation_manifest.json` when hash verification is enabled.
- Unexpected raw `.csv` and `.jsonl` dataset files are rejected.
- CSV headers must exactly match schema field order.
- JSONL parse errors include dataset and line number.
- Empty required datasets are rejected.

## Record contract checks

- Required fields must be present.
- Unknown fields are rejected unless explicitly allowed.
- Primitive field types are checked from schema metadata.
- Categorical values must match configured domains.
- Timestamp fields must parse as ISO timestamps or dates.

## Domain checks

- Production accepted plus rejected quantity must equal produced quantity.
- Inventory available quantity must equal on-hand minus reserved quantity, and inventory value must match quantity times unit cost.
- Sales fulfilled quantity may not exceed ordered quantity, order value must match fulfilled quantity times selling price, and requested delivery date may not precede order date.
- Quality checks validate sample counts, specification limits, pass/fail result, and defect-category consistency.
- Equipment health validates thresholds, threshold status, runtime values, and measurement units.
- Warehouse movement quantity must be positive.
- Supplier performance validates delivered quantities, accepted plus rejected quantities, delay days, delivery status, and quality score.

## Relationship checks

The pipeline builds reference indexes across loaded datasets and validates identifiers for plants, lines, machines, products, batches, shifts, warehouses, items, suppliers, and materials. Relationship checks are local and deterministic; they do not call an external master-data system.
