# fort.mouse

A queryable reference for the individual campsites at Disney's Fort Wilderness.

You don't choose your campsite there — you book a *category*, request a *loop*, and a cast
member assigns you a *site number* at check-in. Disney publishes five pad dimensions for
~845 campsites and nothing per site. This fills that gap.

**Every figure is measured from public aerial imagery, comes from Disney's own published
specs, or is credited to whoever published it first until we verify it ourselves.** Where
something has not been measured, the page says so out loud.

---

## Requirements

| | Version used | Why | Install |
|---|---|---|---|
| **Hugo** (extended) | 0.164 | Builds the site. Needs ≥ 0.126 for Content Adapters. | `brew install hugo` |
| **Python** | 3.9+ | The whole data pipeline. | preinstalled on macOS |
| **PyYAML** | any | The only Python dependency. | `pip3 install pyyaml` |
| **QGIS** | 4.2 | Digitizing pads from aerial imagery. Only needed when measuring. | `brew install --cask qgis` |

There is no `node_modules`, no build toolchain, and no database. The pipeline is stdlib
Python plus PyYAML; the geometry maths is hand-rolled precisely so this still runs in ten
years.

---

## Build and run

```bash
./serve.sh          # live preview at http://localhost:1313 — use this while working
./build.sh          # full deterministic build. Output in public/
./build.sh --icons  # ...and re-rasterise the icons (~10s, rarely needed)
```

Use `./serve.sh` rather than bare `hugo server`. The configured `baseURL` points at the
GitHub Pages subpath, so a plain `hugo server` serves everything under
`/fort.mouse/` and the root 404s. `serve.sh` overrides it back to `/`.

`build.sh` refuses to run while a dev server is live — `--cleanDestinationDir` deletes
`public/` out from under it and leaves it serving 404s.

## Deploying

### GitHub Pages (automatic)

Every push to `master` builds and deploys via `.github/workflows/pages.yml`.

The workflow turns Pages on itself (`configure-pages` with `enablement: true`), so no
setup should be needed. If the first run still fails with:

```
Get Pages site failed. Please verify that the repository has Pages enabled
```

set it by hand once: *Settings → Pages → Build and deployment → Source: **GitHub
Actions*** — then re-run the job. Enablement over the API needs the repo to permit it,
which some org and private repos do not.

The site lands at **https://spercle.github.io/fort.mouse/** — a subpath, which is why
every internal URL goes through Hugo's `relURL`.

> **Two subpath traps, both of which shipped broken once.** `build.sh` now runs
> `pipeline/check_links.py` to catch them.
>
> **1. Generated SVG bypasses `relURL` entirely.** The pipeline writes
> `<image href="/loop-base/100.jpg">` into the map, Hugo inlines it verbatim, and it
> resolves off the site root in production while working perfectly on a root-served
> dev server. The template rewrites it now.
>
> **2. Hugo appends a piped value as the LAST argument.** So
> `readFile $x | replace "a" "b"` means `replace("a", "b", <file>)` and silently
> returns `"a"` — which replaced an entire map with the string `/loop-base/`. Call
> `replace` directly.
>
> **Careful with `relURL`:** Hugo treats a leading `/` as *already relative to the host
> root* and will skip the baseURL subpath entirely. `{{ "/css/x.css" | relURL }}` gives
> `/css/x.css`; `{{ "css/x.css" | relURL }}` gives `/fort.mouse/css/x.css`. Always pass
> the path **without** a leading slash.

CI regenerates only what is free and offline — resolved data, campground maps, loop
signs, icons. Aerials and CC imagery are **committed**, so the build never re-fetches
from Orange County's GIS server or Flickr.

### Anywhere else

The output is inert files. No runtime, no database:

```bash
rsync -a --delete public/ user@server:/var/www/fortmouse/
```

Change `baseURL` in `hugo.toml` to match wherever it lands.

---

## Layout

```
data/
  loops/       MACHINE-OWNED.  Written by derive.py. Safe to delete and regenerate.
  seeds/       HUMAN-OWNED.    Attributed third-party measurements.
  sites/       HUMAN-OWNED.    Your notes. The irreplaceable half of the repo.
  reference/   Fetched OSM + Orange County geometry. Committed; slow to refetch.
  resolved/    GENERATED. The only thing Hugo reads. Gitignored.

pipeline/      Python. Measurement, validation, maps, imagery.
layouts/       Hugo templates.
content/       Two Content Adapters that generate 845 site pages + 21 loop pages.
static/        CSS, plus generated maps and aerials (gitignored).
docs/adr/      Decisions and why.
docs/research/ What was found before building.
```

**Why data is split three ways:** derived fields get regenerated wholesale every time the
measurement method improves; your notes are written once, by hand, and are irreplaceable.
Keeping them in separate files makes data loss impossible rather than merely unlikely.
See [ADR-0002](docs/adr/0002-machine-and-human-data-are-separate-files.md).

---

## How to update things

### Change a measurement

Measurements are never edited by hand. Re-digitize and re-derive:

```bash
python3 pipeline/derive.py 1200 work/loop-1200-pads.geojson
./build.sh
```

`derive.py` refuses to overwrite a loop with an empty roster, so a bad export can't wipe
your work.

### Search

The **Find** box in the masthead searches site numbers, loop numbers, loop names and
categories — "1204", "Dogwood", "Premium Meadow" all work. It runs entirely in the
browser against `assets/search-index.json`, which `build_data.py` regenerates on every
build; there is nothing to reindex by hand.

Results carry three dots: **has photographs**, **measured**, **number verified**, so you
can see what is behind a site before clicking into it.

The index is deliberately tiny — 12 KB for 844 sites and 21 loops, positional arrays
rather than objects, because 844 rows of repeated key names cost more than the data.
Adding a searchable field means adding it there and to the matcher in
`layouts/_default/baseof.html`.

### Say something about a site

Everything known about one site lives in **one file**: `data/sites/101.md`. Facts in
the frontmatter, prose underneath.

```markdown
---
site: 101
loop: 100

site_length_ft: 45
pad_length_ft: 24          # poured concrete only
pad_width_ft: 10
backs_onto: basketball goal

verified:                  # only with a photograph to cite
  evidence: /photos/101-1.jpg
  kind: post
  note: The numbered post is legible, reading 101.
---

The concrete is short for the site — fine for a trailer, tight if you want
the whole rig on slab.
```

Copy `data/sites/_TEMPLATE.md`, rename it to the site number, delete what you don't
have. Every key is optional except `site`. A site with no file just shows what the
aerial pass knows; delete a file and it reverts.

**Site and pad are different measurements** (ADR-0005). The site is the usable length
a rig has to fit into, concrete and apron together — this is what Disney publishes.
The pad is the poured concrete inside it, often far shorter: site 101 is 45 ft of site
over a 24 ft slab. Aerial tracing produces site dimensions, because the slab and the
apron are one surface at that resolution.

**A site file overrides the aerial pass, field by field.** Set only `pad_width_ft` and
the traced `site_length_ft` still shows; set `site_length_ft` and yours replaces the
traced one outright. Nothing merges or averages — the better source wins the field.

By default a site file claims `observed`, a tape measure on the pad, because that is
why you would write one by hand. When it is something else, say so:

```yaml
source: reported        # observed | reported | county-record | disney-category
```

A guest's report and your own measurement must not read the same on the page, and only
`observed` gets the "measured on the ground" callout.

These files are **human-owned**. `derive.py` never touches them, so re-running the
aerial pass cannot overwrite something you stood on the pad to find out. Typos are
caught at build time rather than silently ignored — an unknown key, a site that is not
in any roster, a `verified:` block with no evidence, and a wrong `loop:` all stop the
build and name the file.

There are two shortcuts if you'd rather not open an editor. Both preserve everything
already in the file, including the prose:

```bash
python3 pipeline/observe.py 101 --site-length 45 --pad-length 24 --pad-width 10
python3 pipeline/verify_site.py 1420 --photo /photos/1420-2.jpg --note "Post legible."
```

### Add photographs

Drop them in `incoming/` with any filename, then:

```bash
python3 pipeline/ingest_photos.py            # dry run, says what it would do
python3 pipeline/ingest_photos.py --apply    # moves and records them
```

Each is matched to a site by, in order of confidence: a **site number in the filename**,
then **GPS in the photo's EXIF** matched to the nearest known site within 160 ft, then
nothing — reported and left alone rather than guessed at.

A GPS-tagged photo taken standing on a site is a position fix, which is the one thing
aerial imagery cannot give us; the distance to the mapped position is recorded so it can
be judged. EXIF is parsed by hand (no image dependencies) and proven by
`pipeline/test_exif.py`, which builds a JPEG with known coordinates and checks they come
back within a few feet.

### Add a note about a site

Notes are yours and the pipeline never touches them. Create `data/sites/1204.md`:

```markdown
---
site_number: 1204
---
Backs onto the canal. The picnic table is on the wrong side of the pad — you eat
looking at your own rig. Bathhouse is a two-minute walk, but the path is unlit.
```

### Seed measurements from a published source

Facts aren't copyrightable, but attribution is not optional. Tab-separated, one site
per line:

```
site    width   length
1204    11-12   52
1205    17-19   75
```

```bash
python3 pipeline/seed_measurements.py 1200 work/wp-1200.tsv \
  --credit "The Wilderness Princess" --url https://example.com/source
```

Seeded values render **amber and credited**, and are replaced automatically the moment
your own measurement exists. See [ADR-0004](docs/adr/0004-seed-then-verify-sourcing.md).

### Mark a pad you genuinely cannot see

Three absent states, and they mean different things:

| Value | Meaning |
|---|---|
| `unmeasured` | Nobody has looked yet |
| `occluded` | Looked in every imagery vintage; a rig or canopy covers it. Only resolves on foot |
| `unknown` | No source we have can answer it |

### Add a loop, or start over on one

```bash
python3 pipeline/bootstrap_loops.py            # leaves existing files alone
python3 pipeline/bootstrap_loops.py --force    # rebuilds all 21 from public records
```

### Regenerate the maps and imagery

```bash
python3 pipeline/loop_context.py       # cache each loop's OSM surroundings (slow, network)
python3 pipeline/loop_maps.py          # redraw all 21 campground maps + card thumbnails
python3 pipeline/thumbnails.py 1200    # per-site aerials for one loop
python3 pipeline/thumbnails.py --loops # one aerial per loop
```

### Change the look

All colour lives in `static/css/site.css` as tokens on `:root`, with a dark variant. The
campground maps read the same tokens (`--map-*`), so the maps follow the site theme
automatically — but **regenerate them after a token change**, since the SVG is written at
build time:

```bash
python3 pipeline/loop_maps.py
```

### Verify a single site number

A photograph of the numbered post is primary evidence — everything else in this
project's numbering is inferred from sequence. Once the photo is filed:

```bash
python3 pipeline/verify_site.py 1420 --photo /photos/1420-2.jpg \
  --note "The numbered post is legible, reading 1420."
```

That adds a `verified:` block to `data/sites/1420.md`, keeping anything already in the
file. Writing the block by hand is exactly equivalent. Either way it is **human-owned** —
`derive.py` never touches it, so re-measuring a loop cannot silently undo a verification.
The site page swaps its "hypothesis" warning for a green verified chip and cites the
evidence.

### Record a site range read off a real sign

A loop's entrance sign states its site-number range, which makes it a **primary source**
that beats any published count. Photograph it, drop the photo in `docs/evidence/`, and
add the loop to `SIGN_VERIFIED` in `pipeline/bootstrap_loops.py`:

```python
SIGN_VERIFIED = {
    1600: {"first": 1601, "last": 1646,
           "evidence": "docs/evidence/loop-1600-sign.jpeg",
           "note": "Entrance sign reads 'Timber Trail 1601 - 1646'. TouringPlans "
                   "lists 45 sites for this loop; the sign shows 46."},
}
```

```bash
python3 pipeline/bootstrap_loops.py --force
python3 pipeline/infer_positions.py 1600
python3 pipeline/loop_signs.py
```

Every site in that loop becomes `number_confidence: verified`, the loop page cites the
sign, and the drawn sign drops its "not yet read off the real sign" caveat. This is the
cheapest possible upgrade to the data — one photo settles a whole loop's numbering.

### Add an aerial view to a loop map

Cut a basemap for the loop, then redraw. `loop_maps.py` produces a second `-aerial.svg`
for any loop that has one, and the loop page grows a Drawn / Aerial switch:

```bash
python3 pipeline/loop_basemap.py 100
python3 pipeline/loop_maps.py
```

The aerial is cut to exactly the drawn map's frame bounds, so the two share a coordinate
system and can be compared pad for pad. Drawn stays the default — it reads better; the
aerial is what you check it against.

### Change the icon

The mark lives in `static/icon.svg` and is redrawn in `pipeline/icons.py`. Edit the
shapes in both, then:

```bash
python3 pipeline/icons.py     # ~10s, writes all six PNG sizes
```

There is no ImageMagick or Pillow here and none is needed — `icons.py` contains its own
rasteriser and PNG writer, so the icons rebuild anywhere Python runs.

### Check everything is sane

```bash
python3 pipeline/validate.py         # schema + bounds on every data file
cd pipeline && python3 test_geom.py  # prove the measurement maths
```

`validate.py` enforces real limits — a pad outside 15–90 ft long or 6–30 ft wide is a
digitizing mistake, not a discovery, and the build stops.

---

## Pipeline reference

| Command | Does |
|---|---|
| `bootstrap_loops.py [--force]` | Create starting files for all 21 loops from county + OSM records |
| `qgis_setup.py` | Build the QGIS digitizing project. Run *inside* QGIS; set `LOOP` at the top |
| `derive.py <loop> <pads.geojson> [--demo]` | Digitized pads → measurements, ordered along the loop road |
| `seed_measurements.py <loop> <tsv> --credit …` | Ingest attributed third-party figures |
| `infer_positions.py [loop …]` | Provisional site positions so maps aren't blank. **A scaffold, never data** |
| `loop_context.py [loop …]` | Cache each loop's OSM woods, water, trails, comfort stations |
| `loop_maps.py` | Draw all 21 campground maps and card thumbnails |
| `thumbnails.py [loop] [--loops]` | Cut aerials from county orthoimagery |
| `cc_images.py` | Fetch the freely-licensed decoration images and record attribution |
| `build_data.py` | Validate, merge seeds, resolve every field, write `data/resolved/` |
| `validate.py` | Schema and sanity checks |
| `test_geom.py` | Prove the oriented-bounding-box maths against known pads |
| `demo.py` | Synthetic measurements for previewing the layout. Stamps `status: demo` |
| `icons.py` | Rasterise the favicon and mobile icons from scratch — no image library needed |
| `ingest_photos.py [--apply]` | File photos from `incoming/` against sites, by filename or GPS |
| `test_exif.py` | Prove the hand-rolled EXIF reader against a synthesised photo |
| `verify_site.py <site> --photo … --note …` | Record a site number confirmed from primary evidence |
| `check_links.py` | Fail the build on a reference that will 404 under the subpath |
| `loop_signs.py` | Draw each loop's entrance sign, with its site-number range |
| `loop_basemap.py <loop>` | Cut an aerial that lines up exactly with that loop's map frame |

Start with [`pipeline/README.md`](pipeline/README.md) for the digitizing workflow.

---

## The rules that are structural, not editorial

1. **Absent states are visible.** A filter that silently drops unmeasured sites gives a
   reader worse information than a blog post, with more authority.
2. **Every value carries its source.** `aerial`, `observed`, `reported`, `county-record`,
   `disney-category`, `seeded`.
3. **Category maxima are never presented as measurements.** Disney's "up to 60 × 18 ft" is
   a ceiling for a category, not a fact about your site.
4. **A photo on a site page is first-party.** County aerials, our own, or a guest's. Never
   another guide's — a measurement is a fact, a photograph is a creative work.
5. **Provisional positions never become data.** `inferred_centroid` is never `centroid`,
   so a scaffold can't produce a measurement or an aerial thumbnail.

## Decisions

- [ADR-0001](docs/adr/0001-independent-data-sourcing.md) — independent sourcing *(superseded)*
- [ADR-0002](docs/adr/0002-machine-and-human-data-are-separate-files.md) — machine and human data are separate files
- [ADR-0003](docs/adr/0003-imagery-source-and-legal-basis.md) — imagery source and legal basis
- [ADR-0004](docs/adr/0004-seed-then-verify-sourcing.md) — seed, attribute, verify, replace

---

Unofficial and unaffiliated. Not authorized by, endorsed by, or connected with
The Walt Disney Company. Resort facts are Disney's published information, cited and linked.
