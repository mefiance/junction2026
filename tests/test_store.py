import pytest

from models import AUDIO, Detection, Event
from store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path / "test.db"))
    yield s
    s.close()


def audio_event(event_id, ts, species, count):
    return Event(event_id, ts, [Detection(AUDIO, species, 0.8)], count)


def test_save_and_get(store):
    e = audio_event("a", "2026-11-14T08:00:00Z", "Parus major", 2)
    store.save(e)
    assert store.get("a") == e
    assert store.get("missing") is None


def test_daily_summary(store):
    store.save(audio_event("a", "2026-11-14T08:00:00Z", "Parus major", 2))
    store.save(audio_event("b", "2026-11-14T09:00:00Z", "Parus major", 3))
    store.save(audio_event("c", "2026-11-14T09:30:00Z", "Cyanistes caeruleus", 1))
    store.save(audio_event("d", "2026-11-15T10:00:00Z", "Parus major", 9))
    assert store.daily_summary("2026-11-14") == [
        {"species": "Parus major", "events": 2, "birds_seen": 5},
        {"species": "Cyanistes caeruleus", "events": 1, "birds_seen": 1},
    ]


def test_events_on_sorted_by_time(store):
    store.save(audio_event("late", "2026-11-14T12:00:00Z", "Parus major", 1))
    store.save(audio_event("early", "2026-11-14T07:00:00Z", "Parus major", 1))
    store.save(audio_event("other", "2026-11-15T07:00:00Z", "Parus major", 1))
    assert [e.event_id for e in store.events_on("2026-11-14")] == ["early", "late"]
