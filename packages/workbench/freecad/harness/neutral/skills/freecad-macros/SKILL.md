---
name: freecad-macros
description: Use when writing or running FreeCAD macros: the macro file layout, a guarded main, the selection API in a GUI session, console messages, running a macro file from a script, and where FreeCAD looks for macros.
---

# FreeCAD macros

This skill is for macros in FreeCAD 1.1: Python files that FreeCAD runs, with or without a GUI. If FreeCAD or `freecadcmd` is not available, stop and tell the owner. The environment, the `GuiUp` guard and the table of removed APIs are in `freecad-python`, and scripted objects, commands and workbenches are in `freecad-gui-and-workbenches`. The advice was written against FreeCAD 1.1.4. The macro layout, the console calls and running a macro file were run there; the selection API needs a GUI session and is marked (read). Examples are in `reference.md`.

## The layout of a macro

A macro is a Python file, usually named `Name.FCMacro`. Start it with a header comment (the macro's name, a description and a version), then the imports, then a guard for the GUI parts, then a `main()` and the usual entry check:

- Import `FreeCADGui` and the Qt modules only inside `if FreeCAD.GuiUp:`, so the same file also runs under `freecadcmd`.
- In `main()`, take `FreeCAD.ActiveDocument` and stop with an error message if it is `None`. The example run did exactly that, with no document, and then built its box once a document was open.
- Finish with `doc.recompute()` and a message, and keep the work in `main()` under `if __name__ == "__main__":` so that the file can also be imported.

## The selection API (needs a GUI session, read)

`FreeCADGui.Selection.getSelection()` gives the selected objects. `getSelectionEx()` gives each selected object with its `SubElementNames` (such as `Face1`) and `SubObjects`, and `object.getSubObject(name)` returns the sub-shape. `addSelection(obj)`, `addSelection(obj, "Face1")`, `removeSelection` and `clearSelection` change it. A class with `addSelection`, `removeSelection`, `setSelection` and `clearSelection` methods, registered with `Selection.addObserver`, is told about changes. Under `freecadcmd` the `FreeCADGui` module imports but has no `Selection`, so guard every selection line with `FreeCAD.GuiUp`.

## Console messages

`FreeCAD.Console.PrintMessage`, `PrintWarning`, `PrintError` and `PrintLog` write a line (end it with a newline). On 1.1.4 the console object exposes only `GetObservers` among its observer functions, so a class that merely defines a `receive` method registers nothing; do not rely on catching console output from a macro.

## Run a macro from a script

`runpy.run_path(path, run_name="__main__")` runs a macro file and returns its namespace. Give it an explicit path, run only a macro you trust, and do not build the path from text you did not write. In a GUI session `FreeCADGui.runCommand("Std_DlgMacroExecute")` opens the macro dialog (read).

## Where FreeCAD looks

`FreeCAD.getUserMacroDir(True)` is the user's macro folder, `FreeCAD.getUserAppDataDir()` is the user data folder (a workbench of your own goes in a `Mod` folder inside it, which does not exist until someone makes it), and `FreeCAD.getResourceDir()` is the system resource folder with its own `Mod`. Each call returned a folder that exists. Do not copy a macro or a workbench into the owner's folders without the owner's word.

## Common mistakes

| Mistake | Instead |
|---|---|
| Importing `FreeCADGui` at the top of a macro | Import it under `if FreeCAD.GuiUp:` |
| Assuming a document is open | Check `FreeCAD.ActiveDocument` and say so if it is `None` |
| Running a macro from a path built from outside text | Use an explicit path to a macro you trust |
| Expecting a console observer to be registered by defining a class | It registers nothing; use the print calls |
| Writing into the owner's macro folder unasked | Ask first |
