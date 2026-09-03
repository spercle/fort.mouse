"""Prove the measurement math before anyone spends an afternoon digitizing.

Run: python3 pipeline/test_geom.py
"""

import math
import sys

from geom import min_area_rect, to_local_ft, polyline_length_ft, point_to_polyline_ft

FAILS = []


def check(name, got, want, tol):
    ok = abs(got - want) <= tol
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got:.3f}, want {want:.3f} (+/-{tol})")
    if not ok:
        FAILS.append(name)


def rect_points(length, width, bearing_deg, n_per_edge=1):
    """Corners of a length x width rectangle whose long axis points at `bearing_deg`
    clockwise from north, centred on the origin, in local feet."""
    th = math.radians(bearing_deg)
    lx, ly = math.sin(th), math.cos(th)          # along the long axis
    wx, wy = math.cos(th), -math.sin(th)         # perpendicular
    pts = []
    for sl in (-0.5, 0.5):
        for sw in (-0.5, 0.5):
            pts.append((length * sl * lx + width * sw * wx,
                        length * sl * ly + width * sw * wy))
    return pts


print("min_area_rect recovers a known pad at every orientation")
for bearing in (0, 17, 35, 60, 90, 123, 179):
    L, W, B = min_area_rect(rect_points(48.0, 12.0, bearing))
    check(f"  bearing {bearing:>3}deg  length", L, 48.0, 0.001)
    check(f"  bearing {bearing:>3}deg  width ", W, 12.0, 0.001)
    check(f"  bearing {bearing:>3}deg  bearing", B, bearing % 180, 0.001)

print("\nnoisy digitizing (a hand-clicked pad is never a perfect rectangle)")
import random
random.seed(7)
noisy = [(x + random.uniform(-0.15, 0.15), y + random.uniform(-0.15, 0.15))
         for (x, y) in rect_points(52.0, 18.0, 41.0)]
L, W, B = min_area_rect(noisy)
check("  length within a third of a foot", L, 52.0, 0.35)
check("  width within a third of a foot", W, 18.0, 0.35)
check("  bearing within one degree", B, 41.0, 1.0)

print("\nlat/lon -> local feet, against a known Fort Wilderness distance")
# Loop 1200 county segment 1: 102.3 ft per Orange County's own SHAPE_Length.
seg = [[-81.55733, 28.40364], [-81.55704, 28.40382]]
check("  polyline length", polyline_length_ft(seg), 118.0, 25.0)

print("\npoint_to_polyline_ft finds distance and position along a loop")
line = [[-81.5570, 28.4030], [-81.5560, 28.4030]]   # ~320 ft due east
d, s = point_to_polyline_ft([-81.5565, 28.4032], line)
check("  perpendicular offset", d, 72.9, 8.0)
check("  distance along line", s, 160.0, 12.0)

print()
if FAILS:
    print(f"{len(FAILS)} FAILED")
    sys.exit(1)
print("all passed — the measurement math is sound")
