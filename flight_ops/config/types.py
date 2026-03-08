"""
Type definitions for the flight_ops autonomy package.

Enums and dataclasses used across the MDP-inspired person-following stack.
"""

from dataclasses import dataclass
from enum import Enum


class MissionState(Enum):
    """High-level mission behavior state. TAKEOFF is initial; LAND is absorbing."""

    TAKEOFF = "takeoff"
    FOLLOW = "follow"
    SEARCH = "search"
    CENTER = "center"
    HOVER = "hover"
    REACQUIRE = "reacquire"
    LAND = "land"


@dataclass(frozen=True)
class ControlCommand:
    """RC-style command compatible with send_rc_control(lr, fb, ud, yaw)."""

    lr: int   # left-right velocity, typically -100..100
    fb: int   # forward-backward
    ud: int   # up-down
    yaw: int  # yaw rate


@dataclass
class VisionMeasurement:
    """Filtered CV output from the extractor (one tick)."""

    x_error: float   # horizontal error in image/angle space
    y_error: float   # vertical error
    distance: float  # estimated distance to target
    confidence: float  # 0..1 detection confidence


@dataclass
class TelemetrySnapshot:
    """Snapshot of drone/system state for safety and discretization."""

    battery: float       # 0..100
    latency_ms: float   # command round-trip latency
    altitude_m: float   # altitude in meters
    mission_time_s: float  # elapsed mission time
    link_ok: bool = True  # link healthy


@dataclass
class DiscreteState:
    """MDP observation: discretized features for the policy.

    S = (target_visible, aoo_bucket, distance_bucket, confidence_bucket,
         altitude_bucket, latency_bucket, battery_bucket, lost_duration_bucket)
    aoo_bucket: radial distance from center sqrt(x^2 + y^2).
    """

    target_visible: bool
    aoo_bucket: str   # radial: "centered", "moderate", "large" from sqrt(x^2+y^2)
    distance_bucket: str  # e.g. "near", "good", "far"
    motion_bucket: str  # "still" or "moving" from image-space deltas
    at_reasonable_distance: bool  # within tolerance of OPT_DIST_FROM_TARGET
    confidence_bucket: str  # e.g. "lost", "medium", "good"
    altitude_bucket: str   # e.g. "low", "safe", "high"
    latency_bucket: str   # e.g. "nominal", "degraded", "critical"
    battery_bucket: str   # e.g. "normal", "low", "critical"
    lost_duration_bucket: str  # e.g. "short", "medium", "long"
