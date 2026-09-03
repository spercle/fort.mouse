# Drop photos here

Any filename works. Then:

```bash
python3 pipeline/ingest_photos.py            # says what it would do
python3 pipeline/ingest_photos.py --apply    # moves and records them
```

Each photo is matched to a site by, in order of confidence:

1. **A site number in the filename** — `1204.jpg`, `site 1204 pad.jpg`, `IMG_8823 1204.jpeg`
2. **GPS in the photo's EXIF** — matched to the nearest known site, within 160 ft
3. **Neither** — reported and left here. Never guessed.

A GPS-tagged photo taken standing on the site is worth more than a picture: it is a
position fix, which is the one thing aerial imagery cannot give us. The distance to the
matched site is recorded so it can be judged later.

Photos land in `static/photos/<site>-<n>.jpg` and are recorded in `data/photos.yaml`
with the date taken, how they were matched, and their coordinates.

Anything left in here is ignored by git.
