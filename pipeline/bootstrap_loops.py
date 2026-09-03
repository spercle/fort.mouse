"""Create the starting data file for every campsite loop.

    python3 pipeline/bootstrap_loops.py

Pulls, for all 21 campsite loops:
  * Orange County address-range segments (public record) -> loop identity + number blocks
  * OpenStreetMap road centrelines                       -> geometry for ordering pads
and writes data/loops/<loop>.yaml with an unmeasured roster.

Nothing here is a measurement. Site numbers are a documented-sequence hypothesis and are
marked as such; site counts come from a third party and are contested. Both are recorded
so that digitizing can confirm or refute them.

Existing loop files are left alone unless --force is given, so this cannot clobber work.
"""

import argparse
import json
import math
import os
import ssl
import urllib.parse
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

COUNTY = ("https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/"
          "MapServer/1/query")
OVERPASS = "https://overpass-api.de/api/interpreter"
BBOX = (28.393, -81.578, 28.415, -81.548)

# Loop -> (street name in OSM, Disney category, site count).
# Counts are TouringPlans' and are contested; see docs/research/data-landscape.md.
LOOPS = {
    100:  ("Bay Tree Lane", "Preferred", 27),
    200:  ("Palmetto Path", "Preferred", 37),
    300:  ("Cypress Knee Circle", "Preferred", 61),
    400:  ("Whispering Pine Way", "Premium", 33),
    500:  ("Buffalo Bend", "Premium", 56),
    600:  ("Sunny Sage Way", "Premium Meadow", 37),
    700:  ("Cinnamon Fern Way", "Premium", 34),
    800:  ("Jack Rabbit Run", "Premium Meadow", 74),
    900:  ("Quail Trail", "Premium Meadow", 32),
    1000: ("Racoon Lane", "Premium Meadow", 23),
    1100: ("Possum Path", "Premium", 24),
    1200: ("Dogwood Drive", "Premium", 22),
    1300: ("Tumbleweed Turn", "Premium", 34),
    1400: ("Little Bear Path", "Premium Meadow", 61),
    1500: ("Cottontail Curl", "Tent/Pop-Up", 21),
    1600: ("Timber Trail", "Full Hook-Up", 45),
    1700: ("Hickory Hollow", "Full Hook-Up", 41),
    1800: ("Conestoga Trail", "Full Hook-Up", 32),
    1900: ("Wagon Wheel Way", "Full Hook-Up", 38),
    2000: ("Spanish Moss Lane", "Tent/Pop-Up", 69),
    2100: ("Bobcat Bend", "Full Hook-Up", 44),
}

# Loop 1400 is an inner and outer loop with two street names.
EXTRA_STREETS = {1400: ["Big Bear Path"]}

BASELINE = {
    "Tent/Pop-Up":    (25, 10, False),
    "Full Hook-Up":   (50, 10, True),
    "Preferred":      (45, 10, True),
    "Premium":        (60, 18, True),
    "Premium Meadow": (60, 18, True),
}

NOTES = {
    1400: "Category is contested — Premium Meadow in some sources, plain Premium in "
          "others. Premium Meadow was introduced in January 2020.",
    2100: "Converted from cabins to campsites around 2016. Stale sources still list "
          "2100-2800 as cabins.",
    100:  "Contains two cabins, 118 and 120, interleaved among the campsites. The "
          "roster below does not account for them.",
    700:  "Closed 2026-08-31 to late September 2026 for utility work.",
}


def fetch(url, params=None, timeout=120):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "fort-mouse/0.1"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def ft(a, b):
    R = 20925721.8
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[0], b[1], b[0]))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def plen(pts):
    return sum(ft(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def county_segments():
    """All Fort Wilderness address ranges in one request, grouped by street."""
    data = fetch(COUNTY, {"where": "LEFT_ZIPCODE='32830' OR RIGHT_ZIPCODE='32830'",
                          "outFields": "*", "returnGeometry": "true",
                          "outSR": "4326", "f": "json"})
    by_street = {}
    for f in data.get("features", []):
        a = f["attributes"]
        name = (a.get("BASENAME") or "").strip().lower()
        paths = (f.get("geometry") or {}).get("paths") or []
        if not name or not paths:
            continue
        by_street.setdefault(name, []).append({
            "theoretical_left": [a.get("LEFT_THEORETICAL_MIN"), a.get("LEFT_THEORETICAL_MAX")],
            "theoretical_right": [a.get("RIGHT_THEORETICAL_MIN"), a.get("RIGHT_THEORETICAL_MAX")],
            "from": a.get("FROM_CROSSSTREET"),
            "to": a.get("TO_CROSSSTREET"),
            "length_ft": round(plen(paths[0]), 1),
            "geometry": paths[0],
        })
    return by_street


def osm_roads():
    names = [s for s, _, _ in LOOPS.values()]
    for extra in EXTRA_STREETS.values():
        names += extra
    clauses = "".join(
        f'way["name"="{n}"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});' for n in names)
    data = fetch(OVERPASS, {"data": f"[out:json][timeout:120];({clauses});out geom;"})
    roads = {}
    for el in data.get("elements", []):
        name = (el.get("tags") or {}).get("name", "")
        pts = [[g["lon"], g["lat"]] for g in el.get("geometry", [])]
        if name and pts:
            roads.setdefault(name.lower(), []).append({"id": el["id"], "coords": pts})
    return roads


def street_keys(name):
    """County BASENAME is inconsistent — it drops the street type on some streets
    ('dogwood') and keeps it on others ('possum path'). Try both forms."""
    words = name.lower().split()
    drop = {"lane", "ln", "path", "circle", "cir", "way", "bend", "bnd", "run",
            "trail", "trl", "drive", "dr", "turn", "curl", "hollow"}
    stripped = " ".join(w for w in words if w not in drop)
    return [w for w in dict.fromkeys([" ".join(words), stripped]) if w]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="overwrite loop files that already exist")
    args = ap.parse_args()

    print("fetching Orange County address ranges…")
    county = county_segments()
    print(f"  {len(county)} streets in zip 32830")

    print("fetching OSM road centrelines…")
    roads = osm_roads()
    print(f"  {len(roads)} named roads matched")

    os.makedirs(os.path.join(ROOT, "data", "loops"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "data", "reference"), exist_ok=True)

    written = skipped = 0
    for loop, (street, category, count) in sorted(LOOPS.items()):
        dest = os.path.join(ROOT, "data", "loops", f"{loop}.yaml")
        if os.path.exists(dest) and not args.force:
            print(f"  loop {loop}: exists, left alone")
            skipped += 1
            continue

        streets = [street] + EXTRA_STREETS.get(loop, [])

        # The street name identifies the loop. Do NOT filter on the county's block
        # number: Cottontail Curl (loop 1500) is filed under blocks starting 1400,
        # and the county's own ranges are theoretical rather than Disney's numbering.
        segs, mismatched = [], False
        for s in streets:
            for key in street_keys(s):
                for seg in county.get(key, []):
                    if seg in segs:
                        continue
                    lo = seg["theoretical_left"][0] or seg["theoretical_right"][0] or 0
                    if not (loop <= lo < loop + 100):
                        mismatched = True
                    segs.append(seg)
        segs.sort(key=lambda s: s["theoretical_left"][0] or 0)

        # OSM centreline
        coords = []
        for s in streets:
            for way in roads.get(s.lower(), []):
                coords.extend(way["coords"])
        road_ft = round(plen(coords), 1) if len(coords) > 1 else None

        if coords:
            with open(os.path.join(ROOT, "data", "reference",
                                   f"loop-{loop}-osm-road.geojson"), "w") as fh:
                json.dump({"type": "FeatureCollection", "features": [{
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": coords},
                    "properties": {"source": "OpenStreetMap", "streets": streets,
                                   "length_ft": road_ft}}]}, fh, indent=1)

        if segs:
            with open(os.path.join(ROOT, "data", "reference",
                                   f"loop-{loop}-county-segments.geojson"), "w") as fh:
                json.dump({"type": "FeatureCollection", "features": [{
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": s.pop("geometry")},
                    "properties": s} for s in [dict(x) for x in segs]]}, fh, indent=1)

        length_ft, width_ft, sewer = BASELINE[category]
        L = []
        w = L.append
        w(f"# Loop {loop} — {street}")
        w("#")
        w("# SEED — nothing here is measured. Regenerate from digitized pads with:")
        w(f"#   python3 pipeline/derive.py {loop} work/loop-{loop}-pads.geojson")
        w("# MACHINE-OWNED. Human notes live in data/sites/*.md. See ADR-0002.")
        w("")
        w(f"loop: {loop}")
        w(f"loop_name: {street}")
        w(f"category: {category}")
        w(f"generated: {date.today().isoformat()}")
        w("status: unmeasured")
        w("")
        w("# Disney's published Category maximum. NOT a measurement of any Site.")
        w("category_baseline:")
        w(f"  pad_length_ft: {length_ft}")
        w(f"  pad_width_ft: {width_ft}")
        w(f"  sewer: {str(sewer).lower()}")
        w("  max_occupancy: 8          # effective for arrivals from 2026-01-01")
        w("  source: disney-category")
        w("")
        if segs:
            w("# Loop identity and number blocks from Orange County's public")
            w("# address-range record — not from any fan map. See ADR-0001.")
            w("county_record:")
            w("  source: county-record")
            w("  service: ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/1")
            w(f"  retrieved: {date.today().isoformat()}")
            w("  segments:")
            for s in segs:
                w(f"    - theoretical_left: [{s['theoretical_left'][0]}, {s['theoretical_left'][1]}]")
                w(f"      theoretical_right: [{s['theoretical_right'][0]}, {s['theoretical_right'][1]}]")
                w(f"      from: {json.dumps(s['from'])}")
                w(f"      to: {json.dumps(s['to'])}")
                w(f"      length_ft: {s['length_ft']}")
            w("  caveat: >-")
            w("    ACTUAL ranges are 0 in the source, so only THEORETICAL block")
            w("    allocations are known. Even-left/odd-right is the county's own")
            w("    convention and is NOT Disney's site numbering.")
            if mismatched:
                w("  block_mismatch: >-")
                w(f"    The county files this street under a block that does not match loop")
                w(f"    {loop}. The street name identifies the loop; the county's block")
                w("    numbering is its own and is known to be inconsistent here.")
            w("")
        if road_ft:
            w(f"road_length_ft_osm: {road_ft}")
            w("")
        if loop in NOTES:
            w(f"loop_note: >-")
            w(f"  {NOTES[loop]}")
            w("")
        w("# Count is TouringPlans' and is not authoritative; campground totals are")
        w("# contested across every published source.")
        w(f"expected_site_count: {count}")
        w("")
        w("# HYPOTHESIS ONLY. Loops are documented as numbering sequentially from N01,")
        w("# so this roster is an expectation, not an observation.")
        w("site_count: 0")
        w("sites:")
        for i in range(count):
            w(f"  - site_number: {loop + 1 + i}")
            w("    pad_length_ft: unmeasured")
            w("    pad_width_ft: unmeasured")
            w("    pad_orientation_deg: unmeasured")
            w("    backs_onto: unknown")
            w("    number_confidence: hypothesis")
            w("    source: none")
        if loop == 1200:
            w("")
            w("open_questions:")
            w("  - id: pull-throughs")
            w("    claim: Two pull-through sites exist in Loop 1200")
            w("    status: unverified")
            w("    earliest_source: jlspence FW FAQ, last updated 2009")

        open(dest, "w").write("\n".join(L) + "\n")
        written += 1
        print(f"  loop {loop}: {count} sites, {len(segs)} county segment(s), "
              f"{'road ' + str(int(road_ft)) + ' ft' if road_ft else 'NO ROAD GEOMETRY'}")

    print(f"\n{written} written, {skipped} left alone")


if __name__ == "__main__":
    main()
