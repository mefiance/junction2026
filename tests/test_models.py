import json

from models import Detection, Event, load_endangered_mobbers, load_mobber_statuses


def test_json_roundtrip():
    e = Event("e1", "2026-11-14T10:00:00Z", photos=["photos/1.jpg"])
    e.detections.append(Detection("Parus major", 0.87, "Great Tit"))
    back = Event.from_json(e.to_json())
    assert back == e
    assert isinstance(back.detections[0], Detection)


def test_old_json_without_new_fields_loads():
    raw = json.dumps({
        "event_id": "old", "timestamp": "2026-11-13T08:00:00Z",
        "detections": [{"species": "Parus major", "confidence": 0.8}],
    })
    e = Event.from_json(raw)
    assert e.detections[0].common_name is None
    assert e.detections[0].t_offset_s == 0.0
    assert e.weather is None


def test_top_species():
    e = Event("e", "t", [Detection("Parus major", 0.6), Detection("Poecile montanus", 0.9)])
    assert e.top_species() == "Poecile montanus"
    assert Event("e", "t").top_species() is None


def test_endangered_mobbers_loaded_and_matched():
    mobbers = load_endangered_mobbers()
    assert "Poecile montanus" in mobbers
    e = Event("e1", "2026-11-14T10:00:00Z", [
        Detection("Parus major", 0.9, "Great Tit"),
        Detection("Poecile montanus", 0.82, "Willow Tit"),
    ])
    assert e.endangered_species(mobbers) == ["Poecile montanus"]


def test_every_mobber_has_threatened_status():
    mobbers = load_endangered_mobbers()
    statuses = load_mobber_statuses()
    assert set(statuses) == set(mobbers)
    assert set(statuses.values()) <= {"CR", "EN", "VU"}
    assert statuses["Poecile montanus"] == "EN"


def test_save_event_bundle_creates_folder_and_zip(tmp_path):
    import zipfile
    from bundle import save_event_bundle

    photo_file = tmp_path / "shot.jpg"
    photo_file.write_bytes(b"fake-jpeg-bytes")

    e = Event(
        "2026-11-14T12-00-00Z-abc123",
        "2026-11-14T12:00:00Z",
        detections=[Detection("Poecile montanus", 0.91, "Willow Tit")],
        photos=[str(photo_file)],
        weather={"temperature_c": 8.5, "humidity_rh": 74.0},
    )
    zip_path = save_event_bundle(e, bundle_dir=tmp_path / "captures")
    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        assert "metadata.json" in names
        assert "photo_01.jpg" in names
        meta = json.loads(zf.read("metadata.json").decode("utf-8"))
        assert meta["is_endangered"] is True
        assert meta["status"] == "EN"
        assert meta["weather"]["temperature_c"] == 8.5
