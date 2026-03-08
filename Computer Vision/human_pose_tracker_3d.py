import cv2
import mediapipe as mp
import numpy as np
import time
import math
from dataclasses import dataclass
from typing import Optional, Tuple, Union
from djitellopy import Tello


@dataclass
class TrackData:
    detected: bool = False
    locked: bool = False
    state: str = "SEARCHING"

    x: int = 0
    y: int = 0
    norm_x: float = 0.0
    norm_y: float = 0.0

    bbox: Optional[Tuple[int, int, int, int]] = None
    confidence: float = 0.0

    depth: float = 0.0              # cm if calibrated, relative otherwise
    scale_px: float = 0.0           # body scale used for depth
    depth_calibrated: bool = False

    color_found: bool = False
    color_center: Optional[Tuple[int, int]] = None
    color_area: float = 0.0


class SinglePersonTracker:
    def __init__(
        self,
        source: Union[int, Tello] = 0,
        target_color: str = "magenta",
        min_color_area: int = 120,
        search_pad: int = 180,
        reacquire_pad: int = 120,
        refresh_sec: float = 0.75,
        reference_distance_cm: float = 150.0,
        auto_calibrate: bool = True,
        depth_alpha: float = 0.25,
    ):
        self.is_tello = isinstance(source, Tello)
        self.tello = source if self.is_tello else None
        self.frame_read = None

        if not self.is_tello:
            self.cap = cv2.VideoCapture(source)
            if not self.cap.isOpened():
                raise RuntimeError(f"Could not open camera source {source}")

        self.pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self.min_color_area = min_color_area
        self.search_pad = search_pad
        self.reacquire_pad = reacquire_pad
        self.refresh_sec = refresh_sec
        self.lower_hsv, self.upper_hsv = self._hsv_range(target_color)

        self.locked = False
        self.tracker = None
        self.last_bbox = None
        self.last_refresh = 0.0

        self.reference_distance_cm = reference_distance_cm
        self.auto_calibrate = auto_calibrate
        self.depth_scale = None      # reference_distance_cm * body_scale_px
        self.depth_alpha = depth_alpha
        self.smooth_depth = None

    # ---------- basic helpers ----------

    def _hsv_range(self, name: str):
        presets = {
            "magenta": (np.array([120, 70, 70]), np.array([175, 255, 255])),
            "green":   (np.array([40, 80, 80]),  np.array([85, 255, 255])),
            "cyan":    (np.array([80, 90, 90]),  np.array([105, 255, 255])),
            "orange":  (np.array([5, 120, 120]), np.array([20, 255, 255])),
        }
        return presets.get(name.lower(), presets["magenta"])

    def set_custom_hsv(self, lower, upper):
        self.lower_hsv = np.array(lower, dtype=np.uint8)
        self.upper_hsv = np.array(upper, dtype=np.uint8)

    def _clip(self, x1, y1, x2, y2, shape):
        h, w = shape[:2]
        return (
            max(0, min(w - 1, x1)),
            max(0, min(h - 1, y1)),
            max(1, min(w, x2)),
            max(1, min(h, y2)),
        )

    def _dist(self, a, b):
        return float(math.hypot(a[0] - b[0], a[1] - b[1]))

    def _smooth(self, value: float) -> float:
        if value <= 0:
            return self.smooth_depth if self.smooth_depth is not None else 0.0
        if self.smooth_depth is None:
            self.smooth_depth = value
        else:
            a = self.depth_alpha
            self.smooth_depth = a * value + (1 - a) * self.smooth_depth
        return self.smooth_depth

    def _depth_from_scale(self, body_scale_px: float, allow_calibration=False) -> float:
        if body_scale_px <= 1:
            return self.smooth_depth if self.smooth_depth is not None else 0.0

        if allow_calibration and self.auto_calibrate and self.depth_scale is None:
            self.depth_scale = self.reference_distance_cm * body_scale_px

        raw = (self.depth_scale / body_scale_px) if self.depth_scale else (1000.0 / body_scale_px)
        return self._smooth(raw)

    def _tracker_factory(self):
        if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerCSRT_create"):
            return cv2.legacy.TrackerCSRT_create()
        if hasattr(cv2, "TrackerCSRT_create"):
            return cv2.TrackerCSRT_create()
        if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerKCF_create"):
            return cv2.legacy.TrackerKCF_create()
        if hasattr(cv2, "TrackerKCF_create"):
            return cv2.TrackerKCF_create()
        raise RuntimeError("No CSRT/KCF tracker found in this OpenCV build.")

    def _init_tracker(self, frame, bbox):
        x1, y1, x2, y2 = bbox
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        self.tracker = self._tracker_factory()
        self.tracker.init(frame, (x1, y1, w, h))
        self.locked = True
        self.last_bbox = bbox
        self.last_refresh = time.time()

    # ---------- frame + color ----------

    def _get_frame(self):
        if self.is_tello:
            if self.frame_read is None:
                self.frame_read = self.tello.get_frame_read()
            frame = self.frame_read.frame
            if frame is None:
                return None
        else:
            ok, frame = self.cap.read()
            if not ok:
                return None
        return cv2.flip(frame, 1)

    def _find_color(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_hsv, self.upper_hsv)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, 0.0

        c = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(c))
        if area < self.min_color_area:
            return None, area

        x, y, w, h = cv2.boundingRect(c)
        return (x + w // 2, y + h // 2), area

    # ---------- pose logic ----------

    def _state_from_bbox(self, frame, bbox, state="TRACKER_ONLY"):
        h, w = frame.shape[:2]
        cx_frame, cy_frame = w // 2, h // 2
        x1, y1, x2, y2 = self._clip(*bbox, frame.shape)

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)

        # fallback scale from height, not width
        body_scale_px = max(1.0, bh * 0.45)
        depth = self._depth_from_scale(body_scale_px, allow_calibration=False)

        return TrackData(
            detected=True,
            locked=self.locked,
            state=state,
            x=cx,
            y=cy,
            norm_x=max(-1.0, min(1.0, (cx - cx_frame) / max(1, cx_frame))),
            norm_y=max(-1.0, min(1.0, (cy - cy_frame) / max(1, cy_frame))),
            bbox=(x1, y1, x2, y2),
            confidence=0.75,
            depth=depth,
            scale_px=body_scale_px,
            depth_calibrated=self.depth_scale is not None,
        )

    def _pose_in_roi(self, frame, roi, color_center=None, color_area=0.0, calibrate=False, state="POSE"):
        H, W = frame.shape[:2]
        frame_cx, frame_cy = W // 2, H // 2

        x1, y1, x2, y2 = roi
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return TrackData(state=state, locked=self.locked, color_found=color_center is not None,
                             color_center=color_center, color_area=color_area)

        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        res = self.pose.process(rgb)
        if not res.pose_landmarks:
            return TrackData(state=state, locked=self.locked, color_found=color_center is not None,
                             color_center=color_center, color_area=color_area)

        lm = res.pose_landmarks.landmark
        P = mp.solutions.pose.PoseLandmark

        idx_ls, idx_rs = P.LEFT_SHOULDER.value, P.RIGHT_SHOULDER.value
        idx_lh, idx_rh = P.LEFT_HIP.value, P.RIGHT_HIP.value

        pts = [(int(p.x * (x2 - x1)) + x1, int(p.y * (y2 - y1)) + y1) for p in lm]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bbox = self._clip(min(xs), min(ys), max(xs), max(ys), frame.shape)

        ls, rs, lh, rh = pts[idx_ls], pts[idx_rs], pts[idx_lh], pts[idx_rh]

        shoulder_mid = ((ls[0] + rs[0]) // 2, (ls[1] + rs[1]) // 2)
        hip_mid = ((lh[0] + rh[0]) // 2, (lh[1] + rh[1]) // 2)

        shoulder_width = self._dist(ls, rs)
        torso_height = self._dist(shoulder_mid, hip_mid)

        # Rotation-robust body scale:
        # height dominates, width only helps a bit when frontal
        if torso_height <= 1.0:
            torso_height = max(1.0, (bbox[3] - bbox[1]) * 0.45)

        frontal_ratio = shoulder_width / max(torso_height, 1.0)
        if frontal_ratio > 0.6:
            body_scale_px = 0.75 * torso_height + 0.25 * shoulder_width
        else:
            body_scale_px = torso_height

        depth = self._depth_from_scale(body_scale_px, allow_calibration=calibrate)

        center_x = int((ls[0] + rs[0] + lh[0] + rh[0]) / 4)
        center_y = int((ls[1] + rs[1] + lh[1] + rh[1]) / 4)

        vis = []
        for i in [idx_ls, idx_rs, idx_lh, idx_rh]:
            vis.append(float(getattr(lm[i], "visibility", 0.0)))
        confidence = float(np.mean(vis))

        if color_center is not None:
            cx, cy = color_center
            bx1, by1, bx2, by2 = bbox
            margin = 25
            inside = (bx1 - margin <= cx <= bx2 + margin) and (by1 - margin <= cy <= by2 + margin)
            if not inside:
                return TrackData(
                    state="COLOR_NOT_ON_PERSON",
                    locked=self.locked,
                    color_found=True,
                    color_center=color_center,
                    color_area=color_area,
                )

        return TrackData(
            detected=True,
            locked=self.locked,
            state=state,
            x=center_x,
            y=center_y,
            norm_x=max(-1.0, min(1.0, (center_x - frame_cx) / max(1, frame_cx))),
            norm_y=max(-1.0, min(1.0, (center_y - frame_cy) / max(1, frame_cy))),
            bbox=bbox,
            confidence=confidence,
            depth=depth,
            scale_px=body_scale_px,
            depth_calibrated=self.depth_scale is not None,
            color_found=color_center is not None,
            color_center=color_center,
            color_area=color_area,
        )

    # ---------- main update ----------

    def update(self):
        frame = self._get_frame()
        if frame is None:
            return None, TrackData(state="NO_FRAME", locked=self.locked)

        now = time.time()
        h, w = frame.shape[:2]

        # After first lock, ignore color forever
        if self.locked and self.tracker is not None:
            ok, tracked = self.tracker.update(frame)

            if ok:
                x, y, bw, bh = [int(v) for v in tracked]
                bbox = self._clip(x, y, x + bw, y + bh, frame.shape)
                self.last_bbox = bbox

                x1, y1, x2, y2 = bbox
                roi = self._clip(x1 - 50, y1 - 50, x2 + 50, y2 + 50, frame.shape)
                data = self._pose_in_roi(frame, roi, calibrate=False, state="TRACKING")

                if data.detected and data.bbox is not None:
                    data.locked = True
                    self.last_bbox = data.bbox

                    if now - self.last_refresh >= self.refresh_sec:
                        self._init_tracker(frame, data.bbox)
                        self.last_refresh = now
                    return frame, data

                return frame, self._state_from_bbox(frame, bbox, state="TRACKER_ONLY")

            # local reacquire near last bbox
            if self.last_bbox is not None:
                x1, y1, x2, y2 = self.last_bbox
                roi = self._clip(x1 - self.reacquire_pad, y1 - self.reacquire_pad,
                                 x2 + self.reacquire_pad, y2 + self.reacquire_pad, frame.shape)
                data = self._pose_in_roi(frame, roi, calibrate=False, state="REACQUIRE_LOCAL")
                if data.detected and data.bbox is not None:
                    self._init_tracker(frame, data.bbox)
                    data.locked = True
                    return frame, data

            # full frame fallback because you only care about one person
            data = self._pose_in_roi(frame, (0, 0, w, h), calibrate=False, state="REACQUIRE_FULL")
            if data.detected and data.bbox is not None:
                self._init_tracker(frame, data.bbox)
                data.locked = True
                return frame, data

            return frame, TrackData(state="LOST", locked=True, depth=self.smooth_depth or 0.0,
                                    depth_calibrated=self.depth_scale is not None)

        # Before first lock, require color
        color_center, color_area = self._find_color(frame)
        if color_center is not None:
            cx, cy = color_center
            roi = self._clip(cx - self.search_pad, cy - self.search_pad,
                             cx + self.search_pad, cy + self.search_pad, frame.shape)
            data = self._pose_in_roi(
                frame,
                roi,
                color_center=color_center,
                color_area=color_area,
                calibrate=True,
                state="LOCKING",
            )
            if data.detected and data.bbox is not None:
                self._init_tracker(frame, data.bbox)
                data.locked = True
                data.state = "LOCKED"
                return frame, data

            return frame, TrackData(
                state="COLOR_FOUND",
                locked=False,
                color_found=True,
                color_center=color_center,
                color_area=color_area,
                depth=self.smooth_depth or 0.0,
                depth_calibrated=self.depth_scale is not None,
            )

        return frame, TrackData(
            state="SEARCHING",
            locked=False,
            depth=self.smooth_depth or 0.0,
            depth_calibrated=self.depth_scale is not None,
        )

    # ---------- drawing / cleanup ----------

    def draw(self, frame, data: TrackData):
        if frame is None:
            return None

        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        cv2.line(frame, (cx - 20, cy), (cx + 20, cy), (0, 255, 0), 2)
        cv2.line(frame, (cx, cy - 20), (cx, cy + 20), (0, 255, 0), 2)

        if data.color_found and data.color_center is not None:
            x, y = data.color_center
            cv2.circle(frame, (x, y), 8, (255, 0, 255), -1)
            cv2.putText(frame, "COLOR", (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 255), 2)

        if data.bbox is not None:
            x1, y1, x2, y2 = data.bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)

        if data.detected:
            cv2.circle(frame, (data.x, data.y), 7, (0, 255, 0), -1)
            cv2.line(frame, (cx, cy), (data.x, data.y), (255, 0, 0), 2)

        unit = "cm" if data.depth_calibrated else "rel"
        lines = [
            f"State: {data.state}",
            f"Locked: {data.locked}",
            f"Detected: {data.detected}",
            f"Color: {data.color_found} area={data.color_area:.1f}",
            f"Center: ({data.x}, {data.y})",
            f"Norm: ({data.norm_x:.2f}, {data.norm_y:.2f})",
            f"Conf: {data.confidence:.2f}",
            f"Scale: {data.scale_px:.1f}px",
            f"Depth: {data.depth:.1f} {unit}",
        ]

        for i, line in enumerate(lines):
            (tw, th), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            y0 = 10 + i * 24
            cv2.rectangle(frame, (10, y0), (18 + tw, y0 + th + 8), (0, 0, 0), -1)
            cv2.putText(frame, line, (14, y0 + th + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame

    def release(self):
        if not self.is_tello and hasattr(self, "cap"):
            self.cap.release()


def run_demo(use_tello=True):
    tracker = None
    tello = None
    debug = True
    frame_count = 0

    try:
        if use_tello:
            tello = Tello()
            print("Connecting to Tello...")
            tello.connect()
            print(f"Battery: {tello.get_battery()}%")
            tello.streamon()
            time.sleep(2)
            tello.takeoff()
            time.sleep(1)
            tello.move_up(60)
            time.sleep(1)

            tracker = SinglePersonTracker(
                source=tello,
                target_color="magenta",
                min_color_area=120,
                reference_distance_cm=150.0,
            )
        else:
            tracker = SinglePersonTracker(
                source=0,
                target_color="magenta",
                min_color_area=120,
                reference_distance_cm=150.0,
            )

        print("Press q to quit, d to toggle debug.")
        print("Show the color once near your chest to get the first lock.")

        while True:
            frame, data = tracker.update()
            if frame is not None:
                show = tracker.draw(frame.copy(), data) if debug else frame
                cv2.imshow("Single Person Tracker", show)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("d"):
                debug = not debug

            frame_count += 1
            if frame_count % 30 == 0:
                unit = "cm" if data.depth_calibrated else "rel"
                print(
                    f"[{frame_count}] state={data.state} "
                    f"locked={data.locked} detected={data.detected} "
                    f"depth={data.depth:.1f} {unit}"
                )

    finally:
        if tello is not None:
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


if __name__ == "__main__":
    import sys
    use_tello = not (len(sys.argv) > 1 and sys.argv[1].lower() == "webcam")
    run_demo(use_tello=use_tello)