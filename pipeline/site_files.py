"""Read and write data/sites/<number>.md — one file per site, everything about it.

This is the human-owned half of the data, promised by ADR-0002 and finally implemented.
Facts go in the YAML frontmatter, prose goes in the body:

    ---
    site: 101
    site_length_ft: 45
    pad_length_ft: 24
    ---

    The site runs the full 45 ft, but the concrete is only 24 ft of it.

Nothing generated is ever written here. derive.py rewrites data/loops/ freely; these
files survive it, which is the whole point — re-measuring a loop from imagery must not
be able to discard something someone stood on the pad to find out.

A site with nothing worth saying has no file. Deleting a file returns the site to
whatever the aerial pass knows about it.
"""

import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITES = os.path.join(ROOT, "data", "sites")

# Every key a site file may set. Anything else is a typo, and a typo that silently did
# nothing would be worse than a crash — you would believe a measurement was recorded.
MEASUREMENTS = {
    "site_length_ft", "site_width_ft", "pad_length_ft", "pad_width_ft",
    "pad_orientation_deg", "road_offset_ft", "pad_surface", "backs_onto",
    "approach_side", "backing_difficulty",
}
KEYS = MEASUREMENTS | {"site", "loop", "measured", "verified", "source"}

# Keys allowed inside the `verified:` block.
VERIFIED_KEYS = {"evidence", "kind", "note", "date", "by", "confidence"}

# How the numbers in this file were arrived at. Defaults to `observed` — a tape measure
# on the pad — because that is why you would be writing one by hand. Say otherwise when
# it is otherwise: a guest's report and your own measurement must not read the same.
SOURCES = {"observed", "reported", "county-record", "disney-category"}

# How hard the pad is to back into. A judgement, not a measurement, but the one thing
# a driver most wants to know and the one thing no aerial photograph can say. Kept to a
# closed set so it means the same on every site — free text would give us "tight-ish",
# "not bad" and "PITA" and nothing comparable.
BACKING = {"easy", "middling", "hard"}

FENCE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)


class SiteFileError(Exception):
    pass


def parse(text, where):
    """Split frontmatter from body. Both halves are optional in principle; a file with
    no frontmatter is almost certainly a mistake, so it is rejected rather than read as
    pure prose."""
    m = FENCE.match(text.lstrip("﻿"))
    if not m:
        raise SiteFileError(f"{where}: no --- frontmatter block at the top of the file")
    try:
        front = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        raise SiteFileError(f"{where}: frontmatter is not valid YAML — {exc}")
    if not isinstance(front, dict):
        raise SiteFileError(f"{where}: frontmatter must be a mapping of key: value")
    return front, m.group(2).strip()


def load_all(rosters):
    """Every site file, keyed by site number.

    `rosters` maps site number -> loop number, so a file naming a site that does not
    exist is caught here rather than silently building a page nobody can reach.
    """
    out = {}
    if not os.path.isdir(SITES):
        return out

    errors = []
    for name in sorted(os.listdir(SITES)):
        if not name.endswith(".md") or name.startswith("_"):
            continue
        where = f"data/sites/{name}"
        stem = name[:-3]
        if not stem.isdigit():
            errors.append(f"{where}: filename must be the site number, e.g. 101.md")
            continue

        try:
            front, body = parse(open(os.path.join(SITES, name)).read(), where)
        except SiteFileError as exc:
            errors.append(str(exc))
            continue

        number = int(stem)
        if "site" in front and front["site"] != number:
            errors.append(f"{where}: says site {front['site']} but is named {number}.md")
            continue

        unknown = set(front) - KEYS
        if unknown:
            errors.append(f"{where}: unknown key(s) {sorted(unknown)} — "
                          f"allowed: {sorted(KEYS)}")
            continue

        if number not in rosters:
            errors.append(f"{where}: site {number} is not in any loop roster")
            continue
        if "loop" in front and front["loop"] != rosters[number]:
            errors.append(f"{where}: says loop {front['loop']}, but site {number} is in "
                          f"loop {rosters[number]}")
            continue

        src = front.get("source")
        if src is not None and src not in SOURCES:
            errors.append(f"{where}: source: {src!r} is not one of {sorted(SOURCES)}")
            continue

        back = front.get("backing_difficulty")
        if back is not None and back not in BACKING:
            errors.append(f"{where}: backing_difficulty: {back!r} is not one of "
                          f"{sorted(BACKING)}")
            continue

        ver = front.get("verified")
        if ver is not None:
            if not isinstance(ver, dict):
                errors.append(f"{where}: `verified:` must be a block with at least "
                              f"`evidence:` under it")
                continue
            bad = set(ver) - VERIFIED_KEYS
            if bad:
                errors.append(f"{where}: unknown key(s) in verified: {sorted(bad)}")
                continue
            if not ver.get("evidence"):
                errors.append(f"{where}: verified: needs `evidence:` — a photograph is "
                              f"what makes it verified rather than assumed")
                continue

        if not any(k in front for k in MEASUREMENTS) and not ver and not body:
            errors.append(f"{where}: nothing in it — no measurements, no verification, "
                          f"no notes. Delete the file rather than leaving it empty.")
            continue

        front["notes"] = body or None
        out[number] = front

    if errors:
        raise SiteFileError("\n".join("  " + e for e in errors))
    return out


def write(number, front, body, path=None):
    """Write a site file, frontmatter first. Used by observe.py and verify_site.py;
    hand-editing the file is equally valid and is the expected case."""
    os.makedirs(SITES, exist_ok=True)
    path = path or os.path.join(SITES, f"{number}.md")

    ordered = {"site": number}
    for k in ("loop", "source", "site_length_ft", "site_width_ft", "pad_length_ft",
              "pad_width_ft", "pad_orientation_deg", "road_offset_ft", "pad_surface",
              "backs_onto", "approach_side", "backing_difficulty", "measured",
              "verified"):
        if front.get(k) is not None:
            ordered[k] = front[k]

    text = "---\n" + yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True,
                                    width=88) + "---\n"
    if body:
        text += "\n" + body.strip() + "\n"
    open(path, "w").write(text)
    return path


def read_one(number):
    """Existing frontmatter and body for a site, so a CLI can update one field without
    throwing away the prose someone wrote underneath it."""
    path = os.path.join(SITES, f"{number}.md")
    if not os.path.exists(path):
        return {}, ""
    front, body = parse(open(path).read(), f"data/sites/{number}.md")
    front.pop("notes", None)
    return front, body


def rosters():
    """site number -> loop number, from the machine-owned loop files."""
    loops = os.path.join(ROOT, "data", "loops")
    out = {}
    for f in sorted(os.listdir(loops)):
        if f.endswith(".yaml"):
            d = yaml.safe_load(open(os.path.join(loops, f))) or {}
            for s in d.get("sites") or []:
                out[s["site_number"]] = d["loop"]
    return out
