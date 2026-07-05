# Forecasting Limitations

The tracked controlled sample has only 14 demand dates. It is suitable for deterministic smoke validation, feature generation, lineage, and portfolio evidence, but not for strong forecasting-performance claims.

For credible rolling-origin evidence, run the extended governed preparation profile under `.generated/forecasting/`, then use `configs/forecasting_extended.yaml`. The expected extended sales-order quarantine count is zero. Unexpected sales-order quarantine fails preparation unless deliberate invalid-record injection is explicitly configured and documented; no such injection is implemented in Milestone 4.

Milestone 4 does not implement inventory optimisation, reorder recommendations, dashboards, GenAI, Azure Machine Learning jobs, model endpoints, or cloud deployment.
