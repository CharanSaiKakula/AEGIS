from djitellopy import Tello
import cv2
import time

t = Tello()

try:
    t.connect()
    print("Battery:", t.get_battery(), "%")

    t.streamon()
    frame_read = t.get_frame_read()

    time.sleep(0.5)

    while True:
        frame = frame_read.frame
        if frame is not None:
            cv2.imshow("Tello Live (press q to quit)", frame)

        if (cv2.waitKey(1) & 0xFF) == ord('q'):
            break

finally:

    try:
        t.streamoff()
    except Exception as e:
        print("streamoff cleanup warning:", repr(e))

    try:
        t.end()
    except Exception as e:
        print("end cleanup warning:", repr(e))

    cv2.destroyAllWindows()