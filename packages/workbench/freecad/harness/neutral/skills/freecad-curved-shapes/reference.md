# Reference: Curved Shapes addon examples

Nothing in this file was run for this module. The example and its printed value come from the owner's check of Curved Shapes
1.00.14 on FreeCAD 1.1.4, run headless there; the FreeCAD used here has no addons. Check the addon's version in its
`package.xml` and re-test before you trust it. Each block starts with `# (read)`.

## Ribs between two hull curves

```python
# (read)
import FreeCAD
import Part
import CurvedShapes

V = FreeCAD.Vector
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("CS")


def feat(name, shape):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    return o


# a circular rib at x=0 and two straight hull curves that diverge in Z along X
rib = feat("Rib", Part.Wire(Part.makeCircle(10, V(0, 0, 0), V(1, 0, 0))))
top = feat("HullTop", Part.makeLine((0, 0, 10), (100, 0, 30)))
bottom = feat("HullBottom", Part.makeLine((0, 0, -10), (100, 0, -30)))
doc.recompute()

arr = CurvedShapes.makeCurvedArray(Base=rib, Hullcurves=[top, bottom], Axis=V(1, 0, 0), Items=6, Solid=True)
print(arr.Shape.ShapeType, arr.Shape.isValid(), round(arr.Shape.Volume))    # Solid True 62758

arr.Items = 8                       # properties stay editable; a recompute rebuilds the shape
doc.recompute()
```

The expected volume from the geometry is about 62,832 (the ellipse grows in Z while Y stays 10), so 62,758 is a loft
approximation. With `Axis=V(100, 0, 0)` instead of `V(1, 0, 0)` the owner got an empty result (zero faces, zero volume) and
no error.
