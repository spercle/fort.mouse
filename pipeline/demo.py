"""Generate synthetic pads so the site can be viewed populated before any real
digitizing exists.

    python3 pipeline/demo.py

Writes work/demo-pads.geojson and runs it through derive.py --demo, which stamps
`status: demo` into the loop file so every page renders a warning banner.

None of these numbers describe a real campsite. They are placed along the real road
centreline with plausible Premium-category dimensions purely so the layout, the
provenance badges and the loop aggregates can be seen working.

Restore the honest starting state with:
    cp data/loops/1200.yaml.seed data/loops/1200.yaml
"""

import json
import math
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOOP = 1200
OUT = os.path.join(ROOT, "work", "demo-pads.geojson")

# Degrees per foot at this latitude. Fine for placing fixtures; the real pipeline
# does this properly in geom.py.
FT = 1 / 364000.0

random.seed(1200)

road = json.load(
    open(os.path.join(ROOT, "data", "reference", f"loop-{LOOP}-osm-road.geojson"))
)["features"][0]["geometry"]["coordinates"]

BACKS = ["woods", "woods", "woods", "road", "site", "open"]
VINTAGES = ["oc-2025", "oc-2025", "oc-2022", "oc-2024"]

features = []
n = 22
for i in range(n):
    t = (i + 0.5) / n * (len(road) - 1)
    j = min(int(t), len(road) - 2)
    f = t - j
    lon = road[j][0] + (road[j + 1][0] - road[j][0]) * f
    lat = road[j][1] + (road[j + 1][1] - road[j][1]) * f
    hdg = math.atan2(road[j + 1][0] - road[j][0], road[j + 1][1] - road[j][1])

    side = 1 if i % 2 == 0 else -1
    clat = lat + -math.sin(hdg) * side * 46 * FT
    clon = lon + math.cos(hdg) * side * 46 * FT / math.cos(math.radians(lat))

    # Premium is published at up to 18 x 60 ft; spread under that.
    length = round(random.uniform(41, 61), 1)
    width = round(random.uniform(11, 18), 1)

    th = hdg + math.pi / 2 + math.radians(random.uniform(-9, 9))
    lx, ly = math.sin(th), math.cos(th)
    wx, wy = math.cos(th), -math.sin(th)
    ring = []
    for sl, sw in ((-0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0.5, -0.5)):
        ex = length * sl * lx + width * sw * wx
        ny = length * sl * ly + width * sw * wy
        ring.append([clon + ex * FT / math.cos(math.radians(clat)), clat + ny * FT])
    ring.append(ring[0])

    # Leave a few genuinely absent so the unmeasured and occluded states are visible
    # in the demo rather than only in theory.
    props = {
        "site_number": 1201 + i,
        "pad_surface": "concrete",
        "backs_onto": random.choice(BACKS),
        "approach_side": "left" if side > 0 else "right",
        "imagery_vintage": random.choice(VINTAGES),
        "number_confidence": "hypothesis",
    }
    if i in (7, 15):
        props["notes"] = "occluded"
        props.pop("imagery_vintage")
    if i == 11:
        props["notes"] = "DEMO placeholder — pull-through candidate, unverified"

    features.append({
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [ring]},
        "properties": props,
    })

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({"type": "FeatureCollection", "features": features}, open(OUT, "w"))
print(f"wrote {len(features)} synthetic pads -> {OUT}")

result = subprocess.run(
    [sys.executable, os.path.join(HERE, "derive.py"), str(LOOP), OUT, "--demo"],
    cwd=HERE,
)
sys.exit(result.returncode)
