#!/usr/bin/env bash
set -euo pipefail

APP_NAME="pygmy"
REMOTE_DIR="/home/arduino/ArduinoApps/${APP_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_adb() {
  if command -v adb >/dev/null 2>&1; then
    command -v adb
    return
  fi
  for candidate in \
    "$HOME"/.arduino15/packages/arduino/tools/adb/*/adb \
    "$HOME"/Library/Arduino15/packages/arduino/tools/adb/*/adb; do
    if [ -x "$candidate" ]; then
      echo "$candidate"
      return
    fi
  done
  echo "Error: adb not found. Install adb or Arduino App Lab." >&2
  exit 1
}

ADB="$(find_adb)"

if ! "$ADB" get-state >/dev/null 2>&1; then
  echo "Error: No Arduino UNO Q detected over USB/ADB. Plug in the board and try again." >&2
  exit 1
fi

echo "Pulling files from Arduino UNO Q (${REMOTE_DIR}) into local repo..."
mkdir -p "${SCRIPT_DIR}/sketch" "${SCRIPT_DIR}/python"
"$ADB" pull "${REMOTE_DIR}/app.yaml" "${SCRIPT_DIR}/app.yaml"
"$ADB" pull "${REMOTE_DIR}/sketch/sketch.ino" "${SCRIPT_DIR}/sketch/sketch.ino"
"$ADB" pull "${REMOTE_DIR}/sketch/sketch.yaml" "${SCRIPT_DIR}/sketch/sketch.yaml"
"$ADB" pull "${REMOTE_DIR}/python/main.py" "${SCRIPT_DIR}/python/main.py"

echo "Done! Local repo updated from the board. Run 'git status' or 'git diff' to review."
