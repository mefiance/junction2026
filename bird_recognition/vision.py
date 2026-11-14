"""
USB camera capture module.
Provides BurstCamera (lightweight OpenCV capture: 2 photos/sec for 5 seconds = 10 JPEGs)
"""

import time
from datetime import datetime, timezone
from pathlib import Path

from events import EventBuilder


class CvSource:
    def __init__(self, index: int | str = 0, width: int = 640, height: int = 480):
        import cv2
        self.cap = cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not self.cap.isOpened():
            raise RuntimeError(f"camera {index} not available")

    def grab(self) -> None:
        self.cap.grab()

    def read(self):
        ok, frame = self.cap.read()
        return frame if ok else None

    def close(self) -> None:
        self.cap.release()


class BurstCamera:
    """Lightweight camera that takes `fps` photos/sec for `duration_s` seconds."""

    def __init__(
        self,
        source,
        photo_dir: str = "photos",
        fps: float = 2.0,
        duration_s: float = 5.0,
    ):
        self.source = source
        self.photo_dir = Path(photo_dir)
        self.fps = fps
        self.duration_s = duration_s
        self.interval_s = 1.0 / fps if fps > 0 else 0.5
        self.max_photos = max(1, int(round(fps * duration_s)))
        self._active_event_id: str | None = None
        self._shots_taken: int = 0
        self._last_shot_at: float | None = None

    def idle(self) -> None:
        self.source.grab()

    def step(self, builder: EventBuilder, now: float) -> None:
        if not builder.camera_active(now) or builder.current is None:
            self.idle()
            return

        if builder.current.event_id != self._active_event_id:
            self._active_event_id = builder.current.event_id
            self._shots_taken = 0
            self._last_shot_at = None

        if self._shots_taken >= self.max_photos:
            self.idle()
            return

        if self._last_shot_at is not None and (now - self._last_shot_at) < self.interval_s:
            return

        frame = self.source.read()
        if frame is None:
            return

        self._last_shot_at = now
        self._shots_taken += 1
        saved = self.save_photo(frame, builder.current.event_id, self._shots_taken)
        builder.add_photo(saved)

    def capture_burst(self, event_id: str | None = None) -> list[str]:
        """Synchronously capture `max_photos` frames at `fps` rate."""
        tag = event_id or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        paths: list[str] = []
        for idx in range(1, self.max_photos + 1):
            t0 = time.monotonic()
            frame = self.source.read()
            if frame is not None:
                paths.append(self.save_photo(frame, tag, idx))
            if idx < self.max_photos:
                elapsed = time.monotonic() - t0
                if elapsed < self.interval_s:
                    time.sleep(self.interval_s - elapsed)
        return paths

    def save_photo(self, frame, event_id: str, index: int) -> str:
        import cv2
        event_dir = self.photo_dir / event_id
        event_dir.mkdir(parents=True, exist_ok=True)
        path = event_dir / f"photo_{index:02d}.jpg"
        cv2.imwrite(str(path), frame)
        return str(path)

    def close(self) -> None:
        self.source.close()
