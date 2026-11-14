from events import EventBuilder
from models import Detection

b = EventBuilder(window_s=10, min_confidence=0.6)
b.on_audio([Detection("audio", "Parus major", 0.9)], now=0)
b.on_audio([Detection("audio", "Cyanistes caeruleus", 0.7)], now=12)

first = b.tick(15)
print(first.top_species(), len(first.detections))
print(b.tick(18))
second = b.tick(22)
print(second.top_species(), len(second.detections))
print(b.tick(23))