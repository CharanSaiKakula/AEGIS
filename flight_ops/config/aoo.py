"""
Area of Operation (AOO) / geofence for flight_ops.

Tracks software position (x, y, z in cm) relative to reference hover point (0,0,0)
and clips movement commands to stay within bounds from config.py.
Land/autoland is handled by MDP, not AOO.
"""

from typing import Literal

from . import config as config_module

_Direction = Literal["forward", "back", "right", "left", "up", "down"]
_DIRECTIONS: tuple[_Direction, ...] = ("forward", "back", "right", "left", "up", "down")


class AOO:
    """
    Area of Operation: geofence bounds and position tracking.

    Reference hover point is (0,0,0). x=left/right, y=forward/back, z=up/down.
    """

    def __init__(self):
        self.x_min = config_module.AOO_X_MIN_CM
        self.x_max = config_module.AOO_X_MAX_CM
        self.y_min = config_module.AOO_Y_MIN_CM
        self.y_max = config_module.AOO_Y_MAX_CM
        self.z_min = config_module.AOO_Z_MIN_CM
        self.z_max = config_module.AOO_Z_MAX_CM
        self.move_min_cm = config_module.AOO_MOVE_MIN_CM

        self.current_x = 0
        self.current_y = 0
        self.current_z = 0

    def get_allowed_distance(self, direction: _Direction, requested_cm: int) -> int:
        """
        How much of a requested move is allowed before hitting the geofence.
        Returns 0 if no movement allowed.
        """
        if requested_cm <= 0:
            return 0

        if direction == "forward":
            remaining = self.y_max - self.current_y
        elif direction == "back":
            remaining = self.current_y - self.y_min
        elif direction == "right":
            remaining = self.x_max - self.current_x
        elif direction == "left":
            remaining = self.current_x - self.x_min
        elif direction == "up":
            remaining = self.z_max - self.current_z
        elif direction == "down":
            remaining = self.current_z - self.z_min
        else:
            return 0

        if remaining <= 0:
            return 0
        return min(requested_cm, remaining)

    def clip_move(
        self, direction: _Direction, requested_cm: int
    ) -> tuple[int, bool]:
        """
        Clip requested move to geofence. Returns (allowed_cm, can_execute).
        can_execute is False if allowed_cm < move_min_cm (Tello needs ~20 cm minimum).
        """
        allowed = self.get_allowed_distance(direction, requested_cm)
        can_execute = allowed >= self.move_min_cm
        return (allowed, can_execute)

    def update_position(self, direction: _Direction, moved_cm: int) -> None:
        """Update tracked position after a successful move."""
        if direction == "forward":
            self.current_y += moved_cm
        elif direction == "back":
            self.current_y -= moved_cm
        elif direction == "right":
            self.current_x += moved_cm
        elif direction == "left":
            self.current_x -= moved_cm
        elif direction == "up":
            self.current_z += moved_cm
        elif direction == "down":
            self.current_z -= moved_cm

    def position(self) -> tuple[int, int, int]:
        """Return (x, y, z) in cm."""
        return (self.current_x, self.current_y, self.current_z)

    def reset_position(self) -> None:
        """Reset to reference hover point (e.g. after takeoff)."""
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0


def execute_geofenced_move(tello, aoo: AOO, direction: _Direction, requested_cm: int) -> bool:
    """
    Apply geofence, send discrete move to Tello if allowed.
    Returns True if move was executed, False if blocked by geofence.
    """
    allowed, can_execute = aoo.clip_move(direction, requested_cm)
    if not can_execute:
        return False

    if direction == "forward":
        tello.move_forward(allowed)
    elif direction == "back":
        tello.move_back(allowed)
    elif direction == "right":
        tello.move_right(allowed)
    elif direction == "left":
        tello.move_left(allowed)
    elif direction == "up":
        tello.move_up(allowed)
    elif direction == "down":
        tello.move_down(allowed)
    else:
        return False

    aoo.update_position(direction, allowed)
    return True
