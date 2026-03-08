"""
MDP-inspired policy layer: maps (DiscreteState, MissionState) -> MissionState.

Rule-based scaffold designed for easy verification and future replacement with
SARSA/Q-learning. The policy selects high-level behaviors only; low-level
commands are handled by behavior_manager.

Pipeline: VisionMeasurement -> state_extractor -> DiscreteState -> select_action -> MissionState
"""

from ..config.types import DiscreteState, MissionState


POLICY_ACTIONS = (MissionState.FOLLOW, MissionState.SEARCH, MissionState.CENTER, MissionState.HOVER, MissionState.REACQUIRE)


def select_action(state: DiscreteState, current_state: MissionState) -> MissionState:
    """
    Select next mission state from current state and discrete observation.

    Rules are evaluated in priority order. Designed for later replacement with
    Q[state, action] without changing the MissionManager interface.

    Args:
        state: Bucketized perception (aoo_bucket, distance_bucket, confidence_bucket, lost_duration_bucket).
        current_state: Current mission behavior.

    Returns:
        Next MissionState.
    """
    # Absorbing state: never leave LAND
    if current_state == MissionState.LAND:
        return MissionState.LAND

    # -------------------------------------------------------------------------
    # RULE 1: Target lost -> SEARCH
    # Very low confidence or target lost for a long time.
    # -------------------------------------------------------------------------
    if state.confidence_bucket == "lost":
        return MissionState.SEARCH
    if state.lost_duration_bucket == "long":
        return MissionState.SEARCH

    # -------------------------------------------------------------------------
    # RULE 2: Search → Center (center inbuilt into search)
    # When searching and target becomes visible, center (yaw-only) before follow.
    # -------------------------------------------------------------------------
    if current_state == MissionState.SEARCH and state.confidence_bucket == "good":
        return MissionState.CENTER

    # CENTER -> FOLLOW when centered (stabilization complete)
    if (
        current_state == MissionState.CENTER
        and state.confidence_bucket == "good"
        and state.aoo_bucket == "centered"
    ):
        return MissionState.FOLLOW

    # Stay in CENTER until centered (center_command applied by behavior_manager)
    if current_state == MissionState.CENTER:
        return MissionState.CENTER

    # REACQUIRE -> FOLLOW when centered (legacy path; prefer CENTER)
    if (
        current_state == MissionState.REACQUIRE
        and state.confidence_bucket == "good"
        and state.aoo_bucket == "centered"
    ):
        return MissionState.FOLLOW
    if current_state == MissionState.REACQUIRE:
        return MissionState.REACQUIRE

    # -------------------------------------------------------------------------
    # RULE 2b: FOLLOW -> HOVER when target still and at reasonable distance
    # Reduces unnecessary motion when target has stopped and drone is in position.
    # Stay in HOVER while target remains still and at distance.
    # -------------------------------------------------------------------------
    if (
        current_state in (MissionState.FOLLOW, MissionState.HOVER)
        and state.motion_bucket == "still"
        and state.at_reasonable_distance
    ):
        return MissionState.HOVER

    # -------------------------------------------------------------------------
    # RULE 3: Stable target -> FOLLOW
    # Target visible, confidence good, geometry reasonable.
    # -------------------------------------------------------------------------
    if (
        state.target_visible
        and state.confidence_bucket == "good"
        and state.aoo_bucket in ("centered", "moderate")
    ):
        return MissionState.FOLLOW

    # -------------------------------------------------------------------------
    # RULE 4: Uncertain geometry -> HOVER
    # Confidence moderate; allow perception to stabilize without aggressive motion.
    # -------------------------------------------------------------------------
    if state.confidence_bucket == "medium":
        return MissionState.HOVER

    # -------------------------------------------------------------------------
    # RULE 5: Default
    # No rule triggered; maintain current behavior.
    # -------------------------------------------------------------------------
    return current_state
