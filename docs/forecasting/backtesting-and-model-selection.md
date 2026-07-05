# Backtesting And Model Selection

Rolling-origin backtesting trains only on data available at each origin, predicts the configured horizon, and advances deterministically. The tracked smoke profile uses one short-window backtest; the extended governed profile is configured for three rolling-origin windows. Model comparison uses validation evidence only.

The implemented models are seasonal naive, moving average, linear regression, and random forest. Tie-breaking uses validation WAPE, validation MAE, absolute bias, model simplicity, and model name.
