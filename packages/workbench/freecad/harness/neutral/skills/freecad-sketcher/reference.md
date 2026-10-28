# Reference: Sketcher examples

Each code block is self-contained and was run headless with `freecadcmd` on FreeCAD 1.1.4. The printed value is in the comment.

## Constraint argument forms

| Constraint | Arguments | Meaning |
|---|---|---|
| `Coincident` | `geo1, pt1, geo2, pt2` | two points coincide |
| `Horizontal`, `Vertical` | `geo` | a line is horizontal or vertical |
| `Parallel`, `Perpendicular`, `Tangent`, `Equal` | `geo1, geo2` (a `Tangent` can also name points) | the relation between two elements |
| `Symmetric` | `geo1, pt1, geo2, pt2, line` | two points symmetric about a line |
| `Distance` | `geo1, pt1, geo2, pt2, value` | distance between two points |
| `DistanceX`, `DistanceY` | `geo1, pt1, geo2, pt2, value`, or `geo, value` | horizontal or vertical distance; the second form is a line's extent |
| `Radius`, `Diameter` | `geo, value` | circle or arc size |
| `Angle` | `geo1, geo2, value` | angle between two lines |
| `Block` | `geo` | lock one geometry element |

Point ids: `1` start, `2` end, `3` centre. Index `-1` is the origin or X axis, `-2` the Y axis, and `-3` downward the external geometry.

## A rectangle in a Body, fully constrained

```python
import FreeCAD as App
import Part
import Sketcher

V = App.Vector
doc = App.newDocument("Rect")
body = doc.addObject("PartDesign::Body", "Body")
xy = next(o for o in body.Origin.OriginFeatures if o.Role == "XY_Plane")
sk = body.newObject("Sketcher::SketchObject", "Sketch")
sk.AttachmentSupport = [(xy, "")]
sk.MapMode = "FlatFace"

pts = [(0, 0), (30, 0), (30, 20), (0, 20)]
for i in range(4):
    a, b = pts[i], pts[(i + 1) % 4]
    sk.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))
for i in range(4):
    sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
print(sk.solve(), sk.DoF, sk.FullyConstrained)               # 0 8 False

sk.addConstraint(Sketcher.Constraint("Horizontal", 0))
sk.addConstraint(Sketcher.Constraint("Horizontal", 2))
sk.addConstraint(Sketcher.Constraint("Vertical", 1))
sk.addConstraint(Sketcher.Constraint("Vertical", 3))
sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 30.0))
sk.addConstraint(Sketcher.Constraint("DistanceY", 1, 1, 1, 2, 20.0))
sk.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))   # corner on the origin
print(sk.solve(), sk.DoF, sk.FullyConstrained)               # 0 0 True
print(sk.ConflictingConstraints, sk.RedundantConstraints, sk.MalformedConstraints)   # [] [] []
```

## Conflicts and redundancy

```python
import FreeCAD as App
import Part
import Sketcher

doc = App.newDocument("Conflict")
sk = doc.addObject("Sketcher::SketchObject", "Sketch")
sk.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(10, 0, 0)))
sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 10.0))
sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 12.0))   # contradicts the first
result = sk.solve()
print(result < 0, sk.ConflictingConstraints, sk.RedundantConstraints)
```

## Naming a constraint and driving it

```python
import FreeCAD as App
import Part
import Sketcher

doc = App.newDocument("Named")
varset = doc.addObject("App::VarSet", "VarSet")
varset.addProperty("App::PropertyLength", "BaseLength", "Dimensions", "Base length")
varset.BaseLength = 40.0
sk = doc.addObject("Sketcher::SketchObject", "Sketch")
sk.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(10, 0, 0)))
sk.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))
sk.addConstraint(Sketcher.Constraint("Horizontal", 0))
index = sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 10.0))
sk.renameConstraint(index, "len")
sk.setExpression("Constraints.len", "VarSet.BaseLength")
doc.recompute()
print(sk.Constraints[index].Value)                                 # 40.0
varset.BaseLength = 55.0
doc.recompute()
print(sk.Constraints[index].Value)                                 # 55.0
```

## Names that fail

```python
import FreeCAD as App
import Part
import Sketcher

doc = App.newDocument("Names")
sk = doc.addObject("Sketcher::SketchObject", "Sketch")
sk.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(10, 0, 0)))
sk.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))
sk.addConstraint(Sketcher.Constraint("Horizontal", 0))
index = sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 10.0))
for name in ("h", "m", "s", "l", "t", "g", "in", "mm", "N", "V", "width", "len", "w", "r"):
    sk.renameConstraint(index, name)
    try:
        sk.setExpression("Constraints." + name, "10 mm")
        print(name, "ok")
    except Exception as error:
        print(name, "fails:", str(error)[:50])
```

## Construction, tangent and spline geometry

```python
import math
import FreeCAD as App
import Part
import Sketcher

V = App.Vector
doc = App.newDocument("More")
sk = doc.addObject("Sketcher::SketchObject", "Sketch")

ref = sk.addGeometry(Part.LineSegment(V(0, 0, 0), V(10, 0, 0)), True)    # construction
print(sk.getConstruction(ref))                                           # True

arc_sk = doc.addObject("Sketcher::SketchObject", "Tangent")
arc = arc_sk.addGeometry(Part.ArcOfCircle(Part.Circle(V(0, 0, 0), V(0, 0, 1), 5), 0, math.pi / 2))
line = arc_sk.addGeometry(Part.LineSegment(V(5, 0, 0), V(5, -10, 0)))
arc_sk.addConstraint(Sketcher.Constraint("Tangent", arc, 1, line, 1))   # implies the coincidence
arc_sk.addConstraint(Sketcher.Constraint("Radius", arc, 5.0))
arc_sk.addConstraint(Sketcher.Constraint("Coincident", arc, 3, -1, 1))  # arc centre on the origin
print(arc_sk.solve(), arc_sk.DoF, arc_sk.RedundantConstraints, arc_sk.ConflictingConstraints)   # 0 3 [] []

spline_sk = doc.addObject("Sketcher::SketchObject", "Spline")
spline = Part.BSplineCurve()
spline.interpolate([V(0, 0, 0), V(5, 5, 0), V(10, 0, 0), V(15, 5, 0)])
spline_sk.addGeometry(spline)
print(spline_sk.solve())                                                 # 0
```

## A Coincident beside an end-point Tangent

```python
import math
import FreeCAD as App
import Part
import Sketcher

V = App.Vector
doc = App.newDocument("Redundant")
sk = doc.addObject("Sketcher::SketchObject", "Sketch")
arc = sk.addGeometry(Part.ArcOfCircle(Part.Circle(V(0, 0, 0), V(0, 0, 1), 5), 0, math.pi / 2))
line = sk.addGeometry(Part.LineSegment(V(5, 0, 0), V(5, -10, 0)))
sk.addConstraint(Sketcher.Constraint("Tangent", arc, 1, line, 1))
print(sk.solve(), sk.RedundantConstraints)                        # 0 []
sk.addConstraint(Sketcher.Constraint("Coincident", arc, 1, line, 1))
print(sk.solve(), sk.RedundantConstraints)                        # -2 [2]: the extra constraint is reported
```

## External geometry

```python
import FreeCAD as App
import Part
import Sketcher

V = App.Vector
doc = App.newDocument("External")
body = doc.addObject("PartDesign::Body", "Body")
xy = next(o for o in body.Origin.OriginFeatures if o.Role == "XY_Plane")

base = body.newObject("Sketcher::SketchObject", "BaseRect")
base.AttachmentSupport = [(xy, "")]
base.MapMode = "FlatFace"
for a, b in (((0, 0), (20, 0)), ((20, 0), (20, 20)), ((20, 20), (0, 20)), ((0, 20), (0, 0))):
    base.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))
doc.recompute()                                       # the edge must exist before it is referenced

uses = body.newObject("Sketcher::SketchObject", "UsesExternal")
uses.AttachmentSupport = [(xy, "")]
uses.MapMode = "FlatFace"
uses.addExternal("BaseRect", "Edge1")
uses.addExternal(body.Origin.Name, "X_Axis")          # this Body's own origin
line = uses.addGeometry(Part.LineSegment(V(0, 5, 0), V(10, 5, 0)))
uses.addConstraint(Sketcher.Constraint("Parallel", line, -3))   # the first external edge is -3
print(len(uses.ExternalGeometry), uses.solve())                 # 2 0
```

An edge of a PartDesign feature is also accepted (it printed `accepted 1`), though feature edge names change with the model:

```python
import FreeCAD as App
import Part
import Sketcher

V = App.Vector
doc = App.newDocument("NoFeature")
body = doc.addObject("PartDesign::Body", "Body")
xy = next(o for o in body.Origin.OriginFeatures if o.Role == "XY_Plane")
base = body.newObject("Sketcher::SketchObject", "Base")
base.AttachmentSupport = [(xy, "")]
base.MapMode = "FlatFace"
for a, b in (((0, 0), (20, 0)), ((20, 0), (20, 20)), ((20, 20), (0, 20)), ((0, 20), (0, 0))):
    base.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))
for i in range(4):
    base.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
pad = body.newObject("PartDesign::Pad", "Pad")
pad.Profile = base
pad.Length = 5
doc.recompute()
other = body.newObject("Sketcher::SketchObject", "Other")
other.AttachmentSupport = [(xy, "")]
other.MapMode = "FlatFace"
try:
    other.addExternal("Pad", "Edge1")
    print("accepted", len(other.ExternalGeometry))
except Exception as error:
    print("refused:", str(error)[:60])
```
