"""Record a measurement taken on the ground.

    python3 pipeline/observe.py 101 --site-length 45 \
        --pad-length 24 --pad-width 10 \
        --backs-onto "basketball goal"

Site and pad are separate measurements (ADR-0005). The site is the usable length a rig
has to fit into; the pad is the poured concrete inside it. Site 101 is 45 ft of site
over a 24 ft slab, so recording one as the other would be wrong by 21 feet.

Writes data/sites/<number>.md, which is HUMAN-OWNED — derive.py never touches it, so
re-running the aerial measurements cannot overwrite something someone stood on the pad
with a tape measure to find out. Editing that file by hand does exactly the same thing;
this script is a shortcut, not the interface.

Observed beats aerial beats seeded. Someone on the ground outranks a photograph
from 3,000 feet, which outranks a figure published by somebody else.
"""

import argparse
import os
import sys
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import site_files  # noqa: E402

ROOT = os.path.dirname(HERE)
LOOPS = os.path.join(ROOT, "data", "loops")

# Disney's published maximum per category, for sanity-checking against.
CATEGORY_MAX = {
    "Tent/Pop-Up": (25, 10), "Full Hook-Up": (50, 10), "Preferred": (45, 10),
    "Premium": (60, 18), "Premium Meadow": (60, 18),
}


def find_loop(n):
    for f in sorted(os.listdir(LOOPS)):
        if not f.endswith(".yaml"):
            continue
        d = yaml.safe_load(open(os.path.join(LOOPS, f))) or {}
        if any(s["site_number"] == n for s in d.get("sites") or []):
            return d
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", type=int)
    ap.add_argument("--site-length", type=float, help="usable site length, ft")
    ap.add_argument("--site-width", type=float, help="usable site width, ft")
    ap.add_argument("--pad-length", type=float, help="poured concrete length, ft")
    ap.add_argument("--pad-width", type=float, help="poured concrete width, ft")
    ap.add_argument("--backs-onto")
    ap.add_argument("--surface")
    ap.add_argument("--note")
    # No default. Today is when it was *recorded*, which is not what the page would
    # be claiming — it would read as the day someone stood on the pad. Left out
    # unless known.
    ap.add_argument("--date", default=None,
                    help="date the measurement was taken (YYYY-MM-DD), if known")
    args = ap.parse_args()

    loop = find_loop(args.site)
    if loop is None:
        sys.exit(f"site {args.site} is not in any loop roster")

    # Keep whatever is already there — the prose underneath especially.
    entry, body = site_files.read_one(args.site)
    entry["loop"] = loop["loop"]
    if args.date:
        entry["measured"] = args.date
    before = dict(entry)
    for key, val in (("site_length_ft", args.site_length),
                     ("site_width_ft", args.site_width),
                     ("pad_length_ft", args.pad_length),
                     ("pad_width_ft", args.pad_width),
                     ("backs_onto", args.backs_onto), ("pad_surface", args.surface)):
        if val is not None:
            entry[key] = val
    if entry == before and not args.note:
        sys.exit("nothing to record — pass at least one measurement")
    if args.note:
        body = (body + "\n\n" + args.note).strip() if body else args.note


    path = site_files.write(args.site, entry, body)

    print(f"  site {args.site} ({loop['category']}) -> "
          f"{os.path.relpath(path, ROOT)}")
    for k in ("site_length_ft", "site_width_ft", "pad_length_ft", "pad_width_ft",
              "backs_onto", "pad_surface"):
        if k in entry:
            print(f"    {k}: {entry[k]}")

    # Flag rather than reject: Disney publishes a category ceiling, not a floor,
    # and a short pad is a real thing worth knowing about.
    # Compare like with like: the published figure is a SITE length, so only a site
    # length gets checked against it. A short slab inside a full-length site is normal
    # and must not be flagged as if the site were short.
    cmax = CATEGORY_MAX.get(loop["category"])
    if cmax and args.site_length:
        max_len, _ = cmax
        if args.site_length < max_len * 0.65:
            print(f"\n  NOTE: Disney lists {loop['category']} at up to {max_len} ft "
                  f"of site. {args.site_length} ft is well under that.")
            print("  The published figure is a ceiling for the category, not a promise")
            print("  about any one site — but it is worth a second look.")
    print("\n  edit that file directly for anything else worth saying")


if __name__ == "__main__":
    main()
