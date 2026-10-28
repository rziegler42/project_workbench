# Reference: FEM examples

Every example below was run headless with `freecadcmd` on FreeCAD 1.1.4, and the printed value is in the comment. The
solver and the mesher that ran were the CalculiX (`ccx`) and Gmsh programs that came with that FreeCAD, found on `PATH`.
FreeCAD writes its own temporary files for the mesh and the solver; the examples give the solver a working folder and
remove it afterwards. The examples after "Helpers" use what is defined there.

## Helpers

```python
import math
import os
import shutil
import tempfile

import FreeCAD as App
import ObjectsFem
import Part

FORCE_N, LENGTH, SIDE, YOUNG_MPA = 1000.0, 100.0, 10.0, 210000.0
# A cantilever with an end load: the tip deflection is F * L^3 / (3 * E * I), with I = side^4 / 12.
EXPECTED_TIP_MM = FORCE_N * LENGTH ** 3 / (3 * YOUNG_MPA * SIDE ** 4 / 12)


def build_beam(doc, mesh_length=2.5):
    """A beam of 100 x 10 x 10 mm, fixed at one end face and loaded across the other, with a mesh object."""
    obj = doc.addObject("Part::Feature", "Beam")
    obj.Shape = Part.makeBox(LENGTH, SIDE, SIDE)
    doc.recompute()

    analysis = ObjectsFem.makeAnalysis(doc, "Analysis")
    solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "Solver")
    solver.AnalysisType = "static"
    solver.GeometricalNonlinearity = "linear"
    solver.ThermoMechSteadyState = False
    solver.MatrixSolverType = "default"
    analysis.addObject(solver)

    material = ObjectsFem.makeMaterialSolid(doc, "Steel")
    data = material.Material
    data["Name"] = "Steel"
    data["YoungsModulus"] = "210000 MPa"
    data["PoissonRatio"] = "0.3"
    data["Density"] = "7900 kg/m^3"
    material.Material = data
    analysis.addObject(material)

    fixed = ObjectsFem.makeConstraintFixed(doc, "Fixed")
    fixed.References = [(obj, "Face1")]
    analysis.addObject(fixed)

    force = ObjectsFem.makeConstraintForce(doc, "Force")
    force.References = [(obj, "Face2")]
    force.Force = App.Units.Quantity(FORCE_N, "N")      # a bare number would be in kg*mm/s^2: 1000.0 is only 1 N
    force.Direction = (obj, ["Edge2"])
    force.Reversed = False
    analysis.addObject(force)

    mesh = ObjectsFem.makeMeshGmsh(doc, "FEMMesh")
    mesh.Shape = obj                                    # the property is Shape
    mesh.CharacteristicLengthMax = mesh_length
    analysis.addObject(mesh)
    doc.recompute()
    return obj, analysis, solver, mesh


def solve(analysis, solver, folder):
    """Run the CalculiX tools; return (prerequisite message, solver status)."""
    from femtools import ccxtools
    fea = ccxtools.FemToolsCcx(analysis, solver)
    fea.update_objects()
    fea.setup_working_dir(folder)
    fea.setup_ccx()
    message = fea.check_prerequisites()                 # an empty string when ready
    if message:
        return message, None
    fea.purge_results()
    fea.write_inp_file()
    status = fea.ccx_run()                              # 0 on success
    fea.load_results()
    return message, status


def results_of(doc):
    return [o for o in doc.Objects if o.TypeId.startswith("Fem::FemResultObject")]
```

## A complete static analysis

```python
from femmesh.gmshtools import GmshTools

doc = App.newDocument("Fem")
obj, analysis, solver, mesh = build_beam(doc)
error = GmshTools(mesh).create_mesh()                  # None on success: the mesh must be made before solving
doc.recompute()
print(error, mesh.FemMesh.NodeCount, mesh.FemMesh.VolumeCount)

folder = tempfile.mkdtemp()
message, status = solve(analysis, solver, folder)
print(repr(message), status)
results = results_of(doc)
print(len(results))
tip = max(results[0].DisplacementLengths)
print(round(tip, 3), round(EXPECTED_TIP_MM, 3), round(tip / EXPECTED_TIP_MM, 3))      # about 1.59 1.905 0.84: first-order elements are stiff
shutil.rmtree(folder)
```

## A bare number is not in newtons

```python
doc = App.newDocument("Units")
obj, analysis, solver, mesh = build_beam(doc)
force = doc.getObject("Force")
force.Force = 1000.0
print(force.Force)                                      # 1000.0 mm*kg/s^2, which is 1 N
force.Force = "1000 N"
print(force.Force)                                      # 1000000.0 mm*kg/s^2
force.Force = App.Units.Quantity(1000, "N")
print(force.Force)                                      # the same
```

## Refine the mesh until the answer settles

```python
from femmesh.gmshtools import GmshTools

for length in (5.0, 2.5, 1.5):
    doc = App.newDocument("Refine")
    obj, analysis, solver, mesh = build_beam(doc, length)
    GmshTools(mesh).create_mesh()
    doc.recompute()
    folder = tempfile.mkdtemp()
    message, status = solve(analysis, solver, folder)
    tip = max(results_of(doc)[0].DisplacementLengths)
    print(length, mesh.FemMesh.VolumeCount, status, round(tip, 3), round(tip / EXPECTED_TIP_MM, 3))
    shutil.rmtree(folder)
    App.closeDocument(doc.Name)
# about: 5.0 -> 500 elements, tip 1.15 (0.60); 2.5 -> 3600, tip 1.59 (0.84); 1.5 -> 15300, tip 1.78 (0.94).
# The tip approaches 1.905 from below. Gmsh is not exactly repeatable: counts and tips varied by about 1% between runs.
```

## What a result object holds

```python
from femmesh.gmshtools import GmshTools

doc = App.newDocument("Result")
obj, analysis, solver, mesh = build_beam(doc)
GmshTools(mesh).create_mesh()
doc.recompute()
folder = tempfile.mkdtemp()
solve(analysis, solver, folder)
result = results_of(doc)[0]
print([p for p in result.PropertiesList if not p.startswith(("Label", "Visibility", "Proxy", "ExpressionEngine"))][:24])
print(len(result.NodeNumbers), len(result.DisplacementLengths))
shutil.rmtree(folder)
```

## Without a mesh the solver fails

```python
doc = App.newDocument("NoMesh")
obj, analysis, solver, mesh = build_beam(doc)
folder = tempfile.mkdtemp()
try:
    message, status = solve(analysis, solver, folder)
    print(repr(message), status, len(results_of(doc)))
except Exception as error:
    print("raised", type(error).__name__, str(error)[:80])
shutil.rmtree(folder)
```

## The mesh property is Shape, not Part

```python
doc = App.newDocument("Property")
obj, analysis, solver, mesh = build_beam(doc)
print(hasattr(mesh, "Shape"), hasattr(mesh, "Part"))
try:
    mesh.Part = obj
    print("assigned")
except Exception as error:
    print("raised", type(error).__name__)
```

## Names of the solver makers

```python
print({n: hasattr(ObjectsFem, n) for n in ("makeSolverCalculixCcxTools", "makeSolverCalculiXCcxTools",
                                           "makeSolverCalculiX", "makeAnalysis", "makeMaterialSolid",
                                           "makeConstraintFixed", "makeConstraintForce", "makeMeshGmsh")})
```
