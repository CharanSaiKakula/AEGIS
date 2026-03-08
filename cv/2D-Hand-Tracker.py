import os

import cv2
import mediapipe as mp
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple

from djitellopy import Tello

# Support both legacy mp.solutions (e.g. Windows) and mp.tasks (e.g. Mac 0.10.30+)
_USE_LEGACY = hasattr(mp, "solutions")

if not _USE_LEGACY:
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
        _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for cache_dir in (
            os.path.join(_project_root, ".mediapipe"),
            os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "mediapipe"),
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
class HandData:
    """Data structure to hold all information about detected hand/palm"""
    detected: bool  # True if a hand is detected, False otherwise
    x: int  # X-coordinate of palm center in pixels (0 to frame width)
    y: int  # Y-coordinate of palm center in pixels (0 to frame height)
    x_offset: int  # Horizontal distance from frame center (negative = left, positive = right)
    y_offset: int  # Vertical distance from frame center (negative = up, positive = down)
    normalized_x: float  # X position normalized to -1 (left) to 1 (right), 0 = center
    normalized_y: float  # Y position normalized to -1 (up) to 1 (down), 0 = center
    confidence: float  # Confidence score from MediaPipe (0.0 to 1.0)
    hand_size: float  # Approximate palm area in pixels (width * height of bounding box)


class HandTracker:
    def __init__(self, camera_source=None):
        """
        Initialize hand tracker with either webcam or Tello.
        
        Args:
            camera_source: None for webcam, or Tello object for drone
        """
        self.is_tello = camera_source is not None
        
        if self.is_tello:
            # Use Tello's frame reader
            self.frame_read = camera_source.get_frame_read()
        else:
            # Use webcam
            self.camera = cv2.VideoCapture(0)
        
        # Set frame properties
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640) if not self.is_tello else None
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480) if not self.is_tello else None
        self.camera.set(cv2.CAP_PROP_FPS, 30) if not self.is_tello else None

        # Initialize MediaPipe (legacy or Tasks API)
        if _USE_LEGACY:
            self._legacy_hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._mp_drawing = mp.solutions.drawing_utils
            self._tasks_landmarker = None
        else:
            self._legacy_hands = None
            self._mp_drawing = None
            model_path = _hand_model_path()
            self._tasks_landmarker = _HandLandmarker.create_from_model_path(model_path)

        # Frame dimensions
        self.frame_width = 640
        self.frame_height = 480
        self.center_x = self.frame_width // 2
        self.center_y = self.frame_height // 2  

    def get_hand_data(self) -> Tuple[Optional[np.ndarray], HandData]:
        """
        Capture a frame from the camera/Tello and detect hand/palm.

        Returns:
            A tuple containing:
            - frame: The captured image (BGR format), or None if capture failed
            - hand_data: HandData object with detection results
        """
        # Read frame from appropriate source
        if self.is_tello:
            frame = self.frame_read.frame
            if frame is None:
                return None, HandData(
                    detected=False, x=0, y=0, x_offset=0, y_offset=0,
                    normalized_x=0.0, normalized_y=0.0, confidence=0.0, hand_size=0.0
                )
        else:
            ret, frame = self.camera.read()
            if not ret:
                return None, HandData(
                    detected=False, x=0, y=0, x_offset=0, y_offset=0,
                    normalized_x=0.0, normalized_y=0.0, confidence=0.0, hand_size=0.0
                )

        # Flip the frame horizontally to create a mirror effect (selfie view)
        frame = cv2.flip(frame, 1) #check if needed for tello stream

        # Process the frame for hand detection
        hand_data = self._detect_hand(frame)

        return frame, hand_data

    def _detect_hand(self, frame: np.ndarray) -> HandData:
        """Process frame and extract hand data via MediaPipe (legacy or Tasks API)."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if _USE_LEGACY:
            return self._detect_legacy(rgb_frame)
        return self._detect_tasks(rgb_frame)

    def _detect_legacy(self, rgb_frame: np.ndarray) -> HandData:
        results = self._legacy_hands.process(rgb_frame)
        if not results.multi_hand_landmarks:
            return HandData(
                detected=False, x=0, y=0, x_offset=0, y_offset=0,
                normalized_x=0.0, normalized_y=0.0, confidence=0.0, hand_size=0.0,
            )
        lm = results.multi_hand_landmarks[0]
        return self._landmarks_to_hand_data(
            lm.landmark,
            results.multi_handedness[0].classification[0].score if results.multi_handedness else 1.0,
        )

    def _detect_tasks(self, rgb_frame: np.ndarray) -> HandData:
        rgb_contig = np.ascontiguousarray(rgb_frame)
        mp_image = _mp_image.Image(_mp_image.ImageFormat.SRGB, rgb_contig)
        result = self._tasks_landmarker.detect(mp_image)
        if not result.hand_landmarks:
            return HandData(
                detected=False, x=0, y=0, x_offset=0, y_offset=0,
                normalized_x=0.0, normalized_y=0.0, confidence=0.0, hand_size=0.0,
            )
        landmarks = result.hand_landmarks[0]
        confidence = (
            result.handedness[0][0].score
            if result.handedness and result.handedness[0]
            else 0.5
        )
        # Tasks API uses NormalizedLandmark; convert to (x,y) tuples
        palm_points = [
            (landmarks[0].x or 0, landmarks[0].y or 0),
            (landmarks[5].x or 0, landmarks[5].y or 0),
            (landmarks[9].x or 0, landmarks[9].y or 0),
            (landmarks[13].x or 0, landmarks[13].y or 0),
            (landmarks[17].x or 0, landmarks[17].y or 0),
        ]
        xs = [p[0] for p in palm_points]
        ys = [p[1] for p in palm_points]
        avg_x = sum(xs) / len(xs)
        avg_y = sum(ys) / len(ys)
        pixel_x = int(avg_x * self.frame_width)
        pixel_y = int(avg_y * self.frame_height)
        x_offset = pixel_x - self.center_x
        y_offset = pixel_y - self.center_y
        normalized_x = max(-1.0, min(1.0, x_offset / self.center_x))
        normalized_y = max(-1.0, min(1.0, y_offset / self.center_y))
        x_coords = [int((p.x or 0) * self.frame_width) for p in landmarks]
        y_coords = [int((p.y or 0) * self.frame_height) for p in landmarks]
        width = max(x_coords) - min(x_coords)
        height = max(y_coords) - min(y_coords)
        hand_size = float(width * height)
        return HandData(
            detected=True,
            x=pixel_x, y=pixel_y,
            x_offset=x_offset, y_offset=y_offset,
            normalized_x=normalized_x, normalized_y=normalized_y,
            confidence=confidence,
            hand_size=hand_size,
        )

    def _landmarks_to_hand_data(self, landmarks, confidence: float) -> HandData:
        """Convert legacy landmark list to HandData."""
        palm_indices = [0, 5, 9, 13, 17]
        avg_x = sum(landmarks[i].x for i in palm_indices) / len(palm_indices)
        avg_y = sum(landmarks[i].y for i in palm_indices) / len(palm_indices)
        pixel_x = int(avg_x * self.frame_width)
        pixel_y = int(avg_y * self.frame_height)
        x_offset = pixel_x - self.center_x
        y_offset = pixel_y - self.center_y
        normalized_x = max(-1.0, min(1.0, x_offset / self.center_x))
        normalized_y = max(-1.0, min(1.0, y_offset / self.center_y))
        x_coords = [int(lm.x * self.frame_width) for lm in landmarks]
        y_coords = [int(lm.y * self.frame_height) for lm in landmarks]
        width = max(x_coords) - min(x_coords)
        height = max(y_coords) - min(y_coords)
        hand_size = float(width * height)
        return HandData(
            detected=True,
            x=pixel_x, y=pixel_y,
            x_offset=x_offset, y_offset=y_offset,
            normalized_x=normalized_x, normalized_y=normalized_y,
            confidence=confidence,
            hand_size=hand_size,
        )

    def draw_debug_info(self, frame: np.ndarray, hand_data: HandData) -> np.ndarray:
        """
        Draw visual debugging information on the frame, including landmarks and data.

        Args:
            frame: Input image to draw on
            hand_data: Current hand detection data

        Returns:
            Modified frame with debug drawings
        """
        if frame is None:
            return None

        # Draw center crosshair for reference
        cv2.line(frame, (self.center_x - 20, self.center_y), (self.center_x + 20, self.center_y), (0, 255, 0), 2)
        cv2.line(frame, (self.center_x, self.center_y - 20), (self.center_x, self.center_y + 20), (0, 255, 0), 2)

        # Draw MediaPipe hand landmarks (legacy only; Tasks API skips landmark viz)
        if _USE_LEGACY:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._legacy_hands.process(rgb_frame)
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self._mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS
                    )

        # Draw palm position and data if hand is detected
        if hand_data.detected:
            # Green circle at palm center
            cv2.circle(frame, (hand_data.x, hand_data.y), 10, (0, 255, 0), -1)

            # Blue line from center to palm
            cv2.line(frame, (self.center_x, self.center_y), (hand_data.x, hand_data.y), (255, 0, 0), 2)

            # Text information overlay
            info_lines = [
                f"Hand Detected: {hand_data.detected}",
                f"Palm Position: ({hand_data.x}, {hand_data.y})",
                f"Offset: ({hand_data.x_offset}, {hand_data.y_offset})",
                f"Normalized: ({hand_data.normalized_x:.2f}, {hand_data.normalized_y:.2f})",
                f"Confidence: {hand_data.confidence:.2f}",
                f"Size: {hand_data.hand_size:.1f}px"
            ]

            # Draw each text line
            for i, text in enumerate(info_lines):
                cv2.putText(frame, text, (10, 30 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            # No hand message
            cv2.putText(frame, "No hand detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return frame

    def release(self):
        """Clean up resources: close camera/Tello and MediaPipe."""
        if not self.is_tello:
            self.camera.release()
        if self._legacy_hands is not None:
            self._legacy_hands.close()
        if self._tasks_landmarker is not None:
            self._tasks_landmarker.close()
        cv2.destroyAllWindows()


def main():
    """Main function to run the hand tracking demo with Tello."""
    print("Initializing Tello hand tracker...")

    t = Tello()
    tracker = None

    try:
        t.connect()
        print("Battery:", t.get_battery(), "%")
        t.streamon()
        frame_read = t.get_frame_read()

        tracker = HandTracker(camera_source=t)
        print("Hand tracker ready. Press 'q' to quit.")
        print("Position your palm in front of the Tello camera for detection.")

        while True:
            # Capture and process frame
            frame, hand_data = tracker.get_hand_data()

            if frame is None:
                print("Frame capture failed.")
                break

            # Add visual overlays
            frame = tracker.draw_debug_info(frame, hand_data)

            # Show frame
            cv2.imshow("Palm Tracker - Tello", frame)

            # Console output for detected hand
            if hand_data.detected:
                print(f"Palm at ({hand_data.x}, {hand_data.y}) | Offset: ({hand_data.x_offset}, {hand_data.y_offset})")

            # Exit on 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        if tracker is not None:
            tracker.release()
        try:
            t.streamoff()
        except Exception as e:
            print("Streamoff warning:", repr(e))
        try:
            t.end()
        except Exception as e:
            print("End warning:", repr(e))
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()