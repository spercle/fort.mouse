"""Draw a campground map for every loop, as SVG.

    python3 pipeline/loop_context.py     # once, to cache the surroundings
    python3 pipeline/loop_maps.py

Writes static/loop-map/<loop>.svg in the ordinary campground-map idiom — a filled road
ribbon, numbered pads angled off it, comfort stations, woods and water. The idiom is a
genre convention every campground in the country uses; the geometry here is entirely
ours, from OpenStreetMap and the Orange County public record.

Pads render three ways, and the difference is always visible:
  measured     solid, in the measured colour, at true size and bearing
  known        solid, position known, not yet measured
  provisional  dashed, from `inferred_centroid` — spacing arithmetic, not observation
"""

import json
import math
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "data", "reference")
LOOPS = os.path.join(ROOT, "data", "loops")
OUT = os.path.join(ROOT, "static", "loop-map")

W, H = 1000, 720
PAD = 62
TW, TH = 420, 300
TPAD = 14
EARTH_FT = 20925721.8

STYLE = """
  .bg     { fill: var(--map-paper, #eef0e6); }
  .frame  { fill: none; stroke: var(--rule-strong, #b9c0ae); stroke-width: 1; }
  .wood   { fill: var(--map-wood, #d3ddc4); stroke: none; }
  .water  { fill: var(--map-water, #bcd4dd); stroke: var(--map-water-e, #9dbcc7);
            stroke-width: 1; }
  .canal  { fill: none; stroke: var(--map-water, #bcd4dd); stroke-width: 5;
            stroke-linecap: round; }
  .bldg   { fill: var(--map-bldg, #cfc7b6); stroke: var(--rule-strong, #b9c0ae); }
  .trail  { fill: none; stroke: var(--map-trail, #b3ad97); stroke-width: 1.6;
            stroke-dasharray: 4 4; stroke-linecap: round; }
  .other  { fill: none; stroke: var(--map-road-e, #c8c8bb); stroke-width: 8;
            stroke-linejoin: round; stroke-linecap: round; }
  .road-e { fill: none; stroke: var(--map-road-e, #b6b6a6); stroke-width: 19;
            stroke-linejoin: round; stroke-linecap: round; }
  .road   { fill: none; stroke: var(--map-road, #fbfaf4); stroke-width: 15;
            stroke-linejoin: round; stroke-linecap: round; }
  .stub   { stroke: var(--map-road, #fbfaf4); stroke-width: 4; stroke-linecap: round; }
  .pad    { fill: var(--measured-soft, #dde9e1); stroke: var(--measured, #2e6a4c);
            stroke-width: 1.1; }
  .pad-k  { fill: var(--map-pad, #e6dcc4); stroke: var(--map-pad-e, #b9a97f);
            stroke-width: 1; }
  .pad-i  { fill: var(--map-pad, #e6dcc4); stroke: var(--map-pad-e, #b9a97f);
            stroke-width: 1; stroke-dasharray: 3 2.5; opacity: .9; }
  .cabin-l{ font: 600 10px 'IBM Plex Mono', ui-monospace, monospace;
            fill: var(--map-ink, #3b3a2f); text-anchor: middle; }
  .cabin-k{ font: 600 7.5px 'IBM Plex Mono', ui-monospace, monospace;
            fill: var(--map-ink2, #6f6e5c); text-anchor: middle;
            letter-spacing: .12em; }
  .num    { font: 600 9.5px 'IBM Plex Mono', ui-monospace, monospace;
            fill: var(--map-ink, #3b3a2f); text-anchor: middle; }
  .cs     { fill: var(--accent, #b8461c); }
  .cs-t   { font: 600 8.5px 'IBM Plex Mono', ui-monospace, monospace;
            fill: #fff; text-anchor: middle; }
  .cs-l   { font: 600 9px 'IBM Plex Mono', ui-monospace, monospace;
            fill: var(--accent, #b8461c); text-anchor: middle; }
  .rd-l   { font: 500 9.5px 'IBM Plex Mono', ui-monospace, monospace;
            fill: var(--map-ink2, #6b6a58); }
  .ttl    { font: 800 27px Bitter, Georgia, serif;
            fill: var(--map-ink, #3b3a2f); }
  .sub    { font: 500 12px 'IBM Plex Mono', ui-monospace, monospace;
            fill: var(--map-ink2, #6f6e5c); }
  .lbl    { font: 500 10px 'IBM Plex Mono', ui-monospace, monospace;
            fill: var(--map-ink2, #6f6e5c); }
  .bar    { stroke: var(--map-ink, #3b3a2f); stroke-width: 2; fill: none; }
  .rose   { fill: var(--map-ink, #3b3a2f); }
"""


def to_ft(coords, origin):
    olon, olat = origin
    k = math.radians(1) * EARTH_FT
    cos = math.cos(math.radians(olat))
    return [((lon - olon) * k * cos, (lat - olat) * k) for lon, lat in coords]


class Frame:
    """One projection for the whole drawing, fitted to the loop road."""

    def __init__(self, road_ft, extra_ft):
        pts = road_ft + extra_ft
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        w, h = (max(xs) - min(xs)) or 1, (max(ys) - min(ys)) or 1
        self.scale = min((W - 2 * PAD) / w, (H - 2 * PAD) / h)
        self.ox = (W - w * self.scale) / 2 - min(xs) * self.scale
        self.oy = (H - h * self.scale) / 2 + max(ys) * self.scale

    def __call__(self, pts_ft):
        return [(x * self.scale + self.ox, self.oy - y * self.scale) for x, y in pts_ft]


def path_d(pts, close=False):
    return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts) + (" Z" if close else "")


def load_context(loop):
    p = os.path.join(REF, f"loop-{loop}-context.geojson")
    return json.load(open(p)).get("features", []) if os.path.exists(p) else []


def load_pads(loop, origin):
    p = os.path.join(LOOPS, f"{loop}.yaml")
    if not os.path.exists(p):
        return []
    data = yaml.safe_load(open(p)) or {}
    out = []
    for s in data.get("sites") or []:
        c, state = s.get("centroid"), "known"
        if not c:
            c, state = s.get("inferred_centroid"), "provisional"
        if not c:
            continue

        def num(k):
            return s[k] if isinstance(s.get(k), (int, float)) else None

        if num("pad_length_ft"):
            state = "measured"
        out.append({"number": s["site_number"], "state": state,
                    "ft": to_ft([[c[1], c[0]]], origin)[0],
                    "length": num("pad_length_ft"), "width": num("pad_width_ft"),
                    "bearing": num("pad_orientation_deg")})
    return out


def nearest_road(pt_ft, road_ft):
    """The stretch of road a pad belongs to, so it can sit square to it."""
    best, bi = None, 0
    for i in range(len(road_ft) - 1):
        mx = (road_ft[i][0] + road_ft[i + 1][0]) / 2
        my = (road_ft[i][1] + road_ft[i + 1][1]) / 2
        d = (mx - pt_ft[0]) ** 2 + (my - pt_ft[1]) ** 2
        if best is None or d < best:
            best, bi = d, i
    ax, ay = road_ft[bi]
    bx, by = road_ft[bi + 1]
    bearing = math.degrees(math.atan2(bx - ax, by - ay)) % 180
    return bearing, ((ax + bx) / 2, (ay + by) / 2)


def draw_thumb(loop_no, road_coords):
    """A card-sized reduction: shape, greenery, water, pad marks. No text."""
    origin = (road_coords[0][0], road_coords[0][1])
    road_ft = to_ft(road_coords, origin)
    pads = load_pads(loop_no, origin)
    ctx = load_context(loop_no)
    for f in ctx:
        g = f["geometry"]
        pts = ([g["coordinates"]] if g["type"] == "Point"
               else g["coordinates"][0] if g["type"] == "Polygon"
               else g["coordinates"])
        f["_ft"] = to_ft(pts, origin)

    global W, H, PAD
    ow, oh, op = W, H, PAD
    W, H, PAD = TW, TH, TPAD
    try:
        frame = Frame(road_ft, [p["ft"] for p in pads])
        road_px = frame(road_ft)
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TW} {TH}" '
               f'role="img" aria-label="Map of Loop {loop_no}">',
               f'<style>{STYLE}</style>',
               f'<clipPath id="t{loop_no}"><rect width="{TW}" height="{TH}"/></clipPath>',
               f'<rect class="bg" width="{TW}" height="{TH}"/>',
               f'<g clip-path="url(#t{loop_no})">']
        for f in ctx:
            k = f["properties"]["kind"]
            if k == "wood":
                out.append(f'<path class="wood" d="{path_d(frame(f["_ft"]), True)}"/>')
            elif k == "water":
                poly = f["geometry"]["type"] == "Polygon"
                out.append(f'<path class="{"water" if poly else "canal"}" '
                           f'd="{path_d(frame(f["_ft"]), poly)}"/>')
            elif k == "road":
                out.append(f'<path class="other" d="{path_d(frame(f["_ft"]))}" '
                           f'stroke-width="4"/>')
        out.append(f'<path class="road-e" d="{path_d(road_px)}" stroke-width="9"/>')
        out.append(f'<path class="road" d="{path_d(road_px)}" stroke-width="6.5"/>')
        for p in pads:
            (px, py), = frame([p["ft"]])
            bearing, _ = nearest_road(p["ft"], road_ft)
            rot = p["bearing"] if p["bearing"] is not None else (bearing + 90) % 180
            L = (p["length"] or 42) * frame.scale
            Wd = (p["width"] or 13) * frame.scale
            cls = {"measured": "pad", "known": "pad-k", "provisional": "pad-i"}[p["state"]]
            out.append(f'<g transform="translate({px:.1f} {py:.1f}) rotate({rot:.1f})">'
                       f'<rect class="{cls}" x="{-Wd/2:.1f}" y="{-L/2:.1f}" '
                       f'width="{max(Wd,1.6):.1f}" height="{max(L,3):.1f}" rx="1"/></g>')
        for f in ctx:
            if f["properties"]["kind"] != "comfort":
                continue
            px = frame(f["_ft"])
            cx = sum(x for x, _ in px) / len(px)
            cy = sum(y for _, y in px) / len(px)
            out.append(f'<circle class="cs" cx="{cx:.1f}" cy="{cy:.1f}" r="3.5"/>')
        out.append("</g></svg>")
        return "\n".join(out)
    finally:
        W, H, PAD = ow, oh, op


def draw(loop_no, name, category, road_coords, segments):
    origin = (road_coords[0][0], road_coords[0][1])
    road_ft = to_ft(road_coords, origin)
    pads = load_pads(loop_no, origin)
    ctx = load_context(loop_no)

    for f in ctx:
        g = f["geometry"]
        if g["type"] == "Point":
            f["_ft"] = to_ft([g["coordinates"]], origin)
        elif g["type"] == "Polygon":
            f["_ft"] = to_ft(g["coordinates"][0], origin)
        else:
            f["_ft"] = to_ft(g["coordinates"], origin)

    frame = Frame(road_ft, [p["ft"] for p in pads])
    road_px = frame(road_ft)
    total_ft = sum(math.dist(road_ft[i], road_ft[i + 1])
                   for i in range(len(road_ft) - 1))

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'role="img" aria-label="Campground map of Loop {loop_no}, {name}">',
           f'<style>{STYLE}</style>',
           f'<clipPath id="clip{loop_no}">'
           f'<rect x="9" y="9" width="{W-18}" height="{H-18}"/></clipPath>',
           f'<rect class="bg" width="{W}" height="{H}"/>',
           f'<g clip-path="url(#clip{loop_no})">']

    def by(kind):
        return [f for f in ctx if f["properties"]["kind"] == kind]

    for f in by("wood"):
        svg.append(f'<path class="wood" d="{path_d(frame(f["_ft"]), True)}"/>')
    for f in by("water"):
        poly = f["geometry"]["type"] == "Polygon"
        svg.append(f'<path class="{"water" if poly else "canal"}" '
                   f'd="{path_d(frame(f["_ft"]), poly)}"/>')
    for f in by("trail"):
        svg.append(f'<path class="trail" d="{path_d(frame(f["_ft"]))}"/>')
    for f in by("road"):
        svg.append(f'<path class="other" d="{path_d(frame(f["_ft"]))}"/>')
    for f in by("building"):
        px = frame(f["_ft"])
        svg.append(f'<path class="bldg" d="{path_d(px, True)}"/>')
        # A named cabin inside a campsite loop explains a gap in the numbering.
        nm = (f["properties"].get("name") or "")
        if nm.lower().startswith("cabin"):
            cx = sum(x for x, _ in px) / len(px)
            cy = sum(y for _, y in px) / len(px)
            svg.append(f'<text class="cabin-l" x="{cx:.1f}" y="{cy+3:.1f}">'
                       f'{nm.replace("cabin ", "").strip()}</text>')
            svg.append(f'<text class="cabin-k" x="{cx:.1f}" y="{cy+15:.1f}">CABIN</text>')

    # name the neighbouring loops, so the reader can place themselves
    for f in by("road"):
        nm = f["properties"].get("name")
        if not nm or nm == name:
            continue
        px = frame(f["_ft"])
        mx, my = px[len(px) // 2]
        if PAD < mx < W - PAD and PAD < my < H - PAD:
            svg.append(f'<text class="rd-l" x="{mx:.0f}" y="{my-7:.0f}">{nm}</text>')

    # the loop itself: casing then fill, so it reads as a ribbon
    svg.append(f'<path class="road-e" d="{path_d(road_px)}"/>')
    svg.append(f'<path class="road" d="{path_d(road_px)}"/>')

    # pads, squared to the nearest stretch of road, each with a driveway stub
    placed_nums = []
    for p in pads:
        bearing, road_mid = nearest_road(p["ft"], road_ft)
        rot = p["bearing"] if p["bearing"] is not None else (bearing + 90) % 180
        L = (p["length"] or 42) * frame.scale
        Wd = (p["width"] or 13) * frame.scale
        (px, py), = frame([p["ft"]])
        (rx, ry), = frame([road_mid])
        cls = {"measured": "pad", "known": "pad-k", "provisional": "pad-i"}[p["state"]]
        svg.append(f'<line class="stub" x1="{rx:.1f}" y1="{ry:.1f}" '
                   f'x2="{px:.1f}" y2="{py:.1f}"/>')
        svg.append(f'<g transform="translate({px:.1f} {py:.1f}) rotate({rot:.1f})">'
                   f'<rect class="{cls}" x="{-Wd/2:.1f}" y="{-L/2:.1f}" '
                   f'width="{Wd:.1f}" height="{L:.1f}" rx="1.5"/></g>')
        if all(abs(px - ox) > 22 or abs(py - oy) > 11 for ox, oy in placed_nums):
            placed_nums.append((px, py))
            svg.append(f'<text class="num" x="{px:.1f}" y="{py+3.3:.1f}">'
                       f'{p["number"]}</text>')

    # comfort stations — the amenity every campground map marks. Some are mapped as
    # nodes and some as building outlines, so reduce whatever came back to a point.
    for f in by("comfort"):
        px = frame(f["_ft"])
        cx = sum(x for x, _ in px) / len(px)
        cy = sum(y for _, y in px) / len(px)
        svg.append(f'<circle class="cs" cx="{cx:.1f}" cy="{cy:.1f}" r="9"/>')
        svg.append(f'<text class="cs-t" x="{cx:.1f}" y="{cy+3:.1f}">WC</text>')
        # Keep the caption out of the title block and the footer strip, where it
        # was overprinting "Loop 100" and the provenance line.
        ly = cy + 21
        if ly > H - 40:
            ly = cy - 15
        in_title = cy < PAD + 20 and cx < W * 0.5
        if not in_title:
            svg.append(f'<text class="cs-l" x="{cx:.1f}" y="{ly:.1f}">COMFORT STATION</text>')

    ex, ey = road_px[0]
    svg.append(f'<circle class="cs" cx="{ex:.1f}" cy="{ey:.1f}" r="5"/>')
    svg.append(f'<text class="cs-l" x="{ex:.1f}" y="{ey-11:.1f}">ENTRANCE</text>')
    svg.append('</g>')

    svg.append(f'<rect class="frame" x="9" y="9" width="{W-18}" height="{H-18}"/>')
    svg.append(f'<text class="ttl" x="{PAD-34}" y="{PAD-20}">Loop {loop_no}</text>')
    svg.append(f'<text class="sub" x="{PAD-34}" y="{PAD-2}">{name} · {category}</text>')
    svg.append(f'<text class="lbl" x="{W-PAD+30}" y="{PAD-20}" text-anchor="end">'
               f'{int(round(total_ft))} ft of road · {len(pads)} sites</text>')
    if segments:
        blocks = ", ".join(f"{s['theoretical_left'][0]}-{s['theoretical_left'][1]}"
                           for s in segments if (s.get("theoretical_left") or [None])[0])
        if blocks:
            svg.append(f'<text class="lbl" x="{W-PAD+30}" y="{PAD-5}" text-anchor="end">'
                       f'county blocks {blocks}</text>')

    feet = 50
    for candidate in (500, 400, 300, 250, 200, 150, 100, 50):
        if candidate * frame.scale <= (W - 2 * PAD) * 0.3:
            feet = candidate
            break
    bx, by = PAD - 34, H - 34
    px_len = feet * frame.scale
    svg.append(f'<path class="bar" d="M {bx} {by-5} L {bx} {by} L {bx+px_len:.1f} {by} '
               f'L {bx+px_len:.1f} {by-5}"/>')
    svg.append(f'<text class="lbl" x="{bx+px_len+9:.1f}" y="{by+4}">{feet} ft</text>')

    nx, ny = W - PAD + 22, H - 52
    svg.append(f'<path class="rose" d="M {nx} {ny-19} L {nx+6} {ny+4} L {nx} {ny-1} '
               f'L {nx-6} {ny+4} Z"/>')
    svg.append(f'<text class="lbl" x="{nx-4}" y="{ny+18}">N</text>')

    prov = sum(1 for p in pads if p["state"] == "provisional")

    # An empty loop must not look like a finished one. The campground-style rewrite
    # lost this and twenty maps silently rendered with no sites and no explanation.
    if not pads:
        svg.append(f'<text class="mark" x="{W/2}" y="{H/2 - 4}">'
                   f'NO SITE POSITIONS YET</text>')
        svg.append(f'<text class="key" x="{W/2}" y="{H/2 + 14}" text-anchor="middle">'
                   f'run pipeline/infer_positions.py {loop_no}</text>')

    note = f"{prov} site positions provisional · " if prov else ""
    svg.append(f'<text class="lbl" x="{W/2}" y="{H-16}" text-anchor="middle">'
               f'{note}Geometry: OpenStreetMap · Blocks: Orange County public record</text>')
    svg.append("</svg>")
    return "\n".join(svg)


def main():
    os.makedirs(OUT, exist_ok=True)
    made = 0
    for f in sorted(os.listdir(REF)):
        if not f.endswith("-osm-road.geojson"):
            continue
        loop_no = int(f.split("-")[1])
        fc = json.load(open(os.path.join(REF, f)))
        coords = [p for feat in fc["features"] for p in feat["geometry"]["coordinates"]]
        if len(coords) < 2:
            continue
        meta = {}
        lp = os.path.join(LOOPS, f"{loop_no}.yaml")
        if os.path.exists(lp):
            meta = yaml.safe_load(open(lp)) or {}
        segs = ((meta.get("county_record") or {}).get("segments")) or []
        svg = draw(loop_no, meta.get("loop_name", "?"), meta.get("category", "?"),
                   coords, segs)
        open(os.path.join(OUT, f"{loop_no}.svg"), "w").write(svg)
        open(os.path.join(OUT, f"{loop_no}-thumb.svg"), "w").write(
            draw_thumb(loop_no, coords))
        made += 1
        n = len(load_pads(loop_no, (coords[0][0], coords[0][1])))
        print(f"  loop {loop_no}: {n} pads, {len(load_context(loop_no))} context features")
    print(f"\n{made} loop maps -> static/loop-map/")


if __name__ == "__main__":
    main()
