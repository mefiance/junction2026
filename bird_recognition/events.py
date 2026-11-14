import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from models import VIDEO, Detection, Event

OWL = "Glaucidium passerinum"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class EventBuilder:
    def __init__(
        self,
        window_s: float = 45.0,
        min_confidence: float = 0.5,
        photo_interval_s: float = 2.0,
        owl_mask_s: float = 3.0,
        location: dict | None = None,
    ):
        self.window_s = window_s
        self.min_confidence = min_confidence
        self.photo_interval_s = photo_interval_s
        self.owl_mask_s = owl_mask_s
        self.location = location
        self.current: Event | None = None
        self.camera_until = 0.0
        self.opened_at = 0.0
        self.last_photo_at: float | None = None
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
        self.camera_until = now + self.window_s
        return True

    def on_frame(
        self,
        confidences: list[float],
        now: float,
        save_photo: Callable[[], str] | None = None,
    ) -> None:
        if not self.camera_active(now) or not confidences:
            return
        self.current.max_count = max(self.current.max_count, len(confidences))
        if save_photo is None:
            return
        if self.last_photo_at is not None and now - self.last_photo_at < self.photo_interval_s:
            return
        self.last_photo_at = now
        self.current.detections.append(Detection(
            VIDEO, "bird", round(max(confidences), 3),
            t_offset_s=round(now - self.opened_at, 2), photo=save_photo(),
        ))

    def camera_active(self, now: float) -> bool:
        return self.current is not None and now < self.camera_until

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
        self.current = Event(
            f"{stamp}-{uuid.uuid4().hex[:6]}", stamp,
            location=self.location,
            playback=self.playback if self.masked(now) else None,
        )
        self.opened_at = now
        self.last_photo_at = None

    def _close_if_expired(self, now: float) -> None:
        if self.current is not None and now >= self.camera_until:
            self.ready.append(self.current)
            self.current = None
