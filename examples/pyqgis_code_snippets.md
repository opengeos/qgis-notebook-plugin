# 📓 PyQGIS Code Snippets

## 0. Environment Check

```{code-cell} python
from qgis.core import *
from qgis.utils import iface

print(Qgis.QGIS_VERSION)
print(QgsApplication.qgisSettingsDirPath())
```

## 1. Access QGIS Interface Objects

```{code-cell} python
canvas = iface.mapCanvas()
project = QgsProject.instance()
```

## 2. Add Layers

### 2.1 Add Local Vector Layer

```{code-cell} python
vector_path = "/path/to/data.shp"

vlayer = QgsVectorLayer(vector_path, "My Vector Layer", "ogr")
QgsProject.instance().addMapLayer(vlayer)

print(vlayer.isValid())
```

### 2.2 Add Raster Layer

```{code-cell} python
raster_path = "/path/to/image.tif"

rlayer = QgsRasterLayer(raster_path, "My Raster")
QgsProject.instance().addMapLayer(rlayer)

print(rlayer.isValid())
```

### 2.3 Add Online GeoJSON

```{code-cell} python
url = "https://github.com/opengeos/datasets/releases/download/world/world_cities.geojson"

layer = QgsVectorLayer(url, "World Cities", "ogr")
iface.addVectorLayer(url, "World Cities", "ogr")
```

### 2.4 Add XYZ Tiles (OpenStreetMap)

```{code-cell} python
url = "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"
osm = QgsRasterLayer(url, "OpenStreetMap", "wms")

QgsProject.instance().addMapLayer(osm)
```

## 3. Zoom & Navigation

### Zoom to Active Layer

```{code-cell} python
iface.zoomToActiveLayer()
```

### Zoom to Full Extent

```{code-cell} python
iface.mapCanvas().zoomToFullExtent()
```

### Zoom to Selected Features

```{code-cell} python
iface.mapCanvas().zoomToSelected()
```

## 4. Layer Inspection

### List All Layers

```{code-cell} python
for layer in project.mapLayers().values():
    print(layer.name(), layer.type())
```

### Get Active Layer

```{code-cell} python
layer = iface.activeLayer()
print(layer.name())
```

## 5. Feature & Geometry Operations

### Iterate Over Features

```{code-cell} python
for f in layer.getFeatures():
    print(f.id(), f.attributes())
```

### Access Geometry

```{code-cell} python
for f in layer.getFeatures():
    print(f.geometry().asWkt())
```

### Select by Expression

```{code-cell} python
layer.selectByExpression("population > 1000000")
layer.selectedFeatureCount()
```

### Clear Selection

```{code-cell} python
layer.removeSelection()
```

## 6. Attribute Table Operations

### Add a Field

```{code-cell} python
from PyQt5.QtCore import QVariant

layer.startEditing()

layer.addAttribute(QgsField("area_km2", QVariant.Double))
layer.updateFields()

layer.commitChanges()
```

### Update Attribute Values

```{code-cell} python
layer.startEditing()

idx = layer.fields().indexOf("area_km2")

for f in layer.getFeatures():
    area = f.geometry().area() / 1e6
    layer.changeAttributeValue(f.id(), idx, area)

layer.commitChanges()
```

## 7. Styling & Symbology

### Change Single Symbol Color

```{code-cell} python
from PyQt5.QtGui import QColor

symbol = layer.renderer().symbol()
symbol.setColor(QColor("red"))

layer.triggerRepaint()
```

### Graduated Renderer

```{code-cell} python
from qgis.core import QgsGraduatedSymbolRenderer

renderer = QgsGraduatedSymbolRenderer.createRenderer(
    layer,
    "population",
    5,
    QgsGraduatedSymbolRenderer.EqualInterval,
    QgsSymbol.defaultSymbol(layer.geometryType()),
    QgsColorRamp("Blues")
)

layer.setRenderer(renderer)
layer.triggerRepaint()
```

## 8. Labeling

```{code-cell} python
settings = QgsPalLayerSettings()
settings.fieldName = "name"
settings.enabled = True

layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
layer.setLabelsEnabled(True)

layer.triggerRepaint()
```

## 9. CRS & Reprojection

### Check CRS

```{code-cell} python
layer.crs().authid()
```

### Reproject Layer (In Memory)

```{code-cell} python
import processing

params = {
    "INPUT": layer,
    "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:4326"),
    "OUTPUT": "memory:"
}

result = processing.run("native:reprojectlayer", params)
QgsProject.instance().addMapLayer(result["OUTPUT"])
```

## 10. Processing Algorithms

### Buffer

```{code-cell} python
params = {
    "INPUT": layer,
    "DISTANCE": 1000,
    "SEGMENTS": 8,
    "OUTPUT": "memory:"
}

buffered = processing.run("native:buffer", params)
QgsProject.instance().addMapLayer(buffered["OUTPUT"])
```

### Clip

```{code-cell} python
processing.run(
    "native:clip",
    {
        "INPUT": input_layer,
        "OVERLAY": clip_layer,
        "OUTPUT": "memory:"
    }
)
```

## 11. Raster Operations

### RGB Band Combination

```{code-cell} python
renderer = QgsMultiBandColorRenderer(
    rlayer.dataProvider(),
    4, 3, 2
)

rlayer.setRenderer(renderer)
rlayer.triggerRepaint()
```

### Contrast Stretch

```{code-cell} python
renderer.setContrastEnhancement(
    QgsContrastEnhancement.StretchToMinimumMaximum
)
rlayer.triggerRepaint()
```

## 12. Export Data

### Export Selected Features

```{code-cell} python
QgsVectorFileWriter.writeAsVectorFormat(
    layer,
    "/path/output.geojson",
    "UTF-8",
    layer.crs(),
    "GeoJSON",
    onlySelected=True
)
```

### Export Map as Image

```{code-cell} python
from PyQt5.QtCore import QSize

settings = QgsMapSettings()
settings.setLayers([layer])
settings.setExtent(layer.extent())
settings.setOutputSize(QSize(1920, 1080))

job = QgsMapRendererParallelJob(settings)
job.start()
job.waitForFinished()

img = job.renderedImage()
img.save("/path/map.png")
```

## 13. Messages & Logging

```{code-cell} python
iface.messageBar().pushInfo("PyQGIS", "Task completed successfully")
```

```{code-cell} python
QgsMessageLog.logMessage("Debug message", "Notebook", Qgis.Info)
```

## 14. Plugin-Friendly Utilities

```{code-cell} python
from qgis.utils import iface
```

```{code-cell} python
QgsApplication.instance().messageLog().messageReceived.connect(
    lambda msg, tag, level: print(msg)
)
```
