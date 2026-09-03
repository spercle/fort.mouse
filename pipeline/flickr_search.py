"""Search Flickr for freely-licensed Fort Wilderness photos.

    export FLICKR_API_KEY=...          # free: flickr.com/services/apps/create/apply/
    python3 pipeline/flickr_search.py               # text + geo search, report only
    python3 pipeline/flickr_search.py --download    # also fetch and record attribution

Two searches run:

  TEXT — the obvious one, matching titles, descriptions and tags.

  GEO  — the useful one. Flickr can return photos *taken inside a radius*, so this asks
         for everything geotagged within 800 m of the campground centre. A geotagged
         photo is tied to a location the way nothing in a text search is, which is the
         closest thing to per-site imagery that exists outside somebody's own fieldwork.

Only licences that permit reuse AND modification are requested. NC is excluded because
it would bite the moment the site carries an affiliate link; ND is excluded because it
forbids even resizing.
"""

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

REST = "https://api.flickr.com/services/rest/"

# Flickr licence ids. Deliberately omitting 1,2,3 (NC) and 6 (ND).
LICENCES = {
    4:  ("CC BY 2.0", "https://creativecommons.org/licenses/by/2.0/"),
    5:  ("CC BY-SA 2.0", "https://creativecommons.org/licenses/by-sa/2.0/"),
    7:  ("No known copyright restrictions", "https://www.flickr.com/commons/usage/"),
    9:  ("Public Domain Mark", "https://creativecommons.org/publicdomain/mark/1.0/"),
    10: ("CC0", "https://creativecommons.org/publicdomain/zero/1.0/"),
}
WANTED = ",".join(str(k) for k in LICENCES)

FW_LAT, FW_LON = 28.4035, -81.5568

TEXT_QUERIES = [
    "fort wilderness campsite", "fort wilderness loop", "fort wilderness campground",
    "disney fort wilderness rv", "fort wilderness trailer", "fort wilderness motorhome",
]

RELEVANT = re.compile(r"(fort\s*wilderness|ft\.?\s*wilderness)", re.I)
SITE_NUM = re.compile(r"\b(?:site|loop)\s*#?\s*(\d{3,4})\b", re.I)


def call(key, method, **params):
    q = {"method": method, "api_key": key, "format": "json",
         "nojsoncallback": "1", **params}
    url = REST + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": "fort-mouse/0.1"})
    data = json.loads(urllib.request.urlopen(req, timeout=60, context=CTX).read())
    if data.get("stat") != "ok":
        raise RuntimeError(f"{data.get('code')}: {data.get('message')}")
    return data


def search(key, **params):
    out = {}
    page = 1
    while page <= 5:
        d = call(key, "flickr.photos.search", license=WANTED, per_page=250, page=page,
                 extras="license,owner_name,description,tags,url_l,url_c,geo,date_taken",
                 sort="relevance", **params)
        photos = d["photos"]["photo"]
        for p in photos:
            out[p["id"]] = p
        if page >= int(d["photos"]["pages"] or 1):
            break
        page += 1
        time.sleep(0.3)
    return out


def blob(p):
    desc = (p.get("description") or {})
    return " ".join(filter(None, [p.get("title"), p.get("tags"),
                                  desc.get("_content") if isinstance(desc, dict) else None]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    args = ap.parse_args()

    key = os.environ.get("FLICKR_API_KEY")
    if not key:
        sys.exit(
            "Set FLICKR_API_KEY first.\n\n"
            "  1. https://www.flickr.com/services/apps/create/apply/\n"
            "  2. Choose the non-commercial key — it is instant and free\n"
            "  3. export FLICKR_API_KEY=your_key_here\n")

    hits = {}

    print("TEXT search")
    for q in TEXT_QUERIES:
        try:
            got = search(key, text=q)
        except Exception as exc:
            print(f"  {q!r}: FAILED {exc}")
            continue
        keep = {i: p for i, p in got.items() if RELEVANT.search(blob(p))}
        hits.update(keep)
        print(f"  {q!r}: {len(got)} freely-licensed, {len(keep)} about Fort Wilderness")

    print("\nGEO search — anything geotagged within 800 m of the campground")
    try:
        got = search(key, lat=FW_LAT, lon=FW_LON, radius=0.8, radius_units="km")
        print(f"  {len(got)} freely-licensed geotagged photo(s) inside the campground")
        hits.update(got)
    except Exception as exc:
        print(f"  FAILED {exc}")

    print(f"\n{len(hits)} distinct candidates\n")

    numbered = {i: p for i, p in hits.items() if SITE_NUM.search(blob(p))}
    if numbered:
        print(f"--- {len(numbered)} mention a site or loop number ---")
        for p in numbered.values():
            nums = sorted(set(SITE_NUM.findall(blob(p))))
            lic = LICENCES.get(int(p.get("license", 0)), ("?", ""))[0]
            print(f"  {lic:<32} {str(nums):<14} {p.get('title','')[:44]}")
            print(f"      by {p.get('ownername','?')[:28]}  "
                  f"https://flickr.com/photos/{p['owner']}/{p['id']}")
        print()

    geotagged = [p for p in hits.values() if p.get("latitude") not in (None, 0, "0")]
    print(f"--- {len(geotagged)} carry coordinates ---")
    for p in geotagged[:25]:
        lic = LICENCES.get(int(p.get("license", 0)), ("?", ""))[0]
        print(f"  {p.get('latitude')},{p.get('longitude')}  {lic:<24} {p.get('title','')[:40]}")

    rows = []
    for p in hits.values():
        lic_id = int(p.get("license", 0))
        name, url = LICENCES.get(lic_id, ("unknown", ""))
        rows.append({
            "id": p["id"], "title": p.get("title"), "creator": p.get("ownername"),
            "licence": name, "licence_url": url,
            "landing": f"https://www.flickr.com/photos/{p['owner']}/{p['id']}",
            "image": p.get("url_l") or p.get("url_c"),
            "lat": p.get("latitude"), "lon": p.get("longitude"),
            "taken": p.get("datetaken"),
            "site_numbers": sorted(set(SITE_NUM.findall(blob(p)))) or None,
        })

    dest = os.path.join(ROOT, "work", "flickr-candidates.yaml")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w") as fh:
        yaml.safe_dump({"candidates": rows}, fh, sort_keys=False, allow_unicode=True)
    print(f"\nfull results -> work/flickr-candidates.yaml")

    if args.download:
        out = os.path.join(ROOT, "static", "cc")
        os.makedirs(out, exist_ok=True)
        n = 0
        for r in rows:
            if not r["image"]:
                continue
            try:
                req = urllib.request.Request(r["image"],
                                             headers={"User-Agent": "fort-mouse/0.1"})
                data = urllib.request.urlopen(req, timeout=90, context=CTX).read()
                open(os.path.join(out, f"flickr-{r['id']}.jpg"), "wb").write(data)
                n += 1
            except Exception as exc:
                print(f"  {r['id']}: FAILED {exc}")
        print(f"{n} image(s) -> static/cc/")

    print("\nReminder: these are DECORATION unless a photo is provably of a specific")
    print("site. A geotagged photo inside a loop is evidence about that ground; a")
    print("text-matched photo is not. See the photo policy in docs/data-model.md.")


if __name__ == "__main__":
    main()
