# NYC Tennis & Padel Finder

An interactive web app to find tennis and padel courts across all five NYC boroughs — with filters, drive-time estimates, and Google Maps directions.

**Live site:** https://gal766020-source.github.io/NYC-Tennis-Padel-Courts/

---

## What it does

- Shows 34+ verified tennis and padel courts on an interactive map
- Filter by **sport**, **borough**, **surface**, **access type**, and **indoor/outdoor**
- **Drive-time filter** — enter your address or use your location to see courts within 10–30 min
- **Search** by court name
- **Get Directions** button on each court opens Google Maps
- Fully **mobile responsive**
- Court data loaded from `courts_data.json`, auto-refreshed weekly via GitHub Actions

---

## How the data pipeline works

```
fetch_courts.py  →  courts_data.json  →  index.html (web app)
      ↑
GitHub Actions runs this every Monday at 6am UTC
```

1. `fetch_courts.py` tries to pull live court data from the **OpenStreetMap Overpass API**
2. If the API is unavailable, it falls back to a curated verified dataset
3. The cleaned output is saved to `courts_data.json`
4. The web app reads `courts_data.json` on load — no hardcoded data

---

## Tech stack

| Layer | Tool |
|---|---|
| Frontend | HTML, CSS, Vanilla JavaScript |
| Maps | [Leaflet.js](https://leafletjs.com/) + OpenStreetMap tiles |
| Geocoding | [Nominatim](https://nominatim.org/) (free, no API key needed) |
| Data source | [OpenStreetMap Overpass API](https://overpass-api.de/) |
| Hosting | GitHub Pages |
| CI/CD | GitHub Actions (weekly data refresh) |
| Data pipeline | Python 3 (`fetch_courts.py`) |

---

## Run locally

```bash
# Clone the repo
git clone https://github.com/gal766020-source/NYC-Tennis-Padel-Courts.git
cd NYC-Tennis-Padel-Courts

# Refresh court data manually
python3 fetch_courts.py

# Open the app (no server needed — just open in browser)
open index.html
```

---

## Refresh court data manually

```bash
python3 fetch_courts.py
```

This will:
- Try the live OpenStreetMap API
- Fall back to curated data if API is unavailable
- Save results to `courts_data.json` with a timestamp

---

## Data sources & verification

| Court type | Source |
|---|---|
| NYC Parks tennis courts | OpenStreetMap + NYC Parks Dept verification |
| Major tennis clubs | Verified against venue websites |
| Padel courts | Manually verified (Brooklyn Bridge Park, Manhattan Padel Club confirmed) |

Courts marked ⚠️ in the app popup need re-confirmation as padel is new to NYC and not yet in official datasets.

---

## Project structure

```
nyc-courts-app/
├── index.html          # Web app (UI + map logic)
├── fetch_courts.py     # Data pipeline script
├── courts_data.json    # Generated court data (do not edit manually)
├── README.md           # This file
└── .github/
    └── workflows/
        └── update_courts.yml  # GitHub Actions — weekly data refresh
```

---

## Built by

Gal Gutman — built on personal time to practice automation engineering, data pipelines, and modern deployment workflows using Claude Code as an AI pair programmer.
