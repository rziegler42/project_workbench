---
name: freecad-measure-and-inspection
description: Use when checking a FreeCAD result: shape validity and closed solids, volume, area and bounding box, distances between shapes, Measure.Measurement, and comparing a model with a number you can compute.
---

# FreeCAD measure and inspection

This skill is for checking that a FreeCAD result is right, from Python in FreeCAD 1.1. If FreeCAD or `freecadcmd` is not available, stop and tell the owner. A script that ran without an exception has shown only that it ran, so end every piece of modelling with a check against a number you computed another way. The environment is in `freecad-python`, mesh checks are in `freecad-mesh`, and a scanned part's deviation report is in `freecad-reverse-engineering`. The advice was written against FreeCAD 1.1.4, and every Python example in `reference.md` was run there.

## What a shape reports about itself

`ShapeType`, `isValid()`, `isClosed()`, `Volume`, `Area`, `CenterOfMass` and `BoundBox` describe a shape. A Boolean such as `cut` returns a `Compound`, and a `Compound` has `Volume` and `Area` but no `CenterOfMass`, so take the part out with `.Solids[0]` first. A box with a face missing is a `Shell` with `isClosed()` false, so its volume cannot be trusted. A face made from wires of the same direction had `isValid()` false and a wrong area, and `shape.check(True)` raised "Bad orientation of sub-shape" for it. Check validity and closure before you report any figure.

## Distances

`a.distToShape(b)` returns the distance, the pairs of closest points and extra information. Two boxes 15 mm apart gave 15.0 and the closest points. Touching and overlapping solids give 0.0. A point 20 mm above a box gave 20.0. A point inside a solid gives 0.0 against the solid, but 10.0 (the distance to the surface) against a compound of its faces, which is why a deviation check uses the faces: `Part.Compound(shape.Faces)`. `shape.isInside(point, tolerance, True)` answers whether a point is inside.

## Compare with a number you can compute

Compute the expected value from the specification (the volume of a cylinder is pi r squared h) and compare the relative error with a tolerance you state, not with zero. A mesh is a little smaller than its shape: 0.3% for a fine mesh and 1% for a coarse one in the example. A tolerance that suits a CAD model is too tight for a mesh or a scan.

## Deviation of a mesh from a shape

Measure each sampled mesh vertex against `Part.Compound(shape.Faces)` and report the maximum, a high percentile and the share within tolerance. This is a one-way measure, from the mesh's vertices to the shape. The vertices of a mesh made from a shape lie on the shape, so it reads 0.0 even though the mesh volume is 0.3% smaller; it cannot see the error between vertices. It is the right check for the points of a scan against a rebuilt model, and the wrong check for the quality of a tessellation, which the volume shows. The script `mesh_report.py` in `freecad-reverse-engineering` makes the same one-way measure with numpy.

## The Measure module

`Measure.Measurement` works headless on 1.1.4. Make one, call `addReference3D(object_name, subelement)` with the object's name as a string (passing the object raises a `TypeError`), then call a method: `length`, `area`, `radius`, `volume`, `com`, `angle`, `planePlaneDistance`, `lineLineDistance` or `delta`. On a 10 by 20 by 30 box it gave an edge length of 30.0, a face area of 600.0, a volume of 6000.0, a centre of mass at (5, 10, 15), 10.0 between two opposite faces and 90.0 between two edges; on a cylinder it gave the radius 5.0. `lineLineDistance` and `delta` were listed and not exercised (read). The `Inspection` module exposes no Python names on 1.1.4, so do not rely on it from a script.

## Report the check

State what was measured, how, the expected value and its source, the tolerance, and the result. Say plainly which figures are approximations.

## Common mistakes

| Mistake | Instead |
|---|---|
| Reading `CenterOfMass` of a Boolean result | Take `.Solids[0]` first |
| Reporting a volume from an open or invalid shape | Check `isValid()` and `isClosed()` first |
| Checking a tessellation by its vertices | Compare the volume with the shape's |
| Measuring deviation against the solid | Use the faces, or inside points read as zero |
| Passing the object to `addReference3D` | Pass its name as a string |
| Comparing with zero | State a tolerance and compare the relative error |
