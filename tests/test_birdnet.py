import time

import numpy as np
import pytest

pytestmark = pytest.mark.birdnet


def test_birdnet_runs_on_silence_fast_enough():
    pytest.importorskip("birdnet")
    from audio import BirdNetClassifier, CHUNK_S, SAMPLE_RATE
    classifier = BirdNetClassifier(min_confidence=0.5)
    chunk = np.zeros(int(CHUNK_S * SAMPLE_RATE), dtype=np.float32)
    classifier.classify(chunk, SAMPLE_RATE)
    start = time.monotonic()
    detections = classifier.classify(chunk, SAMPLE_RATE)
    elapsed = time.monotonic() - start
    classifier.close()
    print(f"one 3 s chunk: {elapsed:.3f} s")
    assert detections == []
    assert elapsed < CHUNK_S
