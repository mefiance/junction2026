import json
from dataclasses import dataclass, field, asdict

AUDIO = "audio"
VIDEO = "video"


@dataclass
class Detection:
    source: str
    species: str
    confidence: float
    common_name: str | None = None
    t_offset_s: float = 0.0
    photo: str | None = None


@dataclass
class Event:
    event_id: str
    timestamp: str
    detections: list[Detection] = field(default_factory=list)
    max_count: int = 0
    location: dict | None = None
    playback: dict | None = None
    weather: dict | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "Event":
        data = json.loads(raw)
        data["detections"] = [Detection(**d) for d in data["detections"]]
        return cls(**data)

    def top_species(self) -> str | None:
        audio = [d for d in self.detections if d.source == AUDIO]
        pool = audio or self.detections
        return max(pool, key=lambda d: d.confidence).species if pool else None
