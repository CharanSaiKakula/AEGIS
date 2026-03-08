"""
Integration point for the upstream computer vision (CV) extractor.

The real extractor runs on the ground station and provides filtered measurements.
This module exposes the interface and a mock provider for development and testing.
"""

import numpy as np

from ..config.types import VisionMeasurement
from ..config import config_module as config


def _depth_to_distance_m(depth: float) -> float:
    """
    Convert raw depth (CV output) to meters.

    For SinglePersonTracker with auto_calibrate=False: depth = 1000/body_scale_px.
    Perspective: apparent size ∝ 1/distance, so distance ∝ depth. Thus distance_m = K * depth.
    Tune config.DEPTH_TO_METERS_K via calibration (e.g. at 1m if depth≈10 then K≈0.1).
    """
    if not depth or depth <= 0:
        return 0.0
    return float(config.DEPTH_TO_METERS_K * depth)


def read_measurement_from_tracker(tracker) -> VisionMeasurement:
    """
    Read from DepthHandTracker, convert to VisionMeasurement.
    Tracker must have .read() -> (hand_data, frame) where hand_data has
    x_error, y_error, distance, confidence; or None.
    """
    hand_data, _ = tracker.read()
    if hand_data is None:
        return VisionMeasurement(x_error=0.0, y_error=0.0, distance=0.0, confidence=0.0)
    return VisionMeasurement(
        x_error=hand_data.x_error,
        y_error=hand_data.y_error,
        distance=hand_data.distance,
        confidence=hand_data.confidence,
    )


def read_measurement_from_pose(pose_data) -> VisionMeasurement:
    """
    Convert PoseData or TrackData (from cv.human_pose_tracker_3d) into a VisionMeasurement.
    Uses pose_data.depth (raw CV output) for distance; converts via _depth_to_distance_m.
    Supports both normalized_x/normalized_y (PoseData) and norm_x/norm_y (TrackData).
    """
    if not getattr(pose_data, "detected", False):
        return VisionMeasurement(x_error=0.0, y_error=0.0, distance=0.0, confidence=0.0)
    depth = getattr(pose_data, "depth", 0.0) or 0.0
    distance_m = _depth_to_distance_m(depth)
    conf = getattr(pose_data, "confidence", 1.0)
    if isinstance(conf, bool):
        conf = 1.0 if conf else 0.0
    x_err = getattr(pose_data, "normalized_x", None)
    if x_err is None:
        x_err = getattr(pose_data, "norm_x", 0.0)
    y_err = getattr(pose_data, "normalized_y", None)
    if y_err is None:
        y_err = getattr(pose_data, "norm_y", 0.0)
    return VisionMeasurement(
        x_error=float(x_err),
        y_error=float(y_err),
        distance=distance_m,
        confidence=float(conf),
    )


def get_vision_measurement() -> VisionMeasurement:
    """
    Return the current vision measurement from the CV pipeline.

    This is the integration point: replace the body with a call to your real
    extractor (e.g. a ROS topic, shared memory, or callback from the CV process).
    """
    return _mock_vision_provider()


# -----------------------------------------------------------------------------
# Mock / example provider (for testing and demos)
# -----------------------------------------------------------------------------


def _mock_vision_provider() -> VisionMeasurement:
    """
    Mock provider returning fake data. Use only for development.
    Replace calls to this with your real CV extractor output.
    """
    return VisionMeasurement(
        x_error=0.05,
        y_error=-0.08,
        distance=1.5,
        confidence=0.85,
    )


class MockExtractor:
    """
    Stateful mock extractor for demos. Can be configured to return different
    values or simulate target loss / low confidence over time.
    """

    def __init__(self, default: VisionMeasurement | None = None):
        self._default = default or VisionMeasurement(
            x_error=0.0, y_error=0.0, distance=1.5, confidence=0.9
        )
        self._tick = 0

    def get_measurement(self) -> VisionMeasurement:
        """Return a measurement (mock: can vary by tick for demos)."""
        self._tick += 1
        if self._tick > 10:
            return VisionMeasurement(
                x_error=0.0, y_error=0.0, distance=1.5, confidence=0.2
            )
        return self._default
