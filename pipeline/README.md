# Measuring a loop

**Queue: Loop 1200 (22 sites) → Loop 300 (61 sites).**

Everything below works for any loop. Change `LOOP` at the top of
`pipeline/qgis_setup.py`, and pass the loop number to `derive.py`. Loop identity comes
from `data/loops/<loop>.yaml`, so there is nothing else to register.

The one step that can't be automated: somebody has to look at each pad and draw a
rectangle on it. Everything either side of that is scripted.

Rough digitizing budget, at the observed ~76 s/pad blended average:

| Loop | Name | Sites | Road | Estimate |
|---|---|---|---|---|
| **1200** | Dogwood Drive | 22 | 828 ft | **~28 min** |
| **300** | Cypress Knee Circle | 61 | 1,679 ft | **~77 min** |

Loop 300's county blocks are known — `301-309`, `338-360`, `376-398` — and are drawn on
its map, so you know which stretch of road carries which numbers before you start.

## Before you start

**QGIS 4.2.2 is installed** at `/Applications/QGIS-final-4_2_2.app`.

Read [ADR-0003](../docs/adr/0003-imagery-source-and-legal-basis.md) first if you
haven't. The short version: **do not open Google Earth for this.** Its terms
specifically prohibit tracing features into a dataset, and one afternoon of doing it
the easy way would poison the provenance of everything else.

## 1. Project setup, once

### Fast path — let the script do it

**QGIS ▸ Plugins ▸ Python Console ▸ Show Editor**, open `pipeline/qgis_setup.py`, Run.

It sets the CRS, loads all four imagery vintages in the right stacking order, loads the
county and OSM reference layers, creates `work/loop-1200-pads.gpkg` with exactly the
schema `derive.py` expects, and zooms to the loop. Re-running it replaces its own layers
rather than duplicating them.

Then **File ▸ Save As** to keep the project (it's gitignored).

If a layer reports `FAILED`, add that one by hand from the table below — the rest still
loaded.

### By hand

**Set the project CRS to `EPSG:2236`** (NAD83 / Florida East, ftUS). This is what the
county ortho is delivered in, and it means QGIS's measure tool reads out in feet with
no conversion.

Add these as **XYZ Tiles** / **ArcGIS REST Server** layers:

| Layer | URL | Note |
|---|---|---|
| **OCPA 2025** | `https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2025/MapServer` | **Primary.** Sharpest over Loop 1200. |
| **OCPA 2022** | `.../OCPA/Aerials2022/MapServer` | **Second look.** Equally sharp, different rigs parked. |
| OCPA 2024 | `.../OCPA/Aerials2024/MapServer` | Third. Soft through the export endpoint. |
| Esri World Imagery | `https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}` | **Max zoom 21.** 2.59 in/px, 46 px across a 10 ft pad. Keep it loaded — it is the layer ADR-0003's tracing grant names. |
| NAIP 2023 | `https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer` | 30 cm — too coarse to measure, useful only to check whether a pad is clear |

Set Esri World Imagery's max zoom to 21. Zoom 22 returns an upsampled tile with no
extra detail.

Then add the reference layers from this repo:

- `data/reference/loop-1200-county-segments.geojson` — Orange County's address-range
  segments. These order the loop and bound the site numbers.
- `data/reference/loop-1200-osm-road.geojson` — the road centreline.

*Note on ADR-0003: a conservative reading of Esri's tracing grant does the digitizing
in an Esri client rather than QGIS. A free ArcGIS public account and Map Viewer
satisfies that if you ever want belt-and-braces. The public-records basis stands
either way.*

## 2. The digitizing layer

Create a **new GeoPackage or GeoJSON layer**, polygon, CRS `EPSG:2236`, with fields:

| Field | Type | Required | Values |
|---|---|---|---|
| `site_number` | integer | **yes** | e.g. `1204` |
| `pad_surface` | text | no | `concrete` \| `gravel` |
| `backs_onto` | text | no | `water` \| `woods` \| `road` \| `site` \| `comfort-station` \| `open` |
| `approach_side` | text | no | `left` \| `right` |
| `imagery_vintage` | text | no | `oc-2022` \| `oc-2024` \| `oc-2025` \| `naip-2023` |
| `number_confidence` | text | no | `hypothesis` \| `inferred` \| `verified` |
| `notes` | text | no | free text |

`site_number` is the only one `derive.py` insists on. Everything else is optional and
absent is fine — that's what the `unmeasured` state is for.

## 3. Draw the pads

**View ▸ Toolbars ▸ Shape Digitizing**, then use **Rectangle from 3 points
(projected)**:

1. Click one end of the pad's long edge.
2. Click the other end. This sets both length *and* bearing.
3. Click across to the far side to set the width.

Trace the **concrete**, not the site. The pad is what a rig parks on; the picnic table
and the grass are not part of the measurement.

### When the pad is hidden — which is most of the time

**Roughly 60% of pads have a rig parked on them or canopy over them** in any single
capture. That, not resolution, is the real work.

**Observed on Loop 1200, 2026-09-02** — the vintages are not equal, and it matters:

| Vintage | Verdict for this loop |
|---|---|
| **OCPA 2025** | Sharpest. Make this your primary. |
| **OCPA 2022** | Equally sharp, different rigs parked. Your best second look. |
| OCPA 2024 | Noticeably soft through the export endpoint. Third choice. |
| NAIP 2023 | Visibly blurry at 30 cm. Occupancy check only — never measure from it. |

The strategy is confirmed on real ground: a site occupied in both 2022 and 2024 shows
as **clean, empty concrete in 2025**. Toggle the vintages and record which one you
measured from in `imagery_vintage`.

### The part vintage-stacking does NOT solve

**Rigs move between captures. Trees don't.**

A pad under a mature oak is under that oak in all four captures, and Florida pines are
evergreen so there is no leaf-off season to wait for. So the two kinds of occlusion have
different fates:

- **Rig occlusion** — solved by toggling vintages. This is most of the problem.
- **Canopy occlusion** — not solved by any imagery. This is the residual that only
  resolves by walking the loop with a camera.

Mark the second kind `occluded` and move on. It's a real finding about the site, not a
failure to try hard enough.

*One orientation note: Loop 1200's geometric centre is wooded interior — the sites ring
the perimeter along the road. Don't be alarmed by a wall of canopy in the middle of the
loop; that's not where you're measuring.*

### Numbering

The site numbers in `data/loops/1200.yaml` are a **hypothesis** (`1201`–`1222`), based
on loops being documented as numbering sequentially from `N01`. Nobody has verified it.

The county segments bound each stretch of road to a number block, and sites run in
order along the loop — so ordering by position is usually right and wrong at the
segment boundaries. Set `number_confidence` honestly:

- `hypothesis` — inferred purely from sequence
- `inferred` — sequence plus a segment boundary or another constraint agrees
- `verified` — you have seen the numbered post, in a photo or in person

## 4. Derive

Export the digitizing layer to GeoJSON in **EPSG:4326**, then:

```
python3 pipeline/derive.py 1200 work/loop-1200-pads.geojson
```

That rewrites `data/loops/1200.yaml` with measured length, width, compass orientation,
setback from the road centreline, and the sites ordered around the loop. It reports the
count against the expected 22 and prints min/median/max pad length as a sanity check.

It **only ever writes `data/loops/`.** Your notes in `data/sites/` are never touched —
[ADR-0002](../docs/adr/0002-machine-and-human-data-are-separate-files.md).

To check the measurement math itself:

```
cd pipeline && python3 test_geom.py
```

## 5. The thing to watch for in this loop

Every Fort Wilderness resource repeats that the campground's only two **pull-through**
sites are in Loop 1200. That claim traces to a fan FAQ last updated in **2009**, and in
seventeen years no source has ever named which two sites they are.

A pull-through has road access at both ends. You will be able to see it. If you find
them, name them — and if they aren't there, that's the better story.
