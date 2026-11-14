"""
SQLite storage (`birds.db`) for saving and querying detected bird Events
and generating daily species summaries.
"""

import sqlite3

from models import Event


class Store:
    def __init__(self, path: str = "birds.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            species TEXT,
            photos_count INTEGER,
            payload TEXT NOT NULL)""")
        self.db.commit()

    def save(self, event: Event) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO events VALUES (?, ?, ?, ?, ?)",
            (event.event_id, event.timestamp, event.top_species(), len(event.photos), event.to_json()),
        )
        self.db.commit()

    def get(self, event_id: str) -> Event | None:
        row = self.db.execute(
            "SELECT payload FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return Event.from_json(row[0]) if row else None

    def events_on(self, day: str) -> list[Event]:
        rows = self.db.execute(
            "SELECT payload FROM events WHERE timestamp LIKE ? ORDER BY timestamp",
            (f"{day}%",),
        ).fetchall()
        return [Event.from_json(r[0]) for r in rows]

    def daily_summary(self, day: str) -> list[dict]:
        rows = self.db.execute(
            """SELECT species, COUNT(*) FROM events
               WHERE timestamp LIKE ? GROUP BY species ORDER BY COUNT(*) DESC""",
            (f"{day}%",),
        ).fetchall()
        return [{"species": s, "events": n} for s, n in rows]

    def close(self) -> None:
        self.db.close()
