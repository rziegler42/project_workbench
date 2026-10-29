---
name: freecad-draft
description: Use when scripting FreeCAD's Draft workbench: 2D lines, circles, rectangles, polygons and wires, move, rotate, scale and offset, and rectangular, polar, circular and path arrays. For constrained sketches use freecad-sketcher; for solids use freecad-part.
---

# FreeCAD Draft

This skill is for the Draft workbench in FreeCAD 1.1, used from Python without the interface. If FreeCAD or `freecadcmd` is not available, or `import Draft` fails, stop and tell the owner. The environment and the table of removed APIs are in `freecad-python`; this skill is the Draft part of it. It was written from runs, not from experience of using the workbench: every example in `reference.md` was run headless on FreeCAD 1.1.4, and a statement here that was not run is marked (read). A run shows that an example works in a headless session, not that it is the best way. Plain constrained sketches are in `freecad-sketcher`, and solids and booleans are in `freecad-part`.

## What a Draft object is

Each `Draft.make_...` call adds a document object and returns it: a `Part::Part2DObjectPython` for a circle, rectangle or polygon, and a `Part::FeaturePython` for a line, wire, spline, array or clone. Call `doc.recompute()` and then read `obj.Shape`; every run did. The shapes are plain Part shapes, so `Length`, `Area`, `BoundBox` and the rest of `freecad-part` apply.

| Call | Gives |
|---|---|
| `make_line(p1, p2)` | a `Wire` of one edge, length 10.0 for (0,0,0) to (10,0,0) |
| `make_circle(radius, placement=None, startangle=None, endangle=None)` | a `Face`, or an `Edge` when both angles are given |
| `make_rectangle(length, height)` | a `Face` of area length times height |
| `make_polygon(nfaces, radius=1, inscribed=True)` | a regular polygon `Face`; `radius=5` with 6 sides gave area 64.952 |
| `make_wire(points, closed=False)` | a `Wire`; `closed=True` gives a `Face` |
| `make_bspline(points)` | a spline through the points |
| `make_point(x, y, z)` | a `Vertex` |

A circle, rectangle, polygon or closed wire has `MakeFace` true, so its shape is a `Face`. Set `MakeFace = False` and recompute to get the closed `Wire`. To make a solid, extrude the face: `obj.Shape.extrude(vector)` gave a `Solid` of volume 150.0 for a 10 by 5 rectangle and 3 high, and `Draft.extrude(obj, vector)` gave a `Part::Extrusion` of the same volume. `Draft.make_sketch([obj])` turns objects into a Sketcher sketch (4 geometry elements for a rectangle), with no constraints; `autoconstraints=True` was not run (read).

## Move, rotate, scale

`move(obj_or_list, vector)`, `rotate(obj_or_list, angle_in_degrees, center, axis=Vector(0,0,1))` and `scale(obj_or_list, Vector(sx, sy, sz), center)` change the object in place by default: the call returns the same object and its `Placement` changes. With `copy=True` they leave the original and return a new object (a list for a list). A rectangle 10 by 5 rotated 45 degrees about the origin spans x from -3.536 to 7.071; scaled by 2 its area is 200.0.

## Offset

`offset(obj, delta, copy=False)` takes a vector, not a number. Its length is the distance, and its component across the first edge picks the side. Recompute the document before calling it: on an object whose shape is not computed it printed a notice and raised `AttributeError`. For a closed square from (0,0) to (10,10) the first edge lies on y = 0, and `Vector(0,-1,0)` made a face spanning -1 to 11 while `Vector(0,1,0)` made one spanning 1 to 9. A vector parallel to the first edge prints a notice (`something wrong with firstDir`) and offsets outward whichever way it points, so choose a vector across the first edge. With `copy=False` the object itself is changed. An open wire offsets to one side and stays a `Wire`.

## Arrays

| Call | Meaning | Result |
|---|---|---|
| `make_ortho_array(base, v_x, v_y, v_z, n_x, n_y, n_z)` | a grid; the vectors are the steps | a 3 by 2 grid of a 10 by 5 rectangle at a step of 15 gave 6 faces, 40.0 wide |
| `make_polar_array(base, number, angle, center)` | copies turned about the centre | over 360 the copies are evenly spread; over 180 the last copy is at 180 |
| `make_circular_array(base, r_distance, tan_distance, number, symmetry, axis, center)` | rings of copies | `number` is the number of rings, and the copies on a ring follow `tan_distance` |
| `make_path_array(base, path, count)` | copies along a path object | 4 copies along a line 30 long |

An array is a `Part::FeaturePython` whose shape is a `Compound` of the copies. It is parametric: setting `NumberX` from 3 to 5 and recomputing gave 10 faces, and the array follows its base object (changing the base rectangle's `Length` widened it). The other count, interval and angle properties are listed in its `PropertiesList` but were not set (read). `Fuse` is false by default; with it true, copies that do not touch stayed a `Compound` of the same faces, and what it does to touching copies was not run. `use_link=True` is the default; a grid made with `use_link=False` had the same type and gave the same faces. Do not measure a `Compound` of overlapping copies as one shape (see `freecad-part`).

## Names

The snake_case functions are the current names. The camelCase names that were run (`makeLine`, `makeCircle`, `makeRectangle`, `makePolygon`, `makeWire`) are the same function objects and printed no warning, so old code still works, but write the snake_case names in new code. `makeArray` is a different function with an older argument order: it works for a grid, prints a notice to use `make_ortho_array`, `make_polar_array` or `make_circular_array`, and is not the same object as `make_array`. `reference.md` lists the signatures read from 1.1.4.

## Not run

The module has 38 `make_...` functions. This skill covers only those above. Dimensions, text, labels, hatches, layers, working plane proxies, shape strings, `make_shape2dview`, snapping, `upgrade` and `downgrade`, and everything that needs the interface were not run for this module (read, not run), so check them before you rely on them.

## Common mistakes

| Mistake | Instead |
|---|---|
| Passing a distance to `offset` | Pass a vector across the first edge |
| Calling `offset` before a recompute | Recompute first |
| Expecting `move`, `rotate` or `scale` to leave the original | Pass `copy=True` |
| Reading the number of an array as the number of copies | For a circular array it is the number of rings |
| Measuring an array of overlapping copies as one shape | Fuse them first |
| Using `makeArray` in new code | Use the three `make_..._array` functions |
