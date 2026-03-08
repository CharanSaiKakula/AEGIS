"""
3D Human Pose Tracking with MediaPipe
Tracks full human bodies with depth perception and 3D coordinates
"""

import cv2  # OpenCV for image processing
import mediapipe as mp  # MediaPipe for pose detection
from dataclasses import dataclass  # For creating data structures
from typing import Optional, Tuple, Union  # Type hints
import numpy as np
from djitellopy import Tello  # Tello drone library


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
        # MediaPipe Pose solution with 3D tracking enabled
        self.mp_pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,  # 0=Lite, 1=Full, 2=Heavy (more accurate but slower)
            smooth_landmarks=True,  # Smooth landmark positions
            enable_segmentation=False,  # Don't need segmentation for tracking
            smooth_segmentation=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # MediaPipe drawing utilities for visualizing pose landmarks
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

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
                    pose_size=0.0, depth=0.0, landmarks_3d=None
                )
        else:
            # Get frame from standard webcam using OpenCV
            ret, frame = self.camera.read()
            if not ret:
                return None, PoseData(
                    detected=False, x=0, y=0, x_offset=0, y_offset=0,
                    normalized_x=0.0, normalized_y=0.0, confidence=0.0,
                    pose_size=0.0, depth=0.0, landmarks_3d=None
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
        # Get actual frame dimensions
        h, w = frame.shape[:2]
        center_x = w // 2
        center_y = h // 2

        # Convert BGR image to RGB as required by MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Run MediaPipe pose detection on the RGB frame
        results = self.mp_pose.process(rgb_frame)

        # Check if any pose was detected
        if results.pose_landmarks:
            # Get pose landmarks
            pose_landmarks = results.pose_landmarks

            # Calculate pose center by averaging key landmark positions
            # Use major body landmarks for center calculation
            key_landmarks = [
                pose_landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_HIP],
                pose_landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_HIP],
                pose_landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER],
                pose_landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER],
            ]

            # Calculate average position
            avg_x = sum(lm.x for lm in key_landmarks) / len(key_landmarks)
            avg_y = sum(lm.y for lm in key_landmarks) / len(key_landmarks)

            # Convert normalized coordinates to pixel coordinates
            pixel_x = int(avg_x * w)
            pixel_y = int(avg_y * h)

            # Calculate pixel offsets from frame center
            x_offset = pixel_x - center_x
            y_offset = pixel_y - center_y

            # Normalize offsets to -1 to 1 range for consistent control
            normalized_x = x_offset / center_x if center_x > 0 else 0.0
            normalized_y = y_offset / center_y if center_y > 0 else 0.0

            # Ensure normalized values stay within bounds
            normalized_x = max(-1.0, min(1.0, normalized_x))
            normalized_y = max(-1.0, min(1.0, normalized_y))

            # Get detection confidence score from MediaPipe
            confidence = results.pose_world_landmarks is not None

            # Estimate pose size using bounding box of all landmarks
            x_coords = [int(lm.x * w) for lm in pose_landmarks.landmark]
            y_coords = [int(lm.y * h) for lm in pose_landmarks.landmark]
            width = max(x_coords) - min(x_coords)
            height = max(y_coords) - min(y_coords)
            pose_size = float(width * height)  # Area approximation

            # Estimate depth using inverse of pose size (larger pose = closer = smaller depth value)
            depth = 100000.0 / (pose_size + 1) if pose_size > 0 else 0.0

            # Extract 3D landmarks if available
            landmarks_3d = None
            if results.pose_world_landmarks:
                landmarks_3d = [
                    (lm.x, lm.y, lm.z) for lm in results.pose_world_landmarks.landmark
                ]

            # Return complete pose data
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
                landmarks_3d=landmarks_3d
            )
        else:
            # No pose detected, return default values
            return PoseData(
                detected=False, x=0, y=0, x_offset=0, y_offset=0,
                normalized_x=0.0, normalized_y=0.0, confidence=0.0,
                pose_size=0.0, depth=0.0, landmarks_3d=None
            )

    def draw_debug(self, frame: np.ndarray, pose_data: PoseData) -> Optional[np.ndarray]:
        """
        Draw debug information on the frame for visualization.

        Args:
            frame: Input image to draw on
            pose_data: Current pose detection data

        Returns:
            Modified frame with debug drawings
        """
        if frame is None:
            return None

        # Draw center crosshair for reference
        h, w = frame.shape[:2]
        center_x = w // 2
        center_y = h // 2
        cv2.line(frame, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 0), 2)
        cv2.line(frame, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 0), 2)

        # Re-process frame for drawing (necessary for landmark visualization)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.mp_pose.process(rgb_frame)

        # Draw MediaPipe pose landmarks and connections if detected
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp.solutions.pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
            )

        # Draw pose center and data if pose is detected
        if pose_data.detected:
            # Green circle at pose center
            cv2.circle(frame, (pose_data.x, pose_data.y), 10, (0, 255, 0), -1)

            # Blue line from center to pose
            cv2.line(frame, (center_x, center_y), (pose_data.x, pose_data.y), (255, 0, 0), 2)

            # Text information overlay
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

            # Draw text background and text
            for i, text in enumerate(info_lines):
                # Draw black background rectangle
                (text_width, text_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(frame, (10, 10 + i * 25), (10 + text_width, 10 + text_height + i * 25 + 5), (0, 0, 0), -1)
                # Draw white text
                cv2.putText(frame, text, (10, 30 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame

    def release(self):
        """Release camera resources"""
        if not self.is_tello:
            if hasattr(self, 'camera'):
                self.camera.release()


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
    
    try:
        print("Connecting to Tello...")
        tello.connect()
        print(f"Battery: {tello.get_battery()}%")

        print("Starting video stream...")
        tello.streamon()
        
        # Now initialize pose tracker after Tello is connected and streaming
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

            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                debug_mode = not debug_mode
                print(f"Debug mode: {'ON' if debug_mode else 'OFF'}")

            # Print pose data every 30 frames
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
        except:
            pass
        try:
            tello.end()
        except:
            pass
        tracker.release()
        cv2.destroyAllWindows()
        print("Tello camera test complete.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "webcam":
        test_webcam()
    else:
        test_tello()