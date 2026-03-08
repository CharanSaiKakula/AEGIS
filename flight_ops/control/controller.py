"""
High-level outer-loop controller for FOLLOW, HOVER, and SEARCH.

This layer produces RC-style commands (lr, fb, ud, yaw) that are sent via
send_rc_control. The Tello firmware handles the inner attitude/motor loop.
"""

from ..config.types import VisionMeasurement, ControlCommand
from ..config import config_module as config


def clamp(value: float, lo: int, hi: int) -> int:
    """Clamp to integer in [lo, hi]."""
    return max(lo, min(hi, int(round(value))))


def follow_control(measurement: VisionMeasurement) -> ControlCommand:
    """
    Visual servo for FOLLOW: yaw from x_error, vertical from y_error,
    forward/back from (distance - desired_distance). Left/right = 0 for simplicity.
    """
    yaw = clamp(measurement.x_error * config.YAW_GAIN, config.CMD_MIN, config.CMD_MAX)
    ud = clamp(-measurement.y_error * config.VERTICAL_GAIN, config.CMD_MIN, config.CMD_MAX)
    dist_error = measurement.distance - config.DESIRED_DISTANCE_M
    fb = clamp(-dist_error * config.FORWARD_GAIN, config.CMD_MIN, config.CMD_MAX)
    lr = 0
    return ControlCommand(lr=lr, fb=fb, ud=ud, yaw=yaw)


def hover_command() -> ControlCommand:
    """Zero velocities: hold position."""
    return ControlCommand(lr=0, fb=0, ud=0, yaw=0)


def search_command() -> ControlCommand:
    """Slow yaw scan to reacquire target; no forward/up/down."""
    return ControlCommand(
        lr=0,
        fb=0,
        ud=0,
        yaw=config.SEARCH_YAW_SPEED,
    )
