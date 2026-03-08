"""
Mission orchestrator: owns mission state, runs safety → extract → policy → behavior.

Initial state is TAKEOFF. Final state is LAND (absorbing). Safety can force LAND
from any state; once in LAND, the system never leaves.
"""

from ..config.types import (
    MissionState,
    ControlCommand,
    VisionMeasurement,
    TelemetrySnapshot,
    DiscreteState,
)
from ..perception.state_extractor import extract_discrete_state, target_visible
from ..decision.mdp_policy import select_action
from .behavior_manager import get_behavior_command, request_takeoff, request_land
from ..safety.safety_guard import check_safety


class MissionManager:
    """
    One place that owns current mission state and runs the autonomy pipeline
    each tick: safety → state extraction → policy → behavior command.
    """

    def __init__(self) -> None:
        self._state = MissionState.TAKEOFF
        self._takeoff_done = False
        self._lost_duration_s: float = 0.0
        self._last_mission_time_s: float = 0.0
        self._prev_measurement: VisionMeasurement | None = None

    @property
    def state(self) -> MissionState:
        return self._state

    def step(
        self,
        measurement: VisionMeasurement,
        telemetry: TelemetrySnapshot,
    ) -> tuple[MissionState, ControlCommand, dict]:
        """
        Run one autonomy tick. Safety is checked first; if it fails we force LAND
        and never leave. Otherwise we extract state, run policy, and get command.

        Returns:
            (current_mission_state, control_command, debug_info)
        """
        prev = self._state
        safety_ok, safety_reason = check_safety(telemetry)
        discrete_state: DiscreteState | None = None

        # Update lost_duration: 0 when target visible, else accumulate time since last visible
        vis = target_visible(measurement.confidence)
        if vis:
            self._lost_duration_s = 0.0
        else:
            dt = max(0.0, telemetry.mission_time_s - self._last_mission_time_s)
            self._lost_duration_s += dt
        self._last_mission_time_s = telemetry.mission_time_s

        # Motion magnitude for "target still" check (|dx| + |dy|)
        motion_mag = 0.0
        if self._prev_measurement is not None and vis:
            motion_mag = abs(measurement.x_error - self._prev_measurement.x_error) + abs(
                measurement.y_error - self._prev_measurement.y_error
            )
        self._prev_measurement = measurement

        if not safety_ok and safety_reason:
            self._state = MissionState.LAND
            discrete_state = extract_discrete_state(
                measurement, telemetry, self._lost_duration_s, motion_mag
            )
            cmd = get_behavior_command(self._state, measurement, telemetry)
            return (
                self._state,
                cmd,
                {
                    "previous_state": prev,
                    "new_state": self._state,
                    "safety_reason": safety_reason,
                    "discrete_state": discrete_state,
                },
            )

        if self._state == MissionState.LAND:
            discrete_state = extract_discrete_state(
                measurement, telemetry, self._lost_duration_s, motion_mag
            )
            cmd = get_behavior_command(self._state, measurement, telemetry)
            return (
                self._state,
                cmd,
                {
                    "previous_state": prev,
                    "new_state": self._state,
                    "safety_reason": None,
                    "discrete_state": discrete_state,
                },
            )

        if self._state == MissionState.TAKEOFF and not self._takeoff_done:
            self._takeoff_done = True
            discrete_state = extract_discrete_state(
                measurement, telemetry, self._lost_duration_s, motion_mag
            )
            cmd = get_behavior_command(MissionState.TAKEOFF, measurement, telemetry)
            return (
                MissionState.TAKEOFF,
                cmd,
                {
                    "previous_state": prev,
                    "new_state": MissionState.TAKEOFF,
                    "safety_reason": None,
                    "discrete_state": discrete_state,
                },
            )

        if self._state == MissionState.TAKEOFF and self._takeoff_done:
            discrete_state = extract_discrete_state(
                measurement, telemetry, self._lost_duration_s, motion_mag
            )
            self._state = select_action(discrete_state, MissionState.SEARCH)
            cmd = get_behavior_command(self._state, measurement, telemetry)
            return (
                self._state,
                cmd,
                {
                    "previous_state": MissionState.TAKEOFF,
                    "new_state": self._state,
                    "safety_reason": None,
                    "discrete_state": discrete_state,
                },
            )

        discrete_state = extract_discrete_state(
            measurement, telemetry, self._lost_duration_s, motion_mag
        )
        self._state = select_action(discrete_state, self._state)
        cmd = get_behavior_command(self._state, measurement, telemetry)

        return (
            self._state,
            cmd,
            {
                "previous_state": prev,
                "new_state": self._state,
                "safety_reason": None,
                "discrete_state": discrete_state,
            },
        )

    def request_takeoff(self) -> bool:
        return request_takeoff(self._state)

    def request_land(self) -> bool:
        return request_land(self._state)
