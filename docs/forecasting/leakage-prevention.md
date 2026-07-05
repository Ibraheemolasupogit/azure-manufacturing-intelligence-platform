# Leakage Prevention

Feature generation shifts target-derived values before lag and rolling calculations. Lag and rolling features use only earlier demand dates. Chronological splits are used throughout; random train-test splitting is not used.

The model feature set excludes actual delivery date, fulfilled quantity, order value, and final order status. Categorical encoders and model parameters are fitted only on the training window available at the relevant forecast origin.
