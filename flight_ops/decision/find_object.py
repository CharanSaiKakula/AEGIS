"""
Find object: takeoff → hover → search (human) → center → follow → land.
Uses human pose tracker and perception read_measurement_from_pose.
Center: yaw-only to center the object. Follow: center + maintain commanded distance.
If no person found after full 360° sweep, land immediately.
"""

import time
from enum import Enum

import cv2

from ..config import config_module as config
from ..control import (
    takeoff,
    land,
    move_up,
    apply_command,
    hover_command,
    search_command,
    center_command,
    follow_control,
    set_abort,
    FlightDataCollector,
    DistanceEstimator,
)
from ..perception import read_measurement_from_pose


class State(Enum):
    HOVER = 0
    SEARCH = 1
    CENTER = 2
    FOLLOW = 3


HOVER_ALTITUDE_M = 2
CONFIDENCE_GOOD = 0.9
HOVER_BUFFER_S = 10.0
CENTER_DURATION_S = 10.0
FOLLOW_DURATION_S = 30.0


def _wrap_delta(delta: float) -> float:
    while delta > 180:
        delta -= 360
    while delta <= -180:
        delta += 360
    return delta


def find_object(tello, pose_tracker, frame_read=None, distance_estimator=None) -> None:
    """
    Takeoff, hover, search until person found or full 360°. If found: center (yaw-only),
    then follow (center + maintain distance), then land. If not found: land immediately.
    Uses DistanceEstimator for metric distance when provided.
    """
    takeoff(tello)
    time.sleep(1)  # Wait for IMU to stabilize
    climb_cm = max(0, int((HOVER_ALTITUDE_M - 0.3) * 100))
    if climb_cm >= 20:
        move_up(tello, climb_cm)

    sensor = FlightDataCollector(tello)
    if distance_estimator is None:
        distance_estimator = DistanceEstimator()
    state = State.HOVER
    hover_start = time.monotonic()
    search_yaw_prev: float | None = None
    search_yaw_total = 0.0
    center_start: float | None = None
    follow_start: float | None = None

    while True:
        sensor.collect()
        frame, pose_data = pose_tracker.get_pose_data()
        measurement = read_measurement_from_pose(pose_data, distance_estimator)
        confidence = measurement.confidence

        match state:
            case State.HOVER:
                apply_command(tello, hover_command())
                if (time.monotonic() - hover_start) >= HOVER_BUFFER_S:
                    state = State.SEARCH
                    search_yaw_prev = sensor.yaw
                    search_yaw_total = 0.0
                    print("search")

            case State.SEARCH:
                apply_command(tello, search_command())
                if search_yaw_prev is not None:
                    delta = _wrap_delta(sensor.yaw - search_yaw_prev)
                    search_yaw_total += delta
                search_yaw_prev = sensor.yaw

                if confidence >= CONFIDENCE_GOOD:
                    print("person found")
                    state = State.CENTER
                    center_start = time.monotonic()
                elif abs(search_yaw_total) >= 360:
                    print("full sweep, no person")
                    land(tello)
                    print("landed")
                    break

            case State.CENTER:
                apply_command(tello, center_command(measurement))
                if center_start and (time.monotonic() - center_start) >= CENTER_DURATION_S:
                    set_abort(False)
                    # set_abort(True)
                    # time.sleep(2)
                    # land(tello)
                    # print("landed")
                    # break
                    state = State.FOLLOW
                    follow_start = time.monotonic()
                    print("follow")

            case State.FOLLOW:
                if confidence < 0.10:
                    print("confidence lost in follow")
                    set_abort(True)
                    time.sleep(2)
                    land(tello)
                    print("landed")
                    break
                apply_command(
                    tello,
                    follow_control(
                        measurement,
                        desired_distance_m=config.OPT_DIST_FROM_TARGET,
                    ),
                )
                if follow_start and (time.monotonic() - follow_start) >= FOLLOW_DURATION_S:
                    set_abort(True)
                    time.sleep(2)
                    land(tello)
                    print("landed")
                    break

        print(f"  bat={sensor.bat:.0f}% conf={confidence:.2f} dist={measurement.distance:.2f}m  {state.name}", end="\r")
        if frame is not None:
            cv2.imshow("Find Object", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            land(tello)
            break
        time.sleep(0.05)
