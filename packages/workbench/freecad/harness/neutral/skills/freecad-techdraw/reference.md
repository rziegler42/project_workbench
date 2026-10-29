# Reference: TechDraw examples

Each block was run headless with `freecadcmd` on FreeCAD 1.1.4. The printed value is in the comment. The blocks that make a page or a box use `make_page` and `make_box` from the Helpers block, which must be defined first. A TechDraw object is created with `doc.addObject("TechDraw::...", name)`.

## Helpers

```python
import os

import FreeCAD as App
import Part

V = App.Vector


def make_page(doc, template_name="Default_Template_A4_Landscape.svg"):
    page = doc.addObject("TechDraw::DrawPage", "Page")
    template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    template.Template = os.path.join(App.getResourceDir(), "Mod", "TechDraw", "Templates", template_name)
    page.Template = template
    return page, template


def make_box(doc):
    box = doc.addObject("Part::Feature", "Box")
    box.Shape = Part.makeBox(40, 20, 10)
    return box
```

## The types and the templates

```python
import os

import FreeCAD as App
import TechDraw

doc = App.newDocument("d")
types = [t for t in doc.supportedTypes() if t.startswith("TechDraw")]
print(len(types), types[:6])
# 45 ['TechDraw::DrawPage', 'TechDraw::DrawView', 'TechDraw::DrawViewCollection', 'TechDraw::DrawViewPart', 'TechDraw::DrawViewAnnotation', 'TechDraw::DrawViewSymbol']
base = os.path.join(App.getResourceDir(), "Mod", "TechDraw", "Templates")
print(sorted(os.listdir(base)))
# ['ASME', 'Default_Template_A4_Landscape.svg', 'HowToExample.svg', 'ISO']
```

## A page from a template

```python
import os

import FreeCAD as App

doc = App.newDocument("d")
page, template = make_page(doc)
doc.recompute()
print(page.State, template.State, template.Width, template.Height, template.Orientation, page.Scale, page.ProjectionType)
# ['Up-to-date'] ['Up-to-date'] 297.0 mm 210.0 mm Landscape 1.0 First angle
print(page.getEnumerationsOfProperty("ProjectionType"), page.Views)
# ['First angle', 'Third angle'] []
print(template.EditableTexts)                                                                  # {}
result = template.PageResult
print(os.path.exists(result), os.path.dirname(result) != os.path.dirname(template.Template))   # True True   the copy lives in FreeCAD's cache folder
```

## A projected view

```python
import FreeCAD as App

doc = App.newDocument("d")
page, template = make_page(doc)
box = make_box(doc)
view = doc.addObject("TechDraw::DrawViewPart", "View")
page.addView(view)
view.Source = [box]
view.Direction = App.Vector(0, 0, 1)
view.XDirection = App.Vector(1, 0, 0)
view.Scale = 1.0
view.X = 100
view.Y = 100
doc.recompute()
print(view.State, page.Views, view.ScaleType, view.Scale)                                      # ['Up-to-date'] [<DrawViewPart object>] Page 1.0
```

## What the view computed

```python
import FreeCAD as App

doc = App.newDocument("d")
page, template = make_page(doc)
box = make_box(doc)
view = doc.addObject("TechDraw::DrawViewPart", "View")
page.addView(view)
view.Source = [box]
view.Direction = App.Vector(0, 0, 1)
doc.recompute()
print(len(view.getVisibleEdges()), len(view.getHiddenEdges()), len(view.getVisibleVertexes()))  # 4 0 4
print(type(view.getEdgeByIndex(0)).__name__)                                                   # Edge
print(hasattr(view, "getBoundingBox"), hasattr(view, "getEdgeCount"))                          # False False
```

## Project without a page

`TechDraw.project` needs no page and no document object.

```python
import FreeCAD as App
import Part
import TechDraw

V = App.Vector
box = Part.makeBox(40, 20, 10)
result = TechDraw.project(box, V(0, 0, 1))
print(type(result).__name__, len(result), [len(r.Edges) for r in result])                      # list 4 [4, 0, 4, 0]
print(len(TechDraw.projectEx(box, V(0, 0, 1))))                                                # 10
svg = TechDraw.projectToSVG(box, V(0, 0, 1))
print(type(svg).__name__, len(svg), svg[:20].replace("\n", " "))                               # str 301 <g   fill="none"
dxf = TechDraw.projectToDXF(box, V(0, 0, 1))
print(type(dxf).__name__, len(dxf))                                                            # str 324
```

## A dimension

```python
import FreeCAD as App

doc = App.newDocument("d")
page, template = make_page(doc)
box = make_box(doc)
view = doc.addObject("TechDraw::DrawViewPart", "View")
page.addView(view)
view.Source = [box]
view.Direction = App.Vector(0, 0, 1)
doc.recompute()
dim = doc.addObject("TechDraw::DrawViewDimension", "Dim")
print(dim.getEnumerationsOfProperty("Type"))
# ['Distance', 'DistanceX', 'DistanceY', 'DistanceZ', 'Radius', 'Diameter', 'Angle', 'Angle3Pt', 'Area']
print(dim.getEnumerationsOfProperty("MeasureType"))                                            # ['True', 'Projected']
page.addView(dim)
dim.Type = "Distance"
dim.MeasureType = "Projected"
dim.References2D = [(view, "Edge0")]
doc.recompute()
print(dim.State, dim.getRawValue())                                                            # ['Up-to-date'] 20.0
```

## Dimensions by edge

The edge number is the view's own edge order, not the box's.

```python
import FreeCAD as App

doc = App.newDocument("d")
page, template = make_page(doc)
box = make_box(doc)
view = doc.addObject("TechDraw::DrawViewPart", "View")
page.addView(view)
view.Source = [box]
view.Direction = App.Vector(0, 0, 1)
doc.recompute()
for i in range(4):
    dim = doc.addObject("TechDraw::DrawViewDimension", "Dim%d" % i)
    page.addView(dim)
    dim.Type = "Distance"
    dim.MeasureType = "Projected"
    dim.References2D = [(view, "Edge%d" % i)]
    doc.recompute()
    print(i, dim.State, round(dim.getRawValue(), 3))
# 0 ['Up-to-date'] 20.0
# 1 ['Up-to-date'] 20.0
# 2 ['Up-to-date'] 40.0
# 3 ['Up-to-date'] 40.0
```

## An annotation

```python
import FreeCAD as App

doc = App.newDocument("d")
page, template = make_page(doc)
note = doc.addObject("TechDraw::DrawViewAnnotation", "Note")
page.addView(note)
note.Text = ["Part 1", "Material: steel"]
note.X = 60
note.Y = 20
note.TextSize = 5
doc.recompute()
print(note.State, note.Text, note.X, note.Y, page.Views)
# ['Up-to-date'] ['Part 1', 'Material: steel'] 60.0 mm 20.0 mm [<DrawView object>]
```

## Export

The files are written to a temporary folder that is removed afterwards.

```python
import os
import tempfile

import FreeCAD as App
import TechDraw

doc = App.newDocument("d")
page, template = make_page(doc)
box = make_box(doc)
view = doc.addObject("TechDraw::DrawViewPart", "View")
page.addView(view)
view.Source = [box]
view.Direction = App.Vector(0, 0, 1)
doc.recompute()
with tempfile.TemporaryDirectory() as tmp:
    for label, call in (("writeDXFPage", TechDraw.writeDXFPage), ("writeDXFView", TechDraw.writeDXFView)):
        path = os.path.join(tmp, label + ".dxf")
        call(page if label == "writeDXFPage" else view, path)
        print(label, os.path.exists(path), os.path.getsize(path))
    # writeDXFPage True 4903
    # writeDXFView True 4903
svg = TechDraw.viewPartAsSvg(view)
dxf = TechDraw.viewPartAsDxf(view)
print(type(svg).__name__, len(svg), type(dxf).__name__, len(dxf))                             # str 308 str 340
```

## Saving a document with a page

```python
import os
import tempfile

import FreeCAD as App

doc = App.newDocument("d")
page, template = make_page(doc)
doc.recompute()
with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "page.FCStd")
    doc.saveAs(path)
    print(os.path.exists(path))                                                                # True
```
