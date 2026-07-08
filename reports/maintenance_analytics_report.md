# Predictive Maintenance Analytics Report

Maintenance run ID: `MAINT-f281a27e7d014de8`

This report is deterministic decision-support evidence from synthetic governed inputs. Failure-risk scores are heuristic 0-100 scores, not calibrated probabilities or certified safety instructions.

## KPI summary

- alert_count: 135
- critical_breach_count: 9
- critical_risk_alert_count: 0
- degradation_signal_count: 59
- equipment_records_processed: 504
- high_risk_alert_count: 7
- isolation_forest_anomaly_count: 0
- machines_represented: 18
- near_threshold_observations: 52
- robust_z_anomaly_count: 0
- sensor_types_represented: 2
- sensors_represented: 36
- threshold_status_inconsistency_count: 0
- warning_breach_count: 60

## Top maintenance alerts

| alert_id | sensor_event_id | machine_id | sensor_type | failure_risk_score | risk_level | recommended_action |
| --- | --- | --- | --- | --- | --- | --- |
| MA-743563a7e40b | EH-000477 | MACH-01-02-02 | vibration | 76.3706760154765 | high | prioritise_non_binding_maintenance_review |
| MA-8250f444a5e7 | EH-000424 | MACH-03-01-02 | temperature | 75.27598606682099 | high | prioritise_non_binding_maintenance_review |
| MA-771ab1ab3ba7 | EH-000371 | MACH-01-02-03 | vibration | 71.5483884087287 | high | prioritise_non_binding_maintenance_review |
| MA-a8e176f92845 | EH-000318 | MACH-03-01-03 | temperature | 69.62073023783253 | high | prioritise_non_binding_maintenance_review |
| MA-7851ef57f655 | EH-000212 | MACH-03-02-01 | temperature | 67.8945428116079 | high | prioritise_non_binding_maintenance_review |
| MA-7d4bd9f9061d | EH-000265 | MACH-02-01-01 | vibration | 62.711210200704045 | high | prioritise_non_binding_maintenance_review |
| MA-96fec773c729 | EH-000159 | MACH-02-01-02 | vibration | 61.23759599415051 | high | prioritise_non_binding_maintenance_review |
| MA-f856a37d8dd1 | EH-000373 | MACH-02-01-01 | vibration | 29.666804292544526 | low | review_degradation_trend |
| MA-6943fad062bb | EH-000449 | MACH-02-01-03 | vibration | 29.099342827029698 | low | monitor_near_threshold_sensor |
| MA-cc131f2b2252 | EH-000215 | MACH-03-02-03 | vibration | 28.728685051297045 | low | review_degradation_trend |
| MA-2bb318816bd4 | EH-000501 | MACH-03-02-02 | vibration | 28.584826857738314 | low | monitor_near_threshold_sensor |
| MA-cb4488f3a935 | EH-000471 | MACH-01-01-02 | vibration | 28.382063262053627 | low | monitor_near_threshold_sensor |
| MA-6f2fbe7e2a61 | EH-000499 | MACH-03-02-01 | vibration | 28.31659690099651 | low | monitor_near_threshold_sensor |
| MA-807cf85a44b1 | EH-000491 | MACH-02-02-03 | vibration | 28.249694904464178 | low | monitor_near_threshold_sensor |
| MA-2685d7d51f88 | EH-000181 | MACH-01-01-01 | vibration | 28.091649590957008 | low | review_degradation_trend |
| MA-dfd1ae037931 | EH-000199 | MACH-02-02-01 | vibration | 27.834199318668748 | low | review_degradation_trend |
| MA-a18a67af9d38 | EH-000493 | MACH-03-01-01 | vibration | 27.744198831853446 | low | monitor_near_threshold_sensor |
| MA-f2947538d163 | EH-000354 | MACH-03-01-03 | temperature | 27.732911290040107 | low | review_degradation_trend |
| MA-50c98124ca90 | EH-000333 | MACH-01-02-02 | vibration | 27.1007762841731 | low | monitor_near_threshold_sensor |
| MA-9d2d00985aee | EH-000390 | MACH-03-01-03 | temperature | 26.890759270740297 | low | review_degradation_trend |

## Method notes

- Threshold compliance preserves both source and calculated threshold status.
- Degradation uses chronological rolling statistics and does not use future observations for operational scoring.
- Robust z-score uses `0.6745 * (x - median) / MAD` where sufficient prior history exists.
- Isolation Forest is deterministic and retrospective; its score is a relative anomaly diagnostic, not a probability.
- Investigation context is analytical context only and does not assert root cause.
