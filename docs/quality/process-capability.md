# Process Capability

Capability is calculated only for comparable groups:

```text
product_id + quality_metric + measurement_unit + plant_id + production_line_id
```

Groups must have stable specification limits and at least the configured minimum
observations.

```text
Cp = (USL - LSL) / (6 * standard_deviation)
Cpk = min((USL - mean) / (3 * standard_deviation),
          (mean - LSL) / (3 * standard_deviation))
```

Zero standard deviation and insufficient observations are reported as unavailable
statuses. Capability values are diagnostics only and do not prove process
stability.
