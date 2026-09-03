---
status: accepted
date: 2026-09-02
supersedes: ADR-0001
---

# Measurements may be seeded from published sources, with attribution, then verified

[ADR-0001](0001-independent-data-sourcing.md) required every value to be independently
sourced. That is reversed here for **measurements only**: an existing published figure may
seed a Site, carrying its source, and is replaced as the project's own measurement or a
guest's first-hand report verifies it.

A seeded dataset that is honest about being seeded, and visibly converges on
independence, is more useful than an empty one that is pure. The alternative was a site
that showed `unmeasured` for years.

## Why the reversal is defensible

**A pad length is a fact, and facts are not copyrightable** — *Feist Publications v. Rural
Telephone Service*, 499 U.S. 340 (1991). Copyright can protect the selection and
arrangement of a compilation, not the individual measurements inside it. Reproducing a
number is materially different from reproducing the prose, the ratings, or the photographs
around it.

This does not make attribution optional. Every seeded value records where it came from,
and the source is shown on the page.

## What is still excluded, and why

**Photographs.** A photograph is a creative work with full copyright, not a fact. No
image from another guide is copied, ever. Site pages get their imagery from:

1. **County orthoimagery crops** — `pipeline/thumbnails.py`, one per Site, from the
   Orange County public record under ADR-0003. Free, automatic, and unique to this project.
2. **Our own photographs** from site visits.
3. **Guest submissions**, where sending a photo grants permission to publish it.

**Prose, ratings and subjective judgments.** The incumbent's back-in difficulty scale and
her per-site notes are her editorial work, not facts. We compute our own difficulty score
from geometry instead — see the glossary entry for Back-in Difficulty.

## Consequences

- **`source` becomes load-bearing.** Every measured value carries one of
  `aerial` · `observed` · `reported` · `disney-category` · `county-record` · `seeded`.
  A `seeded` value is visibly second-class in the UI and is what verification replaces.
- **`verified_by` and `verified_date`** record who confirmed a seeded value and when.
- **Convergence is a published metric.** The share of values still `seeded` is shown, so
  the project's progress toward independence is visible rather than claimed.
- **Attribution is permanent.** A value seeded from another guide credits that guide until
  it is replaced, and the credit is removed only when the value is.
- **This ADR does not authorise scraping.** How a seed value is obtained is a separate
  question from whether it may be used. The incumbent's server blocks automated access and
  does not serve a readable `robots.txt`, so seeds are transcribed by hand or obtained with
  the author's agreement.
