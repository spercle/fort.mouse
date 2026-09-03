# Draft: permission request to The Wilderness Princess

Send from your own address. Short, specific, and easy to say yes to — you are asking for
one thing, offering credit, and making clear you'll take no for an answer.

---

**Subject:** Asking permission — measured campsite data for Fort Wilderness

Hi,

I'm a Fort Wilderness camper building a small free reference site for individual
campsites — the thing I always wanted when I got handed a site number at check-in and
had no idea what I'd got.

Your loop and site pages have been the resource I've relied on for years, and I don't
want to build anything that quietly takes from that work. So I'm asking rather than
assuming.

Two things, and a no on either is genuinely fine:

1. **Your width and length figures** as a starting point, credited to you on every site
   that uses them, and replaced as I measure each pad myself. Every page would say the
   number is yours until it isn't.

2. **Your site photos**, credited and linked back to you. I've been generating aerial
   crops from Orange County's public orthoimagery instead, which works but obviously
   doesn't show what a site actually feels like from the ground.

What I'm building is deliberately different from what you have rather than a
replacement: measured pad dimensions from aerial imagery, filterable, one page per site
number. It can't do the thing your site does best — nobody's pipeline is going to write
"don't have to sit with laundry."

Happy to link prominently to you either way, and happy to show you what I've got before
anything goes public.

Thanks for all of it,
Steven

---

## If she says yes

- Record the grant in `docs/outreach/` with the date and exactly what was permitted.
- Photos go in with visible credit and a link on every page that uses one.
- Measurements go through `pipeline/seed_measurements.py --credit "..."` as already built.
- Add an ADR recording the permission, so a future contributor knows the images are
  licensed rather than taken.

## If she says no, or does not reply

Nothing changes. The county aerials already give every site and every loop an image, the
measurements come from digitizing, and guest submissions fill in the ground-level view.
