"""
MDP-inspired policy layer: maps (DiscreteState, current MissionState) -> next MissionState.

This is a rule-based scaffold that emulates MDP decision logic. It can later be
replaced with value iteration / policy iteration over the discrete state space.
TAKEOFF is handled by mission logic; LAND is absorbing and cannot be overridden.
"""

from ..config.types import DiscreteState, MissionState


POLICY_ACTIONS = (MissionState.FOLLOW, MissionState.SEARCH, MissionState.HOVER, MissionState.LAND)


def select_action(discrete_state: DiscreteState, current_state: MissionState) -> MissionState:
    """
    Select next mission state from current state and discrete observation.

    Rules (priority order):
    - If already in LAND, always return LAND (absorbing).
    - If latency or battery critical -> LAND.
    - If altitude high -> HOVER or LAND.
    - If target visible, confidence medium/high, latency nominal, battery normal, altitude safe -> FOLLOW.
    - If target not visible but safety okay -> SEARCH or HOVER.
    """
    if current_state == MissionState.LAND:
        return MissionState.LAND

    ds = discrete_state

    if ds.latency_bucket == "critical" or ds.battery_bucket == "critical":
        return MissionState.LAND

    if ds.altitude_bucket == "high":
        if ds.battery_bucket == "low":
            return MissionState.LAND
        return MissionState.HOVER

    if ds.latency_bucket == "degraded":
        return MissionState.HOVER
    if ds.battery_bucket == "low":
        return MissionState.HOVER

    if (
        ds.target_visible
        and ds.confidence_bucket in ("medium", "high")
        and ds.latency_bucket == "nominal"
        and ds.battery_bucket == "normal"
        and ds.altitude_bucket == "safe"
    ):
        return MissionState.FOLLOW

    if not ds.target_visible:
        if ds.confidence_bucket == "low" and ds.latency_bucket == "nominal":
            return MissionState.SEARCH
        return MissionState.HOVER

    return MissionState.HOVER
