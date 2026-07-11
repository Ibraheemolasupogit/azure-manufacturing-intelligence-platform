"""Deterministic Azure reference architecture artefact specifications."""
# ruff: noqa: E501

from __future__ import annotations

from typing import Any

SYNTHETIC_CLASSIFICATION = "synthetic_portfolio_sample"
DEPLOYMENT_STATUS_REFERENCE = "reference_only"
DISCLAIMER = (
    "Reference architecture only. No Azure resource, Power BI workspace, Fabric item, "
    "credential, deployment, or live service validation is created by this repository."
)

REQUIRED_DOCS = [
    "azure-reference-architecture.md",
    "deployment-boundary.md",
    "security-architecture.md",
    "data-architecture.md",
    "mlops-architecture.md",
    "genai-architecture.md",
    "operations-architecture.md",
    "cost-management.md",
]

REQUIRED_DIAGRAMS = [
    "azure-reference-architecture.mmd",
    "azure-data-flow.mmd",
    "azure-security-boundary.mmd",
    "azure-mlops-flow.mmd",
    "azure-genai-flow.mmd",
    "azure-monitoring-flow.mmd",
]

REQUIRED_INFRA_FILES = [
    "README.md",
    "bicep/main.bicep",
    "bicep/parameters.reference.json",
    "bicep/modules/storage.bicep",
    "bicep/modules/event-hubs.bicep",
    "bicep/modules/analytics.bicep",
    "bicep/modules/machine-learning.bicep",
    "bicep/modules/ai-services.bicep",
    "bicep/modules/monitoring.bicep",
    "bicep/modules/governance.bicep",
    "bicep/modules/dashboards.bicep",
    "terraform/README.md",
    "terraform/main.tf",
    "terraform/variables.tf",
    "terraform/outputs.tf",
    "terraform/terraform.tfvars.example",
    "policies/azure-policy-notes.md",
    "policies/rbac-matrix.md",
    "policies/private-networking-notes.md",
    "policies/data-governance-notes.md",
    "runbooks/deployment-boundary.md",
    "runbooks/local-validation-runbook.md",
    "runbooks/incident-response-runbook.md",
    "runbooks/cost-management-runbook.md",
    "runbooks/model-monitoring-runbook.md",
    "runbooks/data-quality-runbook.md",
]

REQUIRED_OUTPUTS = [
    "azure_service_mapping.csv",
    "azure_service_mapping.json",
    "security_controls_matrix.csv",
    "data_architecture_layers.csv",
    "mlops_mapping.csv",
    "genai_architecture_mapping.csv",
    "operations_mapping.csv",
    "cost_considerations.csv",
    "architecture_decision_records.json",
    "architecture_validation_results.json",
]


SERVICE_MAPPING_ROWS: list[dict[str, str]] = [
    {
        "platform_capability": "telemetry ingestion",
        "local_artefact": "data/raw/production_events.jsonl",
        "azure_service": "Azure Event Hubs",
        "service_role": "Future event ingress for production and equipment telemetry.",
        "reference_architecture_layer": "ingestion",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "Private endpoint, managed identity, RBAC, no shared keys.",
        "governance_controls": "Purview source registration as future production control.",
        "monitoring_controls": "Azure Monitor metrics and dead-letter alerting.",
        "cost_considerations": "Throughput units, retention, and event volume.",
        "limitations": "Local JSONL files only; no broker is deployed.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "raw and curated storage",
        "local_artefact": "data/raw/, data/interim/, outputs/",
        "azure_service": "Azure Data Lake Storage Gen2",
        "service_role": "Future raw, accepted, curated, evidence, and report zones.",
        "reference_architecture_layer": "storage",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "Hierarchical namespace, private endpoint, ACLs, CMK option.",
        "governance_controls": "Zone naming, retention policy, Purview scan plan.",
        "monitoring_controls": "Storage diagnostics and access audit logs.",
        "cost_considerations": "Capacity, transactions, redundancy, lifecycle policies.",
        "limitations": "Repository files remain local and synthetic.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "streaming analytics",
        "local_artefact": "data/raw/equipment_health.jsonl",
        "azure_service": "Azure Stream Analytics",
        "service_role": "Future stream transformations and windowed quality checks.",
        "reference_architecture_layer": "streaming",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "Managed identity outputs and private network paths.",
        "governance_controls": "Documented query ownership and schema contracts.",
        "monitoring_controls": "Job metrics, late input events, and failed outputs.",
        "cost_considerations": "Streaming units and continuous runtime.",
        "limitations": "No streaming job is created.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "operational telemetry analytics",
        "local_artefact": "outputs/monitoring/",
        "azure_service": "Azure Data Explorer",
        "service_role": "Future telemetry serving for quality and maintenance signals.",
        "reference_architecture_layer": "analytics",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "RBAC, table-level access, private endpoint.",
        "governance_controls": "Schema mapping and retention classification.",
        "monitoring_controls": "Ingestion failures and query performance.",
        "cost_considerations": "Cluster size, cache policy, retention.",
        "limitations": "No cluster or database is created.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "analytical serving",
        "local_artefact": "outputs/dashboard/",
        "azure_service": "Azure Synapse Analytics or Microsoft Fabric",
        "service_role": "Future curated serving and semantic model integration.",
        "reference_architecture_layer": "serving",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "Workspace RBAC, managed identity, private networking.",
        "governance_controls": "Certified semantic model and lineage metadata.",
        "monitoring_controls": "Refresh and warehouse workload metrics.",
        "cost_considerations": "Capacity, warehouse compute, refresh frequency.",
        "limitations": "Only local CSV and JSON dashboard artefacts exist.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "demand forecasting",
        "local_artefact": "outputs/forecasting/",
        "azure_service": "Azure Machine Learning",
        "service_role": "Future batch training, evaluation, model registry, and scoring.",
        "reference_architecture_layer": "mlops",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "Workspace isolation, managed identity, registry RBAC.",
        "governance_controls": "Model cards, lineage, and approval gates.",
        "monitoring_controls": "Forecast error and drift metrics.",
        "cost_considerations": "Compute clusters and batch scoring frequency.",
        "limitations": "No AML workspace or model endpoint exists.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "inventory scoring",
        "local_artefact": "outputs/inventory/",
        "azure_service": "Azure Machine Learning batch jobs",
        "service_role": "Future scheduled scoring for inventory risk and allocation.",
        "reference_architecture_layer": "mlops",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "Least-privilege data access and job identity.",
        "governance_controls": "Policy versioning and scenario traceability.",
        "monitoring_controls": "Score distribution and recommendation volume.",
        "cost_considerations": "Batch compute and storage reads.",
        "limitations": "Rules run locally only.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "quality analytics",
        "local_artefact": "outputs/quality/",
        "azure_service": "Azure Data Explorer and Azure Machine Learning",
        "service_role": "Future SPC analytics, anomaly scoring, and defect exploration.",
        "reference_architecture_layer": "analytics_ml",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "Private endpoints and data-product RBAC.",
        "governance_controls": "Quality metric glossary and lineage.",
        "monitoring_controls": "Alert rates and anomaly drift.",
        "cost_considerations": "Cluster/runtime and batch scoring compute.",
        "limitations": "Local static outputs only.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "predictive maintenance",
        "local_artefact": "outputs/maintenance/",
        "azure_service": "Azure Data Explorer and Azure Machine Learning",
        "service_role": "Future equipment telemetry features and failure-risk scoring.",
        "reference_architecture_layer": "analytics_ml",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "Scoped machine telemetry access and audit logs.",
        "governance_controls": "Maintenance signal definitions and lineage.",
        "monitoring_controls": "Anomaly volume and risk-score distribution.",
        "cost_considerations": "Telemetry retention, ADX cache, AML compute.",
        "limitations": "No IoT integration or deployed model.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "platform monitoring",
        "local_artefact": "outputs/monitoring/platform_health_summary.json",
        "azure_service": "Azure Monitor and Log Analytics",
        "service_role": "Future logs, metrics, workbooks, and alert rules.",
        "reference_architecture_layer": "operations",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "Workspace RBAC, data collection rules, retention controls.",
        "governance_controls": "Alert taxonomy and evidence integrity logs.",
        "monitoring_controls": "Domain health, pipeline status, and evidence freshness.",
        "cost_considerations": "Log ingestion, retention, query volume, alert rules.",
        "limitations": "No live telemetry stream exists.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "GenAI assistant",
        "local_artefact": "outputs/genai/",
        "azure_service": "Azure AI Foundry, Azure OpenAI Service, Azure AI Search",
        "service_role": "Future grounded assistant orchestration and retrieval.",
        "reference_architecture_layer": "genai",
        "deployment_status": "planned",
        "security_controls": "Private networking, content filtering, managed identity.",
        "governance_controls": "Prompt registry, citations, evaluation, usage policy.",
        "monitoring_controls": "Grounding quality, refusal rates, latency, cost.",
        "cost_considerations": "Token usage, search indexing, evaluation jobs.",
        "limitations": "Current assistant is deterministic and local; no LLM call.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "dashboard reporting",
        "local_artefact": "outputs/dashboard/",
        "azure_service": "Power BI and Microsoft Fabric semantic model",
        "service_role": "Future operational dashboards and certified semantic layer.",
        "reference_architecture_layer": "reporting",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "Workspace roles, row-level security, sensitivity labels.",
        "governance_controls": "Certified dataset, metric catalogue, lineage.",
        "monitoring_controls": "Refresh failures, usage metrics, semantic model health.",
        "cost_considerations": "Fabric/Power BI capacity and refresh cadence.",
        "limitations": "No .pbix, workspace, or Fabric item is generated.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "governance and catalogue",
        "local_artefact": "lineage-records.json and manifests",
        "azure_service": "Microsoft Purview",
        "service_role": "Future catalogue, glossary, classification, and lineage.",
        "reference_architecture_layer": "governance",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "Purview roles and scan credential isolation.",
        "governance_controls": "Business glossary and lineage mapping.",
        "monitoring_controls": "Scan status and classification coverage.",
        "cost_considerations": "Data map capacity and scanning frequency.",
        "limitations": "No Purview registration or scan occurs.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "secrets management",
        "local_artefact": "configs/",
        "azure_service": "Azure Key Vault",
        "service_role": "Future central store for secrets, keys, and certificates.",
        "reference_architecture_layer": "security",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "RBAC, private endpoint, soft delete, purge protection.",
        "governance_controls": "Secret rotation policy and access review.",
        "monitoring_controls": "Audit events and access anomalies.",
        "cost_considerations": "Operations and key transaction volume.",
        "limitations": "Portfolio configs contain no secrets.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
    {
        "platform_capability": "identity and access",
        "local_artefact": "docs/architecture/security-architecture.md",
        "azure_service": "Microsoft Entra ID",
        "service_role": "Future identity provider for users and managed workloads.",
        "reference_architecture_layer": "security",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "security_controls": "Conditional access, groups, managed identities, RBAC.",
        "governance_controls": "Access reviews and privileged role process.",
        "monitoring_controls": "Sign-in and audit logs.",
        "cost_considerations": "Premium identity features where required.",
        "limitations": "No tenant, principal, or group is created.",
        "synthetic_data_flag": SYNTHETIC_CLASSIFICATION,
    },
]


SECURITY_ROWS: list[dict[str, str]] = [
    {
        "control_id": "SEC-001",
        "control_domain": "identity boundary",
        "azure_service": "Microsoft Entra ID",
        "control_description": "Use Entra groups and managed identities for human and workload access.",
        "local_portfolio_equivalent": "No credentials; local files only.",
        "implementation_status": DEPLOYMENT_STATUS_REFERENCE,
        "evidence_path": "docs/architecture/security-architecture.md",
        "limitations": "No tenant roles are provisioned.",
    },
    {
        "control_id": "SEC-002",
        "control_domain": "rbac",
        "azure_service": "ADLS Gen2, AML, Power BI, Purview",
        "control_description": "Use least-privilege RBAC by platform capability.",
        "local_portfolio_equivalent": "Read/write boundaries documented in repository.",
        "implementation_status": DEPLOYMENT_STATUS_REFERENCE,
        "evidence_path": "infra/policies/rbac-matrix.md",
        "limitations": "RBAC is not applied to a subscription.",
    },
    {
        "control_id": "SEC-003",
        "control_domain": "key vault",
        "azure_service": "Azure Key Vault",
        "control_description": "Store secrets and keys in Key Vault with private endpoints.",
        "local_portfolio_equivalent": "No secrets are required or accepted.",
        "implementation_status": DEPLOYMENT_STATUS_REFERENCE,
        "evidence_path": "docs/architecture/deployment-boundary.md",
        "limitations": "No vault is created.",
    },
    {
        "control_id": "SEC-004",
        "control_domain": "private networking",
        "azure_service": "Virtual Network and Private Link",
        "control_description": "Use private endpoints for storage, ML, AI, monitoring, and governance.",
        "local_portfolio_equivalent": "Documented network segmentation assumptions.",
        "implementation_status": DEPLOYMENT_STATUS_REFERENCE,
        "evidence_path": "infra/policies/private-networking-notes.md",
        "limitations": "No network is deployed.",
    },
    {
        "control_id": "SEC-005",
        "control_domain": "data exfiltration",
        "azure_service": "Storage, Purview, Defender for Cloud",
        "control_description": "Restrict public access and monitor export paths.",
        "local_portfolio_equivalent": "Synthetic data and local-only outputs.",
        "implementation_status": DEPLOYMENT_STATUS_REFERENCE,
        "evidence_path": "docs/architecture/data-architecture.md",
        "limitations": "No production data perimeter is configured.",
    },
    {
        "control_id": "SEC-006",
        "control_domain": "logging and audit",
        "azure_service": "Azure Monitor and Log Analytics",
        "control_description": "Collect diagnostic logs for access, compute, pipelines, and dashboards.",
        "local_portfolio_equivalent": "Monitoring outputs and manifest evidence.",
        "implementation_status": DEPLOYMENT_STATUS_REFERENCE,
        "evidence_path": "outputs/monitoring/platform_health_summary.json",
        "limitations": "No live logs are collected.",
    },
    {
        "control_id": "SEC-007",
        "control_domain": "ci cd security",
        "azure_service": "GitHub Actions",
        "control_description": "Run static validation without secrets or deployment permissions.",
        "local_portfolio_equivalent": ".github/workflows/ci.yml static checks.",
        "implementation_status": "implemented_local",
        "evidence_path": ".github/workflows/ci.yml",
        "limitations": "No cloud deployment stage exists.",
    },
    {
        "control_id": "SEC-008",
        "control_domain": "supply chain",
        "azure_service": "GitHub Advanced Security conceptual mapping",
        "control_description": "Pin dependencies by constraints and run lint, type, and tests.",
        "local_portfolio_equivalent": "pyproject.toml and make quality.",
        "implementation_status": "implemented_local",
        "evidence_path": "pyproject.toml",
        "limitations": "No live dependency scanning service is configured.",
    },
    {
        "control_id": "SEC-009",
        "control_domain": "synthetic data boundary",
        "azure_service": "Microsoft Purview",
        "control_description": "Classify all portfolio evidence as synthetic.",
        "local_portfolio_equivalent": "Manifests use synthetic_portfolio_sample.",
        "implementation_status": "implemented_local",
        "evidence_path": "outputs/dashboard/dashboard-manifest.json",
        "limitations": "No Purview classification is registered.",
    },
]


DATA_LAYER_ROWS: list[dict[str, str]] = [
    {
        "layer_name": "raw",
        "purpose": "Synthetic source landing files.",
        "local_path": "data/raw/",
        "azure_mapping": "ADLS Gen2 raw zone",
        "data_format": "CSV and JSONL",
        "validation_controls": "Synthetic generation manifest and schema metadata.",
        "lineage_controls": "generation_manifest.json",
        "consumer": "ingestion",
        "limitations": "Synthetic and local only.",
    },
    {
        "layer_name": "accepted",
        "purpose": "Validated records accepted by governed ingestion.",
        "local_path": "data/interim/accepted/",
        "azure_mapping": "ADLS Gen2 accepted zone",
        "data_format": "CSV and JSONL",
        "validation_controls": "Data-quality rules and quarantine evidence.",
        "lineage_controls": "data/interim/_metadata/lineage-records.json",
        "consumer": "forecasting, inventory, quality, maintenance",
        "limitations": "No external ingestion.",
    },
    {
        "layer_name": "curated",
        "purpose": "Analytical outputs and model-ready evidence.",
        "local_path": "outputs/",
        "azure_mapping": "Synapse or Fabric curated lakehouse",
        "data_format": "CSV, JSON, Markdown",
        "validation_controls": "Domain manifests and existing-run validators.",
        "lineage_controls": "domain lineage records",
        "consumer": "monitoring, GenAI, dashboard",
        "limitations": "No serving warehouse exists.",
    },
    {
        "layer_name": "dashboard",
        "purpose": "Power BI-ready tables and semantic metadata.",
        "local_path": "outputs/dashboard/",
        "azure_mapping": "Power BI or Fabric semantic model",
        "data_format": "CSV and JSON",
        "validation_controls": "Dashboard manifest and semantic relationship checks.",
        "lineage_controls": "outputs/dashboard/lineage-records.json",
        "consumer": "reporting",
        "limitations": "No workspace or .pbix.",
    },
    {
        "layer_name": "evidence and manifests",
        "purpose": "Hashes, row counts, run IDs, and lineage.",
        "local_path": "outputs/**/manifest.json and lineage-records.json",
        "azure_mapping": "Purview and Azure Monitor evidence layer",
        "data_format": "JSON",
        "validation_controls": "Hash and row-count validation.",
        "lineage_controls": "Architecture lineage records",
        "consumer": "architecture validation",
        "limitations": "No Purview registration occurs.",
    },
]


MLOPS_ROWS: list[dict[str, str]] = [
    {
        "ml_capability": "forecasting",
        "local_artefact": "outputs/forecasting/model_metadata.json",
        "azure_ml_mapping": "AML training job and model registry",
        "model_or_rule_type": "deterministic baseline model",
        "training_or_scoring_mode": "local batch",
        "monitoring_signal": "forecast error and interval coverage",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "limitations": "No deployed model endpoint.",
    },
    {
        "ml_capability": "inventory",
        "local_artefact": "outputs/inventory/inventory_scores.csv",
        "azure_ml_mapping": "AML batch scoring pipeline",
        "model_or_rule_type": "rules and scenario scoring",
        "training_or_scoring_mode": "local batch scoring",
        "monitoring_signal": "risk distribution and reorder volume",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "limitations": "No optimization service.",
    },
    {
        "ml_capability": "quality",
        "local_artefact": "outputs/quality/anomaly_scores.csv",
        "azure_ml_mapping": "AML anomaly scoring job",
        "model_or_rule_type": "SPC and deterministic anomaly score",
        "training_or_scoring_mode": "local analytics batch",
        "monitoring_signal": "alert count and anomaly score drift",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "limitations": "No online scoring.",
    },
    {
        "ml_capability": "maintenance",
        "local_artefact": "outputs/maintenance/maintenance_predictions.json",
        "azure_ml_mapping": "AML batch inference and registry",
        "model_or_rule_type": "failure-risk scoring",
        "training_or_scoring_mode": "local batch",
        "monitoring_signal": "risk score and sensor degradation",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "limitations": "No IoT model deployment.",
    },
]


GENAI_ROWS: list[dict[str, str]] = [
    {
        "genai_capability": "grounded retrieval",
        "local_artefact": "outputs/genai/evidence_catalog.json",
        "azure_ai_mapping": "Azure AI Search index",
        "guardrail": "Only cite governed evidence paths.",
        "evaluation_control": "Citation coverage and unsupported-claim count.",
        "deployment_status": "planned",
        "limitations": "No search index is created.",
    },
    {
        "genai_capability": "prompt orchestration",
        "local_artefact": "outputs/genai/rendered_prompts.json",
        "azure_ai_mapping": "Azure AI Foundry prompt flow",
        "guardrail": "Deterministic prompt templates and refusal logic.",
        "evaluation_control": "Prompt and response diagnostics.",
        "deployment_status": "planned",
        "limitations": "No Foundry project exists.",
    },
    {
        "genai_capability": "response synthesis",
        "local_artefact": "outputs/genai/assistant_responses.json",
        "azure_ai_mapping": "Azure OpenAI Service",
        "guardrail": "No external model call; local deterministic synthesis only.",
        "evaluation_control": "Grounding score and guardrail result.",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "limitations": "No model deployment or token usage.",
    },
]


OPERATIONS_ROWS: list[dict[str, str]] = [
    {
        "operations_capability": "platform health",
        "local_artefact": "outputs/monitoring/platform_health_summary.json",
        "azure_monitor_mapping": "Azure Monitor workbook",
        "alert_type": "domain health degradation",
        "runbook_reference": "infra/runbooks/incident-response-runbook.md",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "limitations": "No live workbook.",
    },
    {
        "operations_capability": "data quality monitoring",
        "local_artefact": "outputs/monitoring/data_quality_monitoring.csv",
        "azure_monitor_mapping": "Log Analytics table and alert rule",
        "alert_type": "data quality threshold breach",
        "runbook_reference": "infra/runbooks/data-quality-runbook.md",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "limitations": "No log ingestion.",
    },
    {
        "operations_capability": "model monitoring",
        "local_artefact": "outputs/monitoring/model_and_analytics_monitoring.csv",
        "azure_monitor_mapping": "AML metrics and alerts",
        "alert_type": "model metric drift",
        "runbook_reference": "infra/runbooks/model-monitoring-runbook.md",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "limitations": "No deployed model metrics.",
    },
    {
        "operations_capability": "cost management",
        "local_artefact": "reports/deployment_boundary_report.md",
        "azure_monitor_mapping": "Cost Management budgets and alerts",
        "alert_type": "budget threshold",
        "runbook_reference": "infra/runbooks/cost-management-runbook.md",
        "deployment_status": DEPLOYMENT_STATUS_REFERENCE,
        "limitations": "No subscription budget.",
    },
]


COST_ROWS: list[dict[str, str]] = [
    {
        "service_area": "ingestion",
        "azure_service": "Event Hubs and Stream Analytics",
        "expected_cost_driver": "Throughput, retention, and streaming units.",
        "cost_control": "Right-size throughput and use autoscale alerts.",
        "local_portfolio_status": "No cloud cost; local files only.",
        "production_consideration": "Model event volume before selecting capacity.",
        "limitation": "No exact price estimate is provided.",
    },
    {
        "service_area": "storage",
        "azure_service": "ADLS Gen2",
        "expected_cost_driver": "Stored capacity, transactions, redundancy, retention.",
        "cost_control": "Lifecycle rules and tiering.",
        "local_portfolio_status": "Tracked small synthetic files.",
        "production_consideration": "Separate hot curated data from archival raw data.",
        "limitation": "No storage account exists.",
    },
    {
        "service_area": "analytics",
        "azure_service": "Data Explorer, Synapse, Fabric",
        "expected_cost_driver": "Compute capacity, cache, query volume.",
        "cost_control": "Pause or scale down non-production compute.",
        "local_portfolio_status": "Local CSV and JSON only.",
        "production_consideration": "Budget by workload class and refresh cadence.",
        "limitation": "No warehouse or cluster.",
    },
    {
        "service_area": "ml",
        "azure_service": "Azure Machine Learning",
        "expected_cost_driver": "Compute clusters, registry, storage, batch jobs.",
        "cost_control": "Use scheduled compute and idle shutdown.",
        "local_portfolio_status": "Local deterministic analytics.",
        "production_consideration": "Separate training from batch scoring budgets.",
        "limitation": "No AML workspace.",
    },
    {
        "service_area": "ai",
        "azure_service": "Azure AI Foundry, Azure OpenAI, Azure AI Search",
        "expected_cost_driver": "Tokens, evaluations, indexes, replicas.",
        "cost_control": "Grounded retrieval limits and usage quotas.",
        "local_portfolio_status": "No external model calls.",
        "production_consideration": "Budget token usage and search index scale.",
        "limitation": "No AI service is called.",
    },
    {
        "service_area": "reporting",
        "azure_service": "Power BI and Fabric",
        "expected_cost_driver": "Capacity, refreshes, storage, users.",
        "cost_control": "Certified semantic models and refresh governance.",
        "local_portfolio_status": "Local Power BI-ready extracts.",
        "production_consideration": "Choose Pro, Premium, or Fabric capacity deliberately.",
        "limitation": "No workspace or semantic model deployed.",
    },
    {
        "service_area": "monitoring",
        "azure_service": "Azure Monitor and Log Analytics",
        "expected_cost_driver": "Log ingestion, retention, alert rules, queries.",
        "cost_control": "Sampling, retention tiers, and alert hygiene.",
        "local_portfolio_status": "Static monitoring reports.",
        "production_consideration": "Control noisy logs and high-cardinality metrics.",
        "limitation": "No live telemetry.",
    },
]


ADR_ROWS: list[dict[str, str]] = [
    {
        "adr_id": "ADR-001",
        "title": "Keep implementation local first",
        "status": "accepted",
        "context": "Portfolio evidence must be reproducible without cloud access.",
        "decision": "Generate static Azure reference artefacts locally.",
        "consequences": "Blueprints are useful for design but not proof of deployment.",
        "local_evidence": "configs/azure_architecture.yaml",
        "azure_mapping": "GitHub Actions and Azure landing zone planning.",
        "limitations": "No subscription validation.",
    },
    {
        "adr_id": "ADR-002",
        "title": "Use synthetic data only",
        "status": "accepted",
        "context": "The platform must not represent real operations.",
        "decision": "All architecture artefacts reference synthetic portfolio evidence.",
        "consequences": "Security and governance controls are conceptual.",
        "local_evidence": "data/raw/generation_manifest.json",
        "azure_mapping": "Purview classification plan.",
        "limitations": "No real sensitivity labels.",
    },
    {
        "adr_id": "ADR-003",
        "title": "Map future telemetry to Event Hubs",
        "status": "accepted",
        "context": "Manufacturing telemetry is event-shaped.",
        "decision": "Use Event Hubs as the reference ingestion broker.",
        "consequences": "Streaming capacity must be planned in production.",
        "local_evidence": "data/raw/production_events.jsonl",
        "azure_mapping": "Azure Event Hubs.",
        "limitations": "No broker is deployed.",
    },
    {
        "adr_id": "ADR-004",
        "title": "Use ADLS Gen2 for storage zones",
        "status": "accepted",
        "context": "Raw, accepted, curated, and evidence zones need durable storage.",
        "decision": "Map local folders to ADLS Gen2 zones.",
        "consequences": "Production needs lifecycle and access policies.",
        "local_evidence": "data/README.md",
        "azure_mapping": "ADLS Gen2.",
        "limitations": "Local files only.",
    },
    {
        "adr_id": "ADR-005",
        "title": "Use ADX for operational telemetry",
        "status": "accepted",
        "context": "Quality and maintenance analytics need fast time-series queries.",
        "decision": "Map telemetry analytics to Azure Data Explorer.",
        "consequences": "ADX retention and cache policies must be cost-governed.",
        "local_evidence": "outputs/monitoring/",
        "azure_mapping": "Azure Data Explorer.",
        "limitations": "No cluster is created.",
    },
    {
        "adr_id": "ADR-006",
        "title": "Use AML for batch scoring",
        "status": "accepted",
        "context": "Forecasting, inventory, quality, and maintenance use repeatable scoring.",
        "decision": "Map these workflows to AML batch jobs and registry concepts.",
        "consequences": "Production requires model governance and compute budgets.",
        "local_evidence": "outputs/forecasting/",
        "azure_mapping": "Azure Machine Learning.",
        "limitations": "No workspace or endpoint.",
    },
    {
        "adr_id": "ADR-007",
        "title": "Map future assistant to Azure AI Foundry",
        "status": "accepted",
        "context": "The assistant needs grounded orchestration and evaluation.",
        "decision": "Use Foundry, Azure OpenAI, and AI Search as conceptual services.",
        "consequences": "Responsible-use and cost controls are required before live use.",
        "local_evidence": "outputs/genai/",
        "azure_mapping": "Azure AI Foundry, Azure OpenAI, Azure AI Search.",
        "limitations": "No external model call.",
    },
    {
        "adr_id": "ADR-008",
        "title": "Use Power BI and Fabric for reporting",
        "status": "accepted",
        "context": "Dashboard outputs are Power BI-ready.",
        "decision": "Map semantic outputs to Power BI and Fabric.",
        "consequences": "Production needs workspace, RLS, and refresh governance.",
        "local_evidence": "outputs/dashboard/",
        "azure_mapping": "Power BI and Fabric.",
        "limitations": "No .pbix or workspace.",
    },
    {
        "adr_id": "ADR-009",
        "title": "Use Purview for governance and lineage",
        "status": "accepted",
        "context": "Manifest and lineage evidence need a catalogue mapping.",
        "decision": "Map local lineage to conceptual Purview assets.",
        "consequences": "Production needs scans, glossary, and ownership model.",
        "local_evidence": "lineage-records.json",
        "azure_mapping": "Microsoft Purview.",
        "limitations": "No Purview registration.",
    },
    {
        "adr_id": "ADR-010",
        "title": "Use Azure Monitor for observability",
        "status": "accepted",
        "context": "Monitoring evidence already has domain health and alerts.",
        "decision": "Map operations to Azure Monitor and Log Analytics.",
        "consequences": "Production must manage log volume and alert quality.",
        "local_evidence": "outputs/monitoring/",
        "azure_mapping": "Azure Monitor and Log Analytics.",
        "limitations": "No live telemetry.",
    },
    {
        "adr_id": "ADR-011",
        "title": "Do not deploy during Milestone 11",
        "status": "accepted",
        "context": "The milestone is an architecture blueprint, not cloud provisioning.",
        "decision": "Forbid Azure CLI deployment, Bicep deployment, and Terraform apply.",
        "consequences": "Validation is static and local only.",
        "local_evidence": "outputs/architecture/architecture-manifest.json",
        "azure_mapping": "Deployment boundary.",
        "limitations": "No live Azure validation.",
    },
]


def architecture_docs() -> dict[str, str]:
    return {
        "azure-reference-architecture.md": _doc(
            "Azure Reference Architecture",
            [
                "The local portfolio maps synthetic manufacturing evidence to conceptual Azure services.",
                "Reference layers cover ingestion, storage, analytics, MLOps, GenAI, monitoring, governance, and reporting.",
                "Dashboard outputs map to Power BI and Fabric semantic-model responsibilities.",
            ],
        ),
        "deployment-boundary.md": _doc(
            "Deployment Boundary",
            [
                "Deployment mode is `reference_only`.",
                "Azure credentials are not required, collected, or validated.",
                "Terraform, Bicep, Power BI, Fabric, and Azure deployment commands are not run.",
            ],
        ),
        "security-architecture.md": _doc(
            "Security Architecture",
            [
                "Identity is mapped to Microsoft Entra ID with managed identity as the future workload pattern.",
                "RBAC, Key Vault, private networking, logging, audit, and CI/CD controls are documented only.",
                "The local portfolio has no secrets and uses synthetic data only.",
            ],
        ),
        "data-architecture.md": _doc(
            "Data Architecture",
            [
                "Raw, accepted, curated, dashboard, evidence, and manifest zones map to ADLS Gen2, Synapse/Fabric, Power BI, and Purview responsibilities.",
                "Schema evolution, retention, lineage, and data-quality gates are local documentation boundaries.",
                "No external data source or production customer data is used.",
            ],
        ),
        "mlops-architecture.md": _doc(
            "MLOps Architecture",
            [
                "Forecasting, inventory, quality, and maintenance outputs map to Azure Machine Learning batch and registry concepts.",
                "The portfolio keeps deterministic local splits, scoring, and manifests.",
                "No live endpoint, online model, or deployed training service exists.",
            ],
        ),
        "genai-architecture.md": _doc(
            "GenAI Architecture",
            [
                "The deterministic assistant maps conceptually to Azure AI Foundry, Azure OpenAI Service, and Azure AI Search.",
                "Prompt templates, guardrails, retrieval, citations, and evaluation remain local.",
                "No external model call, embedding call, index creation, or AI deployment occurs.",
            ],
        ),
        "operations-architecture.md": _doc(
            "Operations Architecture",
            [
                "Monitoring outputs map to Azure Monitor, Log Analytics, workbooks, and alert-rule responsibilities.",
                "Runbooks cover deployment boundary, local validation, incidents, cost, model monitoring, and data quality.",
                "No live telemetry or alert rule is created.",
            ],
        ),
        "cost-management.md": _doc(
            "Cost Management",
            [
                "Cost notes identify drivers for ingestion, storage, analytics, ML, AI, reporting, and monitoring.",
                "Controls include budgets, lifecycle management, capacity governance, quotas, and retention.",
                "No exact live prices are estimated because no Azure resources are deployed.",
            ],
        ),
    }


def diagrams() -> dict[str, str]:
    return {
        "azure-reference-architecture.mmd": """flowchart TD
    Local["Local portfolio evidence (synthetic, tracked)"] --> Ingestion["Reference Azure ingestion (Event Hubs, Stream Analytics)"]
    Ingestion --> Storage["Reference storage (ADLS Gen2 zones)"]
    Storage --> Analytics["Reference analytics (ADX, Synapse, Fabric)"]
    Analytics --> ML["Reference ML (Azure Machine Learning batch)"]
    Analytics --> GenAI["Reference GenAI (AI Foundry, Azure OpenAI, AI Search)"]
    Analytics --> Reporting["Reference reporting (Power BI, Fabric semantic model)"]
    ML --> Monitoring["Reference monitoring (Azure Monitor, Log Analytics)"]
    GenAI --> Monitoring
    Reporting --> Monitoring
    Governance["Reference governance (Purview, Entra ID, Key Vault)"] -.-> Storage
    Governance -.-> Analytics
    Governance -.-> ML
    Governance -.-> GenAI
    Governance -.-> Reporting
""",
        "azure-data-flow.mmd": """flowchart LR
    Raw["Local raw synthetic data"] --> EventHubs["Reference Event Hubs"]
    EventHubs --> Stream["Reference Stream Analytics"]
    Stream --> LakeRaw["Reference ADLS raw"]
    LakeRaw --> LakeAccepted["Reference ADLS accepted"]
    LakeAccepted --> Curated["Reference curated lakehouse"]
    Curated --> Semantic["Reference Fabric semantic model"]
    Semantic --> PowerBI["Reference Power BI"]
    Curated -.-> Purview["Reference Purview lineage"]
""",
        "azure-security-boundary.mmd": """flowchart TD
    Boundary["Reference-only boundary: no live Azure tenant"] --> Entra["Reference Entra ID"]
    Boundary --> KeyVault["Reference Key Vault"]
    Boundary --> PrivateLink["Reference Private Link"]
    Entra --> RBAC["Least-privilege RBAC design"]
    KeyVault --> Secrets["No secrets in local portfolio"]
    PrivateLink --> Network["Private network segmentation notes"]
    Audit["Reference Azure Monitor audit"] --> Boundary
""",
        "azure-mlops-flow.mmd": """flowchart LR
    Evidence["Governed local evidence"] --> Features["Feature generation"]
    Features --> Train["Reference AML training or rules"]
    Train --> Registry["Reference model registry"]
    Registry --> Batch["Reference batch scoring"]
    Batch --> Monitor["Reference model monitoring"]
    Monitor --> Governance["Reference approval and lineage"]
""",
        "azure-genai-flow.mmd": """flowchart LR
    Evidence["Governed evidence catalogue"] --> Search["Reference Azure AI Search"]
    Search --> Prompt["Reference AI Foundry prompt orchestration"]
    Prompt --> Model["Reference Azure OpenAI"]
    Model --> Guardrails["Guardrails and evaluation"]
    Guardrails --> Response["Cited local recommendations"]
    Response --> Monitor["Reference GenAI monitoring"]
""",
        "azure-monitoring-flow.mmd": """flowchart TD
    Pipelines["Local pipeline manifests"] --> Logs["Reference Log Analytics"]
    Outputs["Local monitoring outputs"] --> Logs
    Logs --> Workbooks["Reference Azure Monitor workbooks"]
    Logs --> Alerts["Reference alert taxonomy"]
    Alerts --> Runbooks["Operational runbooks"]
    Workbooks --> PowerBI["Reference Power BI operations view"]
""",
    }


def infra_files() -> dict[str, str]:
    reference = "Reference-only blueprint. It is not a deployment script."
    return {
        "README.md": f"# Infrastructure Blueprint\n\n{DISCLAIMER}\n\n{reference}\n",
        "bicep/main.bicep": (
            "// Reference-only Bicep blueprint. Do not deploy for this portfolio milestone.\n"
            "targetScope = 'resourceGroup'\n"
            "param location string = 'placeholder-location'\n"
            "param environmentName string = 'reference'\n"
            "module storage 'modules/storage.bicep' = { name: 'referenceStorage'; params: { location: location environmentName: environmentName } }\n"
        ),
        "bicep/parameters.reference.json": (
            "{\n"
            '  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",\n'
            '  "contentVersion": "1.0.0.0",\n'
            '  "parameters": {\n'
            '    "location": { "value": "placeholder-location" },\n'
            '    "environmentName": { "value": "reference" }\n'
            "  }\n"
            "}\n"
        ),
        "bicep/modules/storage.bicep": _bicep_module("storage"),
        "bicep/modules/event-hubs.bicep": _bicep_module("eventHubs"),
        "bicep/modules/analytics.bicep": _bicep_module("analytics"),
        "bicep/modules/machine-learning.bicep": _bicep_module("machineLearning"),
        "bicep/modules/ai-services.bicep": _bicep_module("aiServices"),
        "bicep/modules/monitoring.bicep": _bicep_module("monitoring"),
        "bicep/modules/governance.bicep": _bicep_module("governance"),
        "bicep/modules/dashboards.bicep": _bicep_module("dashboards"),
        "terraform/README.md": (
            "# Terraform Blueprint\n\n"
            f"{DISCLAIMER}\n\n"
            "This folder is a static reference. Do not run Terraform apply for this portfolio milestone.\n"
        ),
        "terraform/main.tf": (
            "# Reference-only Terraform blueprint. Do not apply for this portfolio milestone.\n"
            'terraform { required_version = ">= 1.6.0" }\n'
            'locals { environment_name = "reference" }\n'
        ),
        "terraform/variables.tf": (
            "# Reference-only variables. Placeholder values only.\n"
            'variable "location" { type = string default = "placeholder-location" }\n'
        ),
        "terraform/outputs.tf": (
            "# Reference-only outputs. No resource IDs are emitted.\n"
            'output "deployment_status" { value = "reference_only" }\n'
        ),
        "terraform/terraform.tfvars.example": (
            "# Placeholder values only. No subscription, tenant, client secret, or password.\n"
            'location = "placeholder-location"\n'
        ),
        "policies/azure-policy-notes.md": _policy("Azure Policy Notes"),
        "policies/rbac-matrix.md": _policy("RBAC Matrix"),
        "policies/private-networking-notes.md": _policy("Private Networking Notes"),
        "policies/data-governance-notes.md": _policy("Data Governance Notes"),
        "runbooks/deployment-boundary.md": _runbook("Deployment Boundary Runbook"),
        "runbooks/local-validation-runbook.md": _runbook("Local Validation Runbook"),
        "runbooks/incident-response-runbook.md": _runbook("Incident Response Runbook"),
        "runbooks/cost-management-runbook.md": _runbook("Cost Management Runbook"),
        "runbooks/model-monitoring-runbook.md": _runbook("Model Monitoring Runbook"),
        "runbooks/data-quality-runbook.md": _runbook("Data Quality Runbook"),
    }


def markdown_reports(
    run_id: str, service_count: int, security_count: int, adr_count: int
) -> dict[str, str]:
    return {
        "azure_architecture_report.md": (
            "# Azure Architecture Report\n\n"
            f"Run ID: `{run_id}`\n\n"
            f"- Service mappings: {service_count}\n"
            f"- Security controls: {security_count}\n"
            f"- ADRs: {adr_count}\n"
            f"- Deployment mode: `reference_only`\n"
            f"- Azure credentials required: `false`\n\n"
            f"{DISCLAIMER}\n"
        ),
        "deployment_boundary_report.md": (
            "# Deployment Boundary Report\n\n"
            "No Azure resources were deployed. No Azure CLI, Bicep deployment, Terraform apply, "
            "Power BI REST API, or Azure SDK deployment client was executed.\n\n"
            f"{DISCLAIMER}\n"
        ),
    }


def validation_result_template() -> dict[str, Any]:
    return {
        "validation_status": "success",
        "deployment_mode": "reference_only",
        "azure_deployment": False,
        "azure_credentials_required": False,
        "forbidden_active_commands_found": [],
        "secret_findings": [],
        "subscription_or_tenant_findings": [],
    }


def _doc(title: str, bullets: list[str]) -> str:
    body = "\n".join(f"- {item}" for item in bullets)
    return f"# {title}\n\n{DISCLAIMER}\n\n{body}\n"


def _bicep_module(name: str) -> str:
    return (
        "// Reference-only Bicep module. Do not deploy for this portfolio milestone.\n"
        "param location string\n"
        "param environmentName string\n"
        f"var referenceComponent = '{name}'\n"
        "output componentName string = referenceComponent\n"
    )


def _policy(title: str) -> str:
    return f"# {title}\n\n{DISCLAIMER}\n\nDocumented policy intent only; no Azure Policy assignment exists.\n"


def _runbook(title: str) -> str:
    return f"# {title}\n\n{DISCLAIMER}\n\nUse local validation commands only. Escalate production incidents through the future operations process.\n"
