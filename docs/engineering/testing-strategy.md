# Testing Strategy

Implemented tests cover configuration loading, overrides, path resolution, package imports, repository structure, metadata coherence, Azure reference-only safety, deterministic synthetic generation, governed ingestion, validation, quarantine behavior, lineage evidence, demand forecasting, leakage boundaries, chronological splits, metrics, forecast manifests, and CLI entry points.

## Planned test layers

- Unit tests for small deterministic functions.
- Schema tests for data contracts.
- Data-quality tests for nullability, ranges, categories, duplicates, and referential checks.
- Deterministic fixture tests for synthetic generators.
- Pipeline integration tests for local raw-to-interim paths.
- Model evaluation tests for forecasting and predictive workflows.
- Regression tests for stable analytical outputs.
- Documentation checks for implemented-versus-planned accuracy.
- CI controls that run without Azure credentials or internet calls.

Milestone 3 specifically tests raw-input immutability, deterministic ingestion output, run ID changes for relevant configuration changes, missing datasets, missing metadata, source hash mismatch, invalid JSON line reporting, invalid CSV headers, permissive quarantine, duplicate primary keys, strict-mode failure, existing-run tamper detection, overwrite behavior, and CLI execution outside the repository root.

Milestone 4 specifically tests governed accepted input use, raw-input rejection, upstream evidence verification, aggregation, calendar filling, leakage-safe lag and rolling features, chronological splits, baseline metrics, deterministic output, run ID changes, existing-run validation, tamper detection, interval ordering, overwrite behavior, invalid config rejection, and CLI execution outside the repository root.

Extended-profile regression tests verify that longer generated sales orders reference products present in production events, generation remains deterministic, governed ingestion has zero sales-order quarantine, quarantine-threshold enforcement fails on unexpected quarantine, and the extended forecast produces three chronological rolling-origin windows from accepted data.

Later milestones should expand tests in proportion to behavioural risk and blast radius.
