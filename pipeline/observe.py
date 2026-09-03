"""Record a measurement taken on the ground.

    python3 pipeline/observe.py 101 --width 10 --length 24 \
        --backs-onto "basketball goal" --note "Measured on site."

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
    ap.add_argument("--width", type=float)
    ap.add_argument("--length", type=float)
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
    for key, val in (("pad_width_ft", args.width), ("pad_length_ft", args.length),
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
    for k in ("pad_length_ft", "pad_width_ft", "backs_onto", "pad_surface"):
        if k in entry:
            print(f"    {k}: {entry[k]}")

    # Flag rather than reject: Disney publishes a category ceiling, not a floor,
    # and a short pad is a real thing worth knowing about.
    cmax = CATEGORY_MAX.get(loop["category"])
    if cmax and args.length:
        max_len, max_wid = cmax
        if args.length < max_len * 0.65:
            print(f"\n  NOTE: Disney lists {loop['category']} at up to {max_len} ft. "
                  f"{args.length} ft is well under that.")
            print("  That may be exactly right — the published figure is a ceiling for")
            print("  the category, not a promise about any one site — but it is worth")
            print("  a second look before anyone plans a rig around it.")
    print(f"\n  {len(data['sites'])} site(s) measured on the ground")


if __name__ == "__main__":
    main()
