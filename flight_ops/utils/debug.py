"""Print all Tello state fields to the terminal."""

from djitellopy import Tello
import time
import threading
import csv
import os
from datetime import datetime

# Project root (flight_ops/utils -> flight_ops -> repo root)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(_PROJECT_ROOT, "tmp", "logs")
METRICS_CSV = os.path.join(LOG_DIR, "command_metrics.csv")

_metrics_lock = threading.Lock()
_latest_metrics = None
_csv_lock = threading.Lock()


def collect_command_metrics(tello: Tello, num_probes: int = 10, probe_interval: float = 0.15) -> dict:
    """Collect latency and bandwidth metrics by sending probe commands to the Tello."""
    PROBE_CMD = "battery?"
    latencies_ms = []
    bytes_sent = 0
    bytes_received = 0
    cmd_bytes = len(PROBE_CMD.encode("utf-8"))
    start_time = time.perf_counter()

    for _ in range(num_probes):
        t0 = time.perf_counter()
        try:
            response = tello.send_command_with_return(PROBE_CMD, timeout=3)
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000)
            bytes_sent += cmd_bytes
            bytes_received += len(response.encode("utf-8"))
        except Exception:
            pass
        time.sleep(max(0, probe_interval - (time.perf_counter() - t0)))

    elapsed = time.perf_counter() - start_time
    return {
        "latency_ms_min": min(latencies_ms) if latencies_ms else 0,
        "latency_ms_max": max(latencies_ms) if latencies_ms else 0,
        "latency_ms_avg": sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0,
        "latency_samples": len(latencies_ms),
        "bytes_sent": bytes_sent,
        "bytes_received": bytes_received,
        "duration_sec": elapsed,
        "bandwidth_sent_bps": bytes_sent / elapsed if elapsed > 0 else 0,
        "bandwidth_recv_bps": bytes_received / elapsed if elapsed > 0 else 0,
    }


def write_metrics_to_csv(m: dict) -> None:
    """Append metrics to CSV in project tmp/logs."""
    os.makedirs(LOG_DIR, exist_ok=True)
    fieldnames = ["timestamp", "latency_ms_min", "latency_ms_max", "latency_ms_avg",
                  "latency_samples", "bytes_sent", "bytes_received", "duration_sec",
                  "bandwidth_sent_bps", "bandwidth_recv_bps"]
    row = {"timestamp": datetime.now().isoformat(), **m}
    with _csv_lock:
        write_header = not os.path.exists(METRICS_CSV) or os.path.getsize(METRICS_CSV) == 0
        with open(METRICS_CSV, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if write_header:
                w.writeheader()
            w.writerow(row)


def main():
    t = Tello()
    should_exit = threading.Event()

    def wait_for_enter():
        input()
        should_exit.set()

    try:
        time.sleep(1)
        t.connect()
        print("Connected. Streaming state (Press Enter or Ctrl+C to quit)...\n")
        threading.Thread(target=wait_for_enter, daemon=True).start()

        def metrics_collector():
            global _latest_metrics
            while not should_exit.is_set():
                try:
                    m = collect_command_metrics(t, num_probes=5, probe_interval=0.2)
                    with _metrics_lock:
                        _latest_metrics = m
                    write_metrics_to_csv(m)
                except Exception:
                    pass
                for _ in range(30):
                    if should_exit.is_set():
                        return
                    time.sleep(0.1)

        threading.Thread(target=metrics_collector, daemon=True).start()

        while not should_exit.is_set():
            state = t.get_current_state()
            if not state:
                print("Waiting for state packets...")
                time.sleep(0.5)
                continue

            print("\033[2J\033[H", end="")
            print("=== Tello State ===\n")
            print(f"  roll        = {str(state.get('roll', 'N/A')):>10}  (roll (deg))")
            print(f"  pitch       = {str(state.get('pitch', 'N/A')):>10}  (pitch (deg))")
            print(f"  yaw         = {str(state.get('yaw', 'N/A')):>10}  (yaw (deg))")
            print(f"  vgx         = {str(state.get('vgx', 'N/A')):>10}  (speed X (cm/s))")
            print(f"  vgy         = {str(state.get('vgy', 'N/A')):>10}  (speed Y (cm/s))")
            print(f"  vgz         = {str(state.get('vgz', 'N/A')):>10}  (speed Z (cm/s))")
            print(f"  agx         = {str(state.get('agx', 'N/A')):>10}  (accel X)")
            print(f"  agy         = {str(state.get('agy', 'N/A')):>10}  (accel Y)")
            print(f"  agz         = {str(state.get('agz', 'N/A')):>10}  (accel Z)")
            print(f"  h           = {str(state.get('h', 'N/A')):>10}  (height (cm))")
            print(f"  tof         = {str(state.get('tof', 'N/A')):>10}  (TOF distance (cm))")
            print(f"  baro        = {str(state.get('baro', 'N/A')):>10}  (barometer (m))")
            print(f"  mid         = {str(state.get('mid', 'N/A')):>10}  (mission pad ID (-1=none, 1-8))")
            print(f"  x           = {str(state.get('x', 'N/A')):>10}  (mission pad distance X (cm))")
            print(f"  y           = {str(state.get('y', 'N/A')):>10}  (mission pad distance Y (cm))")
            print(f"  z           = {str(state.get('z', 'N/A')):>10}  (mission pad distance Z (cm))")
            print(f"  templ       = {str(state.get('templ', 'N/A')):>10}  (temp low (°C))")
            print(f"  temph       = {str(state.get('temph', 'N/A')):>10}  (temp high (°C))")
            print(f"  bat         = {str(state.get('bat', 'N/A')):>10}  (battery (%))")
            print(f"  time        = {str(state.get('time', 'N/A')):>10}  (flight time (s))")
            print(f"  received_at = {str(state.get('received_at', 'N/A')):>10}  (last update)")

            with _metrics_lock:
                m = _latest_metrics
            if m:
                print("\n=== Command Metrics (latency & bandwidth) ===")
                print(f"  latency_ms  = {m['latency_ms_avg']:.1f} avg  {m['latency_ms_min']:.1f} min  {m['latency_ms_max']:.1f} max  ({m['latency_samples']} samples)")
                print(f"  bw_sent     = {m['bandwidth_sent_bps']:.1f} B/s  ({m['bytes_sent']} B total)")
                print(f"  bw_recv     = {m['bandwidth_recv_bps']:.1f} B/s  ({m['bytes_received']} B total)")

            time.sleep(0.1)

    except KeyboardInterrupt:
        pass
    finally:
        print("\nStopped.")
        try:
            t.end()
        except Exception as e:
            print("Cleanup:", repr(e))


if __name__ == "__main__":
    main()
