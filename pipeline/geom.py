"""Geometry for pad measurement. No dependencies — stdlib only.

Everything here works in local feet. Lat/lon comes in, feet go out, because a pad
is 10-60 ft and we care about a tenth of a foot; an equirectangular projection about
a local origin is exact enough at that scale and avoids a projection library.
"""

import math

EARTH_FT = 20925721.8  # earth radius, feet


def to_local_ft(coords, origin):
    """Project [lon, lat] pairs to local (east, north) feet about `origin`."""
    olon, olat = origin
    coslat = math.cos(math.radians(olat))
    return [
        ((lon - olon) * math.radians(1) * EARTH_FT * coslat,
         (lat - olat) * math.radians(1) * EARTH_FT)
        for lon, lat in coords
    ]


def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def convex_hull(pts):
    """Andrew's monotone chain. Returns hull in counter-clockwise order."""
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def half(points):
        out = []
        for p in points:
            while len(out) >= 2 and _cross(out[-2], out[-1], p) <= 0:
                out.pop()
            out.append(p)
        return out[:-1]

    return half(pts) + half(reversed(pts))


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def min_area_rect(pts):
    """Oriented minimum bounding rectangle via rotating calipers.

    Returns (length_ft, width_ft, bearing_deg) where length >= width and bearing is
    the long axis measured clockwise from north, normalised to [0, 180).

    This is the equivalent of QGIS's `native:orientedminimumbbox` plus
    `main_angle($geometry)`, which we deliberately do not depend on — QGIS has open
    bugs in that pair (#41022, #36632) and this is 30 lines.
    """
    hull = convex_hull(pts)
    if len(hull) < 3:
        raise ValueError("need at least 3 distinct points")

    best = None
    for i in range(len(hull)):
        ax, ay = hull[i]
        bx, by = hull[(i + 1) % len(hull)]
        edge = math.hypot(bx - ax, by - ay)
        if edge == 0:
            continue
        # unit vector along this edge, and its perpendicular
        ux, uy = (bx - ax) / edge, (by - ay) / edge
        us = [( (x - ax) * ux + (y - ay) * uy,
                -(x - ax) * uy + (y - ay) * ux ) for x, y in hull]
        w = max(p[0] for p in us) - min(p[0] for p in us)
        h = max(p[1] for p in us) - min(p[1] for p in us)
        if best is None or w * h < best[0]:
            best = (w * h, w, h, ux, uy)

    _, w, h, ux, uy = best
    if w >= h:
        length, width, lx, ly = w, h, ux, uy
    else:
        length, width, lx, ly = h, w, -uy, ux

    bearing = math.degrees(math.atan2(lx, ly)) % 180.0
    return length, width, bearing


def polyline_length_ft(coords):
    """Length of a [lon, lat] polyline, in feet."""
    total = 0.0
    for i in range(len(coords) - 1):
        total += haversine_ft(coords[i], coords[i + 1])
    return total


def haversine_ft(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[0], b[1], b[0]))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * EARTH_FT * math.asin(math.sqrt(h))


def point_to_polyline_ft(pt, line):
    """Shortest distance from a [lon, lat] point to a [lon, lat] polyline, in feet.

    Also returns how far along the line the closest point falls, which is what
    orders pads around a loop.
    """
    local = to_local_ft(line, pt)
    px, py = 0.0, 0.0  # pt is the projection origin
    best_d, best_s, travelled = None, 0.0, 0.0

    for i in range(len(local) - 1):
        (x1, y1), (x2, y2) = local[i], local[i + 1]
        dx, dy = x2 - x1, y2 - y1
        seg = math.hypot(dx, dy)
        if seg == 0:
            continue
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (seg * seg)))
        cx, cy = x1 + t * dx, y1 + t * dy
        d = math.hypot(px - cx, py - cy)
        if best_d is None or d < best_d:
            best_d, best_s = d, travelled + t * seg
        travelled += seg

    return best_d, best_s
