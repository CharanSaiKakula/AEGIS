from djitellopy import Tello
import time

# ---------------------------------
# DRONE SETUP
# ---------------------------------
tello = Tello()

print("Connecting to drone...")
tello.connect()
print("Battery:", tello.get_battery())

print("Taking off...")
tello.takeoff()
time.sleep(2)

# Move to reference hover point
# NOTE: takeoff already rises somewhat, so 50 cm is safer indoors than 100
print("Moving to reference hover point...")
tello.move_up(50)
time.sleep(2)

print("Reference hover point established.")

# ---------------------------------
# SOFTWARE POSITION TRACKING
# This hover point is treated as (0,0,0)
# x = left/right
# y = forward/back
# z = up/down
# ---------------------------------
current_x = 0
current_y = 0
current_z = 0

# ---------------------------------
# GEOFENCE BOUNDS (cm)
# 0.5 m = 50 cm in each direction
# ---------------------------------
X_MIN = -50
X_MAX = 50
Y_MIN = -50
Y_MAX = 50
Z_MIN = -50
Z_MAX = 50

# ---------------------------------
# HELPERS
# ---------------------------------
def get_allowed_distance(direction, requested_cm):
    """
    Figures out how much of a requested move is safe.
    Returns an integer number of centimeters the drone is allowed to move.
    """

    global current_x, current_y, current_z

    if requested_cm <= 0:
        return 0

    if direction == "forward":
        remaining = Y_MAX - current_y
    elif direction == "back":
        remaining = current_y - Y_MIN
    elif direction == "right":
        remaining = X_MAX - current_x
    elif direction == "left":
        remaining = current_x - X_MIN
    elif direction == "up":
        remaining = Z_MAX - current_z
    elif direction == "down":
        remaining = current_z - Z_MIN
    else:
        return 0

    if remaining <= 0:
        return 0

    return min(requested_cm, remaining)


def update_position(direction, moved_cm):
    """
    Updates the software-tracked position after a successful move.
    """

    global current_x, current_y, current_z

    if direction == "forward":
        current_y += moved_cm
    elif direction == "back":
        current_y -= moved_cm
    elif direction == "right":
        current_x += moved_cm
    elif direction == "left":
        current_x -= moved_cm
    elif direction == "up":
        current_z += moved_cm
    elif direction == "down":
        current_z -= moved_cm


def execute_geofenced_move(direction, requested_cm):
    """
    Applies the geofence, clips the move if needed,
    then sends the allowed move to the drone.
    """

    allowed_cm = get_allowed_distance(direction, requested_cm)

    print(f"Requested: {direction} {requested_cm} cm")

    if allowed_cm == 0:
        print("Blocked by geofence: no movement allowed.")
        print_position()
        return

    # Tello move commands usually require at least ~20 cm
    if allowed_cm < 20:
        print(f"Blocked: only {allowed_cm} cm remained before the boundary, which is too small for a Tello move command.")
        print_position()
        return

    if allowed_cm < requested_cm:
        print(f"Geofence override: clipping move to {allowed_cm} cm")

    if direction == "forward":
        tello.move_forward(allowed_cm)
    elif direction == "back":
        tello.move_back(allowed_cm)
    elif direction == "right":
        tello.move_right(allowed_cm)
    elif direction == "left":
        tello.move_left(allowed_cm)
    elif direction == "up":
        tello.move_up(allowed_cm)
    elif direction == "down":
        tello.move_down(allowed_cm)
    else:
        print("Invalid direction.")
        return

    update_position(direction, allowed_cm)
    print("Move executed.")
    print_position()


def print_position():
    """
    Prints the drone's software-tracked position.
    """
    print(f"Current position -> x={current_x}, y={current_y}, z={current_z}")


# ---------------------------------
# COMMAND LOOP
# ---------------------------------
print("\nDrone ready.")
print("Type commands like:")
print("  forward 30")
print("  back 20")
print("  right 40")
print("  left 25")
print("  up 20")
print("  down 20")
print("Other commands:")
print("  pos")
print("  land")
print("  quit\n")

while True:
    user_input = input("Command: ").strip().lower()

    if user_input == "pos":
        print_position()
        continue

    if user_input == "land":
        print("Landing...")
        tello.land()
        print("Flight complete")
        break

    if user_input == "quit":
        print("Quitting without landing command is unsafe. Landing instead...")
        tello.land()
        print("Flight complete")
        break

    parts = user_input.split()

    if len(parts) != 2:
        print("Invalid format. Use commands like: forward 30")
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

    execute_geofenced_move(direction, distance_cm)