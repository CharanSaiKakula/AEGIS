from djitellopy import Tello
import time
import threading

# =========================================================
# CONFIGURATION
# =========================================================
REFERENCE_CLIMB_CM = 50     # after takeoff, move up this much to define reference point
MIN_MOVE_CM = 20
MAX_MOVE_CM = 100
TELEMETRY_DT = 0.05         # seconds between telemetry updates

# =========================================================
# COORDINATE CONVENTION
# =========================================================
# Expected / Actual coordinates are defined as:
#
# X = forward / back
# Y = right / left
# Z = up / down
#
# So:
# forward 50 -> X += 50
# back 20    -> X -= 20
# right 30   -> Y += 30
# left 10    -> Y -= 10
# up 20      -> Z += 20
# down 20    -> Z -= 20

# =========================================================
# DRONE + STATE
# =========================================================
tello = Tello()

# Software expected position (from commands)
expected_x = 0.0
expected_y = 0.0
expected_z = 0.0

# Telemetry-estimated actual position
actual_x = 0.0
actual_y = 0.0
actual_z = 0.0

# Reference / flight state
is_flying = False
reference_set = False

# Baselines captured at reference point
baseline_h = None
baseline_tof = None

# Telemetry thread control
telemetry_running = False
stop_telemetry = False

# Thread safety
state_lock = threading.Lock()


# =========================================================
# HELPERS: RESET / UPDATE
# =========================================================
def reset_expected_position():
    global expected_x, expected_y, expected_z
    expected_x = 0.0
    expected_y = 0.0
    expected_z = 0.0


def reset_actual_position():
    global actual_x, actual_y, actual_z
    actual_x = 0.0
    actual_y = 0.0
    actual_z = 0.0


def update_expected_position(direction, distance_cm):
    global expected_x, expected_y, expected_z

    if direction == "forward":
        expected_x += distance_cm
    elif direction == "back":
        expected_x -= distance_cm
    elif direction == "right":
        expected_y += distance_cm
    elif direction == "left":
        expected_y -= distance_cm
    elif direction == "up":
        expected_z += distance_cm
    elif direction == "down":
        expected_z -= distance_cm


# =========================================================
# HELPERS: FORMATTING
# =========================================================
def fmt_expected(value):
    return str(int(round(value)))


def fmt_actual(value):
    return f"{value:.1f}"


def fmt_error(value):
    return f"{value:+.1f}"


# =========================================================
# HELPERS: TELEMETRY / REFERENCE
# =========================================================
def set_reference_baseline():
    global baseline_h, baseline_tof

    state = tello.get_current_state()

    h = state.get("h")
    tof = state.get("tof")

    baseline_h = h if isinstance(h, int) else None
    baseline_tof = tof if isinstance(tof, int) else None


def current_actual_z():
    """
    Prefer normalized 'h' if available; fall back to normalized TOF.
    """
    state = tello.get_current_state()

    h = state.get("h")
    tof = state.get("tof")

    if isinstance(h, int) and isinstance(baseline_h, int):
        return float(h - baseline_h)

    if isinstance(tof, int) and isinstance(baseline_tof, int):
        return float(tof - baseline_tof)

    return actual_z


# =========================================================
# TELEMETRY INTEGRATION THREAD
# =========================================================
def telemetry_loop():
    global actual_x, actual_y, actual_z, stop_telemetry, telemetry_running

    telemetry_running = True
    last_time = time.time()

    while not stop_telemetry:
        try:
            state = tello.get_current_state()

            now = time.time()
            dt = now - last_time
            last_time = now

            # Tello reports velocities in cm/s
            vgx = state.get("vgx", 0)
            vgy = state.get("vgy", 0)

            if not isinstance(vgx, (int, float)):
                vgx = 0
            if not isinstance(vgy, (int, float)):
                vgy = 0

            with state_lock:
                # X = forward/back (use vgx)
                actual_x += float(vgx) * dt

                # Y = right/left (use vgy)
                actual_y += float(vgy) * dt

                # Z = use normalized height when reference exists
                if reference_set:
                    actual_z = current_actual_z()

            time.sleep(TELEMETRY_DT)

        except Exception:
            time.sleep(TELEMETRY_DT)

    telemetry_running = False


def start_telemetry():
    global stop_telemetry

    stop_telemetry = False
    thread = threading.Thread(target=telemetry_loop, daemon=True)
    thread.start()
    return thread


# =========================================================
# REPORT
# =========================================================
def print_position_report():
    with state_lock:
        ex = expected_x
        ey = expected_y
        ez = expected_z

        ax = actual_x
        ay = actual_y
        az = actual_z

    err_x = ax - ex
    err_y = ay - ey
    err_z = az - ez

    print()
    print("Expected")
    print(f"X {fmt_expected(ex)}")
    print(f"Y {fmt_expected(ey)}")
    print(f"Z {fmt_expected(ez)}")
    print()
    print("Actual")
    print(f"X {fmt_actual(ax)}")
    print(f"Y {fmt_actual(ay)}")
    print(f"Z {fmt_actual(az)}")
    print()
    print("Error")
    print(f"X {fmt_error(err_x)}")
    print(f"Y {fmt_error(err_y)}")
    print(f"Z {fmt_error(err_z)}")
    print()


# =========================================================
# COMMAND EXECUTION
# =========================================================
def execute_move(direction, distance_cm):
    print(f"Commanding: {direction} {distance_cm} cm")

    if direction == "forward":
        tello.move_forward(distance_cm)
    elif direction == "back":
        tello.move_back(distance_cm)
    elif direction == "right":
        tello.move_right(distance_cm)
    elif direction == "left":
        tello.move_left(distance_cm)
    elif direction == "up":
        tello.move_up(distance_cm)
    elif direction == "down":
        tello.move_down(distance_cm)
    else:
        print("Invalid direction.")
        return

    update_expected_position(direction, distance_cm)

    # Let telemetry settle a moment after the move
    time.sleep(0.5)

    print_position_report()


def print_help():
    print("\nAvailable commands:")
    print("  takeoff")
    print("  reference")
    print("  forward 50")
    print("  back 20")
    print("  right 30")
    print("  left 20")
    print("  up 20")
    print("  down 20")
    print("  pos")
    print("  help")
    print("  land")
    print("  quit")
    print("  q   (EMERGENCY STOP)\n")


# =========================================================
# MAIN
# =========================================================
telemetry_thread = None

try:
    print("Connecting to drone...")
    tello.connect()

    battery = tello.get_battery()
    print(f"Battery: {battery}%")

    if battery < 20:
        print("Battery too low to fly.")
        raise SystemExit

    print("Waiting for drone to settle...")
    time.sleep(3)

    telemetry_thread = start_telemetry()

    print("Drone connected.")
    print("This script does NOT auto-takeoff.")
    print("Type 'takeoff' when ready.")
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
            reference_set = False
            break

        if user_input == "help":
            print_help()
            continue

        if user_input == "pos":
            print_position_report()
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
                time.sleep(1)

                is_flying = True
                reference_set = False
                reset_expected_position()
                reset_actual_position()

                print("Takeoff successful.")
                print("Now type 'reference' to define the normalized hover point.")
            except Exception as e:
                print(f"Takeoff failed: {e}")
                is_flying = False
                reference_set = False
            continue

        if user_input == "reference":
            if not is_flying:
                print("Drone must take off before setting a reference point.")
                continue

            try:
                print(f"Moving to reference hover point (+{REFERENCE_CLIMB_CM} cm)...")
                tello.move_up(REFERENCE_CLIMB_CM)
                time.sleep(1)

                reset_expected_position()
                reset_actual_position()
                set_reference_baseline()
                reference_set = True

                print("Reference hover point established.")
                print("Reference point is now treated as X=0, Y=0, Z=0.")
                print_position_report()
            except Exception as e:
                print(f"Reference setup failed: {e}")
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
            reference_set = False
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
            reference_set = False
            break

        parts = user_input.split()

        if len(parts) != 2:
            print("Invalid format. Example: forward 50")
            continue

        if not is_flying:
            print("Drone must take off before movement commands.")
            continue

        if not reference_set:
            print("Set the reference point first using: reference")
            continue

        direction = parts[0]

        try:
            distance_cm = int(parts[1])
        except ValueError:
            print("Distance must be a whole number in centimeters.")
            continue

        if direction not in ["forward", "back", "right", "left", "up", "down"]:
            print("Invalid direction.")
            continue

        if distance_cm < MIN_MOVE_CM:
            print(f"Tello move commands should usually be at least {MIN_MOVE_CM} cm.")
            continue

        if distance_cm > MAX_MOVE_CM:
            print(f"Distance too large. Keep move commands at {MAX_MOVE_CM} cm or less.")
            continue

        try:
            current_battery = tello.get_battery()
            print(f"Current battery: {current_battery}%")

            if current_battery < 20:
                print("Battery too low for another move. Landing recommended.")
                continue

            execute_move(direction, distance_cm)
        except Exception as e:
            print(f"Move failed: {e}")
            print("Drone state may no longer match software state.")
            print("Use 'pos' to inspect position.")
            print("If needed, use 'land' or 'q'.")

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
    stop_telemetry = True

    try:
        state = tello.get_current_state()
        height = state.get("tof", 0)

        if isinstance(height, int) and height > 10:
            print("Attempting safe landing in cleanup...")
            tello.land()
            print("Cleanup landing complete.")
    except Exception:
        pass
        