from djitellopy import Tello
import time

# =========================================================
# CONFIG
# =========================================================
MIN_MOVE_CM = 20
MAX_MOVE_CM = 100
SAFE_RTH_Z_CM = 50   # if below this relative z, go up first before returning home

# =========================================================
# COORDINATE CONVENTION
# =========================================================
# X = forward / back
# Y = right / left
# Z = up / down
#
# forward 50 -> X += 50
# back 20    -> X -= 20
# right 30   -> Y += 30
# left 10    -> Y -= 10
# up 20      -> Z += 20
# down 20    -> Z -= 20

# =========================================================
# STATE
# =========================================================
tello = Tello()

is_flying = False
home_set = False

expected_x = 0
expected_y = 0
expected_z = 0


# =========================================================
# HELPERS
# =========================================================
def reset_expected_position():
    global expected_x, expected_y, expected_z
    expected_x = 0
    expected_y = 0
    expected_z = 0


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


def print_position_report():
    state = tello.get_current_state()

    bat = state.get("bat", "N/A")
    tof = state.get("tof", "N/A")
    h = state.get("h", "N/A")
    yaw = state.get("yaw", "N/A")

    print()
    print("Tracked Position")
    print(f"X {expected_x}")
    print(f"Y {expected_y}")
    print(f"Z {expected_z}")
    print()
    print("Telemetry")
    print(f"Battery {bat}")
    print(f"TOF     {tof}")
    print(f"h       {h}")
    print(f"Yaw     {yaw}")
    print()


def print_help():
    print("\nAvailable commands:")
    print("  takeoff")
    print("  home")
    print("  forward 50")
    print("  back 20")
    print("  right 30")
    print("  left 20")
    print("  up 20")
    print("  down 20")
    print("  pos")
    print("  rth")
    print("  rth_land")
    print("  land")
    print("  help")
    print("  quit")
    print("  q   (EMERGENCY STOP)\n")


def execute_move(direction, distance_cm, print_after=True):
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

    if print_after:
        print_position_report()


def execute_inverse_move(direction, distance_cm, print_after=False):
    """
    Executes the reverse move physically while updating tracked position correctly.
    """
    if distance_cm <= 0:
        return

    if direction == "forward":
        execute_move("back", distance_cm, print_after=print_after)
    elif direction == "back":
        execute_move("forward", distance_cm, print_after=print_after)
    elif direction == "right":
        execute_move("left", distance_cm, print_after=print_after)
    elif direction == "left":
        execute_move("right", distance_cm, print_after=print_after)
    elif direction == "up":
        execute_move("down", distance_cm, print_after=print_after)
    elif direction == "down":
        execute_move("up", distance_cm, print_after=print_after)


def do_return_to_home(land_after=False):
    global expected_x, expected_y, expected_z, home_set

    if not is_flying:
        print("Drone is not flying.")
        return

    if not home_set:
        print("Home point not set. Use 'home' first.")
        return

    print("\nStarting return to home...")
    print("Current tracked position before RTH:")
    print_position_report()

    # Step 1: rise to safe return altitude if below it
    if expected_z < SAFE_RTH_Z_CM:
        climb_needed = SAFE_RTH_Z_CM - expected_z
        if climb_needed >= MIN_MOVE_CM:
            print(f"Climbing to safe return altitude: +{climb_needed} cm")
            execute_move("up", climb_needed, print_after=False)

    # Step 2: correct Y first (right/left)
    if expected_y > 0:
        print(f"Returning Y to home: left {expected_y} cm")
        execute_move("left", expected_y, print_after=False)
    elif expected_y < 0:
        print(f"Returning Y to home: right {abs(expected_y)} cm")
        execute_move("right", abs(expected_y), print_after=False)

    # Step 3: correct X (forward/back)
    if expected_x > 0:
        print(f"Returning X to home: back {expected_x} cm")
        execute_move("back", expected_x, print_after=False)
    elif expected_x < 0:
        print(f"Returning X to home: forward {abs(expected_x)} cm")
        execute_move("forward", abs(expected_x), print_after=False)

    # Step 4: descend to home Z = 0
    if expected_z > 0:
        print(f"Returning Z to home: down {expected_z} cm")
        execute_move("down", expected_z, print_after=False)
    elif expected_z < 0:
        print(f"Returning Z to home: up {abs(expected_z)} cm")
        execute_move("up", abs(expected_z), print_after=False)

    # Clean reset in software
    reset_expected_position()

    print("\nReturn to home complete.")
    print_position_report()

    if land_after:
        print("Landing at home...")
        tello.land()
        print("Flight complete.")


# =========================================================
# MAIN
# =========================================================
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
            home_set = False
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
                time.sleep(1.5)

                is_flying = True
                home_set = False
                reset_expected_position()

                print("Takeoff successful.")
                print("Now use 'home' to define the home point.")
                print_position_report()
            except Exception as e:
                print(f"Takeoff failed: {e}")
                is_flying = False
            continue

        if user_input == "home":
            if not is_flying:
                print("Drone must take off before setting home.")
                continue

            # Optional: normalize by climbing to safe return altitude first
            if expected_z < SAFE_RTH_Z_CM:
                climb_needed = SAFE_RTH_Z_CM - expected_z
                if climb_needed >= MIN_MOVE_CM:
                    try:
                        print(f"Climbing to safe home altitude: +{climb_needed} cm")
                        execute_move("up", climb_needed, print_after=False)
                    except Exception as e:
                        print(f"Failed to reach safe home altitude: {e}")
                        continue

            reset_expected_position()
            home_set = True

            print("Home point set.")
            print(f"Current position is now treated as X=0, Y=0, Z=0.")
            print_position_report()
            continue

        if user_input == "rth":
            try:
                do_return_to_home(land_after=False)
            except Exception as e:
                print(f"RTH failed: {e}")
            continue

        if user_input == "rth_land":
            try:
                do_return_to_home(land_after=True)
                is_flying = False
            except Exception as e:
                print(f"RTH land failed: {e}")
            break

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
            home_set = False
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
            home_set = False
            break

        parts = user_input.split()

        if len(parts) != 2:
            print("Invalid format. Example: forward 50")
            continue

        if not is_flying:
            print("Drone must take off before movement commands.")
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

            execute_move(direction, distance_cm, print_after=True)

        except Exception as e:
            print(f"Move failed: {e}")
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
    try:
        state = tello.get_current_state()
        height = state.get("tof", 0)

        if isinstance(height, int) and height > 10:
            print("Attempting safe landing in cleanup...")
            tello.land()
            print("Cleanup landing complete.")
    except Exception:
        pass

        # How to use:
        # use this sequence:
        takeoff
# home
# forward 50
# right 30
# up 20
# pos
# rth
# pos
# land

# After the moves, tracked position should be:
# # X 50
# Y 30
# Z 20


# Presenting :
# “We define home manually, track movement commands in software, and execute a safe reverse-path return-to-home with altitude protection.”