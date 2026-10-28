# Reference: reverse-engineering examples

Every Python example below was run headless with `freecadcmd` on FreeCAD 1.1.4, and the printed value is in the comment.
`<skill folder>` stands for the folder that holds this skill's `SKILL.md`; the script is in `scripts/` beside it. The
examples after "Helpers" use what is defined there, so run the helpers first in the same session.

## Running the script on a file

```sh
freecadcmd <skill folder>/scripts/mesh_report.py -- model.stl --repair --min-component 20 --json report.json
```

Arguments after `--` are the mesh file, then `--repair` (repair a copy before fitting), `--min-component N` (the smallest
component to keep, default 20) and `--json path` (also write the report there). The script prints the report as JSON. It
refuses a `--json` target that is the input file, a symbolic link, or not named `*.json`.

## Helpers

```python
import os
import sys
import FreeCAD as App
import Part
import Mesh
import MeshPart

sys.path.insert(0, "<skill folder>/scripts")
import mesh_report as mr                  # importing the script runs nothing

V = App.Vector


def stand_in():
    """A box with a boss and a through hole, standing in for a scanned part."""
    src = (Part.makeBox(40, 30, 10).fuse(Part.makeCylinder(8, 20, V(20, 15, 0)))
           .cut(Part.makeCylinder(4, 40, V(20, 15, -5))).removeSplitter())
    mesh = MeshPart.meshFromShape(Shape=src, LinearDeflection=0.01, AngularDeflection=0.1)
    return src, mesh
```

## Triage

```python
src, mesh = stand_in()
report = mr.triage(mesh)
print({k: report[k] for k in ("facets", "bbox_mm", "is_solid", "non_manifold", "components", "tiny_components")})
print(report["notes"])                                  # [] for a clean closed part

small = MeshPart.meshFromShape(Shape=Part.makeBox(0.01, 0.01, 0.01), LinearDeflection=0.001, AngularDeflection=0.5)
print(mr.triage(small)["notes"])                        # the unit warning: the file may be in metres
```

## Repair a copy

```python
src, mesh = stand_in()
mesh.addFacet(100, 100, 100, 101, 100, 100, 100, 101, 100)       # debris
fixed, log = mr.repair(mesh)
for entry in log:
    print(entry["step"], entry["facets"], entry["volume"])
print(mesh.CountFacets, fixed.CountFacets, mr.triage(fixed)["is_solid"])
```

## Plane and cylinder segmentation

```python
src, mesh = stand_in()
planes = mesh.getSegmentsOfType("Plane", 0.05, 30)
print(len(planes), sorted(len(p) for p in planes)[-3:])        # the plane segments of the part

cylinders = mesh.getSegmentsOfType("Cylinder", 0.05, 30)
print(len(cylinders), sorted(len(c) for c in cylinders))       # what the built-in cylinder segmentation finds here
```

## Fit planes and cylinders

```python
src, mesh = stand_in()
fits, coverage = mr.fit_primitives(mesh)
print(round(coverage, 3))
for fit in fits:
    if fit["type"] == "Cylinder":
        print("Cylinder", round(fit["radius"], 3), fit["quality"], fit["facets"])      # radii 4.0 and 8.0
    else:
        print("Plane", fit["quality"], fit["facets"])
```

## Rebuild with parameters and check the deviation

```python
import math
import Sketcher

src, mesh = stand_in()
fits, coverage = mr.fit_primitives(mesh)
cylinders = sorted([f for f in fits if f["type"] == "Cylinder"], key=lambda f: f["radius"])
hole, boss = cylinders[0], cylinders[-1]
bb = mesh.BoundBox
params = dict(BaseLength=bb.XLength, BaseWidth=bb.YLength, BaseHeight=10.0,
              BossRadius=boss["radius"], BossHeight=bb.ZLength - 10.0, HoleRadius=hole["radius"],
              CenterX=boss["point"][0], CenterY=boss["point"][1])

doc = App.newDocument("Rebuild")
dims = doc.addObject("App::VarSet", "Dims")
for name, value in params.items():
    dims.addProperty("App::PropertyLength", name, "Dimensions", name)
    setattr(dims, name, value)
doc.recompute()

body = doc.addObject("PartDesign::Body", "Body")
xy = next(o for o in body.Origin.OriginFeatures if o.Role == "XY_Plane")


def new_sketch(name, z=0.0):
    sk = body.newObject("Sketcher::SketchObject", name)
    sk.AttachmentSupport = [(xy, "")]
    sk.MapMode = "FlatFace"
    sk.AttachmentOffset = App.Placement(V(0, 0, z), App.Rotation())
    return sk


def named(sk, index, name, expression):
    sk.renameConstraint(index, name)
    sk.setExpression("Constraints." + name, expression)


base = new_sketch("BaseSketch")
pts = [(0, 0), (40, 0), (40, 30), (0, 30)]
for i in range(4):
    a, b = pts[i], pts[(i + 1) % 4]
    base.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))
for i in range(4):
    base.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
for g in (0, 2):
    base.addConstraint(Sketcher.Constraint("Horizontal", g))
for g in (1, 3):
    base.addConstraint(Sketcher.Constraint("Vertical", g))
base.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))
named(base, base.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 40.0)), "len", "Dims.BaseLength")
named(base, base.addConstraint(Sketcher.Constraint("DistanceY", 1, 1, 1, 2, 30.0)), "wid", "Dims.BaseWidth")
pad = body.newObject("PartDesign::Pad", "BasePad")
pad.Profile = base
pad.setExpression("Length", "Dims.BaseHeight")


def circle_sketch(name, z, radius_property):
    s = new_sketch(name, z)
    c = s.addGeometry(Part.Circle(V(20, 15, 0), V(0, 0, 1), 5))
    named(s, s.addConstraint(Sketcher.Constraint("Radius", c, 5.0)), "r", "Dims." + radius_property)
    named(s, s.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, c, 3, 20.0)), "cx", "Dims.CenterX")
    named(s, s.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, c, 3, 15.0)), "cy", "Dims.CenterY")
    return s


boss_pad = body.newObject("PartDesign::Pad", "BossPad")
boss_pad.Profile = circle_sketch("BossSketch", 10.0, "BossRadius")
boss_pad.setExpression("Length", "Dims.BossHeight")
pocket = body.newObject("PartDesign::Pocket", "HolePocket")
pocket.Profile = circle_sketch("HoleSketch", 30.0, "HoleRadius")
pocket.Type = 1                                              # through all
doc.recompute()

print(round(body.Shape.Volume, 2), round(src.Volume, 2))     # 13005.31 13005.31
print([s.FullyConstrained for s in (base, doc.BossSketch, doc.HoleSketch)])    # [True, True, True]
dev = mr.deviation(mesh, body.Shape, samples=800, tol=0.05)
print(round(dev["max"], 4), dev["within_tol"])               # about 0.0 1.0

dims.BossRadius = 10                                         # change a dimension; the model follows
doc.recompute()
print(round(body.Shape.Volume, 2))                           # 14136.28
```

## The ReverseEngineering module

```python
import ReverseEngineering

names = ("approxSurface", "approxCurve", "normalEstimation", "poissonReconstruction",
         "regionGrowingSegmentation", "sampleConsensus", "featureSegmentation")
print({n: hasattr(ReverseEngineering, n) for n in names})
for n in ("approxSurface", "normalEstimation"):
    doc_text = getattr(ReverseEngineering, n).__doc__ or ""
    print(n, "documents its arguments:", bool(doc_text.strip()))
```
