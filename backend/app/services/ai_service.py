from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt
from typing import Any


FEATURE_NAMES = [
    "sequence_violation",
    "geo_implausibility",
    "duplicate_scan_count",
    "time_gap_anomaly",
    "unexpected_custodian",
    "temperature_violation",
    "temperature_duration",
    "shock_anomaly",
    "sensor_gap",
    "sensor_provenance_mismatch",
]

LIFECYCLE_ORDER = {
    "manufactured": 0,
    "inspected": 1,
    "shipped": 2,
    "received": 3,
    "sold": 4,
}

TEMP_MIN = 18.0
TEMP_MAX = 26.0
SHOCK_THRESHOLD_G = 3.0
MAX_PLAUSIBLE_KMH = 900.0
MAX_SENSOR_GAP_HOURS = 2.0


def _timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _distance_km(first: dict[str, Any], second: dict[str, Any]) -> float | None:
    try:
        lat1, lon1 = float(first["latitude"]), float(first["longitude"])
        lat2, lon2 = float(second["latitude"]), float(second["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi, dlambda = radians(lat2 - lat1), radians(lon2 - lon1)
    value = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 6371.0 * 2 * atan2(sqrt(value), sqrt(1 - value))


def _feature_values(
    event_data: dict[str, Any],
    prior_events: list[dict[str, Any]],
    iot_readings: list[dict[str, Any]],
    duplicate_scan_count: int,
) -> dict[str, Any]:
    current_type = str(event_data.get("event_type", "")).lower()
    current_index = LIFECYCLE_ORDER.get(current_type, -1)
    sequence_violation = any(
        LIFECYCLE_ORDER.get(str(item.get("event_type", "")).lower(), -1) > current_index
        for item in prior_events
    ) if current_index >= 0 else False

    geo_implausibility = False
    time_gap_anomaly = False
    if prior_events:
        previous = prior_events[-1]
        previous_time = _timestamp(previous.get("timestamp"))
        current_time = _timestamp(event_data.get("timestamp"))
        if previous_time and current_time:
            elapsed_hours = (current_time - previous_time).total_seconds() / 3600
            distance = _distance_km(previous, event_data)
            geo_implausibility = bool(distance is not None and elapsed_hours > 0 and distance / elapsed_hours > MAX_PLAUSIBLE_KMH)
            previous_type = str(previous.get("event_type", "")).lower()
            time_gap_anomaly = elapsed_hours < 1 / 60 or elapsed_hours > (72 if (previous_type, current_type) == ("shipped", "received") else 14 * 24)
            if elapsed_hours < 0:
                time_gap_anomaly = True

    valid_readings = []
    for reading in iot_readings:
        timestamp = _timestamp(reading.get("timestamp"))
        try:
            valid_readings.append((timestamp, float(reading["temperature"]), float(reading["accel_magnitude"])))
        except (KeyError, TypeError, ValueError):
            continue

    temperature_violation = any(temp < TEMP_MIN or temp > TEMP_MAX for _, temp, _ in valid_readings)
    shock_anomaly = any(accel > SHOCK_THRESHOLD_G for _, _, accel in valid_readings)
    temperature_duration = 0.0
    for previous, current in zip(valid_readings, valid_readings[1:]):
        if previous[0] and current[0] and (previous[1] < TEMP_MIN or previous[1] > TEMP_MAX) and (current[1] < TEMP_MIN or current[1] > TEMP_MAX):
            temperature_duration += max(0.0, (current[0] - previous[0]).total_seconds() / 3600)
    event_time = _timestamp(event_data.get("timestamp"))
    latest_reading = max((item[0] for item in valid_readings if item[0]), default=None)
    sensor_gap = bool(event_time and latest_reading and event_data.get("_unit_status") == "in_transit" and (event_time - latest_reading).total_seconds() > MAX_SENSOR_GAP_HOURS * 3600)
    sensor_mismatch = bool(event_data.get("_unit_status") in {"delivered", "sold"} and len(valid_readings) >= 3 and sum(item[2] for item in valid_readings) / len(valid_readings) > 1.5)

    return {
        "sequence_violation": sequence_violation,
        "geo_implausibility": geo_implausibility,
        "duplicate_scan_count": duplicate_scan_count,
        "time_gap_anomaly": time_gap_anomaly,
        "unexpected_custodian": event_data.get("actor_organization_id") is not None and event_data.get("_current_custodian_org_id") is not None and str(event_data["actor_organization_id"]) != str(event_data["_current_custodian_org_id"]),
        "temperature_violation": temperature_violation,
        "temperature_duration": min(5.0, temperature_duration),
        "shock_anomaly": shock_anomaly,
        "sensor_gap": sensor_gap,
        "sensor_provenance_mismatch": sensor_mismatch,
    }


def score_event(
    event_data: dict[str, Any],
    prior_events: list[dict[str, Any]] | None = None,
    iot_readings: list[dict[str, Any]] | None = None,
    duplicate_scan_count: int = 0,
) -> dict[str, Any]:
    """Score lifecycle provenance using the notebook's ten-feature engine."""
    prior_events = prior_events or []
    iot_readings = iot_readings or []
    features = _feature_values(event_data, prior_events, iot_readings, duplicate_scan_count)
    contributions: dict[str, float] = {}
    weights = {
        "sequence_violation": 45,
        "geo_implausibility": 45,
        "time_gap_anomaly": 25,
        "unexpected_custodian": 40,
        "temperature_violation": 40,
        "shock_anomaly": 35,
        "sensor_gap": 20,
        "sensor_provenance_mismatch": 45,
    }
    for name, weight in weights.items():
        if features[name]:
            contributions[name] = float(weight)
    if features["duplicate_scan_count"] > 1:
        contributions["duplicate_scan_count"] = min(60, 35 + (features["duplicate_scan_count"] - 1) * 8)
    if features["temperature_duration"] > 0:
        contributions["temperature_duration"] = min(20, features["temperature_duration"] * 4)
    iot_keys = {"temperature_violation", "temperature_duration", "shock_anomaly", "sensor_gap", "sensor_provenance_mismatch"}
    iot_total = sum(value for name, value in contributions.items() if name in iot_keys)
    if iot_total > 60:
        for name in iot_keys:
            if name in contributions:
                contributions[name] *= 60 / iot_total
    score = min(100, round(sum(contributions.values())))
    level = "High" if score >= 65 else "Medium" if score >= 35 else "Low"
    top = sorted(contributions.items(), key=lambda item: item[1], reverse=True)[:2]
    reasons = []
    reason_map = {
        "sequence_violation": "Lifecycle event sequence is out of order",
        "geo_implausibility": "Location movement exceeds plausible transport speed",
        "duplicate_scan_count": f"QR code scanned {duplicate_scan_count} times; possible label cloning",
        "time_gap_anomaly": "Unusual time gap between lifecycle events",
        "unexpected_custodian": "Event actor differs from the current custodian",
        "temperature_violation": "Temperature is outside the configured 18-26 C range",
        "temperature_duration": "Temperature remained outside the permitted range",
        "shock_anomaly": "Shock magnitude exceeds the configured threshold",
        "sensor_gap": "IoT telemetry gap detected during transit",
        "sensor_provenance_mismatch": "Sensor motion conflicts with the recorded product status",
    }
    for name, _ in top:
        reasons.append(reason_map[name])
    return {
        "risk_score": score,
        "risk_level": level,
        "reason": "; ".join(reasons) if reasons else "No significant provenance anomaly detected",
        "feature_values": features,
        "contributions": contributions,
        "model_version": "notebook_deterministic_v1",
    }


def score_iot_reading(temperature: float, accel_magnitude: float) -> dict[str, Any]:
    """Score cold-chain temperature and acceleration anomalies deterministically."""
    risk_score = 0
    reasons: list[str] = []

    temperature = float(temperature)
    accel_magnitude = float(accel_magnitude)

    if temperature > 26.0 or temperature < 15.0:
        risk_score += 50
        reasons.append("temperature_violation")

    if accel_magnitude > 3.0:
        risk_score += 40
        reasons.append("shock_anomaly")

    risk_score = min(risk_score, 100)
    if risk_score >= 70:
        risk_level = "High"
    elif risk_score >= 35:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reason": ", ".join(reasons) if reasons else "No IoT anomaly detected",
        "feature_values": {
            "temperature": temperature,
            "accel_magnitude": accel_magnitude,
        },
        "model_version": "1.0-deterministic",
    }


def infer_risk(
    event_history: list[dict[str, Any]],
    current_event: dict[str, Any],
    iot_readings: list[dict[str, Any]],
) -> dict[str, Any]:
    return score_event(current_event, event_history, iot_readings)