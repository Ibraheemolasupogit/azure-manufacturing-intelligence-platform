# Prediction Intervals

Prediction intervals use an empirical absolute-residual quantile from rolling-origin backtests. The configured interval level is recorded in every forecast row.

Lower bounds are clipped at zero and never exceed the point forecast. Upper bounds are never below the point forecast. These intervals are deterministic residual bands, not calibrated probabilistic guarantees.
