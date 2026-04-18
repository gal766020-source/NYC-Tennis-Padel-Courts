"""
tests/test_fetch_courts.py
--------------------------
Automated tests for the fetch_courts.py data pipeline.
Run with: pytest tests/
These tests run automatically in GitHub Actions before every data refresh.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch_courts import (
    FALLBACK_COURTS, SURFACE_MAP, BOROUGH_CENTERS, merge_with_curated
)

NYC_LAT = (40.477, 40.917)
NYC_LNG = (-74.260, -73.700)
REQUIRED_FIELDS = {"id", "name", "sport", "location", "surface", "access",
                   "address", "lat", "lng", "borough", "courts", "verified"}
VALID_SPORTS    = {"tennis", "padel"}
VALID_BOROUGHS  = {"Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"}


# ── Fallback data quality ─────────────────────────────────────────────────────

def test_fallback_courts_exist():
    """Curated dataset must have at least 30 courts."""
    assert len(FALLBACK_COURTS) >= 30, f"Only {len(FALLBACK_COURTS)} fallback courts — expected ≥30"

def test_fallback_courts_required_fields():
    """Every fallback court must have all required fields with non-empty values."""
    for court in FALLBACK_COURTS:
        missing = REQUIRED_FIELDS - set(court.keys())
        assert not missing, f"Court '{court.get('name')}' is missing fields: {missing}"
        assert court["name"], f"Court id={court['id']} has empty name"
        assert court["lat"],  f"Court '{court['name']}' has no latitude"
        assert court["lng"],  f"Court '{court['name']}' has no longitude"

def test_fallback_courts_valid_sport():
    """Every court must be tennis or padel — nothing else."""
    for court in FALLBACK_COURTS:
        assert court["sport"] in VALID_SPORTS, \
            f"'{court['name']}' has invalid sport: {court['sport']}"

def test_fallback_courts_valid_borough():
    """Every court must be in one of the five NYC boroughs."""
    for court in FALLBACK_COURTS:
        assert court["borough"] in VALID_BOROUGHS, \
            f"'{court['name']}' has invalid borough: {court['borough']}"

def test_fallback_courts_within_nyc_bounds():
    """Every court's coordinates must be inside NYC's geographic bounding box."""
    for court in FALLBACK_COURTS:
        assert NYC_LAT[0] <= court["lat"] <= NYC_LAT[1], \
            f"'{court['name']}' latitude {court['lat']} is outside NYC"
        assert NYC_LNG[0] <= court["lng"] <= NYC_LNG[1], \
            f"'{court['name']}' longitude {court['lng']} is outside NYC"

def test_fallback_courts_no_duplicate_ids():
    """Every court must have a unique ID."""
    ids = [c["id"] for c in FALLBACK_COURTS]
    assert len(ids) == len(set(ids)), "Duplicate court IDs found in FALLBACK_COURTS"

def test_fallback_courts_no_duplicate_names():
    """No two courts should have exactly the same name."""
    names = [c["name"] for c in FALLBACK_COURTS]
    dupes = [n for n in names if names.count(n) > 1]
    assert not dupes, f"Duplicate court names: {set(dupes)}"

def test_all_five_boroughs_represented():
    """Fallback data must include courts from all five NYC boroughs."""
    boroughs = {c["borough"] for c in FALLBACK_COURTS}
    missing = VALID_BOROUGHS - boroughs
    assert not missing, f"No fallback courts for: {missing}"


# ── Surface map ───────────────────────────────────────────────────────────────

def test_surface_map_keys_are_lowercase():
    """All surface map keys must be lowercase (raw OSM tags are lowercase)."""
    for key in SURFACE_MAP:
        assert key == key.lower(), f"Surface map key '{key}' is not lowercase"

def test_surface_map_valid_values():
    """Surface map must only output hard, clay, or grass."""
    valid = {"hard", "clay", "grass"}
    for raw, mapped in SURFACE_MAP.items():
        assert mapped in valid, f"Surface '{raw}' maps to invalid value '{mapped}'"


# ── Borough centers ───────────────────────────────────────────────────────────

def test_borough_centers_all_five():
    """Must have search centers for all five boroughs."""
    names = {b[0] for b in BOROUGH_CENTERS}
    assert names == VALID_BOROUGHS, f"Borough centers missing: {VALID_BOROUGHS - names}"

def test_borough_centers_valid_coords():
    """All borough center coordinates must be within NYC bounds."""
    for name, lng, lat, radius in BOROUGH_CENTERS:
        assert NYC_LAT[0] <= lat <= NYC_LAT[1], f"{name} center lat out of bounds"
        assert NYC_LNG[0] <= lng <= NYC_LNG[1], f"{name} center lng out of bounds"
        assert 1000 <= radius <= 20000, f"{name} radius {radius}m seems wrong"


# ── Merge logic ───────────────────────────────────────────────────────────────

def test_merge_deduplicates_by_proximity():
    """merge_with_curated must not add a curated court that's close to a live one."""
    # Central Park is in FALLBACK_COURTS at ~40.7859, -73.9591
    live = [{
        "id": 1000, "name": "Central Park Tennis Center", "sport": "tennis",
        "location": "outdoor", "surface": "clay", "access": "permit",
        "address": "NYC", "lat": 40.7859, "lng": -73.9591,
        "borough": "Manhattan", "courts": 30, "verified": True
    }]
    merged = merge_with_curated(live)
    cp = [c for c in merged if "Central Park" in c["name"]]
    assert len(cp) == 1, "Central Park Tennis Center was duplicated after merge"

def test_merge_adds_missing_curated_courts():
    """merge_with_curated must add curated courts not covered by live data."""
    live = []  # no live courts at all
    merged = merge_with_curated(live)
    assert len(merged) == len(FALLBACK_COURTS), \
        "All fallback courts should be added when live data is empty"

def test_merge_ids_are_sequential():
    """After merging, all court IDs must be unique."""
    live = [{"id": 999, "name": "Test Padel", "sport": "padel",
             "location": "indoor", "surface": "hard", "access": "free",
             "address": "NYC", "lat": 40.75, "lng": -74.00,
             "borough": "Manhattan", "courts": 2, "verified": True}]
    merged = merge_with_curated(live)
    ids = [c["id"] for c in merged]
    assert len(ids) == len(set(ids)), "Duplicate IDs after merge"
