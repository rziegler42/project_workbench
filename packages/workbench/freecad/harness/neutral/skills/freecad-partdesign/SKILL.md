---
name: freecad-partdesign
description: Use when scripting FreeCAD PartDesign: a Body with Pad, Pocket, Hole, Revolution, pipe and loft features, fillets and chamfers, patterns, mirrors, datum planes, and several Bodies combined. Sketches are in freecad-sketcher; shapes without history are in freecad-part.
---

# FreeCAD PartDesign

This skill is for feature-based, editable models in FreeCAD 1.1, built from Python with the PartDesign workbench. If FreeCAD or `freecadcmd` is not available, stop and tell the owner. The environment and the table of removed APIs are in `freecad-python`, the sketches under the features are in `freecad-sketcher`, and dimensions driven by named values are in `freecad-parameters`. For a shape with no feature history, or for a result PartDesign lacks, use `freecad-part`. The advice was written against FreeCAD 1.1.4, and every example in `reference.md` was run there unless it is marked (read).

## Build inside a Body

Make a `PartDesign::Body` with `doc.addObject`, then make every sketch and feature with `body.newObject(type, name)`. A feature made with `doc.addObject("PartDesign::Pad", ...)` belongs to no Body: its parent group is `None`, it is not in the Body's group list, and the Body's `Tip` does not move. When its profile sketch sits inside a Body, the recompute also complains that the links are out of scope. The `Tip` is the last feature of the chain; a new feature takes it, but a pattern does not, so set `body.Tip` yourself after a pattern and read the result from `body.Shape`.

Attach a sketch with `AttachmentSupport = [(plane_or_face, "")]` and `MapMode = "FlatFace"`, and shift it with `AttachmentOffset`. The sketch itself is covered by `freecad-sketcher`.

## Features that use a sketch

| Feature | Set | Notes |
|---|---|---|
| `PartDesign::Pad` | `Profile`, `Length` | the profile must be a closed sketch |
| `PartDesign::Pocket` | `Profile`, `Type` | `Type = 1` is through all |
| `PartDesign::Hole` | `Profile`, `Diameter`, `DepthType` | the profile is a sketch of circles; `"ThroughAll"` |
| `PartDesign::Revolution` | `Profile`, `ReferenceAxis`, `Angle` | `ReferenceAxis = (sketch, ["V_Axis"])` is the sketch's own vertical axis |
| `PartDesign::AdditivePipe` | `Profile`, `Spine` | `Spine = (path_sketch, ["Edge1"])`; the volume of a straight pipe is the profile area times the length |
| `PartDesign::AdditiveLoft` | `Profile`, `Sections` | `Sections = [other_sketch]`; a second sketch can sit on an offset of the same plane |

Put a sketch on a face of a feature with `(feature, "Face6")`, and find the face by geometry (its centre and normal) and never by a number typed from the first build: face and edge names change when the model changes (read). A datum plane is a `PartDesign::Plane` with its own `AttachmentSupport`, `MapMode` and `AttachmentOffset`, and a sketch can be attached to it.

## Finish and repeat

`PartDesign::Fillet`, `Chamfer` and `Thickness` take `Base = (feature, [names])`. Name the edges or faces from the feature's own shape, as in `reference.md`, and set `Radius`, `Size` or `Value`. A thickness also needs `Mode` and `Join`; the example uses `Mode = 0` and `Join = 1`.

Patterns repeat a feature: `LinearPattern` (`Originals`, `Direction`, `Length`, `Occurrences`), `PolarPattern` (`Originals`, `Axis`, `Angle`, `Occurrences`) and `Mirrored` (`Originals`, `MirrorPlane`). A `MultiTransform` lists its transformations, which are separate pattern objects made beforehand. Each pattern needs `body.Tip` set to it afterwards. A mirror plane that misses the part does nothing (read).

## Several Bodies

A `PartDesign::SubShapeBinder` brings another Body's shape in as a reference (`binder.Support = [(other_body, [""])]`; its own volume was the other Body's volume), and it cuts nothing by itself (read). A `PartDesign::Boolean` applies `"Fuse"`, `"Cut"` or `"Common"` with another Body (`feature.addObject(other_body)`), and the Body's volume then changes.

## Check the result

Compare the volume with the volume the geometry gives, for example a pipe of radius 3 and length 30 is about 848.2. Read `feature.State` after `doc.recompute()`. A feature that did not build shows `['Touched', 'Invalid']`, `isValid()` is false, and the console says why, for example that the sketch wire is not closed.

## Common mistakes

| Mistake | Instead |
|---|---|
| `doc.addObject("PartDesign::Pad", ...)` | `body.newObject("PartDesign::Pad", ...)` |
| `sketch.Support = ...` | `sketch.AttachmentSupport = [(plane, "")]` with `MapMode = "FlatFace"` |
| Typing `Face6` or `Edge4` from the first build | Find the face or edge from its geometry |
| Forgetting `body.Tip` after a pattern | Set the Tip to the pattern |
| A profile that is not closed | Close it and read `State` |
| Trusting that the recompute worked | Compare the volume with an independent number |
