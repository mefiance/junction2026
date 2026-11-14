"""
Arduino App Lab entry point (runs on the UNO Q Linux processor).
Runs the BirdNET + USB camera pipeline when available, or acts as a simple
60-second Pygmy Owl buzzer controller over Bridge without taking blind photos.
"""

import sys
import tempfile
import time
from pathlib import Path

from arduino.app_utils import App, Bridge

ROOT_DIR = Path(__file__).resolve().parent.parent
BIRD_REC_DIR = ROOT_DIR / "bird_recognition"
if BIRD_REC_DIR.is_dir() and str(BIRD_REC_DIR) not in sys.path:
    sys.path.insert(0, str(BIRD_REC_DIR))

PLAYBACK_FLAG = Path(tempfile.gettempdir()) / "bird_monitor_playback"
LURE_INTERVAL_S = 60.0
LURE_NOTES = 4

_last_lure_ts = 0.0
_pipeline_attempted = False


def read_weather() -> dict | None:
    try:
        temp = float(Bridge.call("get_temperature", timeout=2))
        hum = float(Bridge.call("get_humidity", timeout=2))
        return {"temperature_c": round(temp, 2), "humidity_rh": round(hum, 2)}
    except Exception as exc:
        print(f"[Bridge] weather read warning: {exc}", flush=True)
        return None


def play_owl_lure(notes: int = LURE_NOTES) -> bool:
    PLAYBACK_FLAG.touch()
    try:
        timeout = max(5.0, notes * 2.6 + 3.0)
        res = Bridge.call("play_owl_bout", int(notes), timeout=timeout)
        return bool(res)
    except Exception as exc:
        print(f"[Bridge] play_owl_bout warning: {exc}", flush=True)
        return False
    finally:
        PLAYBACK_FLAG.unlink(missing_ok=True)


def loop():
    global _last_lure_ts, _pipeline_attempted

    if not _pipeline_attempted:
        _pipeline_attempted = True
        try:
            import birdnet  # noqa: F401
            from main import main as bird_main
            print("[Pygmy] Starting BirdNET + camera pipeline", flush=True)
            bird_main([])
            return
        except Exception as exc:
            print(f"[Pygmy] Running 60s owl buzzer loop ({exc})", flush=True)

    now = time.monotonic()
    if _last_lure_ts == 0.0 or (now - _last_lure_ts) >= LURE_INTERVAL_S:
        weather = read_weather()
        print(f"[Pygmy] Weather: {weather} — playing Pygmy Owl whistle bout...", flush=True)
        play_owl_lure(LURE_NOTES)
        _last_lure_ts = time.monotonic()

    time.sleep(1.0)


App.run(user_loop=loop)
