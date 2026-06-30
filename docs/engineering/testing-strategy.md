# Testing Strategy

Milestone 1 includes unit tests for configuration loading, overrides, path resolution, package imports, repository structure, metadata coherence, and Azure reference-only safety.

## Planned test layers

- Unit tests for small deterministic functions.
- Schema tests for data contracts.
- Data-quality tests for nullability, ranges, categories, duplicates, and referential checks.
- Deterministic fixture tests for synthetic generators.
- Pipeline integration tests for local end-to-end paths.
- Model evaluation tests for forecasting and predictive workflows.
- Regression tests for stable analytical outputs.
- Documentation checks for implemented-versus-planned accuracy.
- CI controls that run without Azure credentials or internet calls.

Later milestones should expand tests in proportion to behavioural risk and blast radius.
