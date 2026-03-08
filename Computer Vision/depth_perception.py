import cv2
import mediapipe as mp
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np


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
    distance: float      # estimated depth (larger = closer)
    z_norm: float        # raw normalized z from MediaPipe (negative when closer)
    confidence: float    # mediapipe detection/tracking confidence


class DepthHandTracker:
    """Hand tracker that returns 3D information using MediaPipe landmarks.

    MediaPipe provides an x,y,z coordinate for each hand landmark; the z value
    is normalized with respect to the hand size.  We use the wrist's z value
    as a proxy for distance.
    """

    def __init__(self, camera_id: int = 0):
        # configure capture
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        # mediapipe hand detector
        self.mp_hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.frame_w = 640
        self.frame_h = 480
        self.center_x = self.frame_w / 2
        self.center_y = self.frame_h / 2


    def read(self) -> Tuple[Optional[ThreeDHandData], Optional[np.ndarray]]:
        """Capture a frame, perform detection, and return ThreeDHandData + frame"""
        ret, frame = self.cap.read()
        if not ret:
            return None, None

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.mp_hands.process(rgb)

        if results.multi_hand_landmarks:
            lm = results.multi_hand_landmarks[0]
            # compute bounding box of landmarks
            xs = [int(p.x * self.frame_w) for p in lm.landmark]
            ys = [int(p.y * self.frame_h) for p in lm.landmark]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            cx = (min_x + max_x) / 2
            cy = (min_y + max_y) / 2
            x_err = (cx - self.center_x) / self.center_x
            y_err = (cy - self.center_y) / self.center_y

            # raw normalized z coordinate (negative closer/further)
            z_norm = lm.landmark[0].z

            # estimate depth using bounding-box area (bigger area = closer)
            box_w = max_x - min_x
            box_h = max_y - min_y
            area = box_w * box_h
            # distance = scale * (1/area); choose scale for reasonable numbers
            distance = 50000.0 / (area + 1)  # arbitrary scaling constant

            confidence = results.multi_handedness[0].classification[0].score

            return ThreeDHandData(int(cx), int(cy), x_err, y_err, distance, z_norm, confidence), frame
        else:
            # no hand detected: return zeros for all fields
            return ThreeDHandData(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0), frame

    def release(self):
        self.cap.release()
        self.mp_hands.close()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    tracker = DepthHandTracker()  # 3D depth relies on landmark z
    try:
        while True:
            data, frame = tracker.read()
            if frame is None:
                break
            if data:
                text = (f"pix=({data.x_pix},{data.y_pix}) err=({data.x_error:.2f},{data.y_error:.2f}) "
                        f"dist={data.distance:.1f} z={data.z_norm:.3f} conf={data.confidence:.2f}")
                cv2.putText(frame, text, (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0),2)
            cv2.imshow('3D Hand Tracker', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        tracker.release()
