"""
Entry point: run with real Tello (connect → takeoff → verify CV → land)
or run mock-only demo. No code removed; real flow is the default.
"""

import os
import sys
import time

# Ensure repo root on path so we can import cv (depth_perception)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import cv2
from djitellopy import Tello

from flight_ops.config.types import VisionMeasurement, TelemetrySnapshot
from flight_ops.core.mission_manager import MissionManager
from flight_ops.config import config_module
from flight_ops.perception.extractor_interface import get_vision_measurement

# CV from project cv/depth_perception (uses its default webcam via .read())
from cv.depth_perception import DepthHandTracker, ThreeDHandData


# -----------------------------------------------------------------------------
# Telemetry from real Tello (for integration)
# -----------------------------------------------------------------------------


def telemetry_from_tello(tello: Tello, latency_ms: float = 80.0) -> TelemetrySnapshot:
    """Build TelemetrySnapshot from current Tello state. latency_ms is default or from metrics."""
    state = tello.get_current_state() or {}
    battery = float(state.get("bat", tello.get_battery()))
    height_cm = state.get("h", 0)
    try:
        height_cm = int(height_cm)
    except (TypeError, ValueError):
        height_cm = 0
    altitude_m = height_cm / 100.0
    mission_time_s = float(state.get("time", 0))
    link_ok = bool(state)
    return TelemetrySnapshot(
        battery=battery,
        latency_ms=latency_ms,
        altitude_m=altitude_m,
        mission_time_s=mission_time_s,
        link_ok=link_ok,
    )


# -----------------------------------------------------------------------------
# Real system: connect → takeoff → verify CV pipeline → land
# -----------------------------------------------------------------------------


def _hand_data_to_measurement(data: ThreeDHandData) -> VisionMeasurement:
    """Convert cv/depth_perception ThreeDHandData to flight_ops VisionMeasurement."""
    return VisionMeasurement(
        x_error=data.x_error,
        y_error=data.y_error,
        distance=data.distance,
        confidence=data.confidence,
    )


# Flight duration before auto-land (seconds)
FLIGHT_DURATION_S = 200.0


def run_with_tello() -> None:
    """
    Connect to Tello, start video stream, takeoff. Run hand-tracking CV in the
    main thread (no separate CV window). Main loop: read webcam for hand data,
    show Tello stream only. Auto-land after FLIGHT_DURATION_S or press 'q'.
    """
    t = Tello()
    tracker = None

    try:
        time.sleep(1)
        t.connect(wait_for_state=True)
        print("Tello connected. Battery:", t.get_battery(), "%")

        t.streamon()
        frame_read = t.get_frame_read()
        time.sleep(0.5)

        # Hand tracking from webcam, non-blocking: background thread runs OpenCV/MediaPipe,
        # .read() returns latest cached (hand_data, frame) so the Tello loop is not blocked
        tracker = DepthHandTracker(non_blocking=True)

        print("Takeoff...")
        t.takeoff()
        # time.sleep(2)
        state = t.get_current_state()
        if state:
            print("  height (cm):", state.get("h", "N/A"), "  battery:", state.get("bat", "N/A"))
        print("Takeoff complete. Tello stream only. Auto-land in {:.0f}s or press 'q'.\n".format(FLIGHT_DURATION_S))

        manager = MissionManager()
        start_time = time.monotonic()
        while (time.monotonic() - start_time) < FLIGHT_DURATION_S:
            # Run CV and MDP every iteration regardless of Tello frame. frame_read.frame
            # can be None during flight (stream delay), which was causing the loop to
            # spin in continue and never run CV/MDP until after land.
            hand_data, _ = tracker.read()
            measurement = (
                _hand_data_to_measurement(hand_data)
                if hand_data is not None
                else VisionMeasurement(x_error=0.0, y_error=0.0, distance=0.0, confidence=0.0)
            )
            telemetry = telemetry_from_tello(t)
            mission_state, cmd, _ = manager.step(measurement, telemetry)

            if hand_data is not None:
                print(
                    "  CV  x_pix={} y_pix={}  x_err={:+.2f} y_err={:+.2f}  dist={:.1f} z_norm={:.3f}  conf={:.2f}".format(
                        hand_data.x_pix, hand_data.y_pix,
                        hand_data.x_error, hand_data.y_error,
                        hand_data.distance, hand_data.z_norm,
                        hand_data.confidence,
                    ),
                    end="\r",
                )

            tello_frame = frame_read.frame
            if tello_frame is not None:
                cv2.putText(
                    tello_frame,
                    f"state={mission_state.value} lr={cmd.lr} fb={cmd.fb} ud={cmd.ud} yaw={cmd.yaw}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1,
                )
                cv2.putText(
                    tello_frame,
                    "CV: hand" if hand_data else "CV: no hand",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if hand_data else (0, 0, 255), 2,
                )
                cv2.imshow("Tello stream (q to land)", tello_frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        print("\nLanding...")
        t.land()
        print("Landed.")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        cv2.destroyAllWindows()
        if tracker is not None:
            tracker.release()
        try:
            t.end()
        except Exception as e:
            print("Cleanup:", repr(e))


# -----------------------------------------------------------------------------
# Mock-only demo (no Tello): full loop with mock telemetry and safety-induced LAND
# -----------------------------------------------------------------------------


def _mock_telemetry(
    battery: float = 80.0,
    latency_ms: float = 50.0,
    altitude_m: float = 1.0,
    mission_time_s: float = 0.0,
    link_ok: bool = True,
) -> TelemetrySnapshot:
    return TelemetrySnapshot(
        battery=battery,
        latency_ms=latency_ms,
        altitude_m=altitude_m,
        mission_time_s=mission_time_s,
        link_ok=link_ok,
    )


def run_demo_mock() -> None:
    """
    Runs several iterations with mock vision and mock telemetry; demonstrates
    transition to LAND when a mock safety threshold is exceeded (e.g. critical battery).
    No Tello connection.
    """
    manager = MissionManager()
    mission_time = 0.0
    dt = 0.5

    for i in range(16):
        if i < 8:
            telemetry = _mock_telemetry(
                battery=80.0 - i * 2,
                latency_ms=60.0,
                altitude_m=1.0,
                mission_time_s=mission_time,
            )
        else:
            telemetry = _mock_telemetry(
                battery=config_module.BATTERY_CRITICAL_PCT - 2,
                latency_ms=60.0,
                altitude_m=1.0,
                mission_time_s=mission_time,
            )

        measurement = VisionMeasurement(
            x_error=0.05, y_error=-0.02, distance=1.5, confidence=0.85
        )

        state, cmd, debug = manager.step(measurement, telemetry)

        print(f"--- tick {i} ---")
        print(f"  mission_state = {state.value}")
        print(f"  measurement   = x_err={measurement.x_error:.2f} y_err={measurement.y_error:.2f} dist={measurement.distance:.2f} conf={measurement.confidence:.2f}")
        if debug.get("discrete_state"):
            ds = debug["discrete_state"]
            print(f"  discrete_state = visible={ds.target_visible} x={ds.x_bucket} y={ds.y_bucket} dist={ds.distance_bucket} conf={ds.confidence_bucket} alt={ds.altitude_bucket} lat={ds.latency_bucket} bat={ds.battery_bucket}")
        print(f"  command       = lr={cmd.lr} fb={cmd.fb} ud={cmd.ud} yaw={cmd.yaw}")
        if debug.get("safety_reason"):
            print(f"  safety        = FORCED LAND: {debug['safety_reason']}")
        else:
            print(f"  safety        = ok")
        print()

        mission_time += dt

        if state.value == "land":
            print("(LAND reached; absorbing. Exiting demo.)")
            break


def main() -> None:
    """Default: run with real Tello (connect, takeoff, verify CV, land)."""
    run_with_tello()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--mock":
        run_demo_mock()
    else:
        main()
