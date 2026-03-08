"""
Configuration and tunable parameters for the flight_ops autonomy stack.

All values are conservative initial placeholders; tune for your environment.
"""

# --- Follow / vision ---
DESIRED_DISTANCE_M = 1.5  # target distance to person (meters)
CONFIDENCE_VISIBLE_THRESHOLD = 0.5   # above this we consider target "visible"
CONFIDENCE_LOST_THRESHOLD = 0.3      # below this we consider target "lost"

# --- Error bucketing (x/y in same units as your CV, e.g. normalized or pixels) ---
X_ERROR_SMALL = 0.1   # within this -> centered
X_ERROR_LARGE = 0.3  # above this -> large
Y_ERROR_SMALL = 0.1
Y_ERROR_LARGE = 0.3

# --- Distance buckets (meters) ---
DISTANCE_NEAR_MAX = 1.0   # distance <= this -> "near"
DISTANCE_FAR_MIN = 2.5    # distance >= this -> "far"; else "good"

# --- Altitude limits (meters) ---
ALTITUDE_LOW_MAX = 0.5    # below -> "low"
ALTITUDE_HIGH_MIN = 3.0   # above -> "high"; else "safe"
ALTITUDE_HARD_MAX = 4.0   # safety: force land above this

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

# --- Follow controller gains (placeholder; tune for your setup) ---
YAW_GAIN = 40
VERTICAL_GAIN = 30
FORWARD_GAIN = 25

# --- Search behavior ---
SEARCH_YAW_SPEED = 20  # slow yaw during search
