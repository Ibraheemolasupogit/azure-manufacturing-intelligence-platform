# Control Charts And SPC Rules

Control-chart points use expanding historical prior observations within
`machine_id + quality_metric + measurement_unit` groups. A point's operational
baseline does not use future observations.

```text
center_line = mean(prior_values)
upper_control_limit = center_line + sigma * prior_standard_deviation
lower_control_limit = center_line - sigma * prior_standard_deviation
```

Implemented SPC rules:

- `SPC_RULE_1`: one point beyond configured control limits.
- `SPC_RULE_2`: two of three consecutive points beyond two standard deviations on
  the same side.
- `SPC_RULE_3`: four of five consecutive points beyond one standard deviation on
  the same side.
- `SPC_RULE_4`: eight consecutive points on the same side of the center line.

Insufficient history produces no signal and is recorded explicitly.
