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
