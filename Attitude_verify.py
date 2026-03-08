from djitellopy import Tello
import time
import threading

# ---------------------------------
# CONFIG
# ---------------------------------
ATTITUDE_PRINT_DT = 0.05   # telemetry polling rate
PULSE_DURATION = 1.0       # seconds for RC pulse
RC_SPEED = 30              # rc speed (-100 to 100)

# ---------------------------------
# STATE
# ---------------------------------
tello = Tello()

is_flying = False
stop_attitude_thread = False
attitude_thread_started = False

latest_pitch = 0
latest_roll = 0
latest_yaw = 0
latest_bat = 0
latest_tof = 0

baseline_yaw = None

state_lock = threading.Lock()


# ---------------------------------
# TELEMETRY THREAD
# ---------------------------------
def attitude_loop():
    global latest_pitch, latest_roll, latest_yaw, latest_bat, latest_tof

    while not stop_attitude_thread:
        try:
            state = tello.get_current_state()

            with state_lock:
                latest_pitch = state.get("pitch", 0)
                latest_roll = state.get("roll", 0)
                latest_yaw = state.get("yaw", 0)
                latest_bat = state.get("bat", 0)
                latest_tof = state.get("tof", 0)

            time.sleep(ATTITUDE_PRINT_DT)

        except Exception:
            time.sleep(ATTITUDE_PRINT_DT)


def start_attitude_thread():
    global attitude_thread_started
    if not attitude_thread_started:
        t = threading.Thread(target=attitude_loop, daemon=True)
        t.start()
        attitude_thread_started = True


# ---------------------------------
# HELPERS
# ---------------------------------
def get_latest_attitude():
    with state_lock:
        return latest_pitch, latest_roll, latest_yaw, latest_bat, latest_tof


def print_attitude():
    p, r, y, b, tof = get_latest_attitude()

    print()
    print("Attitude")
    print(f"Pitch {p}")
    print(f"Roll  {r}")
    print(f"Yaw   {y}")
    print()
    print("Other")
    print(f"Battery {b}")
    print(f"TOF     {tof}")
    print()

    if baseline_yaw is not None:
        yaw_change = y - baseline_yaw
        print(f"Yaw change from baseline -> {yaw_change}")
        print()


def print_help():
    print("\nAvailable commands:")
    print("  takeoff")
    print("  baseline")
    print("  pos")
    print("  cw 30")
    print("  ccw 30")
    print("  pulse_forward")
    print("  pulse_back")
    print("  pulse_right")
    print("  pulse_left")
    print("  land")
    print("  quit")
    print("  q   (EMERGENCY STOP)\n")


# ---------------------------------
# RC PULSE + PEAK ATTITUDE CAPTURE
# ---------------------------------
def rc_pulse_with_peak_capture(name, lr=0, fb=0, ud=0, yw=0, duration=PULSE_DURATION):
    """
    Sends a short RC pulse and captures:
    - max absolute pitch seen during the pulse
    - max absolute roll seen during the pulse
    - final yaw and yaw delta from baseline
    """
    max_abs_pitch = 0
    max_abs_roll = 0
    pitch_at_max = 0
    roll_at_max = 0

    print(f"Sending {name} pulse...")
    tello.send_rc_control(lr, fb, ud, yw)

    start = time.time()
    while time.time() - start < duration:
        p, r, _, _, _ = get_latest_attitude()

        if abs(p) > max_abs_pitch:
            max_abs_pitch = abs(p)
            pitch_at_max = p

        if abs(r) > max_abs_roll:
            max_abs_roll = abs(r)
            roll_at_max = r

        time.sleep(ATTITUDE_PRINT_DT)

    tello.send_rc_control(0, 0, 0, 0)
    time.sleep(0.4)  # let drone settle

    p, r, y, b, tof = get_latest_attitude()

    print()
    print(f"{name} pulse results")
    print(f"Max Pitch Seen During Pulse {pitch_at_max}")
    print(f"Max Roll Seen During Pulse  {roll_at_max}")
    print()
    print("Final Attitude")
    print(f"Pitch {p}")
    print(f"Roll  {r}")
    print(f"Yaw   {y}")
    print()
    print("Other")
    print(f"Battery {b}")
    print(f"TOF     {tof}")
    print()

    if baseline_yaw is not None:
        yaw_change = y - baseline_yaw
        print(f"Final Yaw Change From Baseline {yaw_change}")
        print()


# ---------------------------------
# MAIN
# ---------------------------------
try:
    print("Connecting to drone...")
    tello.connect()

    battery = tello.get_battery()
    print(f"Battery: {battery}%")

    if battery < 20:
        print("Battery too low to fly.")
        raise SystemExit

    print("Waiting for drone to settle...")
    time.sleep(2)

    start_attitude_thread()

    print("Drone connected.")
    print("This script does NOT auto-takeoff.")
    print_help()

    while True:
        user_input = input("Command: ").strip().lower()

        if user_input == "q":
            print("\n!!! EMERGENCY STOP ACTIVATED !!!")
            try:
                tello.emergency()
            except Exception as e:
                print(f"Emergency stop warning: {e}")
            is_flying = False
            break

        if user_input == "help":
            print_help()
            continue

        if user_input == "pos":
            print_attitude()
            continue

        if user_input == "takeoff":
            if is_flying:
                print("Drone is already flying.")
                continue

            try:
                current_battery = tello.get_battery()
                print(f"Current battery: {current_battery}%")

                if current_battery < 20:
                    print("Battery too low to take off.")
                    continue

                print("Taking off...")
                tello.takeoff()
                time.sleep(1.5)
                is_flying = True
                print("Takeoff successful.")
                print_attitude()
            except Exception as e:
                print(f"Takeoff failed: {e}")
                is_flying = False
            continue

        if user_input == "baseline":
            global_baseline = get_latest_attitude()[2]
            baseline_yaw = global_baseline
            print(f"Baseline yaw set to {baseline_yaw}")
            continue

        if user_input == "land":
            if not is_flying:
                print("Drone is already on the ground.")
                break

            try:
                print("Landing...")
                tello.land()
                print("Flight complete.")
            except Exception as e:
                print(f"Landing failed: {e}")

            is_flying = False
            break

        if user_input == "quit":
            if is_flying:
                try:
                    print("Quitting safely by landing...")
                    tello.land()
                    print("Flight complete.")
                except Exception as e:
                    print(f"Quit landing warning: {e}")
            else:
                print("Quitting.")

            is_flying = False
            break

        if not is_flying:
            print("Drone must take off before movement commands.")
            continue

        if user_input == "pulse_forward":
            rc_pulse_with_peak_capture(
                name="Forward",
                lr=0,
                fb=RC_SPEED,
                ud=0,
                yw=0
            )
            continue

        if user_input == "pulse_back":
            rc_pulse_with_peak_capture(
                name="Back",
                lr=0,
                fb=-RC_SPEED,
                ud=0,
                yw=0
            )
            continue

        if user_input == "pulse_right":
            rc_pulse_with_peak_capture(
                name="Right",
                lr=RC_SPEED,
                fb=0,
                ud=0,
                yw=0
            )
            continue

        if user_input == "pulse_left":
            rc_pulse_with_peak_capture(
                name="Left",
                lr=-RC_SPEED,
                fb=0,
                ud=0,
                yw=0
            )
            continue

        parts = user_input.split()

        if len(parts) == 2 and parts[0] in ["cw", "ccw"]:
            try:
                angle = int(parts[1])
            except ValueError:
                print("Angle must be a whole number.")
                continue

            if angle < 1 or angle > 360:
                print("Keep angle between 1 and 360.")
                continue

            try:
                if parts[0] == "cw":
                    print(f"Rotating clockwise {angle} degrees...")
                    tello.rotate_clockwise(angle)
                else:
                    print(f"Rotating counterclockwise {angle} degrees...")
                    tello.rotate_counter_clockwise(angle)

                time.sleep(0.5)

                p, r, y, b, tof = get_latest_attitude()

                print()
                print("Rotation Results")
                print(f"Pitch {p}")
                print(f"Roll  {r}")
                print(f"Yaw   {y}")
                print()
                print("Other")
                print(f"Battery {b}")
                print(f"TOF     {tof}")
                print()

                if baseline_yaw is not None:
                    yaw_change = y - baseline_yaw
                    print(f"Final Yaw Change From Baseline {yaw_change}")
                    print()

            except Exception as e:
                print(f"Rotation failed: {e}")

            continue

        print("Invalid command.")
        print_help()

except KeyboardInterrupt:
    print("\nKeyboard interrupt detected.")
    try:
        if is_flying:
            print("Attempting safe landing...")
            tello.land()
            print("Landing complete.")
    except Exception as e:
        print(f"Keyboard interrupt landing warning: {e}")

except Exception as e:
    print(f"Error: {e}")

finally:
    stop_attitude_thread = True

    try:
        state = tello.get_current_state()
        height = state.get("tof", 0)

        if isinstance(height, int) and height > 10:
            print("Attempting safe landing in cleanup...")
            tello.land()
            print("Cleanup landing complete.")
    except Exception:
        pass

        #takeoff
# #pos
# # baseline
# cw 30
# pos
# ccw 30
# pos
# pulse_forward
# pulse_back
# pulse_right
# pulse_left
# #land

# Output:
# Rotation Results
# Pitch 0
# Roll  0
# Yaw   82

# Other
# Battery 67
# TOF     115

# Final Yaw Change From Baseline 30

# Forward pulse results
# Max Pitch Seen During Pulse 8
# Max Roll Seen During Pulse  1

# Final Attitude
# Pitch 0
# Roll  0
# Yaw   52

# Other
# Battery 66
# TOF     118

# Final Yaw Change From Baseline 0