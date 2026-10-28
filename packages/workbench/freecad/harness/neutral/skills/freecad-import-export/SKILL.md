---
name: freecad-import-export
description: Use when moving FreeCAD geometry in or out of files: STEP, IGES, BREP, STL, OBJ and 3MF export, reading them back, exporting every solid, saving documents, and checking an exported mesh before printing.
---

# FreeCAD import and export

This skill is for writing geometry from FreeCAD to files and reading files back, from Python in FreeCAD 1.1. If FreeCAD or `freecadcmd` is not available, stop and tell the owner. The environment is in `freecad-python`, mesh checks are in `freecad-mesh`, and number checks are in `freecad-measure-and-inspection`. Write exports to a folder the owner named, never into the project by default. The advice was written against FreeCAD 1.1.4, and every example in `reference.md` was run there, each in a temporary folder.

## Solid shapes: STEP, IGES and BREP

`Part.export([obj], path)` writes the format the file extension names: `.step`, `.iges` or `.brep`. A shape can also write itself with `shape.exportStep(path)`. `Part.read(path)` reads a file back as a shape. A STEP file read back as a `Solid`, and IGES and BREP files read back as a `Compound` holding it; the volume was the same, to two decimals, in all three. Compare the volume of the shape read back with the original and check `isValid()` before relying on a file.

## Meshes: STL, OBJ and 3MF

`Mesh.export([obj], path)` meshes a Part object and writes `.stl`, `.obj` or `.3mf`. Read a mesh file back with `Mesh.Mesh(path)`; this works for 3MF too, so existing 3MF files load the same way. A cylinder of radius 10 mm and height 20 mm gave 500 facets in each of the three formats in this run.

## 3MF for printing

3MF from FreeCAD is in millimetres (the file's XML says `unit="millimeter"`), so a slicer needs no scale factor.

How finely a Part object is meshed on export comes from FreeCAD's own tessellation setting, which differs between installs: the owner measured 124 facets for the default export of a cylinder, and this run measured 500. For a repeatable result, mesh the shape yourself with `MeshPart.meshFromShape(Shape=shape, LinearDeflection=..., AngularDeflection=...)`, put it in a `Mesh::Feature` and export that. A `LinearDeflection` of 0.02 and an `AngularDeflection` of 0.2 gave 280 facets for the cylinder, fewer than the default here. Choose the deflection below the printer's resolution (0.01 to 0.05 mm is typical, read); a smaller value makes a bigger file.

Check the file before it goes to a slicer. Read it back and require `isSolid()` true and `hasNonManifolds()` false. Compare `Volume` with the shape's and the bounding box with the intended size, to catch a unit or scale mistake, and allow for the meshing: at a deflection of 0.02 the cylinder read back as 6275.0 against 6283.2, and 19.99 mm against 20 mm. Ask the owner for the printer's minimum wall and overhang limits and do not assume them (read).

## Every solid in a document

Loop over `doc.Objects`, keep those with `obj.Shape.Solids`, and export each under its own name. Objects without a solid, such as a plane, are skipped.

## Whole documents and the Import module

`doc.saveAs(path)` writes a `.FCStd` file and `FreeCAD.openDocument(path)` reopens it with its objects and shapes. The `Import` module offers `export`, `insert`, `open`, `StepShape`, `readDXF`, `writeDXFObject` and `writeDXFShape` on 1.1.4. `Import.insert(path, document_name)` brings a STEP file into an open document as a new object, whose name comes from the file (it was `Part__Feature` for a part labelled `Part`). The DXF functions were listed and not exercised (read).

## Common mistakes

| Mistake | Instead |
|---|---|
| Sending a mesh to a slicer unchecked | Read it back; check `isSolid()`, `hasNonManifolds()`, the volume and the size |
| Relying on the default export's fineness | Mesh the shape yourself with chosen deflections |
| Expecting a `Solid` back from IGES or BREP | Take the solid out of the `Compound` |
| Writing exports into the project | Use a folder the owner named |
| Exporting a reference image or a helper object | Export only the solids you mean |
