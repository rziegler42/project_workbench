---
name: freecad-reverse-engineering
description: Use when rebuilding a scanned or imported mesh (STL, OBJ, 3MF) as an editable FreeCAD model: triage, repair, fitting planes and cylinders, choosing features, and checking deviation. Includes the mesh_report.py script. Mesh basics are in freecad-mesh.
---

# FreeCAD reverse engineering

This skill is for turning a mesh into an editable, parametric FreeCAD model whose dimensions are named values, and for proving the result against the mesh. If FreeCAD or `freecadcmd` is not available, stop and tell the owner. A faceted solid from `makeShapeFromMesh` and `makeSolid` is not reverse engineering and is not the goal. The mesh calls are in `freecad-mesh`, the features are in `freecad-partdesign`, and named dimensions are in `freecad-parameters`. The advice was written against FreeCAD 1.1.4. Every Python example in `reference.md` was run there, and so was the script on generated meshes; statements from the owner's work on real scans are marked (read).

## The script

`scripts/mesh_report.py` sits beside this `SKILL.md`. It needs only FreeCAD's own Python (numpy is part of it) and gives triage, a safe repair of a copy, plane and cylinder fitting, and a deviation check.

Run it with `freecadcmd <this folder>/scripts/mesh_report.py -- model.stl [--repair] [--min-component N] [--json out.json]`. It prints a JSON report and, with `--json`, writes the same text to that file. It refuses a `--json` target that is the input file, a symbolic link, or not named `*.json`. Or import it: put the `scripts` folder on `sys.path`, `import mesh_report as mr`, and call `mr.load(path)`, `mr.triage(mesh)`, `mr.repair(mesh, min_component_facets)`, `mr.fit_primitives(mesh)` and `mr.deviation(mesh, shape, samples, tol)`. Importing it runs nothing.

## The workflow, in order, reporting numbers at each step

1. **Triage** with `mr.triage(mesh)`. Check the units first: a bounding box under 1 mm or over 2 m is almost always a unit error. Read the `notes`. `tiny_components` counts every component of 20 facets or fewer, so on a very coarse mesh the whole part is counted as debris.
2. **Repair a copy** with `mesh, log = mr.repair(mesh)` and compare the facet count and volume per step. Its default `min_component_facets` is 20, which deletes a part with fewer facets than that. Debris, non-manifold edges and flipped normals are cheap to fix.
3. **Fit** with `fits, coverage = mr.fit_primitives(mesh)`. Planes and cylinders come back with a grade of `good`, `marginal` or `poor`, and `coverage` is the share of facets that a primitive explains.
4. **Choose the features** from the fits (below), then build them.
5. **Rebuild with named dimensions** so that changing a value changes the model.
6. **Check the deviation** with `mr.deviation(mesh, body.Shape, tol=...)` and report the maximum, the 95th percentile and the share within tolerance. Do not call the model done without this number.
7. **Iterate** on the worst regions and say plainly which are approximated.

## What to expect

- Plane segmentation with `mesh.getSegmentsOfType("Plane", 0.05, 30)` found the planes of a generated part. The built-in cylinder segmentation found none at deviation 0.05 on the same part, while the script's fit on facet normals recovered the radii 4.0 and 8.0 exactly. The owner reports that the built-in segmentation breaks a clean cylinder into fragments (read).
- Many small cylinders with similar axes and drifting radii mean the surface is not a cylinder but a torus, a sweep or freeform (read). Read `quality` and do not rebuild each patch as a cylinder.
- Facets that no primitive explains (1 minus coverage) are freeform. For a rotationally symmetric part use a revolution of a measured profile; otherwise `ReverseEngineering.approxSurface` or the Surface workbench, and say the region is approximate. `approxSurface` and `normalEstimation` document their arguments; `approxCurve`, `poissonReconstruction`, `regionGrowingSegmentation`, `sampleConsensus` and `featureSegmentation` exist in 1.1.4 but their behaviour was not tested, so test one before relying on it.
- A scan is noisy. Tolerances that suit a mesh exported from CAD are too tight for a scan: take `tol` from the scanner's stated accuracy and say what you chose.

## Repair, and what is safe

`mr.repair` applies `removeDuplicatedPoints`, `removeDuplicatedFacets`, `removeComponents`, `harmonizeNormals`, `fixDegenerations`, `removeNonManifolds` and `fixIndices` to a copy and logs each step. On a mesh with one stray triangle it removed that triangle and made the mesh a closed solid, with the volume changing by the triangle's share only. The calls the script leaves out (`removeNeedles`, `optimizeTopology`, `fixSelfIntersections`) are described in `freecad-mesh`.

## Choose features from the fits (read)

| Fit result | Build |
|---|---|
| Planes facing plus or minus Z at two levels, a bounding box in XY | a base sketch and a Pad (height is the distance between the planes) |
| A cylinder with its axis parallel to Z, radius r, inside the body | a Pocket (a hole) |
| A cylinder with its axis parallel to Z, outside the body | a Pad (a boss) |
| Coaxial cylinders of many radii around a rotation axis | a Revolution of a measured profile |
| Identical features at regular spacing | a LinearPattern or PolarPattern of one feature |
| Poor or marginal fits, uncovered facets | freeform: say so, approximate, report the deviation |

A cylinder's `axis` and `point` give its position. Snap an axis within a degree or two of a world axis to that axis, and near-equal radii to one value, before you build, because scans are noisy.

## Report to the owner

State the mesh health before and after repair, the coverage, which features were fitted and with what grade, which regions are freeform or approximate, the deviation figures against the stated tolerance, and every dimension that was snapped or rounded. A worked rebuild is in `reference.md`.

## Common mistakes

| Mistake | Instead |
|---|---|
| Making a solid from the mesh and stopping | Rebuild it from features with named dimensions |
| Reporting the model without a deviation figure | Run `mr.deviation` and report the numbers |
| Rebuilding every fitted patch as its own cylinder | Read `quality`; a poor fit is not a cylinder |
| Tight tolerances on a scan | Take the tolerance from the scanner's accuracy |
| The default `min_component_facets` on a coarse mesh | Set it below the facet count of the part |
