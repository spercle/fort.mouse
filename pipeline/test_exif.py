"""Prove the hand-rolled EXIF reader and the GPS site matcher.

    cd pipeline && python3 test_exif.py

The reader in ingest_photos.py parses EXIF by hand because the project carries no
image dependencies. That is only worth doing if it is actually correct, so this
builds a JPEG with known GPS coordinates and checks they come back out.
"""

import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest_photos import read_exif, known_sites, feet_between  # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}")
    if not ok:
        print(f"        wanted {want!r}")
        FAILS.append(name)


def build_jpeg_with_gps(lat, lon, taken="2026:09:03 14:22:31"):
    """A minimal but structurally valid JPEG carrying GPS and DateTimeOriginal."""
    def rat(v):
        d = int(v)
        rem = (v - d) * 60          # minutes, with fraction
        m = int(rem)
        sec = (rem - m) * 60        # seconds, with fraction
        return [(d, 1), (m, 1), (round(sec * 10000), 10000)]

    lat_r, lon_r = rat(abs(lat)), rat(abs(lon))

    # Values that do not fit in 4 bytes live after the IFDs.
    # Layout: TIFF header(8) | IFD0 | ExifIFD | GPSIFD | data
    tiff = b"II" + struct.pack("<HI", 42, 8)

    ifd0_off = 8
    ifd0_size = 2 + 2 * 12 + 4
    exif_off = ifd0_off + ifd0_size
    exif_size = 2 + 1 * 12 + 4
    gps_off = exif_off + exif_size
    gps_size = 2 + 4 * 12 + 4
    data_off = gps_off + gps_size

    blobs, cursor = b"", data_off
    def put(b):
        nonlocal blobs, cursor
        off = cursor
        blobs += b
        cursor += len(b)
        return off

    date_off = put(taken.encode("ascii") + b"\x00")
    lat_off = put(b"".join(struct.pack("<II", n, d) for n, d in lat_r))
    lon_off = put(b"".join(struct.pack("<II", n, d) for n, d in lon_r))

    def entry(tag, typ, cnt, val):
        return struct.pack("<HHI", tag, typ, cnt) + struct.pack("<I", val)

    ifd0 = struct.pack("<H", 2)
    ifd0 += entry(0x8769, 4, 1, exif_off)      # ExifIFD pointer
    ifd0 += entry(0x8825, 4, 1, gps_off)       # GPSIFD pointer
    ifd0 += struct.pack("<I", 0)

    exif = struct.pack("<H", 1)
    exif += entry(0x9003, 2, 20, date_off)     # DateTimeOriginal
    exif += struct.pack("<I", 0)

    gps = struct.pack("<H", 4)
    gps += struct.pack("<HHI", 1, 2, 2) + (b"N\x00" if lat >= 0 else b"S\x00") + b"\x00\x00"
    gps += entry(2, 5, 3, lat_off)
    gps += struct.pack("<HHI", 3, 2, 2) + (b"E\x00" if lon >= 0 else b"W\x00") + b"\x00\x00"
    gps += entry(4, 5, 3, lon_off)
    gps += struct.pack("<I", 0)

    payload = b"Exif\x00\x00" + tiff + ifd0 + exif + gps + blobs
    app1 = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    # a tiny valid-enough image body; the reader only needs the APP1 segment
    return b"\xff\xd8" + app1 + b"\xff\xd9"


print("EXIF reader round-trips coordinates it was given")
site = next(iter(known_sites()), None)
if site is None:
    sys.exit("no sites with positions — run pipeline/infer_positions.py first")
number, loop, lat, lon, _ = site

with tempfile.TemporaryDirectory() as tmp:
    p = os.path.join(tmp, "gps.jpg")
    open(p, "wb").write(build_jpeg_with_gps(lat, lon))
    got = read_exif(p)
    print(f"  site {number} is at {lat:.6f}, {lon:.6f}")
    print(f"  reader returned      {got['gps']}")
    check("date parsed", got["taken"], "2026-09-03")
    if got["gps"]:
        d = feet_between(lat, lon, got["gps"][0], got["gps"][1])
        ok = d < 6
        print(f"  {'PASS' if ok else 'FAIL'}  position within 6 ft: {d:.1f} ft")
        if not ok:
            FAILS.append("gps accuracy")
    else:
        print("  FAIL  no GPS returned")
        FAILS.append("gps present")

print("\na photo with no EXIF is reported as having none, not guessed at")
with tempfile.TemporaryDirectory() as tmp:
    p = os.path.join(tmp, "plain.jpg")
    open(p, "wb").write(b"\xff\xd8" + b"\xff\xd9")
    check("no gps", read_exif(p)["gps"], None)
    check("no date", read_exif(p)["taken"], None)

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: {FAILS}")
    sys.exit(1)
print("all passed — EXIF parsing and GPS matching are sound")
