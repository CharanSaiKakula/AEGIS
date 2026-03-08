from djitellopy import Tello
import time

# ---------------------------------
# CONFIGURATION
# ---------------------------------
REFERENCE_CLIMB_CM = 100
MIN_MOVE_CM = 20
MAX_MOVE_CM = 500

# ---------------------------------
# POSITION STATE
# These are software-estimated coordinates
# relative to the reference hover point.
# ---------------------------------
expected_x = 0   # right/left
expected_y = 0   # forward/back
expected_z = 0   # up/down relative to reference point

# Drone state flags
is_flying = False
reference_set = False

# ---------------------------------
# DRONE OBJECT
# ---------------------------------
tello = Tello()


# ---------------------------------
# HELPERS
# ---------------------------------
def reset_expected_position():
    global expected_x, expected_y, expected_z
    expected_x = 0
    expected_y = 0
    expected_z = 0


def update_expected_position(direction, distance_cm):
    global expected_x, expected_y, expected_z

    if direction == "forward":
        expected_y += distance_cm
    elif direction == "back":
        expected_y -= distance_cm
    elif direction == "right":
        expected_x += distance_cm
    elif direction == "left":
        expected_x -= distance_cm
    elif direction == "up":
        expected_z += distance_cm
    elif direction == "down":
        expected_z -= distance_cm


def print_position_report():
    state = tello.get_current_state()

    print("\n--- POSITION REPORT ---")
    print(
        f"Expected position relative to reference point -> "
        f"x={expected_x} cm, y={expected_y} cm, z={expected_z} cm"
    )

    tof = state.get("tof", "N/A")
    h = state.get("h", "N/A")
    baro = state.get("baro", "N/A")
    pitch = state.get("pitch", "N/A")
    roll = state.get("roll", "N/A")
    yaw = state.get("yaw", "N/A")
    vgx = state.get("vgx", "N/A")
    vgy = state.get("vgy", "N/A")
    vgz = state.get("vgz", "N/A")
    bat = state.get("bat", "N/A")

    print(f"Battery -> {bat}%")
    print(f"TOF height above ground -> {tof}")
    print(f"Reported height (h) -> {h}")
    print(f"Barometer -> {baro}")
    print(f"Attitude -> pitch={pitch}, roll={roll}, yaw={yaw}")
    print(f"Velocity -> vgx={vgx}, vgy={vgy}, vgz={vgz}")
    print("-----------------------\n")


def print_status():
    print("\n--- SOFTWARE STATUS ---")
    print(f"is_flying = {is_flying}")
    print(f"reference_set = {reference_set}")
    print("-----------------------")
    print_position_report()


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
    print("Move executed successfully.")
    print_position_report()


def print_help():
    print("\nAvailable commands:")
    print("  takeoff")
    print("  reference")
    print("  forward 20")
    print("  back 20")
    print("  right 20")
    print("  left 20")
    print("  up 20")
    print("  down 20")
    print("  pos")
    print("  status")
    print("  help")
    print("  land")
    print("  quit")
    print("  q   (EMERGENCY STOP)\n")


# ---------------------------------
# MAIN PROGRAM
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
    time.sleep(3)

    print("Drone connected.")
    print("This script does NOT auto-takeoff.")
    print("Type 'takeoff' when you are ready.")
    print_help()

    while True:
        user_input = input("Command: ").strip().lower()

        # EMERGENCY STOP
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

        if user_input == "status":
            print_status()
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

                print("Takeoff successful.")
                print("Now type 'reference' to climb and establish the reference hover point.")
                print_position_report()
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

                reset_expected_position()
                reference_set = True

                print("Reference hover point established.")
                print("Reference point is now treated as x=0, y=0, z=0 in software.")
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
                is_flying = False
                reference_set = False
            else:
                print("Quitting.")
            break

        parts = user_input.split()

        if len(parts) != 2:
            print("Invalid format. Example: forward 20")
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
            print("Use 'status' to inspect software state.")
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
    # Last-resort cleanup landing attempt
    try:
        state = tello.get_current_state()
        height = state.get("tof", 0)

        if isinstance(height, int) and height > 10:
            print("Attempting safe landing in cleanup...")
            tello.land()
            print("Cleanup landing complete.")
    except Exception:
        pass
        