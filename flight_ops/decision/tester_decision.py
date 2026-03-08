"""
Tester: takeoff → hover → search → land.
"""

import time

import cv2

from ..control import (
    takeoff,
    land,
    move_up,
    apply_command,
    hover_command,
    search_command,
    FlightDataCollector,
)
from ..perception import read_measurement_from_tracker


HOVER_ALTITUDE_M = 1.5
CONFIDENCE_GOOD = 0.9


def _wrap_delta(delta: float) -> float:
    while delta > 180:
        delta -= 360
    while delta <= -180:
        delta += 360
    return delta


def run_tester(tello, tracker, frame_read) -> None:
    """Takeoff, hover, search (until hand found or full 360°), hover, land."""
    takeoff(tello)
    time.sleep(1)  # Wait for IMU to stabilize
    climb_cm = max(0, int((HOVER_ALTITUDE_M - 0.3) * 100))
    if climb_cm >= 20:
        move_up(tello, climb_cm)

    sensor = FlightDataCollector(tello)
    phase = "hover"
    hover_start = time.monotonic()
    search_yaw_prev: float | None = None
    search_yaw_total = 0.0
    hover_after_start: float | None = None

    while True:
        sensor.collect()
        measurement = read_measurement_from_tracker(tracker)
        confidence = measurement.confidence

        if phase == "hover":
            apply_command(tello, hover_command())
            if (time.monotonic() - hover_start) >= 10: # 60 s
                phase = "search"
                search_yaw_prev = sensor.yaw
                search_yaw_total = 0.0
                print("search")

        elif phase == "search":
            apply_command(tello, search_command())
            if search_yaw_prev is not None:
                delta = _wrap_delta(sensor.yaw - search_yaw_prev)
                search_yaw_total += delta
            search_yaw_prev = sensor.yaw

            if confidence >= CONFIDENCE_GOOD:
                print("hand found")
                phase = "hover_after"
                hover_after_start = time.monotonic()
            elif abs(search_yaw_total) >= 360:
                print("full sweep")
                phase = "hover_after"
                hover_after_start = time.monotonic()

        elif phase == "hover_after":
            apply_command(tello, hover_command())
            if hover_after_start and (time.monotonic() - hover_after_start) >= 10: # 60 s
                land(tello)
                print("landed")
                break

        if confidence > 0:
            print(f"  bat={sensor.bat:.0f}% conf={confidence:.2f}  {phase}", end="\r")
        tello_frame = frame_read.frame
        if tello_frame is not None:
            cv2.imshow("Tester", tello_frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            land(tello)
            break
        time.sleep(0.05)
