"""
State extraction: convert VisionMeasurement + TelemetrySnapshot into DiscreteState.

Bucketization is explicit and readable; thresholds come from config.
"""

import numpy as np

from ..config.types import VisionMeasurement, TelemetrySnapshot, DiscreteState
from ..config import config_module as config


def bucket_aoo(x_error: float, y_error: float) -> str:
    """Bucket radial distance from center: r = sqrt(x^2 + y^2) -> centered, moderate, large."""
    r = np.sqrt(x_error**2 + y_error**2).item()
    if r <= config.AOO_RADIUS_SMALL:
        return "centered"
    if r <= config.AOO_RADIUS_LARGE:
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
    """Bucket confidence: lost, medium, good."""
    if confidence < 0.4:
        return "lost"
    if confidence < 0.7:
        return "medium"
    return "good"


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


def bucket_lost_duration(lost_duration_s: float) -> str:
    """Bucket time since target last visible: short, medium, long."""
    if lost_duration_s <= config.LOST_DURATION_SHORT_MAX:
        return "short"
    if lost_duration_s <= config.LOST_DURATION_MEDIUM_MAX:
        return "medium"
    return "long"


def target_visible(confidence: float) -> bool:
    """True if target is considered visible (above visibility threshold)."""
    return confidence >= config.CONFIDENCE_VISIBLE_THRESHOLD


def bucket_motion(motion_mag: float) -> str:
    """Bucket target motion from image-space delta: still, moving."""
    if motion_mag <= config.TARGET_MOTION_STILL_THRESHOLD:
        return "still"
    return "moving"


def at_reasonable_distance(distance: float) -> bool:
    """True if within ~20% of OPT_DIST_FROM_TARGET (the hover-at distance)."""
    target = config.OPT_DIST_FROM_TARGET
    tol = 0.2 * target
    return abs(distance - target) <= tol


def extract_discrete_state(
    measurement: VisionMeasurement,
    telemetry: TelemetrySnapshot,
    lost_duration_s: float = 0.0,
    motion_mag: float = 0.0,
) -> DiscreteState:
    """
    Convert raw measurement and telemetry into a DiscreteState for the MDP policy.

    Args:
        measurement: Vision measurement (x/y errors, distance, confidence).
        telemetry: Drone state (battery, altitude, latency, etc.).
        lost_duration_s: Seconds since target was last visible. 0 when visible.
        motion_mag: Magnitude of target motion (e.g. |dx|+|dy|). 0 when no prev.
    """
    return DiscreteState(
        target_visible=target_visible(measurement.confidence),
        aoo_bucket=bucket_aoo(measurement.x_error, measurement.y_error),
        distance_bucket=bucket_distance(measurement.distance),
        motion_bucket=bucket_motion(motion_mag),
        at_reasonable_distance=at_reasonable_distance(measurement.distance),
        confidence_bucket=bucket_confidence(measurement.confidence),
        altitude_bucket=bucket_altitude(telemetry.altitude_m),
        latency_bucket=bucket_latency(telemetry.latency_ms),
        battery_bucket=bucket_battery(telemetry.battery),
        lost_duration_bucket=bucket_lost_duration(lost_duration_s),
    )
