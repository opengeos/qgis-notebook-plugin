"""
PyQGIS Code Snippets

This module contains pre-defined PyQGIS code snippets for quick insertion
into notebook cells.
"""

SNIPPETS = [
    {
        "title": "1. Environment Check",
        "code": """from qgis.core import *
from qgis.utils import iface

print(Qgis.QGIS_VERSION)
print(QgsApplication.qgisSettingsDirPath())""",
    },
    {
        "title": "2. Access QGIS Interface Objects",
        "code": """canvas = iface.mapCanvas()
project = QgsProject.instance()""",
    },
    {
        "title": "3. Add Local Vector Layer",
        "code": """vector_path = "/path/to/data.shp"

vlayer = QgsVectorLayer(vector_path, "My Vector Layer", "ogr")
QgsProject.instance().addMapLayer(vlayer)

print(vlayer.isValid())""",
    },
    {
        "title": "4. Add Raster Layer",
        "code": """raster_path = "/path/to/image.tif"

rlayer = QgsRasterLayer(raster_path, "My Raster")
QgsProject.instance().addMapLayer(rlayer)

print(rlayer.isValid())""",
    },
    {
        "title": "5. Add Online GeoJSON",
        "code": """url = "https://github.com/opengeos/datasets/releases/download/world/world_cities.geojson"

layer = QgsVectorLayer(url, "World Cities", "ogr")
iface.addVectorLayer(url, "World Cities", "ogr")""",
    },
    {
        "title": "6. Add XYZ Tiles (OpenStreetMap)",
        "code": """url = "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"
osm = QgsRasterLayer(url, "OpenStreetMap", "wms")

QgsProject.instance().addMapLayer(osm)""",
    },
    {
        "title": "7. Zoom to Active Layer",
        "code": """iface.zoomToActiveLayer()""",
    },
    {
        "title": "8. Zoom to Full Extent",
        "code": """iface.mapCanvas().zoomToFullExtent()""",
    },
    {
        "title": "9. Zoom to Selected Features",
        "code": """iface.mapCanvas().zoomToSelected()""",
    },
    {
        "title": "10. List All Layers",
        "code": """for layer in project.mapLayers().values():
    print(layer.name(), layer.type())""",
    },
    {
        "title": "11. Get Active Layer",
        "code": """layer = iface.activeLayer()
print(layer.name())""",
    },
    {
        "title": "12. Iterate Over Features",
        "code": """for f in layer.getFeatures():
    print(f.id(), f.attributes())""",
    },
    {
        "title": "13. Access Geometry",
        "code": """for f in layer.getFeatures():
    print(f.geometry().asWkt())""",
    },
    {
        "title": "14. Select by Expression",
        "code": """layer.selectByExpression("population > 1000000")
layer.selectedFeatureCount()""",
    },
    {
        "title": "15. Clear Selection",
        "code": """layer.removeSelection()""",
    },
    {
        "title": "16. Add a Field",
        "code": """from PyQt5.QtCore import QVariant

layer.startEditing()

layer.addAttribute(QgsField("area_km2", QVariant.Double))
layer.updateFields()

layer.commitChanges()""",
    },
    {
        "title": "17. Update Attribute Values",
        "code": """layer.startEditing()

idx = layer.fields().indexOf("area_km2")

for f in layer.getFeatures():
    area = f.geometry().area() / 1e6
    layer.changeAttributeValue(f.id(), idx, area)

layer.commitChanges()""",
    },
    {
        "title": "18. Change Single Symbol Color",
        "code": """from PyQt5.QtGui import QColor

symbol = layer.renderer().symbol()
symbol.setColor(QColor("red"))

layer.triggerRepaint()""",
    },
    {
        "title": "19. Graduated Renderer",
        "code": """from qgis.core import QgsGraduatedSymbolRenderer

renderer = QgsGraduatedSymbolRenderer.createRenderer(
    layer,
    "population",
    5,
    QgsGraduatedSymbolRenderer.EqualInterval,
    QgsSymbol.defaultSymbol(layer.geometryType()),
    QgsColorRamp("Blues")
)

layer.setRenderer(renderer)
layer.triggerRepaint()""",
    },
    {
        "title": "20. Labeling",
        "code": """settings = QgsPalLayerSettings()
settings.fieldName = "name"
settings.enabled = True

layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
layer.setLabelsEnabled(True)

layer.triggerRepaint()""",
    },
    {
        "title": "21. Check CRS",
        "code": """layer.crs().authid()""",
    },
    {
        "title": "22. Reproject Layer (In Memory)",
        "code": """import processing

params = {
    "INPUT": layer,
    "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:4326"),
    "OUTPUT": "memory:"
}

result = processing.run("native:reprojectlayer", params)
QgsProject.instance().addMapLayer(result["OUTPUT"])""",
    },
    {
        "title": "23. Buffer",
        "code": """params = {
    "INPUT": layer,
    "DISTANCE": 1000,
    "SEGMENTS": 8,
    "OUTPUT": "memory:"
}

buffered = processing.run("native:buffer", params)
QgsProject.instance().addMapLayer(buffered["OUTPUT"])""",
    },
    {
        "title": "24. Clip",
        "code": """processing.run(
    "native:clip",
    {
        "INPUT": input_layer,
        "OVERLAY": clip_layer,
        "OUTPUT": "memory:"
    }
)""",
    },
    {
        "title": "25. RGB Band Combination",
        "code": """renderer = QgsMultiBandColorRenderer(
    rlayer.dataProvider(),
    4, 3, 2
)

rlayer.setRenderer(renderer)
rlayer.triggerRepaint()""",
    },
    {
        "title": "26. Contrast Stretch",
        "code": """renderer.setContrastEnhancement(
    QgsContrastEnhancement.StretchToMinimumMaximum
)
rlayer.triggerRepaint()""",
    },
    {
        "title": "27. Export Selected Features",
        "code": """QgsVectorFileWriter.writeAsVectorFormat(
    layer,
    "/path/output.geojson",
    "UTF-8",
    layer.crs(),
    "GeoJSON",
    onlySelected=True
)""",
    },
    {
        "title": "28. Export Map as Image",
        "code": """from PyQt5.QtCore import QSize

settings = QgsMapSettings()
settings.setLayers([layer])
settings.setExtent(layer.extent())
settings.setOutputSize(QSize(1920, 1080))

job = QgsMapRendererParallelJob(settings)
job.start()
job.waitForFinished()

img = job.renderedImage()
img.save("/path/map.png")""",
    },
    {
        "title": "29. Messages & Logging (Info)",
        "code": """iface.messageBar().pushInfo("PyQGIS", "Task completed successfully")""",
    },
    {
        "title": "30. Messages & Logging (Log)",
        "code": """QgsMessageLog.logMessage("Debug message", "Notebook", Qgis.Info)""",
    },
    {
        "title": "31. Import iface",
        "code": """from qgis.utils import iface""",
    },
    {
        "title": "32. Connect to Message Log",
        "code": """QgsApplication.instance().messageLog().messageReceived.connect(
    lambda msg, tag, level: print(msg)
)""",
    },
]
