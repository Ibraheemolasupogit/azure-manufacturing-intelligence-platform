# Degradation Analysis

Degradation features are calculated chronologically by `machine_id + sensor_type + measurement_unit`. Rolling means, maxima, standard deviations, and slope features use only prior or current observations, avoiding future leakage for operational alert scoring.

The configured minimum history is 5 observations. Records with less history are labelled `insufficient_history`. Rising vibration and temperature trends increase risk; falling pressure sensor types are supported in configuration for future schemas.

The controlled run generated 59 degradation signals. Runtime and service outputs use explicit proxy assumptions because no real maintenance schedule exists in the synthetic source data.
