"""Build the Loop 1200 digitizing project. Paste into QGIS's Python Console.

    QGIS ▸ Plugins ▸ Python Console ▸ (Show Editor) ▸ open this file ▸ Run

Sets the CRS to feet, loads the four imagery vintages in the order the imagery
actually supports, loads the county and OSM reference layers, creates the pad layer
with the exact schema derive.py expects, and zooms to the loop.

Safe to re-run — it removes anything it previously added rather than duplicating.
"""

import os
from urllib.parse import quote

from qgis.core import (
    QgsProject, QgsRasterLayer, QgsVectorLayer, QgsCoordinateReferenceSystem,
    QgsCoordinateTransform, QgsRectangle, QgsField, QgsVectorFileWriter,
    QgsFields,
)

# QGIS 4 moved field types to QMetaType and geometry types onto Qgis.WkbType.
# QGIS 3.x wants QVariant and QgsWkbTypes. Support both rather than pinning.
try:
    from qgis.PyQt.QtCore import QMetaType
    TYPE_INT, TYPE_STR = QMetaType.Type.Int, QMetaType.Type.QString
except (ImportError, AttributeError):
    from qgis.PyQt.QtCore import QVariant
    TYPE_INT, TYPE_STR = QVariant.Int, QVariant.String

try:
    from qgis.core import Qgis
    WKB_POLYGON = Qgis.WkbType.Polygon
except (ImportError, AttributeError):
    from qgis.core import QgsWkbTypes
    WKB_POLYGON = QgsWkbTypes.Polygon

# --- point this at your checkout if the script can't work it out ------------
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) \
    if "__file__" in globals() else os.path.expanduser(
        "~/CoWork/01_personal/fort.mouse")

# ---- CHANGE THIS to the loop you are working on -------------------------
LOOP = 1200
# -------------------------------------------------------------------------

CRS_FT = "EPSG:2236"          # NAD83 / Florida East, ftUS — measurements come out in feet

project = QgsProject.instance()


def drop_existing(names):
    for layer in list(project.mapLayers().values()):
        if layer.name() in names:
            project.removeMapLayer(layer.id())


# --------------------------------------------------------------------------
# 1. CRS. Everything downstream depends on this being feet.
# --------------------------------------------------------------------------
project.setCrs(QgsCoordinateReferenceSystem(CRS_FT))
print(f"CRS set to {CRS_FT} — the measure tool now reads in feet")

# --------------------------------------------------------------------------
# 2. Imagery, bottom of the stack first so 2025 ends up on top.
#    Order reflects what the imagery actually looks like over this loop, not
#    what the metadata claims: 2024 is soft, NAIP is only an occupancy check.
# --------------------------------------------------------------------------
OCPA = "https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials{}/MapServer"
ESRI = ("https://services.arcgisonline.com/ArcGIS/rest/services/"
        "World_Imagery/MapServer/tile/{z}/{y}/{x}")
NAIP = ("https://imagery.nationalmap.gov/arcgis/rest/services/"
        "USGSNAIPImagery/ImageServer")

imagery = [
    ("NAIP 2023 — occupancy check only", f"url={NAIP}", "arcgismapserver"),
    ("Esri World Imagery (ADR-0003 tracing grant)",
     f"type=xyz&url={quote(ESRI, safe='')}&zmax=21&zmin=0", "wms"),
    ("OCPA 2024 — soft", f"url={OCPA.format(2024)}", "arcgismapserver"),
    ("OCPA 2022 — second look", f"url={OCPA.format(2022)}", "arcgismapserver"),
    ("OCPA 2025 — PRIMARY", f"url={OCPA.format(2025)}", "arcgismapserver"),
]

drop_existing([name for name, _, _ in imagery])
for name, uri, provider in imagery:
    layer = QgsRasterLayer(uri, name, provider)
    if layer.isValid():
        project.addMapLayer(layer)
        print(f"  loaded  {name}")
    else:
        print(f"  FAILED  {name}  — add it by hand from pipeline/README.md")

# --------------------------------------------------------------------------
# 3. Reference layers — the county's public record and the road centreline.
# --------------------------------------------------------------------------
refs = [
    (f"Loop {LOOP} county segments", f"data/reference/loop-{LOOP}-county-segments.geojson"),
    (f"Loop {LOOP} road (OSM)", f"data/reference/loop-{LOOP}-osm-road.geojson"),
]
drop_existing([name for name, _ in refs])
for name, rel in refs:
    path = os.path.join(REPO, rel)
    if not os.path.exists(path):
        print(f"  MISSING {rel}")
        continue
    layer = QgsVectorLayer(path, name, "ogr")
    if layer.isValid():
        project.addMapLayer(layer)
        print(f"  loaded  {name}")

# --------------------------------------------------------------------------
# 4. The pad layer. Schema matches derive.py exactly — site_number is the only
#    field it requires; the rest are optional and blank is a legitimate answer.
# --------------------------------------------------------------------------
PADS = os.path.join(REPO, "work", f"loop-{LOOP}-pads.gpkg")
PADS_NAME = f"Loop {LOOP} pads"
drop_existing([PADS_NAME])

if not os.path.exists(PADS):
    fields = QgsFields()
    fields.append(QgsField("site_number", TYPE_INT))
    for name in ("pad_surface", "backs_onto", "approach_side",
                 "imagery_vintage", "number_confidence", "notes"):
        fields.append(QgsField(name, TYPE_STR))

    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "GPKG"
    opts.layerName = "pads"
    os.makedirs(os.path.dirname(PADS), exist_ok=True)

    writer = QgsVectorFileWriter.create(
        PADS, fields, WKB_POLYGON,
        QgsCoordinateReferenceSystem(CRS_FT),
        project.transformContext(), opts)

    # The writer only commits to disk when it is destroyed. Without this the file
    # is never written and the failure is completely silent.
    err = writer.hasError()
    msg = writer.errorMessage()
    del writer

    if err != QgsVectorFileWriter.NoError or not os.path.exists(PADS):
        raise RuntimeError(
            f"could not create {PADS}\n  {msg}\n"
            "  Create it by hand: Layer > Create Layer > New GeoPackage Layer, "
            "polygon, EPSG:2236, with the fields in pipeline/README.md")
    print(f"  created {PADS}")

pads = QgsVectorLayer(f"{PADS}|layername=pads", PADS_NAME, "ogr")
if pads.isValid():
    project.addMapLayer(pads)
    print(f"  loaded  {PADS_NAME}  (toggle editing and start drawing)")

# --------------------------------------------------------------------------
# 5. Zoom to the loop, framed from its own road geometry rather than a
#    hardcoded box, so this works for any loop.
# --------------------------------------------------------------------------
import json

bbox = None
road = os.path.join(REPO, "data", "reference", f"loop-{LOOP}-osm-road.geojson")
if os.path.exists(road):
    pts = [p for f in json.load(open(road))["features"]
           for p in f["geometry"]["coordinates"]]
    if pts:
        bbox = (min(p[0] for p in pts), min(p[1] for p in pts),
                max(p[0] for p in pts), max(p[1] for p in pts))

try:
    if bbox is None:
        raise ValueError(f"no road geometry for loop {LOOP}")
    src = QgsCoordinateReferenceSystem("EPSG:4326")
    tx = QgsCoordinateTransform(src, project.crs(), project)
    extent = tx.transformBoundingBox(QgsRectangle(*bbox))
    extent.grow(120)  # feet of breathing room
    iface.mapCanvas().setExtent(extent)
    iface.mapCanvas().refresh()
    print(f"zoomed to Loop {LOOP}")
except (NameError, ValueError) as exc:
    print(f"could not zoom automatically ({exc}) — zoom manually")

print("\nready. Shape Digitizing ▸ Rectangle from 3 points (projected).")
print("Trace the concrete, not the site. Record which vintage you measured from.")
