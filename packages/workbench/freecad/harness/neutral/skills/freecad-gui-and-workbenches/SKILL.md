---
name: freecad-gui-and-workbenches
description: Use when building FreeCAD interface and scripted objects: commands, task panels, scripted FeaturePython objects with properties, view providers, Coin3D nodes, and custom workbenches. Most of the interface needs a GUI session.
---

# FreeCAD interface, scripted objects and workbenches

This skill is for extending FreeCAD 1.1 from Python: scripted objects that hold properties and rebuild a shape, and the commands, task panels, view providers and workbenches that put them in the interface. If FreeCAD or `freecadcmd` is not available, stop and tell the owner. The environment is in `freecad-python`, macros are in `freecad-macros`, and the FreeCAD MCP server is in `freecad-mcp`. The advice was written against FreeCAD 1.1.4. The scripted objects ran headless; the commands, task panels, view providers and workbench loading need a GUI session, a display or the workbench loader, so they are marked (read) and were not run. Examples are in `reference.md`.

## Scripted objects (run headless)

Make the object with `doc.addObject("Part::FeaturePython", name)` and give it a proxy class. The proxy's `__init__(obj)` sets `obj.Proxy = self` and adds properties with `obj.addProperty(type, name, group, tooltip)`; `execute(obj)` builds `obj.Shape` and runs on every recompute; `onChanged(obj, prop)` reacts to a change (for example showing a hidden property when a switch is turned on); and `__getstate__` and `__setstate__` save and restore the proxy.

- **Saving and reopening.** The proxy class must be importable from a module when the document is opened. Define it in a file on the path and import it, not in a throwaway script. The example saved a document, closed it and reopened it, and the proxy came back as an instance of its class.
- **Migrating an older document.** `onDocumentRestored(obj)` runs after a load. Add a property that an older version lacked, copy a renamed property's value and `removeProperty` the old one. A change made while restoring does not mark the object for recompute: in the example the shape stayed at its old volume until `obj.touch()` and a recompute. Do not name a new property after one every object already has, such as `Label2`, because `hasattr` is then already true.
- **Property types.** All of the common types were added to a scripted object: integers, floats, lengths and other quantities, strings, files and paths, booleans, enumerations, vectors, placements, matrices, links and lists of links, colours, materials, Python objects, lists and maps. For an enumeration, set the list of choices first and then the value, and read them back with `getEnumerationsOfProperty`.
- **Which objects refer to which.** `obj.InList` and `obj.OutList` give the objects that refer to it and that it refers to, and `InListRecursive` and `OutListRecursive` follow the chain.
- **Attachment.** Give a scripted object `addExtension("Part::AttachExtensionPython")`, then set `AttachmentSupport` and `MapMode`; the example placed a box on the face of a plate (a placement of z = 4.0 and an up-to-date state).

## Commands (needs a GUI session, read)

Register a class with `GetResources` (a pixmap, menu text, a tooltip, optionally a shortcut), `IsActive` and `Activated` by `FreeCADGui.addCommand("Unique_Name", MyCommand())`. The name must be unique. Make `IsActive` cheap: it is called often.

## Task panels and dialogs (needs a GUI session, read)

A task panel in the sidebar is the preferred way to build an interactive tool. Its class has a `form` (a widget, or a list of widgets for several pages), `accept`, `reject` and `getStandardButtons`; show it with `FreeCADGui.Control.showDialog(panel)` and close it with `FreeCADGui.Control.closeDialog()`. Return the flag itself from `getStandardButtons` (`Ok | Cancel`): converting it to an `int` fails in PySide6. Do not open a modal dialog (`exec()`) from code sent through the MCP `execute_code` tool, which blocks the GUI thread (see `freecad-mcp`). A standalone `QDialog`, file dialogs, message boxes and input dialogs come from `PySide`, which is FreeCAD's shim for PySide6. A `.ui` file from Qt Designer loads with `QUiLoader`.

## View providers and the 3D view (needs a GUI session, read)

A view provider controls how an object looks in the tree and the 3D view: `attach`, `getDisplayModes`, `getDefaultDisplayMode`, `setDisplayMode`, `getIcon`, `updateData`, `onChanged`, `doubleClicked` and, if the object has children, `claimChildren`. Create it only under `if FreeCAD.GuiUp:`, since `ViewObject` is `None` headless. Colours and transparency are set on the view object (`ShapeAppearance`, `ShapeColor` and `Transparency`, which runs from 0 to 100; see `freecad-python` for the removed `DiffuseColor`). The camera calls are `viewIsometric`, `viewFront`, `fitAll`, `setCameraType` and `saveImage`.

## Coin3D nodes

Coin3D nodes can be built without a view: a `coin.SoSeparator` with a material, a transform and a shape, and its children counted and read back. Putting them in the 3D view needs the scenegraph of the active view, `FreeCADGui.ActiveDocument.ActiveView.getSceneGraph()`, and so a GUI session (read). Remove what you added when you finish.

## A workbench

A workbench is a folder with `Init.py` (runs at start-up without a GUI), `InitGui.py` (runs at GUI start-up and defines the workbench), a module of commands, and `Resources/icons`. `Init.py` can register importers and exporters with `FreeCAD.addImportType` and `addExportType`; in the example both registered and read back. `InitGui.py` defines a `FreeCADGui.Workbench` subclass with `MenuText`, `ToolTip`, an icon, `Initialize` (import the command module here, not at the top, and call `appendToolbar` and `appendMenu`), `Activated`, `Deactivated`, `ContextMenu` and `GetClassName`, then calls `FreeCADGui.addWorkbench`. The workbench loader is not available headless, so this part is read. Where FreeCAD looks for workbenches is in `freecad-macros`; put nothing in the owner's folders without the owner's word.

## Common mistakes

| Mistake | Instead |
|---|---|
| A proxy class defined only in a throwaway script | Define it in a module that can be imported when the document opens |
| Changing a property in `onDocumentRestored` and expecting a rebuild | `obj.touch()`, then recompute |
| Adding a property named like a built-in one | Choose a name `hasattr` does not already find |
| Setting an enumeration's value before its choices | Set the list first |
| Creating a view provider headless | Guard it with `FreeCAD.GuiUp` |
| `getStandardButtons` returning an `int` | Return the flag |
| A modal dialog from the MCP `execute_code` tool | Use a task panel |
