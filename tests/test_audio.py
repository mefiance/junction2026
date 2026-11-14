from datetime import date

import numpy as np
import pytest

from audio import CHUNK_S, FileSource, parse_label, split_chunks, week_48


def test_parse_label():
    assert parse_label("Parus major_Great Tit") == ("Parus major", "Great Tit")
    assert parse_label("Glaucidium passerinum_Eurasian Pygmy-Owl") == ("Glaucidium passerinum", "Eurasian Pygmy-Owl")
    assert parse_label("Noise") == ("Noise", None)


def test_week_48():
    assert week_48(date(2026, 1, 1)) == 1
    assert week_48(date(2026, 1, 31)) == 4
    assert week_48(date(2026, 11, 14)) == 42
    assert week_48(date(2026, 12, 31)) == 48


def test_split_chunks_pads_tail():
    sr = 48000
    chunks = list(split_chunks(np.ones(int(sr * 7)), sr))
    assert len(chunks) == 3
    assert all(len(c) == int(CHUNK_S * sr) for c, _ in chunks)
    assert chunks[-1][0][-1] == 0.0


def test_file_source_mono(tmp_path):
    sf = pytest.importorskip("soundfile")
    sr = 48000
    stereo = np.zeros((sr * 6, 2), dtype=np.float32)
    path = tmp_path / "x.wav"
    sf.write(path, stereo, sr)
    chunks = list(FileSource(str(path)))
    assert len(chunks) == 2
    assert chunks[0][0].ndim == 1
    assert chunks[0][1] == sr
