---
name: freecad-mesh
description: Use when scripting FreeCAD meshes: loading and writing STL or OBJ, mesh properties and operations, converting between meshes and shapes, and checking and repairing a mesh before use. For rebuilding a mesh as a parametric model use freecad-reverse-engineering.
---

# FreeCAD Mesh

This skill is for the Mesh and MeshPart modules in FreeCAD 1.1: reading, checking, repairing and converting triangle meshes from Python. If FreeCAD or `freecadcmd` is not available, stop and tell the owner. The environment and the table of removed APIs are in `freecad-python`. Turning a scanned mesh into an editable model, with a script that reports on it, is `freecad-reverse-engineering`. The advice was written against FreeCAD 1.1.4, and every example in `reference.md` was run there unless it is marked (read).

## Load, make and write

`Mesh.Mesh(path)` reads a mesh file, and `mesh.write(path)` writes STL or OBJ by the file extension. A mesh can also be made from a list of triangles, nine numbers each, or grown with `addFacet(x1, y1, z1, x2, y2, z2, x3, y3, z3)`. `CountPoints`, `CountFacets`, `Volume`, `Area` and `isSolid()` describe it. A volume is only meaningful when `isSolid()` is true.

## Meshes and shapes

`MeshPart.meshFromShape(Shape=shape, LinearDeflection=..., AngularDeflection=...)` meshes a shape; the mesh is a little smaller than the shape (1564.9 against 1570.8 for a cylinder), and the deflection sets how much. The other way, `shape.makeShapeFromMesh(mesh.Topology, tolerance)` followed by `Part.makeSolid`, gives a valid solid for a closed mesh, but a faceted one: it has one planar face for each facet (164 for the cylinder above). That is not a parametric model and is not reverse engineering.

## Operations

`unite`, `intersect` and `difference` return a new mesh and do not change the one they are called on. On two boxes with coincident faces they gave wrong volumes (1166.7, 541.7 and 333.3, where 1500, 500 and 500 are right) and open meshes. Check `isSolid()` and compare the volume with a number you can compute, or do the Boolean on shapes and mesh the result. `offset` and `smooth` change the mesh in place. Smoothing shrank a finely meshed sphere by about 2.6%, and it collapsed a 12-facet cube to a tenth of its volume, so compare the volume before and after.

## Check a mesh before you use it

Read these first: `isSolid()`, `hasNonManifolds()`, `hasSelfIntersections()`, `countNonUniformOrientedFacets()` (flipped normals), `hasCorruptedFacets()` and `len(getSeparateComponents())`. Check the units: a bounding box under 1 mm or over 2 m is almost always a unit error, so ask for one real dimension.

## Repair a copy, one step at a time

Work on `mesh.copy()` and log the facet count and volume after each step. The safe steps, in this order, are `removeDuplicatedPoints`, `removeDuplicatedFacets`, `removeComponents(n)`, `harmonizeNormals`, `fixDegenerations`, `removeNonManifolds` and `fixIndices`. `removeComponents(n)` removes every component of fewer than `n` facets, so a value above the size of the part deletes the part: a 12-facet box was reduced to nothing by `removeComponents(20)`.

Do not apply these without looking (read, from the owner's measurements on a real scan): `removeNeedles` removed about a quarter of the facets, `optimizeTopology` brought back self-intersections, and `fixSelfIntersections` removed facets and left `isSolid()` false. If you call them, log the change and stop when the facet count or the volume moves by more than a few percent.

## Read a mesh

`crossSections([((x, y, z), (nx, ny, nz))], min_distance)` cuts it with planes, `getPlanarSegments(deviation, min_facets)` finds planes (the minimum is in facets, so a 12-facet cube has none at 30), `getCurvaturePerVertex()` gives one value per vertex, `MeshPart.wireFromMesh(mesh)` returns boundary wires (none for a closed mesh), `trimByPlane(base, normal)` cuts the mesh and leaves it open, so its volume means nothing, and `MeshPart.projectShapeOnMesh(shape, mesh, distance)` projects a shape onto it.

## Common mistakes

| Mistake | Instead |
|---|---|
| `mesh.unite(other)` and ignoring the return value | `result = mesh.unite(other)`, then check `result.isSolid()` |
| `removeComponents(n)` with `n` larger than the part | Choose `n` below the facet count of the part |
| Reporting a volume from a mesh that is not solid | Check `isSolid()` first |
| Treating a `makeSolid` result as a model | It is faceted; use `freecad-reverse-engineering` to rebuild it |
| Running a repair on the original | Repair a copy and log each step |
