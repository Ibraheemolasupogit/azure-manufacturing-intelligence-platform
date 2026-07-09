# GenAI Lineage And Manifest

The assistant writes `outputs/genai/genai-manifest.json` and `outputs/genai/lineage-records.json`.

The manifest records the GenAI run ID, pipeline version, software version, configuration hash, evidence inputs, evidence hashes, catalogue row count, supported task types, prompt-template hashes, response counts, guardrail counts, evaluation metrics, outputs, hashes, validation status, warnings, synthetic classification, external model status, Azure deployment status, Git commit, and upstream immutability confirmation.

Lineage links governed evidence to the catalogue, retrieval, prompts, guardrails, responses, evaluation, and narrative reports. It does not claim Microsoft Purview registration.
