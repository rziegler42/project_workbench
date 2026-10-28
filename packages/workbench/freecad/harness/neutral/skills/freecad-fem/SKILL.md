---
name: freecad-fem
description: Use when scripting a FreeCAD FEM analysis: the analysis, solver, material, constraints and Gmsh mesh, generating the mesh, running CalculiX, reading results, and checking them against a hand calculation.
---

# FreeCAD FEM

This skill is for finite element analysis from Python in FreeCAD 1.1, with the CalculiX solver and the Gmsh mesher. If FreeCAD, `freecadcmd`, `ccx` or `gmsh` is not available, stop and tell the owner. On the FreeCAD used here the solver and the mesher came with it, and the runs had their folder on `PATH`. The environment and the table of removed APIs are in `freecad-python`, and checking a number against another is `freecad-measure-and-inspection`. The advice was written against FreeCAD 1.1.4, and every example in `reference.md` was run there, including the solver.

## Build the analysis

1. `ObjectsFem.makeAnalysis(doc, name)`.
2. A solver: `ObjectsFem.makeSolverCalculiXCcxTools(doc, name)`, then set `AnalysisType = "static"`, `GeometricalNonlinearity = "linear"`, `ThermoMechSteadyState = False` and `MatrixSolverType = "default"`. The name with a lower-case `x` (`makeSolverCalculixCcxTools`) no longer exists. `ObjectsFem.makeSolverCalculiX` is the newer framework solver; it exists and was not exercised (read).
3. A material: `ObjectsFem.makeMaterialSolid`, then copy its `Material` dictionary, set `YoungsModulus` (`"210000 MPa"`), `PoissonRatio` and `Density`, and assign it back.
4. Constraints: `makeConstraintFixed` and `makeConstraintForce`, with `References = [(object, "FaceN")]`. A force also takes a `Direction`, an edge or a face of the solid as `(object, ["Edge2"])`, and `Reversed`.
5. A mesh: `ObjectsFem.makeMeshGmsh`. The property that names the solid is `Shape`; `Part` no longer exists and assigning it raises an `AttributeError`. Set `CharacteristicLengthMax` for the element size.
6. Add each of these to the analysis with `analysis.addObject(...)`.

## A force is not a bare number

`force.Force = 1000.0` is stored as `1000.0 mm*kg/s^2`, which is **1 N**. Newtons need a quantity: `force.Force = "1000 N"` or `App.Units.Quantity(1000, "N")`, stored as `1000000.0 mm*kg/s^2`. A load of 1 N instead of 1000 N gave a tip deflection a thousand times too small and an analysis that ran without complaint. Print `force.Force` and read its unit.

## Generate the mesh, then solve

The mesh must be made explicitly: `err = GmshTools(mesh).create_mesh()` from `femmesh.gmshtools`, which returns `None` on success. Then `ccxtools.FemToolsCcx(analysis, solver)` from `femtools`, and in order `update_objects()`, `setup_working_dir(folder)`, `setup_ccx()`, `check_prerequisites()` (an empty string when ready), `purge_results()`, `write_inp_file()`, `ccx_run()` (0 on success) and `load_results()`. Give the solver a working folder you made and remove afterwards; FreeCAD also writes its own temporary files for the mesher. With no mesh, `check_prerequisites()` returned "FEM mesh has neither volume nor shell or edge elements" and nothing ran; the source reports that the solver fails with a missing node set instead, which was not seen.

## Read the result

The result is a `Fem::FemResultObject` in the document. Its properties include `DisplacementLengths` and `DisplacementVectors`, the node stresses and strains (`NodeStressXX` and so on), `NodeNumbers` and `MaxShear`. `max(result.DisplacementLengths)` is the largest displacement, in millimetres.

## Check the answer against a hand calculation

A solver that ran has not shown that the answer is right. For a cantilever of 100 by 10 by 10 mm, fixed at one end and loaded with 1000 N across the other, beam theory gives a tip deflection of F L cubed over 3 E I, which is 1.905 mm for steel at 210000 MPa. The analysis gave:

| Element size | Elements | Tip deflection | Share of 1.905 |
|---|---|---|---|
| 5.0 mm | about 500 | about 1.15 mm | about 0.60 |
| 2.5 mm | about 3600 | about 1.59 mm | about 0.84 |
| 1.5 mm | about 15300 | about 1.78 mm | about 0.94 |

First-order elements are too stiff on a coarse mesh, so the answer approaches the true value from below as the mesh is refined. Refine until the result stops changing, say so, and report the element size and the figure at each level. Gmsh is not exactly repeatable: counts and tips varied by about 1% between runs.

## Common mistakes

| Mistake | Instead |
|---|---|
| `force.Force = 1000.0` | `"1000 N"` or `Quantity(1000, "N")`, and print it |
| Solving without a generated mesh | `GmshTools(mesh).create_mesh()` first |
| `mesh.Part = obj` | `mesh.Shape = obj` |
| Trusting one coarse mesh | Refine until the answer settles, and compare with a hand calculation |
| `ObjectsFem.makeSolverCalculixCcxTools` | `makeSolverCalculiXCcxTools` |
