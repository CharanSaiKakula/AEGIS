"""
Integration point for the upstream computer vision (CV) extractor.

The real extractor runs on the ground station and provides filtered measurements.
This module exposes the interface and a mock provider for development and testing.
"""

from ..config.types import VisionMeasurement


def get_vision_measurement() -> VisionMeasurement:
    """
    Return the current vision measurement from the CV pipeline.

    This is the integration point: replace the body with a call to your real
    extractor (e.g. a ROS topic, shared memory, or callback from your CV process).
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
