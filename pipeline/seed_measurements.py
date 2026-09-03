"""Merge published measurements into a loop's seed file.

    python3 pipeline/seed_measurements.py 1200 work/wp-1200.tsv \\
        --credit "The Wilderness Princess" --url https://wildernessprincess.net/loop-site-details/

Input is a tab-separated file, one Site per line. Blank cells are fine:

    site    width   length
    1204    11-12   52
    1205    17-19   75
    1206            48

Writes data/seeds/<loop>.yaml, which is HUMAN-OWNED — `derive.py` never touches it, so a
recompute of the aerial measurements cannot destroy your seeds (ADR-0002). The build
merges the two, and an aerial or observed value always beats a seed (ADR-0004).

Only WIDTH and LENGTH are taken. Difficulty ratings and site notes from another guide are
that author's editorial work rather than facts, and are not ingested — we compute our own
back-in difficulty from geometry.

Widths are often published as a range ("11-12"). The low end is stored, because the
question a reader is asking is whether their rig fits.
"""

import argparse
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_measure(cell):
    """'11-12' -> (11.0, '11-12').  '52' -> (52.0, None).  '' -> (None, None)."""
    cell = (cell or "").strip()
    if not cell:
        return None, None
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", cell)]
    if not nums:
        return None, None
    if len(nums) > 1:
        return min(nums), cell
    return nums[0], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("loop", type=int)
    ap.add_argument("tsv")
    ap.add_argument("--credit", required=True, help="who published these figures")
    ap.add_argument("--url", default="", help="where they were published")
    args = ap.parse_args()

    rows = []
    with open(args.tsv) as fh:
        for raw in fh:
            if not raw.strip() or raw.lower().lstrip().startswith("site"):
                continue
            cells = raw.rstrip("\n").split("\t")
            if not cells[0].strip().isdigit():
                print(f"  skipped, no site number: {raw.strip()[:60]}")
                continue
            n = int(cells[0].strip())
            width, width_raw = parse_measure(cells[1] if len(cells) > 1 else "")
            length, length_raw = parse_measure(cells[2] if len(cells) > 2 else "")
            if width is None and length is None:
                continue
            rows.append((n, width, width_raw, length, length_raw))

    if not rows:
        sys.exit("no usable rows found — expected: site<TAB>width<TAB>length")

    rows.sort()
    out = [
        f"# Loop {args.loop} — seeded measurements",
        "#",
        "# HUMAN-OWNED. derive.py never writes here, so recomputing the aerial",
        "# measurements cannot destroy these. See ADR-0002 and ADR-0004.",
        "#",
        "# These are attributed facts from another published source. Each is replaced the",
        "# moment we measure it ourselves or a guest verifies it from their own stay.",
        "",
        f"loop: {args.loop}",
        f"seeded: {date.today().isoformat()}",
        "attribution:",
        f"  credit: {args.credit!r}",
    ]
    if args.url:
        out.append(f"  url: {args.url}")
    out += ["  source: seeded", "", "sites:"]

    for n, width, width_raw, length, length_raw in rows:
        out.append(f"  - site_number: {n}")
        if length is not None:
            out.append(f"    pad_length_ft: {length}")
            if length_raw:
                out.append(f"    pad_length_published: {length_raw!r}")
        if width is not None:
            out.append(f"    pad_width_ft: {width}")
            if width_raw:
                out.append(f"    pad_width_published: {width_raw!r}")
        out.append("    verified_by: null")
        out.append("    verified_date: null")

    dest = os.path.join(ROOT, "data", "seeds", f"{args.loop}.yaml")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w").write("\n".join(out) + "\n")

    ranged = sum(1 for r in rows if r[2] or r[4])
    print(f"  wrote {dest}")
    print(f"  {len(rows)} sites seeded, credited to {args.credit}")
    print(f"  {ranged} had published ranges; stored the low end, kept the original text")
    print("  every one is marked unverified — verification replaces them")


if __name__ == "__main__":
    main()
