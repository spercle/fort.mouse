---
status: accepted
date: 2026-09-02
---

# Pad measurements come from Orange County 3-inch orthoimagery, via Esri World Imagery

All pad geometry is digitized from the **Orange County 2024 orthoimagery** (3.00 in /
0.0762 m GSD, 0.11 m horizontal accuracy), consumed through the **Esri World Imagery**
XYZ service, which serves the county product at z=21 (~2.58 in/px) over Fort Wilderness.
The OCPA 2022 and 2025 vintages and the 2023 NAIP tile are loaded alongside as alternates.

**Google imagery is not used for anything in this project.**

## Why this is worth an ADR

The obvious tool is Google Earth. It is free, everyone has it, and its imagery here is
excellent. **Its terms of service specifically prohibit exactly this use** — "use Google
Maps to create or augment any other mapping-related dataset," and the Geo Guidelines bar
"digitizing or tracing information from the imagery." Without this record, the single most
likely well-meaning contribution to this project is someone measuring pads in Google Earth
and destroying the provenance of the dataset in the process.

## The legal basis, which is deliberately doubled

1. **Esri grants it explicitly.** *World Imagery Map — Data Collection and Editing Uses
   Permitted*, clause 3: users may "trace features… in the creation of vector data" and
   "publicly share that vector data through a GIS data clearinghouse of their own."
2. **The underlying pixels are a Florida public record.** *Microdecisions, Inc. v.
   Skinner*, 889 So. 2d 871 (Fla. 2d DCA 2004) held that a county Property Appraiser "has
   no authority to assert copyright protection in the GIS maps, which are public records."

Either basis alone would do. Both together mean the project does not depend on one
permission continuing to hold.

## Rejected

| | |
|---|---|
| **Google Maps / Earth / Street View** | Prohibited by ToS for this exact use. Not a close call. |
| **Bing** | Its tracing grant is scoped solely to OpenStreetMap and does not transfer. |
| **Mapbox Satellite** | Non-commercial derivation only, and no resolution advantage here. |
| **NAIP alone** | Public domain and tempting, but 30 cm gives ±1.4 ft on pad width — it **fails** the ±1 ft target. Useful only as a fourth vintage for occlusion checking. |
| **Nearmap / Vexcel / EagleView** | $5,200/yr at the smallest published tier, or quote-only, for imagery no better than the free county product. |

## Consequences

- **Occlusion, not resolution, is the binding constraint.** RVs are parked on pads and the
  canopy is dense; roughly 60% of pads are difficult in any single capture. The four-vintage
  stack exists specifically to defeat this, and it is why alternate vintages are part of the
  method rather than a nicety.
- A conservative reading of the Esri grant does the tracing in an Esri client rather than
  QGIS. A free ArcGIS public account satisfies it if we ever want belt-and-braces.
- One open question to close: whether the 2024 raster is county-produced or EagleView-
  licensed. A Chapter 119 request to `GIS@ocfl.net` settles it and also yields raw GeoTIFFs
  at full 3 inch instead of a tile cache.
