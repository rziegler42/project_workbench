# Reference: measure and inspect examples

Every example below was run headless with `freecadcmd` on FreeCAD 1.1.4, and the printed value is in the comment.

## What a shape reports about itself

```python
import FreeCAD as App
import Part

V = App.Vector
result = Part.makeBox(10, 20, 30).cut(Part.makeCylinder(4, 40, V(5, 10, -5)))
print(result.ShapeType, hasattr(result, "CenterOfMass"))           # Compound False: a Boolean returns a Compound
solid = result.Solids[0]                                            # take the Solid out of it
bb = solid.BoundBox
print(solid.ShapeType, solid.isValid(), solid.isClosed())
print(round(solid.Volume, 2), round(solid.Area, 2), solid.CenterOfMass)
print(bb.XLength, bb.YLength, bb.ZLength, bb.Center)

shell = Part.Shell(Part.makeBox(10, 10, 10).Faces[:5])            # a box with one face missing
print(shell.ShapeType, shell.isValid(), shell.isClosed())         # Shell True False

outer = Part.Wire([Part.makeLine((0, 0, 0), (10, 0, 0)), Part.makeLine((10, 0, 0), (10, 10, 0)),
                   Part.makeLine((10, 10, 0), (0, 10, 0)), Part.makeLine((0, 10, 0), (0, 0, 0))])
hole = Part.Wire(Part.makeCircle(2, V(5, 5, 0)))
broken = Part.Face([outer, hole])                                  # an inner wire in the same direction
print(broken.isValid(), round(broken.Area, 3))
try:
    broken.check(True)
    print("check passed")
except Exception as error:
    print("check raised:", str(error)[:80])
```

## Distances between shapes and points

```python
import FreeCAD as App
import Part

V = App.Vector
a = Part.makeBox(10, 10, 10)
b = Part.makeBox(10, 10, 10, V(25, 0, 0))
distance, pairs, info = a.distToShape(b)
print(distance, [(tuple(p), tuple(q)) for p, q in pairs][:1])      # 15.0 and a closest pair of points

touching = Part.makeBox(10, 10, 10, V(10, 0, 0))
overlapping = Part.makeBox(10, 10, 10, V(5, 0, 0))
print(a.distToShape(touching)[0], a.distToShape(overlapping)[0])    # both 0.0

point = Part.Vertex(V(5, 5, 30))
print(a.distToShape(point)[0])                                      # 20.0: from the top face
inside = Part.Vertex(V(5, 5, 5))
print(a.distToShape(inside)[0], a.isInside(V(5, 5, 5), 1e-6, True))  # a point inside: distance 0.0, isInside True
```

## Compare with a number you can compute

```python
import math

import FreeCAD as App
import MeshPart
import Part


def check(label, measured, expected, tolerance):
    error = abs(measured - expected) / expected
    print("%-22s measured %9.2f expected %9.2f error %.4f %s" % (
        label, measured, expected, error, "ok" if error <= tolerance else "OUT OF TOLERANCE"))


cylinder = Part.makeCylinder(10, 20)
check("cylinder volume", cylinder.Volume, math.pi * 100 * 20, 1e-6)
check("cylinder area", cylinder.Area, 2 * math.pi * 10 * 20 + 2 * math.pi * 100, 1e-6)
mesh = MeshPart.meshFromShape(Shape=cylinder, LinearDeflection=0.05, AngularDeflection=0.3)
check("mesh volume", mesh.Volume, cylinder.Volume, 0.01)           # a mesh is a little smaller than its shape
check("coarse mesh volume", MeshPart.meshFromShape(Shape=cylinder, LinearDeflection=1.0,
                                                   AngularDeflection=0.5).Volume, cylinder.Volume, 0.01)
```

## Deviation of a mesh from a shape

```python
import FreeCAD as App
import MeshPart
import Part

shape = Part.makeCylinder(10, 20)
mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.3)
surface = Part.Compound(shape.Faces)                      # faces, not the solid: inside points would read as zero
step = max(1, len(mesh.Points) // 200)
distances = sorted(surface.distToShape(Part.Vertex(mesh.Points[i].Vector))[0] for i in range(0, len(mesh.Points), step))
print(len(distances), round(distances[-1], 4), round(distances[int(0.95 * len(distances))], 4))
within = sum(1 for d in distances if d <= 0.05) / len(distances)
print(within)                                              # 1.0: but see below, the vertices lie ON the surface

# The vertices of a mesh made from a shape lie on the shape, so this measures nothing about the error between them.
# The volume does show it:
print(round(mesh.Volume, 1), round(shape.Volume, 1))       # 6262.8 6283.2

inside = Part.Vertex(App.Vector(0, 0, 10))
print(shape.distToShape(inside)[0], surface.distToShape(inside)[0])         # 0.0 against the solid, 10.0 against the faces
```

## The Measure and Inspection modules

```python
import FreeCAD as App
import Inspection
import Measure
import Part

for module in (Measure, Inspection):
    print(module.__name__, [n for n in dir(module) if not n.startswith("_")])

doc = App.newDocument("Measure")
box = doc.addObject("Part::Feature", "Box")
box.Shape = Part.makeBox(10, 20, 30)
doc.recompute()
measurement = Measure.Measurement()
print([n for n in dir(measurement) if not n.startswith("_")])
```

## Measure.Measurement on a box with known answers

```python
import FreeCAD as App
import Measure
import Part

doc = App.newDocument("Measure")
box = doc.addObject("Part::Feature", "Box")
box.Shape = Part.makeBox(10, 20, 30)
cyl = doc.addObject("Part::Feature", "Cyl")
cyl.Shape = Part.makeCylinder(5, 12)
doc.recompute()


def measure(method, *references):
    m = Measure.Measurement()
    for name, sub in references:
        m.addReference3D(name, sub)              # the object's NAME as a string, not the object
    return getattr(m, method)()


print(measure("length", ("Box", "Edge1")))                              # 30.0
print(measure("area", ("Box", "Face1")))                                # 600.0
print(measure("radius", ("Cyl", "Face1")))                              # 5.0
print(measure("volume", ("Box", "")))                                   # 6000.0
print(measure("com", ("Box", "")))                                      # Vector (5.0, 10.0, 15.0)
print(measure("planePlaneDistance", ("Box", "Face1"), ("Box", "Face2")))   # 10.0
print(measure("angle", ("Box", "Edge1"), ("Box", "Edge2")))             # 90.0
try:
    m = Measure.Measurement()
    m.addReference3D(box, "Edge1")                # passing the object itself is refused
except TypeError as error:
    print("TypeError:", str(error)[:40])
```
