---
name: freecad-parameters
description: Use when driving FreeCAD dimensions from named values: an App::VarSet or a Spreadsheet with aliases, expressions on feature properties and sketch constraints, derived values, and reading or clearing expressions.
---

# FreeCAD parameters

This skill is for holding a model's dimensions in named values and binding them to the model with expressions, in FreeCAD 1.1. If FreeCAD or `freecadcmd` is not available, stop and tell the owner. The environment is in `freecad-python`, naming a sketch constraint is in `freecad-sketcher`, and the features that take the values are in `freecad-partdesign`. The VarSet part follows the owner's practice. The Spreadsheet part and the comparison below were written by the author of this skill, not taken from the owner's text; every example in `reference.md` was run on FreeCAD 1.1.4.

## Two ways to hold the values

An `App::VarSet` is an object whose properties are the values. Each property has a type (`App::PropertyLength`, `PropertyAngle`, `PropertyInteger`, `PropertyBool`), a group and a tooltip, and a length keeps its unit.

A `Spreadsheet::Sheet` is a grid of cells. A cell holds text, a number, a quantity such as `30 mm`, or, when it starts with `=`, a formula over other cells. `sheet.setAlias(cell, name)` gives a cell the name an expression uses.

Neither is better in general. A VarSet suits a few typed, named values, and a sheet suits values that form a table, are computed from one another, or have to be read by other tools; a sheet can import and export files (read). If the project already uses one, follow it; if it uses neither, ask the owner which to use before choosing.

## Bind the values to the model

Bind a property with `obj.setExpression("Property", "Name.Value")`, for example `pad.setExpression("Length", "Dims.BaseHeight")` for a VarSet property or `"Params.height"` for a sheet alias. Bind a named sketch constraint the same way, with `sketch.setExpression("Constraints.width", "...")`. Derive a dependent value with an expression and do not type in its result: `Dims.Outer - 2 * Dims.Wall`. A formula in a sheet cell does the same inside the sheet.

Change a value and call `doc.recompute()`; the model follows. `obj.ExpressionEngine` lists an object's bindings, and `obj.setExpression("Property", None)` removes one.

## A bad expression is not refused when you set it

`setExpression` accepted an expression that names a property which does not exist. The failure shows only at the recompute: the object's `State` becomes `['Touched', 'Invalid']` and the console names the missing property. After binding, recompute and read `State`, and compare the result with the number you expect.

## Common mistakes

| Mistake | Instead |
|---|---|
| Typing in a value that can be derived | Bind an expression such as `Dims.Outer - 2 * Dims.Wall` |
| Binding and not recomputing | `doc.recompute()`, then read `State` |
| Choosing a VarSet or a sheet without looking at the project | Follow what the project uses, or ask the owner |
| Naming a constraint `h`, `mm` or `N` | Use a descriptive name (see `freecad-sketcher`) |
| Assuming `setExpression` checked the name | Read `State` after the recompute |
