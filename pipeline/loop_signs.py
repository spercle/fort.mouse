"""Draw a loop entrance sign for every loop, as SVG.

    python3 pipeline/loop_signs.py

Writes static/loop-sign/<loop>.svg — a drawn replica of the real Fort Wilderness loop
entrance sign: a dark routed board between two weathered posts, black iron straps at
each end, the loop's name in serif over its site-number range.

Reference photograph: docs/evidence/loop-1600-sign.jpeg (Timber Trail, 1601 - 1646).

The number range comes from the loop's own roster, so a sign shows what we actually
believe about that loop. Where the range is a hypothesis rather than something read off
the real sign, the drawing says so underneath rather than implying certainty it does not
have.
"""

import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOPS = os.path.join(ROOT, "data", "loops")
OUT = os.path.join(ROOT, "static", "loop-sign")

W, H = 660, 300

# Taken off the photograph rather than invented.
BOARD = "#43331f"
BOARD_EDGE = "#5d4830"
BOARD_SHADOW = "#2e2315"
POST = "#8d8271"
POST_SHADE = "#6f6555"
IRON = "#241f1a"
IRON_HI = "#3d362e"
LETTER = "#f1ece0"


def sign(loop, name, first, last, verified):
    board_x, board_y, board_w, board_h = 26, 96, 608, 96
    post_w, post_top, post_bottom = 34, 74, 300
    posts = (86, 540)
    strap = 26

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="Loop {loop} entrance sign: {name}, sites {first} to {last}">']

    # posts, behind the board
    for px in posts:
        s.append(f'<rect x="{px}" y="{post_top}" width="{post_w}" '
                 f'height="{post_bottom - post_top}" rx="{post_w/2:.0f}" fill="{POST}"/>')
        s.append(f'<rect x="{px + post_w - 11}" y="{post_top}" width="11" '
                 f'height="{post_bottom - post_top}" rx="5" fill="{POST_SHADE}" '
                 f'opacity=".55"/>')

    # board: shadow, face, routed inner bevel
    s.append(f'<rect x="{board_x}" y="{board_y + 5}" width="{board_w}" '
             f'height="{board_h}" rx="9" fill="{BOARD_SHADOW}" opacity=".45"/>')
    s.append(f'<rect x="{board_x}" y="{board_y}" width="{board_w}" height="{board_h}" '
             f'rx="9" fill="{BOARD}"/>')
    s.append(f'<rect x="{board_x + 7}" y="{board_y + 7}" width="{board_w - 14}" '
             f'height="{board_h - 14}" rx="6" fill="none" stroke="{BOARD_EDGE}" '
             f'stroke-width="2.5"/>')

    # iron straps holding the board to each post
    for px in posts:
        cx = px + post_w / 2 - strap / 2
        s.append(f'<rect x="{cx:.0f}" y="{board_y - 8}" width="{strap}" '
                 f'height="{board_h + 16}" rx="4" fill="{IRON}"/>')
        s.append(f'<rect x="{cx + 4:.0f}" y="{board_y - 8}" width="4" '
                 f'height="{board_h + 16}" rx="2" fill="{IRON_HI}" opacity=".7"/>')
        for cy in (board_y + 16, board_y + board_h - 16):
            s.append(f'<circle cx="{cx + strap/2:.0f}" cy="{cy:.0f}" r="3" '
                     f'fill="{IRON_HI}"/>')

    # lettering, centred between the straps
    mid = (posts[0] + post_w / 2 + posts[1] + post_w / 2) / 2
    s.append(f'<text x="{mid:.0f}" y="{board_y + 42}" fill="{LETTER}" '
             f'text-anchor="middle" font-family="Bitter, Georgia, serif" '
             f'font-size="30" font-weight="600">{name}</text>')
    s.append(f'<text x="{mid:.0f}" y="{board_y + 76}" fill="{LETTER}" '
             f'text-anchor="middle" font-family="Bitter, Georgia, serif" '
             f'font-size="25">{first} - {last}</text>')

    if not verified:
        s.append(f'<text x="{mid:.0f}" y="{H - 8}" text-anchor="middle" '
                 f'fill="currentColor" opacity=".55" font-size="12" '
                 f'font-family="IBM Plex Mono, ui-monospace, monospace">'
                 f'range not yet read off the real sign</text>')

    s.append("</svg>")
    return "\n".join(s)


def main():
    os.makedirs(OUT, exist_ok=True)
    made = verified_n = 0
    for f in sorted(os.listdir(LOOPS)):
        if not f.endswith(".yaml"):
            continue
        d = yaml.safe_load(open(os.path.join(LOOPS, f))) or {}
        sites = d.get("sites") or []
        if not sites:
            continue
        loop = d["loop"]
        first = sites[0]["site_number"]
        last = sites[-1]["site_number"]
        verified = bool(d.get("sign_evidence"))
        verified_n += verified
        open(os.path.join(OUT, f"{loop}.svg"), "w").write(
            sign(loop, d["loop_name"], first, last, verified))
        made += 1
        print(f"  loop {loop:<5} {d['loop_name']:<26} {first}-{last}"
              f"{'   VERIFIED from photo' if verified else ''}")
    print(f"\n{made} signs -> static/loop-sign/  ({verified_n} verified from a real sign)")


if __name__ == "__main__":
    main()
