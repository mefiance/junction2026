"""
Main runtime loop (LivePipeline) and WAV file replay.
Listens to 3-second audio chunks in a background thread, triggers the Pygmy Owl
buzzer every 60s or when an endangered bird is heard, runs the 5-second camera photo burst
only when a bird is detected, and saves completed events to birds.db.
"""

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
        lure_fn: Callable[[], bool] | None = None,
        lure_interval_s: float | None = None,
        lure_on_audio: bool = False,
        lure_cooldown_s: float = 30.0,
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
        self.lure_fn = lure_fn
        self.lure_interval_s = lure_interval_s
        self.lure_on_audio = lure_on_audio
        self.lure_cooldown_s = lure_cooldown_s
        self.detections: queue.Queue = queue.Queue()
        self.stop = threading.Event()
        self.started = clock()
        self.last_lure_at: float | None = None

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

    def _trigger_lure(self, now: float) -> None:
        if self.lure_fn is None:
            return
        self.last_lure_at = now
        self.builder.on_playback(True, now)
        try:
            self.lure_fn()
        finally:
            after = self.clock()
            self.builder.on_playback(False, after)
            self.last_lure_at = after

    def _can_lure(self, now: float) -> bool:
        if self.lure_fn is None:
            return False
        return self.last_lure_at is None or (now - self.last_lure_at) >= self.lure_cooldown_s

    def step(self) -> None:
        now = self.clock()
        if self.playback_flag is not None:
            self.builder.on_playback(self.playback_flag.exists(), now)

        # Every 60s: play owl buzzer to attract birds (camera stays OFF until a bird is heard)
        if (
            self.lure_interval_s is not None
            and self.lure_fn is not None
            and not self.builder.camera_active(now)
            and (self.last_lure_at is None or (now - self.last_lure_at) >= self.lure_interval_s)
        ):
            self._trigger_lure(now)
            now = self.clock()

        heard_target = False
        while True:
            try:
                detections = self.detections.get_nowait()
            except queue.Empty:
                break
            self.log(now - self.started, detections)
            if self.builder.on_audio(detections, now) and self.builder.take_photos:
                heard_target = True

        # If an endangered bird was heard, play owl call to pull it closer, then camera takes burst
        if heard_target and self.lure_on_audio and self._can_lure(now):
            self._trigger_lure(now)
            now = self.clock()

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
