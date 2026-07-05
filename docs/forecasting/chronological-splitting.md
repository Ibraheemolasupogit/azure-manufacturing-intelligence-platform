# Chronological Splitting

The controlled run uses training, validation, held-out test, and future forecast periods in strict chronological order. Validation metrics select the model. Held-out test metrics are reported only after selection and do not alter the selected model.

Future forecast dates start after the final observed demand date.
