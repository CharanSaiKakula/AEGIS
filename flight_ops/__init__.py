"""
flight_ops: autonomy package for DJI Tello person-following.

Pipeline: extractor -> state extraction -> MDP policy -> behavior -> controller
-> safety guardrails. Safety can force LAND; LAND is absorbing.
"""

from .config.types import (
    MissionState,
    ControlCommand,
    VisionMeasurement,
    TelemetrySnapshot,
    DiscreteState,
)
from .core.mission_manager import MissionManager
from .perception.state_extractor import extract_discrete_state
from .decision.mdp_policy import select_action
from .core.behavior_manager import get_behavior_command
from .safety.safety_guard import check_safety, should_force_land
from .control.controller import follow_control, hover_command, search_command

__all__ = [
    "MissionState",
    "ControlCommand",
    "VisionMeasurement",
    "TelemetrySnapshot",
    "DiscreteState",
    "MissionManager",
    "extract_discrete_state",
    "select_action",
    "get_behavior_command",
    "check_safety",
    "should_force_land",
    "follow_control",
    "hover_command",
    "search_command",
]
