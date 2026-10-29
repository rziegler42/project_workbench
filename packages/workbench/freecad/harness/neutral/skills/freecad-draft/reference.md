# Reference: Draft examples

Each block is self-contained and was run headless with `freecadcmd` on FreeCAD 1.1.4. The printed value is in the comment. Every block recomputes the document before it reads a `Shape`.

## Create 2D objects

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
line = Draft.make_line(V(0, 0, 0), V(10, 0, 0))
circle = Draft.make_circle(5)
rect = Draft.make_rectangle(10, 5)
poly = Draft.make_polygon(6, radius=5)                     # a hexagon, inscribed by default
doc.recompute()
for o in (line, circle, rect, poly):
    print(o.Name, o.TypeId, o.Shape.ShapeType, round(o.Shape.Length, 3), round(o.Shape.Area, 3))
# Line Part::FeaturePython Wire 10.0 0.0
# Circle Part::Part2DObjectPython Face 31.416 78.54
# Rectangle Part::Part2DObjectPython Face 30.0 50.0
# Polygon Part::Part2DObjectPython Face 30.0 64.952
print(rect.Length, rect.Height, rect.MakeFace, poly.FacesNumber, poly.Radius, circle.Radius)    # 10.0 mm 5.0 mm True 6 5.0 mm 5.0 mm
```

## Arc, placement and point

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
arc = Draft.make_circle(5, startangle=0, endangle=90)
shifted = Draft.make_circle(5, placement=App.Placement(V(10, 0, 0), App.Rotation()))
point = Draft.make_point(1, 2, 3)
doc.recompute()
print(arc.FirstAngle, arc.LastAngle, round(arc.Shape.Length, 3), arc.Shape.ShapeType)         # 0.0 deg 90.0 deg 7.854 Edge
print(shifted.Shape.BoundBox.XMin, shifted.Shape.BoundBox.XMax)                               # 5.0 15.0
print(point.Shape.ShapeType, point.Shape.Vertexes[0].Point)                                   # Vertex Vector (1.0, 2.0, 3.0)
```

## Wires and splines

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
pts = [V(0, 0, 0), V(10, 0, 0), V(10, 5, 0)]
open_wire = Draft.make_wire(pts, closed=False)
closed_wire = Draft.make_wire(pts, closed=True)
spline = Draft.make_bspline([V(0, 0, 0), V(5, 5, 0), V(10, 0, 0)])
doc.recompute()
print(open_wire.Closed, round(open_wire.Shape.Length, 3))                                      # False 15.0
print(closed_wire.Closed, closed_wire.Shape.ShapeType, len(closed_wire.Shape.Faces))          # True Face 1
print(round(spline.Shape.Length, 3))                                                          # 14.789
```

## Face or wire, then a solid

```python
import FreeCAD as App
import Draft
import Part

V = App.Vector
doc = App.newDocument("d")
rect = Draft.make_rectangle(10, 5)
doc.recompute()
print(rect.MakeFace, rect.Shape.ShapeType, len(rect.Shape.Faces))                             # True Face 1
solid = rect.Shape.extrude(V(0, 0, 3))
print(solid.ShapeType, round(solid.Volume, 3))                                                # Solid 150.0
rect.MakeFace = False
doc.recompute()
print(rect.Shape.ShapeType, len(rect.Shape.Faces), rect.Shape.isClosed())                     # Wire 0 True
face = Part.Face(Part.Wire(rect.Shape.Edges))
print(face.ShapeType, round(face.Area, 3), round(face.extrude(V(0, 0, 3)).Volume, 3))         # Face 50.0 150.0
```

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
rect = Draft.make_rectangle(10, 5)
doc.recompute()
ex = Draft.extrude(rect, V(0, 0, 3))
doc.recompute()
print(ex.TypeId, ex.Shape.ShapeType, round(ex.Shape.Volume, 3))                               # Part::Extrusion Solid 150.0
sk = Draft.make_sketch([rect], autoconstraints=False)
doc.recompute()
print(sk.TypeId, len(sk.Geometry), sk.Shape.ShapeType)                                        # Sketcher::SketchObject 4 Wire
```

## Move, rotate and scale

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
rect = Draft.make_rectangle(10, 5)
doc.recompute()
moved = Draft.move(rect, V(10, 0, 0), copy=True)
rotated = Draft.rotate(rect, 45, V(0, 0, 0), axis=V(0, 0, 1), copy=True)
scaled = Draft.scale(rect, V(2, 2, 2), center=V(0, 0, 0), copy=True)
doc.recompute()
print(moved.Name, moved.Shape.BoundBox.XMin, moved.Shape.BoundBox.XMax)                       # Rectangle001 10.0 20.0
bb = rotated.Shape.BoundBox
print(round(bb.XMin, 3), round(bb.XMax, 3), round(bb.YMax, 3))                                # -3.536 7.071 10.607
print(scaled.Shape.BoundBox.XMax, scaled.Shape.BoundBox.YMax, round(scaled.Shape.Area, 3))    # 20.0 10.0 200.0
print([o.Name for o in doc.Objects])                                                          # ['Rectangle', 'Rectangle001', 'Rectangle002', 'Rectangle003']
```

## Move in place, and several objects

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
a = Draft.make_rectangle(2, 2)
b = Draft.make_circle(1)
doc.recompute()
same = Draft.move(a, V(0, 0, 3))                      # copy=False is the default: the object itself moves
doc.recompute()
print(same is a, a.Placement.Base, a.Shape.BoundBox.ZMin)                                     # True Vector (0.0, 0.0, 3.0) 3.0
Draft.move([a, b], V(5, 0, 0))
doc.recompute()
print(a.Placement.Base, b.Placement.Base)                                                     # Vector (5.0, 0.0, 3.0) Vector (5.0, 0.0, 0.0)
copies = Draft.move([a, b], V(0, 5, 0), copy=True)
print(type(copies).__name__, [o.Name for o in copies])                                        # list ['Rectangle001', 'Circle001']
```

## Offset

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
for label, delta in (("-y", V(0, -1, 0)), ("+y", V(0, 1, 0)), ("-y by 2", V(0, -2, 0))):
    wire = Draft.make_wire([V(0, 0, 0), V(10, 0, 0), V(10, 10, 0), V(0, 10, 0)], closed=True)
    doc.recompute()                                   # offset reads the shape, so recompute first
    off = Draft.offset(wire, delta, copy=True)
    doc.recompute()
    bb = off.Shape.BoundBox
    print(label, off.Shape.ShapeType, round(bb.XMin, 3), round(bb.XMax, 3), round(bb.YMin, 3), round(bb.YMax, 3))
# -y Face -1.0 11.0 -1.0 11.0       the first edge lies on y = 0, so -y moves outward
# +y Face 1.0 9.0 1.0 9.0           and +y moves inward
# -y by 2 Face -2.0 12.0 -2.0 12.0
```

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
wire = Draft.make_wire([V(0, 0, 0), V(10, 0, 0), V(10, 10, 0), V(0, 10, 0)], closed=True)
doc.recompute()
off = Draft.offset(wire, V(1, 0, 0), copy=True)      # parallel to the first edge: a notice is printed, and the offset goes outward
doc.recompute()
bb = off.Shape.BoundBox
print(round(bb.XMin, 3), round(bb.XMax, 3), round(bb.YMin, 3), round(bb.YMax, 3))             # -1.0 11.0 0.0 11.0   a notice "something wrong with firstDir" is printed
inplace = Draft.offset(wire, V(0, -1, 0))             # copy=False changes the object itself
doc.recompute()
print(inplace is wire, round(wire.Shape.BoundBox.XMin, 3), round(wire.Shape.BoundBox.XMax, 3))    # True -1.0 11.0
```

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
wire = Draft.make_wire([V(0, 0, 0), V(10, 0, 0), V(10, 10, 0)], closed=False)
doc.recompute()
for delta in (V(0, 1, 0), V(0, -1, 0)):
    off = Draft.offset(wire, delta, copy=True)
    doc.recompute()
    bb = off.Shape.BoundBox
    print(delta, off.Shape.ShapeType, round(off.Shape.Length, 3), round(bb.XMin, 3), round(bb.XMax, 3), round(bb.YMin, 3), round(bb.YMax, 3))
# Vector (0, 1, 0) Wire 18.0 0.0 9.0 1.0 10.0       an open wire is offset to one side and stays a Wire
# Vector (0, -1, 0) Wire 22.0 0.0 11.0 -1.0 10.0
```

## Rectangular (orthogonal) array

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
rect = Draft.make_rectangle(10, 5)
doc.recompute()
grid = Draft.make_ortho_array(rect, V(15, 0, 0), V(0, 15, 0), V(0, 0, 15), 3, 2, 1)     # x, y, z step; nx, ny, nz
doc.recompute()
print(grid.TypeId, grid.ArrayType, grid.NumberX, grid.NumberY, grid.Fuse)                     # Part::FeaturePython ortho 3 2 False
print(grid.Shape.ShapeType, len(grid.Shape.Faces), round(grid.Shape.BoundBox.XMax, 3))        # Compound 6 40.0
grid.NumberX = 5                                      # an array is parametric: change a property and recompute
doc.recompute()
print(len(grid.Shape.Faces), round(grid.Shape.BoundBox.XMax, 3))                              # 10 70.0
rect.Length = 12                                      # and it follows its base object
doc.recompute()
print(round(grid.Shape.BoundBox.XMax, 3), round(grid.Shape.Area, 3))                          # 72.0 600.0
grid.Fuse = True
doc.recompute()
print(grid.Shape.ShapeType, len(grid.Shape.Faces))                                            # Compound 10
```

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
rect = Draft.make_rectangle(10, 5)
doc.recompute()
plain = Draft.make_ortho_array(rect, V(15, 0, 0), V(0, 15, 0), V(0, 0, 15), 2, 2, 1, use_link=False)
doc.recompute()
print(plain.TypeId, plain.ArrayType, len(plain.Shape.Faces))                                  # Part::FeaturePython ortho 4
```

## Polar array

```python
import math

import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
r = Draft.make_rectangle(2, 2, placement=App.Placement(V(10, 0, 0), App.Rotation()))
doc.recompute()
for total in (360, 180):
    polar = Draft.make_polar_array(r, 4, total, V(0, 0, 0))      # base, number, angle, center
    doc.recompute()
    angles = sorted(round(math.degrees(math.atan2(f.CenterOfMass.y, f.CenterOfMass.x)) % 360, 1) for f in polar.Shape.Faces)
    print(polar.ArrayType, polar.NumberPolar, polar.Angle, angles)
# polar 4 360.0 deg [5.2, 95.2, 185.2, 275.2]     over 360 the copies are spread evenly, so none repeats the first
# polar 4 180.0 deg [5.2, 65.2, 125.2, 185.2]     over less than 360 the last copy lies at the end of the angle
```

## Circular array

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
cube = Draft.make_rectangle(2, 2)
doc.recompute()
for circles, step in ((1, 10), (2, 10), (3, 10), (2, 5)):
    arr = Draft.make_circular_array(cube, 20, step, circles, 1, V(0, 0, 1), V(0, 0, 0))   # radial step, tangential step, circles, symmetry, axis, centre
    doc.recompute()
    print(circles, step, arr.NumberCircles, arr.RadialDistance, arr.TangentialDistance, len(arr.Shape.Faces))
# 1 10 1 20.0 mm 10.0 mm 1       the number is the number of circles, not of copies
# 2 10 2 20.0 mm 10.0 mm 13
# 3 10 3 20.0 mm 10.0 mm 38
# 2 5 2 20.0 mm 5.0 mm 26       a smaller tangential step puts more copies on each circle
```

## Array along a path

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
peg = Draft.make_rectangle(1, 1)
path = Draft.make_line(V(0, 0, 0), V(30, 0, 0))
doc.recompute()
arr = Draft.make_path_array(peg, path, count=4)
doc.recompute()
print(arr.TypeId, arr.Count, len(arr.Shape.Faces), round(arr.Shape.BoundBox.XMax, 3))         # Part::FeaturePython 4 4 31.0
```

## Clone, mirror

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
rect = Draft.make_rectangle(10, 5)
doc.recompute()
clone = Draft.make_clone(rect)
mirrored = Draft.mirror(rect, V(0, 0, 0), V(0, 1, 0))       # the mirror line passes through the two points
doc.recompute()
print(clone.Shape.BoundBox.XMax, mirrored.Name, mirrored.Shape.BoundBox.XMin, mirrored.Shape.BoundBox.XMax)    # 10.0 Mirror -10.0 0.0
rect.Length = 20                                      # a clone follows its original
doc.recompute()
print(clone.Shape.BoundBox.XMax)                                                              # 20.0
```

## The names

```python
import Draft

print(Draft.make_line is Draft.makeLine, Draft.make_circle is Draft.makeCircle, Draft.make_rectangle is Draft.makeRectangle)    # True True True
print(Draft.make_polygon is Draft.makePolygon, Draft.make_wire is Draft.makeWire)             # True True
print(Draft.make_array is Draft.makeArray)                                                    # False
names = [n for n in dir(Draft) if n.startswith("make_")]
print(len(names))                                                                             # 38
```

```python
import inspect

import Draft

for name in ("make_line", "make_circle", "make_rectangle", "make_polygon", "make_wire", "make_bspline", "move", "rotate",
             "scale", "offset", "make_ortho_array", "make_polar_array", "make_circular_array", "make_path_array"):
    print(name, inspect.signature(getattr(Draft, name)))
# make_line (first_param, last_param=None)
# make_circle (radius, placement=None, face=None, startangle=None, endangle=None, support=None)
# make_rectangle (length, height=0, placement=None, face=None, support=None)
# make_polygon (nfaces, radius=1, inscribed=True, placement=None, face=None, support=None)
# make_wire (pointslist, closed=False, placement=None, face=None, support=None, bs2wire=False)
# make_bspline (pointslist, closed=False, placement=None, face=None, support=None)
# move (selection, vector, copy=False, subelements=False)
# rotate (selection, angle, center=Vector (0.0, 0.0, 0.0), axis=Vector (0.0, 0.0, 1.0), copy=False, subelements=False)
# scale (selection, scale, center=Vector (0.0, 0.0, 0.0), copy=False, clone=False, subelements=False)
# offset (obj, delta, copy=False, bind=False, sym=False, occ=False)
# make_ortho_array (base_object, v_x=Vector (10.0, 0.0, 0.0), v_y=Vector (0.0, 10.0, 0.0), v_z=Vector (0.0, 0.0, 10.0), n_x=2, n_y=2, n_z=1, use_link=True)
# make_polar_array (base_object, number=5, angle=360, center=Vector (0.0, 0.0, 0.0), use_link=True)
# make_circular_array (base_object, r_distance=100, tan_distance=50, number=3, symmetry=1, axis=Vector (0.0, 0.0, 1.0), center=Vector (0.0, 0.0, 0.0), use_link=True)
# make_path_array (base_object, path_object, count=4, extra=Vector (0.0, 0.0, 0.0), subelements=None, align=False, align_mode='Original', tan_vector=Vector (1.0, 0.0, 0.0), force_vertical=False, vertical_vector=Vector (0.0, 0.0, 1.0), start_offset=0.0, end_offset=0.0, use_link=True)
```

## The old array function

```python
import FreeCAD as App
import Draft

V = App.Vector
doc = App.newDocument("d")
rect = Draft.make_rectangle(10, 5)
doc.recompute()
old = Draft.makeArray(rect, V(15, 0, 0), V(0, 15, 0), 3, 2)       # prints a notice to use the three make_..._array functions
doc.recompute()
print(old.ArrayType, old.NumberX, old.NumberY, len(old.Shape.Faces))                          # ortho 3 2 6
```
