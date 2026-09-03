"""Place provisional site markers along a loop road.

    python3 pipeline/infer_positions.py 300

Writes `inferred_centroid` onto each site in data/loops/<loop>.yaml — a position
derived from the loop's own road geometry and the county's block ranges, spaced by the
site count. It is a SCAFFOLD, not data:

  * it never touches `centroid`, which only digitizing writes,
  * so it never produces an aerial thumbnail or a measurement,
  * and the map draws it dashed, captioned as provisional.

Its job is to make the loop map legible before anyone has digitized it, and to give a
digitizer a numbered starting point to correct. Cross-referencing published sources to
fix which number belongs to which pad is exactly the right way to improve it — the
layout is a fact, and facts can be checked against anything.
"""

import math
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json

EARTH_FT = 20925721.8


def road(loop):
    p = os.path.join(ROOT, "data", "reference", f"loop-{loop}-osm-road.geojson")
    if not os.path.exists(p):
        return []
    fc = json.load(open(p))
    return [c for f in fc["features"] for c in f["geometry"]["coordinates"]]


def one(loop):
    path = os.path.join(ROOT, "data", "loops", f"{loop}.yaml")
    data = yaml.safe_load(open(path))
    pts = road(loop)
    sites = data.get("sites") or []
    if len(pts) < 2 or not sites:
        print(f"  loop {loop}: SKIPPED — no road geometry or no roster")
        return

    # cumulative length along the centreline, in degrees-space but weighted properly
    lat0 = pts[0][1]
    cos = math.cos(math.radians(lat0))
    def d(a, b):
        return math.hypot((b[0] - a[0]) * cos, b[1] - a[1])
    cum = [0.0]
    for i in range(len(pts) - 1):
        cum.append(cum[-1] + d(pts[i], pts[i + 1]))
    total = cum[-1]

    OFFSET_FT = 52.0
    off_deg = OFFSET_FT / EARTH_FT / math.radians(1)

    n = len(sites)
    for i, site in enumerate(sites):
        t = (i + 0.5) / n * total
        j = max(0, min(len(pts) - 2, next(
            (k for k in range(len(pts) - 1) if cum[k + 1] >= t), len(pts) - 2)))
        span = cum[j + 1] - cum[j] or 1e-12
        f = (t - cum[j]) / span
        lon = pts[j][0] + (pts[j + 1][0] - pts[j][0]) * f
        lat = pts[j][1] + (pts[j + 1][1] - pts[j][1]) * f

        dx = (pts[j + 1][0] - pts[j][0]) * cos
        dy = pts[j + 1][1] - pts[j][1]
        m = math.hypot(dx, dy) or 1e-12
        side = 1 if i % 2 == 0 else -1
        site["inferred_centroid"] = [round(lat + (dx / m) * off_deg * side, 6),
                                     round(lon - (dy / m) * off_deg * side / cos, 6)]

    data["positions_inferred"] = True
    with open(path, "w") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True, width=100)
    print(f"  loop {loop}: {n} provisional positions along "
          f"{int(total/off_deg*OFFSET_FT)} ft of road")


def main():
    if len(sys.argv) > 1:
        loops = [int(a) for a in sys.argv[1:]]
    else:
        d = os.path.join(ROOT, "data", "loops")
        loops = sorted(int(f[:-5]) for f in os.listdir(d) if f.endswith(".yaml"))
    for loop in loops:
        one(loop)
    print("\nThese are a scaffold — spacing arithmetic, not observation.")
    print("Digitizing replaces them and writes real centroids.")


if __name__ == "__main__":
    main()
