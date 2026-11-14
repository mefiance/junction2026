import csv
import json
import sys
from pathlib import Path

STATUS_CSV = Path("data/status.csv")
MOBBERS_JSON = Path("endangered_mobbers.json")


def main() -> None:
    statuses = {r["species"]: r["status"] for r in csv.DictReader(STATUS_CSV.open(encoding="utf-8"))}
    mobbers = json.loads(MOBBERS_JSON.read_text(encoding="utf-8"))
    missing = []
    for m in mobbers:
        status = statuses.get(m["scientific"])
        if status:
            m["status"] = status
        else:
            m.pop("status", None)
            missing.append(m["scientific"])
    lines = ",\n".join(f"  {{ {json.dumps(m, ensure_ascii=False)[1:-1]} }}" for m in mobbers)
    MOBBERS_JSON.write_text(f"[\n{lines}\n]\n", encoding="utf-8")
    print(f"{len(mobbers) - len(missing)}/{len(mobbers)} mobbers have a status")
    if missing:
        print("no status in data/status.csv:", ", ".join(missing))
        sys.exit(1)


if __name__ == "__main__":
    main()
