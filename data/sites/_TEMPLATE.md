---
# Copy this to <site number>.md — 101.md, 1420.md — and delete what you don't have.
# Files starting with _ are ignored, so this one never becomes a page.
#
# Everything here is optional except `site`. A site with no file simply shows what
# the aerial pass knows about it.

site: 1234
loop: 1200          # optional; checked against the roster, so a typo is caught

# ---- measured on the ground ----------------------------------------------------
# The SITE is what a rig has to fit into, concrete and apron together — this is the
# figure Disney publishes. The PAD is the poured concrete inside it, often much
# shorter: site 101 is 45 ft of site over a 24 ft slab. See ADR-0005.

site_length_ft: 45
site_width_ft: 10
pad_length_ft: 24
pad_width_ft: 10
pad_surface: concrete
backs_onto: woods           # free text — woods, water, road, comfort station...
approach_side: driver       # which side you back in from
pad_orientation_deg: 42
road_offset_ft: 18
measured: 2026-01-14        # optional; leave it out rather than guessing

# ---- the site number, confirmed from a photograph -------------------------------
# Only with real evidence. Everything else in this project's numbering is inferred
# from sequence, and saying otherwise would be the one lie that matters.

verified:
  evidence: /photos/1234-1.jpg   # must exist under static/
  kind: post                     # post | sign
  note: The numbered post is legible, reading 1234.
  date: 2026-01-14
---

Anything below the fence is markdown, and shows up as **Notes** on the site page.
Shade, noise, how level the ground is, where the hook-ups actually are — the things
no aerial photograph can tell you.
