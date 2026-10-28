---
name: freecad-assembly
description: Use when scripting FreeCAD Assembly: bodies linked into an assembly, a grounded part, joints between faces and vertices, the reference format, flipping and offsets, and checking that the solved layout is right.
---

# FreeCAD Assembly

This skill is for the Assembly workbench in FreeCAD 1.1: putting parts together with joints from Python. If FreeCAD or `freecadcmd` is not available, stop and tell the owner. The environment is in `freecad-python`, the parts are `freecad-partdesign` bodies, and named values that drive offsets are in `freecad-parameters`. The advice was written against FreeCAD 1.1.4, and every example in `reference.md` was run there, headless; the source reports that it exercised joint creation only in the GUI, and the examples show that it works headless too.

## The structure

An assembly is an `Assembly::AssemblyObject` with `Type = "Assembly"`. It holds a joint group (`Assembly::JointGroup`) and one `App::Link` for each part, whose `LinkedObject` is the part's `PartDesign::Body`. Model each part as its own Body, link it into the assembly, ground one part with `JointObject.GroundedJoint`, then add joints between faces and vertices of the links. The joint types, by index in `JointObject.JointTypes`, are Fixed, Revolute, Cylindrical, Slider, Ball, Distance, Parallel, Perpendicular, Angle, RackPinion, Screw, Gears and Belt.

## A joint reference has one correct form

A reference is `[link, [element, vertex]]`, and the two names are object names joined by dots, relative to the link: `"<Body>.<Feature>.<FaceN>"` and `"<Body>.<Feature>.<VertexM>"`, for example `["Block.Pad.Face5", "Block.Pad.Vertex1"]`. The first entry gives the face (the orientation) and the second the vertex (the origin of the joint's coordinate system). Give the moving part first and the fixed part second.

**A wrong form is accepted without an error.** With the Body name missing (`"Pad.Face5."`), `asm.solve()` returned 0, both joint placements were the identity, and the block ended up inside the base (z from 0 to 10, where the correct form gives 10 to 20). After every solve, check that `joint.Placement1` and `joint.Placement2` are not the identity and that the bounding boxes are where you expect. A return of 0 means the solver ran, not that the layout is right.

## Choose faces and vertices by geometry

Names such as `Face6` and `Vertex2` change when a part changes. Find the face from its centre and normal, and the vertex as one of that face's vertices at the position you want, as the helpers in `reference.md` do.

## Joint behaviour

- Joint coordinate systems are made to coincide, so two faces with opposite outward normals can end up on the wrong side. If a part lands inside its mate, call `joint.Proxy.flipOnePart(joint)`, solve again and re-check the bounding box. In the example one flip moved the block from z 10 to 20 into z 0 to 10, and a second flip restored it.
- `joint.Offset2 = App.Placement(...)` shifts the mate: a 5 mm offset in X moved the block 5 mm.
- An expression on a joint property is accepted and follows a named value: `joint.setExpression("Offset2.Base.x", "Dims.Shift")` moved the block to x = 8.0 and then 12.0 as the value changed. After changing a value, run `doc.recompute()`, `asm.solve()` and `doc.recompute()` again.
- A Revolute joint leaves its rotation free: setting `joint.Angle` to 45 did not turn the part (the change was 0.0). To pose a mechanism, use an Angle joint or an offset rotation (read, not tested).

## Parts in other documents

Parts in other documents need external links; that case is not covered (read). For exporting an assembly, including as 3MF, see `freecad-import-export`.

## Common mistakes

| Mistake | Instead |
|---|---|
| A reference like `"Pad.Face5."` | `"<Body>.<Feature>.<FaceN>"`, and check the placements |
| Trusting `solve() == 0` | Check the placements and the bounding boxes |
| Typing `Face6` from the first build | Choose the face from its geometry |
| A part inside its mate | Flip one part and re-solve |
| Expecting `joint.Angle` to pose a Revolute joint | Use an Angle joint or an offset rotation |
