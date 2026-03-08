"""
Entry point: run with real Tello (connect → takeoff → verify CV → land)
or run mock-only demo. No code removed; real flow is the default.
"""

import time
from djitellopy import Tello

from .config.types import VisionMeasurement, TelemetrySnapshot
from .core.mission_manager import MissionManager
from .config import config_module
from .perception.extractor_interface import get_vision_measurement


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


def run_with_tello() -> None:
    """
    Connect to Tello, takeoff, verify CV pipeline (one measurement), then land.
    Uses the autonomy stack with real telemetry; vision is still mock until you
    plug in the real extractor.
    """
    t = Tello()
    try:
        time.sleep(1)
        t.connect()
        print("Tello connected. Battery:", t.get_battery(), "%")

        # --- Takeoff ---
        print("Takeoff...")
        t.takeoff()
        time.sleep(2)
        state = t.get_current_state()
        if state:
            print("  height (cm):", state.get("h", "N/A"), "  battery:", state.get("bat", "N/A"))
        print("Takeoff complete.")

        # --- Verify CV pipeline (get measurement; stack runs one step) ---
        measurement = get_vision_measurement()
        print("CV pipeline OK. Measurement: x_err={:.2f} y_err={:.2f} dist={:.2f} conf={:.2f}".format(
            measurement.x_error, measurement.y_error, measurement.distance, measurement.confidence
        ))
        telemetry = telemetry_from_tello(t)
        manager = MissionManager()
        mission_state, cmd, debug = manager.step(measurement, telemetry)
        print("Stack step: state={}  cmd lr={} fb={} ud={} yaw={}".format(
            mission_state.value, cmd.lr, cmd.fb, cmd.ud, cmd.yaw
        ))

        # --- Land ---
        print("Landing...")
        t.land()
        print("Landed.")
    except KeyboardInterrupt:
        print("Interrupted.")
    finally:
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
