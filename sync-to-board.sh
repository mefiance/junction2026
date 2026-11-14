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

echo "Pushing local files to Arduino UNO Q (${REMOTE_DIR})..."
"$ADB" shell "mkdir -p ${REMOTE_DIR}/sketch ${REMOTE_DIR}/python"
"$ADB" push "${SCRIPT_DIR}/app.yaml" "${REMOTE_DIR}/app.yaml"
"$ADB" push "${SCRIPT_DIR}/.gitignore" "${REMOTE_DIR}/.gitignore"
"$ADB" push "${SCRIPT_DIR}/README.md" "${REMOTE_DIR}/README.md"
"$ADB" push "${SCRIPT_DIR}/sketch/sketch.ino" "${REMOTE_DIR}/sketch/sketch.ino"
"$ADB" push "${SCRIPT_DIR}/sketch/sketch.yaml" "${REMOTE_DIR}/sketch/sketch.yaml"
"$ADB" push "${SCRIPT_DIR}/python/main.py" "${REMOTE_DIR}/python/main.py"

echo "Done! Arduino App Lab is now synced with your local repo."
