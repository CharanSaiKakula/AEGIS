"""
Entry point: aegis fly runs autonomy via find_object (time-based + DistanceEstimator) or ruleset (MDP policy).
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
from flight_ops.control import DistanceEstimator
from flight_ops.decision.find_object import find_object

from cv.human_pose_tracker_3d import PoseTracker3D


# Same init as find_object
HOVER_ALTITUDE_M = 2


def run_with_tello_ruleset(t: Tello, tracker: PoseTracker3D) -> None:
    """Ruleset controller: MissionManager + MDP policy pipeline.
    Init matches find_object. Flow: search → center → follow (ruleset)."""
    from flight_ops.core.mission_manager import MissionManager
    from flight_ops.control import (
        land,
        apply_command,
        FlightDataCollector,
        DistanceEstimator,
    )
    from flight_ops.perception import read_measurement_from_pose

    # Takeoff is done in run_with_tello() before tracker creation (see comment there).
    sensor = FlightDataCollector(t)
    distance_estimator = DistanceEstimator()
    manager = MissionManager()

    while True:
        sensor.collect()
        frame, pose_data = tracker.get_pose_data()
        measurement = read_measurement_from_pose(pose_data, distance_estimator)
        telemetry = sensor.to_telemetry_snapshot()

        state, cmd, debug = manager.step(measurement, telemetry)

        if manager.request_land():
            land(t)
            print("landed")
            break

        apply_command(t, cmd)

        conf = measurement.confidence
        if conf > 0:
            print(
                f"  bat={sensor.bat:.0f}% conf={conf:.2f} dist={measurement.distance:.2f}m "
                f"{state.value}",
                end="\r",
            )
        if frame is not None:
            cv2.imshow("Ruleset", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            land(t)
            break
        time.sleep(0.05)


def run_with_tello() -> None:
    t = None
    tracker = None
    try:
        t = Tello()
        time.sleep(1)
        t.connect(wait_for_state=True)
        print("Tello connected. Battery:", t.get_battery(), "%")
        t.streamon()
        time.sleep(0.5)

        use_ruleset = True  # False → find_object (does its own takeoff)
        if use_ruleset:
            # Takeoff before PoseTracker3D: MediaPipe/TensorFlow init in tracker
            # __init__ can block the Tello command channel and cause takeoff timeout.
            from flight_ops.control import takeoff, move_up
            takeoff(t)
            time.sleep(1)
            climb_cm = max(0, int((HOVER_ALTITUDE_M - 0.3) * 100))
            if climb_cm >= 20:
                move_up(t, climb_cm)

        tracker = PoseTracker3D(camera_source=t)
        distance_estimator = DistanceEstimator()
        if use_ruleset:
            run_with_tello_ruleset(t, tracker)
        else:
            find_object(t, tracker, distance_estimator=distance_estimator)

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
    
    run_with_tello()
