# Reference: Part examples

Each block is self-contained and was run headless with `freecadcmd` on FreeCAD 1.1.4. The printed value is in the comment.

## Primitives

```python
import FreeCAD as App
import Part

box = Part.makeBox(10, 20, 30)
box_placed = Part.makeBox(10, 20, 30, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
cyl = Part.makeCylinder(5, 20)
cone = Part.makeCone(5, 2, 10)
sph = Part.makeSphere(10)
tor = Part.makeTorus(10, 2)
plane = Part.makePlane(10, 10)
helix = Part.makeHelix(2, 10, 5)            # pitch, height, radius
print(round(box.Volume), round(cyl.Volume), round(cone.Volume), round(sph.Volume), round(tor.Volume))
print(box_placed.ShapeType, plane.ShapeType, helix.ShapeType)
```

## Curves and edges

```python
import FreeCAD as App
import Part

V = App.Vector
line = Part.makeLine((0, 0, 0), (10, 0, 0))
circle = Part.makeCircle(5, V(0, 0, 0), V(0, 0, 1))
arc = Part.makeCircle(5, V(0, 0, 0), V(0, 0, 1), 0, 180)
arc3 = Part.Arc(V(0, 0, 0), V(5, 5, 0), V(10, 0, 0)).toShape()
ellipse = Part.Ellipse(V(0, 0, 0), 10, 5).toShape()

points = [V(0, 0, 0), V(2, 3, 0), V(5, 1, 0), V(8, 4, 0)]
through = Part.BSplineCurve()
through.interpolate(points)                  # passes through the points
poles = Part.BSplineCurve()
poles.buildFromPoles(points)                 # the points are control points
bezier = Part.BezierCurve()
bezier.setPoles([V(0, 0, 0), V(3, 5, 0), V(7, 5, 0), V(10, 0, 0)])
for edge in (line, circle, arc, arc3, ellipse, through.toShape(), poles.toShape(), bezier.toShape()):
    print(edge.ShapeType, round(edge.Length, 3))
```

## Wires, faces and solids

```python
import FreeCAD as App
import Part

V = App.Vector
pts = [V(0, 0, 0), V(10, 0, 0), V(10, 10, 0), V(0, 10, 0)]
edges = [Part.makeLine(pts[i], pts[(i + 1) % 4]) for i in range(4)]
wire = Part.Wire(edges)                             # edges connect end to end
sorted_wire = Part.Wire(Part.__sortEdges__([edges[2], edges[0], edges[3], edges[1]]))
face = Part.Face(wire)
hole = Part.Wire(Part.makeCircle(2, V(5, 5, 0)))
flat = Part.Face([wire, hole])                      # same direction: an INVALID face, area 112.566
hole.reverse()                                      # an inner wire runs the other way round
with_hole = Part.Face([wire, hole])                 # first wire is the outer one
cut_hole = face.cut(Part.Face(Part.Wire(Part.makeCircle(2, V(5, 5, 0)))))   # or cut one face from another
print(wire.isClosed(), sorted_wire.isClosed(), round(face.Area, 3))
print(flat.isValid(), round(flat.Area, 3), with_hole.isValid(), round(with_hole.Area, 3), round(cut_hole.Area, 3))

box = Part.makeBox(10, 10, 10)
shell = Part.Shell(box.Faces)
solid = Part.Solid(shell)
compound = Part.Compound([box, Part.makeSphere(3)])
print(shell.isClosed(), solid.ShapeType, round(solid.Volume), compound.ShapeType)
```

## Combine and finish

```python
import FreeCAD as App
import Part

V = App.Vector
a = Part.makeBox(10, 10, 10)
b = Part.makeBox(10, 10, 10, V(5, 0, 0))
c = Part.makeCylinder(2, 10, V(5, 5, 0))
union = a.fuse(b)
print(round(union.Volume), len(union.Faces), len(union.removeSplitter().Faces))
print(round(a.cut(c).Volume), round(a.common(b).Volume), round(a.multiFuse([b, c]).Volume))

filleted = a.makeFillet(1.0, a.Edges)
partial = a.makeFillet(1.0, [a.Edges[0], a.Edges[3]])
chamfered = a.makeChamfer(1.0, a.Edges)
print(round(filleted.Volume, 3), round(partial.Volume, 3), round(chamfered.Volume, 3))

hollow = a.makeThickness([a.Faces[5]], -1.0, 1e-3)
grown = a.makeOffsetShape(1.0, 1e-3)
section = a.section(Part.makePlane(100, 100, V(-50, -50, 5)))
print(round(hollow.Volume), round(grown.Volume), section.ShapeType, round(section.Length))
```

## Extrude, revolve, loft and sweep

```python
import FreeCAD as App
import Part

V = App.Vector
square = Part.Face(Part.Wire([Part.makeLine((0, 0, 0), (10, 0, 0)), Part.makeLine((10, 0, 0), (10, 10, 0)),
                              Part.makeLine((10, 10, 0), (0, 10, 0)), Part.makeLine((0, 10, 0), (0, 0, 0))]))
print(round(square.extrude(V(0, 0, 10)).Volume))

rect = Part.Face(Part.Wire([Part.makeLine((5, 0, 0), (10, 0, 0)), Part.makeLine((10, 0, 0), (10, 0, 4)),
                            Part.makeLine((10, 0, 4), (5, 0, 4)), Part.makeLine((5, 0, 4), (5, 0, 0))]))
print(round(rect.revolve(V(0, 0, 0), V(0, 0, 1), 360).Volume, 1))

w1 = Part.Wire(Part.makeCircle(5, V(0, 0, 0)))
w2 = Part.Wire(Part.makeCircle(2, V(0, 0, 10)))
loft = Part.makeLoft([w1, w2], True)
print(loft.ShapeType, round(loft.Volume, 1))

path = Part.Wire([Part.makeLine((0, 0, 0), (0, 0, 20))])
profile = Part.Wire(Part.makeCircle(3, V(0, 0, 0)))
pipe = path.makePipe(profile)                       # an open Shell: its Volume is just its area
solid_pipe = path.makePipeShell([profile], True, False)    # True asks for a solid
print(pipe.ShapeType, pipe.isClosed(), round(pipe.Volume, 1))                  # Shell False 377.0
print(solid_pipe.ShapeType, solid_pipe.isClosed(), round(solid_pipe.Volume, 1))   # Solid True 565.5
```

## Reading a shape

```python
import FreeCAD as App
import Part

shape = Part.makeBox(10, 20, 30)
print(len(shape.Vertexes), len(shape.Edges), len(shape.Wires), len(shape.Faces), len(shape.Shells), len(shape.Solids))
print(shape.Vertexes[0].Point)

edge = shape.Edges[0]
middle = edge.FirstParameter + 0.5 * (edge.LastParameter - edge.FirstParameter)
print(edge.Length, type(edge.Curve).__name__)
print(edge.firstVertex().Point, edge.lastVertex().Point, edge.valueAt(middle), edge.tangentAt(middle))

face = shape.Faces[0]
print(face.Area, type(face.Surface).__name__, face.CenterOfMass, face.normalAt(0.5, 0.5))

bb = shape.BoundBox
print(bb.XLength, bb.YLength, bb.ZLength, bb.Center, round(bb.DiagonalLength, 3))
print(shape.Volume, shape.Area, shape.CenterOfMass, shape.ShapeType, shape.isValid(), shape.isClosed())
```

## Putting a shape in the document

```python
import FreeCAD as App
import Part

doc = App.newDocument("Show")
obj = doc.addObject("Part::Feature", "Pillar")
obj.Shape = Part.makeCylinder(5, 20)
doc.recompute()
print(obj.State, round(obj.Shape.Volume, 1))
Part.show(Part.makeBox(1, 1, 1), "Cube")
print([o.Name for o in doc.Objects])
```
