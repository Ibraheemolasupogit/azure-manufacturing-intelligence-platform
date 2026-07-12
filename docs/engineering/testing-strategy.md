# Testing Strategy

Implemented tests cover configuration loading, overrides, path resolution, package imports, repository structure, metadata coherence, Azure reference-only safety, deterministic synthetic generation, governed ingestion, validation, quarantine behavior, lineage evidence, demand forecasting, leakage boundaries, chronological splits, metrics, forecast manifests, inventory intelligence, quality analytics, and CLI entry points.
Inventory tests also cover governed input protection, upstream hash verification, deterministic inventory scoring, policy math, scenario comparison, manifest validation, tamper detection, overwrite protection, raw-input rejection, and CLI execution outside the repository root.

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

Milestone 5 specifically tests that inventory intelligence reads accepted governed inputs and validated forecast outputs only, preserves upstream files, computes bounded risk scores and non-negative reorder quantities, emits deterministic manifests and lineage, validates existing runs, and separates rules-based inventory policy from constrained scenario allocation.

Milestone 6 specifically tests that quality analytics reads governed accepted quality and production data only, preserves upstream files, verifies hashes and manifests, calculates specification compliance, capability diagnostics, SPC signals, anomaly scores, risk scores, deterministic alerts, existing-run validation, tamper detection, overwrite behavior, raw-input rejection, and CLI execution outside the repository root.

Later milestones should expand tests in proportion to behavioural risk and blast radius.
## Maintenance tests

Milestone 7 tests cover governed input use, raw-input rejection, upstream row and hash evidence through manifests, threshold formula checks, threshold consistency flags, runtime and maintenance-state scoring, degradation insufficient-history handling, robust z-score and zero-MAD fallback, deterministic Isolation Forest scoring, anomaly score wording, risk and health score ranges, deterministic alert IDs, existing-run validation, tamper detection, overwrite protection, configuration validation, and CLI execution outside the repository root.

The CI workflow runs `make maintenance-ci` and validates the generated maintenance run under `.generated/ci/maintenance/`, then removes `.generated/`.

## Monitoring tests

Milestone 8 tests cover required manifest loading, missing evidence failures, hash and row-count checks, domain health scoring, label mapping, deterministic deductions, alert ID stability, alert ordering, platform summary determinism, lineage completeness, existing-run validation, tamper detection, overwrite protection, invalid configuration, and CLI execution outside the repository root.

The CI workflow runs `make monitoring-ci` and validates the generated monitoring run under `.generated/ci/monitoring/`, then removes `.generated/`.
## GenAI Assistant Testing

Milestone 9 tests cover the evidence catalogue, required domains, hash calculation, `.generated` exclusion, deterministic retrieval, prompt rendering, guardrail refusal paths, response citation validity, unsupported-claim counts, grounding and citation metrics, all standard assistant tasks, manifest output metadata, lineage targets, overwrite protection, invalid configuration, existing-run validation, tamper detection, CLI execution outside the repository root, and CI generation under `.generated/ci/genai/`.

The tests use local deterministic evidence only and do not access Azure, OpenAI, the internet, external evaluators, embeddings, vector databases, or live services.

## Dashboard Output Testing

Milestone 10 tests cover dashboard configuration loading, environment overrides, path resolution, governed upstream manifest checks, source hash verification, non-empty dimensions and facts, primary key uniqueness, semantic model relationship validity, metric catalogue completeness, page and visual specification validity, synthetic-data disclaimers, deployment boundary flags, deterministic manifests, lineage records, overwrite protection, tamper detection, existing-run validation, and CLI execution outside the repository root.

The CI workflow runs `make dashboard-ci` and validates the generated dashboard run under `.generated/ci/dashboard/`. Dashboard tests do not create `.pbix` files, call Power BI or Fabric APIs, access Azure services, publish dashboards, or mutate upstream governed evidence.

## Architecture Blueprint Testing

Milestone 11 tests cover architecture configuration loading, invalid deployment-mode rejection, governed evidence use, required docs, required diagrams, required infra blueprint files, service mapping coverage, security control domains, data architecture layers, MLOps mappings, GenAI no-external-call boundaries, operations runbook mapping, cost service areas, ADR decisions, reference-only deployment flags, Azure credentials required false, forbidden active deployment command scanning, secret-like value scanning, manifest row counts, manifest sizes, manifest hashes, lineage target hashes, existing-run validation, tamper detection, overwrite protection, CLI execution outside the repository root, and CI generation under `.generated/ci/architecture/`.

The CI workflow runs `make architecture-ci` and validates the generated architecture run with static checks only. Architecture tests do not access Azure, Power BI, Fabric, Terraform backends, Bicep deployment, the internet, external services, credentials, secrets, or live cloud resources.

## Final Release Testing

Milestone 12 tests cover release configuration loading, invalid external-service and cloud-deployment rejection, final evidence index generation, `.generated` exclusion, catalogue reference checks, report and architecture index checks, data catalogue generation, model/domain catalogue coverage, dashboard semantic model coverage, GenAI external-call false checks, Azure reference deployment-status checks, validation summary, repository health, manifest counts, sizes, hashes, lineage hashes, release docs, milestone 12 evidence, existing-run validation, tamper detection, overwrite protection, CLI execution outside the repository root, CI release execution, and `validate-all` target coverage.

The CI workflow runs `make release-ci` and validates the generated release run under `.generated/ci/release/`. Release tests do not access Azure, Power BI, Fabric, OpenAI, the internet, external APIs, credentials, secrets, or live services.
