---
name: freecad-techdraw
description: Use when scripting FreeCAD's TechDraw workbench: a drawing page from a template, projected views of a part, dimensions and annotations, and DXF or SVG export. For the older Drawing workbench see freecad-python; for sketches use freecad-sketcher.
---

# FreeCAD TechDraw

This skill is for the TechDraw workbench in FreeCAD 1.1, used from Python without the interface. If FreeCAD or `freecadcmd` is not available, or `import TechDraw` fails, stop and tell the owner. The environment and the table of removed APIs are in `freecad-python`; the old `Drawing` workbench is gone in 1.1 and TechDraw replaces it. The skill was written from runs, not from experience of using the workbench: every example in `reference.md` was run headless on FreeCAD 1.1.4, and a statement here that was not run is marked (read). A run shows that an example works on that version, not that it is the best way. The shape a view is made from comes from `freecad-part` or `freecad-partdesign`.

## What works headless

`import TechDraw` works with `freecadcmd`. `import TechDrawGui` fails there ("Cannot load Gui module in console application"), so everything that needs the interface is out of reach: the TechDraw commands, the page viewer, and anything that draws a page on screen (read). Document objects of the 46 TechDraw types can be created and computed without it.

| Object | Made with | Main properties |
|---|---|---|
| Page | `TechDraw::DrawPage` | `Template`, `Scale`, `ProjectionType` (`First angle` or `Third angle`), `Views` |
| Template | `TechDraw::DrawSVGTemplate` | `Template` (an SVG file), `Width`, `Height`, `Orientation`, `EditableTexts` |
| Projected view | `TechDraw::DrawViewPart` | `Source`, `Direction`, `XDirection`, `Scale`, `ScaleType`, `X`, `Y`, `Rotation` |
| Dimension | `TechDraw::DrawViewDimension` | `Type`, `MeasureType`, `References2D`, `References3D`, `FormatSpec` |
| Annotation | `TechDraw::DrawViewAnnotation` | `Text` (a list of lines), `TextSize`, `X`, `Y` |

`TechDraw::DrawViewSection`, `DrawProjGroup` and `DrawViewDetail` exist, with `BaseView`, `SectionNormal` and `SectionOrigin` (section), `Anchor` and `Views` (projection group) and `BaseView`, `AnchorPoint` and `Radius` (detail), but no example for them was run (read).

## A page from a template

FreeCAD's resource folder holds `Mod/TechDraw/Templates` with `Default_Template_A4_Landscape.svg`, `HowToExample.svg` and the folders `ASME` and `ISO`. Build the template path from `App.getResourceDir()`, as the Helpers block in `reference.md` does. The A4 landscape template gave a page 297 mm by 210 mm, `Scale` 1.0 and `ProjectionType` `First angle`. Create the page and the template object, set `page.Template = template`, and recompute; both were `Up-to-date`. `EditableTexts` was empty for this template. Computing a page writes a copy of the template into FreeCAD's user cache folder, outside the project.

## A projected view

Create a `DrawViewPart`, add it with `page.addView(view)`, then set `Source` (a list of objects, here a `Part::Feature` box), `Direction`, `XDirection`, `Scale`, `X` and `Y`, and recompute. The example adds the view to the page first; the other order was not run. `Direction` `(0, 0, 1)` looks down the z axis. A 40 by 20 by 10 box viewed that way gave 4 visible edges, no hidden edges and 4 visible vertices. `getVisibleEdges()`, `getHiddenEdges()`, `getVisibleVertexes()` and `getEdgeByIndex(n)` read what the view computed; `getBoundingBox` and `getEdgeCount` do not exist.

`TechDraw.project(shape, direction)` needs no page and no document: it returned four shapes (with 4, 0, 4 and 0 edges; what each of the four holds was not checked), `projectEx` returned 10, and `projectToSVG` and `projectToDXF` returned strings. Use these to get the outline of a part without building a page.

## Dimensions and annotations

A dimension needs a view to refer to. Create `DrawViewDimension`, add it to the page, set `Type` (`Distance`, `DistanceX`, `DistanceY`, `DistanceZ`, `Radius`, `Diameter`, `Angle`, `Angle3Pt` or `Area`), `MeasureType` (`True` or `Projected`) and `References2D = [(view, "Edge0")]`, then recompute. `getRawValue()` gave the length: 20.0 for edges 0 and 1 and 40.0 for edges 2 and 3 of the box view. The edge numbers are the view's own, so read a value and check it before you trust a number. Other `Type` values and `References3D` were not run (read).

An annotation is a `DrawViewAnnotation` with `Text` set to a list of lines, a position (`X`, `Y`, in millimetres on the page) and `TextSize`. It computed and appeared in `page.Views`.

## Export

`TechDraw.writeDXFPage(page, path)` and `TechDraw.writeDXFView(view, path)` each wrote a DXF file (4903 bytes for the box page and for the box view). `viewPartAsSvg(view)` and `viewPartAsDxf(view)` return strings and write nothing. A document with a page saved with `doc.saveAs` to a temporary folder. Exporting a page as PDF or SVG with the interface, and printing, were not run (read).

## Check the result

Do every check below before relying on a page, and call `doc.recompute()` first.

| Check | How |
|---|---|
| Everything computed | `obj.State` is `['Up-to-date']` for the page, the template, each view and each dimension |
| The view holds the part | `len(view.getVisibleEdges())` is not zero, and `page.Views` lists the view |
| A dimension is the one you meant | `dim.getRawValue()` against a length you can compute |
| The export has content | the file exists and `os.path.getsize(path)` is not zero |

## Common mistakes

| Mistake | Instead |
|---|---|
| Importing `TechDrawGui` in `freecadcmd` | Use `TechDraw` only |
| Writing `import Drawing` | Use `TechDraw`; see `freecad-python` |
| Using a template path typed by hand | Build it from `App.getResourceDir()` |
| Trusting an edge number for a dimension | Read `getRawValue()` and compare |
| Calling `getEdgeCount` or `getBoundingBox` on a view | Use `len(view.getVisibleEdges())` |
| Writing export files into the project | Use a temporary folder |

Examples for every step above are in `reference.md`.
