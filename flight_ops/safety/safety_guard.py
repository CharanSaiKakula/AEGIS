"""
Hard safety overrides above the MDP. If safety says land, the mission must
transition to LAND and stay there; the policy cannot override.
"""

from ..config.types import TelemetrySnapshot
from ..config import config_module as config


def should_force_land(telemetry: TelemetrySnapshot) -> bool:
    """True if safety requires an immediate transition to LAND."""
    safe, _ = check_safety(telemetry)
    return not safe


def _altitude_for_safety(t: TelemetrySnapshot) -> float:
    """Altitude in meters for safety check. Uses TOF indoors when configured."""
    if config.USE_TOF_FOR_ALTITUDE and t.tof_cm >= 5:
        return t.tof_cm / 100.0
    return t.altitude_m


def check_safety(telemetry: TelemetrySnapshot) -> tuple[bool, str | None]:
    """
    Check whether it is safe to continue. Safety sits above the MDP.

    Returns:
        (safe_to_continue, reason)
        - If safe_to_continue is False, reason describes why (e.g. "battery_critical").
        - If safe_to_continue is True, reason is None.
    """
    t = telemetry

    if not t.link_ok:
        return False, "link_lost"

    if t.battery <= config.BATTERY_CRITICAL_PCT:
        return False, "battery_critical"

    if t.latency_ms >= config.LATENCY_CRITICAL_MS:
        return False, "latency_critical"

    alt_m = _altitude_for_safety(t)
    if alt_m >= config.ALTITUDE_HARD_MAX:
        return False, "altitude_over_max"

    if t.mission_time_s >= config.MISSION_TIME_MAX_S:
        return False, "mission_time_max"

    return True, None
