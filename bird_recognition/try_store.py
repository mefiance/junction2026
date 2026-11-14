from models import Detection, Event
from store import Store

store = Store("test.db")

e1 = Event("a", "2026-11-14T08:00:00Z", [Detection("audio", "Parus major", 0.8)], 2)
e2 = Event("b", "2026-11-14T09:00:00Z", [Detection("audio", "Parus major", 0.9)], 3)
e3 = Event("c", "2026-11-14T09:30:00Z", [Detection("audio", "Cyanistes caeruleus", 0.7)], 1)
e4 = Event("d", "2026-11-15T10:00:00Z", [Detection("audio", "Parus major", 0.9)], 9)

store.save(e1)
store.save(e2)
store.save(e3)
store.save(e4)

print(store.get("a"))
print(store.daily_summary("2026-11-14"))