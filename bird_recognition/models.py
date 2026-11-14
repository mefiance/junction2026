"""
Data models for a single BirdNET audio Detection and a grouped Event.
Also loads `endangered_mobbers.json` to check if a detected bird is an endangered target species.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_MOBBERS_PATHS = (
    Path(__file__).resolve().parent.parent / "endangered_mobbers.json",
    Path(__file__).resolve().parent / "endangered_mobbers.json",
    Path("endangered_mobbers.json"),
)


def _read_mobbers(path: str | Path | None = None) -> list[dict]:
    candidates = [Path(path)] if path is not None else list(DEFAULT_MOBBERS_PATHS)
    for candidate in candidates:
        if candidate.is_file():
            return [row for row in json.loads(candidate.read_text(encoding="utf-8")) if "scientific" in row]
    return []


def load_endangered_mobbers(path: str | Path | None = None) -> dict[str, str]:
    return {row["scientific"]: row["english"] for row in _read_mobbers(path)}


def load_mobber_statuses(path: str | Path | None = None) -> dict[str, str]:
    return {row["scientific"]: row["status"] for row in _read_mobbers(path) if row.get("status")}


@dataclass
class Detection:
    species: str
    confidence: float
    common_name: str | None = None
    t_offset_s: float = 0.0


@dataclass
class Event:
    event_id: str
    timestamp: str
    detections: list[Detection] = field(default_factory=list)
    photos: list[str] = field(default_factory=list)
    location: dict | None = None
    playback: dict | None = None
    weather: dict | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "Event":
        data = json.loads(raw)
        det_fields = {"species", "confidence", "common_name", "t_offset_s"}
        data["detections"] = [
            Detection(**{k: v for k, v in d.items() if k in det_fields})
            for d in data.get("detections", [])
        ]
        event_fields = {"event_id", "timestamp", "detections", "photos", "location", "playback", "weather"}
        return cls(**{k: v for k, v in data.items() if k in event_fields})

    def top_species(self) -> str | None:
        return max(self.detections, key=lambda d: d.confidence).species if self.detections else None

    def endangered_species(self, mobbers: dict[str, str] | None = None) -> list[str]:
        lookup = load_endangered_mobbers() if mobbers is None else mobbers
        found = []
        for d in self.detections:
            if d.species in lookup and d.species not in found:
                found.append(d.species)
        return found
