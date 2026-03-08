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
    HOVER = "hover"
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
    """MDP observation: discretized features for the policy."""

    target_visible: bool
    x_bucket: str       # e.g. "centered", "moderate", "large"
    y_bucket: str
    distance_bucket: str  # e.g. "near", "good", "far"
    confidence_bucket: str  # e.g. "low", "medium", "high"
    altitude_bucket: str   # e.g. "low", "safe", "high"
    latency_bucket: str   # e.g. "nominal", "degraded", "critical"
    battery_bucket: str   # e.g. "normal", "low", "critical"
