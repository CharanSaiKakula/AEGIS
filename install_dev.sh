#!/usr/bin/env bash
# Install requirements.txt + DJITelloPy in editable (dev) mode from GitHub
# Usage: ./install_dev.sh [--mac] [DJITelloPy_dir]
#   --mac  Pre-download MediaPipe .task models to .mediapipe/ (for Mac with mediapipe 0.10.30+)
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse --mac flag and optional DJITelloPy path
INSTALL_MAC_MODELS=false
REPO_DIR="$SCRIPT_DIR/DJITelloPy"
for arg in "$@"; do
  if [[ "$arg" == "--mac" ]]; then
    INSTALL_MAC_MODELS=true
  elif [[ -n "$arg" && "$arg" != -* ]]; then
    REPO_DIR="$arg"
  fi
done

# MediaPipe models for Mac (Tasks API)
HAND_MODEL_URL="https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
POSE_MODEL_URL="https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"
MEDIAPIPE_DIR="$SCRIPT_DIR/.mediapipe"
HAND_MODEL_PATH="$MEDIAPIPE_DIR/hand_landmarker.task"
POSE_MODEL_PATH="$MEDIAPIPE_DIR/pose_landmarker_full.task"

if [[ "$INSTALL_MAC_MODELS" == "true" ]]; then
  echo "Installing MediaPipe models for Mac (.mediapipe)..."
  mkdir -p "$MEDIAPIPE_DIR"
  if [[ -f "$HAND_MODEL_PATH" ]]; then
    echo "  hand_landmarker.task already exists, skipping."
  else
    echo "  Downloading hand_landmarker.task..."
    curl -sL "$HAND_MODEL_URL" -o "$HAND_MODEL_PATH"
    echo "  Done. hand_landmarker.task installed."
  fi
  if [[ -f "$POSE_MODEL_PATH" ]]; then
    echo "  pose_landmarker_full.task already exists, skipping."
  else
    echo "  Downloading pose_landmarker_full.task..."
    curl -sL "$POSE_MODEL_URL" -o "$POSE_MODEL_PATH"
    echo "  Done. pose_landmarker_full.task installed."
  fi
fi

echo "Installing requirements.txt..."
pip install -r "$SCRIPT_DIR/requirements.txt"

if [[ -d "$REPO_DIR" ]]; then
  echo "Directory $REPO_DIR exists; updating..."
  git -C "$REPO_DIR" pull
else
  git clone https://github.com/damiafuentes/DJITelloPy.git "$REPO_DIR"
fi

pip install -e "$REPO_DIR"
pip install -e "$SCRIPT_DIR"
echo "Done. Requirements, DJITelloPy, and aegis CLI installed."