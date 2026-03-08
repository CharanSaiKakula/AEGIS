"""
Configuration and tunable parameters for the flight_ops autonomy stack.

All values are conservative initial placeholders; tune for your environment.
"""

# --- Follow / vision ---
DESIRED_DISTANCE_M = 1.5  # target distance to person (meters)
CONFIDENCE_VISIBLE_THRESHOLD = 0.7   # above this we consider target "visible"

# --- AOO (radial) bucketing: r = sqrt(x_error^2 + y_error^2) ---
AOO_RADIUS_SMALL = 0.1   # r <= this -> "centered"
AOO_RADIUS_LARGE = 0.5   # r <= this -> "moderate"; else "large"

# --- Distance buckets (meters) ---
TARGET_FOLLOW_DISTANCE = 1.5  # meters
DISTANCE_NEAR_MAX = 1.0      # <= this -> "near"
DISTANCE_FAR_MIN = 3.0       # >= this -> "far"

# --- Altitude buckets (meters) ---
ALTITUDE_LOW_MAX = 0.5       # < this -> "low"
ALTITUDE_HIGH_MIN = 1.5      # >= this -> "high"
ALTITUDE_HARD_MAX = 2.0      # safety: land if exceeded

# --- Lost duration buckets (seconds since target last visible) ---
LOST_DURATION_SHORT_MAX = 5.0   # <= this -> "short"
LOST_DURATION_MEDIUM_MAX = 15.0  # <= this -> "medium"; else "long"

# --- Battery ---
BATTERY_LOW_PCT = 30
BATTERY_CRITICAL_PCT = 15

# --- Latency (ms) ---
LATENCY_DEGRADED_MS = 150
LATENCY_CRITICAL_MS = 400

# --- Mission time (optional safety cap, seconds) ---
MISSION_TIME_MAX_S = 600.0  # 10 min placeholder

# --- Command saturation (same scale as send_rc_control, e.g. -100..100) ---
CMD_MAX = 100
CMD_MIN = -100

# --- Follow controller gains  ---
YAW_GAIN = 50
VERTICAL_GAIN = 15
FORWARD_GAIN = 10

# --- Smith predictor (delay compensation) ---
SMITH_TAU_S = 0.20  # prediction horizon (s)
# --- Velocity filter (exponential smoother) ---
VELOCITY_FILTER_ALPHA = 0.3  # α in v = α*v_raw + (1-α)*v_prev

# --- Search behavior ---
SEARCH_YAW_SPEED = 30  # slow yaw during search

# --- Find object (center → follow → land) ---
OPT_DIST_FROM_TARGET = 3.0  # distance to maintain during follow; also the "at distance" threshold for hover (meters)
TARGET_MOTION_STILL_THRESHOLD = 0.02  # |dx|+|dy| below this -> target "still"

# --- AOO (Area of Operation) / geofence: radial in xy (cm) ---
# Reference hover point = (0,0,0). radius = sqrt(x^2 + y^2).
AOO_MOVE_MIN_CM = 20  # Tello needs ~20 cm minimum per move
AOO_RADIUS_MAX_CM = 141  # max radial distance (sqrt(100^2+100^2) for ~100x100 box)

AOO_Z_MIN_CM = AOO_MOVE_MIN_CM
AOO_Z_MAX_CM = 100
