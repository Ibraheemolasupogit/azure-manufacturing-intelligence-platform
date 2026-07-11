# Azure Service Mapping

The project uses local components to represent responsibilities commonly handled by Azure services. These mappings are architectural references rather than evidence of deployed cloud infrastructure.

| Local capability | Azure reference service |
| --- | --- |
| JSONL and CSV event simulation | Azure Event Hubs and Azure IoT Hub |
| Local raw-data directories | Azure Data Lake Storage Gen2 |
| Local accepted and quarantine directories | Azure Data Lake Storage Gen2 medallion-style zones |
| Local validation rules | Azure Data Factory data flows or Microsoft Fabric data pipelines |
| Python streaming simulator | Azure Stream Analytics |
| Local telemetry analysis | Azure Data Explorer |
| Local analytical outputs | Azure Synapse Analytics |
| Local forecast training and model metadata | Azure Machine Learning |
| Local inventory scoring and scenario policy | Azure Machine Learning batch scoring or Container Apps |
| Local quality SPC and anomaly scoring | Azure Data Explorer and Azure Machine Learning batch scoring |
| Local feature preparation | Azure Synapse Analytics or Microsoft Fabric |
| Local forecast, inventory, and quality metrics and diagnostics | Azure Monitor and Application Insights |
| Local GenAI adapter | Azure AI Foundry |
| Local dashboard extracts | Microsoft Power BI |
| Local lineage metadata | Microsoft Purview |
| Local structured logs and metrics | Azure Monitor and Application Insights |
| GitHub Actions | Azure DevOps Pipelines or GitHub Actions for Azure |

## Safety boundary

The completed local milestones do not create Azure resource IDs, credentials, endpoints, screenshots, deployment logs, model registrations, or success claims. `azure_mapping.enabled` is false in the provided configuration and must not initiate cloud calls.
## Predictive maintenance reference mapping

Milestone 7 maps local maintenance responsibilities to Azure concepts without deploying them:

- Governed equipment-health and production inputs: Azure Data Lake Storage Gen2 responsibility.
- Operational telemetry analytics and sensor-threshold exploration: Azure Data Explorer responsibility.
- Feature preparation and analytical tables: Azure Synapse Analytics or Microsoft Fabric responsibility.
- Batch anomaly and failure-risk scoring: Azure Machine Learning responsibility.
- Equipment and pipeline metrics: Azure Monitor responsibility.
- Lineage metadata: Microsoft Purview responsibility.
- Maintenance alert and score extracts: Power BI-ready output responsibility.

No Azure SDK client, credential, endpoint, workspace, database, dashboard, or deployment is created by this milestone.

## Monitoring reference mapping

Milestone 8 maps local monitoring responsibilities to Azure concepts without deploying them:

- Platform and pipeline metrics: Azure Monitor responsibility.
- Local observability summaries: Log Analytics responsibility.
- Evidence and output query patterns: Azure Data Explorer responsibility.
- Analytics and model-health indicators: Azure Machine Learning monitoring responsibility.
- Local lineage metadata: Microsoft Purview responsibility.
- Portfolio health extracts: Power BI-ready output responsibility.

No live telemetry collection, Azure SDK client, workspace, dashboard, secret, or cloud deployment is created.
## Milestone 9 GenAI Reference Mapping

The deterministic GenAI operations assistant is a local simulation of responsibilities that could later map to Azure services:

| Local Milestone 9 component | Azure reference |
| --- | --- |
| Evidence catalogue | Azure AI Search responsibility |
| Prompt-template rendering | Azure AI Foundry prompt-flow responsibility |
| Future model endpoint boundary | Azure OpenAI Service responsibility |
| Deterministic evaluation | Azure Machine Learning evaluation responsibility |
| Manifest and lineage | Microsoft Purview responsibility |
| Guardrail and health evidence | Azure Monitor responsibility |
| Narrative report outputs | Power BI-ready narrative responsibility |

No Azure AI service is deployed or called by Milestone 9.

## Milestone 10 dashboard reference mapping

| Local Milestone 10 component | Reference service |
| --- | --- |
| Dashboard CSV and JSON outputs | Power BI import-ready artefacts |
| Semantic model metadata | Microsoft Fabric semantic model responsibility |
| Curated dashboard tables | Azure Synapse or ADLS Gen2 curated gold responsibility |
| Dashboard lineage | Microsoft Purview responsibility |
| Platform health views | Azure Monitor responsibility |

No Power BI, Fabric, Synapse, ADLS, Purview, Azure Monitor, or Azure deployment is created by Milestone 10.

## Milestone 11 architecture blueprint mapping

Milestone 11 writes static mapping evidence under `outputs/architecture/`:

- `azure_service_mapping.csv` and `.json`: maps local capabilities to Event Hubs, ADLS Gen2, Stream Analytics, Azure Data Explorer, Synapse/Fabric, Azure Machine Learning, Azure AI Foundry, Azure OpenAI, Azure AI Search, Azure Monitor, Log Analytics, Application Insights, Microsoft Purview, Power BI, Key Vault, Entra ID, and Container Apps responsibilities.
- `security_controls_matrix.csv`: documents identity, RBAC, Key Vault, private networking, exfiltration, audit, CI/CD, supply-chain, and synthetic-data controls.
- `data_architecture_layers.csv`, `mlops_mapping.csv`, `genai_architecture_mapping.csv`, `operations_mapping.csv`, and `cost_considerations.csv`: map local governed evidence to production architecture responsibilities.

All deployment statuses remain `reference_only` or `planned`. No Azure service, Power BI workspace, Fabric item, Terraform state, or Bicep deployment is created.
