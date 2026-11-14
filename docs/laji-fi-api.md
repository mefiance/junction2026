# laji.fi API: access token and the Finnish bird Red List

How to get an access token for the FinBIF API (`api.laji.fi`) and download the list of Finnish bird species with their latest Finnish Red List (IUCN) status. The device uses this list offline to tag detections with a conservation status.

Verified against the live API on 2026-11-14. The ready-made script is [`tools/fetch_status.py`](../tools/fetch_status.py). It wrote 673 bird taxa, 315 of them with a Red List status (evaluation year 2019).

## 1. Get an access token

The token is tied to an email address and sent by email. Each team member requests their own.

```bash
curl -X POST "https://api.laji.fi/api-user" \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
```

- The token arrives in that inbox.
- Calling the endpoint again sends a new token. Old tokens keep working.
- `https://apitest.laji.fi` is a separate test service with its own tokens. Use production (`api.laji.fi`) for real data.

Keep the token out of git. Either export it:

```bash
export LAJI_TOKEN="paste-token-here"
```

or put it in `.env` in the repo root (already in `.gitignore`):

```
LAJI_KEY=paste-token-here
```

## 2. Authenticate requests

Without a token every call returns `{"errorCode": "ACCESS_TOKEN_MISSING"}`.

| Header | Value |
|---|---|
| `Authorization` | `Bearer $LAJI_TOKEN` |
| `API-Version` | `1`. **Required.** Without it the API returns `401 AUTHORIZATION_REQUIRED` even with a valid token. |
| `Accept-Language` | `en` (or `fi`, `sv`). Sets the language of names in the response. |

The `?access_token=` query parameter mentioned in older docs did not work in testing. Use the header.

Quick check:

```bash
curl -s "https://api.laji.fi/taxa/MX.37580" \
  -H "Authorization: Bearer $LAJI_TOKEN" -H "API-Version: 1" -H "Accept-Language: en"
```

`MX.37580` is the FinBIF taxon id for **Aves** (birds). The response should contain `"scientificName": "Aves"`.

## 3. Download the dataset

Endpoint: `POST /taxa/{id}/species` returns species and subspecies under a taxon. It is paginated.

| Query parameter | Value | Meaning |
|---|---|---|
| `finnish` | `true` | only taxa that occur in Finland |
| `selectedFields` | `id,scientificName,vernacularName,latestRedListStatusFinland` | trim the response |
| `pageSize` | `1000` | results per page |
| `page` | `1`, `2`, … | page number |

```bash
curl -s -X POST \
  "https://api.laji.fi/taxa/MX.37580/species?finnish=true&selectedFields=id,scientificName,vernacularName,latestRedListStatusFinland&pageSize=1000&page=1" \
  -H "Authorization: Bearer $LAJI_TOKEN" -H "API-Version: 1" -H "Accept-Language: en" \
  -H "Content-Type: application/json" -d '{}'
```

Response shape (per spec):

```json
{
  "currentPage": 1,
  "lastPage": 1,
  "total": 500,
  "results": [
    {
      "id": "MX.xxxxx",
      "scientificName": "Poecile montanus",
      "vernacularName": "Willow Tit",
      "latestRedListStatusFinland": {"status": "MX.iucnEN", "year": 2019}
    }
  ]
}
```

Species that were never evaluated have no `latestRedListStatusFinland` field.

### Status codes

Strip the `MX.iucn` prefix to get the standard IUCN code.

| API value | Code | Meaning |
|---|---|---|
| `MX.iucnEX` | EX | Extinct |
| `MX.iucnEW` | EW | Extinct in the wild |
| `MX.iucnRE` | RE | Regionally extinct (in Finland) |
| `MX.iucnCR` | CR | Critically endangered |
| `MX.iucnEN` | EN | Endangered |
| `MX.iucnVU` | VU | Vulnerable |
| `MX.iucnNT` | NT | Near threatened |
| `MX.iucnLC` | LC | Least concern |
| `MX.iucnDD` | DD | Data deficient |
| `MX.iucnNA` | NA | Not applicable (for example, a vagrant species) |
| `MX.iucnNE` | NE | Not evaluated |

## 4. Build `data/status.csv`

Run on a machine with internet access, from the repo root:

```bash
.venv/bin/python tools/fetch_status.py
```

The script reads the token from `LAJI_TOKEN` or `.env`, downloads all pages and writes `data/status.csv`:

```
species,common_name,status,year
Parus major,Great Tit,LC,2019
Poecile montanus,Willow Tit,EN,2019
Glaucidium passerinum,Eurasian Pygmy Owl,VU,2019
```

- **macOS with Python from python.org:** plain `urllib` fails with `CERTIFICATE_VERIFY_FAILED`, because that Python ships without system root certificates. The script uses the `certifi` bundle, which is installed with `birdnet`. The alternative is to run `Install Certificates.command` from the Python folder in Applications.
- **Names are rewritten to BirdNET's taxonomy.** FinBIF uses newer names for five species. The script maps them (`BIRDNET_NAMES`): `Astur gentilis` → `Accipiter gentilis`, `Coloeus monedula` → `Corvus monedula`, `Eudromias morinellus` → `Charadrius morinellus`, `Thinornis dubius` → `Charadrius dubius`, `Corvus corone cornix` → `Corvus cornix`. All other unmatched names are subspecies, and BirdNET does not output those anyway.

## 5. How the device uses it

The device does not read `data/status.csv` directly. The lure targets are the 24 mobbing species in `endangered_mobbers.json`, and each entry carries its Red List code:

```json
{ "english": "Willow Tit", "scientific": "Poecile montanus", "status": "EN" }
```

- `tools/enrich_mobbers.py` copies the codes from `data/status.csv` into `endangered_mobbers.json`. It fails if a mobber has no status.
- Today all 24 mobbers are threatened: 2 CR, 9 EN, 13 VU.
- `models.load_mobber_statuses()` returns `{scientific name: code}`. `bundle.py` writes the code to `metadata.json` as `"status"`, and the live log shows it as `[ENDANGERED EN]`.
- The code is stored at the time of the observation. The Red List is re-evaluated every few years.

## 6. Refresh

About every 6 months, from the repo root:

```bash
.venv/bin/python tools/fetch_status.py
.venv/bin/python tools/enrich_mobbers.py
```

Commit both `data/status.csv` and `endangered_mobbers.json`, then sync to the board (`sync-to-board.sh` already pushes `endangered_mobbers.json`). Don't rely on a scheduled GitHub Actions workflow for this. In public repositories, GitHub disables scheduled workflows after 60 days without repository activity.

## 7. License and attribution

- FinBIF distributes its open data under **CC BY 4.0** by default ([user access licenses](https://info.laji.fi/en/frontpage/datasets-and-their-use/user-access-licenses/)). Attribution is required in publications and presentations ([citing FinBIF](https://info.laji.fi/en/frontpage/mission/citing-and-acknowledging-finbif/)).
- The license for the taxonomy and Red List data specifically is not stated separately. Check it before publishing on Arduino Project Hub.
- Suggested credit: *Red List status: Finnish Biodiversity Information Facility (FinBIF), laji.fi, Red List of Finnish Species 2019, CC BY 4.0.*

## Links

- API spec (Swagger): <https://api.laji.fi/openapi>
- API overview: <https://info.laji.fi/en/frontpage/api/api-laji-fi/>
- Taxonomy API notes: <https://info.laji.fi/en/frontpage/api/api-laji-fi/taxonomy-api/>
- Red List web service: <https://punainenkirja.laji.fi/en>
