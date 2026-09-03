"""Turn digitized pad polygons into a loop's machine-owned data file.

    python3 pipeline/derive.py 1200 work/loop-1200-pads.geojson

Reads a GeoJSON FeatureCollection of pad polygons (see pipeline/README.md for the
digitizing contract) and writes data/loops/<loop>.yaml.

This only ever writes data/loops/. It never touches data/sites/ — see ADR-0002.
"""

import json
import os
import sys
from datetime import date

from geom import (min_area_rect, to_local_ft, centroid, polyline_length_ft,
                  point_to_polyline_ft)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = False

# Disney's published Category specs. These are category maxima, never a measurement
# of any particular Site — which is why they are emitted with their own provenance.
CATEGORY = {
    "Tent/Pop-Up":    {"site_length_ft": 25, "site_width_ft": 10, "sewer": False},
    "Full Hook-Up":   {"site_length_ft": 50, "site_width_ft": 10, "sewer": True},
    "Preferred":      {"site_length_ft": 45, "site_width_ft": 10, "sewer": True},
    "Premium":        {"site_length_ft": 60, "site_width_ft": 18, "sewer": True},
    "Premium Meadow": {"site_length_ft": 60, "site_width_ft": 18, "sewer": True},
}

def loop_meta(loop):
    """Read the loop's identity from its own file rather than a second registry."""
    path = os.path.join(ROOT, "data", "loops", f"{loop}.yaml")
    if not os.path.exists(path):
        return None
    import yaml
    d = yaml.safe_load(open(path)) or {}
    if "loop_name" not in d or "category" not in d:
        return None
    return {"name": d["loop_name"], "category": d["category"],
            "expected_sites": d.get("expected_site_count") or len(d.get("sites") or [])}


def load_road(loop):
    """The loop's road centreline, used to order pads and measure setback."""
    path = os.path.join(ROOT, "data", "reference", f"loop-{loop}-osm-road.geojson")
    if not os.path.exists(path):
        return None
    fc = json.load(open(path))
    coords = []
    for f in fc["features"]:
        coords.extend(f["geometry"]["coordinates"])
    return coords or None


def measure(feature, road):
    """Everything derivable from one digitized pad polygon."""
    props = feature.get("properties", {})
    ring = feature["geometry"]["coordinates"][0]
    if ring[0] == ring[-1]:
        ring = ring[:-1]

    origin = (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    local = to_local_ft(ring, origin)
    length, width, bearing = min_area_rect(local)

    site = {
        "site_number": int(props["site_number"]),
        # What you trace from above is the whole hardstand — the concrete slab and
        # the apron around it read as one surface at this resolution. That is the
        # SITE, not the pad. Separating the poured concrete needs someone on the
        # ground; see ADR-0005.
        "site_length_ft": round(length, 1),
        "site_width_ft": round(width, 1),
        "pad_orientation_deg": round(bearing, 1),
        "centroid": [round(origin[1], 6), round(origin[0], 6)],
    }

    if road:
        offset, along = point_to_polyline_ft(list(origin), road)
        site["road_offset_ft"] = round(offset, 1)
        site["_along_ft"] = along  # ordering only; stripped before writing

    for key in ("pad_surface", "backs_onto", "approach_side", "imagery_vintage",
                "number_confidence", "notes"):
        if props.get(key) not in (None, ""):
            site[key] = props[key]

    return site


def emit(loop, sites, meta, info, demo=False):
    """Hand-rolled YAML so field order is stable and diffs stay readable."""
    cat = CATEGORY[info["category"]]
    out = []
    w = out.append

    w(f"# Loop {loop} — {info['name']}")
    w("#")
    w("# MACHINE-OWNED. Safe to delete and regenerate: `python3 pipeline/derive.py"
      f" {loop} <pads.geojson>`")
    w("# Human notes live in data/sites/*.md and are never written here. See ADR-0002.")
    w("")
    if demo:
        w("# " + "!" * 74)
        w("# DEMO DATA — SYNTHETIC. Every measurement below is invented so the site can")
        w("# be viewed populated. None of it describes a real campsite. The pages render")
        w("# a warning banner while status is `demo`.")
        w("# Restore the real seed: cp data/loops/1200.yaml.seed data/loops/1200.yaml")
        w("# " + "!" * 74)
        w("")
    w(f"loop: {loop}")
    w(f"loop_name: {info['name']}")
    w(f"category: {info['category']}")
    w(f"generated: {date.today().isoformat()}")
    if demo:
        w("status: demo")
    w("")
    w("# Disney's published Category maximum. NOT a measurement of any Site.")
    w("category_baseline:")
    w(f"  site_length_ft: {cat['site_length_ft']}")
    w(f"  site_width_ft: {cat['site_width_ft']}")
    w(f"  sewer: {str(cat['sewer']).lower()}")
    w("  max_occupancy: 8          # effective for arrivals from 2026-01-01")
    w("  source: disney-category")
    w("")
    for k, v in meta.items():
        w(f"{k}: {json.dumps(v) if isinstance(v, (list, dict)) else v}")
    if meta:
        w("")
    w(f"site_count: {len(sites)}")
    w("sites:")

    for s in sites:
        s.pop("_along_ft", None)
        w(f"  - site_number: {s['site_number']}")
        for key in ("site_length_ft", "site_width_ft", "pad_orientation_deg",
                    "road_offset_ft", "pad_surface", "backs_onto", "approach_side"):
            if key in s:
                w(f"    {key}: {s[key]}")
        if "centroid" in s:
            w(f"    centroid: [{s['centroid'][0]}, {s['centroid'][1]}]")
        w(f"    number_confidence: {s.get('number_confidence', 'unverified')}")
        if "imagery_vintage" in s:
            w(f"    imagery_vintage: {s['imagery_vintage']}")
        w("    source: aerial")
        if "notes" in s:
            w(f"    notes: {json.dumps(s['notes'])}")

    return "\n".join(out) + "\n"


def main():
    global DEMO
    args = [a for a in sys.argv[1:] if a != "--demo"]
    DEMO = "--demo" in sys.argv
    if len(args) != 2:
        sys.exit(__doc__)
    loop = int(args[0])
    info = loop_meta(loop)
    if info is None:
        sys.exit(f"no data/loops/{loop}.yaml — run pipeline/bootstrap_loops.py first")

    fc = json.load(open(args[1]))

    # The digitizing layer is EPSG:2236 (feet); this wants EPSG:4326 (degrees).
    # Getting that export wrong produces plausible-looking nonsense, so refuse it
    # loudly rather than writing bad measurements.
    sample = None
    for f in fc.get("features", []):
        if f.get("geometry", {}).get("type") == "Polygon":
            sample = f["geometry"]["coordinates"][0][0]
            break
    if sample and not (-82.0 < sample[0] < -81.0 and 28.0 < sample[1] < 29.0):
        sys.exit(
            f"coordinates look like {sample} — that is not lat/lon over Fort Wilderness.\n"
            "Re-export the digitizing layer as GeoJSON in EPSG:4326 "
            "(Export ▸ Save Features As ▸ CRS: EPSG:4326).")

    road = load_road(loop)
    if road is None:
        print("  ! no road centreline found; pads will not be ordered along the loop")

    sites = []
    for f in fc["features"]:
        if f.get("geometry", {}).get("type") != "Polygon":
            continue
        if "site_number" not in f.get("properties", {}):
            sys.exit("every pad polygon needs a site_number property")
        sites.append(measure(f, road))

    if road:
        sites.sort(key=lambda s: s.get("_along_ft", 0))
    else:
        sites.sort(key=lambda s: s["site_number"])

    meta = {}
    if road:
        meta["road_length_ft"] = round(polyline_length_ft(road), 1)

    dest = os.path.join(ROOT, "data", "loops", f"{loop}.yaml")

    # Refuse to replace a loop file with nothing. An empty digitizing export is far
    # more likely to be a mistake — wrong file, wrong layer, forgot to save edits —
    # than a deliberate request to wipe the loop.
    if not sites and os.path.exists(dest):
        sys.exit(
            f"{sys.argv[2] if len(sys.argv) > 2 else 'input'} contains no pad polygons.\n"
            f"Refusing to overwrite data/loops/{loop}.yaml with an empty roster.\n"
            "Check you exported the pads layer, saved your edits, and chose GeoJSON.")

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w").write(emit(loop, sites, meta, info, demo=DEMO))

    expected = info["expected_sites"]
    print(f"  wrote {dest}")
    print(f"  {len(sites)} sites measured (expected ~{expected})")
    if len(sites) != expected:
        print(f"  ! count differs from the expected {expected} — worth resolving")
    if sites:
        lens = [s["site_length_ft"] for s in sites]
        print(f"  pad length: min {min(lens)}, median {sorted(lens)[len(lens)//2]}, max {max(lens)}")


if __name__ == "__main__":
    main()
