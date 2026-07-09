# Retrieval And Prompting

Retrieval uses deterministic keyword and domain matching. It supports executive summary, forecasting, inventory, quality, maintenance, monitoring, lineage, and data-quality intents.

Ranking prioritizes matched domains, supported question types, manifests, reports, and keyword matches. Ordering is stable and capped by configuration.

Prompt templates are rendered to `outputs/genai/rendered_prompts.json` for transparency only. They include the task, evidence list, guardrails, citation behaviour, synthetic-data disclaimer, and no-live-operations disclaimer. No rendered prompt is sent to an external model.
