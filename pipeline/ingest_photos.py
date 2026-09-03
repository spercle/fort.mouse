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
# Live Photos arrive as a HEIC plus a MOV of the same name. The still is what a web
# page needs; the movie is 4-5 MB of nothing useful here.
SKIP_EXTS = {".mov", ".mp4", ".aae"}
# NAS and OS droppings that are not photographs.
SKIP_NAMES = {"@eadir", ".ds_store", "thumbs.db", ".spotlight-v100"}
MAX_EDGE = 2000          # published long edge; phones now shoot 5712 px
JPEG_QUALITY = 78
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
    out = {"gps": None, "taken": None, "orientation": None}
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
        elif tag == 0x0112:                      # Orientation
            out["orientation"] = struct.unpack(endian + "H", app1[voff:voff + 2])[0]

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


def clear_orientation(path):
    """Set the EXIF orientation tag to 1, in place.

    sips -r rotates the pixels but leaves the tag alone, so a browser — which
    honours the tag — rotates the already-rotated image a second time and shows it
    upside down. Viewers that ignore EXIF show it correctly, which is exactly how
    this got shipped once.
    """
    data = bytearray(open(path, "rb").read())
    if data[:2] != b"\xff\xd8":
        return False
    i, base = 2, None
    while i < len(data) - 4:
        if data[i] != 0xFF:
            break
        marker, size = data[i + 1], struct.unpack(">H", bytes(data[i + 2:i + 4]))[0]
        if marker == 0xE1 and data[i + 4:i + 10] == b"Exif\x00\x00":
            base = i + 10
            break
        i += 2 + size
    if base is None:
        return False

    endian = "<" if data[base:base + 2] == b"II" else ">"
    ifd0 = struct.unpack(endian + "I", bytes(data[base + 4:base + 8]))[0]
    off = base + ifd0
    if off + 2 > len(data):
        return False
    n = struct.unpack(endian + "H", bytes(data[off:off + 2]))[0]
    for k in range(n):
        e = off + 2 + k * 12
        if e + 12 > len(data):
            break
        tag = struct.unpack(endian + "H", bytes(data[e:e + 2]))[0]
        if tag == 0x0112:
            data[e + 8:e + 10] = struct.pack(endian + "H", 1)
            open(path, "wb").write(bytes(data))
            return True
    return False


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
    # Skip the yyyymmdd_hhmmss in phone filenames, or IMG_20251116_170758 matches
    # nothing useful and 1116 could collide with a real site number.
    cleaned = re.sub(r"\b(19|20)\d{6}[_-]?\d{0,6}\b", " ", name)
    for m in re.finditer(r"(?<!\d)(\d{3,4})(?!\d)", cleaned):
        n = int(m.group(1))
        if n in valid:
            return n
    return None


def date_from_name(name):
    """Phone filenames carry the capture time when EXIF has been stripped."""
    m = re.search(r"\b((?:19|20)\d{2})(\d{2})(\d{2})\b", name)
    if m:
        y, mo, d = m.groups()
        if "01" <= mo <= "12" and "01" <= d <= "31":
            return f"{y}-{mo}-{d}"
    return None


def collect(root):
    """Every photo under incoming/, with the folder name as a site hint."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_NAMES
                       and not d.startswith(".")]
        hint = os.path.basename(dirpath)
        hint = int(hint) if hint.isdigit() else None
        for fn in sorted(filenames):
            if fn.lower() in SKIP_NAMES or fn.startswith("."):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in SKIP_EXTS or ext not in EXTS:
                continue
            found.append((os.path.join(dirpath, fn), fn, hint))
    return found


def convert(src, dest):
    """Normalise to a web-sized JPEG with the rotation baked into the pixels.

    Browsers honour EXIF orientation, but resizing tools routinely drop the tag and
    leave the image sideways. Baking it in removes the question. Uses macOS sips,
    which is the only image tool this project assumes.
    """
    import subprocess
    def dims(path):
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                             capture_output=True).stdout.decode()
        w = h = 0
        for line in out.splitlines():
            if "pixelWidth" in line:
                w = int(line.split(":")[1])
            elif "pixelHeight" in line:
                h = int(line.split(":")[1])
        return w, h

    src_w, src_h = dims(src)
    # Only ever shrink. Passing a max larger than the image made sips upscale a
    # 1164px photo to 3436px, which is worse than doing nothing.
    target = min(MAX_EDGE, max(src_w, src_h)) or MAX_EDGE

    # Convert and rotate in one pass. Chaining a second sips call over the output
    # re-encoded it down to 700px.
    ori = read_exif(src).get("orientation")
    cmd = ["sips", "-s", "format", "jpeg",
           "-s", "formatOptions", str(JPEG_QUALITY),
           "-Z", str(target)]
    if ori in (3, 6, 8):
        cmd += ["-r", str({3: 180, 6: 90, 8: 270}[ori])]
    cmd += [src, "--out", dest]

    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not os.path.exists(dest):
        return False, (r.stderr or b"").decode()[:80]

    out_w, out_h = dims(dest)
    if max(out_w, out_h) > MAX_EDGE or out_w < 400:
        return False, f"unexpected output size {out_w}x{out_h} from {src_w}x{src_h}"

    # The rotation is in the pixels now, so the tag must stop claiming it is needed.
    if ori in (3, 6, 8):
        clear_orientation(dest)
        still = read_exif(dest).get("orientation")
        if still not in (None, 1):
            return False, f"orientation tag still {still} after rotating"
    return True, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually move the files")
    args = ap.parse_args()

    os.makedirs(INCOMING, exist_ok=True)
    found = collect(INCOMING)
    if not found:
        print("  nothing in incoming/ — drop photos there and run this again")
        return

    sites = known_sites()
    valid = {n for n, _, _, _, _ in sites}
    manifest = yaml.safe_load(open(MANIFEST)) if os.path.exists(MANIFEST) else None
    manifest = manifest or {"photos": []}

    planned, unmatched = [], []
    for path, fn, folder_hint in found:
        exif = read_exif(path)
        size = os.path.getsize(path)

        site, how, dist = None, None, None
        if folder_hint in valid:
            site, how = folder_hint, "folder"
        if site is None:
            site = site_from_name(fn, valid)
            how = "filename" if site else None
        if site is None and exif["gps"]:
            best = min(sites, key=lambda s: feet_between(
                exif["gps"][0], exif["gps"][1], s[2], s[3]))
            d = feet_between(exif["gps"][0], exif["gps"][1], best[2], best[3])
            if d <= MAX_MATCH_FT:
                site, how, dist = best[0], "gps", round(d, 1)

        taken = exif["taken"] or date_from_name(fn)
        if site is None:
            unmatched.append((fn, size, exif))
            continue
        planned.append({"src": path, "name": fn, "site": site, "how": how,
                        "dist": dist, "taken": taken, "gps": exif["gps"],
                        "size": size, "orientation": exif["orientation"]})

    print(f"  {len(found)} photo(s) under incoming/\n")
    counts = {}
    for p in planned:
        prior = sum(1 for q in manifest["photos"] if q["site"] == p["site"])
        counts[p["site"]] = counts.get(p["site"], prior) + 1
        p["dest"] = f"static/photos/{p['site']}-{counts[p['site']]}.jpg"
        via = p["how"] + (f", {p['dist']} ft away" if p["dist"] is not None else "")
        rot = f"  rotate {({3: 180, 6: 90, 8: 270}).get(p['orientation'], 0)}deg" \
              if p["orientation"] in (3, 6, 8) else ""
        mb = p["size"] / 1e6
        print(f"  {p['name']:<30} -> site {p['site']}  [{via}]"
              f"  {mb:.1f}MB{rot}")
    if unmatched:
        print()
        for fn, size, exif in unmatched:
            why = "no site number, no GPS" if not exif["gps"] else "GPS not near a site"
            print(f"  {fn:<30} -> LEFT ALONE  ({why})")

    skipped = 0
    for dirpath, dirnames, filenames in os.walk(INCOMING):
        dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_NAMES
                       and not d.startswith(".")]
        skipped += sum(1 for f in filenames
                       if os.path.splitext(f)[1].lower() in SKIP_EXTS)
    if skipped:
        print(f"\n  {skipped} Live Photo movie(s) ignored — the still is what a page needs")

    if not args.apply:
        print(f"\n  dry run. {len(planned)} would be filed, {len(unmatched)} left alone.")
        print("  Re-run with --apply to convert and move them.")
        return

    os.makedirs(PHOTOS, exist_ok=True)
    done = 0
    for p in planned:
        dest_abs = os.path.join(ROOT, p["dest"])
        ok, err = convert(p["src"], dest_abs)
        if not ok:
            print(f"  {p['name']}: CONVERSION FAILED {err}")
            continue
        # The source is moved aside, never deleted. A conversion can go wrong in
        # ways that are not obvious until the page is looked at, and the original
        # is the only thing that makes that recoverable.
        keep = os.path.join(INCOMING, "_filed",
                            os.path.relpath(p["src"], INCOMING))
        os.makedirs(os.path.dirname(keep), exist_ok=True)
        shutil.move(p["src"], keep)
        done += 1
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
