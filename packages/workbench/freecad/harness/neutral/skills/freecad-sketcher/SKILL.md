---
name: freecad-sketcher
description: Use when scripting FreeCAD sketches: adding geometry and constraints, construction and external geometry, checking degrees of freedom and conflicts, and naming constraints so expressions can drive them. Features built on a sketch are in freecad-partdesign.
---

# FreeCAD Sketcher

This skill is for sketches in FreeCAD 1.1, made from Python with the Sketcher workbench. If FreeCAD or `freecadcmd` is not available, stop and tell the owner. The environment and the table of removed APIs are in `freecad-python`; the features that use a sketch, such as a Pad or a Pocket, are in `freecad-partdesign`; and dimensions driven by a VarSet or a Spreadsheet are in `freecad-parameters`. The advice was written against FreeCAD 1.1.4, and every example in `reference.md` was run there unless it is marked (read).

## Attach the sketch

Make a sketch for a PartDesign model with `body.newObject("Sketcher::SketchObject", name)` so it belongs to the Body. Attach it with `sketch.AttachmentSupport = [(plane_or_face, "")]` and `sketch.MapMode = "FlatFace"`. The old `sketch.Support` no longer exists, and the old `Fixed` constraint type does not exist either; use `Block`, or a `Coincident` constraint to the origin.

## Add geometry, then constrain it

`addGeometry` returns the geometry's index and takes a second argument `True` for construction geometry, which is not part of the profile. A constraint names geometry by index and a point on it by a point id: `1` is the start, `2` the end and `3` the centre of a circle or arc. Index `-1` is the origin for a point and the X axis for a line, and `-2` is the Y axis. Pin a sketch to the origin with `Constraint("Coincident", geo, point, -1, 1)`. A tangent between two end points already implies that they coincide, so do not add a `Coincident` as well: the extra constraint made `solve()` return `-2` and appeared in `RedundantConstraints`.

The constraint types are `Coincident`, `Horizontal`, `Vertical`, `Parallel`, `Perpendicular`, `Tangent`, `Equal`, `Symmetric`, `Distance`, `DistanceX`, `DistanceY`, `Radius`, `Diameter`, `Angle`, `Block` and `InternalAlignment`. The argument lists are in `reference.md`.

## Check the sketch after building it

Call `sketch.solve()`: `0` means the solver succeeded, and it is not the number of degrees of freedom. A negative result means conflicting or redundant constraints. Then read `sketch.DoF`, `sketch.FullyConstrained` and the three lists `ConflictingConstraints`, `RedundantConstraints` and `MalformedConstraints`, which hold constraint indices. A sketch that recomputes without error but is not fully constrained changes shape when a parameter changes, so constrain it fully before you drive it with parameters.

## Name a constraint so a parameter can drive it

`sketch.renameConstraint(index, "name")` names a constraint, and `sketch.setExpression("Constraints.name", "...")` binds it to an expression. Do not name a constraint after a unit symbol: `h`, `m`, `s`, `l`, `t`, `g`, `in`, `mm`, `N` and `V` fail with `Failed to parse expression`. A name such as `width` or `len` is fine.

## External geometry

`addExternal(object_name, "Edge1")` references an edge of another sketch, or an axis of the Body's own origin (use the Body's origin object by name, since "Origin" alone is ambiguous with more than one Body). The referenced edge must exist, so recompute first. External edges are addressed from index `-3` downward in the order they were added. An edge of a PartDesign feature was also accepted as external geometry in a check on 1.1.4, but edge names such as `Edge4` change when the model changes (read), so prefer a sketch edge or an origin axis.

## Common mistakes

| Mistake | Instead |
|---|---|
| `sketch.Support = ...` | `sketch.AttachmentSupport = [(plane, "")]` and `MapMode = "FlatFace"` |
| `Constraint("Fixed", ...)` | `Block`, or `Coincident` to `(-1, 1)` |
| Treating `solve() == 0` as fully constrained | Read `DoF` and `FullyConstrained` |
| Adding `Coincident` beside an end-point `Tangent` | Let the `Tangent` imply it |
| Naming a constraint `h`, `mm`, `N` | Use a descriptive name |
| Referencing a feature's edge by name | Reference a sketch edge or an origin axis |
