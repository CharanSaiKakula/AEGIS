"""
State extraction: convert VisionMeasurement + TelemetrySnapshot into DiscreteState.

Bucketization is explicit and readable; thresholds come from config.
"""

from ..config.types import VisionMeasurement, TelemetrySnapshot, DiscreteState
from ..config import config_module as config


def bucket_x_error(x_error: float) -> str:
    """Bucket horizontal error: centered, moderate, large."""
    abs_x = abs(x_error)
    if abs_x <= config.X_ERROR_SMALL:
        return "centered"
    if abs_x <= config.X_ERROR_LARGE:
        return "moderate"
    return "large"


def bucket_y_error(y_error: float) -> str:
    """Bucket vertical error: centered, moderate, large."""
    abs_y = abs(y_error)
    if abs_y <= config.Y_ERROR_SMALL:
        return "centered"
    if abs_y <= config.Y_ERROR_LARGE:
        return "moderate"
    return "large"


def bucket_distance(distance: float) -> str:
    """Bucket distance: near, good, far."""
    if distance <= config.DISTANCE_NEAR_MAX:
        return "near"
    if distance >= config.DISTANCE_FAR_MIN:
        return "far"
    return "good"


def bucket_confidence(confidence: float) -> str:
    """Bucket confidence: low, medium, high."""
    if confidence < 0.4:
        return "low"
    if confidence < 0.7:
        return "medium"
    return "high"


def bucket_altitude(altitude_m: float) -> str:
    """Bucket altitude: low, safe, high."""
    if altitude_m < config.ALTITUDE_LOW_MAX:
        return "low"
    if altitude_m >= config.ALTITUDE_HIGH_MIN:
        return "high"
    return "safe"


def bucket_latency(latency_ms: float) -> str:
    """Bucket latency: nominal, degraded, critical."""
    if latency_ms >= config.LATENCY_CRITICAL_MS:
        return "critical"
    if latency_ms >= config.LATENCY_DEGRADED_MS:
        return "degraded"
    return "nominal"


def bucket_battery(battery_pct: float) -> str:
    """Bucket battery: normal, low, critical."""
    if battery_pct <= config.BATTERY_CRITICAL_PCT:
        return "critical"
    if battery_pct <= config.BATTERY_LOW_PCT:
        return "low"
    return "normal"


def target_visible(confidence: float) -> bool:
    """True if target is considered visible (above visibility threshold)."""
    return confidence >= config.CONFIDENCE_VISIBLE_THRESHOLD


def extract_discrete_state(
    measurement: VisionMeasurement, telemetry: TelemetrySnapshot
) -> DiscreteState:
    """
    Convert raw measurement and telemetry into a DiscreteState for the MDP policy.
    """
    return DiscreteState(
        target_visible=target_visible(measurement.confidence),
        x_bucket=bucket_x_error(measurement.x_error),
        y_bucket=bucket_y_error(measurement.y_error),
        distance_bucket=bucket_distance(measurement.distance),
        confidence_bucket=bucket_confidence(measurement.confidence),
        altitude_bucket=bucket_altitude(telemetry.altitude_m),
        latency_bucket=bucket_latency(telemetry.latency_ms),
        battery_bucket=bucket_battery(telemetry.battery),
    )
