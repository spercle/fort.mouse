"""Cut an aerial basemap that lines up exactly with a loop's drawn map.

    python3 pipeline/loop_basemap.py 100

Writes static/loop-base/<loop>.jpg — county orthoimagery covering precisely the
geographic bounds of the loop map's frame, at the same aspect ratio, so when
loop_maps.py places it behind the drawing every road, tree and pad sits where it
actually is on the ground.

This is the answer to "the sites do not line up". The drawn road comes from
OpenStreetMap and the pad positions are arithmetic; neither is grounded in the
imagery. Putting the photograph underneath means the drawing is measured against
reality on every single view, and any pad in the wrong place is obvious.

Requires the frame maths in loop_maps.py, so the two cannot drift apart.
"""

import json
import math
import os
import ssl
import sys
import urllib.parse
import urllib.request

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from loop_maps import W, H, Frame, to_ft, load_pads, EARTH_FT  # noqa: E402

ROOT = os.path.dirname(HERE)
REF = os.path.join(ROOT, "data", "reference")
OUT = os.path.join(ROOT, "static", "loop-base")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 2025 and 2022 are the sharp vintages over Fort Wilderness; 2024 is soft through
# the export endpoint. See docs/research/imagery-and-measurement.md.
VINTAGE = "2025"
SERVICE = ("https://vgispublic.ocpafl.org/server/rest/services/OCPA/"
           f"Aerials{VINTAGE}/MapServer/export")


def frame_bounds(loop):
    """The lat/lon rectangle the drawn map actually covers."""
    road = [c for f in json.load(
        open(os.path.join(REF, f"loop-{loop}-osm-road.geojson")))["features"]
        for c in f["geometry"]["coordinates"]]
    origin = (road[0][0], road[0][1])
    road_ft = to_ft(road, origin)
    pads = load_pads(loop, origin)
    frame = Frame(road_ft, [p["ft"] for p in pads])

    # invert the projection at the two corners of the viewBox
    def unproject(px, py):
        x_ft = (px - frame.ox) / frame.scale
        y_ft = (frame.oy - py) / frame.scale
        k = math.radians(1) * EARTH_FT
        lat = origin[1] + y_ft / k
        lon = origin[0] + x_ft / (k * math.cos(math.radians(origin[1])))
        return lon, lat

    west, north = unproject(0, 0)
    east, south = unproject(W, H)
    return west, south, east, north


def main():
    loop = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    west, south, east, north = frame_bounds(loop)

    params = {
        "bbox": f"{west},{south},{east},{north}",
        "bboxSR": "4326", "imageSR": "4326",
        # Twice the viewBox, so the photograph still holds up on a retina screen.
        "size": f"{W * 2},{H * 2}",
        "format": "jpg", "f": "image",
    }
    req = urllib.request.Request(SERVICE + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": "fort-mouse/0.1"})
    data = urllib.request.urlopen(req, timeout=120, context=CTX).read()
    if data[:2] != b"\xff\xd8":
        sys.exit("server did not return a JPEG")

    os.makedirs(OUT, exist_ok=True)
    dest = os.path.join(OUT, f"{loop}.jpg")
    open(dest, "wb").write(data)

    span_ft = (east - west) * math.cos(math.radians(south)) * math.radians(1) * EARTH_FT
    print(f"  loop {loop}: {len(data):,}B  {W*2}x{H*2}px covering {span_ft:.0f} ft across")
    print(f"  bbox {west:.6f},{south:.6f} -> {east:.6f},{north:.6f}")
    print(f"  -> {dest}")


if __name__ == "__main__":
    main()
