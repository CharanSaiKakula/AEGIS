"""
Collect flight data from the Tello for MDP decision logic and safety.

Provides battery, attitude (yaw/pitch/roll), velocities, altitude, and other
fields needed by TelemetrySnapshot and future MDP state discretization.
"""

import time
from typing import TYPE_CHECKING

from ..config.types import TelemetrySnapshot

if TYPE_CHECKING:
    from djitellopy import Tello


class FlightDataCollector:
    """
    Collects and exposes Tello flight data. Call collect() to refresh, then
    read attributes (yaw, bat, temp, etc.).

    Usage:
        sensor = FlightDataCollector(tello)
        sensor.collect()
        print(sensor.yaw, sensor.bat, sensor.temp)
        telemetry = sensor.to_telemetry_snapshot()
    """

    def __init__(
        self,
        tello: "Tello",
        *,
        mission_start: float | None = None,
        latency_ms: float = 0.0,
    ) -> None:
        self._tello = tello
        self._mission_start = mission_start if mission_start is not None else time.monotonic()
        self._latency_ms = latency_ms

        # Populated by collect(). Access as sensor.yaw, sensor.bat, etc.
        self.battery: float = 0.0
        self.bat: float = 0.0  # alias
        self.latency_ms: float = 0.0
        self.altitude_m: float = 0.0
        self.mission_time_s: float = 0.0
        self.link_ok: bool = False

        self.yaw: float = 0.0
        self.pitch: float = 0.0
        self.roll: float = 0.0

        self.speed_x: float = 0.0
        self.speed_y: float = 0.0
        self.speed_z: float = 0.0

        self.height_cm: float = 0.0
        self.mission_pad_id: int = -1

        self.temp: float = 0.0
        self.templ: float = 0.0
        self.temph: float = 0.0

    def collect(self) -> None:
        """Fetch latest state from Tello and update all attributes."""
        tello = self._tello
        state = tello.get_current_state() if tello else None

        def _get(key: str, default: float | int = 0) -> float | int:
            if state and key in state:
                try:
                    val = state[key]
                    return float(val) if isinstance(val, (int, float, str)) else default
                except (ValueError, TypeError):
                    return default
            return default

        self.battery = float(_get("bat", 0))
        self.bat = self.battery
        self.latency_ms = self._latency_ms
        self.height_cm = float(_get("h", 0))
        self.altitude_m = self.height_cm / 100.0
        self.mission_time_s = time.monotonic() - self._mission_start

        self.yaw = float(_get("yaw", 0))
        self.pitch = float(_get("pitch", 0))
        self.roll = float(_get("roll", 0))

        self.speed_x = float(_get("vgx", 0))
        self.speed_y = float(_get("vgy", 0))
        self.speed_z = float(_get("vgz", 0))

        self.mission_pad_id = int(_get("mid", -1))

        self.templ = float(_get("templ", 0))
        self.temph = float(_get("temph", 0))
        self.temp = (self.templ + self.temph) / 2.0 if (self.templ or self.temph) else 0.0

        self.link_ok = state is not None and len(state) > 0

    def to_telemetry_snapshot(self) -> TelemetrySnapshot:
        """Return TelemetrySnapshot for MDP policy and safety checks."""
        return TelemetrySnapshot(
            battery=self.battery,
            latency_ms=self.latency_ms,
            altitude_m=self.altitude_m,
            mission_time_s=self.mission_time_s,
            link_ok=self.link_ok,
        )


def _main() -> None:
    """Stream flight data to stdout. Run with: aegis run flight_ops/control/flight_data_collector.py"""
    import os
    import sys

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from djitellopy import Tello

    t = Tello()
    time.sleep(1)
    t.connect(wait_for_state=True)
    print("Connected. Streaming flight data (Ctrl+C to quit)...\n")

    sensor = FlightDataCollector(t)
    try:
        while True:
            sensor.collect()
            print(
                f"\rbattery={sensor.bat:.0f}% alt={sensor.altitude_m:.2f}m "
                f"yaw={sensor.yaw:.0f} pitch={sensor.pitch:.0f} roll={sensor.roll:.0f} "
                f"vx={sensor.speed_x:.0f} vy={sensor.speed_y:.0f} vz={sensor.speed_z:.0f} "
                f"temp={sensor.temp:.0f}°C t={sensor.mission_time_s:.1f}s",
                end="",
            )
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        t.end()


if __name__ == "__main__":
    _main()
