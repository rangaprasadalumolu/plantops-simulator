"""Documented deterministic anomaly rules for synthetic demonstrations."""
MASS_BALANCE_TOLERANCE = 0.15
BLOCKAGE_FLOW_RATIO = 0.70
PUMP_DEGRADATION_FLOW_RATIO = 0.80
PRESSURE_HIGH_KPA = 650.0
FLOW_MIN_LPS = 0.0
FLOW_MAX_LPS = 250.0
LEVEL_MIN_PCT = 0.0
LEVEL_MAX_PCT = 100.0
SCENARIO_TYPES = ("normal", "leak", "blockage", "pump_degradation", "sensor_fault")
ALARM_SEVERITIES = ("info", "warning", "critical")
