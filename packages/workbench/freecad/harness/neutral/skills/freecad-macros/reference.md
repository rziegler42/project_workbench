# Reference: macro examples

Every block without a `# (read)` first line was run headless with `freecadcmd` on FreeCAD 1.1.4, and the printed value is in
the comment. Blocks marked `# (read)` need a GUI session and were not run. Files are written to a temporary folder that the
block removes.

## A macro with a header and a guarded main

```python
import os
import runpy
import shutil
import tempfile

import FreeCAD as App

MACRO = '''# -*- coding: utf-8 -*-
# FreeCAD Macro: Example
# Description: Makes a box in the active document
# Version: 1.0

import FreeCAD
import Part

if FreeCAD.GuiUp:
    import FreeCADGui


def main():
    doc = FreeCAD.ActiveDocument
    if doc is None:
        FreeCAD.Console.PrintError("No active document\\n")
        return "no document"
    if FreeCAD.GuiUp:
        selection = FreeCADGui.Selection.getSelection()
        if not selection:
            FreeCAD.Console.PrintWarning("Nothing selected\\n")
    box = doc.addObject("Part::Feature", "MacroBox")
    box.Shape = Part.makeBox(10, 10, 10)
    doc.recompute()
    FreeCAD.Console.PrintMessage("Macro completed\\n")
    return box.Shape.Volume


if __name__ == "__main__":
    RESULT = main()
'''

folder = tempfile.mkdtemp()
path = os.path.join(folder, "Example.FCMacro")
with open(path, "w", encoding="utf-8") as handle:
    handle.write(MACRO)

print(runpy.run_path(path, run_name="__main__")["RESULT"])       # no document
App.newDocument("Target")
print(round(runpy.run_path(path, run_name="__main__")["RESULT"], 1))       # 1000.0
print([o.Name for o in App.ActiveDocument.Objects])              # ['MacroBox']
shutil.rmtree(folder)
```

## Console output

```python
import FreeCAD as App

App.Console.PrintMessage("information\n")
App.Console.PrintWarning("a warning\n")
App.Console.PrintError("an error\n")
App.Console.PrintLog("log only\n")
print([n for n in dir(App.Console) if "bserver" in n])           # ['GetObservers']: nothing here registers an observer
```

## Where FreeCAD looks for macros and workbenches

```python
import os

import FreeCAD as App

for label, path in (("user macro folder", App.getUserMacroDir(True)),
                    ("user data folder", App.getUserAppDataDir()),
                    ("resource folder", App.getResourceDir())):
    print(label, isinstance(path, str), os.path.isdir(path))
print(os.path.isdir(os.path.join(App.getUserAppDataDir(), "Mod")))       # a user Mod folder exists only if one was made
```

## Run a macro file from a script, with an explicit path

```python
import os
import runpy
import shutil
import tempfile

folder = tempfile.mkdtemp()
path = os.path.join(folder, "Hello.FCMacro")
with open(path, "w", encoding="utf-8") as handle:
    handle.write("VALUE = 6 * 7\nprint('hello from the macro')\n")
namespace = runpy.run_path(path, run_name="__main__")           # an explicit path, and a macro you trust
print(namespace["VALUE"])                                         # 42
shutil.rmtree(folder)
```

## Selection (needs a GUI session)

```python
# (read)
import FreeCADGui

selection = FreeCADGui.Selection.getSelection()                  # a list of objects
extended = FreeCADGui.Selection.getSelectionEx()                 # with sub-elements
for item in extended:
    print(item.Object.Name, item.SubElementNames)                # for example ('Face1', 'Edge3')
    for sub in item.SubElementNames:
        shape = item.Object.getSubObject(sub)

FreeCADGui.Selection.addSelection(item.Object)
FreeCADGui.Selection.addSelection(item.Object, "Face1")
FreeCADGui.Selection.clearSelection()
```

```python
# (read)
import FreeCADGui


class SelectionWatcher:
    def addSelection(self, doc, obj, sub, pos):
        print("selected", obj, sub, pos)

    def removeSelection(self, doc, obj, sub):
        print("deselected", obj, sub)

    def setSelection(self, doc):
        print("selection set in", doc)

    def clearSelection(self, doc):
        print("selection cleared in", doc)


watcher = SelectionWatcher()
FreeCADGui.Selection.addObserver(watcher)
# later: FreeCADGui.Selection.removeObserver(watcher)
```

## The macro dialog (needs a GUI session)

```python
# (read)
import FreeCADGui

FreeCADGui.runCommand("Std_DlgMacroExecute")                      # opens the macro dialog
```
