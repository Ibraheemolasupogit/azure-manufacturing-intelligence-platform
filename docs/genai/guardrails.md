# Guardrails

The assistant refuses or constrains requests for live production action, safety-critical maintenance instructions, real-world plant status, missing evidence, unsupported causal proof, external web or cloud data, validation overrides, secrets, credentials, and deployment details.

Guardrail decisions are deterministic and written to `outputs/genai/guardrail_results.json`. Each record includes triggered rules, decision, response policy, refusal message where applicable, allowed scope, evidence requirement, evidence availability, and `external_model_called=false`.
