# Contributing

This project is built as a production-style portfolio repository. Contributions should keep the platform local-first, deterministic, reproducible, testable, modular, auditable, CI-ready, and explicit about the difference between implemented capabilities and planned Azure mappings.

## Development workflow

1. Create or activate a Python 3.11+ environment.
2. Run `make install`.
3. Make focused changes within the relevant package boundary.
4. Run `make quality`.
5. Keep generated data, caches, build artefacts, credentials, and local environment files out of source control.

## Coding standards

Use type hints, docstrings for public functions and classes, `pathlib`, standard logging, deterministic behaviour, explicit error handling, and small testable functions. Avoid hidden network calls, fake metrics, fake deployment evidence, notebook-only implementation, hard-coded absolute paths, and unnecessary frameworks.

## Documentation standards

Documentation must be clear about scope. Future capabilities may be described as planned, but must not be presented as complete until implemented and tested.

## Security

Use synthetic data only. Never commit real employee, customer, supplier, production, commercial, credential, endpoint, or secret material.
