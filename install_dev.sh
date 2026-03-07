#!/usr/bin/env bash
# Install requirements.txt + DJITelloPy in editable (dev) mode from GitHub
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${1:-$SCRIPT_DIR/DJITelloPy}"

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