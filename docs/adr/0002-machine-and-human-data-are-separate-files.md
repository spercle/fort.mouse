---
status: accepted
date: 2026-09-02
---

# Machine-owned data and human-owned notes live in separate files

Derived Site data lives in per-Loop files (`data/loops/1200.yaml`), owned by the
measurement pipeline. Human writing — notes, photo references, anything observed on a
visit or sent in by email — lives in per-Site Markdown (`data/sites/1204.md`) and is
never touched by the pipeline.

## Why

The two have opposite lifecycles. Derived fields are **regenerated wholesale** every
time the aerial-measurement method improves, which will happen often and early. Human
notes are **written once, by hand, and are irreplaceable** — nobody remembers the exact
wording of a note about site 1204 well enough to retype it.

A single file per Site forces every recompute to merge into 845 files while carefully
preserving hand-written fields. That merge is the kind of code that works for a year and
then eats a paragraph. Splitting the files makes the destructive case impossible rather
than merely unlikely: the pipeline has no write access to anything a human authored.

## Considered and rejected

**One file per Site, machine and human fields side by side.** This is the obvious shape,
which is exactly why this ADR exists — without it, someone will eventually consolidate
the two and think they are tidying up. Rejected because it makes a data-loss bug possible
in the most-run code path in the project.

**Per-Site machine files instead of per-Loop.** Rejected for ergonomics: 845 files whose
diffs are all touched by every recompute, versus 21 readable ones.

## Consequences

- The build joins the two sources by `site_number`. A Site with no Markdown file is
  normal, not an error — most Sites will have none for a long time.
- Human notes can reference a measured value but must never restate one. If a note says
  "52 feet" it will go stale silently the next time the pad is remeasured.
- `data/loops/*.yaml` is safe to delete and regenerate at any time. `data/sites/*.md` is
  not, and should be treated as the irreplaceable half of the repository.

## Implementation

`data/sites/<number>.md` — one file per site, YAML frontmatter for facts and a markdown
body for prose. Added 2026-09-03, having been specified here and referenced by three
generators for some time without existing. It absorbed the interim `data/observed.yaml`
and `data/verified.yaml`, which had scattered facts about a single site across two
shared list files plus a notes file that nothing read.

`pipeline/site_files.py` is the only reader. Unknown keys, unknown sites, a `loop:` that
contradicts the roster, and a `verified:` block with no evidence all fail the build
rather than being ignored — a typo that silently did nothing would be worse than a
crash, because you would believe a measurement had been recorded.
