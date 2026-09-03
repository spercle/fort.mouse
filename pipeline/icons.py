"""Generate the site icons. No dependencies — rasteriser and PNG writer included.

    python3 pipeline/icons.py

Writes static/favicon-32.png, apple-touch-icon.png (180), icon-192.png, icon-512.png
and icon-maskable-512.png, alongside the hand-written static/icon.svg that modern
browsers prefer.

The mark is a routed wooden sign carrying a pine — the site's whole visual language in
one shape, and only two tones so it survives being 16 pixels wide.

There is no ImageMagick, rsvg, cairosvg or Pillow on this machine and none is wanted.
The shapes are simple enough to rasterise directly: a rounded rectangle, a polygon, a
rectangle and a circle, sampled 3x3 per pixel for antialiasing, then deflated into a PNG.
"""

import math
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static")

BARK = (0x43, 0x30, 0x1f)
BARK_DARK = (0x2b, 0x1e, 0x12)
CANVAS = (0xf2, 0xec, 0xdd)
EMBER = (0xb8, 0x50, 0x1c)

SS = 3  # supersampling factor per axis


def rounded_rect(x, y, w, h, r):
    def inside(px, py):
        if not (x <= px <= x + w and y <= py <= y + h):
            return False
        cx = min(max(px, x + r), x + w - r)
        cy = min(max(py, y + r), y + h - r)
        return (px - cx) ** 2 + (py - cy) ** 2 <= r * r
    return inside


def polygon(points):
    def inside(px, py):
        hit = False
        n = len(points)
        for i in range(n):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % n]
            if (y1 > py) != (y2 > py):
                xint = (x2 - x1) * (py - y1) / (y2 - y1) + x1
                if px < xint:
                    hit = not hit
        return hit
    return inside


def circle(cx, cy, r):
    return lambda px, py: (px - cx) ** 2 + (py - cy) ** 2 <= r * r


def ring(x, y, w, h, r, thickness):
    outer = rounded_rect(x, y, w, h, r)
    t = thickness
    inner = rounded_rect(x + t, y + t, w - 2 * t, h - 2 * t, max(r - t, 0))
    return lambda px, py: outer(px, py) and not inner(px, py)


def build_layers(maskable=False):
    """Shapes in paint order, in a 512-unit design space."""
    # A maskable icon may be cropped to a circle, so keep the mark well inside.
    pad = 64 if maskable else 0
    s = (512 - 2 * pad) / 512.0

    def m(v):
        return pad + v * s

    pine = polygon([(m(256), m(88)), (m(336), m(236)), (m(296), m(236)),
                    (m(356), m(350)), (m(156), m(350)), (m(216), m(236)),
                    (m(176), m(236))])
    trunk = rounded_rect(m(232), m(342), 48 * s, 74 * s, 10 * s)

    return [
        (rounded_rect(0, 0, 512, 512, 512 / 2 if maskable else 96), BARK),
        (ring(m(34), m(34), 444 * s, 444 * s, 66 * s, 10 * s), BARK_DARK),
        (pine, CANVAS),
        (trunk, CANVAS),
        (circle(m(256), m(452), 20 * s), EMBER),
    ]


def render(size, maskable=False):
    layers = build_layers(maskable)
    scale = 512.0 / size
    step = scale / SS
    half = step / 2
    rows = []
    for py in range(size):
        row = bytearray([0])  # PNG filter byte: none
        base_y = py * scale
        for px in range(size):
            base_x = px * scale
            acc = [0, 0, 0, 0]
            for sy in range(SS):
                dy = base_y + sy * step + half
                for sx in range(SS):
                    dx = base_x + sx * step + half
                    colour = None
                    for shape, rgb in layers:
                        if shape(dx, dy):
                            colour = rgb
                    if colour is None:
                        continue
                    acc[0] += colour[0]
                    acc[1] += colour[1]
                    acc[2] += colour[2]
                    acc[3] += 255
            n = SS * SS
            a = acc[3] // n
            if a == 0:
                row += bytes(4)
            else:
                hits = acc[3] / 255
                row += bytes((int(acc[0] / hits), int(acc[1] / hits),
                              int(acc[2] / hits), a))
        rows.append(bytes(row))
    return b"".join(rows)


def write_png(path, size, raw):
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    open(path, "wb").write(png)
    return len(png)


def main():
    os.makedirs(OUT, exist_ok=True)
    targets = [
        ("favicon-32.png", 32, False),
        ("favicon-48.png", 48, False),
        ("apple-touch-icon.png", 180, False),
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("icon-maskable-512.png", 512, True),
    ]
    for name, size, maskable in targets:
        n = write_png(os.path.join(OUT, name), size, render(size, maskable))
        print(f"  {name:<26} {size:>4}px  {n:>7,}B{'  (maskable)' if maskable else ''}")
    print(f"\n{len(targets)} icons -> static/")


if __name__ == "__main__":
    main()
