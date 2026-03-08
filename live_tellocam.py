from flask import Flask, Response
from djitellopy import Tello
import cv2
import threading
import time
import numpy as np

app = Flask(__name__)
tello = None
frame_read = None

def init_drone():
    global tello, frame_read
    tello = Tello()
    try:
        tello.connect()
        tello.streamon()
        time.sleep(2)   
        tello.takeoff()
        
        frame_read = tello.get_frame_read()
        print("Connected to Tello. Battery:", tello.get_battery(), "%")
    except Exception as e:
        print("Could not connect to Tello:", e)
        tello = None

def generate_frames():
    global frame_read
    while True:
        if frame_read is not None and frame_read.frame is not None:
            frame = frame_read.frame
            
            # Convert RGB to BGR to fix the blue tint issue because OpenCV imencode expects BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Optional: Resize to save bandwidth or process
            # frame = cv2.resize(frame, (640, 480))
            
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        else:
            # Generate static noise if no drone connection
            noise = np.random.randint(0, 256, (360, 480, 3), dtype=np.uint8)
            cv2.putText(noise, "NO SIGNAL / DETACHED", (70, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            ret, buffer = cv2.imencode('.jpg', noise)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.05)
        
        time.sleep(0.03) # Cap frame rate

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    threading.Thread(target=init_drone, daemon=True).start()
    app.run(host='0.0.0.0', port=5505, debug=False, threaded=True)
