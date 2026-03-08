import os
import threading
import cv2
import mediapipe as mp
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple

# Prefer legacy mp.solutions.hands when available (e.g. Windows); otherwise use mp.tasks (e.g. Mac 0.10.30).
_USE_LEGACY = hasattr(mp, "solutions")

if _USE_LEGACY:
    _Hands = mp.solutions.hands.Hands
else:
    # MediaPipe Tasks API: need hand_landmarker.task model
    from mediapipe.tasks.python.vision.core import image as _mp_image
    from mediapipe.tasks.python.vision import hand_landmarker as _hand_landmarker_module

    _HandLandmarker = _hand_landmarker_module.HandLandmarker

    _HAND_MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/latest/hand_landmarker.task"
    )

    def _hand_model_path() -> str:
        path = os.environ.get("MEDIAPIPE_HAND_MODEL")
        if path and os.path.isfile(path):
            return path
        # Prefer project-local cache so it works without ~/.cache write permission
        _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for cache_dir in (
            os.path.join(_project_root, ".mediapipe"),
            os.path.join(
                os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")),
                "mediapipe",
            ),
        ):
            try:
                os.makedirs(cache_dir, exist_ok=True)
                path = os.path.join(cache_dir, "hand_landmarker.task")
                if not os.path.isfile(path):
                    import urllib.request
                    urllib.request.urlretrieve(_HAND_MODEL_URL, path)
                return path
            except (OSError, PermissionError):
                continue
        raise FileNotFoundError(
            "Could not create cache dir for hand_landmarker.task. "
            "Set MEDIAPIPE_HAND_MODEL to a hand_landmarker.task path."
        )


@dataclass
class ThreeDHandData:
    """Structure holding pixel coords, normalized error, and depth.

    Units for each field:
      * ``x_pix``/``y_pix`` – pixels (0..width-1, 0..height-1).
      * ``x_error``/``y_error`` – unitless normalized distance from image
        center; value of 1 corresponds to one half-width/height of the frame.
      * ``distance`` – arbitrary units proportional to inverse hand area (larger
        means closer); scale may be calibrated to real-world units with a
        known reference.
      * ``z_norm`` – MediaPipe's normalized depth; dimensionless and negative
        when hand is in front of the image plane.
      * ``confidence`` – unitless score between 0 and 1.

    The centroid of the detected hand (computed from the bounding box of
    landmarks) is given by ``x_pix``/``y_pix``.  ``x_error`` and ``y_error``
    are the signed distances from the image center along each axis, normalized
    to the range [-1,1] (negative = left/up, positive = right/down).
    """
    x_pix: int           # hand center x coordinate in pixels (origin top-left)
    y_pix: int           # hand center y coordinate in pixels
    x_error: float       # normalized horizontal distance from image center
    y_error: float       # normalized vertical distance from image center
    distance: float       # estimated depth (larger = closer)
    z_norm: float        # raw normalized z from MediaPipe (negative when closer)
    confidence: float     # mediapipe detection/tracking confidence


class DepthHandTracker:
    """Hand tracker that returns 3D information using MediaPipe landmarks.

    Works with both legacy mp.solutions.hands (e.g. Windows) and
    mp.tasks.vision.HandLandmarker (e.g. Mac with mediapipe 0.10.30).

    When non_blocking=True, capture and detection run in a background thread;
    read() returns the latest cached result immediately so your main loop
    (e.g. Tello flight) is not blocked by OpenCV/MediaPipe.
    """

    def __init__(self, camera_id: int = 0, non_blocking: bool = False):
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.frame_w = 640
        self.frame_h = 480
        self.center_x = self.frame_w / 2
        self.center_y = self.frame_h / 2
        self._non_blocking = non_blocking
        self._cache: Tuple[Optional[ThreeDHandData], Optional[np.ndarray]] = (None, None)
        self._cache_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        if _USE_LEGACY:
            self._legacy_hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._tasks_landmarker = None
        else:
            self._legacy_hands = None
            model_path = _hand_model_path()
            self._tasks_landmarker = _HandLandmarker.create_from_model_path(model_path)

        if non_blocking:
            self._thread = threading.Thread(target=self._run_background, daemon=True)
            self._thread.start()

    def _run_background(self) -> None:
        while not self._stop.is_set():
            result = self._read_one()
            with self._cache_lock:
                self._cache = result

    def _read_one(self) -> Tuple[Optional[ThreeDHandData], Optional[np.ndarray]]:
        ret, frame = self.cap.read()
        if not ret:
            return None, None
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if _USE_LEGACY:
            return self._read_legacy(rgb, frame)
        return self._read_tasks(rgb, frame)

    def read(self) -> Tuple[Optional[ThreeDHandData], Optional[np.ndarray]]:
        if self._non_blocking:
            with self._cache_lock:
                return self._cache[0], self._cache[1]
        return self._read_one()

    def _read_legacy(
        self, rgb: np.ndarray, frame: np.ndarray
    ) -> Tuple[Optional[ThreeDHandData], Optional[np.ndarray]]:
        results = self._legacy_hands.process(rgb)
        if results.multi_hand_landmarks:
            lm = results.multi_hand_landmarks[0]
            xs = [int(p.x * self.frame_w) for p in lm.landmark]
            ys = [int(p.y * self.frame_h) for p in lm.landmark]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            cx = (min_x + max_x) / 2
            cy = (min_y + max_y) / 2
            x_err = (cx - self.center_x) / self.center_x
            y_err = (cy - self.center_y) / self.center_y
            z_norm = lm.landmark[0].z
            box_w = max_x - min_x
            box_h = max_y - min_y
            area = box_w * box_h
            distance = 50000.0 / (area + 1)
            confidence = results.multi_handedness[0].classification[0].score
            return (
                ThreeDHandData(int(cx), int(cy), x_err, y_err, distance, z_norm, confidence),
                frame,
            )
        return ThreeDHandData(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0), frame

    def _read_tasks(
        self, rgb: np.ndarray, frame: np.ndarray
    ) -> Tuple[Optional[ThreeDHandData], Optional[np.ndarray]]:
        rgb_contig = np.ascontiguousarray(rgb)
        mp_image = _mp_image.Image(_mp_image.ImageFormat.SRGB, rgb_contig)
        result = self._tasks_landmarker.detect(mp_image)
        if result.hand_landmarks:
            landmarks = result.hand_landmarks[0]
            xs = [int((p.x or 0) * self.frame_w) for p in landmarks]
            ys = [int((p.y or 0) * self.frame_h) for p in landmarks]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            cx = (min_x + max_x) / 2
            cy = (min_y + max_y) / 2
            x_err = (cx - self.center_x) / self.center_x
            y_err = (cy - self.center_y) / self.center_y
            z_norm = landmarks[0].z if landmarks[0].z is not None else 0.0
            box_w = max_x - min_x
            box_h = max_y - min_y
            area = box_w * box_h
            distance = 50000.0 / (area + 1)
            confidence = (
                result.handedness[0][0].score
                if result.handedness and result.handedness[0]
                else 0.5
            )
            return (
                ThreeDHandData(int(cx), int(cy), x_err, y_err, distance, z_norm, confidence),
                frame,
            )
        return ThreeDHandData(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0), frame

    def release(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self.cap.release()
        if self._legacy_hands is not None:
            self._legacy_hands.close()
        if self._tasks_landmarker is not None:
            self._tasks_landmarker.close()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    tracker = DepthHandTracker()
    try:
        while True:
            data, frame = tracker.read()
            if frame is None:
                break
            if data:
                text = (f"pix=({data.x_pix},{data.y_pix}) err=({data.x_error:.2f},{data.y_error:.2f}) "
                        f"dist={data.distance:.1f} z={data.z_norm:.3f} conf={data.confidence:.2f}")
                cv2.putText(frame, text, (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0),2)
            cv2.imshow('3D Hand Tracker (Mac)', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        tracker.release()
