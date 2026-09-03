# fort.mouse

A queryable reference for the individual campsites at Disney's Fort Wilderness.

You don't choose your campsite there — you book a category, request a loop, and a cast
member assigns you a number at check-in. This is the reference for what that number
actually gets you.

**Every figure is measured from public aerial imagery, comes from Disney's own published
specs, or is credited to whoever published it first until we verify it ourselves.** Where
something has not been measured, the page says so.

## Build

```
./build.sh          # validate -> resolve -> render, output in public/
hugo server         # live preview on :1313
```

Deploy is a copy: `rsync -a --delete public/ user@server:/var/www/fortmouse/`

## Layout

```
data/loops/      machine-owned, written by pipeline/derive.py     (ADR-0002)
data/seeds/      human-owned attributed seed measurements         (ADR-0004)
data/sites/      human-owned notes — the irreplaceable half
data/reference/  OSM + county geometry
data/resolved/   generated; the only thing Hugo reads
pipeline/        Python: measurement, validation, maps, imagery
layouts/         Hugo templates
```

## Pipeline

| Command | Does |
|---|---|
| `pipeline/bootstrap_loops.py` | Create starting files for all 21 loops from public records |
| `pipeline/qgis_setup.py` | Build the QGIS digitizing project (run inside QGIS) |
| `pipeline/derive.py <loop> <pads.geojson>` | Digitized pads -> measurements |
| `pipeline/seed_measurements.py` | Ingest attributed third-party figures |
| `pipeline/loop_context.py` | Cache each loop's OSM surroundings |
| `pipeline/loop_maps.py` | Draw the campground maps |
| `pipeline/thumbnails.py [--loops]` | Cut aerials from county orthoimagery |
| `pipeline/validate.py` | Schema + sanity checks |
| `pipeline/test_geom.py` | Prove the measurement maths |

Start with `pipeline/README.md` for the digitizing workflow.

## Decisions

- [ADR-0001](docs/adr/0001-independent-data-sourcing.md) — independent sourcing *(superseded)*
- [ADR-0002](docs/adr/0002-machine-and-human-data-are-separate-files.md) — machine and human data are separate files
- [ADR-0003](docs/adr/0003-imagery-source-and-legal-basis.md) — imagery source and legal basis
- [ADR-0004](docs/adr/0004-seed-then-verify-sourcing.md) — seed, attribute, verify, replace

Unofficial and unaffiliated. Not authorized by, endorsed by, or connected with
The Walt Disney Company.
