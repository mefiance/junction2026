from events import OWL, EventBuilder
from models import Detection


def tit(conf=0.9, species="Parus major"):
    return [Detection(species, conf)]


def test_low_and_equal_confidence_ignored():
    b = EventBuilder(window_s=10, min_confidence=0.5)
    assert b.on_audio(tit(0.4), now=0) is False
    assert b.on_audio(tit(0.5), now=0) is False
    assert not b.camera_active(0)


def test_window_extends_and_closes():
    b = EventBuilder(window_s=10, min_confidence=0.5)
    assert b.on_audio(tit(), now=0)
    assert b.camera_active(5)
    assert b.tick(5) is None
    b.on_audio(tit(0.7, "Cyanistes caeruleus"), now=8)
    assert b.tick(15) is None
    event = b.tick(18)
    assert event.top_species() == "Parus major"
    assert [d.t_offset_s for d in event.detections] == [0.0, 8.0]
    assert b.tick(19) is None


def test_late_audio_without_tick_starts_new_event():
    b = EventBuilder(window_s=10, min_confidence=0.5)
    b.on_audio(tit(), now=0)
    b.on_audio(tit(0.7, "Cyanistes caeruleus"), now=19)
    first = b.tick(20)
    assert first.top_species() == "Parus major"
    assert b.tick(28) is None
    second = b.tick(29)
    assert second.top_species() == "Cyanistes caeruleus"
    assert second.detections[0].t_offset_s == 0.0


def test_owl_masked_during_playback_and_after():
    b = EventBuilder(window_s=10, min_confidence=0.5, owl_mask_s=3)
    b.on_playback(True, now=0)
    assert b.on_audio(tit(0.95, OWL), now=1) is False
    b.on_playback(False, now=2)
    assert b.on_audio(tit(0.95, OWL), now=4) is False
    assert b.on_audio(tit(0.95, OWL), now=6) is True


def test_event_records_playback():
    b = EventBuilder(window_s=10, min_confidence=0.5)
    b.on_playback(True, now=0)
    b.on_audio(tit(), now=1)
    event = b.tick(11)
    assert event.playback["species"] == OWL


def test_burst_camera_takes_2fps_for_5s_and_attaches_weather(tmp_path):
    from vision import BurstCamera

    class FakeSource:
        def grab(self):
            pass

        def read(self):
            return b"frame"

        def close(self):
            pass

    class TestBurstCamera(BurstCamera):
        def save_photo(self, frame, event_id: str, index: int) -> str:
            p = self.photo_dir / f"{event_id}_{index:02d}.jpg"
            self.photo_dir.mkdir(parents=True, exist_ok=True)
            p.write_bytes(frame)
            return str(p)

    b = EventBuilder(
        window_s=10,
        min_confidence=0.5,
        weather_fn=lambda: {"temperature_c": 11.2, "humidity_rh": 68.0},
        mobbers={"Poecile montanus": "Willow Tit"},
    )
    cam = TestBurstCamera(FakeSource(), photo_dir=str(tmp_path), fps=2.0, duration_s=5.0)

    # Common bird heard -> logged, but camera stays OFF
    b.on_audio(tit(0.9, "Parus major"), now=0.0)
    assert not b.camera_active(0.0)

    # Endangered mobber heard -> camera turns ON and takes 2 fps * 5s = 10 photos
    b.on_audio(tit(0.9, "Poecile montanus"), now=1.0)
    assert b.camera_active(1.0)
    t = 1.0
    while t <= 7.0:
        cam.step(b, now=t)
        t += 0.25

    event = b.tick(12.0)
    assert event is not None
    assert event.weather == {"temperature_c": 11.2, "humidity_rh": 68.0}
    assert len(event.photos) == 10
