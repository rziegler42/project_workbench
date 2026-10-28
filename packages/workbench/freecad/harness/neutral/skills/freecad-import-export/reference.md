# Reference: import and export examples

Every example below was run headless with `freecadcmd` on FreeCAD 1.1.4, and the printed value is in the comment. Each
example writes into a temporary folder and removes it again.

## Shapes: STEP, IGES and BREP

```python
import os
import shutil
import tempfile

import FreeCAD as App
import Part

folder = tempfile.mkdtemp()
doc = App.newDocument("Shapes")
obj = doc.addObject("Part::Feature", "Part")
obj.Shape = Part.makeBox(10, 20, 30).cut(Part.makeCylinder(4, 40, App.Vector(5, 10, -5)))
doc.recompute()
print(round(obj.Shape.Volume, 2))

for name in ("part.step", "part.iges", "part.brep"):
    Part.export([obj], os.path.join(folder, name))              # the extension picks the format
    back = Part.read(os.path.join(folder, name))
    print(name, back.ShapeType, round(back.Volume, 2), back.isValid())

obj.Shape.exportStep(os.path.join(folder, "direct.step"))       # a shape can also export itself
direct = Part.Shape()
direct.read(os.path.join(folder, "direct.step"))
print(round(direct.Volume, 2))
shutil.rmtree(folder)
```

## Meshes: STL, OBJ and 3MF

```python
import os
import shutil
import tempfile

import FreeCAD as App
import Mesh
import Part

folder = tempfile.mkdtemp()
doc = App.newDocument("Meshes")
obj = doc.addObject("Part::Feature", "Part")
obj.Shape = Part.makeCylinder(10, 20)
doc.recompute()

for name in ("part.stl", "part.obj", "part.3mf"):
    path = os.path.join(folder, name)
    Mesh.export([obj], path)                                    # a Part object is meshed on export
    back = Mesh.Mesh(path)
    print(name, back.CountFacets, round(back.Volume, 1), back.isSolid())
shutil.rmtree(folder)
```

## 3MF for printing: units, fineness and a check on the file

```python
import os
import shutil
import tempfile
import zipfile

import FreeCAD as App
import Mesh
import MeshPart
import Part

folder = tempfile.mkdtemp()
doc = App.newDocument("Print")
shape = Part.makeCylinder(10, 20)
obj = doc.addObject("Part::Feature", "Cylinder")
obj.Shape = shape
doc.recompute()

default = os.path.join(folder, "default.3mf")
Mesh.export([obj], default)

mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02, AngularDeflection=0.2)
feature = doc.addObject("Mesh::Feature", "ForPrint")
feature.Mesh = mesh
controlled = os.path.join(folder, "controlled.3mf")
Mesh.export([feature], controlled)

print(Mesh.Mesh(default).CountFacets, Mesh.Mesh(controlled).CountFacets)      # the controlled export is finer

with zipfile.ZipFile(controlled) as archive:
    names = archive.namelist()
    model = archive.read([n for n in names if n.endswith(".model")][0]).decode("utf-8")
print('unit="millimeter"' in model)                              # True: 3MF from FreeCAD is in millimetres

back = Mesh.Mesh(controlled)
print(back.isSolid(), back.hasNonManifolds(), round(back.Volume, 1), round(shape.Volume, 1))
bb = back.BoundBox
print(round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2))        # 20.0 20.0 20.0
shutil.rmtree(folder)
```

## Export every solid in a document

```python
import os
import shutil
import tempfile

import FreeCAD as App
import Part

folder = tempfile.mkdtemp()
doc = App.newDocument("Batch")
for name, shape in (("Block", Part.makeBox(10, 10, 10)), ("Ball", Part.makeSphere(5)), ("Plate", Part.makePlane(5, 5))):
    doc.addObject("Part::Feature", name).Shape = shape
doc.recompute()

written = []
for obj in doc.Objects:
    if hasattr(obj, "Shape") and obj.Shape.Solids:                  # solids only: the plate is skipped
        path = os.path.join(folder, obj.Name + ".step")
        Part.export([obj], path)
        written.append(os.path.basename(path))
print(sorted(written))
shutil.rmtree(folder)
```

## A whole document and the Import module

```python
import os
import shutil
import tempfile

import FreeCAD as App
import Part

folder = tempfile.mkdtemp()
doc = App.newDocument("Whole")
doc.addObject("Part::Feature", "Block").Shape = Part.makeBox(10, 10, 10)
doc.recompute()
saved = os.path.join(folder, "whole.FCStd")
doc.saveAs(saved)
App.closeDocument(doc.Name)
reopened = App.openDocument(saved)
print([o.Name for o in reopened.Objects], round(reopened.Block.Shape.Volume, 1))

import Import

print([n for n in dir(Import) if not n.startswith("_")])
Import.export([reopened.Block], os.path.join(folder, "via_import.step"))
target = App.newDocument("Target")
Import.insert(os.path.join(folder, "via_import.step"), target.Name)
print([o.Name for o in target.Objects])
shutil.rmtree(folder)
```
