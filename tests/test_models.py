import json

from models import AUDIO, VIDEO, Detection, Event


def test_json_roundtrip():
    e = Event("e1", "2026-11-14T10:00:00Z", max_count=2)
    e.detections.append(Detection(AUDIO, "Parus major", 0.87, "Great Tit"))
    e.detections.append(Detection(VIDEO, "bird", 0.71, photo="photos/1.jpg"))
    back = Event.from_json(e.to_json())
    assert back == e
    assert isinstance(back.detections[0], Detection)


def test_old_json_without_new_fields_loads():
    raw = json.dumps({
        "event_id": "old", "timestamp": "2026-11-13T08:00:00Z", "max_count": 1,
        "detections": [{"source": "audio", "species": "Parus major", "confidence": 0.8, "photo": None}],
    })
    e = Event.from_json(raw)
    assert e.detections[0].common_name is None
    assert e.detections[0].t_offset_s == 0.0
    assert e.weather is None


def test_top_species_prefers_audio():
    e = Event("e", "t", [Detection(VIDEO, "bird", 0.99), Detection(AUDIO, "Parus major", 0.6)])
    assert e.top_species() == "Parus major"


def test_top_species_video_only_and_empty():
    assert Event("e", "t", [Detection(VIDEO, "bird", 0.7)]).top_species() == "bird"
    assert Event("e", "t").top_species() is None
