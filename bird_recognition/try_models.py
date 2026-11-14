from models import Detection, Event

e = Event("e1", "2026-11-14T10:00:00Z")
e.detections.append(Detection("audio", "Parus major", 0.87))
e.detections.append(Detection("video", "bird", 0.71, photo="photos/1.jpg"))
e.max_count = 2

raw = e.to_json()
print(raw)

back = Event.from_json(raw)
print(back == e)
print(type(back.detections[0]))