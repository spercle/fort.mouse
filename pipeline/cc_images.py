"""Fetch the freely-licensed Fort Wilderness images and record their attribution.

    python3 pipeline/cc_images.py

These are DECORATION ONLY — home page, about page, category illustration. They must
never appear on a Site page, where a reader could take them as evidence about the site
they are looking at. See the photo policy in docs/data-model.md.

Every image is CC BY or CC BY-SA, which means attribution is mandatory and must travel
with the image. `data/credits.yaml` is written for the templates to render.

Note on BY-SA: displaying the work with credit does not affect the licence of anything
around it. Resizing for the web is an adaptation, and the adaptation carries the same
licence — which it does, since we credit and link the licence on every use. Don't crop
or recolour in a way that changes what the photo shows.

Only resize what needs it. `sips -Z` re-encodes, and on an already-web-sized JPEG that
makes the file BIGGER, not smaller.
"""

import json
import os
import ssl
import urllib.request

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static", "cc")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

LICENCE_URL = {
    "by-2.0": "https://creativecommons.org/licenses/by/2.0/",
    "by-sa-2.0": "https://creativecommons.org/licenses/by-sa/2.0/",
    "by-sa-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
}

# Hand-picked from an Openverse search restricted to by / by-sa / cc0. Twenty of the
# twenty-five results were one photographer's Christmas-lights set; these are the ones
# that actually say something about the campground.
IMAGES = [
    {
        "id": "loop-400-airstream",
        "title": "2007 Airstream International at Loop 400",
        "creator": "foqus",
        "licence": "by-2.0",
        "landing": "https://www.flickr.com/photos/86485152@N00/2969945960",
        "note": "The only loop-specific freely-licensed photo of Fort Wilderness "
                "found anywhere. Loop 400, Whispering Pine Way.",
    },
    {
        "id": "trail-ride",
        "title": "Trail ride, Fort Wilderness Campground",
        "creator": "gruntzooki",
        "licence": "by-sa-2.0",
        "landing": "https://www.flickr.com/photos/37996580417@N01/335736635",
        "note": "Tri-Circle-D Ranch trail ride.",
    },
    {
        "id": "abandoned-trail",
        "title": "Abandoned trail at Disney's Fort Wilderness",
        "creator": "Marco from Orlando, Florida",
        "licence": "by-2.0",
        "landing": "https://commons.wikimedia.org/w/index.php?curid=47087441",
        "note": "One of the closed trails — the vintage Fort Wilderness people miss.",
    },
    {
        "id": "railroad-remnants",
        "title": "Fort Wilderness Railroad track remnants",
        "creator": "Evan Wohrman",
        "licence": "by-sa-2.0",
        "landing": "https://www.flickr.com/photos/46027550@N00/50138385543",
        "note": "The Fort Wilderness Railroad ran 1973-1980. Track is still findable.",
    },
    {
        "id": "trailer-christmas-lights",
        "title": "Trailer Christmas lights, Fort Wilderness Campground",
        "creator": "gruntzooki",
        "licence": "by-sa-2.0",
        "landing": "https://www.flickr.com/photos/37996580417@N01/335744033",
        "note": "The loops at Christmas, 2006.",
    },
]


def openverse_url(landing):
    """Resolve a landing page back to the direct image via the Openverse API."""
    q = urllib.parse.quote(landing)
    url = f"https://api.openverse.org/v1/images/?q={q}&page_size=1"
    req = urllib.request.Request(url, headers={"User-Agent": "fort-mouse/0.1"})
    with urllib.request.urlopen(req, timeout=45, context=CTX) as r:
        data = json.loads(r.read())
    results = data.get("results") or []
    return results[0].get("url") if results else None


def main():
    import urllib.parse  # noqa: F401  (used by openverse_url)

    cached = json.load(open(os.path.join(
        os.environ.get("FM_SCRATCH", "/tmp"), "cc-images.json"))) \
        if os.path.exists(os.path.join(os.environ.get("FM_SCRATCH", "/tmp"),
                                       "cc-images.json")) else []
    by_landing = {c["foreign"]: c for c in cached}

    os.makedirs(OUT, exist_ok=True)
    credits = []

    for img in IMAGES:
        direct = (by_landing.get(img["landing"]) or {}).get("url")
        if not direct:
            print(f"  {img['id']}: no direct URL cached, skipping")
            continue
        dest = os.path.join(OUT, f"{img['id']}.jpg")
        try:
            req = urllib.request.Request(direct, headers={"User-Agent": "fort-mouse/0.1"})
            data = urllib.request.urlopen(req, timeout=90, context=CTX).read()
            if data[:2] != b"\xff\xd8" and data[:4] != b"\x89PNG":
                raise RuntimeError("not an image")
            open(dest, "wb").write(data)
            print(f"  {img['id']}: {len(data):>9,}B  {img['licence']}")
        except Exception as exc:
            print(f"  {img['id']}: FAILED {exc}")
            continue

        credits.append({
            "id": img["id"],
            "file": f"/cc/{img['id']}.jpg",
            "title": img["title"],
            "creator": img["creator"],
            "licence": img["licence"].upper().replace("-", " ", 1),
            "licence_url": LICENCE_URL[img["licence"]],
            "landing": img["landing"],
            "note": img["note"],
        })

    with open(os.path.join(ROOT, "data", "credits.yaml"), "w") as fh:
        yaml.safe_dump({"decoration": credits}, fh, sort_keys=False, allow_unicode=True)
    print(f"\n{len(credits)} image(s) -> static/cc/, attribution -> data/credits.yaml")
    print("DECORATION ONLY. Never on a Site page — see docs/data-model.md.")


if __name__ == "__main__":
    main()
