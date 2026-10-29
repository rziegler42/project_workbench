# Reference: Surface examples

Each block is self-contained and was run headless with `freecadcmd` on FreeCAD 1.1.4. The printed value is in the comment. A Surface object is created with `doc.addObject("Surface::...", name)`; its inputs are links to other objects, written as `(object, "Edge1")` for one sub-element or `(object, ["Edge1", "Edge2"])` for several.

## The types and the module

```python
import FreeCAD as App
import Surface

doc = App.newDocument("d")
types = [t for t in doc.supportedTypes() if t.startswith("Surface::")]
print(len(types), types)                                                                      # 7 ['Surface::Filling', 'Surface::Sewing', 'Surface::Cut', 'Surface::GeomFillSurface', 'Surface::Extend', 'Surface::FeatureBlendCurve', 'Surface::Sections']
print([n for n in dir(Surface) if not n.startswith("_")])                                   # ['BlendCurve', 'BlendPoint']
try:
    doc.addObject("Surface::CurveOnMesh", "C")
    print("CurveOnMesh created")
except Exception as error:
    print("CurveOnMesh", type(error).__name__, error)       # CurveOnMesh TypeError Document::addObject: 'Surface::CurveOnMesh' is not a document object type
```

## A surface from four edges

```python
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("d")


def part(shape, name):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    return o


bent = part(Part.makePolygon([V(0, 0, 0), V(10, 0, 0), V(10, 10, 5), V(0, 10, 0), V(0, 0, 0)]), "Bent")
s = doc.addObject("Surface::GeomFillSurface", "S")
s.BoundaryList = [(bent, "Edge%d" % (i + 1)) for i in range(4)]
print(s.getEnumerationsOfProperty("FillType"), s.FillType)                                    # ['Stretched', 'Coons', 'Curved'] Stretched
for fill in ("Stretched", "Curved"):
    s.FillType = fill
    doc.recompute()
    sh = s.Shape
    print(fill, s.State, sh.ShapeType, sh.isValid(), round(sh.Area, 3))
# Stretched ['Up-to-date'] Face True 107.904
# Curved ['Up-to-date'] Face True 107.904
print(s.ReversedList)                                                                         # (False,)
```

## Edges from separate objects, in any order

```python
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("d")


def part(shape, name):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    return o


pts = [V(0, 0, 0), V(10, 0, 0), V(10, 10, 0), V(0, 10, 0)]
edges = [part(Part.makeLine(pts[i], pts[(i + 1) % 4]), "E%d" % i) for i in range(4)]
for label, order in (("in order", edges), ("shuffled", [edges[0], edges[2], edges[1], edges[3]]), ("three", edges[:3])):
    s = doc.addObject("Surface::GeomFillSurface", "S")
    s.BoundaryList = [(e, "Edge1") for e in order]
    doc.recompute()
    print(label, s.State, s.Shape.isNull(), s.Shape.isValid(), round(s.Shape.Area, 3))
# in order ['Up-to-date'] False True 100.0
# shuffled ['Up-to-date'] False True 100.0
# three ['Up-to-date'] False True 100.0     with one side left out the shape was still a valid face of area 100.0
```

## The flat square with each fill type

```python
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("d")
square = doc.addObject("Part::Feature", "Square")
square.Shape = Part.makePolygon([V(0, 0, 0), V(10, 0, 0), V(10, 10, 0), V(0, 10, 0), V(0, 0, 0)])
for fill in ("Stretched", "Coons", "Curved"):
    s = doc.addObject("Surface::GeomFillSurface", "S")
    s.BoundaryList = [(square, "Edge%d" % (i + 1)) for i in range(4)]
    s.FillType = fill
    doc.recompute()
    print(fill, s.State, "null" if s.Shape.isNull() else (s.Shape.isValid(), round(s.Shape.Area, 3)))
# Stretched ['Up-to-date'] (True, 100.0)
# Coons ['Touched', 'Invalid'] null
# Curved ['Up-to-date'] (True, 100.0)
```

## Coons: only some boundaries worked

```python
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("d")


def part(shape, name):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    return o


pts = [V(0, 0, 0), V(10, 0, 0), V(10, 10, 5), V(0, 10, 0)]
lines = [part(Part.makeLine(pts[i], pts[(i + 1) % 4]), "L%d" % i) for i in range(4)]
a = part(Part.Arc(V(0, 0, 0), V(5, -1, 1), V(10, 0, 0)).toShape(), "A")
b = part(Part.Arc(V(10, 0, 0), V(11, 5, 1), V(10, 10, 0)).toShape(), "B")
c = part(Part.Arc(V(10, 10, 0), V(5, 11, 1), V(0, 10, 0)).toShape(), "C")
d = part(Part.Arc(V(0, 10, 0), V(-1, 5, 1), V(0, 0, 0)).toShape(), "D")
for label, edges in (("lines", lines), ("arcs", [a, b, c, d])):
    for fill in ("Stretched", "Coons", "Curved"):
        s = doc.addObject("Surface::GeomFillSurface", "S")
        s.BoundaryList = [(e, "Edge1") for e in edges]
        s.FillType = fill
        doc.recompute()
        print(label, fill, s.State, "null" if s.Shape.isNull() else (s.Shape.isValid(), round(s.Shape.Area, 3)))
# lines Stretched ['Up-to-date'] (True, 107.904)
# lines Coons ['Touched', 'Invalid'] null       the console printed "Curves are disjoint"
# lines Curved ['Up-to-date'] (True, 107.904)
# arcs Stretched ['Up-to-date'] (True, 133.733)
# arcs Coons ['Up-to-date'] (True, 134.422)
# arcs Curved ['Up-to-date'] (True, 128.355)
```

## Filling: a bent boundary, a circle, a point

```python
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("d")


def part(shape, name):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    return o


bent = part(Part.makePolygon([V(0, 0, 0), V(10, 0, 0), V(10, 10, 5), V(0, 10, 0), V(0, 0, 0)]), "Bent")
f = doc.addObject("Surface::Filling", "F")
f.BoundaryEdges = [(bent, ["Edge1", "Edge2", "Edge3", "Edge4"])]
doc.recompute()
print(f.State, f.Shape.ShapeType, f.Shape.isValid(), round(f.Shape.Area, 3))                  # ['Up-to-date'] Face True 107.903
print(f.Degree, f.MaximumDegree, f.MaximumSegments, f.Iterations, f.Tolerance3d)              # 3 8 9 2 0.0001

circle = part(Part.makeCircle(5), "Circle")
whole = doc.addObject("Surface::Filling", "G")
whole.BoundaryEdges = [(circle, ["Edge1"])]
doc.recompute()
print("one closed edge:", whole.Shape.isNull())                                               # one closed edge: True   (the console printed "Failed to create a face from constraints")

h1 = part(Part.makeCircle(5, V(0, 0, 0), V(0, 0, 1), 0, 180), "H1")
h2 = part(Part.makeCircle(5, V(0, 0, 0), V(0, 0, 1), 180, 360), "H2")
halves = doc.addObject("Surface::Filling", "H")
halves.BoundaryEdges = [(h1, ["Edge1"]), (h2, ["Edge1"])]
doc.recompute()
print("two half circles:", halves.Shape.isValid(), round(halves.Shape.Area, 3), round(3.14159265 * 25, 3))   # two half circles: True 78.54 78.54

pt = part(Part.Vertex(V(0, 0, 3)), "Pt")
lifted = doc.addObject("Surface::Filling", "K")
lifted.BoundaryEdges = [(h1, ["Edge1"]), (h2, ["Edge1"])]
lifted.Points = [(pt, ["Vertex1"])]
doc.recompute()
print(lifted.Shape.isValid(), round(lifted.Shape.Area, 3), lifted.Shape.distToShape(Part.Vertex(V(0, 0, 3)))[0] < 1e-4)   # True 102.225 True
```

## Filling: the boundary order

```python
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("d")
bent = doc.addObject("Part::Feature", "Bent")
bent.Shape = Part.makePolygon([V(0, 0, 0), V(10, 0, 0), V(10, 10, 5), V(0, 10, 0), V(0, 0, 0)])
f = doc.addObject("Surface::Filling", "F")
f.BoundaryEdges = [(bent, ["Edge1", "Edge2", "Edge3", "Edge4"])]
doc.recompute()
print(f.BoundaryOrder)                                                                        # []
f.BoundaryOrder = [0, 0, 0, 0]
doc.recompute()
print(f.State)                                                                                # ['Up-to-date']
f.BoundaryOrder = [1, 1, 1, 1]                        # one order per edge; 1 asks for a tangent match that edges cannot give
doc.recompute()
print(f.State)                                                                                # ['Touched', 'Invalid']
f.Tolerance3d = 0.001
f.MaximumDegree = 5
f.BoundaryOrder = []
doc.recompute()
face = f.Shape.Faces[0]
print(f.State, face.Surface.UDegree, face.Surface.VDegree, round(f.Shape.Area, 3))            # ['Up-to-date'] 5 5 107.903
```

## Surface through sections

```python
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("d")


def part(shape, name):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    return o


a = part(Part.makeLine(V(0, 0, 0), V(10, 0, 0)), "A")
b = part(Part.makeLine(V(0, 5, 2), V(10, 5, 2)), "B")
c = part(Part.makeLine(V(0, 10, 0), V(10, 10, 0)), "C")
for label, order in (("in order", (a, b, c)), ("reversed", (c, b, a)), ("out of order", (a, c, b))):
    s = doc.addObject("Surface::Sections", "S")
    s.NSections = [(o, "Edge1") for o in order]
    doc.recompute()
    print(label, s.State, s.Shape.isValid(), round(s.Shape.Area, 3))
# in order ['Up-to-date'] True 109.823
# reversed ['Up-to-date'] True 109.823
# out of order ['Up-to-date'] True 158.77       valid, but a different and unwanted surface

arc1 = part(Part.makeCircle(5, V(0, 0, 0), V(0, 0, 1), 0, 180), "Arc1")
arc2 = part(Part.makeCircle(8, V(0, 0, 6), V(0, 0, 1), 0, 180), "Arc2")
loft = doc.addObject("Surface::Sections", "L")
loft.NSections = [(arc1, "Edge1"), (arc2, "Edge1")]
doc.recompute()
print(loft.State, loft.Shape.ShapeType, loft.Shape.isValid(), round(loft.Shape.Area, 3))      # ['Up-to-date'] Face True 136.984
```

## Extend a surface

```python
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("d")
base = doc.addObject("Part::Feature", "Base")
base.Shape = Part.makePlane(10, 10)
e = doc.addObject("Surface::Extend", "E")
e.Face = (base, ["Face1"])
print(e.ExtendUPos, e.ExtendUNeg, e.ExtendVPos, e.ExtendVNeg, e.ExtendUSymetric, e.ExtendVSymetric)    # 0.05 0.05 0.05 0.05 True True
e.ExtendUSymetric = False                             # the flags default to True, which extends both sides together
e.ExtendVSymetric = False
for prop in ("ExtendUPos", "ExtendUNeg", "ExtendVPos", "ExtendVNeg"):
    setattr(e, prop, 0.0)
doc.recompute()
print(round(e.Shape.Area, 3))                                                                 # 100.0
e.ExtendUPos = 0.5                                    # a fraction of the parameter range, here 10
e.ExtendUNeg = 0.1
doc.recompute()
bb = e.Shape.BoundBox
print(round(e.Shape.Area, 3), round(bb.XMin, 3), round(bb.XMax, 3))                           # 160.0 -1.0 15.0
print(e.SampleU, e.SampleV, e.Tolerance)                                                      # 32 32 0.1
```

```python
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("d")
bent = doc.addObject("Part::Feature", "Bent")
bent.Shape = Part.makePolygon([V(0, 0, 0), V(10, 0, 0), V(10, 10, 5), V(0, 10, 0), V(0, 0, 0)])
s = doc.addObject("Surface::GeomFillSurface", "S")
s.BoundaryList = [(bent, "Edge%d" % (i + 1)) for i in range(4)]
doc.recompute()
e = doc.addObject("Surface::Extend", "E")
e.Face = (s, ["Face1"])
e.ExtendUSymetric = False
e.ExtendVSymetric = False
for prop in ("ExtendUPos", "ExtendUNeg", "ExtendVPos", "ExtendVNeg"):
    setattr(e, prop, 0.0)
e.ExtendUPos = 0.5
doc.recompute()
print(e.State, e.Shape.isValid(), round(e.Shape.Area, 3), round(s.Shape.Area, 3))             # ['Up-to-date'] True 168.667 107.904
print(e.Shape.Faces[0].ParameterRange)                                                        # (0.0, 1.0, 0.0, 1.0)   the extended face is reparametrised
```

## Sewing and cutting

```python
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("d")


def part(shape, name):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    return o


a = part(Part.makePlane(10, 10), "A")
b = part(Part.makePlane(10, 10, V(10, 0, 0)), "B")
c = part(Part.makePlane(10, 10, V(30, 0, 0)), "C")
for label, other in (("touching", b), ("apart", c)):
    sew = doc.addObject("Surface::Sewing", "Sew")
    sew.ShapeList = [(a, ["Face1"]), (other, ["Face1"])]
    doc.recompute()
    sh = sew.Shape
    print(label, sew.State, sh.ShapeType, sh.isValid(), round(sh.Area, 3), len(sh.Faces))
# touching ['Up-to-date'] Shell True 200.0 2
# apart ['Up-to-date'] Compound True 200.0 2
print(sew.Tolerance, sew.SewingOption, sew.CutFreeEdges, sew.DegenerateShape, sew.Nonmanifold)    # 1e-07 True True True False

plane = part(Part.makePlane(20, 20), "Plane")
hole = part(Part.makePlane(6, 6, V(5, 5, 0)), "Hole")
cut = doc.addObject("Surface::Cut", "Cut")
cut.ShapeList = [(plane, ["Face1"]), (hole, ["Face1"])]       # a face and a face
doc.recompute()
print(cut.State, cut.Shape.ShapeType, cut.Shape.isValid(), round(cut.Shape.Area, 3))          # ['Up-to-date'] Shell True 364.0
```

## Cut with a solid or a shell

```python
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("d")


def part(shape, name):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    return o


plane = part(Part.makePlane(20, 20), "Plane")
box = part(Part.makeBox(6, 6, 6, V(5, 5, -3)), "Box")
shell = part(Part.makeBox(6, 6, 6, V(5, 5, -3)).Shells[0], "Shell")
for label, other, sub in (("solid", box, "Solid1"), ("shell", shell, "Shell1"), ("box face", box, "Face1")):
    cut = doc.addObject("Surface::Cut", "Cut")
    cut.ShapeList = [(plane, ["Face1"]), (other, [sub])]
    doc.recompute()
    print(label, cut.State, "null" if cut.Shape.isNull() else (cut.Shape.ShapeType, round(cut.Shape.Area, 3)))
# solid ['Up-to-date'] ('Shell', 364.0)
# shell ['Up-to-date'] ('Shell', 400.0)       no error, and the plane is unchanged
# box face ['Up-to-date'] ('Shell', 364.0)
```

## Checking a result

```python
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("d")
a = doc.addObject("Part::Feature", "A")
a.Shape = Part.makeLine(V(0, 0, 0), V(10, 0, 0))
b = doc.addObject("Part::Feature", "B")
b.Shape = Part.makeLine(V(0, 5, 2), V(10, 5, 2))
c = doc.addObject("Part::Feature", "C")
c.Shape = Part.makeLine(V(0, 10, 0), V(10, 10, 0))
s = doc.addObject("Surface::Sections", "S")
s.NSections = [(a, "Edge1"), (b, "Edge1"), (c, "Edge1")]
doc.recompute()
face = s.Shape.Faces[0]
print(s.Shape.isNull(), face.Surface.__class__.__name__, face.isValid(), round(face.Area, 3))   # False BSplineSurface True 109.823
u0, u1, v0, v1 = face.ParameterRange
zs = [face.valueAt(u0 + (u1 - u0) * i / 20.0, v0 + (v1 - v0) * j / 20.0).z for i in range(21) for j in range(21)]
print(round(min(zs), 3), round(max(zs), 3))                                                   # 0.0 2.0
print(s.Shape.BoundBox.ZMax, face.optimalBoundingBox().ZMax)                                  # 4.0 2.0000001   the plain BoundBox is larger than the surface
print(round(face.distToShape(a.Shape)[0], 6), round(face.distToShape(c.Shape)[0], 6))         # 0.0 0.0   the boundary edges lie on the surface
```
