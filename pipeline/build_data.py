"""Validate, merge and resolve the data into what Hugo renders.

    python3 pipeline/build_data.py

Reads:
    data/loops/*.yaml    machine-owned, written by derive.py
    data/seeds/*.yaml    human-owned attributed seeds (ADR-0004)
Writes:
    data/resolved/*.yaml         one per loop, every field already resolved
    data/resolved/index.json     the client-side site-number lookup

Precedence lives here, not in a template: a measurement of our own always beats a seed,
a seed always beats an absence. Hugo then renders a value that already knows what it is
and where it came from.
"""

import json
import os
import sys

import yaml

from validate import Invalid, validate_loop, validate_seed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOPS = os.path.join(ROOT, "data", "loops")
SEEDS = os.path.join(ROOT, "data", "seeds")
OUT = os.path.join(ROOT, "data", "resolved")
AERIAL = os.path.join(ROOT, "static", "aerial")

ABSENT = {"unmeasured", "occluded", "unknown"}

MEASURES = ["pad_length_ft", "pad_width_ft", "pad_orientation_deg",
            "road_offset_ft", "pad_surface", "backs_onto", "approach_side"]

LABEL = {
    "unmeasured": "Unmeasured",
    "occluded": "Hidden in all imagery",
    "unknown": "Unknown",
}
NOTE = {
    "unmeasured": "Nobody has measured this yet.",
    "occluded": ("A rig or tree canopy covers this pad in every available aerial "
                 "capture. It resolves only on foot."),
    "unknown": "No source we have can answer this.",
}
UNITS = {"pad_length_ft": " ft", "pad_width_ft": " ft",
         "pad_orientation_deg": "°", "road_offset_ft": " ft"}


def resolve(raw, source):
    """One field, as the templates will see it."""
    if raw is None:
        return {"state": "unmeasured", "display": LABEL["unmeasured"],
                "note": NOTE["unmeasured"], "source": None}
    if isinstance(raw, str) and raw in ABSENT:
        return {"state": raw, "display": LABEL[raw], "note": NOTE[raw], "source": None}
    return {"state": "measured", "value": raw, "source": source}


def main():
    try:
        loops = {}
        for f in sorted(os.listdir(LOOPS)) if os.path.isdir(LOOPS) else []:
            if f.endswith(".yaml"):
                data = yaml.safe_load(open(os.path.join(LOOPS, f)))
                validate_loop(data, f"data/loops/{f}")
                loops[data["loop"]] = data

        seeds = {}
        if os.path.isdir(SEEDS):
            for f in sorted(os.listdir(SEEDS)):
                if f.endswith(".yaml"):
                    data = yaml.safe_load(open(os.path.join(SEEDS, f)))
                    validate_seed(data, f"data/seeds/{f}")
                    seeds[data["loop"]] = data
    except Invalid as exc:
        print("VALIDATION FAILED — nothing written\n" + str(exc), file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUT, exist_ok=True)
    index = []
    totals = {"sites": 0, "own": 0, "seeded": 0}

    for loop_no, loop in sorted(loops.items()):
        seed_file = seeds.get(loop_no, {})
        credit = (seed_file.get("attribution") or {}).get("credit")
        by_number = {s["site_number"]: s for s in seed_file.get("sites", [])}

        out_sites, own, seeded, lengths = [], 0, 0, []

        for site in loop["sites"]:
            n = site["site_number"]
            own_source = site.get("source") or "aerial"
            fields = {k: resolve(site.get(k), own_source) for k in MEASURES}

            seed = by_number.get(n)
            if seed:
                for key in ("pad_length_ft", "pad_width_ft"):
                    if fields[key]["state"] != "measured" and seed.get(key) is not None:
                        fields[key] = {
                            "state": "measured", "value": seed[key], "source": "seeded",
                            "credit": credit,
                            "published": seed.get(key.replace("_ft", "_published")),
                        }

            for key, unit in UNITS.items():
                f = fields[key]
                if f["state"] == "measured":
                    f["display"] = f"{f['value']}{unit}"
            for key in ("pad_surface", "backs_onto", "approach_side"):
                f = fields[key]
                if f["state"] == "measured":
                    f["display"] = str(f["value"])

            length = fields["pad_length_ft"]
            if length["state"] == "measured":
                if length["source"] == "seeded":
                    seeded += 1
                else:
                    own += 1
                    lengths.append(length["value"])

            # An aerial is only this site's if we know where this site is. A file
            # left behind from an earlier run — demo data, a since-corrected
            # centroid — must not be shown as a photograph of the pad.
            has_real_position = bool(site.get("centroid"))
            aerial = f"/aerial/{n}.jpg" if has_real_position else None
            out_sites.append({
                "site_number": n,
                "fields": fields,
                "number_confidence": site.get("number_confidence", "unverified"),
                "imagery_vintage": site.get("imagery_vintage"),
                "notes": site.get("notes"),
                "aerial": aerial if (aerial and os.path.exists(
                    os.path.join(AERIAL, f"{n}.jpg"))) else None,
                "is_measured": length["state"] == "measured",
                "seeded_credit": credit if length.get("source") == "seeded" else None,
            })
            index.append({"n": n, "l": loop_no})

        lengths.sort()
        resolved = {
            "loop": loop_no,
            "loop_name": loop["loop_name"],
            "category": loop["category"],
            "status": loop.get("status"),
            "category_baseline": loop["category_baseline"],
            "county_record": loop.get("county_record"),
            "road_length_ft": loop.get("road_length_ft") or loop.get("road_length_ft_osm"),
            "loop_note": loop.get("loop_note"),
            "sign_evidence": loop.get("sign_evidence"),
            "aerial": (f"/loop-aerial/{loop_no}.jpg"
                       if os.path.exists(os.path.join(ROOT, "static", "loop-aerial",
                                                      f"{loop_no}.jpg")) else None),
            "open_questions": loop.get("open_questions") or [],
            "site_count": len(out_sites),
            "own_count": own,
            "seeded_count": seeded,
            "median_pad_ft": lengths[len(lengths) // 2] if lengths else None,
            "longest_pad_ft": lengths[-1] if lengths else None,
            "sites": out_sites,
        }
        with open(os.path.join(OUT, f"{loop_no}.yaml"), "w") as fh:
            yaml.safe_dump(resolved, fh, sort_keys=False, allow_unicode=True)

        totals["sites"] += len(out_sites)
        totals["own"] += own
        totals["seeded"] += seeded
        print(f"  loop {loop_no}: {len(out_sites)} sites, {own} ours, {seeded} seeded")

    src = os.path.join(ROOT, "data", "credits.yaml")
    if os.path.exists(src):
        with open(os.path.join(OUT, "credits.yaml"), "w") as fh:
            fh.write(open(src).read())

    # assets/, not static/, so Hugo can fingerprint it — see baseof.html.
    assets = os.path.join(ROOT, "assets")
    os.makedirs(assets, exist_ok=True)
    json.dump(index, open(os.path.join(assets, "search-index.json"), "w"))
    print(f"\n{totals['sites']} sites across {len(loops)} loop(s) -> data/resolved/")
    print(f"  {totals['own']} measured by us, {totals['seeded']} still seeded")


if __name__ == "__main__":
    main()
