"""
Packages each finished Event into a folder and a `.zip` file (`captures/<event_id>.zip`)
containing `metadata.json` + all burst photos, and provides `UnoQHardware` to call
the Arduino UNO Q sketch (Modulino Thermo & Buzzer) over Bridge.
"""

import json
import shutil
import zipfile
from pathlib import Path

from models import Event, load_endangered_mobbers


def save_event_bundle(
    event: Event,
    bundle_dir: str | Path = "captures",
    mobbers: dict[str, str] | None = None,
) -> Path:
    """Save an Event's metadata.json and photos into a folder and a .zip archive."""
    root = Path(bundle_dir)
    root.mkdir(parents=True, exist_ok=True)

    species_slug = (event.top_species() or "lure_burst").replace(" ", "_")
    folder_name = f"{event.event_id}_{species_slug}"
    event_dir = root / folder_name
    event_dir.mkdir(parents=True, exist_ok=True)

    lookup = load_endangered_mobbers() if mobbers is None else mobbers

    copied_photos: list[str] = []
    for idx, photo_path in enumerate(event.photos, start=1):
        src = Path(photo_path)
        if src.is_file():
            dst_name = f"photo_{idx:02d}{src.suffix or '.jpg'}"
            dst = event_dir / dst_name
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            copied_photos.append(dst_name)

    top_det = max(event.detections, key=lambda d: d.confidence) if event.detections else None
    species = top_det.species if top_det else None
    common_name = (top_det.common_name if top_det else None) or (lookup.get(species) if species else None)

    payload = {
        "timestamp": event.timestamp,
        "location": event.location,
        "species": species,
        "common_name": common_name,
        "confidence": top_det.confidence if top_det else None,
        "is_endangered": bool(species and species in lookup),
        "weather": event.weather,
    }

    meta_path = event_dir / "metadata.json"
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    zip_path = root / f"{folder_name}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(meta_path, arcname="metadata.json")
        for photo_name in copied_photos:
            p = event_dir / photo_name
            if p.is_file():
                zf.write(p, arcname=photo_name)

    return zip_path


class UnoQHardware:
    """Interfaces with the Arduino UNO Q STM32 sketch (Modulino Thermo + Buzzer) via Bridge."""

    def __init__(self, bridge=None, playback_flag: Path | None = None):
        self.playback_flag = playback_flag
        if bridge is not None:
            self.bridge = bridge
        else:
            try:
                from arduino.app_utils import Bridge
                self.bridge = Bridge
            except Exception:
                self.bridge = None

    def read_weather(self) -> dict | None:
        if self.bridge is None:
            return None
        try:
            temp = float(self.bridge.call("get_temperature", timeout=2))
            hum = float(self.bridge.call("get_humidity", timeout=2))
            return {"temperature_c": round(temp, 2), "humidity_rh": round(hum, 2)}
        except Exception:
            return None

    def play_owl_lure(self, notes: int = 3) -> bool:
        """Trigger the Pygmy Owl whistle on the Modulino Buzzer and manage the playback mask flag."""
        if self.playback_flag is not None:
            self.playback_flag.touch()
        try:
            if self.bridge is None:
                return False
            # Each whistle note + pause takes ~2.2s on the MCU; allow generous timeout
            timeout = max(5.0, notes * 2.6 + 3.0)
            res = self.bridge.call("play_owl_bout", int(notes), timeout=timeout)
            return bool(res)
        except Exception:
            return False
        finally:
            if self.playback_flag is not None:
                self.playback_flag.unlink(missing_ok=True)
