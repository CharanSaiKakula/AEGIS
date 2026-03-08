"""
High-level outer-loop controller for FOLLOW, HOVER, and SEARCH.

Designed for active slow-rate control: instantiate, then call .step() or
.follow()/.hover()/.search() at your control loop rate (e.g. 5–20 Hz).
Follow mode uses a Smith predictor with exponential velocity smoothing.
The Tello firmware handles the inner attitude/motor loop.
"""

import time

from ..config.types import VisionMeasurement, ControlCommand, MissionState
from ..config import config_module as config


def _clamp(value: float, lo: int, hi: int) -> int:
    """Clamp to integer in [lo, hi]."""
    return max(lo, min(hi, int(round(value))))


def _exponential_smooth(v_raw: float, v_prev: float, alpha: float) -> float:
    """Exponential smoother: v = α*v_raw + (1-α)*v_prev."""
    return alpha * v_raw + (1.0 - alpha) * v_prev


class TelloController:
    """
    High-level slow-rate controller producing RC commands for the Tello.

    Call .step(mode, measurement) or .follow()/.hover()/.search() each control
    tick. Gains and limits come from config. Use .set_abort(True) to exit follow
    and return hover; safety is arbitrated by the caller.
    """

    def __init__(self):
        self.yaw_gain = config.YAW_GAIN
        self.vertical_gain = config.VERTICAL_GAIN
        self.forward_gain = config.FORWARD_GAIN
        self.desired_distance_m = config.DESIRED_DISTANCE_M
        self.search_yaw_speed = config.SEARCH_YAW_SPEED
        self.cmd_min = config.CMD_MIN
        self.cmd_max = config.CMD_MAX
        self.tau_s = config.SMITH_TAU_S
        self.filter_alpha = config.VELOCITY_FILTER_ALPHA

        # Smith predictor state
        self._x_prev: float = 0.0
        self._y_prev: float = 0.0
        self._d_prev: float = 0.0
        self._vx_img_prev: float = 0.0
        self._vy_img_prev: float = 0.0
        self._vd_prev: float = 0.0
        self._last_t: float | None = None
        self._initialized: bool = False

        # Abort flag: when True, controller exits and returns hover; access via set_abort()
        self._abort: bool = False

    def set_abort(self, value: bool) -> None:
        """Set abort flag. When True, follow() returns hover until set to False."""
        self._abort = value

    def _reset_follow_state(self) -> None:
        """Reset Smith predictor state (e.g. after target loss)."""
        self._initialized = False

    def _smith_predict(self, measurement: VisionMeasurement) -> tuple[float, float, float]:
        """
        Shared Smith predictor: returns (x_pred, y_pred, d_pred) for delay compensation.
        Used by both follow() and center().
        """
        x = measurement.x_error
        y = measurement.y_error
        d = measurement.distance

        now = time.monotonic()
        dt = 0.1
        if self._last_t is not None:
            dt = max(0.01, min(0.5, now - self._last_t))
        self._last_t = now

        if self._initialized:
            vx_img_raw = (x - self._x_prev) / dt
            vy_img_raw = (y - self._y_prev) / dt
            vd_raw = (d - self._d_prev) / dt
        else:
            vx_img_raw = vy_img_raw = vd_raw = 0.0
            self._initialized = True

        vx_img = _exponential_smooth(vx_img_raw, self._vx_img_prev, self.filter_alpha)
        vy_img = _exponential_smooth(vy_img_raw, self._vy_img_prev, self.filter_alpha)
        vd = _exponential_smooth(vd_raw, self._vd_prev, self.filter_alpha)

        self._vx_img_prev = vx_img
        self._vy_img_prev = vy_img
        self._vd_prev = vd
        self._x_prev = x
        self._y_prev = y
        self._d_prev = d

        tau = self.tau_s
        x_pred = x + vx_img * tau
        y_pred = y + vy_img * tau
        d_pred = d + vd * tau
        return x_pred, y_pred, d_pred

    def center(self, measurement: VisionMeasurement) -> ControlCommand:
        """Yaw-only Smith-predicted control: keep the object centered in the frame."""
        x_pred, _, _ = self._smith_predict(measurement)
        yaw = _clamp(self.yaw_gain * x_pred, self.cmd_min, self.cmd_max)
        return ControlCommand(lr=0, fb=0, ud=0, yaw=-yaw)

    def follow(
        self,
        measurement: VisionMeasurement,
        desired_distance_m: float | None = None,
    ) -> ControlCommand:
        """
        Smith predictor visual servo: yaw from x_pred, vertical from y_pred, forward/back from d_pred.
        Args:
            measurement: Vision measurement (x/y errors, distance).
            desired_distance_m: Distance in meters to maintain from the target. If None, uses config default.
        """
        if self._abort:
            return self.hover()

        x_pred, y_pred, d_pred = self._smith_predict(measurement)
        d_ref = desired_distance_m if desired_distance_m is not None else self.desired_distance_m

        yaw = _clamp(self.yaw_gain * x_pred, self.cmd_min, self.cmd_max)
        ud = _clamp(-self.vertical_gain * y_pred, self.cmd_min, self.cmd_max)
        fb = _clamp(self.forward_gain * (d_pred - d_ref), self.cmd_min, self.cmd_max)

        return ControlCommand(lr=0, fb=fb, ud=ud, yaw=yaw)

    def hover(self) -> ControlCommand:
        """Zero velocities: hold position."""
        return ControlCommand(lr=0, fb=0, ud=0, yaw=0)

    def search(self) -> ControlCommand:
        """Slow yaw scan to reacquire target; no forward/up/down."""
        return ControlCommand(lr=0, fb=0, ud=0, yaw=self.search_yaw_speed)

    def step(
        self,
        mode: MissionState,
        measurement: VisionMeasurement | None = None,
        desired_distance_m: float | None = None,
    ) -> ControlCommand:
        """
        Single control tick. Call at your loop rate (e.g. 5–20 Hz).

        Args:
            mode: Current mission state (TAKEOFF, FOLLOW, SEARCH, HOVER, LAND).
            measurement: Required for FOLLOW; ignored for other modes.
            desired_distance_m: For FOLLOW, distance in meters to maintain from target. If None, uses config default.
        """
        if mode == MissionState.FOLLOW and measurement is not None:
            return self.follow(measurement, desired_distance_m=desired_distance_m)
        return self.hover()


# Backward-compatible module-level functions (use default instance)
_default = TelloController()


def set_abort(value: bool) -> None:
    """Set abort flag on the default controller. When True, follow_control returns hover."""
    _default.set_abort(value)


def follow_control(
    measurement: VisionMeasurement,
    desired_distance_m: float | None = None,
) -> ControlCommand:
    return _default.follow(measurement, desired_distance_m=desired_distance_m)


def hover_command() -> ControlCommand:
    return _default.hover()


def search_command() -> ControlCommand:
    return _default.search()


def center_command(measurement: VisionMeasurement) -> ControlCommand:
    return _default.center(measurement)
