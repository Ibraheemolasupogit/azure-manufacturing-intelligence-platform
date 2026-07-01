# Strict Versus Permissive Mode

Milestone 3 supports two local ingestion modes.

| Mode | Behavior | Intended use |
| --- | --- | --- |
| `strict` | Any quarantined record fails the run before publishing outputs. | Tracked local sample and regression quality gates. |
| `permissive` | Valid records are accepted and invalid records are quarantined if the total quarantine rate is within configuration. | CI smoke runs, validation tests, and future controlled examples of rejected records. |

Both modes perform the same source discovery, file verification, schema checks, domain checks, relationship checks, and duplicate detection. The difference is the publication policy after validation.

The default local and CI profiles use strict mode. Permissive mode is available for controlled tests and future examples where invalid synthetic records should be written to quarantine without failing publication.
