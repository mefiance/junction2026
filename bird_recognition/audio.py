"""
Audio input streams (microphone or WAV file) and BirdNET v2.4 LiteRT classifier.
Splits incoming audio into 3-second chunks and filters BirdNET species predictions
by location (lat/lon) and current week of the year.
"""

import time
from collections.abc import Iterator
from datetime import date

import numpy as np

from models import Detection

SAMPLE_RATE = 48000
CHUNK_S = 3.0

Chunk = tuple[np.ndarray, int]


def parse_label(label: str) -> tuple[str, str | None]:
    scientific, _, common = label.partition("_")
    return scientific, common or None


def week_48(day: date) -> int:
    return (day.month - 1) * 4 + min((day.day - 1) // 7, 3) + 1


def split_chunks(mono: np.ndarray, sr: int) -> Iterator[Chunk]:
    step = int(CHUNK_S * sr)
    for start in range(0, len(mono), step):
        chunk = mono[start:start + step]
        if len(chunk) < step:
            chunk = np.pad(chunk, (0, step - len(chunk)))
        yield chunk.astype(np.float32), sr


class FileSource:
    def __init__(self, path: str, realtime: bool = False):
        self.path = path
        self.realtime = realtime

    def __iter__(self) -> Iterator[Chunk]:
        import soundfile as sf
        audio, sr = sf.read(self.path, dtype="float32", always_2d=True)
        for chunk in split_chunks(audio.mean(axis=1), sr):
            if self.realtime:
                time.sleep(CHUNK_S)
            yield chunk


class MicSource:
    def __init__(self, device: int | str | None = None, sample_rate: int = SAMPLE_RATE):
        self.device = device
        self.sample_rate = sample_rate

    def __iter__(self) -> Iterator[Chunk]:
        import sounddevice as sd
        frames = int(CHUNK_S * self.sample_rate)
        with sd.InputStream(
            samplerate=self.sample_rate, channels=1, dtype="float32",
            device=self.device, blocksize=frames,
        ) as stream:
            while True:
                data, _ = stream.read(frames)
                yield data[:, 0].copy(), self.sample_rate


class BirdNetClassifier:
    def __init__(
        self,
        lat: float | None = None,
        lon: float | None = None,
        day: date | None = None,
        min_confidence: float = 0.5,
        top_k: int = 3,
    ):
        import birdnet
        model = birdnet.load("acoustic", "2.4", "tf", library="litert")
        species = None
        if lat is not None and lon is not None:
            geo = birdnet.load("geo", "2.4", "tf", library="litert")
            week = week_48(day or date.today())
            species = geo.predict(lat, lon, week=week).to_set()
        self.session = model.predict_session(
            top_k=top_k,
            default_confidence_threshold=min_confidence,
            custom_species_list=species,
        )
        self.session.__enter__()

    def classify(self, chunk: np.ndarray, sr: int) -> list[Detection]:
        rows = self.session.run_arrays((chunk, sr)).to_structured_array()
        out = []
        for row in rows:
            scientific, common = parse_label(str(row["species_name"]))
            out.append(Detection(scientific, round(float(row["confidence"]), 3), common))
        return out

    def close(self) -> None:
        self.session.__exit__(None, None, None)
