"""Record a measurement taken on the ground.

    python3 pipeline/observe.py 101 --site-length 45 \
        --pad-length 24 --pad-width 10 \
        --backs-onto "basketball goal"

Site and pad are separate measurements (ADR-0005). The site is the usable length a rig
has to fit into; the pad is the poured concrete inside it. Site 101 is 45 ft of site
over a 24 ft slab, so recording one as the other would be wrong by 21 feet.

Writes data/observed.yaml, which is HUMAN-OWNED — derive.py never touches it, so
re-running the aerial measurements cannot overwrite something someone stood on the
pad with a tape measure to find out.

Observed beats aerial beats seeded. Someone on the ground outranks a photograph
from 3,000 feet, which outranks a figure published by somebody else.
"""

import argparse
import os
import sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "observed.yaml")
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

    entry = {"site_number": args.site, "source": "observed"}
    if args.date:
        entry["date"] = args.date
    for key, val in (("site_length_ft", args.site_length),
                     ("site_width_ft", args.site_width),
                     ("pad_length_ft", args.pad_length),
                     ("pad_width_ft", args.pad_width),
                     ("backs_onto", args.backs_onto), ("pad_surface", args.surface),
                     ("note", args.note)):
        if val is not None:
            entry[key] = val
    if len(entry) == len({"site_number", "source"}) + bool(args.date):
        sys.exit("nothing to record — pass at least one measurement")

    data = yaml.safe_load(open(PATH)) if os.path.exists(PATH) else None
    data = data or {"sites": []}
    data["sites"] = [s for s in data["sites"] if s["site_number"] != args.site]
    data["sites"].append(entry)
    data["sites"].sort(key=lambda s: s["site_number"])
    with open(PATH, "w") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True, width=88)

    print(f"  site {args.site} ({loop['category']}) recorded from observation")
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
    print(f"\n  {len(data['sites'])} site(s) measured on the ground")


if __name__ == "__main__":
    main()
