---
name: freecad-python
description: Use when writing or debugging FreeCAD 1.1 Python: scripts, macros, headless runs with freecadcmd, the GuiUp guard, units, or an older example whose API was removed. Single workbenches and tasks have their own freecad skills.
---

# FreeCAD Python

This skill is for Python that runs inside FreeCAD 1.1, headless with `freecadcmd` or in the GUI. If FreeCAD or `freecadcmd` is not available, stop and tell the owner; do not try to fetch or build a copy. The advice was written against FreeCAD 1.1.4. A statement marked (read) was read from the owner's practice and not run; the others were run headless on that version. The skills whose names start with `freecad-` cover single workbenches and tasks, and for its own topic a detail in one of them wins over this skill. Worked examples are in `reference.md`.

## Run a script headless first

Run a script with `freecadcmd script.py`. Arguments for the script follow a `--`, and the script reads them from `sys.argv`. Under `freecadcmd` there is no GUI: `FreeCAD.GuiUp` is false and an object's `ViewObject` is `None`. `import FreeCADGui` still succeeds, but the module has none of the GUI parts (no `Selection`, `Control` or main window), so a successful import is not a test for a GUI. Guard every GUI line with `if FreeCAD.GuiUp:`.

Test an unfamiliar call headless before running it in a GUI session. In a GUI session a script that opens a modal dialog blocks the GUI thread (read); show a task panel instead.

## Start from a document and recompute

Take the active document or make one, add objects, then call `doc.recompute()` after every change that other objects depend on. An object that failed to recompute shows it in its `State`; read it before trusting `Shape`. When the request names no document, wrap the script in `doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Name")`.

## Units and scale

FreeCAD stores lengths in millimetres. Convert with `FreeCAD.Units.Quantity` and `getValueAs`, and parse user text with `FreeCAD.Units.parseQuantity`. Establish the units and the scale before measuring anything, and ask for one real dimension when the source has none; a file of unknown units can be off by a factor of 1000. State the unit beside every number you report.

## Check the result against its source

After building, compare the result with what it was built from (a requirement, a drawing, a mesh) and report the numbers, including what was approximated or assumed. A script that ran without an exception has shown only that it ran. Useful first checks are `shape.isValid()`, `shape.Volume`, `shape.BoundBox` and the object's `State`.

## Removed, renamed and deprecated APIs in 1.1

Check this table before writing code from memory or from an older example. Rows marked (read) were not run. A deprecated name that still exists in 1.1.4 may still run; use the new name anyway.

| Do not use | Use instead |
|---|---|
| `from PySide2 import ...` | `from PySide import ...` (FreeCAD's shim) or `PySide6` |
| `dialog.exec_()` (read) | `dialog.exec()` |
| `getStandardButtons` returning `int(A \| B)` (read) | return the flag itself: `SB.Ok \| SB.Cancel` |
| `import FEM` | `import Fem` and `import ObjectsFem` |
| `ObjectsFem.makeSolverCalculixCcxTools` | `makeSolverCalculiXCcxTools` or `makeSolverCalculiX` |
| Gmsh `mesh.Part = obj` | `mesh.Shape = obj` |
| `import Drawing` | `import TechDraw` |
| the `importOBJ` module | `Mesh.export([obj], "x.obj")` |
| `sketch.Support = ...` | `sketch.AttachmentSupport = [(plane, "")]` with `sketch.MapMode = "FlatFace"` |
| `Sketcher.Constraint("Fixed", ...)` | `Block` to lock geometry, or a `Coincident` constraint to the origin `(-1, 1)` |
| `Draft.makeArray(...)` (the name still exists in 1.1.4) | `Draft.make_ortho_array`, `make_polar_array`, `make_circular_array` |
| Draft camelCase names (`makeLine`, `makeCircle`; still present as aliases in 1.1.4) | snake_case names (`make_line`, `make_circle`) |
| `ViewObject.DiffuseColor` (read) | `ViewObject.ShapeAppearance` (a list of `FreeCAD.Material`) and `ViewObject.Transparency` |
| the icon path `:/icons/Part_Box.svg` (read) | `:/icons/freecad.svg` or a file path |
| the `Std_Macro` command (read) | `Std_DlgMacroExecute` |
| the Raytracing and Drawing workbenches | removed from the core |

The module that holds the CAM workbench is still imported as `import Path`.

A PartDesign feature such as a Pad belongs inside a `PartDesign::Body`: make it with `body.newObject("PartDesign::Pad", ...)`. A Pad made with `doc.addObject` and given a profile also recomputed to a valid solid in a headless check on 1.1.4, so the tool does not stop you; keeping features in a Body is the modelling rule (read), not an error the tool raises.

## Shorthand to API

When a request is in shorthand, map the words to calls: box to `Part.makeBox`, cylinder to `Part.makeCylinder`, sphere to `Part.makeSphere`, merge, combine or join to `.fuse()`, subtract or cut to `.cut()`, intersect to `.common()`, round edges to `.makeFillet()`, and bevel to `.makeChamfer()`. Assume millimetres unless the request says otherwise, and say so.

## Common mistakes

| Mistake | Instead |
|---|---|
| Using `FreeCADGui` or `ViewObject` without a guard | Wrap it in `if FreeCAD.GuiUp:` |
| Reading `Shape` before `doc.recompute()` | Recompute, then check `State` |
| Trusting a number whose unit is unknown | Establish the scale first and print the unit |
| Copying an older example unchanged | Check it against the table above |
| Reporting "it ran" as "it is right" | Compare with the source and report the numbers |
