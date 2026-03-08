"""
Metric distance estimator for human pose from cv/human_pose_tracker_3d.

Fuses shoulder-width pinhole model (metric) with pose-area depth proxy (stable).
Output is smoothed and in meters for use by the follow controller.
"""

from __future__ import annotations

import numpy as np


# Tello camera: horizontal FOV ≈ 82.6°, width ≈ 960 px -> f ≈ 550 px
FOCAL_LENGTH_PX = 550.0
# Average human shoulder width (m)
SHOULDER_WIDTH_M = 0.42
# Fusion: d = ALPHA_SHOULDER * d_shoulder + (1 - ALPHA_SHOULDER) * d_area
ALPHA_SHOULDER = 0.7
# Area depth: Z ∝ 1/sqrt(depth) -> d_area = AREA_DEPTH_K * sqrt(1/depth). Tune K by calibration.
AREA_DEPTH_K = 2.0
# Output filter: d_filtered = FILTER_ALPHA * d + (1 - FILTER_ALPHA) * prev_d
FILTER_ALPHA = 0.4
# Min shoulder width in px to trust geometric estimate (avoid div by tiny)
MIN_SHOULDER_PX = 10.0


def _exponential_smooth(value: float, prev: float, alpha: float) -> float:
    return alpha * value + (1.0 - alpha) * prev


def estimate_distance_m(pose_data, prev_d_filtered: float | None = None) -> tuple[float, float]:
    """
    Estimate distance to the detected person in meters.

    Uses shoulder-width model (metric) fused with pose-area depth proxy (stable).
    When pose is not detected, returns (0.0, prev_d_filtered) so caller can hold.

    Args:
        pose_data: PoseData from cv.human_pose_tracker_3d (must have .detected, .depth,
                   .pose_size, .shoulder_width_px).
        prev_d_filtered: Previous filtered distance (m) for smoothing.

    Returns:
        (d_raw, d_filtered): raw fused distance (m) and exponentially smoothed distance (m).
    """
    if not getattr(pose_data, "detected", False):
        prev = prev_d_filtered if prev_d_filtered is not None else 0.0
        return 0.0, prev

    depth = getattr(pose_data, "depth", 0.0) or 0.0
    shoulder_px = getattr(pose_data, "shoulder_width_px", 0.0) or 0.0

    d_shoulder: float | None = None
    if shoulder_px >= MIN_SHOULDER_PX:
        d_shoulder = (FOCAL_LENGTH_PX * SHOULDER_WIDTH_M) / shoulder_px
        d_shoulder = max(0.3, min(10.0, d_shoulder))  # clamp to plausible range (m)

    d_area: float | None = None
    if depth > 0:
        d_area = AREA_DEPTH_K * float(np.sqrt(1.0 / depth))
        d_area = max(0.3, min(10.0, d_area))

    if d_shoulder is not None and d_area is not None:
        d_raw = ALPHA_SHOULDER * d_shoulder + (1.0 - ALPHA_SHOULDER) * d_area
    elif d_shoulder is not None:
        d_raw = d_shoulder
    elif d_area is not None:
        d_raw = d_area
    else:
        prev = prev_d_filtered if prev_d_filtered is not None else 0.0
        return 0.0, prev

    prev = prev_d_filtered if prev_d_filtered is not None else d_raw
    d_filtered = _exponential_smooth(d_raw, prev, FILTER_ALPHA)
    return d_raw, d_filtered


class DistanceEstimator:
    """
    Stateful distance estimator: call .estimate(pose_data) each tick.
    Holds previous filtered distance for smoothing and no-detection hold.
    """

    def __init__(self):
        self._prev_d_filtered: float | None = None

    def estimate(self, pose_data) -> float:
        """
        Return estimated distance to person in meters (filtered).
        When no pose detected, returns last filtered value (hold).
        """
        _, d_filtered = estimate_distance_m(pose_data, self._prev_d_filtered)
        self._prev_d_filtered = d_filtered
        return d_filtered

    def reset(self) -> None:
        """Clear filter state (e.g. after target loss)."""
        self._prev_d_filtered = None
