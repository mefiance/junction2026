import numpy as np

from events import EventBuilder
from models import AUDIO, Detection
from pipeline import LivePipeline, replay
from store import Store


class ScriptedClassifier:
    def __init__(self, script):
        self.script = list(script)

    def classify(self, chunk, sr):
        species = self.script.pop(0)
        return [Detection(AUDIO, species, 0.9)] if species else []


def silent_chunks(n):
    return [(np.zeros(10, dtype=np.float32), 48000) for _ in range(n)]


def test_replay_splits_events_by_silence(tmp_path):
    script = ["Parus major", None, "Parus major"] + [None] * 5 + ["Cyanistes caeruleus"]
    store = Store(str(tmp_path / "t.db"))
    seen = []
    saved = replay(
        silent_chunks(len(script)), ScriptedClassifier(script),
        EventBuilder(window_s=9), store, on_event=seen.append,
    )
    assert saved == 2
    assert [e.top_species() for e in seen] == ["Parus major", "Cyanistes caeruleus"]
    assert [len(e.detections) for e in seen] == [2, 1]
    assert store.get(seen[0].event_id) == seen[0]
    store.close()


def test_live_pipeline_runs_to_end_of_source(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    seen = []
    clock = iter(range(0, 1000, 5))
    pipeline = LivePipeline(
        silent_chunks(2), ScriptedClassifier(["Parus major", None]),
        EventBuilder(window_s=1), store, on_event=seen.append, clock=lambda: next(clock),
    )
    pipeline.run()
    assert [e.top_species() for e in seen] == ["Parus major"]
    store.close()
