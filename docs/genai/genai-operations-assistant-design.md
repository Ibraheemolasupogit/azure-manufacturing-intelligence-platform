# GenAI Operations Assistant Design

Milestone 9 adds a deterministic, local-first operations assistant that simulates a governed GenAI workflow without calling any model, cloud service, vector database, internet endpoint, or Azure service.

The assistant reads tracked evidence from generation, ingestion, forecasting, inventory, quality, maintenance, and monitoring. It builds an evidence catalogue, retrieves evidence with deterministic domain and keyword rules, renders prompt templates for auditability, evaluates guardrails, synthesizes rule-based answers, and writes manifests, lineage, diagnostics, evaluation results, and Markdown reports.

Azure AI Foundry, Azure OpenAI Service, Azure AI Search, Azure Machine Learning prompt evaluation, Microsoft Purview, Azure Monitor, and Power BI are reference mappings only. No deployment or service call occurs.
