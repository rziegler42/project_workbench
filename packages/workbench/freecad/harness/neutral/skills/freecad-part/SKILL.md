---
name: freecad-part
description: Use when scripting FreeCAD's Part workbench: primitives, edges, wires, faces, shells and solids, booleans, fillets, loft, sweep, and reading shape topology. For editable parametric models use freecad-partdesign instead.
---

# FreeCAD Part

This skill is for the Part workbench in FreeCAD 1.1: building and reading B-rep shapes from Python. If FreeCAD or `freecadcmd` is not available, stop and tell the owner. The environment, the `GuiUp` guard and the table of removed APIs are in `freecad-python`. Part gives plain shapes with no feature history; when the model must stay editable, build it with PartDesign (`freecad-partdesign`) and use Part for the pieces PartDesign lacks. The advice was written against FreeCAD 1.1.4 and every example in `reference.md` was run there unless it is marked (read).

## The shape hierarchy

A shape is one of Vertex, Edge, Wire, Face, Shell, Solid, CompSolid or Compound, each built from the levels before it. A boolean on solids gives a solid or a compound, so test `ShapeType` before relying on a `Solid`.

## Build from the bottom up

1. Prefer a primitive (`makeBox`, `makeCylinder`, `makeCone`, `makeSphere`, `makeTorus`, `makePlane`, `makeHelix`, `makeWedge`) when the part is one.
2. Otherwise draw edges (`makeLine`, `makeCircle`, `Part.Arc`, `Part.Ellipse`, `Part.BSplineCurve`, `Part.BezierCurve`), join them into a `Part.Wire`, make a `Part.Face` from a closed planar wire, and extrude or revolve it into a solid.
3. A `Part.Wire` needs edges that connect end to end; `Part.__sortEdges__` orders loose edges, and takes the list itself.
4. A face with holes is `Part.Face([outer, hole1, hole2])`, the outer wire first, but an inner wire must run the other way round: wires of one direction give an invalid face with a wrong area. Reverse each hole with `wire.reverse()`, or cut a face made from the hole out of the outer face. Check `isValid()` on the result.
5. A solid from a shell needs a closed shell.

## Combine and finish

Combine with `fuse`, `cut`, `common` and `multiFuse`. After a fuse call `removeSplitter()` to merge the seam edges it leaves. Round or bevel edges with `makeFillet(radius, edges)` and `makeChamfer(distance, edges)`; pass only the edges you mean. Hollow a solid with `makeThickness`, offset it with `makeOffsetShape`, and cut a section with `section`. Profiles become solids by `extrude`, `revolve`, `Part.makeLoft(wires, True)` and `makePipeShell(profiles, True, False)` along a path. `makePipe` returns an open shell, not a solid, and its `Volume` is only its area, so use `makePipeShell` with its solid flag when you need a volume.

## Read the result

`Volume`, `Area`, `CenterOfMass`, `BoundBox`, `ShapeType`, `isValid()` and `isClosed()` describe a shape; `Vertexes`, `Edges`, `Wires`, `Faces`, `Shells` and `Solids` list its parts. A shape that is not valid or not closed gives numbers that cannot be trusted, so check both before you report a volume. Face and edge names such as `Face6` change when the model changes; find them from geometry, never hard-code them after the first build.

## Put it in the document

`Part.show(shape, "Name")` adds a shape quickly. For a named object that you will recompute, make one with `doc.addObject("Part::Feature", "Name")` and set its `Shape`, then call `doc.recompute()`.

## Common mistakes

| Mistake | Instead |
|---|---|
| Making a solid from an open shell | Check `shell.isClosed()` first |
| Passing hole wires that run the same way as the outer wire | Reverse them, and check `isValid()` |
| Using `makePipe` and reading its `Volume` | Use `makePipeShell(..., True, ...)` for a solid |
| Filleting every edge when you meant some | Pass the edge list you chose |
| Reporting a volume without checking validity | Check `isValid()` and `ShapeType` first |
| Hard-coding `Face6` after the first build | Select faces by geometry |
| Building an editable part from Part shapes | Use `freecad-partdesign` |
