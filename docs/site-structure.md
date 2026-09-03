# Site structure

## URLs

```
/                    the 21 campsite Loops, compared
/loop/1200           the Sites in that Loop, filterable
/site/1204           the verdict page for one Site
[ 1204 ] in header   jumps to any Site from anywhere
```

Home is **Loops**, not Sites, because before arrival the Loop Request is the only lever
a guest has. Site pages are built **first** — they are the atoms everything aggregates
from, and one URL per Site is a structural advantage no existing resource has.

## Site page anatomy — verdict first

The page answers the question before it shows its work.

**1. Verdict line.** The whole point of the page, readable in two seconds on a phone at
the check-in desk:

> **Site 1204** · Loop 1200 Dogwood Drive · Premium
> 48 ft measured · 12 ft wide · back-in from the right · moderate · 40% canopy · backs onto woods

Where a value is unmeasured it **says so out loud** rather than being omitted:

> Length unmeasured — Disney lists this category at up to 60 ft

**2. Evidence table.** Every value with its `source` and `as_of`. The verdict is the
claim; this is the proof.

**3. Photos.** First-party only. Absent for most Sites for a long time, and that is fine.

**4. Notes.** Human writing, from `data/sites/NNNN.md`. Usually empty.

**5. Loop context.** Previous/next Site, link back to the Loop.

**6. Correction link.** A `mailto:` pre-filled with the Site number and a short template,
so an email arrives with structure already in it.

## Why not the alternatives

**Data table first** is more honest but unreadable on a phone, and it makes 845 pages
that each require a reading session.

**Photo led** is what the incumbent does, and it is precisely why her site cannot answer
questions — comparing 40 sites means looking at 40 pictures.

Having a table is **not** the differentiator; the incumbent already has one, with columns
`Site Number | Photo | Width | Length | Back In Pain Scale | Notes`. The differentiators
are **one URL per Site**, **queryable**, and **measured rather than felt**. The verdict
line is what makes a per-Site URL worth existing.
