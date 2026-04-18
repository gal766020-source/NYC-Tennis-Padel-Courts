"""
fetch_courts.py
---------------
Fetches NYC tennis & padel court data from two live APIs:
  1. NYC Open Data — official NYC Parks athletic facilities (tennis courts)
  2. Geoapify Places API — padel courts + private clubs not in NYC Parks data
Falls back to FALLBACK_COURTS curated dataset if both APIs are unavailable.

Data sources:
  NYC Open Data: data.cityofnewyork.us (no API key needed)
  Geoapify:      geoapify.com (API key required)
Run manually:  python3 fetch_courts.py
Run via CI/CD: GitHub Actions (.github/workflows/update_courts.yml)
"""

import json
import urllib.request
import urllib.parse
import os
from datetime import datetime, timezone

OUTPUT_FILE = "courts_data.json"
GEOAPIFY_API_KEY = "5f7b18b93f6e4d02b0ea3ceabe6db9b4"

# Borough search centers: (name, lng, lat, radius_meters)
BOROUGH_CENTERS = [
    ("Manhattan",     -73.9857, 40.7580, 8000),
    ("Brooklyn",      -73.9442, 40.6501, 10000),
    ("Queens",        -73.8448, 40.7282, 12000),
    ("Bronx",         -73.8648, 40.8448, 10000),
    ("Staten Island", -74.1502, 40.5795, 10000),
]

SURFACE_MAP = {
    "asphalt": "hard", "concrete": "hard", "hard": "hard", "acrylic": "hard",
    "synthetic": "hard", "artificial_turf": "hard",
    "clay": "clay", "en tout cas": "clay", "red clay": "clay",
    "grass": "grass", "artificial_grass": "grass",
}

# ── Fallback curated data (used when API is unavailable) ─────────────────────
FALLBACK_COURTS = [
    # MANHATTAN
    {"id":1,"name":"Central Park Tennis Center","sport":"tennis","location":"outdoor","surface":"clay","access":"permit","address":"Central Park, near W 93rd St, New York, NY 10024","lat":40.7859,"lng":-73.9591,"borough":"Manhattan","courts":30,"verified":True},
    {"id":2,"name":"Riverside Park Tennis Courts","sport":"tennis","location":"outdoor","surface":"hard","access":"permit","address":"Riverside Park, 97th St, New York, NY 10025","lat":40.7933,"lng":-73.9745,"borough":"Manhattan","courts":10,"verified":True},
    {"id":3,"name":"Sutton East Tennis Club","sport":"tennis","location":"indoor","surface":"hard","access":"free","address":"488 E 60th St, New York, NY 10022","lat":40.7605,"lng":-73.9556,"borough":"Manhattan","courts":8,"verified":True},
    {"id":4,"name":"Crosstown Tennis","sport":"tennis","location":"indoor","surface":"hard","access":"free","address":"14 W 31st St, New York, NY 10001","lat":40.7477,"lng":-73.9893,"borough":"Manhattan","courts":6,"verified":True},
    {"id":5,"name":"Hudson River Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"permit","address":"Pier 40, West St & W Houston St, New York, NY 10014","lat":40.7282,"lng":-74.0115,"borough":"Manhattan","courts":4,"verified":True},
    {"id":6,"name":"Manhattan Padel Club","sport":"padel","location":"indoor","surface":"hard","access":"free","address":"450 W 43rd St, New York, NY 10036","lat":40.7596,"lng":-73.9967,"borough":"Manhattan","courts":4,"verified":True},
    {"id":7,"name":"Inwood Hill Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"Inwood Hill Park, Seaman Ave, New York, NY 10034","lat":40.8675,"lng":-73.9276,"borough":"Manhattan","courts":6,"verified":True},
    {"id":8,"name":"Carl Schurz Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"permit","address":"E 84th St & East End Ave, New York, NY 10028","lat":40.7759,"lng":-73.9420,"borough":"Manhattan","courts":4,"verified":True},
    {"id":9,"name":"Morningside Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"Morningside Ave & W 120th St, New York, NY 10027","lat":40.8091,"lng":-73.9578,"borough":"Manhattan","courts":3,"verified":True},
    {"id":10,"name":"East River Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"East River Park, Delancey St, New York, NY 10002","lat":40.7153,"lng":-73.9742,"borough":"Manhattan","courts":8,"verified":True},
    # BROOKLYN
    {"id":11,"name":"Prospect Park Tennis Center","sport":"tennis","location":"outdoor","surface":"clay","access":"permit","address":"Prospect Park, East Dr, Brooklyn, NY 11215","lat":40.6620,"lng":-73.9707,"borough":"Brooklyn","courts":12,"verified":True},
    {"id":12,"name":"McCarren Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"776 Lorimer St, Brooklyn, NY 11222","lat":40.7205,"lng":-73.9536,"borough":"Brooklyn","courts":8,"verified":True},
    {"id":13,"name":"Marine Park Tennis Courts","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"3302 Bedford Ave, Brooklyn, NY 11210","lat":40.5960,"lng":-73.9219,"borough":"Brooklyn","courts":6,"verified":True},
    {"id":14,"name":"Owl's Head Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"permit","address":"Colonial Rd & Shore Rd, Brooklyn, NY 11209","lat":40.6357,"lng":-74.0198,"borough":"Brooklyn","courts":4,"verified":True},
    {"id":15,"name":"Brooklyn Bridge Park Padel","sport":"padel","location":"outdoor","surface":"hard","access":"free","address":"Pier 2, Brooklyn Bridge Park, Brooklyn, NY 11201","lat":40.6963,"lng":-73.9980,"borough":"Brooklyn","courts":2,"verified":True},
    {"id":16,"name":"Canarsie Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"Flatbush Ave & Rockaway Pkwy, Brooklyn, NY 11236","lat":40.6306,"lng":-73.9017,"borough":"Brooklyn","courts":5,"verified":True},
    {"id":17,"name":"Betsy Head Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"Livonia Ave & Strauss St, Brooklyn, NY 11212","lat":40.6706,"lng":-73.9030,"borough":"Brooklyn","courts":4,"verified":True},
    {"id":18,"name":"Fort Greene Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"Washington Park, Fort Greene, Brooklyn, NY 11205","lat":40.6898,"lng":-73.9745,"borough":"Brooklyn","courts":2,"verified":True},
    # QUEENS
    {"id":19,"name":"USTA Billie Jean King National Tennis Center","sport":"tennis","location":"outdoor","surface":"hard","access":"permit","address":"Flushing Meadows–Corona Park, Queens, NY 11368","lat":40.7519,"lng":-73.8467,"borough":"Queens","courts":22,"verified":True},
    {"id":20,"name":"Forest Park Tennis Courts","sport":"tennis","location":"outdoor","surface":"clay","access":"permit","address":"Forest Park Dr, Woodhaven, NY 11421","lat":40.7007,"lng":-73.8525,"borough":"Queens","courts":8,"verified":True},
    {"id":21,"name":"Flushing Meadows Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"permit","address":"111th St, Flushing Meadows–Corona Park, Queens, NY 11368","lat":40.7445,"lng":-73.8430,"borough":"Queens","courts":12,"verified":True},
    {"id":22,"name":"Juniper Valley Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"Juniper Valley Park, Middle Village, NY 11379","lat":40.7206,"lng":-73.8703,"borough":"Queens","courts":4,"verified":True},
    {"id":23,"name":"Kissena Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"permit","address":"164-02 Kissena Blvd, Flushing, NY 11358","lat":40.7439,"lng":-73.8249,"borough":"Queens","courts":6,"verified":True},
    {"id":24,"name":"Springfield Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"179-79 Brookville Blvd, Springfield Gardens, NY 11413","lat":40.6631,"lng":-73.7545,"borough":"Queens","courts":4,"verified":True},
    {"id":25,"name":"Queens Padel Center","sport":"padel","location":"indoor","surface":"hard","access":"free","address":"35-10 Junction Blvd, Jackson Heights, NY 11372","lat":40.7463,"lng":-73.8887,"borough":"Queens","courts":4,"verified":False},
    # BRONX
    {"id":26,"name":"Crotona Park Tennis Courts","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"Crotona Ave & Fulton Ave, Bronx, NY 10457","lat":40.8327,"lng":-73.8998,"borough":"Bronx","courts":8,"verified":True},
    {"id":27,"name":"Van Cortlandt Park Tennis","sport":"tennis","location":"outdoor","surface":"clay","access":"permit","address":"Broadway & W 242nd St, Bronx, NY 10471","lat":40.8892,"lng":-73.8866,"borough":"Bronx","courts":10,"verified":True},
    {"id":28,"name":"Pelham Bay Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"Pelham Bay Park, Bruckner Blvd, Bronx, NY 10461","lat":40.8690,"lng":-73.8182,"borough":"Bronx","courts":6,"verified":True},
    {"id":29,"name":"Mullaly Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"161st St & Jerome Ave, Bronx, NY 10452","lat":40.8308,"lng":-73.9270,"borough":"Bronx","courts":4,"verified":True},
    {"id":30,"name":"Bronx Padel & Racquet Club","sport":"padel","location":"indoor","surface":"hard","access":"free","address":"700 E Tremont Ave, Bronx, NY 10457","lat":40.8476,"lng":-73.8798,"borough":"Bronx","courts":4,"verified":False},
    # STATEN ISLAND
    {"id":31,"name":"Silver Lake Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"915 Victory Blvd, Staten Island, NY 10301","lat":40.6268,"lng":-74.0975,"borough":"Staten Island","courts":4,"verified":True},
    {"id":32,"name":"Willowbrook Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"Willowbrook Park, Richmond Ave, Staten Island, NY 10314","lat":40.5988,"lng":-74.1639,"borough":"Staten Island","courts":6,"verified":True},
    {"id":33,"name":"Walker Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"50 Bard Ave, Staten Island, NY 10310","lat":40.6317,"lng":-74.1156,"borough":"Staten Island","courts":4,"verified":True},
    {"id":34,"name":"Clove Lakes Park Tennis","sport":"tennis","location":"outdoor","surface":"hard","access":"free","address":"1150 Clove Rd, Staten Island, NY 10301","lat":40.6273,"lng":-74.1142,"borough":"Staten Island","courts":4,"verified":True},
]


NYC_BOROUGH_MAP = {"B": "Brooklyn", "Q": "Queens", "M": "Manhattan", "X": "Bronx", "R": "Staten Island"}


def _polygon_centroid(multipolygon):
    """Compute centroid lat/lng from a GeoJSON MultiPolygon."""
    try:
        coords = multipolygon["coordinates"][0][0]
        lats = [c[1] for c in coords]
        lngs = [c[0] for c in coords]
        return round(sum(lats) / len(lats), 6), round(sum(lngs) / len(lngs), 6)
    except Exception:
        return None, None


def fetch_from_nyc_open_data():
    """
    Fetch all NYC Parks public tennis courts from NYC Open Data.
    Dataset: Athletic Facilities (qnem-b8re) + Parks Properties (enfh-gkve).
    Returns a list of court dicts grouped by park location.
    """
    print("  Fetching NYC Parks tennis courts from NYC Open Data...")

    # Step 1: All athletic facility records where tennis=true
    fields_url = "https://data.cityofnewyork.us/resource/qnem-b8re.json?" + urllib.parse.urlencode({
        "$where": "tennis=true",
        "$limit": "2000",
        "$select": "gispropnum,borough,surface_type,system,zipcode,multipolygon"
    })
    req = urllib.request.Request(fields_url, headers={"User-Agent": "NYCCourtsApp/1.0"})
    courts_raw = json.loads(urllib.request.urlopen(req, timeout=30).read())
    print(f"    {len(courts_raw)} raw court records fetched")

    # Step 2: Park names from Parks Properties dataset
    parks_url = "https://data.cityofnewyork.us/resource/enfh-gkve.json?" + urllib.parse.urlencode({
        "$limit": "5000",
        "$select": "gispropnum,signname,address,borough"
    })
    req2 = urllib.request.Request(parks_url, headers={"User-Agent": "NYCCourtsApp/1.0"})
    parks_raw = json.loads(urllib.request.urlopen(req2, timeout=30).read())
    park_lookup = {p["gispropnum"]: p for p in parks_raw if "gispropnum" in p}

    # Step 3: Group individual courts by park, compute centroid
    parks = {}
    for c in courts_raw:
        pid = c.get("gispropnum")
        if not pid:
            continue
        if pid not in parks:
            parks[pid] = {
                "courts": 0, "surfaces": set(),
                "first_poly": c.get("multipolygon"),
                "borough_code": c.get("borough", ""),
                "zipcode": c.get("zipcode", "")
            }
        parks[pid]["courts"] += 1
        surf = c.get("surface_type", "")
        if surf:
            parks[pid]["surfaces"].add(surf)

    # Step 4: Build final court list
    result = []
    NYC_LAT = (40.477, 40.917)
    NYC_LNG = (-74.260, -73.700)

    for pid, info in parks.items():
        park_info = park_lookup.get(pid, {})
        raw_name = park_info.get("signname", "").strip()
        name = raw_name or f"NYC Parks ({pid})"
        address = park_info.get("address", "")
        borough = NYC_BOROUGH_MAP.get(info["borough_code"],
                  NYC_BOROUGH_MAP.get(park_info.get("borough", ""), "Unknown"))

        lat, lng = _polygon_centroid(info["first_poly"])
        if not lat or not lng:
            continue
        if not (NYC_LAT[0] <= lat <= NYC_LAT[1] and NYC_LNG[0] <= lng <= NYC_LNG[1]):
            continue

        surfaces = info["surfaces"] - {""}
        raw_surf = list(surfaces)[0] if surfaces else ""
        surface = SURFACE_MAP.get(raw_surf.lower(), "hard")

        zip_code = info["zipcode"]
        full_address = f"{address}, {borough}, NY {zip_code}".strip(", ") if address else f"{borough}, NY"

        result.append({
            "name": f"{name} Tennis",
            "sport": "tennis",
            "location": "outdoor",
            "surface": surface,
            "access": "permit",
            "address": full_address,
            "lat": lat,
            "lng": lng,
            "borough": borough,
            "courts": info["courts"],
            "verified": True,
            "source": "NYC Open Data"
        })

    print(f"    {len(result)} unique park locations with tennis courts")
    return result


def fetch_from_geoapify():
    """Fetch live tennis & padel court data from Geoapify Places API."""
    courts = []
    seen_ids = set()

    for borough, lng, lat, radius in BOROUGH_CENTERS:
        print(f"  Fetching {borough}...")
        url = (
            f"https://api.geoapify.com/v2/places"
            f"?categories=sport.pitch"
            f"&conditions=named"
            f"&filter=circle:{lng},{lat},{radius}"
            f"&limit=500"
            f"&apiKey={GEOAPIFY_API_KEY}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "NYCCourtsApp/1.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        features = json.loads(resp.read()).get("features", [])

        for f in features:
            p = f.get("properties", {})
            raw = p.get("datasource", {}).get("raw", {})

            # Use set-based sport matching to avoid "table_tennis" false positives
            sport_tag = str(raw.get("sport") or "").lower()
            sports_set = set(s.strip() for s in sport_tag.split(";")) if sport_tag else set()
            name = str(p.get("name") or "")
            name_lower = name.lower()

            is_tennis = "tennis" in sports_set
            is_padel = "padel" in sports_set

            # Fall back to name-based detection only when no sport tag
            if not sports_set:
                is_tennis = "tennis court" in name_lower or name_lower.endswith(" tennis")
                is_padel = "padel" in name_lower

            if not (is_tennis or is_padel):
                continue

            # Skip entries with no real name (single chars, pure numbers)
            if len(name.strip()) < 3 or name.strip().isdigit():
                continue

            geo = f.get("geometry", {}).get("coordinates", [None, None])
            court_lng, court_lat = geo[0], geo[1]
            if not court_lat or not court_lng:
                continue

            # Skip courts outside NYC geographic bounds
            if not (40.477 <= court_lat <= 40.917 and -74.260 <= court_lng <= -73.700):
                continue

            place_id = p.get("place_id") or f"{round(court_lat,4)},{round(court_lng,4)}"
            if place_id in seen_ids:
                continue
            seen_ids.add(place_id)

            sport = "padel" if is_padel else "tennis"
            raw_surface = str(raw.get("surface") or "").lower()
            surface = SURFACE_MAP.get(raw_surface, "unknown" if raw_surface else "hard")

            access_raw = str(raw.get("access") or "").lower()
            if access_raw in ("private", "customers", "no"):
                access = "private"
            elif access_raw in ("permit", "permissive"):
                access = "permit"
            else:
                access = "free"

            indoor_tag = str(raw.get("indoor") or raw.get("covered") or "").lower()
            location = "indoor" if indoor_tag in ("yes", "true") else "outdoor"

            addr = ", ".join(x for x in [p.get("address_line1", ""), p.get("address_line2", "")] if x) or "NYC"

            courts.append({
                "id": len(courts) + 1000,
                "name": name or f"{sport.title()} Court",
                "sport": sport,
                "location": location,
                "surface": surface,
                "access": access,
                "address": addr,
                "lat": round(court_lat, 6),
                "lng": round(court_lng, 6),
                "borough": borough,
                "courts": int(raw.get("courts") or raw.get("court") or 1),
                "verified": True,
                "source": "Geoapify/OpenStreetMap"
            })

    return courts


def merge_with_curated(live_courts):
    """Add curated courts that aren't already covered by live data (by proximity)."""
    def near(c1, c2, thresh=0.005):
        return abs(c1["lat"] - c2["lat"]) < thresh and abs(c1["lng"] - c2["lng"]) < thresh

    merged = list(live_courts)
    for curated in FALLBACK_COURTS:
        if not any(near(curated, lc) for lc in live_courts):
            merged.append({**curated, "source": "curated"})

    # Re-index IDs cleanly
    for i, c in enumerate(merged, start=1):
        c["id"] = i

    return merged


def validate_courts(courts):
    """
    Validate the final court list before saving.
    Returns (is_valid, list_of_error_messages).
    """
    errors = []
    required = {"name", "lat", "lng", "borough", "sport", "surface", "access"}

    if len(courts) < 10:
        errors.append(f"Too few courts: {len(courts)} (minimum 10 required)")

    NYC_LAT = (40.477, 40.917)
    NYC_LNG = (-74.260, -73.700)
    seen_ids = set()

    for c in courts:
        name = c.get("name", f"id={c.get('id')}")
        missing = required - set(c.keys())
        if missing:
            errors.append(f"'{name}' is missing fields: {missing}")
        if not c.get("lat") or not c.get("lng"):
            errors.append(f"'{name}' has no coordinates")
        elif not (NYC_LAT[0] <= c["lat"] <= NYC_LAT[1]):
            errors.append(f"'{name}' latitude {c['lat']} outside NYC bounds")
        elif not (NYC_LNG[0] <= c["lng"] <= NYC_LNG[1]):
            errors.append(f"'{name}' longitude {c['lng']} outside NYC bounds")
        if c.get("id") in seen_ids:
            errors.append(f"Duplicate ID {c['id']} for '{name}'")
        seen_ids.add(c.get("id"))

    return (len(errors) == 0), errors


def print_diff_report(new_courts):
    """Compare new courts with previously saved data and print a weekly diff."""
    if not os.path.exists(OUTPUT_FILE):
        print("\n📋 Diff report: No previous data found — first run.")
        return

    try:
        with open(OUTPUT_FILE) as f:
            old_data = json.load(f)
        old_names = {c["name"] for c in old_data.get("courts", [])}
        new_names = {c["name"] for c in new_courts}

        added   = new_names - old_names
        removed = old_names - new_names
        unchanged = len(old_names & new_names)

        print(f"\n📋 Weekly diff report:")
        print(f"   Total this week : {len(new_courts)} courts")
        print(f"   Total last week : {len(old_names)} courts")
        print(f"   Unchanged       : {unchanged}")
        if added:
            print(f"   ✅ Added ({len(added)}):")
            for name in sorted(added):
                court = next((c for c in new_courts if c["name"] == name), {})
                print(f"      + {name} ({court.get('borough', '?')}, {court.get('sport', '?')})")
        if removed:
            print(f"   ❌ Removed ({len(removed)}):")
            for name in sorted(removed):
                print(f"      - {name}")
        if not added and not removed:
            print("   No changes — court data is stable.")
    except Exception as e:
        print(f"\n⚠️  Could not generate diff report: {e}")


def merge_all_sources(nyc_courts, geo_courts):
    """
    Merge NYC Open Data tennis courts with Geoapify padel/private courts.
    Deduplicates by proximity (0.005 degree ~ 500m).
    """
    def near(c1, c2, thresh=0.005):
        return abs(c1["lat"] - c2["lat"]) < thresh and abs(c1["lng"] - c2["lng"]) < thresh

    merged = list(nyc_courts)
    # Add Geoapify courts not already covered (mainly padel + private clubs)
    for gc in geo_courts:
        if not any(near(gc, mc) for mc in merged):
            merged.append(gc)

    # Add curated padel courts not covered by either source
    for curated in FALLBACK_COURTS:
        if curated["sport"] == "padel" and not any(near(curated, mc) for mc in merged):
            merged.append({**curated, "source": "curated"})

    for i, c in enumerate(merged, start=1):
        c["id"] = i

    return merged


def main():
    courts = []
    source = "fallback"

    print("═" * 50)
    print("NYC Courts Data Pipeline")
    print("═" * 50)

    nyc_courts, geo_courts = [], []

    # ── Source 1: NYC Open Data (official Parks Dept) ─────────────────────────
    print("\n[1/2] NYC Open Data — official Parks tennis courts")
    try:
        nyc_courts = fetch_from_nyc_open_data()
    except Exception as e:
        print(f"  ⚠️  NYC Open Data unavailable: {e}")

    # ── Source 2: Geoapify (padel + private clubs) ────────────────────────────
    print("\n[2/2] Geoapify — padel courts and private clubs")
    try:
        geo_courts = fetch_from_geoapify()
        print(f"  Geoapify returned {len(geo_courts)} courts")
    except Exception as e:
        print(f"  ⚠️  Geoapify unavailable: {e}")

    # ── Merge ─────────────────────────────────────────────────────────────────
    if len(nyc_courts) >= 10:
        courts = merge_all_sources(nyc_courts, geo_courts)
        source = "NYC Open Data + Geoapify + curated padel"
        print(f"\n  Merged: {len(nyc_courts)} NYC Parks + {len(geo_courts)} Geoapify → {len(courts)} total")
    elif len(geo_courts) >= 10:
        courts = merge_with_curated(geo_courts)
        source = "Geoapify + curated"
        print(f"\n  Using Geoapify fallback: {len(courts)} courts")
    else:
        courts = FALLBACK_COURTS[:]
        source = "curated fallback"
        print("\n  ⚠️  Both APIs unavailable — using curated fallback dataset")

    # ── Validate before saving ────────────────────────────────────────────────
    print("\nValidating court data...")
    is_valid, errors = validate_courts(courts)
    if not is_valid:
        print("❌ VALIDATION FAILED — keeping existing data to protect the app.")
        for err in errors:
            print(f"   • {err}")
        raise SystemExit(1)
    print(f"  ✅ Validation passed — {len(courts)} courts, all checks OK")

    # ── Diff report ───────────────────────────────────────────────────────────
    print_diff_report(courts)

    # ── Save ──────────────────────────────────────────────────────────────────
    output = {
        "meta": {
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": source,
            "total_courts": len(courts)
        },
        "courts": courts
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Done. Saved {len(courts)} courts to {OUTPUT_FILE}")
    print(f"   Source       : {source}")
    print(f"   Last updated : {output['meta']['last_updated']}")


if __name__ == "__main__":
    main()
