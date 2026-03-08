"""
Area of Operation (AOO) / geofence for flight_ops.

Uses radial metric in xy: radius = sqrt(x^2 + y^2). z has separate bounds.
Reference hover point is (0,0,0). Land/autoland is handled by MDP, not AOO.
"""

from typing import Literal

import numpy as np

from . import config as config_module

_Direction = Literal["forward", "back", "right", "left", "up", "down"]
_DIRECTIONS: tuple[_Direction, ...] = ("forward", "back", "right", "left", "up", "down")


class AOO:
    """
    Area of Operation: radial geofence in xy, bounds in z.

    radius = sqrt(x^2 + y^2) <= AOO_RADIUS_MAX_CM. z in [z_min, z_max].
    """

    def __init__(self):
        self.radius_max_cm = config_module.AOO_RADIUS_MAX_CM
        self.z_min = config_module.AOO_Z_MIN_CM
        self.z_max = config_module.AOO_Z_MAX_CM
        self.move_min_cm = config_module.AOO_MOVE_MIN_CM

        self.current_x = 0
        self.current_y = 0
        self.current_z = 0

    def _radial_limit_for_axis(self, axis: Literal["x", "y"], sign: int) -> int:
        """Max allowed movement along axis before exceeding radial limit. sign: +1 or -1."""
        x, y = self.current_x, self.current_y
        r_sq_max = self.radius_max_cm * self.radius_max_cm

        if axis == "x":
            # Circle: x^2 + y^2 = R^2. Right edge x = +sqrt(R^2 - y^2), left x = -sqrt(R^2 - y^2)
            if y * y > r_sq_max:
                return 0
            x_edge = float(np.sqrt(r_sq_max - y * y))
            if sign > 0:  # right: remaining = x_edge - x
                remaining = x_edge - x
            else:  # left: remaining = x - (-x_edge)
                remaining = x + x_edge
        else:  # y
            if x * x > r_sq_max:
                return 0
            y_edge = float(np.sqrt(r_sq_max - x * x))
            if sign > 0:  # forward: remaining = y_edge - y
                remaining = y_edge - y
            else:  # back: remaining = y - (-y_edge)
                remaining = y + y_edge
        return max(0, int(remaining))

    def get_allowed_distance(self, direction: _Direction, requested_cm: int) -> int:
        """
        How much of a requested move is allowed before hitting the geofence.
        Returns 0 if no movement allowed.
        """
        if requested_cm <= 0:
            return 0

        if direction == "forward":
            remaining = self._radial_limit_for_axis("y", 1)
        elif direction == "back":
            remaining = self._radial_limit_for_axis("y", -1)
        elif direction == "right":
            remaining = self._radial_limit_for_axis("x", 1)
        elif direction == "left":
            remaining = self._radial_limit_for_axis("x", -1)
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
