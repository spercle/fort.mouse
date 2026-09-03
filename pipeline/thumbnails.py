"""Cut a per-site aerial thumbnail from the county orthoimagery.

    python3 pipeline/thumbnails.py 1200

Writes static/aerial/<site>.jpg for every site in the loop that has a centroid.

These are legitimately publishable: the imagery is Orange County / State of Florida
orthoimagery, a public record under Florida Statutes ch. 119 — see ADR-0003. It is the
one kind of per-site image this project can produce at scale without anyone's fieldwork.

A thumbnail is only as accurate as the centroid it was cut from, so sites whose numbering
is a hypothesis get an image of roughly the right ground, not certainly the right pad.
The site page says so.
"""

import json
import math
import os
import ssl
import sys
import urllib.parse
import urllib.request

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "static", "aerial")

VINTAGE = "2025"
SERVICE = (
    "https://vgispublic.ocpafl.org/server/rest/services/OCPA/"
    f"Aerials{VINTAGE}/MapServer/export"
)
HALF_FT = 60          # a 120 ft window comfortably holds a 60 ft pad plus context
PIXELS = 512

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def crop(lat, lon, dest):
    dlat = HALF_FT / 364000.0
    dlon = dlat / math.cos(math.radians(lat))
    params = {
        "bbox": f"{lon - dlon},{lat - dlat},{lon + dlon},{lat + dlat}",
        "bboxSR": "4326",
        "imageSR": "4326",
        "size": f"{PIXELS},{PIXELS}",
        "format": "jpg",
        "f": "image",
    }
    req = urllib.request.Request(
        SERVICE + "?" + urllib.parse.urlencode(params),
        headers={"User-Agent": "fort-mouse/0.1"},
    )
    data = urllib.request.urlopen(req, timeout=90, context=ctx).read()
    if data[:2] != b"\xff\xd8":
        raise RuntimeError("server did not return a JPEG")
    open(dest, "wb").write(data)
    return len(data)


def main():
    if "--loops" in sys.argv:
        loop_overviews()
        return
    loop = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    path = os.path.join(ROOT, "data", "loops", f"{loop}.yaml")
    data = yaml.safe_load(open(path))

    os.makedirs(OUT_DIR, exist_ok=True)
    done = skipped = 0

    for site in data.get("sites", []):
        centroid = site.get("centroid")   # never inferred_centroid — see infer_positions.py
        if not centroid:
            skipped += 1
            continue
        n = site["site_number"]
        dest = os.path.join(OUT_DIR, f"{n}.jpg")
        try:
            size = crop(centroid[0], centroid[1], dest)
            done += 1
            print(f"  {n}  {size:>7,}B")
        except Exception as exc:
            skipped += 1
            print(f"  {n}  FAILED {exc}")

    print(f"\n{done} thumbnails written to static/aerial/, {skipped} skipped")
    print(f"Source: Orange County {VINTAGE} orthoimagery (public record, ADR-0003)")



def loop_overviews():
    """One aerial per loop, framed on its road centreline.

    This is the legitimate answer to wanting a picture for every loop: county
    orthoimagery is a Florida public record (ADR-0003), so these are ours to publish,
    and no other Fort Wilderness resource has them.
    """
    ref = os.path.join(ROOT, "data", "reference")
    out = os.path.join(ROOT, "static", "loop-aerial")
    os.makedirs(out, exist_ok=True)
    done = 0

    for f in sorted(os.listdir(ref)):
        if not f.endswith("-osm-road.geojson"):
            continue
        loop = f.split("-")[1]
        fc = json.load(open(os.path.join(ref, f)))
        pts = [p for feat in fc["features"] for p in feat["geometry"]["coordinates"]]
        if not pts:
            continue

        lons = [p[0] for p in pts]
        lats = [p[1] for p in pts]
        clat, clon = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
        # square window with a margin, so every loop is framed the same way
        pad = 1.25
        dlat = max(max(lats) - min(lats),
                   (max(lons) - min(lons)) * math.cos(math.radians(clat))) / 2 * pad
        dlat = max(dlat, 0.0004)
        dlon = dlat / math.cos(math.radians(clat))

        params = {
            "bbox": f"{clon - dlon},{clat - dlat},{clon + dlon},{clat + dlat}",
            "bboxSR": "4326", "imageSR": "4326", "size": "900,900",
            "format": "jpg", "f": "image",
        }
        req = urllib.request.Request(
            SERVICE + "?" + urllib.parse.urlencode(params),
            headers={"User-Agent": "fort-mouse/0.1"})
        try:
            data = urllib.request.urlopen(req, timeout=120, context=ctx).read()
            if data[:2] != b"\xff\xd8":
                raise RuntimeError("not a JPEG")
            open(os.path.join(out, f"{loop}.jpg"), "wb").write(data)
            done += 1
            print(f"  loop {loop}  {len(data):>8,}B")
        except Exception as exc:
            print(f"  loop {loop}  FAILED {exc}")

    print(f"\n{done} loop overviews -> static/loop-aerial/")

if __name__ == "__main__":
    main()
