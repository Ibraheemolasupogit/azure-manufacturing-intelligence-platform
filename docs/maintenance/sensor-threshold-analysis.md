# Sensor Threshold Analysis

Every equipment-health record preserves the governed source `threshold_status` and calculates an independent `calculated_threshold_status` from `measurement`, `warning_threshold`, and `critical_threshold`.

The pipeline records distance from warning and critical thresholds, normalized nearest-threshold distance, warning breach, critical breach, near-warning, near-critical, near-threshold, breach direction, margin percentage, and consistency flags. Source values are not overwritten.

The controlled run found 60 warning breaches, 9 critical breaches, 52 near-threshold observations, and 0 source/calculated threshold-status inconsistencies.
