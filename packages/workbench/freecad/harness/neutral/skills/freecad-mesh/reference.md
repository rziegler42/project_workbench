# Reference: Mesh and MeshPart examples

Every example below was run headless with `freecadcmd` on FreeCAD 1.1.4, and the printed value is in the comment. The
examples after "Helpers" use the function defined there, so run the helpers first in the same session. A few write a
small file into the current folder and remove it again.

## Helpers

```python
import os
import FreeCAD as App
import Part
import Mesh
import MeshPart

V = App.Vector


def box_mesh(w=10, d=10, h=10, at=(0, 0, 0)):
    shape = Part.makeBox(w, d, h, V(*at))
    return MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.1, AngularDeflection=0.5)
```

## Make, read and write a mesh

```python
mesh = box_mesh(10, 20, 30)
print(mesh.CountPoints, mesh.CountFacets, round(mesh.Volume, 1), round(mesh.Area, 1), mesh.isSolid())
# 8 12 6000.0 2200.0 True
mesh.write("example.stl")
mesh.write("example.obj")
again = Mesh.Mesh("example.stl")
print(again.CountFacets, round(again.Volume, 1))                  # 12 6000.0
os.remove("example.stl")
os.remove("example.obj")
```

## Make a mesh from triangles

```python
verts = [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0], [5, 5, 10]]
facets = [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4], [0, 1, 2], [0, 2, 3]]
pyramid = Mesh.Mesh([verts[a] + verts[b] + verts[c] for a, b, c in facets])   # nine numbers per triangle
print(pyramid.CountFacets, pyramid.CountPoints)

single = Mesh.Mesh()
single.addFacet(0, 0, 0, 1, 0, 0, 0, 1, 0)
print(single.CountFacets)                                         # 1
```

## Combine and change meshes

```python
a = box_mesh(10, 10, 10)
b = box_mesh(10, 10, 10, at=(5, 0, 0))
# unite, intersect and difference RETURN a new mesh; they do not change `a`
for name in ("unite", "intersect", "difference"):
    result = getattr(a, name)(b)
    print(name, result.CountFacets, round(result.Volume, 1), result.isSolid(), round(a.Volume, 1))

grown = a.copy()
grown.offset(1.0)                                        # offset and smooth change the mesh in place
print(round(a.Volume, 1), round(grown.Volume, 1))

ball = MeshPart.meshFromShape(Shape=Part.makeSphere(10), LinearDeflection=0.05, AngularDeflection=0.2)
before = ball.Volume
ball.smooth()
print(round(before, 1), round(ball.Volume, 1))          # smoothing changes the volume: compare before and after

cube = box_mesh(10, 10, 10)                              # only 12 facets: smoothing destroys it
cube.smooth()
print(round(cube.Volume, 1))                             # 95.4 where the volume was 1000.0
```

## Between a mesh and a shape

```python
shape = Part.makeCylinder(5, 20)
mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.3)
print(mesh.CountFacets, round(mesh.Volume, 1), round(shape.Volume, 1))          # the mesh is slightly smaller

rebuilt = Part.Shape()
rebuilt.makeShapeFromMesh(mesh.Topology, 0.05)       # a shell of one triangle face per facet
solid = Part.makeSolid(rebuilt)                      # valid only for a closed mesh
print(len(rebuilt.Faces) == mesh.CountFacets, solid.ShapeType, solid.isValid())
print(len(solid.Faces), solid.Faces[0].Surface.__class__.__name__)              # faceted: every face is a plane
```

## Health of a mesh

```python
mesh = box_mesh(10, 10, 10)
good = {
    "solid": mesh.isSolid(),
    "non-manifold": mesh.hasNonManifolds(),
    "self-intersections": mesh.hasSelfIntersections(),
    "flipped normals": mesh.countNonUniformOrientedFacets(),
    "corrupted": mesh.hasCorruptedFacets(),
    "components": len(mesh.getSeparateComponents()),
}
print(good)

bad = mesh.copy()
bad.addFacet(100, 100, 100, 101, 100, 100, 100, 101, 100)     # a stray triangle far away: debris
first = bad.Facets[0]
p = [tuple(q) for q in first.Points]
bad.addFacet(*(p[0] + p[1] + p[2]))                           # the same triangle again: a duplicate facet
print(bad.CountFacets, bad.isSolid(), len(bad.getSeparateComponents()))
print(sorted(len(c.Facets) if hasattr(c, "Facets") else c.CountFacets for c in bad.getSeparateComponents()))
```

## Repair a copy, step by step

```python
mesh = box_mesh(10, 10, 10)
mesh.addFacet(100, 100, 100, 101, 100, 100, 100, 101, 100)               # debris
first = mesh.Facets[0]
p = [tuple(q) for q in first.Points]
mesh.addFacet(*(p[0] + p[1] + p[2]))                                      # a duplicate facet
before = (mesh.CountFacets, round(mesh.Volume, 3), mesh.isSolid())

work = mesh.copy()
for name, step in (("removeDuplicatedPoints", work.removeDuplicatedPoints),
                   ("removeDuplicatedFacets", work.removeDuplicatedFacets),
                   ("removeComponents", lambda: work.removeComponents(5)),   # drops components of fewer than 5 facets
                   ("harmonizeNormals", work.harmonizeNormals),
                   ("fixDegenerations", work.fixDegenerations),
                   ("removeNonManifolds", work.removeNonManifolds),
                   ("fixIndices", work.fixIndices)):
    facets, volume = work.CountFacets, work.Volume
    step()
    print("%-24s facets %3d -> %3d   volume %8.3f -> %8.3f" % (name, facets, work.CountFacets, volume, work.Volume))
print(before, (work.CountFacets, round(work.Volume, 3), work.isSolid()))
```

## Reading a mesh

```python
import FreeCAD as App

mesh = box_mesh(10, 10, 10)
sections = mesh.crossSections([((0, 0, 5.0), (0, 0, 1))], 0.1)       # [(point, normal)], minimum distance
print(len(sections), len(sections[0]))                                # one plane, its polylines
print(len(mesh.getPlanarSegments(0.05, 30)), len(mesh.getPlanarSegments(0.05, 1)))   # 0 6: the minimum is in facets
print(len(mesh.getCurvaturePerVertex()))                              # one value per vertex
wires = MeshPart.wireFromMesh(mesh)
print(type(wires).__name__, len(wires) if hasattr(wires, "__len__") else "")
top = mesh.copy()
top.trimByPlane(App.Vector(0, 0, 5), App.Vector(0, 0, 1))
print(top.CountFacets, top.isSolid())                                 # a trimmed mesh is open: its Volume means nothing
projected = MeshPart.projectShapeOnMesh(Part.makeLine((5, 5, 20), (5, 5, 30)), mesh, 1.0)
print(type(projected).__name__)
```
