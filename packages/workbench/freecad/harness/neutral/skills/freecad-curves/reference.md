# Reference: Curves addon examples

Nothing in this file was run for this module. The examples and their printed values come from the owner's checks of Curves
0.6.71 on FreeCAD 1.1.4, run in a GUI session through the FreeCAD MCP server; the FreeCAD used here has no addons. Check
the addon's version in its `package.xml` and re-test before you trust them. Each block starts with `# (read)`.

## Helpers

```python
# (read)
import FreeCAD as App
import Part

V = App.Vector
doc = App.newDocument("CurvesDemo")


def feat(name, shape):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    return o


def bspline(points):
    c = Part.BSplineCurve()
    c.interpolate(points)
    return c.toShape()
```

## Sweep 2 Rails

```python
# (read)
from freecad.Curves import Sweep2RailsFP

r1 = feat("Rail1", bspline([V(0, 0, 0), V(2, 0, 25), V(0, 0, 50)]))
r2 = feat("Rail2", bspline([V(20, 0, 0), V(24, 0, 25), V(20, 0, 50)]))
p1 = feat("Prof1", Part.makeLine((0, 0, 0), (20, 0, 0)))
p2 = feat("Prof2", Part.makeLine((0, 0, 50), (20, 0, 50)))
doc.recompute()
Sweep2RailsFP.Sweep2RailsCommand().makeFeature([r1, r2, p1, p2])      # the first two are the rails
sweep = doc.Objects[-1]
print(sweep.State, round(sweep.Shape.Area, 1))      # ['Up-to-date'] 1066.7 (1000.0 on straight rails)
```

## JoinCurve

```python
# (read)
from freecad.Curves import JoinCurves

a = feat("LA", Part.makeLine((0, 0, 0), (10, 0, 0)))
b = feat("LB", Part.makeLine((10, 0, 0), (10, 10, 0)))
doc.recompute()
JoinCurves.joinCommand().makeJoinFeature([(a, ("Edge1",)), (b, ("Edge1",))])
print(doc.Objects[-1].Shape.Length)                  # 20.0, one edge
```

## HQ Ruled Surface

```python
# (read)
from freecad.Curves import HQRuledSurfaceFP

c1 = feat("HA", Part.makeLine((0, 0, 0), (10, 0, 0)))
c2 = feat("HB", Part.makeLine((0, 10, 0), (10, 10, 0)))
doc.recompute()
HQRuledSurfaceFP.HQ_Ruled_Surface_Command().makeFeature([c1, c2])
print(round(doc.Objects[-1].Shape.Area, 2))          # 100.01
```

## Gordon surface

```python
# (read)
from freecad.Curves import gordonFP

u1 = feat("U1", bspline([V(0, 0, 0), V(5, 0, 0), V(10, 0, 0)]))
u2 = feat("U2", bspline([V(0, 10, 0), V(5, 10, 0), V(10, 10, 0)]))
v1 = feat("V1", bspline([V(0, 0, 0), V(0, 5, 0), V(0, 10, 0)]))
v2 = feat("V2", bspline([V(10, 0, 0), V(10, 5, 0), V(10, 10, 0)]))
doc.recompute()
gordonFP.gordonCommand().makeGordonFeature([u1, u2, v1, v2])
gordon = doc.Objects[-1]
print(round(gordon.Shape.Area, 1))                   # 100.0
```

After the owner moved three of the four input curves, this feature recomputed to an area of 200.0.
