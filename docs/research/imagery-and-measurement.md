# Imagery, licensing and measurement method

Research conducted 2026-09-02. Campground centroid ~28.4035 N, -81.5568 W.
Orange County parcel 272412000000005.

## Headline

3-inch imagery exists, is free, and is legally clean from two independent directions.
**Resolution was never the problem. Occlusion is.**

## 1. The imagery — Orange County 2024, 3 inch (0.0762 m) GSD

Verified via the Esri World Imagery metadata layer:

```
SOURCE_INFO   : "Orange County2024"
SOURCE        : "State of Florida"
DATE          : 2024-04-26
RESOLUTION    : 0.0762 m  = exactly 3.00 inches
ACCURACY      : 0.11 m    = 0.36 ft horizontal
```

**Access, verified working, no auth:**

| Route | Effective GSD here |
|---|---|
| **Esri World Imagery XYZ**, `.../World_Imagery/MapServer/tile/{z}/{y}/{x}` | **z=21 → 2.58 in/px** |
| OCPA tile cache `vgispublic.ocpafl.org/.../OCPA/Aerials2024/MapServer` | 6.25 in (LOD 10; LOD 11 404s here) |
| Orange County gov `ocgis4.ocfl.net/.../Public_Aerial_Base` | 10.4 in — too coarse |

Esri's basemap serves the county's full 3-inch product; the county's own public cache
does not. Available OCPA vintages: **2006, 2022, 2024, 2025**.

## 2. Does it resolve a pad? Yes, with margin

Pad width 10-18 ft. Digitizing a concrete/grass edge localizes to ~±1 px; two edges
give ±1.4 px.

| Source | GSD | px across 10 ft | Width error | Meets ±1 ft? |
|---|---|---|---|---|
| **OC 2024 via Esri z21** | 3 in | **40.0** | **±0.35 ft** | yes, comfortably |
| OCPA cache / FCDOP standard | 6 in | 20.0 | ±0.7 ft | yes, no margin |
| NAIP 2023 | 30 cm | 10.2 | ±1.4 ft | **no** |
| 3DEP DEM | 1 m | 3.05 | ±4.6 ft | no |
| Sentinel-2 | 10 m | 0.30 | — | absurd |

## 3. THE ACTUAL CONSTRAINT: occlusion

Rendering live loops at 28.4117 / -81.5601 shows the real obstacle:

- **RVs are parked on the pads.** In the 2024 capture most Loop 100 sites have a rig
  sitting on the concrete. The pad is not visible at all.
- **The canopy is dense.** Mature pine and oak over a large fraction of pads.
- Estimated **~40% clean / ~60% difficult**.

**Mitigation, and it works:** the 2022 / 2024 / 2025 captures show *different* vehicles
at different sites. Stacking three OCPA vintages plus NAIP 2023 gives **four independent
chances per pad** to catch it empty. This is the single most important workflow decision
in the project.

Consequence for the data model: `occluded` (looked, could not see) must be a distinct
state from `unmeasured` (have not looked yet).

### Verified against Loop 1200, 2026-09-02

Pulled a 180 ft window over Dogwood Drive from all four sources and compared:

- **The stacking strategy works.** A site occupied in both 2022 and 2024 is clean, empty
  concrete in 2025.
- **The vintages are not equal.** 2025 and 2022 are sharp; **2024 is noticeably soft**
  through the export endpoint; NAIP at 30 cm is visibly blurry and fit only for checking
  whether something is parked there.
- **Rigs move between captures; trees do not.** Vintage stacking defeats rig occlusion —
  which is most of the problem — but a pad under a mature oak is under it in all four
  captures, and Florida pines are evergreen so there is no leaf-off window to wait for.
  **Canopy occlusion is the true residual and resolves only on foot.**

## 4. Licensing — clean from two directions

**Esri World Imagery explicitly permits it.** From *"World Imagery Map — Data Collection
and Editing Uses Permitted"* (ArcGIS item `8e90a00a0a6845a49262e0b756f57a10`), clause 3,
verbatim:

> "Esri and its imagery contributors grant Users the non-exclusive right to use the World
> Imagery map to trace features and validate edits in the creation of vector data. Users
> that create vector data from the World Imagery map can publicly share that vector data
> through a **GIS data clearinghouse of their own** or through another open data site."

*(Inference: clauses 1-2 frame this around Esri clients, and clause 3 says "building on
the use cases above." A conservative reading does the tracing in an Esri client. A free
ArcGIS public account satisfies that cheaply if belt-and-braces is wanted.)*

**And the pixels are a Florida public record.** *Microdecisions, Inc. v. Skinner*, 889
So. 2d 871 (Fla. 2d DCA 2004): a county **Property Appraiser** tried to license GIS maps;
the court held he "has no authority to assert copyright protection in the GIS maps, which
are public records." The FCDOP standards state "All final data will be considered public
record." OCPA's site notice asserts copyright but contains only accuracy disclaimers, no
derivative-works restriction — and under *Microdecisions* that assertion is unenforceable.

**Residual risk:** proving the 2024 raster is county-produced rather than EagleView-
licensed (OCPA separately licenses EagleView "Reveal"). Mitigate with a Chapter 119
request to `GIS@ocfl.net` for the 2024 orthoimagery and its metadata.

### Explicitly ruled out

| Source | Status |
|---|---|
| **Google Maps / Earth / Street View** | **Prohibited.** ToS bars "use Google Maps to create or augment any other mapping-related dataset"; Geo Guidelines bar "digitizing or tracing information from the imagery." No exception. Do not use for anything. |
| Bing / Microsoft | Tracing grant is **OSM-only** and does not transfer to your own dataset. |
| Mapbox Satellite | Non-commercial derivation only; commercial needs a Satellite license. Not worth the ambiguity. |
| Nearmap | $5,200/yr smallest published tier. No hobbyist option. |
| Vexcel / EagleView | Quote-only; same resolution as the free county ortho. |

## 5. Georeferencing — the good find

**Orange County's public address data**, `ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer`:

**Layer 0 — Address Points.** 415 individually addressed units, each with lat/lon, where
the address number **is** the Disney unit number: Bobcat Bend 2100-2144, Arrowhead Way
2200-2244, Shawnee Bend 2300-2340, Settlers Bend 2400-2457, Cedar Cir 2501-2533, Moccasin
Trl 2600-2667, Heron Hollow 2700-2772, Willow Way 2800-2870. **These are the cabins** —
which we scoped out. Campsite loops get one address point per loop, not per site.

**Layer 1 — Address Ranges.** Road segments with number ranges. This
**independently reproduces the whole loop-number-to-loop-name mapping from a public record
rather than a fan map** — exactly the independence ADR-0001 requires. It also subdivides
each loop into 2-5 segments with sub-ranges, e.g. Cottontail Curl: `1400-1410` (49 ft),
`1412-1450` (411 ft), `1452-1500` (442 ft). So a site localizes to a specific road segment
with known geometry, and its ordinal position within that segment is constrained.

Caveats: `ACTUAL_MIN/MAX` are all 0 — only *theoretical* ranges are populated, and the
county's even-left/odd-right parity is **not** Disney's convention. Some inconsistencies
(Cottontail Curl encoded 1400-1500; Tumbleweed Turn and Wagon Wheel Way overlap neighbours).

**OSM confirmed unusable:** 25 pitches, 6 numbered, and 19 carry
`source=...wildernessprincess.net/.../loop100map.png`. Using it imports exactly the
provenance problem ADR-0001 exists to avoid.

**Street View:** coverage inside the campground unverified (Google's probe endpoint now
400s). Legally unusable as a source regardless. Mapillary/KartaView coverage unverified —
worth five minutes in a browser, since Mapillary is CC-BY-SA and site-number posts would
be legitimately readable from it.

### Honest assessment

- **Cabins: solved** by spatial join. (Out of scope anyway.)
- **Campsite loop assignment: solved** from the county address ranges.
- **Ordinal position within a loop: not solved.** Ordering digitized pads along the road
  centerline and assigning sequentially will be mostly right, with errors at segment
  boundaries, skipped numbers, and both-sides-of-road ambiguity.
- **Residual ~100-300 sites need hand verification** from on-site photos of the numbered
  posts. Publish a `number_confidence` field rather than pretending.

## 6. Tooling

- **CRS: EPSG:2236** (NAD83 / Florida East, ftUS) so measurements come out in feet natively.
- **Digitize:** QGIS Shape Digitizing → *Rectangle from 3 points (projected)*. Click both
  ends of the pad's long edge (sets length and bearing), then a third point for width.
- **Derive:** `native:orientedminimumbbox` gives width, height, angle, area in one pass.
  `main_angle($geometry)` returns the long axis **clockwise in degrees from North** — the
  compass orientation directly, no conversion. *(Known bugs QGIS #41022, #36632 — spot-check.)*
- **Nearest obstruction:** `native:joinbynearest` for distance plus `azimuth()` for bearing.
- **Canopy:** PDAL `filters.hag_nn` on the free 3DEP QL1 tile (0.35 m pulse spacing,
  verified 200 OK) → threshold `HeightAboveGround[2:]` → 0.5 m binary raster →
  `native:zonalstatisticsfb`; the MEAN of a 0/1 raster is fractional cover.
  **Lidar is 2018** — predates Ian (2022) and Milton (2024). Record the vintage.
  NAIP NDVI is the currency alternative but cannot separate canopy from turfgrass.
- **SAM assist:** Geo-SAM or samgeo give one-click-per-pad segmentation. Useful as an
  accelerator; fully automatic extraction of 845 correctly-separated pads is **not** solved
  — SAM merges pad, apron and road, or splits a shadowed pad in two.

## 7. Effort

| | |
|---|---|
| Clean, unoccluded pad | 15-30 s |
| Occluded pad (toggle 4 vintages, reason from apron and rig footprint) | 1-3 min |
| Blended average at ~40/60 split | **~76 s/pad** |
| **All 845 sites, pure digitizing** | **~18 hours** |
| **Realistic total** with QA, orientation spot-checks, canopy pipeline, numbering | **30-50 hours** |
| **Loop 1200, 22 sites** | **~28 minutes of digitizing** |

## Two things to do first

1. **File a Chapter 119 request** to `GIS@ocfl.net` for the 2024 orthoimagery and its
   metadata — pins down county-produced vs EagleView-licensed, and gets raw GeoTIFFs at
   full 3 inch rather than through a tile cache.
2. **Pull layers 0 and 1** from `ocgis4.ocfl.net/.../AGOL_Open_Data/MapServer` now. They
   hand you the loop name-to-number mapping from a public record instead of a fan map.
