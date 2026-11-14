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
        temp = round(float(Bridge.call("get_temperature", timeout=2)), 2)
        hum = round(float(Bridge.call("get_humidity", timeout=2)), 2)
        decision = "safe" if (temp >= -5.0 and hum <= 95.0) else "unsafe"
        print(f"[thermo] {temp}C, {hum}% RH -> {decision}", flush=True)
        return {"temperature_c": temp, "humidity_rh": hum}
    except Exception as exc:
        print(f"[thermo] read failed ({exc})", flush=True)
        return None


def play_owl_lure(notes: int = LURE_NOTES) -> bool:
    PLAYBACK_FLAG.touch()
    try:
        print(f"[buzzer] playing {int(notes)} notes...", flush=True)
        timeout = max(5.0, notes * 2.6 + 3.0)
        res = Bridge.call("play_owl_bout", int(notes), timeout=timeout)
        ok = bool(res)
        if ok:
            print("[buzzer] done", flush=True)
        else:
            print("[thermo] unsafe weather -> buzzer blocked", flush=True)
        return ok
    except Exception as exc:
        print(f"[buzzer] failed ({exc})", flush=True)
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
