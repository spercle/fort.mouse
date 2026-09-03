"""Take photos out of incoming/ and file them against the right campsite.

    python3 pipeline/ingest_photos.py            # dry run: says what it would do
    python3 pipeline/ingest_photos.py --apply    # actually move and record them

Drop photos into `incoming/` with any filename. Each is matched to a site by, in
order of confidence:

  1. a site number in the filename       — "1204.jpg", "site 1204 pad.jpg"
  2. GPS coordinates in the photo's EXIF — matched to the nearest known site
  3. nothing                             — reported and left alone, never guessed

A GPS-tagged photo is worth more than an image: it is a position fix taken standing
on the site, which is the one thing aerial imagery cannot give us. Where a photo's
coordinates land within a sensible distance of a site, that distance is recorded so
it can be judged later.

EXIF is parsed here rather than with a library, because the project has no image
dependencies and reading a few tags is a hundred lines.
"""

import argparse
import os
import re
import shutil
import struct
import sys
from datetime import datetime

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCOMING = os.path.join(ROOT, "incoming")
PHOTOS = os.path.join(ROOT, "static", "photos")
MANIFEST = os.path.join(ROOT, "data", "photos.yaml")
LOOPS = os.path.join(ROOT, "data", "loops")

EXTS = {".jpg", ".jpeg", ".png", ".heic"}
MAX_MATCH_FT = 160.0     # beyond this a GPS fix is not confidently "that site"
EARTH_FT = 20925721.8


# --------------------------------------------------------------------------
# EXIF, by hand
# --------------------------------------------------------------------------

def _rational(buf, off, endian):
    num, den = struct.unpack(endian + "II", buf[off:off + 8])
    return num / den if den else 0.0


def read_exif(path):
    """Return {'gps': (lat, lon) | None, 'taken': 'YYYY-MM-DD' | None}."""
    out = {"gps": None, "taken": None}
    try:
        data = open(path, "rb").read(256 * 1024)
    except OSError:
        return out
    if data[:2] != b"\xff\xd8":
        return out

    # find the APP1 segment holding "Exif\0\0"
    i, app1 = 2, None
    while i < len(data) - 4:
        if data[i] != 0xFF:
            break
        marker, size = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker == 0xE1 and data[i + 4:i + 10] == b"Exif\x00\x00":
            app1 = data[i + 10:i + 2 + size]
            break
        i += 2 + size
    if not app1 or len(app1) < 8:
        return out

    endian = "<" if app1[:2] == b"II" else ">"
    ifd0 = struct.unpack(endian + "I", app1[4:8])[0]

    def entries(offset):
        if offset + 2 > len(app1):
            return
        n = struct.unpack(endian + "H", app1[offset:offset + 2])[0]
        for k in range(n):
            e = offset + 2 + k * 12
            if e + 12 > len(app1):
                return
            tag, typ, cnt = struct.unpack(endian + "HHI", app1[e:e + 8])
            yield tag, typ, cnt, e + 8

    def ptr(voff):
        return struct.unpack(endian + "I", app1[voff:voff + 4])[0]

    gps_off = exif_off = None
    for tag, typ, cnt, voff in entries(ifd0):
        if tag == 0x8825:
            gps_off = ptr(voff)
        elif tag == 0x8769:
            exif_off = ptr(voff)

    if exif_off:
        for tag, typ, cnt, voff in entries(exif_off):
            if tag == 0x9003 and cnt >= 19:          # DateTimeOriginal
                s = app1[ptr(voff):ptr(voff) + 19].decode("ascii", "ignore")
                try:
                    out["taken"] = datetime.strptime(
                        s, "%Y:%m:%d %H:%M:%S").date().isoformat()
                except ValueError:
                    pass

    if gps_off:
        vals = {}
        for tag, typ, cnt, voff in entries(gps_off):
            if tag in (1, 3) and cnt >= 2:           # N/S, E/W
                vals[tag] = app1[voff:voff + 1].decode("ascii", "ignore")
            elif tag in (2, 4) and cnt == 3:         # lat, lon as 3 rationals
                base = ptr(voff)
                vals[tag] = [_rational(app1, base + 8 * j, endian) for j in range(3)]
        if 2 in vals and 4 in vals:
            def dms(v):
                return v[0] + v[1] / 60 + v[2] / 3600
            lat, lon = dms(vals[2]), dms(vals[4])
            if vals.get(1, "N") == "S":
                lat = -lat
            if vals.get(3, "E") == "W":
                lon = -lon
            if lat or lon:
                out["gps"] = (round(lat, 7), round(lon, 7))
    return out


# --------------------------------------------------------------------------

def known_sites():
    """Every site we have any position for, real centroid preferred."""
    out = []
    for f in sorted(os.listdir(LOOPS)):
        if not f.endswith(".yaml"):
            continue
        d = yaml.safe_load(open(os.path.join(LOOPS, f))) or {}
        for s in d.get("sites") or []:
            c = s.get("centroid") or s.get("inferred_centroid")
            if c:
                out.append((s["site_number"], d["loop"], c[0], c[1],
                            bool(s.get("centroid"))))
    return out


def feet_between(a_lat, a_lon, b_lat, b_lon):
    import math
    la1, lo1, la2, lo2 = map(math.radians, (a_lat, a_lon, b_lat, b_lon))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * EARTH_FT * math.asin(math.sqrt(h))


def site_from_name(name, valid):
    for m in re.finditer(r"\b(\d{3,4})\b", name):
        n = int(m.group(1))
        if n in valid:
            return n
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually move the files")
    args = ap.parse_args()

    os.makedirs(INCOMING, exist_ok=True)
    files = [f for f in sorted(os.listdir(INCOMING))
             if os.path.splitext(f)[1].lower() in EXTS]
    if not files:
        print(f"  nothing in incoming/ — drop photos there and run this again")
        return

    sites = known_sites()
    valid = {n for n, _, _, _, _ in sites}
    manifest = yaml.safe_load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    manifest = manifest or {"photos": []}
    existing = {p["file"] for p in manifest["photos"]}

    planned, unmatched = [], []
    for f in files:
        path = os.path.join(INCOMING, f)
        size = os.path.getsize(path)
        exif = read_exif(path)

        site = site_from_name(f, valid)
        how, dist = ("filename", None) if site else (None, None)

        if site is None and exif["gps"]:
            best = min(sites, key=lambda s: feet_between(
                exif["gps"][0], exif["gps"][1], s[2], s[3]))
            d = feet_between(exif["gps"][0], exif["gps"][1], best[2], best[3])
            if d <= MAX_MATCH_FT:
                site, how, dist = best[0], "gps", round(d, 1)

        if site is None:
            unmatched.append((f, size, exif))
            continue
        planned.append({"src": f, "site": site, "how": how, "dist": dist,
                        "taken": exif["taken"], "gps": exif["gps"], "size": size})

    print(f"  {len(files)} file(s) in incoming/\n")
    for p in planned:
        n = sum(1 for q in manifest["photos"] if q["site"] == p["site"]) + \
            sum(1 for q in planned[:planned.index(p)] if q["site"] == p["site"])
        # Keep the real format. Naming a PNG or a HEIC ".jpg" would be a lie the
        # browser sniffs past but every other tool trips over.
        ext = os.path.splitext(p["src"])[1].lower()
        ext = ".jpg" if ext == ".jpeg" else ext
        dest = f"static/photos/{p['site']}-{n + 1}{ext}"
        via = p["how"] + (f", {p['dist']} ft away" if p["dist"] is not None else "")
        big = "  (large — consider resizing)" if p["size"] > 3_000_000 else ""
        print(f"  {p['src']:<28} -> site {p['site']}  [{via}]{big}")
        p["dest"] = dest
    if unmatched:
        print()
        for f, size, exif in unmatched:
            why = "no site number in the name, no GPS" if not exif["gps"] else \
                  "GPS is not near any known site"
            print(f"  {f:<28} -> LEFT ALONE  ({why})")

    if not args.apply:
        print(f"\n  dry run. {len(planned)} would be filed, {len(unmatched)} left alone.")
        print("  Re-run with --apply to move them.")
        return

    os.makedirs(PHOTOS, exist_ok=True)
    for p in planned:
        dest_abs = os.path.join(ROOT, p["dest"])
        shutil.move(os.path.join(INCOMING, p["src"]), dest_abs)
        manifest["photos"].append({
            "site": p["site"],
            "file": "/" + p["dest"].split("static/", 1)[1],
            "taken": p["taken"],
            "matched_by": p["how"],
            "gps": list(p["gps"]) if p["gps"] else None,
            "gps_distance_ft": p["dist"],
            "credit": "own",
            "added": datetime.now().date().isoformat(),
        })
    manifest["photos"].sort(key=lambda x: (x["site"], x["file"]))
    with open(MANIFEST, "w") as fh:
        yaml.safe_dump(manifest, fh, sort_keys=False, allow_unicode=True)
    print(f"\n  moved {len(planned)}, recorded in data/photos.yaml")
    print("  run ./build.sh to see them on the site")


if __name__ == "__main__":
    main()
