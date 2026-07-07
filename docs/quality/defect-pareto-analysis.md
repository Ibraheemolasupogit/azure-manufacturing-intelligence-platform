# Defect Pareto Analysis

Defect Pareto rows are generated for:

- defect category
- severity
- product
- plant
- production line
- machine
- batch
- quality metric

Only failed inspections or rows with defective units contribute to Pareto counts.
Passing inspections do not receive invented defect categories. Rows are sorted by
defect count descending, defective units descending, and category value ascending.

The output records defect count, defective units, percentage of total, cumulative
percentage, and deterministic rank.
