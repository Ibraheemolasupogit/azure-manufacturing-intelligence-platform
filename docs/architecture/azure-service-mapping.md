# Azure Service Mapping

The project uses local components to represent responsibilities commonly handled by Azure services. These mappings are architectural references rather than evidence of deployed cloud infrastructure.

| Local capability | Azure reference service |
| --- | --- |
| JSONL and CSV event simulation | Azure Event Hubs and Azure IoT Hub |
| Local raw-data directories | Azure Data Lake Storage Gen2 |
| Python streaming simulator | Azure Stream Analytics |
| Local telemetry analysis | Azure Data Explorer |
| Local analytical outputs | Azure Synapse Analytics |
| Local model training | Azure Machine Learning |
| Local GenAI adapter | Azure AI Foundry |
| Local dashboard extracts | Microsoft Power BI |
| Local lineage metadata | Microsoft Purview |
| Local structured logs and metrics | Azure Monitor and Application Insights |
| GitHub Actions | Azure DevOps Pipelines or GitHub Actions for Azure |

## Safety boundary

Milestone 1 does not create Azure resource IDs, credentials, endpoints, screenshots, deployment logs, or success claims. `azure_mapping.enabled` is false in the provided configuration and must not initiate cloud calls.
