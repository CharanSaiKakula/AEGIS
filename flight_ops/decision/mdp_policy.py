"""
MDP-inspired policy layer: maps (DiscreteState, MissionState) -> MissionState.

Rule-based scaffold with temporal filtering and hysteresis to prevent oscillation
from single-frame vision failures. Uses lost_duration_s from state for
deterministic, threshold-based decisions. Designed for easy replacement with
SARSA/Q-learning.
"""

from ..config.types import DiscreteState, MissionState


# --- Stabilization thresholds (temporal filtering and hysteresis) ---
LOSS_TIMEOUT_S = 0.8   # Seconds of loss before SEARCH (ignore single-frame drops)
SHORT_DROP_S = 0.3     # Ignore vision drops shorter than this; hold current state

POLICY_ACTIONS = (MissionState.FOLLOW, MissionState.SEARCH, MissionState.HOVER, MissionState.CENTER)


def _visible(state: DiscreteState) -> bool:
    """Target is visible: confidence good or medium (not lost)."""
    return state.confidence_bucket in ("good", "medium")


def select_action(state: DiscreteState, current_state: MissionState) -> MissionState:
    """
    Select next mission state with temporal filtering and hysteresis.

    Reacquisition path: SEARCH -> CENTER -> FOLLOW. CENTER actively yaws to
    center the target (center_command); REACQUIRE used hover and got stuck.

    Priority order:
    1. Long loss -> SEARCH
    2. SEARCH + target (good conf) -> CENTER (active centering, not hover)
    3. CENTER + centered -> FOLLOW
    4. Short vision drop -> hold
    5. Visible + good geometry -> FOLLOW
    6. Default -> hold
    """
    if current_state == MissionState.LAND:
        return MissionState.LAND

    if current_state == MissionState.TAKEOFF:
        return current_state

    visible = _visible(state)

    # RULE 1: Long loss -> SEARCH (never react to single-frame loss)
    if state.lost_duration_s > LOSS_TIMEOUT_S:
        return MissionState.SEARCH

    # RULE 2: Search found target -> CENTER (actively yaw to center; requires "good"
    # to avoid flapping on medium-confidence flickers)
    if current_state == MissionState.SEARCH and state.confidence_bucket == "good":
        return MissionState.CENTER

    # RULE 3: CENTER -> FOLLOW when centered (CENTER uses center_command so we
    # make progress; REACQUIRE used hover and could never get centered)
    if current_state == MissionState.CENTER:
        if state.confidence_bucket == "good" and state.aoo_bucket in ("centered", "moderate"):
            return MissionState.FOLLOW
        return current_state

    # RULE 4: Ignore short vision drops
    if 0 < state.lost_duration_s < SHORT_DROP_S:
        return current_state

    # RULE 5: FOLLOW when target visible with reasonable geometry
    if (
        visible
        and state.confidence_bucket == "good"
        and state.aoo_bucket in ("centered", "moderate")
    ):
        return MissionState.FOLLOW

    # RULE 6: HOVER when target still and at distance
    if (
        current_state in (MissionState.FOLLOW, MissionState.HOVER)
        and state.motion_bucket == "still"
        and state.at_reasonable_distance
    ):
        return MissionState.HOVER

    # RULE 7: Medium confidence -> HOVER (stabilize before aggressive moves)
    if state.confidence_bucket == "medium":
        return MissionState.HOVER

    # REACQUIRE fallback: if we end up here, go to SEARCH to re-center
    if current_state == MissionState.REACQUIRE:
        return MissionState.SEARCH if not visible else MissionState.CENTER

    return current_state
