"""
3D Human Pose Tracking with MediaPipe
Tracks full human bodies with depth perception and 3D coordinates.
Supports legacy mp.solutions.pose (e.g. Windows) and Tasks API (e.g. Mac 0.10.30+).
On Mac, run: ./install_dev.sh --mac  to install .mediapipe/pose_landmarker_full.task
"""

import os
import cv2  # OpenCV for image processing
import mediapipe as mp  # MediaPipe for pose detection
from dataclasses import dataclass  # For creating data structures
from typing import Optional, Tuple, Union  # Type hints
import numpy as np
from djitellopy import Tello  # Tello drone library
import time
# Legacy mp.solutions when available (e.g. Windows); else use Tasks API (e.g. Mac 0.10.30+)
_USE_LEGACY = hasattr(mp, "solutions")

if _USE_LEGACY:
    _PoseLandmark = mp.solutions.pose.PoseLandmark  # for indices
else:
    # Tasks API: pose model path and landmark indices (same as BlazePose 33-point)
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
    """Data structure to hold all information about detected human pose"""
    detected: bool  # True if a pose is detected, False otherwise
    x: int  # X-coordinate of pose center in pixels (0 to frame width)
    y: int  # Y-coordinate of pose center in pixels (0 to frame height)
    x_offset: int  # Horizontal distance from frame center (negative = left, positive = right)
    y_offset: int  # Vertical distance from frame center (negative = up, positive = down)
    normalized_x: float  # X position normalized to -1 (left) to 1 (right), 0 = center
    normalized_y: float  # Y position normalized to -1 (up) to 1 (down), 0 = center
    confidence: float  # Confidence score from MediaPipe (0.0 to 1.0)
    pose_size: float  # Approximate pose area in pixels (width * height of bounding box)
    depth: float  # Estimated depth (inverse of pose size, arbitrary units)
    landmarks_3d: Optional[list]  # List of 3D landmark coordinates if available
    shoulder_width_px: float  # Shoulder width in pixels (for metric distance; 0 if unavailable)


class PoseTracker3D:
    def __init__(self, camera_source: Union[int, Tello] = 0):
        """
        Initialize 3D pose tracker with either a webcam or Tello drone.

        Args:
            camera_source: Either an int (camera ID) or Tello object
        """
        # Detect if using Tello or webcam
        self.is_tello = isinstance(camera_source, Tello)

        if self.is_tello:
            # Store Tello object - frame reader will be initialized later after connect/streamon
            self.tello = camera_source
            self.frame_read = None  # Will be set after Tello is ready
        else:
            self.camera = cv2.VideoCapture(camera_source)

        if _USE_LEGACY:
            self._legacy_pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                smooth_landmarks=True,
                enable_segmentation=False,
                smooth_segmentation=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._tasks_landmarker = None
            self.mp_drawing = mp.solutions.drawing_utils
            self.mp_drawing_styles = mp.solutions.drawing_styles
        else:
            self._legacy_pose = None
            from mediapipe.tasks.python import BaseOptions
            from mediapipe.tasks.python.vision import PoseLandmarkerOptions, RunningMode

            model_path = _pose_model_path()
            # Use CPU delegate on Mac to avoid NSOpenGLPixelFormat/GPU init failures
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

    def get_pose_data(self) -> Tuple[Optional[np.ndarray], PoseData]:
        """
        Capture a frame from the camera/Tello and detect human pose with 3D tracking.

        Returns:
            A tuple containing:
            - frame: The captured image (BGR format), or None if capture failed
            - pose_data: PoseData object with detection results
        """
        # Read frame from appropriate source (Tello or webcam)
        if self.is_tello:
            # Initialize frame reader if not done yet
            if self.frame_read is None:
                self.frame_read = self.tello.get_frame_read()
            
            # Get frame from Tello drone stream
            frame = self.frame_read.frame
            # Check if frame is valid
            if frame is None:
                return None, PoseData(
                    detected=False, x=0, y=0, x_offset=0, y_offset=0,
                    normalized_x=0.0, normalized_y=0.0, confidence=0.0,
                    pose_size=0.0, depth=0.0, landmarks_3d=None, shoulder_width_px=0.0
                )
        else:
            # Get frame from standard webcam using OpenCV
            ret, frame = self.camera.read()
            if not ret:
                return None, PoseData(
                    detected=False, x=0, y=0, x_offset=0, y_offset=0,
                    normalized_x=0.0, normalized_y=0.0, confidence=0.0,
                    pose_size=0.0, depth=0.0, landmarks_3d=None, shoulder_width_px=0.0
                )

        # Flip the frame horizontally to create a mirror effect (optional for Tello)
        frame = cv2.flip(frame, 1)

        # Process the frame for pose detection
        pose_data = self._detect_pose(frame)

        return frame, pose_data

    def _detect_pose(self, frame: np.ndarray) -> PoseData:
        """
        Internal method to process the frame and extract pose data using MediaPipe.

        Args:
            frame: Input image in BGR format

        Returns:
            PoseData object with detection results
        """
        h, w = frame.shape[:2]
        center_x = w // 2
        center_y = h // 2
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if _USE_LEGACY:
            return self._detect_pose_legacy(rgb_frame, frame, w, h, center_x, center_y)
        return self._detect_pose_tasks(rgb_frame, frame, w, h, center_x, center_y)

    def _detect_pose_legacy(
        self, rgb_frame: np.ndarray, frame: np.ndarray,
        w: int, h: int, center_x: int, center_y: int
    ) -> PoseData:
        results = self._legacy_pose.process(rgb_frame)
        if not results.pose_landmarks:
            return _empty_pose_data()
        pose_landmarks = results.pose_landmarks
        key_landmarks = [
            pose_landmarks.landmark[_PoseLandmark.LEFT_HIP],
            pose_landmarks.landmark[_PoseLandmark.RIGHT_HIP],
            pose_landmarks.landmark[_PoseLandmark.LEFT_SHOULDER],
            pose_landmarks.landmark[_PoseLandmark.RIGHT_SHOULDER],
        ]
        avg_x = sum(lm.x for lm in key_landmarks) / len(key_landmarks)
        avg_y = sum(lm.y for lm in key_landmarks) / len(key_landmarks)
        pixel_x = int(avg_x * w)
        pixel_y = int(avg_y * h)
        x_offset = pixel_x - center_x
        y_offset = pixel_y - center_y
        normalized_x = max(-1.0, min(1.0, x_offset / center_x if center_x > 0 else 0.0))
        normalized_y = max(-1.0, min(1.0, y_offset / center_y if center_y > 0 else 0.0))
        confidence = results.pose_world_landmarks is not None
        x_coords = [int(lm.x * w) for lm in pose_landmarks.landmark]
        y_coords = [int(lm.y * h) for lm in pose_landmarks.landmark]
        width = max(x_coords) - min(x_coords)
        height = max(y_coords) - min(y_coords)
        pose_size = float(width * height)
        depth = 100000.0 / (pose_size + 1) if pose_size > 0 else 0.0
        landmarks_3d = None
        if results.pose_world_landmarks:
            landmarks_3d = [(lm.x, lm.y, lm.z) for lm in results.pose_world_landmarks.landmark]
        left_sh = pose_landmarks.landmark[_PoseLandmark.LEFT_SHOULDER]
        right_sh = pose_landmarks.landmark[_PoseLandmark.RIGHT_SHOULDER]
        shoulder_width_px = abs(left_sh.x - right_sh.x) * w
        return PoseData(
            detected=True, x=pixel_x, y=pixel_y, x_offset=x_offset, y_offset=y_offset,
            normalized_x=normalized_x, normalized_y=normalized_y, confidence=confidence,
            pose_size=pose_size, depth=depth, landmarks_3d=landmarks_3d,
            shoulder_width_px=shoulder_width_px,
        )

    def _detect_pose_tasks(
        self, rgb_frame: np.ndarray, frame: np.ndarray,
        w: int, h: int, center_x: int, center_y: int
    ) -> PoseData:
        rgb_contig = np.ascontiguousarray(rgb_frame)
        mp_image = _mp_image.Image(_mp_image.ImageFormat.SRGB, rgb_contig)
        result = self._tasks_landmarker.detect(mp_image)
        if not result.pose_landmarks:
            return _empty_pose_data()
        landmarks = result.pose_landmarks[0]
        key_indices = [LEFT_HIP_IDX, RIGHT_HIP_IDX, LEFT_SHOULDER_IDX, RIGHT_SHOULDER_IDX]
        xs = [landmarks[i].x for i in key_indices]
        ys = [landmarks[i].y for i in key_indices]
        avg_x = sum(xs) / len(xs)
        avg_y = sum(ys) / len(ys)
        pixel_x = int(avg_x * w)
        pixel_y = int(avg_y * h)
        x_offset = pixel_x - center_x
        y_offset = pixel_y - center_y
        normalized_x = max(-1.0, min(1.0, x_offset / center_x if center_x > 0 else 0.0))
        normalized_y = max(-1.0, min(1.0, y_offset / center_y if center_y > 0 else 0.0))
        x_coords = [int((p.x or 0) * w) for p in landmarks]
        y_coords = [int((p.y or 0) * h) for p in landmarks]
        width = max(x_coords) - min(x_coords)
        height = max(y_coords) - min(y_coords)
        pose_size = float(width * height)
        depth = 100000.0 / (pose_size + 1) if pose_size > 0 else 0.0
        landmarks_3d = None
        if result.pose_world_landmarks:
            landmarks_3d = [
                (p.x or 0, p.y or 0, p.z or 0) for p in result.pose_world_landmarks[0]
            ]
        shoulder_width_px = abs((landmarks[LEFT_SHOULDER_IDX].x or 0) - (landmarks[RIGHT_SHOULDER_IDX].x or 0)) * w
        return PoseData(
            detected=True, x=pixel_x, y=pixel_y, x_offset=x_offset, y_offset=y_offset,
            normalized_x=normalized_x, normalized_y=normalized_y, confidence=True,
            pose_size=pose_size, depth=depth, landmarks_3d=landmarks_3d,
            shoulder_width_px=shoulder_width_px,
        )

    def draw_debug(self, frame: np.ndarray, pose_data: PoseData) -> Optional[np.ndarray]:
        """Draw debug information on the frame for visualization."""
        if frame is None:
            return None
        h, w = frame.shape[:2]
        center_x = w // 2
        center_y = h // 2
        cv2.line(frame, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 0), 2)
        cv2.line(frame, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 0), 2)
        if _USE_LEGACY:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._legacy_pose.process(rgb_frame)
            if results.pose_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    mp.solutions.pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style(),
                )
        else:
            rgb_contig = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            mp_image = _mp_image.Image(_mp_image.ImageFormat.SRGB, rgb_contig)
            result = self._tasks_landmarker.detect(mp_image)
            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]
                for pt in landmarks:
                    x, y = int((pt.x or 0) * w), int((pt.y or 0) * h)
                    cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)
        if pose_data.detected:
            cv2.circle(frame, (pose_data.x, pose_data.y), 10, (0, 255, 0), -1)
            cv2.line(frame, (center_x, center_y), (pose_data.x, pose_data.y), (255, 0, 0), 2)
            info_lines = [
                f"Pose Detected: {pose_data.detected}",
                f"Pose Center: ({pose_data.x}, {pose_data.y})",
                f"Offset: ({pose_data.x_offset}, {pose_data.y_offset})",
                f"Normalized: ({pose_data.normalized_x:.2f}, {pose_data.normalized_y:.2f})",
                f"Confidence: {pose_data.confidence:.2f}",
                f"Size: {pose_data.pose_size:.1f}px",
                f"Depth: {pose_data.depth:.2f}",
                f"3D Landmarks: {len(pose_data.landmarks_3d) if pose_data.landmarks_3d else 0}"
            ]
            for i, text in enumerate(info_lines):
                (text_width, text_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(frame, (10, 10 + i * 25), (10 + text_width, 10 + text_height + i * 25 + 5), (0, 0, 0), -1)
                cv2.putText(frame, text, (10, 30 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return frame

    def release(self):
        """Release camera and MediaPipe resources"""
        if not self.is_tello and hasattr(self, "camera"):
            self.camera.release()
        if _USE_LEGACY and self._legacy_pose is not None:
            self._legacy_pose.close()
        if not _USE_LEGACY and self._tasks_landmarker is not None:
            self._tasks_landmarker.close()


def _empty_pose_data() -> PoseData:
    return PoseData(
        detected=False, x=0, y=0, x_offset=0, y_offset=0,
        normalized_x=0.0, normalized_y=0.0, confidence=0.0,
        pose_size=0.0, depth=0.0, landmarks_3d=None, shoulder_width_px=0.0,
    )


# ============================================================================
# STANDALONE TEST FUNCTIONS
# ============================================================================

def test_webcam():
    """Test pose tracking with webcam"""
    print("Testing 3D Pose Tracking with Webcam...")
    print("Press 'q' to quit, 'd' to toggle debug drawing")

    tracker = PoseTracker3D(camera_source=0)
    debug_mode = True

    try:
        while True:
            frame, pose_data = tracker.get_pose_data()

            if frame is not None:
                if debug_mode:
                    frame = tracker.draw_debug(frame, pose_data)

                cv2.imshow("3D Human Pose Tracking", frame)

            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                debug_mode = not debug_mode
                print(f"Debug mode: {'ON' if debug_mode else 'OFF'}")

            # Print pose data every 30 frames
            if hasattr(tracker, 'frame_count'):
                tracker.frame_count = getattr(tracker, 'frame_count', 0) + 1
                if tracker.frame_count % 30 == 0:
                    status = "DETECTED" if pose_data.detected else "NOT DETECTED"
                    print(f"[{tracker.frame_count}] {status} - "
                          f"Pos: ({pose_data.x}, {pose_data.y}) | "
                          f"Depth: {pose_data.depth:.2f}")

    except KeyboardInterrupt:
        print("Interrupted by user")

    finally:
        tracker.release()
        cv2.destroyAllWindows()
        print("Webcam test complete.")


def test_tello():
    """Test pose tracking with Tello drone camera feed"""
    print("Testing 3D Pose Tracking with Tello Drone Camera...")
    print("Make sure Tello is connected.")
    print("Press 'q' to quit, 'd' to toggle debug drawing")

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
        tello.move_up(160)

        tracker = PoseTracker3D(camera_source=tello)
        debug_mode = True

        print("Human pose detection active! Press 'q' to quit.")

        frame_count = 0
        while True:
            frame, pose_data = tracker.get_pose_data()

            if frame is not None:
                if debug_mode:
                    frame = tracker.draw_debug(frame, pose_data)

                cv2.imshow("Tello 3D Human Pose Detection", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                debug_mode = not debug_mode
                print(f"Debug mode: {'ON' if debug_mode else 'OFF'}")

            frame_count += 1
            if frame_count % 30 == 0:
                status = "DETECTED" if pose_data.detected else "NOT DETECTED"
                print(f"[{frame_count}] {status} - "
                      f"Pos: ({pose_data.x}, {pose_data.y}) | "
                      f"Depth: {pose_data.depth:.2f}")

    except KeyboardInterrupt:
        print("Interrupted by user")

    finally:
        print("Cleaning up...")
        try:
            tello.streamoff()
        except Exception:
            pass
        try:
            tello.end()
        except Exception:
            pass
        if tracker is not None:
            tracker.release()
        cv2.destroyAllWindows()
        print("Tello camera test complete.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "webcam":
        test_webcam()
    else:
        test_tello()