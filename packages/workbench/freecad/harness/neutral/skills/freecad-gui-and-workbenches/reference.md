# Reference: GUI, scripted objects and workbench examples

Every block without a `# (read)` first line was run headless with `freecadcmd` on FreeCAD 1.1.4, and the printed value is in
the comment. Blocks marked `# (read)` need a GUI session, a display or the workbench loader and were not run. Files are
written to a temporary folder that the block removes.

## A scripted object: proxy, properties, recompute

```python
import FreeCAD as App
import Part


class Box:
    """A custom parametric box."""

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "Box"
        obj.addProperty("App::PropertyLength", "Length", "Dimensions", "The length").Length = 10.0
        obj.addProperty("App::PropertyLength", "Width", "Dimensions", "The width").Width = 10.0
        obj.addProperty("App::PropertyLength", "Height", "Dimensions", "The height").Height = 5.0
        obj.addProperty("App::PropertyBool", "Chamfered", "Options", "Chamfer the edges").Chamfered = False
        obj.addProperty("App::PropertyLength", "ChamferSize", "Options", "Chamfer size").ChamferSize = 1.0
        obj.setPropertyStatus("ChamferSize", "Hidden")

    def execute(self, obj):
        """Called on recompute: build the shape here."""
        shape = Part.makeBox(obj.Length, obj.Width, obj.Height)
        if obj.Chamfered and obj.ChamferSize > 0:
            shape = shape.makeChamfer(obj.ChamferSize, shape.Edges)
        obj.Shape = shape

    def onChanged(self, obj, prop):
        """Called when a property changes."""
        if prop == "Chamfered":
            obj.setPropertyStatus("ChamferSize", "-Hidden" if obj.Chamfered else "Hidden")

    def __getstate__(self):
        return {"Type": self.Type}

    def __setstate__(self, state):
        if state:
            self.Type = state.get("Type", "Box")


doc = App.newDocument("Scripted")
obj = doc.addObject("Part::FeaturePython", "Block")
Box(obj)
doc.recompute()
print(round(obj.Shape.Volume, 1), obj.State)                     # 500.0 ['Up-to-date']
print(obj.getPropertyStatus("ChamferSize"))                      # contains 'Hidden'
obj.Length = 20
obj.Chamfered = True                                             # onChanged shows the property again
doc.recompute()
print(round(obj.Shape.Volume, 2), obj.getPropertyStatus("ChamferSize"))      # 935.33, no 'Hidden'
```

## Save, reopen and migrate a scripted object

```python
import os
import shutil
import sys
import tempfile

import FreeCAD as App

folder = tempfile.mkdtemp()
with open(os.path.join(folder, "scripted_block.py"), "w", encoding="utf-8") as handle:
    handle.write('''
import Part


class Block:
    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "Block"
        obj.addProperty("App::PropertyLength", "Side", "Dimensions", "The side").Side = 10.0

    def execute(self, obj):
        obj.Shape = Part.makeBox(obj.Side, obj.Side, obj.Side)

    def onDocumentRestored(self, obj):
        # a property added in a later version of the class is added when an older document is opened
        if not hasattr(obj, "Migrated"):
            obj.addProperty("App::PropertyString", "Migrated", "Options", "Added on restore")
            obj.Migrated = "yes"
        if hasattr(obj, "OldSide"):
            obj.Side = obj.OldSide
            obj.removeProperty("OldSide")

    def __getstate__(self):
        return {"Type": self.Type}

    def __setstate__(self, state):
        self.Type = (state or {}).get("Type", "Block")
''')
sys.path.insert(0, folder)
import scripted_block

doc = App.newDocument("Original")
obj = doc.addObject("Part::FeaturePython", "Block")
scripted_block.Block(obj)
obj.addProperty("App::PropertyLength", "OldSide", "Old", "An old name")
obj.OldSide = 30.0
doc.recompute()
path = os.path.join(folder, "block.FCStd")
doc.saveAs(path)
App.closeDocument(doc.Name)

reopened = App.openDocument(path)
block = reopened.Block
print(type(block.Proxy).__name__, block.Proxy.Type)               # Block Block
print(block.Migrated, hasattr(block, "OldSide"), block.Side)       # yes False 30.0 mm
reopened.recompute()
print(round(block.Shape.Volume, 1))                              # 1000.0: the shape was not rebuilt
block.touch()                                                    # a change made while restoring does not mark the object
reopened.recompute()
print(round(block.Shape.Volume, 1))                              # 27000.0
sys.path.remove(folder)
shutil.rmtree(folder)
```

## Property types and enumerations

```python
import FreeCAD as App

doc = App.newDocument("Properties")
obj = doc.addObject("App::FeaturePython", "Holder")
types = ["App::PropertyInteger", "App::PropertyFloat", "App::PropertyLength", "App::PropertyDistance",
         "App::PropertyAngle", "App::PropertyArea", "App::PropertyVolume", "App::PropertySpeed",
         "App::PropertyAcceleration", "App::PropertyForce", "App::PropertyPressure", "App::PropertyPercent",
         "App::PropertyQuantity", "App::PropertyString", "App::PropertyFile", "App::PropertyPath",
         "App::PropertyBool", "App::PropertyEnumeration", "App::PropertyVector", "App::PropertyVectorList",
         "App::PropertyPlacement", "App::PropertyMatrix", "App::PropertyLink", "App::PropertyLinkList",
         "App::PropertyLinkSub", "App::PropertyColor", "App::PropertyMaterial", "App::PropertyPythonObject",
         "App::PropertyIntegerList", "App::PropertyFloatList", "App::PropertyStringList", "App::PropertyMap"]
missing = []
for i, kind in enumerate(types):
    try:
        obj.addProperty(kind, "P%d" % i, "Test", kind)
    except Exception as error:
        missing.append((kind, type(error).__name__))
print(len(types) - len(missing), "of", len(types), "added;", missing)

obj.addProperty("App::PropertyEnumeration", "Style", "Options", "Style choice")
obj.Style = ["Solid", "Wireframe", "Points"]          # set the choices first
obj.Style = "Wireframe"                               # then the value
print(obj.Style, obj.getEnumerationsOfProperty("Style"))
```

## Which objects refer to which

```python
import FreeCAD as App
import Part

doc = App.newDocument("Links")
a = doc.addObject("Part::Feature", "A")
a.Shape = Part.makeBox(1, 1, 1)
b = doc.addObject("Part::Feature", "B")
b.Shape = Part.makeBox(1, 1, 1)
holder = doc.addObject("App::FeaturePython", "Holder")
holder.addProperty("App::PropertyLink", "Source", "Links", "Source")
holder.Source = a
print([o.Name for o in a.InList], [o.Name for o in holder.OutList])         # ['Holder'] ['A']
print([o.Name for o in a.InListRecursive], [o.Name for o in holder.OutListRecursive])
```

## A scripted object with attachment (needs the attach extension)

```python
import FreeCAD as App
import Part

doc = App.newDocument("Attach")
plate = doc.addObject("Part::Feature", "Plate")
plate.Shape = Part.makeBox(20, 20, 4)
doc.recompute()

holder = doc.addObject("Part::FeaturePython", "Attached")
holder.addExtension("Part::AttachExtensionPython")
holder.Shape = Part.makeBox(5, 5, 5)
holder.AttachmentSupport = [(plate, "Face6")]
holder.MapMode = "FlatFace"
doc.recompute()
print(holder.State, round(holder.Placement.Base.z, 3))
```

## Coin3D nodes without a view

```python
from pivy import coin

group = coin.SoSeparator()
material = coin.SoMaterial()
material.diffuseColor.setValue(0.0, 0.8, 0.2)
material.transparency.setValue(0.3)
transform = coin.SoTransform()
transform.translation.setValue(10, 0, 0)
sphere = coin.SoSphere()
sphere.radius.setValue(3.0)
for node in (material, transform, sphere):
    group.addChild(node)
print(group.getNumChildren(), sphere.radius.getValue())          # 3 3.0
```

## A task panel (needs a GUI session)

```python
# (read)
import FreeCAD
import FreeCADGui
from PySide import QtWidgets


class BoxPanel:
    """A task panel for the sidebar."""

    def __init__(self):
        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle("Box")
        layout = QtWidgets.QVBoxLayout(self.form)
        self.length = QtWidgets.QDoubleSpinBox()
        self.length.setRange(0.1, 10000.0)
        self.length.setValue(10.0)
        self.length.setSuffix(" mm")
        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Length:", self.length)
        layout.addLayout(form_layout)

    def accept(self):
        import Part
        Part.show(Part.makeBox(self.length.value(), 10, 5), "Box")
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.Control.closeDialog()
        return True

    def reject(self):
        FreeCADGui.Control.closeDialog()
        return True

    def getStandardButtons(self):
        buttons = QtWidgets.QDialogButtonBox.StandardButton
        return buttons.Ok | buttons.Cancel          # return the flag itself; int() of it fails in PySide6


FreeCADGui.Control.showDialog(BoxPanel())
```

## A command (needs a GUI session)

```python
# (read)
import FreeCAD
import FreeCADGui


class MyCommand:
    def GetResources(self):
        return {"Pixmap": ":/icons/freecad.svg", "MenuText": "My command", "ToolTip": "Does something",
                "Accel": "Ctrl+Shift+M"}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        FreeCAD.Console.PrintMessage("activated\n")


FreeCADGui.addCommand("My_Command", MyCommand())          # the name must be unique
```

## A view provider (needs a GUI session)

```python
# (read)
from pivy import coin


class ViewProviderBox:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = vobj.Object
        self.standard = coin.SoGroup()
        vobj.addDisplayMode(self.standard, "Standard")

    def getDisplayModes(self, vobj):
        return ["Standard"]

    def getDefaultDisplayMode(self):
        return "Standard"

    def setDisplayMode(self, mode):
        return mode

    def getIcon(self):
        return ":/icons/freecad.svg"

    def doubleClicked(self, vobj):
        return True

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


# in the factory function: if FreeCAD.GuiUp: ViewProviderBox(obj.ViewObject)
```

## A workbench (needs the workbench loader)

```
MyWorkbench/
    __init__.py
    Init.py            runs at start-up, without a GUI: register importers and exporters
    InitGui.py         runs at GUI start-up: define the workbench
    MyCommands.py      the command classes
    Resources/icons/   the icons
```

```python
# (read)
# InitGui.py
import os

import FreeCADGui


class MyWorkbench(FreeCADGui.Workbench):
    MenuText = "My Workbench"
    ToolTip = "A custom workbench"

    def __init__(self):
        self.__class__.Icon = os.path.join(os.path.dirname(__file__), "Resources", "icons", "MyWorkbench.svg")

    def Initialize(self):
        import MyCommands                                      # import here, not at the top of the file
        self.appendToolbar("My Tools", ["My_Command"])
        self.appendMenu("My Workbench", ["My_Command"])

    def GetClassName(self):
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(MyWorkbench)
```

```python
# Init.py: it runs at start-up without a GUI, and it also runs in a script
import FreeCAD

FreeCAD.addImportType("My Format (*.myf)", "MyImporter")
FreeCAD.addExportType("My Format (*.myf)", "MyExporter")
print(FreeCAD.getImportType("myf"), FreeCAD.getExportType("myf"))
```

## The 3D view (needs a GUI session)

```python
# (read)
import FreeCADGui

view = FreeCADGui.ActiveDocument.ActiveView
view.viewIsometric()
view.viewFront()
view.fitAll()
view.setCameraType("Orthographic")
view.saveImage("view.png", 1200, 800, "White")
```
