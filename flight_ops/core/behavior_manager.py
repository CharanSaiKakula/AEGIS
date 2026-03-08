"""
Behavior manager: map MissionState to high-level command and interface signals.

Separates "what mode am I in?" from "what exact command do I send?" and
from "do we need takeoff/land from the drone API?".
"""

from ..config.types import (
    MissionState,
    ControlCommand,
    VisionMeasurement,
    TelemetrySnapshot,
)
from ..config import config_module as config
from ..control.controller import follow_control, hover_command, search_command, center_command


def get_behavior_command(
    state: MissionState,
    measurement: VisionMeasurement,
    telemetry: TelemetrySnapshot,
) -> ControlCommand:
    """
    Return the RC command for the current mission state.
    Does not perform takeoff/land; caller uses request_takeoff / request_land for that.
    """
    if state == MissionState.TAKEOFF:
        return hover_command()

    if state == MissionState.FOLLOW:
        return follow_control(measurement, desired_distance_m=config.OPT_DIST_FROM_TARGET)

    if state == MissionState.SEARCH:
        return search_command()

    if state == MissionState.CENTER:
        return center_command(measurement)

    if state == MissionState.REACQUIRE:
        return hover_command()

    if state == MissionState.HOVER:
        return hover_command()

    if state == MissionState.LAND:
        return hover_command()

    return hover_command()


def request_takeoff(state: MissionState) -> bool:
    """True if the mission layer should send a takeoff command to the drone."""
    return state == MissionState.TAKEOFF


def request_land(state: MissionState) -> bool:
    """True if the mission layer should send a land command to the drone."""
    return state == MissionState.LAND
