"""
CLI entry point for the bird recognition & owl-lure system.
Connects the microphone (BirdNET), USB camera (2 fps x 5s burst), SQLite store,
and Arduino UNO Q hardware (buzzer + temperature/humidity sensor).
"""

import argparse
import sys
import tempfile
from pathlib import Path

from models import Detection, Event, load_endangered_mobbers, load_mobber_statuses
from store import Store

# Default configuration
LAT = 61.4978
LON = 23.761
PLACE = "Tampere"
MIN_CONF = 0.5
WINDOW_S = 15.0
LURE_INTERVAL_S = 60.0
LURE_NOTES = 4
BURST_FPS = 2.0
BURST_SECONDS = 5.0
PHOTO_DIR = "photos"
BUNDLE_DIR = "captures"
DB_PATH = "birds.db"

PLAYBACK_FLAG = Path(tempfile.gettempdir()) / "bird_monitor_playback"
MOBBERS = load_endangered_mobbers()
STATUSES = load_mobber_statuses()


def print_event(event: Event) -> None:
    print(event.to_json(), flush=True)


def print_detections(t: float, detections: list[Detection]) -> None:
    for d in detections:
        tag = f" [ENDANGERED {STATUSES.get(d.species, '?')}]" if d.species in MOBBERS else ""
        print(f"{t:8.1f}s  {d.species} ({d.common_name})  {d.confidence:.2f}{tag}", file=sys.stderr, flush=True)


def debug_detections(t: float, detections: list[Detection]) -> None:
    if not detections:
        print(f"{t:8.1f}s  -", file=sys.stderr, flush=True)
    print_detections(t, detections)


def with_levels(source):
    import numpy as np
    for chunk, sr in source:
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        hint = "  silent: check microphone permission" if rms < 1e-4 else ""
        print(f"level {rms:.4f}{hint}", file=sys.stderr, flush=True)
        yield chunk, sr


def make_camera(camera_index: int | str = 0):
    from vision import BurstCamera, CvSource
    idx = int(camera_index) if str(camera_index).isdigit() else camera_index
    return BurstCamera(
        CvSource(idx),
        photo_dir=PHOTO_DIR,
        fps=BURST_FPS,
        duration_s=BURST_SECONDS,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bird-monitor")
    parser.add_argument("--wav", help="Test with a WAV file instead of live microphone")
    parser.add_argument("--no-camera", action="store_true", help="Disable USB camera capture")
    parser.add_argument("--camera-index", default="0", help="USB camera index (default: 0)")
    parser.add_argument("--debug", action="store_true", help="Print audio levels and low-confidence detections")
    return parser


def main(argv: list[str] | None = None) -> None:
    from audio import BirdNetClassifier, FileSource, MicSource
    from bundle import UnoQHardware, save_event_bundle
    from events import EventBuilder
    from pipeline import LivePipeline, replay

    args = build_parser().parse_args(argv)
    location = {"lat": LAT, "lon": LON, "name": PLACE}
    hw = UnoQHardware(playback_flag=PLAYBACK_FLAG)

    print("loading BirdNET...", file=sys.stderr, flush=True)
    classifier = BirdNetClassifier(
        LAT, LON,
        min_confidence=0.05 if args.debug else MIN_CONF,
    )
    builder = EventBuilder(
        window_s=WINDOW_S,
        min_confidence=MIN_CONF,
        location=location,
        weather_fn=hw.read_weather,
        mobbers=MOBBERS,
    )
    store = Store(DB_PATH)
    log = debug_detections if args.debug else print_detections

    def handle_event(event: Event) -> None:
        if event.endangered_species(MOBBERS):
            zip_path = save_event_bundle(event, bundle_dir=BUNDLE_DIR, mobbers=MOBBERS, statuses=STATUSES)
            print(f"saved endangered bundle: {zip_path}", file=sys.stderr, flush=True)
        print_event(event)

    try:
        if args.wav:
            saved = replay(FileSource(args.wav), classifier, builder, store, handle_event, log)
            print(f"saved {saved} events to {DB_PATH}", file=sys.stderr)
            return

        source = MicSource()
        if args.debug:
            source = with_levels(source)
        camera = None if args.no_camera else make_camera(args.camera_index)
        print("listening, Ctrl+C to stop", file=sys.stderr, flush=True)
        try:
            LivePipeline(
                source,
                classifier,
                builder,
                store,
                camera=camera,
                playback_flag=PLAYBACK_FLAG,
                on_event=handle_event,
                log=log,
                lure_fn=(lambda: hw.play_owl_lure(LURE_NOTES)) if hw.bridge is not None else None,
                lure_interval_s=LURE_INTERVAL_S,
                lure_on_audio=True,
            ).run()
        except KeyboardInterrupt:
            pass
        finally:
            if camera is not None:
                camera.close()
    finally:
        classifier.close()
        store.close()


if __name__ == "__main__":
    main()
