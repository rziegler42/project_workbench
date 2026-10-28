# Reference: PartDesign examples

Every example below was run headless with `freecadcmd` on FreeCAD 1.1.4, and the printed value is in the comment. The
examples after "Helpers" use the helper functions defined there, so run the helpers first in the same session. Each
example starts its own document.

## Helpers

```python
import math
import FreeCAD as App
import Part
import Sketcher

V = App.Vector


def new_body(doc, name):
    body = doc.addObject("PartDesign::Body", name)
    return body, {o.Role: o for o in body.Origin.OriginFeatures}   # XY_Plane, XZ_Plane, YZ_Plane, X_Axis, ...


def sketch(body, name, support, sub="", offset=None):
    sk = body.newObject("Sketcher::SketchObject", name)
    sk.AttachmentSupport = [(support, sub)]
    sk.MapMode = "FlatFace"
    if offset:
        sk.AttachmentOffset = offset
    return sk


def rect(sk, w, d, x0=0, y0=0):
    pts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + d), (x0, y0 + d)]
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        sk.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))


def box_body(doc, name, w=20, d=20, h=10):
    body, o = new_body(doc, name)
    sk = sketch(body, "Base", o["XY_Plane"])
    rect(sk, w, d)
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = sk
    pad.Length = h
    doc.recompute()
    return body, o, pad


def edge_names(shape, test):
    return ["Edge%d" % (i + 1) for i, e in enumerate(shape.Edges) if test(e)]


def face_names(shape, test):
    return ["Face%d" % (i + 1) for i, f in enumerate(shape.Faces) if test(f)]
```

## A Pad, and what a Body holds

```python
doc = App.newDocument("Pad")
body, o, pad = box_body(doc, "Body")
print(round(pad.Shape.Volume, 1), pad.State)           # 4000.0 ['Up-to-date']
print([x.Name for x in body.Group], body.Tip.Name)     # ['Base', 'Pad'] Pad
```

## Features made inside and outside a Body

```python
doc = App.newDocument("Outside")
body, o, pad = box_body(doc, "Body")
loose = doc.addObject("PartDesign::Pad", "Loose")      # made with addObject, not body.newObject
loose.Profile = pad.Profile
loose.Length = 3
doc.recompute()
print(pad.getParentGeoFeatureGroup().Name)             # Body
print(loose.getParentGeoFeatureGroup())                # None: it belongs to no Body
print([x.Name for x in body.Group], body.Tip.Name)     # ['Base', 'Pad'] Pad: the loose Pad is not in the Body
print(loose.State)                                     # the console also says its links are out of scope
```

## A Pocket and a Hole

```python
doc = App.newDocument("Cut")
body, o, pad = box_body(doc, "Body")
top = face_names(pad.Shape, lambda f: abs(f.CenterOfMass.z - 10) < 1e-6 and f.normalAt(0, 0).z > 0.9)[0]

hole_sketch = sketch(body, "HoleSketch", pad, top)
hole_sketch.addGeometry(Part.Circle(V(10, 10, 0), V(0, 0, 1), 2))
doc.recompute()
hole = body.newObject("PartDesign::Hole", "Hole")
hole.Profile = hole_sketch
hole.Diameter = 4
hole.DepthType = "ThroughAll"
doc.recompute()
print(round(hole.Shape.Volume, 2), round(4000 - math.pi * 4 * 10, 2))          # 3874.34 3874.34

pocket_sketch = sketch(body, "PocketSketch", o["XY_Plane"], offset=App.Placement(V(0, 0, 10), App.Rotation()))
pocket_sketch.addGeometry(Part.Circle(V(4, 4, 0), V(0, 0, 1), 1.5))
pocket = body.newObject("PartDesign::Pocket", "Pocket")
pocket.Profile = pocket_sketch
pocket.Type = 1                                                                # 1 = ThroughAll
doc.recompute()
print(round(pocket.Shape.Volume, 2), round(4000 - math.pi * 4 * 10 - math.pi * 2.25 * 10, 2))
```

## Fillet, chamfer and thickness name edges and faces from geometry

```python
doc = App.newDocument("Dress")
body, o, pad = box_body(doc, "Body")
top_edges = edge_names(pad.Shape, lambda e: all(abs(v.Point.z - 10) < 1e-6 for v in e.Vertexes))
print(top_edges)                                                               # the four top edges

fillet = body.newObject("PartDesign::Fillet", "Fillet")
fillet.Base = (pad, top_edges)                                                 # (feature, [edge names])
fillet.Radius = 1
doc.recompute()
print(round(fillet.Shape.Volume, 2), fillet.State)                              # 3983.22 ['Up-to-date']

doc = App.newDocument("Chamfer")
body, o, pad = box_body(doc, "Body")
chamfer = body.newObject("PartDesign::Chamfer", "Chamfer")
chamfer.Base = (pad, edge_names(pad.Shape, lambda e: all(abs(v.Point.z - 10) < 1e-6 for v in e.Vertexes)))
chamfer.Size = 1
doc.recompute()
print(round(chamfer.Shape.Volume, 2))                                          # 3961.33

doc = App.newDocument("Shell")
body, o, pad = box_body(doc, "Body")
shell = body.newObject("PartDesign::Thickness", "Thickness")
shell.Base = (pad, face_names(pad.Shape, lambda f: abs(f.CenterOfMass.z - 10) < 1e-6 and f.normalAt(0, 0).z > 0.9))
shell.Value = 2
shell.Mode = 0
shell.Join = 1
doc.recompute()
print(round(shell.Shape.Volume, 1))                                            # 1952.0
```

## Patterns

```python
doc = App.newDocument("Patterns")
body, o, pad = box_body(doc, "Body")
cut_sketch = sketch(body, "CutSketch", o["XY_Plane"], offset=App.Placement(V(0, 0, 10), App.Rotation()))
cut_sketch.addGeometry(Part.Circle(V(3, 3, 0), V(0, 0, 1), 1))
pocket = body.newObject("PartDesign::Pocket", "Pocket")
pocket.Profile = cut_sketch
pocket.Type = 1
lp = body.newObject("PartDesign::LinearPattern", "LinearPattern")
lp.Originals = [pocket]
lp.Direction = (o["X_Axis"], [""])
lp.Length = 10
lp.Occurrences = 3
body.Tip = lp                                       # a pattern does not become the Tip by itself
doc.recompute()
print(round(body.Shape.Volume, 2), round(4000 - 3 * math.pi * 10, 2))        # 3905.75 3905.75

doc = App.newDocument("Polar")
body, o = new_body(doc, "Body")
peg = sketch(body, "Peg", o["XY_Plane"])
peg.addGeometry(Part.Circle(V(10, 0, 0), V(0, 0, 1), 2))
pad = body.newObject("PartDesign::Pad", "Pad")
pad.Profile = peg
pad.Length = 5
polar = body.newObject("PartDesign::PolarPattern", "PolarPattern")
polar.Originals = [pad]
polar.Axis = (o["Z_Axis"], [""])
polar.Angle = 360
polar.Occurrences = 4
body.Tip = polar
doc.recompute()
print(round(body.Shape.Volume, 1))                                             # 251.3 (four 4*pi*5 pegs)
```

## Mirrored and MultiTransform

```python
doc = App.newDocument("Mirror")
body, o, pad = box_body(doc, "Body")
hole_sketch = sketch(body, "HoleSketch", o["XY_Plane"], offset=App.Placement(V(0, 0, 10), App.Rotation()))
hole_sketch.addGeometry(Part.Circle(V(5, 5, 0), V(0, 0, 1), 2))
pocket = body.newObject("PartDesign::Pocket", "Pocket")
pocket.Profile = hole_sketch
pocket.Type = 1
mid = body.newObject("PartDesign::Plane", "MidPlane")        # a plane through the middle of the part (x = 10)
mid.AttachmentSupport = [(o["YZ_Plane"], "")]
mid.MapMode = "FlatFace"
mid.AttachmentOffset = App.Placement(V(0, 0, 10), App.Rotation())
doc.recompute()
mirrored = body.newObject("PartDesign::Mirrored", "Mirrored")
mirrored.Originals = [pocket]
mirrored.MirrorPlane = (mid, [""])
body.Tip = mirrored
doc.recompute()
print(round(body.Shape.Volume, 2), round(4000 - 2 * math.pi * 4 * 10, 2))    # 3748.67 3748.67

doc = App.newDocument("Multi")
body, o, pad = box_body(doc, "Body")
hole_sketch = sketch(body, "HoleSketch", o["XY_Plane"], offset=App.Placement(V(0, 0, 10), App.Rotation()))
hole_sketch.addGeometry(Part.Circle(V(3, 3, 0), V(0, 0, 1), 1))
pocket = body.newObject("PartDesign::Pocket", "Pocket")
pocket.Profile = hole_sketch
pocket.Type = 1
multi = body.newObject("PartDesign::MultiTransform", "Multi")
multi.Originals = [pocket]
row = body.newObject("PartDesign::LinearPattern", "Row")     # the transformations are separate objects
row.Direction = (o["X_Axis"], [""])
row.Length = 10
row.Occurrences = 3
multi.Transformations = [row]
body.Tip = multi
doc.recompute()
print(round(body.Shape.Volume, 2), round(4000 - 3 * math.pi * 10, 2))        # 3905.75 3905.75
```

## Revolution, pipe and loft

```python
doc = App.newDocument("Rev")
body, o = new_body(doc, "Body")
profile = sketch(body, "Profile", o["XZ_Plane"])
for a, c in [((0, 0), (10, 0)), ((10, 0), (10, 20)), ((10, 20), (0, 20)), ((0, 20), (0, 0))]:
    profile.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(c[0], c[1], 0)))
for i in range(4):
    profile.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
rev = body.newObject("PartDesign::Revolution", "Revolution")
rev.Profile = profile
rev.ReferenceAxis = (profile, ["V_Axis"])           # the sketch's own vertical axis
rev.Angle = 360
doc.recompute()
print(round(rev.Shape.Volume, 1), round(math.pi * 100 * 20, 1))              # 6283.2 6283.2

doc = App.newDocument("Pipe")
body, o = new_body(doc, "Body")
path = sketch(body, "Path", o["XZ_Plane"])                                    # sketch Y runs along world Z here
path.addGeometry(Part.LineSegment(V(0, 0, 0), V(0, 30, 0)))
prof = sketch(body, "Prof", o["XY_Plane"])
prof.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 3))
pipe = body.newObject("PartDesign::AdditivePipe", "Pipe")
pipe.Profile = prof
pipe.Spine = (path, ["Edge1"])                      # the path sketch and the edge to follow
doc.recompute()
print(round(pipe.Shape.Volume, 1), round(math.pi * 9 * 30, 1))               # 848.2 848.2

doc = App.newDocument("ArcPipe")
body, o = new_body(doc, "Body")
path = sketch(body, "Path", o["XZ_Plane"])
path.addGeometry(Part.ArcOfCircle(Part.Circle(V(20, 0, 0), V(0, 0, 1), 20), math.pi / 2, math.pi))
prof = sketch(body, "Prof", o["XY_Plane"])
prof.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 2))
arc_pipe = body.newObject("PartDesign::AdditivePipe", "Pipe")
arc_pipe.Profile = prof
arc_pipe.Spine = (path, ["Edge1"])
doc.recompute()
print(round(arc_pipe.Shape.Volume, 1), arc_pipe.Shape.isValid())             # 394.8 True

doc = App.newDocument("Loft")
body, o = new_body(doc, "Body")
s1 = sketch(body, "L1", o["XY_Plane"])
s1.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 10))
s2 = sketch(body, "L2", o["XY_Plane"], offset=App.Placement(V(0, 0, 20), App.Rotation()))
s2.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 5))
loft = body.newObject("PartDesign::AdditiveLoft", "Loft")
loft.Profile = s1
loft.Sections = [s2]
doc.recompute()
print(round(loft.Shape.Volume, 1))                                             # 3665.2
```

## A datum plane

```python
doc = App.newDocument("Datum")
body, o, pad = box_body(doc, "Body")
datum = body.newObject("PartDesign::Plane", "DatumPlane")
datum.AttachmentSupport = [(o["XY_Plane"], "")]
datum.MapMode = "FlatFace"
datum.AttachmentOffset = App.Placement(V(0, 0, 5), App.Rotation())
doc.recompute()
on_datum = sketch(body, "OnDatum", datum)
on_datum.addGeometry(Part.Circle(V(10, 10, 0), V(0, 0, 1), 3))
doc.recompute()
print(on_datum.Placement.Base.z)                                               # 5.0
```

## Several Bodies

```python
doc = App.newDocument("Bodies")
body_a, oa, pad_a = box_body(doc, "BodyA")                                    # 20 x 20 x 10 = 4000
body_b, ob = new_body(doc, "BodyB")
sk_b = sketch(body_b, "Base", ob["XY_Plane"])
rect(sk_b, 10, 10, 5, 5)
pad_b = body_b.newObject("PartDesign::Pad", "Pad")
pad_b.Profile = sk_b
pad_b.Length = 20
doc.recompute()

binder = body_a.newObject("PartDesign::SubShapeBinder", "Binder")            # brings in a shape; cuts nothing
binder.Support = [(body_b, [""])]
doc.recompute()
print(round(binder.Shape.Volume, 1))                                          # 2000.0 (BodyB's volume)

cut = body_a.newObject("PartDesign::Boolean", "Boolean")
cut.Type = "Cut"                                                              # "Fuse", "Cut" or "Common"
cut.addObject(body_b)
doc.recompute()
print(round(body_a.Shape.Volume, 1))                                          # 3000.0 = 4000 - 10*10*10
```

## When a feature does not build

```python
doc = App.newDocument("Failing")
body, o = new_body(doc, "Body")
open_sketch = sketch(body, "Open", o["XY_Plane"])
open_sketch.addGeometry(Part.LineSegment(V(0, 0, 0), V(10, 0, 0)))
open_sketch.addGeometry(Part.LineSegment(V(10, 0, 0), V(10, 10, 0)))        # a profile that is not closed
pad = body.newObject("PartDesign::Pad", "Pad")
pad.Profile = open_sketch
pad.Length = 5
doc.recompute()
print(pad.State)                                                              # a failed feature says so in State
print(pad.isValid())
```
