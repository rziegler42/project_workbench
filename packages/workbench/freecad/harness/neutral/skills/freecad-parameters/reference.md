# Reference: parameters examples

Every example below was run headless with `freecadcmd` on FreeCAD 1.1.4, and the printed value is in the comment. The
VarSet examples follow the owner's source; the Spreadsheet examples were written by the author of this skill and checked
by running them.

## Helpers

```python
import math
import FreeCAD as App
import Part
import Sketcher

V = App.Vector


def padded_box(doc, w=20, d=20, h=10):
    """A Body with a rectangular Pad, constrained by four dimensions you can name."""
    body = doc.addObject("PartDesign::Body", "Body")
    xy = next(o for o in body.Origin.OriginFeatures if o.Role == "XY_Plane")
    sk = body.newObject("Sketcher::SketchObject", "Sketch")
    sk.AttachmentSupport = [(xy, "")]
    sk.MapMode = "FlatFace"
    pts = [(0, 0), (w, 0), (w, d), (0, d)]
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        sk.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
    sk.addConstraint(Sketcher.Constraint("Horizontal", 0))
    sk.addConstraint(Sketcher.Constraint("Horizontal", 2))
    sk.addConstraint(Sketcher.Constraint("Vertical", 1))
    sk.addConstraint(Sketcher.Constraint("Vertical", 3))
    sk.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))
    width = sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, float(w)))
    depth = sk.addConstraint(Sketcher.Constraint("DistanceY", 1, 1, 1, 2, float(d)))
    sk.renameConstraint(width, "width")
    sk.renameConstraint(depth, "depth")
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = sk
    pad.Length = h
    doc.recompute()
    return body, sk, pad
```

## A VarSet holds the dimensions

```python
doc = App.newDocument("VarSetModel")
body, sk, pad = padded_box(doc)

varset = doc.addObject("App::VarSet", "Dims")
varset.addProperty("App::PropertyLength", "BaseWidth", "Dimensions", "Width of the base")
varset.addProperty("App::PropertyLength", "BaseDepth", "Dimensions", "Depth of the base")
varset.addProperty("App::PropertyLength", "BaseHeight", "Dimensions", "Height of the base")
varset.addProperty("App::PropertyAngle", "Opening", "Dimensions", "An opening angle")
varset.addProperty("App::PropertyInteger", "Count", "Dimensions", "A count")
varset.BaseWidth, varset.BaseDepth, varset.BaseHeight = 30.0, 20.0, 10.0
varset.Opening, varset.Count = 30, 3

pad.setExpression("Length", "Dims.BaseHeight")                    # a feature property
sk.setExpression("Constraints.width", "Dims.BaseWidth")           # a named sketch constraint
sk.setExpression("Constraints.depth", "Dims.BaseDepth")
doc.recompute()
print(round(pad.Shape.Volume, 1))                                  # 6000.0

varset.BaseHeight = 15
doc.recompute()
print(round(pad.Shape.Volume, 1))                                  # 9000.0
print(pad.ExpressionEngine, varset.Opening, varset.Count)
```

## Derive a value instead of precomputing it

```python
doc = App.newDocument("Derived")
body, sk, pad = padded_box(doc)
varset = doc.addObject("App::VarSet", "Dims")
for name in ("Outer", "Wall"):
    varset.addProperty("App::PropertyLength", name, "Dimensions", name)
varset.Outer, varset.Wall = 30.0, 4.0

sk.setExpression("Constraints.width", "Dims.Outer")
sk.setExpression("Constraints.depth", "Dims.Outer - 2 * Dims.Wall")      # derived, not typed in
pad.setExpression("Length", "Dims.Wall * 2")
doc.recompute()
print(round(pad.Shape.Volume, 1), pad.State)                       # 30 x 22 x 8 = 5280.0
```

## A Spreadsheet holds the dimensions

```python
doc = App.newDocument("SheetModel")
body, sk, pad = padded_box(doc)

sheet = doc.addObject("Spreadsheet::Sheet", "Params")
sheet.set("A1", "width")
sheet.set("B1", "30 mm")
sheet.setAlias("B1", "width")                  # an alias is the name an expression uses
sheet.set("A2", "depth")
sheet.set("B2", "20 mm")
sheet.setAlias("B2", "depth")
sheet.set("A3", "height")
sheet.set("B3", "10 mm")
sheet.setAlias("B3", "height")
doc.recompute()

sk.setExpression("Constraints.width", "Params.width")
sk.setExpression("Constraints.depth", "Params.depth")
pad.setExpression("Length", "Params.height")
doc.recompute()
print(round(pad.Shape.Volume, 1))                                  # 6000.0

sheet.set("B3", "15 mm")
doc.recompute()
print(round(pad.Shape.Volume, 1))                                  # 9000.0
print(sheet.get("B3"), sheet.getContents("B3"), sheet.getAlias("B3"))
```

## A cell can hold a formula

```python
doc = App.newDocument("SheetFormula")
body, sk, pad = padded_box(doc)

sheet = doc.addObject("Spreadsheet::Sheet", "Params")
sheet.set("A1", "outer")
sheet.set("B1", "30 mm")
sheet.setAlias("B1", "outer")
sheet.set("A2", "wall")
sheet.set("B2", "4 mm")
sheet.setAlias("B2", "wall")
sheet.set("A3", "inner")
sheet.set("B3", "=outer - 2 * wall")        # a leading = makes a formula
sheet.setAlias("B3", "inner")
doc.recompute()

sk.setExpression("Constraints.width", "Params.outer")
sk.setExpression("Constraints.depth", "Params.inner")
pad.setExpression("Length", "Params.wall")
doc.recompute()
print(sheet.get("B3"), round(pad.Shape.Volume, 1))                 # 22 mm and 30 x 22 x 4 = 2640.0
```

## Reading and clearing expressions, and a bad expression

```python
doc = App.newDocument("Expr")
body, sk, pad = padded_box(doc)
varset = doc.addObject("App::VarSet", "Dims")
varset.addProperty("App::PropertyLength", "BaseHeight", "Dimensions", "Height")
varset.BaseHeight = 12

pad.setExpression("Length", "Dims.BaseHeight")
print(pad.ExpressionEngine)                         # [('Length', 'Dims.BaseHeight')]
pad.setExpression("Length", None)                   # None removes the expression
print(pad.ExpressionEngine)                         # []

try:
    pad.setExpression("Length", "Dims.NoSuchProperty")
    doc.recompute()
    print("accepted; State:", pad.State)
except Exception as error:
    print("raised:", type(error).__name__, str(error)[:60])
```

## What each one offers

```python
import FreeCAD as App

doc = App.newDocument("Offers")
varset = doc.addObject("App::VarSet", "Dims")
varset.addProperty("App::PropertyLength", "L", "Dimensions", "A length")
varset.addProperty("App::PropertyAngle", "A", "Dimensions", "An angle")
varset.addProperty("App::PropertyInteger", "N", "Dimensions", "A count")
varset.addProperty("App::PropertyBool", "On", "Dimensions", "A flag")
print([varset.getTypeIdOfProperty(n) for n in ("L", "A", "N", "On")])
varset.L = 5
print(type(varset.L).__name__, varset.L.Unit.Type if hasattr(varset.L, "Unit") else None)

sheet = doc.addObject("Spreadsheet::Sheet", "Table")
sheet.set("A1", "5 mm")
sheet.set("A2", "3")
sheet.set("A3", "text")
doc.recompute()
print([sheet.get(c) for c in ("A1", "A2", "A3")])
print([hasattr(sheet, n) for n in ("importFile", "exportFile")])    # file import and export exist
```
