"""
Tello movement executor: takeoff, land, apply RC commands.

All Tello move commands are managed here; main and decision scripts call this layer
instead of invoking tello.takeoff() / tello.land() / send_rc_control directly.
"""

from ..config.types import ControlCommand


def takeoff(tello) -> None:
    """Execute takeoff."""
    tello.takeoff()


def move_up(tello, cm: int | float) -> None:
    """Move up by cm (20-500)."""
    # tello.move_up(min(500, max(20, int(cm))))
    tello.move_up(cm)


def land(tello) -> None:
    """Execute land."""
    tello.land()


def apply_command(tello, cmd: ControlCommand) -> None:
    """Send RC command to Tello via send_rc_control(lr, fb, ud, yaw)."""
    tello.send_rc_control(cmd.lr, cmd.fb, cmd.ud, cmd.yaw)
