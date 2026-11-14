import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from models import Detection, Event
from store import Store

PLAYBACK_FLAG = Path(tempfile.gettempdir()) / "bird_monitor_playback"


def device_arg(value: str) -> int | str:
    return int(value) if value.isdigit() else value


def print_event(event: Event) -> None:
    print(event.to_json(), flush=True)


def print_detections(t: float, detections: list[Detection]) -> None:
    for d in detections:
        print(f"{t:8.1f}s  {d.species} ({d.common_name})  {d.confidence:.2f}", file=sys.stderr, flush=True)


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


def cmd_run(args: argparse.Namespace) -> None:
    from audio import BirdNetClassifier, FileSource, MicSource
    from events import EventBuilder
    from pipeline import LivePipeline, replay

    location = {"lat": args.lat, "lon": args.lon, "name": args.place}
    use_geo = not args.no_geo
    print("loading BirdNET...", file=sys.stderr, flush=True)
    classifier = BirdNetClassifier(
        args.lat if use_geo else None, args.lon if use_geo else None,
        min_confidence=0.05 if args.debug else args.min_conf,
    )
    builder = EventBuilder(window_s=args.window, min_confidence=args.min_conf, location=location)
    store = Store(args.db)
    log = debug_detections if args.debug else print_detections
    try:
        if args.wav and not args.realtime:
            saved = replay(FileSource(args.wav), classifier, builder, store, print_event, log)
            print(f"saved {saved} events to {args.db}", file=sys.stderr)
            return
        source = FileSource(args.wav, realtime=True) if args.wav else MicSource(args.mic_device, args.mic_rate)
        if args.debug:
            source = with_levels(source)
        camera = make_camera(args) if args.camera else None
        print("listening, Ctrl+C to stop", file=sys.stderr, flush=True)
        try:
            LivePipeline(
                source, classifier, builder, store, camera=camera,
                playback_flag=PLAYBACK_FLAG, on_event=print_event, log=log,
            ).run()
        except KeyboardInterrupt:
            pass
        finally:
            if camera is not None:
                camera.close()
    finally:
        classifier.close()
        store.close()


def make_camera(args: argparse.Namespace):
    from vision import Camera, CvSource, YoloDetector
    return Camera(CvSource(device_arg(args.camera_index)), YoloDetector(), args.photo_dir)


def cmd_summary(args: argparse.Namespace) -> None:
    store = Store(args.db)
    out = {"day": args.day, "summary": store.daily_summary(args.day)}
    if args.events:
        out["events"] = [json.loads(e.to_json()) for e in store.events_on(args.day)]
    store.close()
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_playback(args: argparse.Namespace) -> None:
    if args.action == "start":
        PLAYBACK_FLAG.touch()
    else:
        PLAYBACK_FLAG.unlink(missing_ok=True)
    print(f"playback {args.action}: {PLAYBACK_FLAG}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bird-monitor")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    src = run.add_mutually_exclusive_group(required=True)
    src.add_argument("--wav")
    src.add_argument("--mic", action="store_true")
    run.add_argument("--realtime", action="store_true")
    run.add_argument("--mic-device", type=device_arg)
    run.add_argument("--mic-rate", type=int, default=48000)
    run.add_argument("--camera", action="store_true")
    run.add_argument("--camera-index", default="0")
    run.add_argument("--photo-dir", default="photos")
    run.add_argument("--lat", type=float, default=61.4978)
    run.add_argument("--lon", type=float, default=23.761)
    run.add_argument("--place", default="Tampere")
    run.add_argument("--no-geo", action="store_true")
    run.add_argument("--window", type=float, default=45.0)
    run.add_argument("--min-conf", type=float, default=0.5)
    run.add_argument("--db", default="birds.db")
    run.add_argument("--debug", action="store_true")
    run.set_defaults(func=cmd_run)

    summary = sub.add_parser("summary")
    summary.add_argument("--day", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    summary.add_argument("--events", action="store_true")
    summary.add_argument("--db", default="birds.db")
    summary.set_defaults(func=cmd_summary)

    playback = sub.add_parser("playback")
    playback.add_argument("action", choices=["start", "stop"])
    playback.set_defaults(func=cmd_playback)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
