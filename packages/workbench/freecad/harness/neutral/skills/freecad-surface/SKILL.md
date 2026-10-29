---
name: freecad-surface
description: Use when scripting FreeCAD's Surface workbench: a surface from boundary edges (GeomFillSurface, Filling), through sections, extending a surface, sewing, and checking the result. For lofts and sweeps that make solids use freecad-partdesign; for freeform curve tools use freecad-curves.
---

# FreeCAD Surface

This skill is for the Surface workbench in FreeCAD 1.1, used from Python without the interface. If FreeCAD or `freecadcmd` is not available, or a `Surface::` object type cannot be created, stop and tell the owner. The environment and the table of removed APIs are in `freecad-python`. The skill was written from runs, not from experience of using the workbench: every example in `reference.md` was run headless on FreeCAD 1.1.4, and a statement here that was not run is marked (read). A run shows that an example works on that version, not that it is the best way. Loft and sweep solids are in `freecad-partdesign`, and the shape tools that read a result are in `freecad-part`.

## What is in 1.1.4

`doc.supportedTypes()` listed seven Surface object types: `Surface::GeomFillSurface`, `Surface::Filling`, `Surface::Sections`, `Surface::Extend`, `Surface::Sewing`, `Surface::Cut` and `Surface::FeatureBlendCurve`. `Surface::CurveOnMesh` is not a document object type there. The `Surface` module itself exposes only `BlendCurve` and `BlendPoint` as Python names; the objects are made with `doc.addObject`. Each result is a Part-level shape (a `Face`, `Shell` or `Compound`), not a PartDesign feature; take it into a Body with a sub-shape binder if you need that (`freecad-partdesign`).

| Object | Inputs | Gave |
|---|---|---|
| `GeomFillSurface` | `BoundaryList`: one `(object, "EdgeN")` per boundary edge; `FillType` `Stretched`, `Coons` or `Curved` | a `Face` |
| `Filling` | `BoundaryEdges`: `(object, [edge names])`; optional `Points` | a `Face` |
| `Sections` | `NSections`: `(object, "EdgeN")` per section, in order | a `Face` |
| `Extend` | `Face` as `(object, ["Face1"])` and six extend values | a `Face` |
| `Sewing` | `ShapeList`: `(object, ["Face1"])` per face | a `Shell` when the faces touch |
| `Cut` | `ShapeList`: exactly two faces | a `Shell` |

## Boundary surfaces

`GeomFillSurface` on four straight edges, flat or bent, gave a valid `Face` with `Stretched` and `Curved` (area 100.0 for a flat 10 by 10 square, 107.904 for the same square with one corner raised by 5). The edges can come from one wire object, taken edge by edge, or from separate objects, and listing them in a different order made no difference to the result. `Coons` failed on every straight-edge boundary I tried and on a boundary of an arc and two lines: the object was `Invalid` with a null shape and the console printed "Curves are disjoint". It worked on four arcs (area 134.422, against 133.733 for `Stretched` and 128.355 for `Curved`). Try `Stretched` first and check the result. With one side of the flat square left out, `Stretched` still gave a valid `Face` of area 100.0, so a result being valid does not show that the boundary was complete.

`Filling` is for a boundary that `GeomFillSurface` does not take. A bent four-edge boundary gave a valid `Face` of area 107.903. A circle that is one closed edge failed ("Failed to create a face from constraints", null shape), but the same circle as two half-arcs gave a valid `Face` of area 78.54, which is the area of the disc. A point added through `Points` pulled the surface through it (the shape passed within 1e-4 of the point, and the area rose to 102.225). `BoundaryOrder` is empty by default; `[0, 0, 0, 0]` was fine, and `[1, 1, 1, 1]` made the object `Invalid` with these plain edges, so leave it empty unless the edges belong to faces (that case was not run, read). `Tolerance3d` and `MaximumDegree` (default 8) can be set; with 0.001 and 5 the surface had degree 5 in both directions.

## Sections

`Sections` takes the sections in the order they follow along the surface. Three lines, with the middle one raised by 2, gave a valid `Face` of area 109.823, and the same lines in the reverse order gave the same area. The same lines in the order first, last, middle gave a valid `Face` of area 158.77, so the order is part of the input and `isValid` does not catch a wrong one. Two arcs of different radius and height gave a valid `Face` (136.984).

## Extend

`Extend` has `ExtendUPos`, `ExtendUNeg`, `ExtendVPos` and `ExtendVNeg`, each a fraction of the surface's parameter range, and `ExtendUSymetric` and `ExtendVSymetric` (so spelled), which default to true with all four values 0.05. With the flags true the two sides extend together, so set both flags false before you set one side. Then `ExtendUPos = 0.5` on a 10 by 10 plane gave a face from x 0 to 15 and area 150.0. The result is reparametrised: a face extended from a filled surface had the parameter range (0, 1, 0, 1). `SampleU`, `SampleV` and `Tolerance` default to 32, 32 and 0.1.

## Sewing and Cut

`Sewing` of two planes that touch gave a valid `Shell` of 2 faces and area 200.0; planes that did not touch gave a `Compound` of the same two faces, with no error, so test `ShapeType`. `Cut` took two faces and gave a `Shell` (a 20 by 20 plane with a 6 by 6 face cut out had area 364.0); a face with a solid or with a shell gave an `Invalid` object with a null shape and the console printed "Two shapes must be entered at a time for a cut operation".

## Check the result

Do every check below before using a surface, and call `doc.recompute()` first.

| Check | How |
|---|---|
| The object computed | `obj.State` is `['Up-to-date']`; an `Invalid` state with a null shape (`obj.Shape.isNull()`) means it failed, and the console says why |
| The shape is sound | `shape.isValid()`, `ShapeType`, and `face.Surface.__class__.__name__` (`BSplineSurface` for these) |
| It is the surface you meant | compare `shape.Area` with a value you can compute, or sample `face.valueAt(u, v)` over `face.ParameterRange` |
| It meets the boundary | `face.distToShape(edge)[0]` was 0.0 for each boundary edge |
| Its height | `BoundBox` overstated it (ZMax 4.0 for a surface whose sampled maximum was 2.0); use `face.optimalBoundingBox()` or sample the face |

`Surface::FeatureBlendCurve` has start and end edges, parameters, sizes and continuities (default continuity 2), but it was not run for this module (read). So were the Surface commands, which need the interface.

## Common mistakes

| Mistake | Instead |
|---|---|
| Trusting `isValid()` alone | Also check the area, the state and the null shape |
| Using `Coons` on straight edges | Use `Stretched` or `Curved` |
| Filling one closed edge | Split it into two edges |
| Giving `Sections` out of order | List them in order along the surface |
| Setting one `Extend` side with the flags true | Set both flags false first |
| Reading a surface's height from `BoundBox` | Use `optimalBoundingBox()` or sample |
| Giving `Cut` a solid | Give it two faces |
