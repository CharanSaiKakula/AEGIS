"""
Single-person persistent tracking with:
- initial color lock
- persistent CSRT/KCF tracker after lock (or pose-only on Mac/opencv-python)
- MediaPipe pose refinement + reacquisition
- improved depth estimate using torso width
- optional one-point auto calibration to approximate centimeters

Supports legacy mp.solutions.pose (e.g. Windows) and Tasks API (e.g. Mac 0.10.30+).
On Mac, run: ./install_dev.sh --mac  to install .mediapipe/pose_landmarker_full.task

Controls:
- Press 'q' to quit
- Press 'd' to toggle debug overlay
"""

import os
import cv2
import mediapipe as mp
from dataclasses import dataclass
from typing import Optional, Tuple, Union
import numpy as np
from djitellopy import Tello
import time
import math

# Legacy mp.solutions when available (e.g. Windows); else use Tasks API (e.g. Mac 0.10.30+)
_USE_LEGACY = hasattr(mp, "solutions")

if _USE_LEGACY:
    _PoseLandmark = mp.solutions.pose.PoseLandmark
else:
    from mediapipe.tasks.python.vision.core import image as _mp_image
    from mediapipe.tasks.python.vision import pose_landmarker as _pose_landmarker_module

    _PoseLandmarker = _pose_landmarker_module.PoseLandmarker
    LEFT_HIP_IDX, RIGHT_HIP_IDX = 23, 24
    LEFT_SHOULDER_IDX, RIGHT_SHOULDER_IDX = 11, 12

    def _pose_model_path() -> str:
        path = os.environ.get("MEDIAPIPE_POSE_MODEL")
        if path and os.path.isfile(path):
            return path
        _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(_project_root, ".mediapipe", "pose_landmarker_full.task")
        if os.path.isfile(path):
            return path
        raise FileNotFoundError(
            "pose_landmarker_full.task not found. Run: ./install_dev.sh --mac"
        )


@dataclass
class PoseData:
    detected: bool
    x: int
    y: int
    x_offset: int
    y_offset: int
    normalized_x: float
    normalized_y: float
    confidence: float
    pose_size: float
    depth: float                      # estimated distance; cm if calibrated, otherwise relative
    landmarks_3d: Optional[list]

    bbox: Optional[Tuple[int, int, int, int]] = None
    target_locked: bool = False
    color_found: bool = False
    color_center: Optional[Tuple[int, int]] = None
    color_area: float = 0.0

    torso_width_px: float = 0.0
    depth_is_calibrated: bool = False
    state: str = "SEARCHING_FOR_COLOR"


class PoseTracker3D:
    def __init__(
        self,
        camera_source: Union[int, Tello] = 0,
        target_color: str = "magenta",
        min_color_area: int = 500,
        search_padding: int = 180,
        reacquire_padding: int = 120,
        tracker_refresh_interval: float = 0.75,
        auto_calibrate_depth: bool = True,
        reference_distance_cm: float = 150.0,
        depth_smoothing_alpha: float = 0.25,
    ):
        """
        Args:
            camera_source: webcam index or Tello object
            target_color: 'magenta', 'green', 'cyan', or 'orange'
            min_color_area: minimum contour area for first lock
            search_padding: ROI half-size around color blob for initial pose lock
            reacquire_padding: ROI expansion around last bbox when reacquiring
            tracker_refresh_interval: how often to refresh visual tracker from pose bbox
            auto_calibrate_depth: if True, first successful lock assumes the user is at reference_distance_cm
            reference_distance_cm: used for one-point depth calibration on first lock
            depth_smoothing_alpha: EMA smoothing for depth estimate
        """
        self.is_tello = isinstance(camera_source, Tello)

        if self.is_tello:
            self.tello = camera_source
            self.frame_read = None
        else:
            self.camera = cv2.VideoCapture(camera_source)
            if not self.camera.isOpened():
                raise RuntimeError(f"Could not open camera source {camera_source}")

        # MediaPipe: legacy solutions API or Tasks API (Mac 0.10.30+)
        if _USE_LEGACY:
            self.mp_pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                smooth_landmarks=True,
                enable_segmentation=False,
                smooth_segmentation=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self._tasks_landmarker = None
            self.mp_drawing = mp.solutions.drawing_utils
            self.mp_drawing_styles = mp.solutions.drawing_styles
        else:
            self.mp_pose = None
            from mediapipe.tasks.python import BaseOptions
            from mediapipe.tasks.python.vision import PoseLandmarkerOptions, RunningMode

            model_path = _pose_model_path()
            base_opts = BaseOptions(
                model_asset_path=model_path,
                delegate=BaseOptions.Delegate.CPU,
            )
            options = PoseLandmarkerOptions(
                base_options=base_opts,
                running_mode=RunningMode.IMAGE,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
            )
            self._tasks_landmarker = _PoseLandmarker.create_from_options(options)
            self.mp_drawing = None
            self.mp_drawing_styles = None

        # Lock / tracker state
        self.has_target_lock = False
        self.visual_tracker = None
        self.last_bbox: Optional[Tuple[int, int, int, int]] = None
        self.last_seen_time: float = 0.0
        self.last_tracker_refresh_time: float = 0.0

        # Color-lock state
        self.min_color_area = min_color_area
        self.search_padding = search_padding
        self.reacquire_padding = reacquire_padding
        self.tracker_refresh_interval = tracker_refresh_interval
        self.lower_hsv, self.upper_hsv = self._get_hsv_range(target_color)

        # Depth calibration / smoothing
        self.auto_calibrate_depth = auto_calibrate_depth
        self.reference_distance_cm = reference_distance_cm
        self.depth_scale: Optional[float] = None   # distance_cm * torso_width_px from first lock
        self.depth_smoothing_alpha = depth_smoothing_alpha
        self.smoothed_depth: Optional[float] = None
        self.last_torso_width_px: float = 0.0

    # -------------------------------------------------------------------------
    # Utility helpers
    # -------------------------------------------------------------------------

    def _empty_pose(
        self,
        color_found: bool = False,
        color_center: Optional[Tuple[int, int]] = None,
        color_area: float = 0.0,
        state: str = "SEARCHING_FOR_COLOR",
    ) -> PoseData:
        last_depth = self.smoothed_depth if self.smoothed_depth is not None else 0.0
        return PoseData(
            detected=False,
            x=0,
            y=0,
            x_offset=0,
            y_offset=0,
            normalized_x=0.0,
            normalized_y=0.0,
            confidence=0.0,
            pose_size=0.0,
            depth=last_depth,
            landmarks_3d=None,
            bbox=None,
            target_locked=self.has_target_lock,
            color_found=color_found,
            color_center=color_center,
            color_area=color_area,
            torso_width_px=self.last_torso_width_px,
            depth_is_calibrated=self.depth_scale is not None,
            state=state,
        )

    def _get_hsv_range(self, color_name: str) -> Tuple[np.ndarray, np.ndarray]:
        color_name = color_name.lower()
        ranges = {
            "magenta": (np.array([125, 100, 100]), np.array([170, 255, 255])),
            # "magenta": (np.array([0, 0, 0]), np.array([180, 255, 60])),  # black (low V)
            "green":   (np.array([40, 80, 80]),    np.array([85, 255, 255])),
            "cyan":    (np.array([80, 100, 100]),  np.array([105, 255, 255])),
            "orange":  (np.array([5, 120, 120]),   np.array([20, 255, 255])),
        }
        if color_name not in ranges:
            print(f"Unknown color '{color_name}', defaulting to magenta.")
            color_name = "magenta"
        return ranges[color_name]

    def set_custom_hsv(self, lower_hsv: Tuple[int, int, int], upper_hsv: Tuple[int, int, int]):
        self.lower_hsv = np.array(lower_hsv, dtype=np.uint8)
        self.upper_hsv = np.array(upper_hsv, dtype=np.uint8)

    def _clip_roi(self, x1: int, y1: int, x2: int, y2: int, frame_shape) -> Tuple[int, int, int, int]:
        h, w = frame_shape[:2]
        x1 = max(0, min(w - 1, x1))
        y1 = max(0, min(h - 1, y1))
        x2 = max(1, min(w, x2))
        y2 = max(1, min(h, y2))
        return x1, y1, x2, y2

    def _dist(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        return float(math.hypot(p1[0] - p2[0], p1[1] - p2[1]))

    def _smooth_depth(self, raw_depth: float) -> float:
        if raw_depth <= 0:
            return self.smoothed_depth if self.smoothed_depth is not None else 0.0

        if self.smoothed_depth is None:
            self.smoothed_depth = raw_depth
        else:
            a = self.depth_smoothing_alpha
            self.smoothed_depth = a * raw_depth + (1.0 - a) * self.smoothed_depth
        return self.smoothed_depth

    def _estimate_depth_from_torso(self, torso_width_px: float, allow_calibration: bool = False) -> float:
        """
        Estimate distance from torso width in pixels.
        - If calibrated, returns approx centimeters.
        - Otherwise returns a stable relative estimate.
        """
        if torso_width_px <= 1:
            return self.smoothed_depth if self.smoothed_depth is not None else 0.0

        self.last_torso_width_px = torso_width_px

        # One-point calibration at first strong lock
        if allow_calibration and self.auto_calibrate_depth and self.depth_scale is None:
            self.depth_scale = self.reference_distance_cm * torso_width_px

        if self.depth_scale is not None:
            raw_depth = self.depth_scale / torso_width_px
        else:
            # Relative estimate only
            raw_depth = 1000.0 / torso_width_px

        return self._smooth_depth(raw_depth)

    def _create_tracker(self):
        """
        OpenCV tracker: CSRT/KCF/MOSSE if available. Returns None on opencv-python (no contrib).
        Fall back to pose-only tracking when None.
        """
        candidates = [
            ("legacy", "TrackerCSRT_create"),
            ("legacy", "TrackerKCF_create"),
            ("legacy", "TrackerMOSSE_create"),
            (None, "TrackerCSRT_create"),
            (None, "TrackerKCF_create"),
            (None, "TrackerMOSSE_create"),
        ]
        for attr, name in candidates:
            mod = getattr(cv2, attr, cv2) if attr else cv2
            create_fn = getattr(mod, name, None)
            if create_fn is not None:
                try:
                    return create_fn()
                except Exception:
                    pass
        return None

    def _init_tracker_from_bbox(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]):
        x1, y1, x2, y2 = bbox
        self.visual_tracker = self._create_tracker()
        if self.visual_tracker is not None:
            w = max(1, x2 - x1)
            h = max(1, y2 - y1)
            self.visual_tracker.init(frame, (x1, y1, w, h))
        self.has_target_lock = True
        self.last_bbox = bbox
        self.last_seen_time = time.time()
        self.last_tracker_refresh_time = self.last_seen_time

    def _find_target_color(self, frame: np.ndarray) -> Tuple[Optional[Tuple[int, int]], float]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_hsv, self.upper_hsv)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, 0.0

        largest = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(largest))
        if area < self.min_color_area:
            return None, area

        x, y, w, h = cv2.boundingRect(largest)
        return (x + w // 2, y + h // 2), area

    def _pose_from_bbox(self, frame: np.ndarray, bbox: Tuple[int, int, int, int], state: str) -> PoseData:
        h, w = frame.shape[:2]
        frame_cx = w // 2
        frame_cy = h // 2
        tracker_only = (state == "TRACKER_ONLY")

        x1, y1, x2, y2 = bbox
        orig_w = max(1, x2 - x1)
        orig_h = max(1, y2 - y1)
        orig_area = orig_w * orig_h

        x1, y1, x2, y2 = self._clip_roi(x1, y1, x2, y2, frame.shape)
        px = (x1 + x2) // 2
        py = (y1 + y2) // 2

        x_offset = px - frame_cx
        y_offset = py - frame_cy

        normalized_x = x_offset / frame_cx if frame_cx > 0 else 0.0
        normalized_y = y_offset / frame_cy if frame_cy > 0 else 0.0
        normalized_x = max(-1.0, min(1.0, normalized_x))
        normalized_y = max(-1.0, min(1.0, normalized_y))

        bbox_w = max(1, x2 - x1)
        bbox_h = max(1, y2 - y1)
        pose_size = float(bbox_w * bbox_h)

        clipped_area = bbox_w * bbox_h
        if orig_area > 0 and clipped_area < 0.2 * orig_area:
            return self._empty_pose(state=state)

        if tracker_only:
            return self._empty_pose(state=state)

        torso_width_px = max(1.0, bbox_w * 0.35)
        depth = self._estimate_depth_from_torso(torso_width_px, allow_calibration=False)

        if orig_area > 0:
            conf = 0.75 * (clipped_area / orig_area)
            conf = max(0.0, min(1.0, conf))
        else:
            conf = 0.0

        return PoseData(
            detected=True,
            x=px,
            y=py,
            x_offset=x_offset,
            y_offset=y_offset,
            normalized_x=normalized_x,
            normalized_y=normalized_y,
            confidence=conf,
            pose_size=pose_size,
            depth=depth,
            landmarks_3d=None,
            bbox=(x1, y1, x2, y2),
            target_locked=self.has_target_lock,
            color_found=False,
            color_center=None,
            color_area=0.0,
            torso_width_px=torso_width_px,
            depth_is_calibrated=self.depth_scale is not None,
            state=state,
        )

    def _run_pose_on_roi(
        self,
        frame: np.ndarray,
        roi: Tuple[int, int, int, int],
        color_center: Optional[Tuple[int, int]] = None,
        color_area: float = 0.0,
        allow_depth_calibration: bool = False,
        state: str = "POSE_REFINEMENT",
    ) -> PoseData:
        full_h, full_w = frame.shape[:2]
        frame_center_x = full_w // 2
        frame_center_y = full_h // 2

        x1, y1, x2, y2 = roi
        roi_frame = frame[y1:y2, x1:x2]
        if roi_frame.size == 0:
            return self._empty_pose(
                color_found=color_center is not None,
                color_center=color_center,
                color_area=color_area,
                state=state,
            )

        roi_h, roi_w = roi_frame.shape[:2]
        rgb_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB)

        if _USE_LEGACY:
            results = self.mp_pose.process(rgb_roi)
            if not results.pose_landmarks:
                return self._empty_pose(
                    color_found=color_center is not None,
                    color_center=color_center,
                    color_area=color_area,
                    state=state,
                )
            landmarks = results.pose_landmarks.landmark
            idx_ls = _PoseLandmark.LEFT_SHOULDER.value
            idx_rs = _PoseLandmark.RIGHT_SHOULDER.value
            idx_lh = _PoseLandmark.LEFT_HIP.value
            idx_rh = _PoseLandmark.RIGHT_HIP.value

            def _get_x(lm):
                return lm.x
            def _get_y(lm):
                return lm.y
            key_landmarks = [landmarks[idx_ls], landmarks[idx_rs], landmarks[idx_lh], landmarks[idx_rh]]
            x_coords = [int(lm.x * roi_w) for lm in landmarks]
            y_coords = [int(lm.y * roi_h) for lm in landmarks]
            visibility_vals = [float(getattr(landmarks[i], "visibility", 0.0)) for i in [idx_ls, idx_rs, idx_lh, idx_rh]]
        else:
            rgb_contig = np.ascontiguousarray(rgb_roi)
            mp_image = _mp_image.Image(_mp_image.ImageFormat.SRGB, rgb_contig)
            result = self._tasks_landmarker.detect(mp_image)
            if not result.pose_landmarks:
                return self._empty_pose(
                    color_found=color_center is not None,
                    color_center=color_center,
                    color_area=color_area,
                    state=state,
                )
            landmarks_list = result.pose_landmarks[0]
            idx_ls, idx_rs = LEFT_SHOULDER_IDX, RIGHT_SHOULDER_IDX
            idx_lh, idx_rh = LEFT_HIP_IDX, RIGHT_HIP_IDX

            def _get_x(lm):
                return lm.x or 0
            def _get_y(lm):
                return lm.y or 0
            key_landmarks = [landmarks_list[idx_ls], landmarks_list[idx_rs], landmarks_list[idx_lh], landmarks_list[idx_rh]]
            x_coords = [int((lm.x or 0) * roi_w) for lm in landmarks_list]
            y_coords = [int((lm.y or 0) * roi_h) for lm in landmarks_list]
            visibility_vals = [1.0, 1.0, 1.0, 1.0]

        avg_x = sum(_get_x(lm) for lm in key_landmarks) / len(key_landmarks)
        avg_y = sum(_get_y(lm) for lm in key_landmarks) / len(key_landmarks)

        pixel_x = x1 + int(avg_x * roi_w)
        pixel_y = y1 + int(avg_y * roi_h)

        x_offset = pixel_x - frame_center_x
        y_offset = pixel_y - frame_center_y

        normalized_x = x_offset / frame_center_x if frame_center_x > 0 else 0.0
        normalized_y = y_offset / frame_center_y if frame_center_y > 0 else 0.0
        normalized_x = max(-1.0, min(1.0, normalized_x))
        normalized_y = max(-1.0, min(1.0, normalized_y))

        bbox_x1 = x1 + min(x_coords)
        bbox_y1 = y1 + min(y_coords)
        bbox_x2 = x1 + max(x_coords)
        bbox_y2 = y1 + max(y_coords)
        bbox_x1, bbox_y1, bbox_x2, bbox_y2 = self._clip_roi(
            bbox_x1, bbox_y1, bbox_x2, bbox_y2, frame.shape
        )
        bbox = (bbox_x1, bbox_y1, bbox_x2, bbox_y2)

        bbox_w = max(1, bbox_x2 - bbox_x1)
        bbox_h = max(1, bbox_y2 - bbox_y1)
        pose_size = float(bbox_w * bbox_h)

        confidence = float(np.mean(visibility_vals))

        landmarks_3d = None
        if _USE_LEGACY and hasattr(results, "pose_world_landmarks") and results.pose_world_landmarks:
            landmarks_3d = [(lm.x, lm.y, lm.z) for lm in results.pose_world_landmarks.landmark]
        elif not _USE_LEGACY and hasattr(result, "pose_world_landmarks") and result.pose_world_landmarks:
            wl = result.pose_world_landmarks[0]
            landmarks_3d = [(p.x or 0, p.y or 0, p.z or 0) for p in wl]

        ls = (x1 + int(_get_x(key_landmarks[0]) * roi_w), y1 + int(_get_y(key_landmarks[0]) * roi_h))
        rs = (x1 + int(_get_x(key_landmarks[1]) * roi_w), y1 + int(_get_y(key_landmarks[1]) * roi_h))
        lh = (x1 + int(_get_x(key_landmarks[2]) * roi_w), y1 + int(_get_y(key_landmarks[2]) * roi_h))
        rh = (x1 + int(_get_x(key_landmarks[3]) * roi_w), y1 + int(_get_y(key_landmarks[3]) * roi_h))

        shoulder_width = self._dist(ls, rs)
        hip_width = self._dist(lh, rh)
        torso_candidates = [v for v in [shoulder_width, hip_width] if v > 1.0]
        torso_width_px = float(np.mean(torso_candidates)) if torso_candidates else max(1.0, bbox_w * 0.35)

        depth = self._estimate_depth_from_torso(
            torso_width_px,
            allow_calibration=allow_depth_calibration
        )

        if color_center is not None:
            cx, cy = color_center
            margin = 25
            color_inside_bbox = (
                bbox_x1 - margin <= cx <= bbox_x2 + margin and
                bbox_y1 - margin <= cy <= bbox_y2 + margin
            )
            if not color_inside_bbox:
                return self._empty_pose(
                    color_found=True,
                    color_center=color_center,
                    color_area=color_area,
                    state="COLOR_FOUND_BUT_NOT_ON_PERSON",
                )

        return PoseData(
            detected=True,
            x=pixel_x,
            y=pixel_y,
            x_offset=x_offset,
            y_offset=y_offset,
            normalized_x=normalized_x,
            normalized_y=normalized_y,
            confidence=confidence,
            pose_size=pose_size,
            depth=depth,
            landmarks_3d=landmarks_3d,
            bbox=bbox,
            target_locked=self.has_target_lock,
            color_found=color_center is not None,
            color_center=color_center,
            color_area=color_area,
            torso_width_px=torso_width_px,
            depth_is_calibrated=self.depth_scale is not None,
            state=state,
        )

    # -------------------------------------------------------------------------
    # Main frame acquisition
    # -------------------------------------------------------------------------

    def get_pose_data(self) -> Tuple[Optional[np.ndarray], PoseData]:
        if self.is_tello:
            if self.frame_read is None:
                self.frame_read = self.tello.get_frame_read()
            frame = self.frame_read.frame
            if frame is None:
                return None, self._empty_pose(state="NO_FRAME")
        else:
            ret, frame = self.camera.read()
            if not ret:
                return None, self._empty_pose(state="NO_FRAME")

        frame = cv2.flip(frame, 1)
        pose_data = self._detect_pose(frame)
        return frame, pose_data

    # -------------------------------------------------------------------------
    # Core logic
    # -------------------------------------------------------------------------

    def _detect_pose(self, frame: np.ndarray) -> PoseData:
        now = time.time()
        h, w = frame.shape[:2]

        # ---------------------------------------------------------------------
        # MODE 1a: Locked, no visual tracker (pose-only fallback on Mac/opencv-python)
        # ---------------------------------------------------------------------
        if self.has_target_lock and self.visual_tracker is None:
            if self.last_bbox is not None:
                bx1, by1, bx2, by2 = self.last_bbox
                rx1, ry1, rx2, ry2 = self._clip_roi(
                    bx1 - self.reacquire_padding,
                    by1 - self.reacquire_padding,
                    bx2 + self.reacquire_padding,
                    by2 + self.reacquire_padding,
                    frame.shape
                )
                pose = self._run_pose_on_roi(
                    frame,
                    (rx1, ry1, rx2, ry2),
                    allow_depth_calibration=False,
                    state="TRACKER_LOCKED",
                )
                if pose.detected and pose.bbox is not None:
                    self.last_bbox = pose.bbox
                    self.last_seen_time = now
                    pose.target_locked = True
                    return pose
                return self._pose_from_bbox(frame, self.last_bbox, state="TRACKER_ONLY")
            pose = self._run_pose_on_roi(
                frame,
                (0, 0, w, h),
                allow_depth_calibration=False,
                state="REACQUIRE_FULL_FRAME",
            )
            if pose.detected and pose.bbox is not None:
                self.last_bbox = pose.bbox
                pose.target_locked = True
                return pose
            return self._empty_pose(state="LOST_AFTER_LOCK")

        # ---------------------------------------------------------------------
        # MODE 1b: After first lock, visual tracker available
        # ---------------------------------------------------------------------
        if self.has_target_lock and self.visual_tracker is not None:
            ok, tracked = self.visual_tracker.update(frame)

            if ok:
                x, y, bw, bh = [int(v) for v in tracked]
                bbox = self._clip_roi(x, y, x + bw, y + bh, frame.shape)
                self.last_bbox = bbox
                self.last_seen_time = now

                x1, y1, x2, y2 = bbox
                pad = 50
                rx1, ry1, rx2, ry2 = self._clip_roi(
                    x1 - pad, y1 - pad, x2 + pad, y2 + pad, frame.shape
                )

                pose = self._run_pose_on_roi(
                    frame,
                    (rx1, ry1, rx2, ry2),
                    allow_depth_calibration=False,
                    state="TRACKER_LOCKED",
                )

                if pose.detected and pose.bbox is not None:
                    pose.target_locked = True

                    if (now - self.last_tracker_refresh_time) >= self.tracker_refresh_interval:
                        self._init_tracker_from_bbox(frame, pose.bbox)
                        self.last_tracker_refresh_time = now

                    self.last_bbox = pose.bbox
                    self.last_seen_time = now
                    return pose

                return self._pose_from_bbox(frame, bbox, state="TRACKER_ONLY")

            # Tracker failed -> try local pose reacquisition
            if self.last_bbox is not None:
                bx1, by1, bx2, by2 = self.last_bbox
                rx1, ry1, rx2, ry2 = self._clip_roi(
                    bx1 - self.reacquire_padding,
                    by1 - self.reacquire_padding,
                    bx2 + self.reacquire_padding,
                    by2 + self.reacquire_padding,
                    frame.shape
                )

                pose = self._run_pose_on_roi(
                    frame,
                    (rx1, ry1, rx2, ry2),
                    allow_depth_calibration=False,
                    state="REACQUIRE_LOCAL",
                )
                if pose.detected and pose.bbox is not None:
                    self._init_tracker_from_bbox(frame, pose.bbox)
                    pose.target_locked = True
                    return pose

            pose = self._run_pose_on_roi(
                frame,
                (0, 0, w, h),
                allow_depth_calibration=False,
                state="REACQUIRE_FULL_FRAME",
            )
            if pose.detected and pose.bbox is not None:
                self._init_tracker_from_bbox(frame, pose.bbox)
                pose.target_locked = True
                return pose

            return self._empty_pose(state="LOST_AFTER_LOCK")

        # ---------------------------------------------------------------------
        # MODE 2: Before first lock, require target color
        # ---------------------------------------------------------------------
        color_center, color_area = self._find_target_color(frame)

        if color_center is not None:
            cx, cy = color_center
            x1, y1, x2, y2 = self._clip_roi(
                cx - self.search_padding,
                cy - self.search_padding,
                cx + self.search_padding,
                cy + self.search_padding,
                frame.shape
            )

            pose = self._run_pose_on_roi(
                frame,
                (x1, y1, x2, y2),
                color_center=color_center,
                color_area=color_area,
                allow_depth_calibration=True,
                state="FIRST_LOCK_FROM_COLOR",
            )

            if pose.detected and pose.bbox is not None:
                self._init_tracker_from_bbox(frame, pose.bbox)
                pose.target_locked = True
                pose.state = "LOCKED"
                return pose

            return self._empty_pose(
                color_found=True,
                color_center=color_center,
                color_area=color_area,
                state="COLOR_FOUND_SEARCHING_PERSON",
            )

        return self._empty_pose(state="SEARCHING_FOR_COLOR")

    # -------------------------------------------------------------------------
    # Debug drawing
    # -------------------------------------------------------------------------

    def draw_debug(self, frame: np.ndarray, pose_data: PoseData) -> Optional[np.ndarray]:
        if frame is None:
            return None

        h, w = frame.shape[:2]
        center_x = w // 2
        center_y = h // 2

        cv2.line(frame, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 0), 2)
        cv2.line(frame, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 0), 2)

        if pose_data.color_found and pose_data.color_center is not None:
            cx, cy = pose_data.color_center
            cv2.circle(frame, (cx, cy), 10, (255, 0, 255), -1)
            cv2.putText(frame, "COLOR", (cx + 10, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)

        if pose_data.bbox is not None:
            x1, y1, x2, y2 = pose_data.bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)

        if pose_data.detected:
            cv2.circle(frame, (pose_data.x, pose_data.y), 8, (0, 255, 0), -1)
            cv2.line(frame, (center_x, center_y), (pose_data.x, pose_data.y), (255, 0, 0), 2)

        depth_label = "cm" if pose_data.depth_is_calibrated else "rel"
        info_lines = [
            f"State: {pose_data.state}",
            f"Detected: {pose_data.detected}",
            f"Target Locked: {pose_data.target_locked}",
            f"Color Found: {pose_data.color_found}",
            f"Color Area: {pose_data.color_area:.1f}",
            f"Center: ({pose_data.x}, {pose_data.y})",
            f"Offset: ({pose_data.x_offset}, {pose_data.y_offset})",
            f"Normalized: ({pose_data.normalized_x:.2f}, {pose_data.normalized_y:.2f})",
            f"Confidence: {pose_data.confidence:.2f}",
            f"Torso Width px: {pose_data.torso_width_px:.1f}",
            f"Depth: {pose_data.depth:.1f} {depth_label}",
            f"Calibrated: {pose_data.depth_is_calibrated}",
        ]

        for i, text in enumerate(info_lines):
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1)
            y_top = 10 + i * 24
            cv2.rectangle(frame, (10, y_top), (10 + tw + 8, y_top + th + 8), (0, 0, 0), -1)
            cv2.putText(frame, text, (14, y_top + th + 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)

        return frame

    def release(self):
        if not self.is_tello and hasattr(self, "camera"):
            self.camera.release()
        if _USE_LEGACY and self.mp_pose is not None:
            self.mp_pose.close()
        if not _USE_LEGACY and getattr(self, "_tasks_landmarker", None) is not None:
            self._tasks_landmarker.close()


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def test_webcam():
    print("Testing persistent single-person tracking with webcam...")
    print("Press 'q' to quit, 'd' to toggle debug drawing")
    print("For first lock: show the target color (default magenta) near your chest.")
    print("If auto calibration is on, stand roughly at the known reference distance during first lock.")

    tracker = PoseTracker3D(
        camera_source=0,
        target_color="magenta",
        auto_calibrate_depth=True,
        reference_distance_cm=150.0,
    )

    debug_mode = True
    frame_count = 0

    try:
        while True:
            frame, pose_data = tracker.get_pose_data()

            if frame is not None:
                display = tracker.draw_debug(frame.copy(), pose_data) if debug_mode else frame
                cv2.imshow("Persistent Single-Person Tracking", display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                debug_mode = not debug_mode
                print(f"Debug mode: {'ON' if debug_mode else 'OFF'}")

            frame_count += 1
            if frame_count % 30 == 0:
                depth_label = "cm" if pose_data.depth_is_calibrated else "rel"
                print(
                    f"[{frame_count}] state={pose_data.state} | "
                    f"locked={pose_data.target_locked} | "
                    f"detected={pose_data.detected} | "
                    f"depth={pose_data.depth:.1f} {depth_label}"
                )

    except KeyboardInterrupt:
        print("Interrupted by user")

    finally:
        tracker.release()
        cv2.destroyAllWindows()
        print("Webcam test complete.")


def test_tello():
    print("Testing persistent single-person tracking with Tello...")
    print("Press 'q' to quit, 'd' to toggle debug drawing")
    print("For first lock: show the target color (default magenta) near your chest.")
    print("If auto calibration is on, stand roughly at the known reference distance during first lock.")

    tello = Tello()
    tracker = None

    try:
        print("Connecting to Tello...")
        tello.connect()
        print(f"Battery: {tello.get_battery()}%")

        print("Starting video stream...")
        tello.streamon()
        time.sleep(2)

        tello.takeoff()
        time.sleep(1)
        tello.move_up(60)
        time.sleep(1)

        tracker = PoseTracker3D(
            camera_source=tello,
            target_color="magenta",
            auto_calibrate_depth=True,
            reference_distance_cm=150.0,
        )

        debug_mode = True
        frame_count = 0

        print("Tracking active. Show the color once to lock.")

        while True:
            frame, pose_data = tracker.get_pose_data()

            if frame is not None:
                display = tracker.draw_debug(frame.copy(), pose_data) if debug_mode else frame
                cv2.imshow("Tello Persistent Single-Person Tracking", display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                debug_mode = not debug_mode
                print(f"Debug mode: {'ON' if debug_mode else 'OFF'}")

            frame_count += 1
            if frame_count % 30 == 0:
                depth_label = "cm" if pose_data.depth_is_calibrated else "rel"
                print(
                    f"[{frame_count}] state={pose_data.state} | "
                    f"locked={pose_data.target_locked} | "
                    f"detected={pose_data.detected} | "
                    f"depth={pose_data.depth:.1f} {depth_label}"
                )

    except KeyboardInterrupt:
        print("Interrupted by user")

    finally:
        print("Cleaning up...")
        try:
            tello.land()
        except:
            pass
        try:
            tello.streamoff()
        except:
            pass
        try:
            tello.end()
        except:
            pass
        if tracker is not None:
            tracker.release()
        cv2.destroyAllWindows()
        print("Tello test complete.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1].lower() == "webcam":
        test_webcam()
    else:
        test_tello()
