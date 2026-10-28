---
name: freecad-curved-shapes
description: Use when scripting the Curved Shapes addon in FreeCAD: ribs scaled between bounding hull curves, curved arrays of wings or hulls, the Axis argument. The addon is not part of FreeCAD. For sweeps and Gordon surfaces use freecad-curves.
---

# FreeCAD Curved Shapes addon

This skill is for the Curved Shapes addon, which is not part of FreeCAD 1.1, used from Python. If the addon is missing, so that `import CurvedShapes` fails, stop and tell the owner; do not try to fetch or build it. Nothing in this skill was run for this module: the owner's source says it was checked with Curved Shapes 1.00.14 on FreeCAD 1.1.4, and the FreeCAD used to check this module has no addons, so every statement is marked as read. The addon's interface is unversioned and can change when the addon updates. Read the version from the `package.xml` in the addon's folder first, and re-test before trusting an example if it differs. The environment is in `freecad-python`, and the surface tools of the other addon are in `freecad-curves`. Examples are in `reference.md`.

## When to use it (read)

Prefer PartDesign for what it can do (`freecad-partdesign`). Use Curved Shapes for ribs or sections scaled between bounding curves, as in wings, hulls and tapered organic shapes, which core PartDesign lacks. The result is a Part-level shape, not a PartDesign feature, so bring it into a Body with a `PartDesign::SubShapeBinder` or work at Part level, and check `isValid()` and `Volume` before relying on it for printing.

## Where it can run (read)

`import CurvedShapes` works under `freecadcmd` and in the GUI, and its `make*` functions run headless. All input shapes must be document objects with a `Shape`, for example a `Part::Feature`, a sketch or a Draft object. The functions add a `Part::FeaturePython` object to the document and recompute.

## The rules that matter

- **`Axis` is a direction mask, not a length.** Pass a unit-sized vector such as `V(1, 0, 0)`. The code multiplies it with the bounding box of the hull curves, so `V(100, 0, 0)` pushes every rib far outside the hull and the result is empty (zero faces, zero volume) with **no error**. This cost a wrong result in the owner's testing.
- Ribs are scaled only along the coordinate axes in which the hull curves actually extend. In the example the hulls vary in Z only, so the circle becomes an ellipse that grows in Z while Y stays 10. The volume should be about 62,832 (pi times 10 times the area under the Z half-width), and the tool returned 62,758, a loft approximation.
- With `Items=n` and neither `Surface` nor `Solid`, the result is only the `n` ribs as wires. `Surface=True` lofts a face and `Solid=True` lofts a solid. `Positions=[0.0 ... 1.0]` places the ribs explicitly and overrides `Items`. `Twist` and `Twists` rotate the ribs about the axis.
- The properties of the created object stay editable: set `arr.Items = 8` and recompute, and the shape is rebuilt.

## Other constructors were not checked

`makeCurvedSegment(Shape1=, Shape2=, Hullcurves=[], Items=, Surface=)`, `makeInterpolatedMiddle(Shape1=, Shape2=)`, `makeCurvedPathArray(Base=, Path=, Hullcurves=[])`, `cutSurfaces` and `makeNotchConnector` ran without error on simple inputs, but their geometry was not checked. Check the area, volume and validity yourself, against a number you can compute.

## Common mistakes

| Mistake | Instead |
|---|---|
| `Axis=V(100, 0, 0)` | `Axis=V(1, 0, 0)`; a length gives an empty result with no error |
| Trusting a result without a volume check | Compare with a number you can compute |
| Passing a bare shape | Pass a document object with a `Shape` |
| Presenting the unchecked constructors as working | Check their geometry first |
| Relying on an example after the addon updated | Check `package.xml` and re-test |
