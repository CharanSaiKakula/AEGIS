# HackCU12-Project
Drone Project

## Mac setup (CV / MediaPipe)

On macOS, MediaPipe 0.10.30+ uses the Tasks API and requires downloaded `.task` models. Install them with:

```bash
./install_dev.sh --mac
```

This downloads `hand_landmarker.task` and `pose_landmarker_full.task` into `.mediapipe/` for use by `cv/depth_perception_mac.py` and `cv/human_pose_tracker_3d.py`.

**GPU / display requirements:** Pose and hand tracking on Mac can require a valid GPU/OpenGL context. If you see errors like `NSOpenGLPixelFormat` or `kGpuService ... cannot be created`, run the app from a normal terminal (not headless) with display access, and ensure your terminal/app has **Camera** permission in **System Preferences → Security & Privacy → Privacy**. Running in a sandboxed or headless environment may still fail until MediaPipe supports a CPU-only path for these tasks on macOS.

---

bruh - vishnu