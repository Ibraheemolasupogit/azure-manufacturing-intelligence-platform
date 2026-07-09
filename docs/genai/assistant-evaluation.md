# Assistant Evaluation

Evaluation is deterministic and transparent. It checks evidence references, citation coverage, grounding score, unsupported claim count, synthetic-data disclaimer presence, external-call prohibition, guardrail compliance, answer length, and domain relevance.

Results are written to `outputs/genai/assistant_evaluation.csv` and `outputs/genai/assistant_evaluation_summary.json`. The controlled run requires grounding and citation coverage of at least 0.90 and zero unsupported claims.
