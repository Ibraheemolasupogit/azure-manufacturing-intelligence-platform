# Evaluation Metrics

Milestone 4 calculates MAE, RMSE, WAPE, sMAPE, forecast bias, and absolute forecast bias.

WAPE is `sum(abs(actual - forecast)) / sum(abs(actual))`; when the denominator is zero, WAPE is reported as null. sMAPE handles zero actual and forecast values by contributing zero for that row. Accuracy percentages are not reported.
