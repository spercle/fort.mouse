# Site data model — DRAFT

Status: proposed, not agreed. Every field lists where it comes from and what it costs.

## Principle: machine data and human data have different lifecycles

Derived fields get **recomputed wholesale** when the method improves. Human notes and
photos must **never** be clobbered by a recompute. So they live in different files.

## Principle: every measured value carries provenance

A number without a source is a liability. Each measured field carries:

- `value`
- `source` — `disney-category` | `aerial` | `county-record` | `observed` | `reported`
- `as_of` — date the value was established
- `imagery_vintage` — for aerial values, which capture it was measured from

Three distinct absent-states, and the difference matters:

| State | Meaning |
|---|---|
| `unmeasured` | Nobody has looked yet |
| `occluded` | Looked, in every available vintage, and the pad could not be seen |
| `unknown` | Not knowable from any source we have |

`occluded` is honest in a way `unmeasured` is not — it tells a reader the gap will not
close just by waiting. None of the three is ever silently omitted.

---

## Identity — free, exact, day one

| Field | Source | Notes |
|---|---|---|
| `site_number` | Disney map + observation | e.g. 1412. Primary key. |
| `loop` | Disney map | 100-2100 for campsites |
| `loop_name` | **OSM** | Verified 29/29 against road ways |
| `category` | Disney published | Preferred, Premium, Premium Meadow, Full Hook-Up, Tent/Pop-Up |

## Category baseline — free, Disney's own published numbers, all 845 sites on day one

These are Disney's five published specs. They are **not** per-site measurements — they
are the category's stated maximum. Recording them with `source: disney-category` gives
a complete, populated, defensible dataset immediately, which real measurements later
override site by site.

| Field | Source |
|---|---|
| `category_pad_length_ft` | Disney rates page (25 / 45 / 50 / 60 by category) |
| `category_pad_width_ft` | Disney rates page (10 or 18 by category) |
| `sewer` | Disney — true for all but Tent/Pop-Up |
| `max_occupancy` | Disney — 8, effective for arrivals from 2026-01-01 |

## Measured from aerial imagery — the moat

Nobody has done this systematically. It scales to all 845 sites without a site visit,
and it is independently sourced.

| Field | Why it matters |
|---|---|
| `pad_length_ft`, `pad_width_ft` | The actual question a big rig owner is asking |
| `pad_orientation_deg` | Compass bearing of the pad's long axis — this is what actually determines afternoon sun |
| `pad_surface` | Concrete vs gravel, visible from above |
| `approach_side` | Back-in from the left or the right |
| `approach_road_width_ft` | Objective input to back-in difficulty |
| `approach_obstruction` | Nearest tree/post/hydrant to the pad opening |
| `canopy_coverage_pct` | The shade question, measured instead of guessed |
| `backs_onto` | water / woods / road / another site / comfort station / open — the privacy question |

**Back-in difficulty becomes a computed score** from approach side, road width, and
obstruction — objective and reproducible, rather than a subjective rating.

## DEFERRED — computed from OSM routing

| Field |
|---|
| `walk_m_to_comfort_station` |
| `walk_m_to_bus_stop` |
| `walk_m_to_pool` |
| `walk_m_to_trading_post` |

OSM has all 29 loop roads plus named POIs (Pioneer Hall, both Trading Posts, Bike Barn,
comfort stations), so these are a routing calculation, not fieldwork.

**Cut from v1.** These are a pure computation over data we already have, so deferring
them forecloses nothing — once Sites are georeferenced, distances fall out for free.
Revisit once a loop is measured end to end.

## Human-observed — from your visits and from email

The expensive layer. Sparse forever, and that is fine.

| Field |
|---|
| `levelness` |
| `noise_notes` — generator, road, boat horn, Electrical Water Pageant |
| `privacy_notes` |
| `photos[]` — with date and permission-to-publish recorded |
| `notes` — free text |
| `number_confidence` — how sure we are this pad **is** the Site number assigned to it |

---

## Storage shape — proposed

```
data/
  loops/
    1400.yaml          <- machine-owned: all sites in loop 1400, derived fields
  sites/
    1412.md            <- human-owned: frontmatter + prose notes + photo refs
```

- **Per-loop data files** keep diffs readable and files small, and Loop is a natural
  unit. 21 files instead of 845.
- **Per-site Markdown** exists only for sites that have human content. Most will not,
  at first. Absence is normal.
- A recompute rewrites `data/loops/*.yaml` and touches nothing in `data/sites/`.
- No database. Plain files in git means full history, reviewable diffs, and the
  dataset survives the project.

## Search

845 records is tiny. Build a JSON index at build time, ship it to the browser, search
entirely client-side. No server, no service, instant. This also powers the
type-a-site-number box.

---

## Photo policy

**A photo on a Site page must depict that Site and must be first-party** — taken by us,
or sent by a guest who stayed there and granted permission. No exceptions. The Guide's
only claim is that its data is measured rather than repeated; a stock image on a Site
page silently contradicts it.

**Free-to-use imagery is decoration only** — home page, about page, category
illustrations. Never on a Site page. Prefer CC0 / public domain: `BY` needs attribution,
`SA` infects derivatives, and `NC` becomes a problem if the project ever carries
affiliate links.

Every photo record carries `credit`, `date`, and `license`.

## Deploy shape

Self-hosted. The build runs locally and produces static files; the server needs no
runtime, no Node, and no database. Deploy is a copy of `dist/` — which means the server
cannot break the site, and the site cannot break the server.
