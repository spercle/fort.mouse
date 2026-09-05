"""Generate a calibration panorama for testing the 360 viewer.

    python3 pipeline/make_test_pano.py            # writes into incoming/

A real photograph is a bad test for a projection. It looks plausible whichever way you
map it, so a viewer that is subtly wrong — off by a hemisphere, poles pinched the wrong
way, seam in the middle instead of behind you — still looks like a nice picture of a
campsite. A grid does not: if the horizon is not straight, or north is not where the
marker says, you can see it immediately.

It also sidesteps the photo policy. A stock 360 of somebody else's campsite on a Site
page is exactly what docs/data-model.md forbids, and this is unmistakably not a
photograph of anywhere.

What it draws, on a 2:1 equirectangular grid:

  * a coloured quadrant per cardinal direction — N red, E green, S blue, W yellow
  * 1/2/3/4 bars stacked at the horizon at N/E/S/W, so a 90 degrees error is obvious
  * meridians and parallels every 15 degrees, doubled at the equator and at due north
  * a bright zenith cap and a dark nadir cap, so the poles are told apart at a glance

PNG is written by hand, because zlib is in the standard library and this project does
not take an image dependency for something this small. sips converts it to JPEG, and
the GPano XMP is injected afterwards — sips does not preserve it, which is the whole
reason ingest_photos.py records the projection in the manifest instead of trusting the
file to still say so.
"""

import argparse
import os
import struct
import subprocess
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCOMING = os.path.join(ROOT, "incoming")

# Quadrant tints, centred on each cardinal direction. Deliberately not a smooth wheel:
# a hard edge every 90 degrees is what makes a rotation error visible.
QUADRANT = [
    (150, 60, 60),    # N
    (60, 140, 70),    # E
    (60, 80, 160),    # S
    (150, 140, 55),   # W
]
LINE = (245, 245, 245)
ZENITH = (250, 250, 235)
NADIR = (28, 28, 32)

XMP_NS = b"http://ns.adobe.com/xap/1.0/\x00"


def gpano_xmp(width, height):
    """The Photo Sphere XMP block, as a camera would write it.

    This is the marker ingest_photos.py looks for. Google's spec calls for the full
    cropped-area set even on an uncropped sphere, so all of it is here rather than the
    two tags a lenient reader would settle for.
    """
    return (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" '
        'xmlns:GPano="http://ns.google.com/photos/1.0/panorama/" '
        'GPano:ProjectionType="equirectangular" '
        'GPano:UsePanoramaViewer="True" '
        f'GPano:FullPanoWidthPixels="{width}" '
        f'GPano:FullPanoHeightPixels="{height}" '
        f'GPano:CroppedAreaImageWidthPixels="{width}" '
        f'GPano:CroppedAreaImageHeightPixels="{height}" '
        'GPano:CroppedAreaLeftPixels="0" '
        'GPano:CroppedAreaTopPixels="0" '
        'GPano:PoseHeadingDegrees="0"/>'
        '</rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
    ).encode("utf-8")


def write_png(path, width, height, rows):
    """Minimal RGB8 PNG. Each row is prefixed with filter byte 0 (None)."""
    raw = bytearray()
    for row in rows:
        raw.append(0)
        raw += row

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
        fh.write(chunk(b"IHDR", ihdr))
        fh.write(chunk(b"IDAT", zlib.compress(bytes(raw), 6)))
        fh.write(chunk(b"IEND", b""))


def draw(width, height):
    """Yield one row of RGB bytes at a time, so the full 25 MB is never all resident."""
    # Bars at the horizon: 1 at N, 2 at E, 3 at S, 4 at W. Counting them tells you
    # which way you are facing without needing to render a single glyph.
    bar_h = max(2, height // 90)
    for y in range(height):
        # Latitude: +90 at the top row, -90 at the bottom.
        lat = 90.0 - (y + 0.5) * 180.0 / height
        row = bytearray()
        near_parallel = (abs(((lat + 7.5) % 15.0) - 7.5) < (90.0 / height))
        on_equator = abs(lat) < (180.0 / height)
        for x in range(width):
            # Longitude 0 at the centre of the image, increasing east, so due north
            # is dead ahead when the viewer opens — the convention a stitched sphere
            # uses and the one the shader assumes.
            lon = (x + 0.5) * 360.0 / width - 180.0
            if lat > 82:
                row += bytes(ZENITH)
                continue
            if lat < -82:
                row += bytes(NADIR)
                continue

            quad = int(((lon + 45.0) % 360.0) // 90.0)
            r, g, b = QUADRANT[quad]
            # Fade toward the poles so latitude is readable, not just longitude.
            k = 1.0 - abs(lat) / 120.0
            r, g, b = int(r * k), int(g * k), int(b * k)

            near_meridian = (abs(((lon + 7.5) % 15.0) - 7.5) < (180.0 / width))
            on_north = abs(lon) < (360.0 / width)
            if on_equator or on_north:
                r, g, b = LINE
            elif near_parallel or near_meridian:
                r, g, b = (min(255, r + 70), min(255, g + 70), min(255, b + 70))

            # The counting bars, stacked just above the horizon. The separation is
            # measured the short way round, or the bars at due south — which sits at
            # both edges — would be dropped.
            centre = quad * 90.0
            if abs(((lon - centre + 180.0) % 360.0) - 180.0) < 9.0:
                n = quad + 1
                for i in range(n):
                    top = -6.0 - i * 4.0
                    if top - 2.5 < lat < top:
                        r, g, b = LINE
            row += bytes((r, g, b))
        yield row


def inject_xmp(path, width, height):
    """Insert an XMP APP1 segment straight after SOI, the way a camera writes it."""
    data = open(path, "rb").read()
    if data[:2] != b"\xff\xd8":
        raise SystemExit(f"{path}: not a JPEG, cannot add the GPano marker")
    payload = XMP_NS + gpano_xmp(width, height)
    seg = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    open(path, "wb").write(data[:2] + seg + data[2:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=4096,
                    help="long edge; height is always half of it")
    ap.add_argument("--out", default=os.path.join(INCOMING, "816-360-testpattern.jpg"),
                    help="where to write the JPEG")
    args = ap.parse_args()

    width = args.width
    height = width // 2
    if width % 2:
        sys.exit("width must be even — an equirectangular image is exactly 2:1")

    tmp = args.out + ".png"
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    print(f"  drawing {width}x{height} calibration grid...")
    write_png(tmp, width, height, draw(width, height))

    r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80",
                        tmp, "--out", args.out], capture_output=True)
    os.remove(tmp)
    if r.returncode != 0 or not os.path.exists(args.out):
        sys.exit("sips could not convert the PNG: "
                 + (r.stderr or b"").decode()[:200])

    inject_xmp(args.out, width, height)
    mb = os.path.getsize(args.out) / 1e6
    print(f"  {os.path.relpath(args.out, ROOT)}  {width}x{height}  {mb:.1f}MB")
    print("  tagged GPano:ProjectionType=equirectangular")
    print("\n  now:  python3 pipeline/ingest_photos.py")


if __name__ == "__main__":
    main()
