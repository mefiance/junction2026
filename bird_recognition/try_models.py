from models import Detection, Event

e = Event("e1", "2026-11-14T10:00:00Z", photos=["photos/1.jpg"])
e.detections.append(Detection("Parus major", 0.87, "Great Tit"))

raw = e.to_json()
print(raw)

back = Event.from_json(raw)
print(back == e)
print(type(back.detections[0]))
