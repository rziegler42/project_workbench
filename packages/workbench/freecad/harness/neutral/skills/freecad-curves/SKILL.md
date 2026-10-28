---
name: freecad-curves
description: Use when scripting the Curves addon in FreeCAD: two-rail sweeps, Gordon and ruled surfaces, joined splines. The addon is not part of FreeCAD. For ribs between hull curves use freecad-curved-shapes; for plain pipes and lofts use freecad-partdesign.
---

# FreeCAD Curves addon

This skill is for the Curves workbench, an addon that is not part of FreeCAD 1.1, used from Python. If the addon is missing, so that `import freecad.Curves` fails, stop and tell the owner; do not try to fetch or build it. Nothing in this skill was run for this module: the owner's source says it was checked with Curves 0.6.71 on FreeCAD 1.1.4, and the FreeCAD used to check this module has no addons, so every statement is marked as read. The addon's interface is unversioned and can change when the addon updates. Read the version from the `package.xml` in the addon's folder first, and re-test before trusting an example if it differs. The addon's own README calls the workbench experimental. The environment is in `freecad-python`, and the ribs-between-curves addon is `freecad-curved-shapes`. Examples are in `reference.md`.

## Use the core tools first (read)

Prefer PartDesign for what it can do: `AdditivePipe` along a path, `AdditiveLoft` between sections and `Revolution`. They are parametric, stay inside a Body and print reliably (see `freecad-partdesign`). Reach for the addon when you need what the core lacks:

| Need | Tool |
|---|---|
| A surface through two rails and several profiles | Sweep 2 Rails |
| A surface skinning a grid of curves | Gordon |
| A smooth ruled surface between two edges | HQ Ruled Surface |
| Several edges joined into one smooth BSpline | JoinCurve |

The results are Part-level shells and faces, not PartDesign features. To use one inside a Body, bring it in with a `PartDesign::SubShapeBinder` (see `freecad-partdesign`) or work at Part level. A surface becomes a solid only if you close it (`Part.Shell`, then `Part.Solid`). Check `shape.isValid()` and the area or volume before relying on a result for printing.

## Where it can run (read)

The library modules that have no GUI commands import without a GUI: `freecad.Curves.nurbs_tools`, `gordon`, `blend_curve` and `curves_to_surface`. The feature modules (`Sweep2RailsFP`, `JoinCurves`, `HQRuledSurfaceFP`, `gordonFP` and the others) call `FreeCADGui.addCommand` when imported, so they need a GUI session. Run them through the FreeCAD MCP server's `execute_code` tool (see `freecad-mcp`) and not through `freecadcmd`.

## Call the feature, not the menu

Each feature class follows one pattern: a `...Command` class with a `make...Feature` method that builds a `Part::FeaturePython` from the objects you pass. Call that method directly instead of simulating a selection. The created object's name and label have spaces replaced by underscores (`Sweep_2_Rails`), so take the object from `doc.Objects[-1]` instead of looking it up by the menu label. The tools print debug lines to the console; that is normal. The input objects must be document objects with a `Shape`.

## What the owner measured (read)

- Sweep 2 Rails: the first two objects are the rails and the rest are profiles. The area was 1000.0 on straight rails and 1066.7 on bulged rails.
- JoinCurve takes `(object, ("EdgeN",))` pairs and gave one edge of length 20.0.
- HQ Ruled Surface between two lines gave an area of 100.01.
- Gordon over four crossing curves gave 100.0, and after three input curves were moved it recomputed to 200.0, so these features follow their inputs.

## Do not present these as working

`PipeShell` (it needs `pipeshellProfile` objects and an `(object, ("EdgeN",))` spine, and its default output is "Sections", not a surface), `blend_curve.BlendCurve` and `BlendSurface`, `IsoCurve`, `CurveOnSurface`, `approximate`, and the other tools in the addon's folder were not verified. To learn a tool's input convention, read the `makeFeature` of its `...Command`, then test it on a case whose answer you can compute.

## Freeform regions of a scan (read)

For regions that primitive fitting cannot explain (see `freecad-reverse-engineering`), a Gordon or Sweep 2 Rails surface over curves traced from mesh cross-sections can rebuild the surface. Measure its deviation and report it. This was not run end to end.

## Common mistakes

| Mistake | Instead |
|---|---|
| Using the addon for a plain pipe or loft | Use `AdditivePipe` or `AdditiveLoft` |
| Importing a feature module under `freecadcmd` | Run it in a GUI session |
| Looking the created object up by its menu label | Take `doc.Objects[-1]` |
| Presenting `PipeShell` or `IsoCurve` as working | They were not verified; test them first |
| Relying on an example after the addon updated | Check `package.xml` and re-test |
