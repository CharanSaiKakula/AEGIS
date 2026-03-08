import cv2  
import mediapipe as mp  
from dataclasses import dataclass  
from typing import Optional, Tuple 
import numpy as np
from djitellopy import Tello

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

        # Initialize MediaPipe
        self.mp_hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils

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
        """
        Internal method to process the frame and extract hand data using MediaPipe.

        Args:
            frame: Input image in BGR format

        Returns:
            HandData object with detection results
        """
        # Convert BGR image to RGB as required by MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Run MediaPipe hand detection on the RGB frame
        results = self.mp_hands.process(rgb_frame)

        # Check if any hands were detected
        if results.multi_hand_landmarks:
            # Use the first (and only) detected hand
            hand_landmarks = results.multi_hand_landmarks[0]

            # Calculate palm center by averaging key landmark positions
            # Landmarks: 0=wrist, 5=index base, 9=middle base, 13=ring base, 17=pinky base
            palm_points = [
                hand_landmarks.landmark[0],   # Wrist landmark
                hand_landmarks.landmark[5],   # Base of index finger
                hand_landmarks.landmark[9],   # Base of middle finger
                hand_landmarks.landmark[13],  # Base of ring finger
                hand_landmarks.landmark[17]   # Base of pinky finger
            ]

            # Compute average x and y coordinates (normalized 0-1)
            avg_x = sum(point.x for point in palm_points) / len(palm_points)
            avg_y = sum(point.y for point in palm_points) / len(palm_points)

            # Convert normalized coordinates to pixel coordinates
            pixel_x = int(avg_x * self.frame_width)
            pixel_y = int(avg_y * self.frame_height)

            # Calculate pixel offsets from frame center
            x_offset = pixel_x - self.center_x
            y_offset = pixel_y - self.center_y

            # Normalize offsets to -1 to 1 range for consistent control
            normalized_x = x_offset / self.center_x
            normalized_y = y_offset / self.center_y

            # Ensure normalized values stay within bounds
            normalized_x = max(-1.0, min(1.0, normalized_x))
            normalized_y = max(-1.0, min(1.0, normalized_y))

            # Get detection confidence score from MediaPipe
            confidence = results.multi_handedness[0].classification[0].score if results.multi_handedness else 1.0

            # Estimate hand size using bounding box of all landmarks
            x_coords = [int(lm.x * self.frame_width) for lm in hand_landmarks.landmark]
            y_coords = [int(lm.y * self.frame_height) for lm in hand_landmarks.landmark]
            width = max(x_coords) - min(x_coords)
            height = max(y_coords) - min(y_coords)
            hand_size = float(width * height)  # Area approximation

            # Return complete hand data
            return HandData(
                detected=True,
                x=pixel_x,
                y=pixel_y,
                x_offset=x_offset,
                y_offset=y_offset,
                normalized_x=normalized_x,
                normalized_y=normalized_y,
                confidence=confidence,
                hand_size=hand_size
            )
        else:
            # No hand detected, return default values
            return HandData(
                detected=False, x=0, y=0, x_offset=0, y_offset=0,
                normalized_x=0.0, normalized_y=0.0, confidence=0.0, hand_size=0.0
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

        # Re-process frame for drawing (necessary for landmark visualization)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.mp_hands.process(rgb_frame)

        # Draw MediaPipe hand landmarks and connections if detected
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS)

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
            self.camera.release()  # Release webcam
        # Note: Tello cleanup is handled in main()
        self.mp_hands.close()  # Close MediaPipe
        cv2.destroyAllWindows()  # Close OpenCV windows


def main():
    """Main function to run the hand tracking demo with Tello."""
    print("Initializing Tello hand tracker...")

    t = Tello()
    
    try:
        t.connect()
        print("Battery:", t.get_battery(), "%")
        # t.takeoff()  # Uncomment to make drone take off
        # t.move_up(100)  # Move up for better view

        t.streamon()
        frame_read = t.get_frame_read()

        # Create tracker with Tello
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
        # Clean up
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