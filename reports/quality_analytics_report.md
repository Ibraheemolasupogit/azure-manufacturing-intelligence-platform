# Quality Analytics Report

- Quality run ID: `QUALITY-ea15caf8c05763b0`
- Quality records processed: 168
- Specification failures: 26
- Near-limit observations: 5
- Robust-z anomalies: 2
- Isolation Forest anomalies: 12
- High-risk alerts: 6
- Critical-risk alerts: 4

## Top Alerts

| Risk | Inspection | Product | Machine | Metric | Action |
| --- | --- | --- | --- | --- | --- |
| critical | QC-000153-1 | PROD-006 | MACH-02-01-03 | diameter_mm | investigate_specification_failure |
| critical | QC-000138-1 | PROD-006 | MACH-03-02-03 | diameter_mm | investigate_specification_failure |
| critical | QC-000103-1 | PROD-008 | MACH-01-01-01 | surface_finish_ra | investigate_specification_failure |
| critical | QC-000066-1 | PROD-008 | MACH-03-02-03 | diameter_mm | investigate_specification_failure |
| high | QC-000123-1 | PROD-006 | MACH-02-01-03 | diameter_mm | investigate_specification_failure |
| high | QC-000006-1 | PROD-007 | MACH-03-02-03 | diameter_mm | investigate_specification_failure |
| high | QC-000042-1 | PROD-006 | MACH-03-02-03 | diameter_mm | investigate_specification_failure |
| high | QC-000021-1 | PROD-007 | MACH-02-01-03 | diameter_mm | investigate_specification_failure |
| high | QC-000004-1 | PROD-005 | MACH-02-02-01 | surface_finish_ra | investigate_specification_failure |
| high | QC-000148-1 | PROD-001 | MACH-02-02-01 | surface_finish_ra | investigate_specification_failure |
| low | QC-000107-1 | PROD-004 | MACH-03-01-02 | torque_nm | review_process_control_signal |
| low | QC-000083-1 | PROD-002 | MACH-03-01-02 | torque_nm | review_process_control_signal |
| low | QC-000086-1 | PROD-006 | MACH-01-02-02 | torque_nm | review_anomalous_quality_measurement |
| low | QC-000030-1 | PROD-001 | MACH-03-02-03 | diameter_mm | monitor_near_limit_quality_metric |
| low | QC-000009-1 | PROD-002 | MACH-02-01-03 | diameter_mm | monitor_near_limit_quality_metric |
| low | QC-000070-1 | PROD-004 | MACH-02-02-01 | surface_finish_ra | monitor_near_limit_quality_metric |
| low | QC-000163-1 | PROD-001 | MACH-01-01-01 | surface_finish_ra | monitor_near_limit_quality_metric |
| low | QC-000010-1 | PROD-003 | MACH-02-02-01 | surface_finish_ra | monitor_near_limit_quality_metric |
| low | QC-000125-1 | PROD-008 | MACH-03-01-02 | torque_nm | review_anomalous_quality_measurement |
| low | QC-000032-1 | PROD-003 | MACH-01-02-02 | torque_nm | review_anomalous_quality_measurement |

## Notes

- Quality-risk scores are deterministic heuristic scores, not calibrated probabilities.
- Investigation context is analytical context, not root-cause proof.
- No Azure services are deployed or called by this milestone.
