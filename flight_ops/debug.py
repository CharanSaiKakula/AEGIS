"""Print all Tello state fields to the terminal."""

from djitellopy import Tello
import time
import threading


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

        while not should_exit.is_set():
            state = t.get_current_state()

            if not state:
                print("Waiting for state packets...")
                time.sleep(0.5)
                continue

            # Clear line and print header
            print("\033[2J\033[H", end="")  # Clear screen, cursor home
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
