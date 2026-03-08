"""
Integration point for the upstream computer vision (CV) extractor.

The real extractor runs on the ground station and provides filtered measurements.
This module exposes the interface and a mock provider for development and testing.
"""

from ..config.types import VisionMeasurement


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


def read_measurement_from_pose(pose_data, distance_estimator) -> VisionMeasurement:
    """
    Convert PoseData (from cv.human_pose_tracker_3d) and distance_estimator
    into a VisionMeasurement for the follow/find_object pipeline.
    """
    if not getattr(pose_data, "detected", False):
        return VisionMeasurement(x_error=0.0, y_error=0.0, distance=0.0, confidence=0.0)
    distance_m = distance_estimator.estimate(pose_data)
    conf = getattr(pose_data, "confidence", 1.0)
    if isinstance(conf, bool):
        conf = 1.0 if conf else 0.0
    return VisionMeasurement(
        x_error=getattr(pose_data, "normalized_x", 0.0),
        y_error=getattr(pose_data, "normalized_y", 0.0),
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
