# Development Standards

The repository should remain local-first, deterministic, reproducible, testable, modular, auditable, CI-ready, and honest about implementation status.

## Required practices

- Use clear module boundaries.
- Add type hints and public docstrings.
- Prefer `pathlib` for filesystem work.
- Use standard-library logging unless a future milestone justifies more.
- Keep functions small and testable.
- Validate configuration and data contracts explicitly.
- Use deterministic seeds for synthetic data and tests.
- Preserve UTF-8 and portable paths.

## Avoid

- Unnecessary frameworks.
- Placeholder production claims.
- Unused abstractions.
- Dead code.
- Notebook-only implementation.
- Hard-coded absolute paths.
- Hidden network calls.
- Fake metrics, fake dashboards, fake deployment evidence, or fabricated Azure success.
