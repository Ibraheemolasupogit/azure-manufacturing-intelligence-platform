# Specification And Yield Metrics

For each quality record:

```text
within_specification =
  lower_specification_limit <= measured_value <= upper_specification_limit
```

The pipeline records distance from each limit, normalised distance to the nearest
limit, near-limit flags, warning-limit flags, source inspection result, calculated
specification result, and a consistency flag. Source results are not overwritten.

Yield context comes from production events joined by `batch_id`.

```text
production_yield = accepted_quantity / produced_quantity
scrap_rate = rejected_quantity / produced_quantity
first_pass_yield_proxy = accepted_quantity / produced_quantity
```

Because explicit rework fields are not available, first-pass yield is labelled as
a proxy and is not presented as exact first-pass yield.
