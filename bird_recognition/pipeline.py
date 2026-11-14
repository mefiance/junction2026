import queue
import threading
import time
from collections.abc import Callable, Iterable
from pathlib import Path

from audio import CHUNK_S, Chunk
from events import EventBuilder
from models import Detection, Event
from store import Store

EventSink = Callable[[Event], None]
DetectionLog = Callable[[float, list[Detection]], None]


def _ignore(*_) -> None:
    pass


def drain(builder: EventBuilder, store: Store, now: float, on_event: EventSink) -> int:
    count = 0
    while (event := builder.tick(now)) is not None:
        store.save(event)
        on_event(event)
        count += 1
    return count


def finish(builder: EventBuilder, store: Store, on_event: EventSink) -> int:
    events = builder.flush()
    for event in events:
        store.save(event)
        on_event(event)
    return len(events)


def replay(
    source: Iterable[Chunk],
    classifier,
    builder: EventBuilder,
    store: Store,
    on_event: EventSink = _ignore,
    log: DetectionLog = _ignore,
) -> int:
    now = 0.0
    saved = 0
    for chunk, sr in source:
        now += CHUNK_S
        detections = classifier.classify(chunk, sr)
        log(now, detections)
        builder.on_audio(detections, now)
        saved += drain(builder, store, now, on_event)
    return saved + finish(builder, store, on_event)


class LivePipeline:
    def __init__(
        self,
        source: Iterable[Chunk],
        classifier,
        builder: EventBuilder,
        store: Store,
        camera=None,
        playback_flag: Path | None = None,
        on_event: EventSink = _ignore,
        log: DetectionLog = _ignore,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.source = source
        self.classifier = classifier
        self.builder = builder
        self.store = store
        self.camera = camera
        self.playback_flag = playback_flag
        self.on_event = on_event
        self.log = log
        self.clock = clock
        self.detections: queue.Queue = queue.Queue()
        self.stop = threading.Event()
        self.started = clock()

    def run(self) -> None:
        listener = threading.Thread(target=self._listen, daemon=True)
        listener.start()
        try:
            while not self.stop.is_set():
                self.step()
                time.sleep(0.05 if self.builder.camera_active(self.clock()) else 0.2)
            self.step()
        finally:
            finish(self.builder, self.store, self.on_event)

    def step(self) -> None:
        now = self.clock()
        if self.playback_flag is not None:
            self.builder.on_playback(self.playback_flag.exists(), now)
        while True:
            try:
                detections = self.detections.get_nowait()
            except queue.Empty:
                break
            self.log(now - self.started, detections)
            self.builder.on_audio(detections, now)
        if self.camera is not None:
            if self.builder.camera_active(now):
                self.camera.step(self.builder, now)
            else:
                self.camera.idle()
        drain(self.builder, self.store, now, self.on_event)

    def _listen(self) -> None:
        try:
            for chunk, sr in self.source:
                if self.stop.is_set():
                    break
                self.detections.put(self.classifier.classify(chunk, sr))
        finally:
            self.stop.set()
