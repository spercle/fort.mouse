"""Cache the OSM surroundings of each loop, so the maps have context.

    python3 pipeline/loop_context.py [loop ...]

Writes data/reference/loop-<loop>-context.geojson: woods, water, canals, neighbouring
roads, trails, buildings and comfort stations within ~400 ft of the loop.

© OpenStreetMap contributors, ODbL.
"""
import json, math, os, ssl, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "data", "reference")
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
MARGIN = 0.0012   # ~400 ft


def kind(t):
    if t.get("natural") == "water" or t.get("waterway"): return "water"
    if t.get("natural") == "wood" or t.get("landuse") == "forest": return "wood"
    if t.get("amenity") == "toilets": return "comfort"
    if "building" in t: return "building"
    h = t.get("highway")
    if h in ("track", "footway", "path"): return "trail"
    if h: return "road"
    if t.get("amenity"): return "amenity"
    return None


def fetch(loop):
    road = os.path.join(REF, f"loop-{loop}-osm-road.geojson")
    if not os.path.exists(road):
        return None
    pts = [p for f in json.load(open(road))["features"]
           for p in f["geometry"]["coordinates"]]
    lo = (min(p[1] for p in pts) - MARGIN, min(p[0] for p in pts) - MARGIN,
          max(p[1] for p in pts) + MARGIN, max(p[0] for p in pts) + MARGIN)
    q = f"""[out:json][timeout:90];
    ( way["natural"]({lo[0]},{lo[1]},{lo[2]},{lo[3]});
      way["waterway"]({lo[0]},{lo[1]},{lo[2]},{lo[3]});
      way["landuse"]({lo[0]},{lo[1]},{lo[2]},{lo[3]});
      way["building"]({lo[0]},{lo[1]},{lo[2]},{lo[3]});
      way["highway"]({lo[0]},{lo[1]},{lo[2]},{lo[3]});
      node["amenity"]({lo[0]},{lo[1]},{lo[2]},{lo[3]});
      way["amenity"]({lo[0]},{lo[1]},{lo[2]},{lo[3]}); );out geom;"""
    req = urllib.request.Request("https://overpass-api.de/api/interpreter",
        data=urllib.parse.urlencode({"data": q}).encode(),
        headers={"User-Agent": "fort-mouse/0.1"})
    data = json.loads(urllib.request.urlopen(req, timeout=150, context=CTX).read())

    feats = []
    for el in data.get("elements", []):
        t = el.get("tags") or {}
        k = kind(t)
        if not k:
            continue
        if el["type"] == "node":
            geom, gt = [el["lon"], el["lat"]], "Point"
        else:
            geom = [[g["lon"], g["lat"]] for g in el.get("geometry", [])]
            if len(geom) < 2:
                continue
            closed = geom[0] == geom[-1]
            gt = "Polygon" if (closed and k in ("wood", "water", "building")) else "LineString"
            if gt == "Polygon":
                geom = [geom]
        feats.append({"type": "Feature",
                      "geometry": {"type": gt, "coordinates": geom},
                      "properties": {"kind": k, "name": t.get("name"),
                                     "highway": t.get("highway")}})
    out = os.path.join(REF, f"loop-{loop}-context.geojson")
    json.dump({"type": "FeatureCollection", "features": feats}, open(out, "w"))
    tally = {}
    for f in feats:
        tally[f["properties"]["kind"]] = tally.get(f["properties"]["kind"], 0) + 1
    print(f"  loop {loop}: {tally}")
    return feats


if __name__ == "__main__":
    loops = [int(a) for a in sys.argv[1:]] or [
        int(f.split("-")[1]) for f in sorted(os.listdir(REF))
        if f.endswith("-osm-road.geojson")]
    import time
    for i, l in enumerate(loops):
        fetch(l)
        if i < len(loops) - 1:
            time.sleep(1.2)
