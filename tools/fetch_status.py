import csv
import json
import os
import re
import ssl
import sys
import urllib.request
from pathlib import Path

import certifi

API = "https://api.laji.fi"
AVES = "MX.37580"
FIELDS = "id,scientificName,vernacularName,latestRedListStatusFinland"
OUT = Path("data/status.csv")
BIRDNET_NAMES = {
    "Astur gentilis": "Accipiter gentilis",
    "Coloeus monedula": "Corvus monedula",
    "Eudromias morinellus": "Charadrius morinellus",
    "Thinornis dubius": "Charadrius dubius",
    "Corvus corone cornix": "Corvus cornix",
}


def read_token(env_path: Path = Path(".env")) -> str:
    if os.environ.get("LAJI_TOKEN"):
        return os.environ["LAJI_TOKEN"]
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            m = re.match(r"\s*(?:export\s+)?LAJI_(?:KEY|TOKEN)\s*[:=]\s*['\"]?([^'\"\s]+)", line)
            if m:
                return m.group(1)
    sys.exit("set LAJI_TOKEN or put LAJI_KEY=... into .env")


def fetch_page(token: str, page: int, ctx: ssl.SSLContext) -> dict:
    url = (f"{API}/taxa/{AVES}/species?finnish=true&selectedFields={FIELDS}"
           f"&pageSize=1000&page={page}")
    req = urllib.request.Request(url, data=b"{}", method="POST", headers={
        "Authorization": f"Bearer {token}",
        "API-Version": "1",
        "Accept-Language": "en",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
        return json.load(resp)


def to_row(taxon: dict) -> dict:
    status = taxon.get("latestRedListStatusFinland") or {}
    return {
        "species": BIRDNET_NAMES.get(taxon["scientificName"], taxon["scientificName"]),
        "common_name": taxon.get("vernacularName") or "",
        "status": status.get("status", "").removeprefix("MX.iucn"),
        "year": status.get("year", ""),
    }


def main() -> None:
    token = read_token()
    ctx = ssl.create_default_context(cafile=certifi.where())
    rows, page = [], 1
    while True:
        data = fetch_page(token, page, ctx)
        rows.extend(to_row(t) for t in data["results"])
        if page >= data.get("lastPage", page):
            break
        page += 1
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["species", "common_name", "status", "year"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} taxa written to {OUT}")


if __name__ == "__main__":
    main()
