---
status: superseded by ADR-0004
date: 2026-09-02
---

# All Site data is independently sourced

Disney publishes campsite specs only at the Category level — five pad dimensions for
~845 Sites — and assigns the actual Site number at check-in. The only per-Site dataset
that exists is wildernessprincess.net's: width, length and a back-in difficulty rating
for Loops 100-1300, gathered by hand over years by one person, served from a host that
actively blocks automated fetching.

**We do not use it.** *(Superseded — see [ADR-0004](0004-seed-then-verify-sourcing.md). Measurements may now be seeded with attribution; the photo exclusion survives.)* Every value in this project comes from Disney's own published
Category specs, OpenStreetMap, public aerial imagery, our own site visits, or guests
describing their own stay by email.

## Why this is worth an ADR

It is the one decision here that cannot be undone. Every other choice — storage format,
page structure, hosting, even the name — can be reversed on a wet afternoon. A dataset
seeded from someone else's measurements is derived from them permanently; there is no
later point at which it becomes independent. The cost of getting this wrong is paid
years from now, when the project is worth defending.

There is precedent for the mistake: 20 of the 25 campsite pitches that exist in
OpenStreetMap were traced from her loop map and carry it as their `source` tag. The
tracer abandoned the effort after one loop and left a licensing problem behind.

## Considered and rejected

**Seed from published fan-site tables, then correct on our own visits.** Rejected. It
gets the database populated in an afternoon, and the entire dataset is derivative from
that afternoon onward regardless of how much is later overwritten. It is also simply
unkind to the one person who did this work before us.

## Consequences

- **Real measurements arrive slowly.** An aerial-measurement pipeline has to be built
  before per-Site dimensions exist at scale. This is the project's main technical risk.
- **Disney's Category specs are the day-one baseline.** They populate all ~845 Sites
  immediately, and must always be labeled `source: disney-category` so nobody mistakes a
  category maximum for a measurement of their Site. This is why Provenance is a
  first-class field rather than metadata — see ADR on the data model when written.
- **The gap becomes the differentiator.** Loops 1400-2100 are where the incumbent's data
  thins to photo captions. Independent sourcing means we have no reason to start at
  Loop 100 and every reason to start where the map is blank.
- **Contributions must be first-hand.** Guests may describe Sites they stayed on. A
  submission that transcribes another site's table is declined.
