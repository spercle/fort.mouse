# Fort Wilderness Campsite Reference

A queryable reference tool for the individual campsites at Disney's Fort Wilderness
Resort & Campground. It exists to answer questions about *one specific numbered
campsite* — questions that today's loop-level guides and photo galleries cannot answer.

## Language

**Site**:
A single numbered campsite at Fort Wilderness, e.g. Site 1412. This is the atomic
unit of the entire product — the thing records are keyed on and the thing users are
ultimately asking about.
_Avoid_: campsite, spot, pad, lot. Never use "site" to mean the website.

**Loop**:
The numbered road cluster that Sites belong to, e.g. Loop 1400. A first-class parent
of Site, not a category label — Loops have their own attributes and identity.
_Avoid_: neighborhood, section, area, street.

**Pad**:
The **poured concrete** within a Site. A component of a Site, never a synonym for it,
and routinely much shorter than the Site: site 101 is 45 ft of Site over a 24 ft Pad.
Say "concrete pad" wherever the two could be confused.
_Avoid_: using "pad" for the whole parking surface — that is the Site Length.

**Site Length**:
The usable length a rig has to fit into, concrete and apron together. This is the
figure Disney publishes per Category, the figure a guest compares against their rig,
and the headline measurement on a Site page. What gets traced from aerial imagery,
because the slab and the apron are not separable from above.
_Avoid_: pad length, pad size.

**The Guide**:
The product itself. Placeholder term until a name is settled. Chosen specifically so
that "site" is never ambiguous.
_Avoid_: the site, the website.

**Category**:
Disney's own classification of a Site, which is what you actually book: Tent/Pop-Up,
Full Hook-Up, Preferred, Premium, or Premium Meadow. A Loop is (mostly) uniform in
Category. Disney publishes one Site dimension per Category and nothing finer — and it is a
Site Length, not a Pad; the concrete inside it may be far shorter.
_Avoid_: tier, class, type, level.

**Loop Request**:
A guest's non-binding ask for a particular Loop, made by phone or fax roughly 1-2
weeks before arrival. This is the only lever a guest has over where they end up.
_Avoid_: booking, reservation, preference.

**Site Assignment**:
The cast member's allocation of a specific Site to a guest, made at check-in. Guests
book a Category and request a Loop; they are *assigned* a Site. The gap between
Loop Request and Site Assignment is the whole reason this project exists.
_Avoid_: booking, selection — nothing about it is chosen by the guest.

**Cabin**:
A built lodging unit at Fort Wilderness, distinct from a Site. Cabins occupy Loops
2200-2800, plus two anomalies (118 and 120) sitting inside campsite Loop 100.
**Cabins are out of scope** — they are in active refurbishment and their inventory is
changing, so any data collected now would rot. The Guide models them only insofar as
it must explain why 118 and 120 are missing from Loop 100.

**Provenance**:
Where a given fact about a Site came from, and how much it can be trusted. Not
metadata — a first-class part of every measured value, because the Guide's data will
be assembled from sources of very different quality.

**Back-in Difficulty**:
How hard a Site is to reverse a rig onto, expressed as a score **computed** from
approach side, approach road width, and the nearest obstruction to the pad opening.
Deliberately measured rather than rated by feel — this is the field where the Guide
most visibly differs from existing prose guides.
_Avoid_: rating, grumpiness, difficulty level.

**Occlusion**:
A pad being invisible in a given aerial capture — a rig parked on it, or canopy over it.
Roughly 60% of pads are occluded in any single capture, which makes it the binding
constraint on measurement, not image resolution. Defeated by comparing several capture
vintages, never by better imagery.

**Number Confidence**:
How sure we are that a given digitized pad is the Site number assigned to it. Loop
assignment is solid (public county address ranges); ordinal position within a Loop is
inferred from order along the road and is not. Published rather than hidden.
