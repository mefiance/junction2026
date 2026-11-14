from datetime import datetime, timezone
from pathlib import Path

from events import EventBuilder

BIRD_CLASS = 14


class CvSource:
    def __init__(self, index: int | str = 0, width: int = 640, height: int = 480):
        import cv2
        self.cap = cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not self.cap.isOpened():
            raise RuntimeError(f"camera {index} not available")

    def grab(self) -> None:
        self.cap.grab()

    def read(self):
        ok, frame = self.cap.read()
        return frame if ok else None

    def close(self) -> None:
        self.cap.release()


class YoloDetector:
    def __init__(self, weights: str = "yolo11n.pt", imgsz: int = 320, min_confidence: float = 0.4):
        from ultralytics import YOLO
        self.model = YOLO(weights)
        self.imgsz = imgsz
        self.min_confidence = min_confidence

    def detect(self, frame) -> list[float]:
        result = self.model.predict(
            frame, imgsz=self.imgsz, classes=[BIRD_CLASS],
            conf=self.min_confidence, verbose=False,
        )[0]
        return [float(c) for c in result.boxes.conf]


class Camera:
    def __init__(self, source, detector, photo_dir: str = "photos"):
        self.source = source
        self.detector = detector
        self.photo_dir = Path(photo_dir)

    def idle(self) -> None:
        self.source.grab()

    def step(self, builder: EventBuilder, now: float) -> None:
        frame = self.source.read()
        if frame is None:
            return
        confidences = self.detector.detect(frame)
        builder.on_frame(confidences, now, lambda: self.save_photo(frame))

    def save_photo(self, frame) -> str:
        import cv2
        self.photo_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%fZ")
        path = self.photo_dir / f"{stamp}.jpg"
        cv2.imwrite(str(path), frame)
        return str(path)

    def close(self) -> None:
        self.source.close()
