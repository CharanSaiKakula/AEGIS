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
from ..perception.state_extractor import extract_discrete_state
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

        if not safety_ok and safety_reason:
            self._state = MissionState.LAND
            discrete_state = extract_discrete_state(measurement, telemetry)
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
            discrete_state = extract_discrete_state(measurement, telemetry)
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
            discrete_state = extract_discrete_state(measurement, telemetry)
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
            discrete_state = extract_discrete_state(measurement, telemetry)
            self._state = select_action(discrete_state, MissionState.FOLLOW)
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

        discrete_state = extract_discrete_state(measurement, telemetry)
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
