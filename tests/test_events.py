from events import OWL, EventBuilder
from models import AUDIO, Detection


def tit(conf=0.9, species="Parus major"):
    return [Detection(AUDIO, species, conf)]


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


def test_frames_count_max_and_throttle_photos():
    b = EventBuilder(window_s=10, min_confidence=0.5, photo_interval_s=2)
    photos = iter(f"p{i}.jpg" for i in range(10))
    b.on_frame([0.9], now=0, save_photo=lambda: next(photos))
    b.on_audio(tit(), now=0)
    b.on_frame([0.8], now=1, save_photo=lambda: next(photos))
    b.on_frame([0.8, 0.7, 0.6], now=2, save_photo=lambda: next(photos))
    b.on_frame([0.8, 0.7], now=3.5, save_photo=lambda: next(photos))
    b.on_frame([], now=4, save_photo=lambda: next(photos))
    event = b.tick(10)
    assert event.max_count == 3
    assert [d.photo for d in event.detections if d.photo] == ["p0.jpg", "p1.jpg"]


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
