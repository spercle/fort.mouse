"""Record that a site number has been confirmed from primary evidence.

    python3 pipeline/verify_site.py 1420 --photo /photos/1420-2.jpg \
        --note "The numbered post is legible, reading 1420."

Writes to data/verified.yaml, which is HUMAN-OWNED — derive.py never touches it, so
re-measuring a loop cannot silently undo a verification.

A photograph of the numbered post, or of the loop's entrance sign, is a primary
source. Everything else in this project's numbering is inference from sequence.
"""

import argparse
import os
import sys
from datetime import date

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "verified.yaml")
LOOPS = os.path.join(ROOT, "data", "loops")


def site_exists(n):
    for f in os.listdir(LOOPS):
        if not f.endswith(".yaml"):
            continue
        d = yaml.safe_load(open(os.path.join(LOOPS, f))) or {}
        if any(s["site_number"] == n for s in d.get("sites") or []):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", type=int)
    ap.add_argument("--photo", required=True, help="site-relative path, /photos/...")
    ap.add_argument("--note", required=True)
    ap.add_argument("--kind", default="post", choices=["post", "sign"])
    ap.add_argument("--date", default=None, help="when the evidence was captured")
    args = ap.parse_args()

    if not site_exists(args.site):
        sys.exit(f"site {args.site} is not in any loop roster")
    if not os.path.exists(os.path.join(ROOT, "static", args.photo.lstrip("/"))):
        sys.exit(f"no such photo: static{args.photo}")

    data = yaml.safe_load(open(PATH)) if os.path.exists(PATH) else None
    data = data or {"sites": []}
    data["sites"] = [s for s in data["sites"] if s["site_number"] != args.site]
    data["sites"].append({
        "site_number": args.site,
        "confidence": "verified",
        "evidence": args.photo,
        "kind": args.kind,
        "note": args.note,
        "verified_by": "own photograph",
        "date": args.date or date.today().isoformat(),
    })
    data["sites"].sort(key=lambda s: s["site_number"])
    with open(PATH, "w") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True, width=88)
    print(f"  site {args.site} recorded as verified, citing {args.photo}")
    print(f"  {len(data['sites'])} site(s) verified from primary evidence")


if __name__ == "__main__":
    main()
