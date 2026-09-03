# Fort Wilderness campsite data landscape

Research conducted 2026-09-02. Everything below is sourced; inferences are labeled.

## Headline

Nobody has a queryable per-site database. Nobody has site-level geodata. The raw
material — pad geometry — is visible in public aerial imagery and has never been
systematically digitized.

## 1. There is no authoritative per-site data from Disney

Disney publishes pad dimensions at the **category** level only:

| Category | Published pad size | Sewer |
|---|---|---|
| Tent or Pop-Up | 10' x 25' | no |
| Full Hook-Up | 10' x 50' | yes |
| Preferred | 10' x 45' | yes |
| Premium | 18' x 60' | yes |
| Premium Meadow | 18' x 60' | yes |

Not published anywhere: per-site length, per-site width, back-in vs pull-through,
per-site max RV length, per-site amperage, per-site orientation. No API, no feed.
`disneyworld.disney.go.com/robots.txt` disallows `/reservations/`.

## 2. THE CRITICAL FACT: you do not choose your site

**Site numbers are assigned at check-in.** The official guest map has a blank
`Cabin/Site ________` line printed on it for a cast member to fill in.

Guests can only **request a loop** — by phone (407-824-2900) or fax (407-824-3508),
typically ~1-2 weeks before arrival. Requests are not guaranteed.

This is the gap the entire hobbyist ecosystem exists to fill, and it means the
product's unit of *decision* (Loop) differs from its unit of *record* (Site).

## 3. What already exists

| Resource | Granularity | Queryable | Map | Notes |
|---|---|---|---|---|
| **wildernessprincess.net** | **Individual site** | No | Static PNGs | **The incumbent.** Width + length + back-in difficulty for loops 100-1300. Thins to photo captions for 1400-2100. Blocks bots (ModSecurity 406). |
| TouringPlans | Loop only | Interactive SVG | Yes | `rooms_present: false` — they have **no** per-site records. Asserts AI-licensing terms. Blocks bots (403). |
| Fort Fiends | Forum threads | No | No | **Currently offline** (Cloudflare 522). `fortwildernessguide.com` does not resolve. |
| DISboards photo thread | Individual site | No | No | Running since 2007, 52 pages. Asks for structured fields, never aggregates them. Unmined. |
| Campendium / The Dyrt / RV Life | Campground only | Campground level | Yes | Site numbers only incidental in review prose. |
| CampsitePhotos.com | **Empty stub** | - | Paywalled | "No photos yet." Zero coverage. Lists 847 sites. |
| "Fort Wilderness" iOS app | None | No | No | A **chatbot**, $4.99/wk or $49/yr, 0 ratings. Not a database. |
| YouTube | Loop-level drives | No | No | No site-by-site reference video exists. |

Searched and **absent**: no public spreadsheet/Airtable, no GitHub repo with FW data
(0 results), no published GeoJSON. One WDWMagic hobbyist built a private chart of
loops 100/200/300 from fan-site dimensions + satellite, and never published it.

## 4. Loops and numbering

28 loops, numbered by hundreds. **100-2100 are campsites (21 loops); 2200-2800 are
cabins (7 loops).** Sites number sequentially within a loop from `N01`.

| Loop | Street name | Category | Sites |
|---|---|---|---|
| 100 | Bay Tree Lane | Preferred | 27 |
| 200 | Palmetto Path | Preferred | 37 |
| 300 | Cypress Knee Circle | Preferred | 61 |
| 400 | Whispering Pine Way | Premium | 33 |
| 500 | Buffalo Bend | Premium | 56 |
| 600 | Sunny Sage Way | Premium Meadow | 37 |
| 700 | Cinnamon Fern Way | Premium | 34 |
| 800 | Jack Rabbit Run | Premium Meadow | 74 |
| 900 | Quail Trail | Premium Meadow | 32 |
| 1000 | Raccoon Lane | Premium Meadow | 23 |
| 1100 | Possum Path | Premium | 24 |
| 1200 | Dogwood Drive | Premium | 22 |
| 1300 | Tumbleweed Turn | Premium | 34 |
| 1400 | Little Bear Path & Big Bear Path | Premium Meadow | 61 |
| 1500 | Cottontail Curl | Tent/Pop-Up | 21 |
| 1600 | Timber Trail | Full Hook-Up | 45 |
| 1700 | Hickory Hollow | Full Hook-Up | 41 |
| 1800 | Conestoga Trail | Full Hook-Up | 32 |
| 1900 | Wagon Wheel Way | Full Hook-Up | 38 |
| 2000 | Spanish Moss Lane | Tent/Pop-Up | 69 |
| 2100 | Bobcat Bend | Full Hook-Up | 44 |

Loop names verified against OSM road data (29/29 exact match). Counts from
TouringPlans' embedded `buildings-data`.

### Edge cases that will bite the data model

- **Loop 100 contains two cabins** (118 and 120) interleaved among campsites.
  Confirmed independently by OSM and by wildernessprincess.net's gallery skipping them.
  So "loop 2200+ = cabins" is not a clean rule.
- **Loop 2100 was converted from cabins to campsites** ~2016. Stale sources still
  say cabins are 2100-2800.
- **Total site count is contested and no source is authoritative**: TouringPlans 845,
  CampsitePhotos 847, Campendium/AllEars/press 799, one widely-copied line says 788.
  *(Inference: ~845 likely counts every numbered pad; 799 is a legacy marketing number.)*
- **Loop 1400's category is contested** — Premium Meadow vs plain Premium depending
  on source. Premium Meadow was introduced as a category in January 2020.
- **Pull-throughs are unverified.** "Two pull-throughs in the 1200 loop" traces to a
  2009 FAQ and has been repeated ever since. **No source names those two site numbers.**

### Recent changes

- Cabins → DVC prefabs, phased July 2024 through ~April 2025.
- **Max guests per campsite cut 10 → 8**, effective for arrivals from Jan 1, 2026.
- **Loop 700 closed Aug 31 - late Sept 2026** for utility work (i.e. right now).
- Meadow Swimmin' Pool expansion under construction, targeted mid-2026.
- Disney Lakeshore Lodge (DVC) on the former River Country site, opening July 1, 2027.
  No evidence of campsite loops being permanently removed for it.

## 5. Geodata

**Available free today:** all 29 loop roads mapped as named ways in OSM, plus 163
building footprints and named POIs (Pioneer Hall, both Trading Posts, Bike Barn,
Tri-Circle-D Ranch, comfort stations). Campground is `way/805831512`.

**The gap:** only **25 `tourism=camp_pitch` objects exist in the whole campground**,
all in Loop 100, and only 6 carry a real site number. Against ~845 sites that is
**~0.7% coverage**.

**Tainted:** 20 of those 25 pitches carry
`source=https://i0.wp.com/wildernessprincess.net/.../loop100map.png` — someone traced
them off the incumbent's copyrighted map and abandoned the effort after one loop.
*(Inference: that is a licensing problem for OSM, and means even the tiny existing
pitch data is derivative rather than independent.)*

**No georeferenced official map exists.** The Disney PDF is a raster illustration —
`pdftotext` returns zero characters, no coordinate system, no site numbers.

## 6. Rights and risk

Disney owns the FORT WILDERNESS mark. (USPTO/TMview/Justia were all blocked during
research, so the specific registration is unverified; ownership is not in doubt.)

**The observed pattern every fan site follows:** nominative use of the name for
editorial reference + a prominent unaffiliated/unendorsed disclaimer + no Disney
logos or marks in branding. Verbatim from wildernessprincess.net: *"This site is
unofficial and not authorized by any organizations written about in it."*

**Content licensing is the more concrete risk than trademark:**

1. The official map is `©Disney FW2001/11120555 0314`. Reproducing or tracing it is a
   copyright question. OSM loop geometry is the clean alternative.
2. **wildernessprincess.net's photos and measurements are her original work.**
   Scraping to seed a database is the single most likely source of an actual
   complaint — and the OSM trace above shows the ecosystem has already done it once.
3. TouringPlans asserts AI-licensing terms on every page; treat their loop polygons
   as off-limits absent reading those terms.
4. Both sites actively block automated fetching. Scraping them is technically
   adversarial, not merely a rights question.
5. Avoid Disney fonts, the FW logo lockup, Mickey silhouettes, any styling implying
   endorsement.

*(Inference: Disney historically tolerates editorial fan sites — wdwmagic, DISboards,
AllEars and TouringPlans have run 20+ years — and enforces against merchandise and
impersonation. A free, disclaimered, editorial reference with independently sourced
data sits inside the tolerated zone. A paid product using Disney artwork does not.)*
