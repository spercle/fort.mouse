"""Schema validation for the data files. Pure stdlib + PyYAML.

    python3 pipeline/validate.py

This is deliberately in the pipeline rather than the site generator. A bad value should
be refused at the point it is *written*, not discovered later when something tries to
render it. `derive.py` and `build_data.py` both call it.
"""

import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ABSENT = {"unmeasured", "occluded", "unknown"}
SOURCES = {"observed", "aerial", "county-record", "reported", "seeded",
           "disney-category", "none"}
CONFIDENCE = {"hypothesis", "inferred", "verified", "unverified"}
CATEGORIES = {"Tent/Pop-Up", "Full Hook-Up", "Preferred", "Premium", "Premium Meadow"}

# Sanity bounds. A pad outside these is a digitizing mistake, not a discovery.
BOUNDS = {
    # The usable site — what a rig has to fit into, and what Disney publishes.
    "site_length_ft": (15.0, 90.0),
    "site_width_ft": (6.0, 30.0),
    # The poured concrete within it, which is routinely much shorter. Site 101 is
    # 45 ft of site over a 24 ft slab, so the floor here has to be far lower.
    "pad_length_ft": (6.0, 90.0),
    "pad_width_ft": (4.0, 30.0),
    "pad_orientation_deg": (0.0, 180.0),
    "road_offset_ft": (0.0, 300.0),
}


class Invalid(Exception):
    pass


def _measure(errors, where, key, value):
    """A field is a number in range, or a named absence. Nothing else."""
    if value is None:
        return
    if isinstance(value, str):
        if value not in ABSENT:
            errors.append(
                f"{where}.{key}: {value!r} is not a measurement or one of "
                f"{sorted(ABSENT)}")
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{where}.{key}: expected a number, got {type(value).__name__}")
        return
    lo, hi = BOUNDS.get(key, (None, None))
    if lo is not None and not (lo <= value <= hi):
        errors.append(f"{where}.{key}: {value} is outside {lo}-{hi} — check the digitizing")


def validate_loop(data, name="loop"):
    errors = []
    for key in ("loop", "loop_name", "category", "sites"):
        if key not in data:
            errors.append(f"{name}: missing required key {key!r}")
    if errors:
        raise Invalid("\n".join(errors))

    if data["category"] not in CATEGORIES:
        errors.append(f"{name}.category: {data['category']!r} is not one of "
                      f"{sorted(CATEGORIES)}")

    base = data.get("category_baseline") or {}
    for key in ("site_length_ft", "site_width_ft", "sewer", "max_occupancy"):
        if key not in base:
            errors.append(f"{name}.category_baseline: missing {key!r}")

    seen = set()
    for i, site in enumerate(data.get("sites") or []):
        where = f"{name}.sites[{i}]"
        n = site.get("site_number")
        if not isinstance(n, int):
            errors.append(f"{where}.site_number: expected an integer, got {n!r}")
            continue
        if n in seen:
            errors.append(f"{where}.site_number: {n} appears more than once")
        seen.add(n)
        if n // 100 * 100 != data["loop"]:
            errors.append(f"{where}.site_number: {n} does not belong to loop {data['loop']}")

        for key in BOUNDS:
            _measure(errors, where, key, site.get(key))

        conf = site.get("number_confidence")
        if conf is not None and conf not in CONFIDENCE:
            errors.append(f"{where}.number_confidence: {conf!r} not in {sorted(CONFIDENCE)}")

        src = site.get("source")
        if src is not None and src not in SOURCES:
            errors.append(f"{where}.source: {src!r} not in {sorted(SOURCES)}")

    if errors:
        raise Invalid("\n".join("  " + e for e in errors))


def validate_seed(data, name="seed"):
    errors = []
    if "attribution" not in data or "credit" not in (data.get("attribution") or {}):
        errors.append(f"{name}: seeds must carry attribution.credit — see ADR-0004")
    for i, site in enumerate(data.get("sites") or []):
        where = f"{name}.sites[{i}]"
        if not isinstance(site.get("site_number"), int):
            errors.append(f"{where}.site_number: expected an integer")
            continue
        for key in ("site_length_ft", "site_width_ft", "pad_length_ft", "pad_width_ft"):
            _measure(errors, where, key, site.get(key))
    if errors:
        raise Invalid("\n".join("  " + e for e in errors))


def validate_all(verbose=True):
    checked = 0
    for kind, folder, fn in (("loop", "loops", validate_loop),
                             ("seed", "seeds", validate_seed)):
        d = os.path.join(ROOT, "data", folder)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".yaml"):
                continue
            path = os.path.join(d, f)
            data = yaml.safe_load(open(path))
            fn(data, f"data/{folder}/{f}")
            checked += 1
            if verbose:
                print(f"  ok  data/{folder}/{f}")
    return checked


if __name__ == "__main__":
    try:
        n = validate_all()
    except Invalid as exc:
        print("VALIDATION FAILED\n" + str(exc), file=sys.stderr)
        sys.exit(1)
    print(f"{n} file(s) valid")
