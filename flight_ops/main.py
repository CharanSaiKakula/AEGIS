"""
Entry point: aegis fly runs takeoff → climb to 1.5m → search → hover when hand found → land.
"""

import os
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import cv2
from djitellopy import Tello

from flight_ops.config.types import VisionMeasurement, TelemetrySnapshot
from flight_ops.config import config_module
from flight_ops.decision.tester_decision import run_tester
from flight_ops.perception import read_measurement_from_tracker

from cv.depth_perception_mac import DepthHandTracker


def run_with_tello() -> None:
    t = None
    tracker = None
    try:
        t = Tello()
        time.sleep(1)
        t.connect(wait_for_state=True)
        print("Tello connected. Battery:", t.get_battery(), "%")
        t.streamon()
        frame_read = t.get_frame_read()
        time.sleep(0.5)
        tracker = DepthHandTracker(non_blocking=True)

        run_tester(t, tracker, frame_read)
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        cv2.destroyAllWindows()
        if tracker is not None:
            tracker.release()
        try:
            if t is not None:
                t.end()
        except Exception as e:
            print("Cleanup:", repr(e))


def run_demo_mock() -> None:
    """Mock-only demo: MDP loop with mock telemetry."""
    from flight_ops.core.mission_manager import MissionManager

    manager = MissionManager()
    mission_time = 0.0
    dt = 0.5

    for i in range(16):
        telemetry = TelemetrySnapshot(
            battery=80.0 - i * 2 if i < 8 else config_module.BATTERY_CRITICAL_PCT - 2,
            latency_ms=60.0,
            altitude_m=1.0,
            mission_time_s=mission_time,
        )
        measurement = VisionMeasurement(x_error=0.05, y_error=-0.02, distance=1.5, confidence=0.85)
        state, cmd, _ = manager.step(measurement, telemetry)
        print(f"tick {i} state={state.value} cmd=lr{cmd.lr} fb{cmd.fb} ud{cmd.ud} yaw{cmd.yaw}")
        mission_time += dt
        if state.value == "land":
            print("LAND reached.")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--mock":
        run_demo_mock()
    else:
        run_with_tello()
