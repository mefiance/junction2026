"""
Groups individual audio detections into time-windowed Events.
Also masks out Pygmy Owl detections while our own buzzer is playing,
attaches temperature/humidity readings, and controls when the camera is active.
"""

import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from models import Detection, Event

OWL = "Glaucidium passerinum"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class EventBuilder:
    def __init__(
        self,
        window_s: float = 45.0,
        min_confidence: float = 0.5,
        owl_mask_s: float = 3.0,
        location: dict | None = None,
        weather_fn: Callable[[], dict | None] | None = None,
        mobbers: dict[str, str] | set[str] | None = None,
    ):
        self.window_s = window_s
        self.min_confidence = min_confidence
        self.owl_mask_s = owl_mask_s
        self.location = location
        self.weather_fn = weather_fn
        self.mobbers = mobbers
        self.current: Event | None = None
        self.camera_until = 0.0
        self.take_photos = False
        self.opened_at = 0.0
        self.ready: list[Event] = []
        self.playback: dict | None = None
        self.playing = False
        self.mask_until = 0.0

    def on_playback(self, active: bool, now: float) -> None:
        if active and not self.playing:
            self.playback = {"species": OWL, "started": utc_now()}
        if self.playing and not active:
            self.mask_until = now + self.owl_mask_s
        self.playing = active

    def masked(self, now: float) -> bool:
        return self.playing or now < self.mask_until

    def on_audio(self, detections: list[Detection], now: float) -> bool:
        keep = [
            d for d in detections
            if d.confidence > self.min_confidence and not (d.species == OWL and self.masked(now))
        ]
        if not keep:
            return False
        self._close_if_expired(now)
        if self.current is None:
            self._open(now)
        for d in keep:
            d.t_offset_s = round(now - self.opened_at, 2)
        self.current.detections.extend(keep)
        if self.mobbers is None or any(d.species in self.mobbers for d in keep):
            self.take_photos = True
        self.camera_until = now + self.window_s
        return True

    def add_photo(self, photo_path: str) -> None:
        if self.current is not None:
            self.current.photos.append(photo_path)

    def camera_active(self, now: float) -> bool:
        return self.current is not None and self.take_photos and now < self.camera_until

    def tick(self, now: float) -> Event | None:
        self._close_if_expired(now)
        return self.ready.pop(0) if self.ready else None

    def flush(self) -> list[Event]:
        if self.current is not None:
            self.ready.append(self.current)
            self.current = None
        out, self.ready = self.ready, []
        return out

    def _open(self, now: float) -> None:
        stamp = utc_now()
        weather = self.weather_fn() if self.weather_fn is not None else None
        self.current = Event(
            f"{stamp}-{uuid.uuid4().hex[:6]}",
            stamp,
            location=self.location,
            playback=self.playback if self.masked(now) else None,
            weather=weather,
        )
        self.opened_at = now
        self.take_photos = False

    def _close_if_expired(self, now: float) -> None:
        if self.current is not None and now >= self.camera_until:
            self.ready.append(self.current)
            self.current = None
            self.take_photos = False
