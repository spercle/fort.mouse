# 5. Site length and concrete pad are different measurements

Date: 2026-09-03

## Status

Accepted. Refines the Pad definition in `CONTEXT.md`.

## Context

Site 101 was measured on the ground: the concrete slab is 24 ft long. Disney lists
Preferred at 45 ft, so the figure looked like a discrepancy worth flagging.

It was not a discrepancy. The site really is 45 ft; only the poured concrete is 24 ft.
The rest is apron — usable ground a rig can occupy, but not slab.

Until now the project had one pair of fields, `pad_length_ft` and `pad_width_ft`, doing
both jobs at once:

- `category_baseline.pad_length_ft: 45` held Disney's published figure, which is a
  **site** dimension.
- `derive.py` was going to write the traced hardstand into the same field, which is
  also a **site** dimension.
- `observe.py` wrote a tape-measure reading of the **concrete** into it too.

So a site page compared 24 ft of slab against 45 ft of site and presented the gap as
if this pad were half the size of its category. That is wrong in the direction that
matters: it would tell someone with a 40 ft rig to avoid a site that fits them.

## Decision

Two distinct measurements, both first-class:

- **`site_length_ft` / `site_width_ft`** — the usable site, concrete and apron
  together. Disney's published category figure, the headline number on a site page,
  the basis for loop medians, and what a guest compares against their rig.
- **`pad_length_ft` / `pad_width_ft`** — the poured concrete only.

`category_baseline` is renamed to the `site_*` keys, because that is what Disney
publishes. All 21 loop files are migrated; no pad has been digitized yet, so no
existing measurement had to be reinterpreted.

Aerial tracing produces **site** dimensions. At county orthoimagery resolution the
slab and the apron read as one surface, and pretending otherwise would invent a
precision the imagery does not have. `derive.py` says so at the point of measurement.

Validation bounds are split accordingly: a site length below 15 ft is a digitizing
error, but a 6 ft concrete pad is merely a small one.

## Consequences

The distinction has to be maintained by whoever measures. `observe.py` takes
`--site-length` and `--pad-length` as separate flags with no default mapping between
them, so recording one as the other requires typing the wrong flag rather than merely
being imprecise.

Where both are known and the pad is shorter, the site page says which number to use
for what — the slab matters for levelling and setup, the site length for whether the
rig fits at all.

The category-ceiling check in `observe.py` now compares only site lengths against the
published figure. A short slab inside a full-length site is normal and no longer
triggers a warning.

Most sites will have a site length long before they have a pad length: one comes from
tracing imagery, the other only from someone standing on the concrete.
