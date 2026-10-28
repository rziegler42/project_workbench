# Reference: the FreeCAD Python environment

Examples for the core skill. They were written against FreeCAD 1.1.4. A block that needs the GUI is marked (read);
the rest were run headless with `freecadcmd`.

## The module layout

`FreeCAD` (also `App`) is the core: documents, objects and properties, with `Vector`, `Rotation`, `Placement`, `Matrix`,
`Units` and `Console` inside it. `FreeCADGui` (also `Gui`) exists only when the GUI is active and holds `Selection`,
`Control` (task panels), `ActiveDocument` and `getMainWindow()`. The geometry and workbench modules (`Part`, `Mesh`,
`Sketcher`, `Draft`, `Fem`, `TechDraw`) are imported by name.

## Documents and objects

```python
import FreeCAD

doc = FreeCAD.newDocument("Example")          # or FreeCAD.ActiveDocument
box = doc.addObject("Part::Box", "Box")
box.Length, box.Width, box.Height = 10, 20, 30
doc.recompute()

print(box.State)            # a list; an empty or "Up-to-date" state means the recompute worked
same = doc.getObject("Box")  # or doc.Box
print(same.Shape.Volume)     # 6000.0
print([o.Name for o in doc.findObjects("Part::Box")])

doc.removeObject("Box")
FreeCAD.closeDocument(doc.Name)
```

Other lifecycle calls are `FreeCAD.openDocument(path)`, `doc.save()`, `doc.saveAs(path)`, `FreeCAD.setActiveDocument(name)`,
`obj.touch()` to mark an object for recompute, and `doc.recompute([objects])` for some objects only.

## Vectors, rotations and placements

```python
V = FreeCAD.Vector
a, b = V(1, 0, 0), V(0, 1, 0)
print(a.cross(b), a.dot(b), (a + b).Length)

rotation = FreeCAD.Rotation(V(0, 0, 1), 45)               # axis, degrees
placement = FreeCAD.Placement(V(10, 20, 0), rotation)     # position, orientation
box.Placement = placement
```

## Units

```python
from FreeCAD import Units

length = Units.Quantity("1 in")
print(length.getValueAs("mm"))            # 25.4
print(float(Units.parseQuantity("2.5 in")))   # the value in millimetres
angle = Units.parseQuantity("3.14 rad")        # keep angles in their own variable
```

## Properties

```python
obj = doc.addObject("App::FeaturePython", "Holder")   # any document object takes properties
obj.addProperty("App::PropertyFloat", "Factor", "Parameters", "A tooltip")
obj.Factor = 42.0
print(obj.getTypeIdOfProperty("Factor"), obj.getGroupOfProperty("Factor"))   # App::PropertyFloat Parameters
obj.setPropertyStatus("Factor", "ReadOnly")
obj.setPropertyStatus("Factor", "-ReadOnly")           # a leading minus removes a status
```

`getTypeOfProperty` returns the property's flags (an empty list here), not its type name; use `getTypeIdOfProperty` for the name. `getPropertyStatus` lists `ReadOnly` after it is set and no longer lists it after `-ReadOnly`. Other statuses include `Hidden`, `Transient`, `Output` and `NoRecompute` (read).

## Console output

```python
FreeCAD.Console.PrintMessage("information\n")
FreeCAD.Console.PrintWarning("a warning\n")
FreeCAD.Console.PrintError("an error\n")
FreeCAD.Console.PrintLog("log only\n")
```

## Writing a script that runs both ways

```python
import sys
import FreeCAD

def main(argv):
    doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Run")
    # ... build the model ...
    doc.recompute()
    if FreeCAD.GuiUp:
        import FreeCADGui      # (read) GUI-only lines go inside this guard
        FreeCADGui.SendMsgToActiveView("ViewFit")
    return 0

main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
```
