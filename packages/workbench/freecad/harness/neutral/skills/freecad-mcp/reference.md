# Reference: the FreeCAD MCP server

The tool names, arguments and limits below were read from the source of the open-source server `freecad-mcp` (MIT licence) at
version 0.1.28, commit `8babe9927ce8e6e8fe7dd6ae2ffa2c93776e845a`, in `src/freecad_mcp/server.py` (sha-256
`80aba311dd4e88a6d5908d5b53b6b959733bacff65ecb128679352491a26f84f`), on 2026-10-28. The server was not run for this module, so
every statement about its tools is read. The scripts you would send through it are checked below under `freecadcmd` on
FreeCAD 1.1.4. Blocks without a `# (read)` first line were run; the printed value is in the comment.

## The tools at version 0.1.28 (read)

| Tool | Arguments | What it does |
|---|---|---|
| `execute_code` | `code`, `include_screenshot=True`, `view_name="Isometric"`, `timeout=None` | runs Python on FreeCAD's GUI thread and returns its output and a screenshot |
| `execute_code_async` | `code` | runs Python in a background thread and returns a job id at once |
| `execute_code_headless` | `code`, `timeout=600` | runs a complete script in a separate `freecadcmd` process |
| `get_async_status` | `job_id=""` | the state of background jobs; empty lists all running and up to 20 recent |
| `get_view` | `view_name`, `width`, `height`, `focus_object` | a screenshot of the active view |
| `reload_document` | `doc_name` | reloads a document from disk after a script saved it |
| `list_documents`, `get_objects`, `get_object`, `get_parts_list` | | read the open documents and their objects |
| `create_document`, `create_object`, `edit_object`, `delete_object` | | change documents and objects |
| `insert_part_from_library` | `relative_path`, `include_screenshot`, `view_name` | inserts a part from the parts library addon |
| `run_fem_analysis` | `doc_name`, `analysis_name`, `timeout=600`, ... | runs the CalculiX solver on an analysis container |
| `get_rpc_status` | | the health of the connection; a `stuck` state names the operation that is still running |

The views for `get_view` are Isometric, Front, Top, Right, Back, Left, Bottom, Dimetric and Trimetric.

## Limits and warnings stated in the server's own descriptions (read)

- `execute_code` has a 90 s budget on the GUI thread. `timeout` raises it for that call, to at most 1800 s. Without it, a call
  that runs out of time reports a timeout while the task keeps running, and the result is lost.
- `execute_code_async` must not call `FreeCADGui`, touch the view or the selection, create or edit objects, change properties,
  call `doc.recompute()` or save. Documents and the scenegraph are not thread-safe, and writing from that thread can freeze
  FreeCAD's event loop until it is restarted. Writes go through an injected `commit(fn, timeout=120)`, which runs `fn` on the
  GUI thread and returns its result.
- `execute_code_headless` runs on the machine of the MCP server, with no connection to the open documents and nothing from the
  `execute_code` namespace. A native crash ends only that process. Open documents from disk, save the result, and call
  `reload_document` to show it.
- `run_fem_analysis` runs the solver on the GUI thread and blocks every other call while it runs.
- If the addon has an authentication token set, the server needs it. Supply it through the `FREECAD_MCP_TOKEN` environment
  variable and not on the command line, where other users can read it.
- The server's `--freecadcmd` option names the command that starts headless FreeCAD for `execute_code_headless`; without it the
  server looks on `PATH`.

## A script for execute_code that also runs without a GUI

```python
import FreeCAD as App
import Part

doc = App.ActiveDocument or App.newDocument("Example")
box = doc.addObject("Part::Feature", "Box")
box.Shape = Part.makeBox(10, 20, 30)
doc.recompute()
print("volume", round(box.Shape.Volume, 1))                      # volume 6000.0
if App.GuiUp:
    import FreeCADGui                                            # GUI-only lines go inside this guard
    FreeCADGui.SendMsgToActiveView("ViewFit")
else:
    print("no GUI here; ViewObject is", box.ViewObject)           # no GUI here; ViewObject is None
```

## A script for execute_code_headless

```python
import os
import shutil
import tempfile

import FreeCAD as App
import Part

folder = tempfile.mkdtemp()
doc = App.newDocument("Heavy")
shape = Part.makeCylinder(5, 30).cut(Part.makeCylinder(2, 40, App.Vector(0, 0, -5)))
obj = doc.addObject("Part::Feature", "Tube")
obj.Shape = shape
doc.recompute()
print("built", round(obj.Shape.Volume, 1))                       # printed output is returned to the caller
path = os.path.join(folder, "heavy.FCStd")
doc.saveAs(path)                                                 # save the result; the caller then reloads it
shape.exportBrep(os.path.join(folder, "tube.brep"))
print(sorted(os.listdir(folder)))                                # ['heavy.FCStd', 'tube.brep']
App.closeDocument(doc.Name)
print(round(App.openDocument(path).Tube.Shape.Volume, 1))        # the same volume after reopening
shutil.rmtree(folder)
```

## Heavy geometry in the background (read)

```python
# (read)
# sent to execute_code_async; commit() is injected by the server
fused = base.fuse(addition).removeSplitter()        # slow, and safe to run in the background


def apply():                                        # runs on the GUI thread
    obj.Shape = fused
    doc.recompute()


commit(apply)
```

Fetch the shapes into module-level variables first with `execute_code`, run the heavy computation with `execute_code_async`,
and apply the result inside `commit()`.

## Getting a view to compare (read)

```
get_view(view_name="Front", width=1200, height=800, focus_object="Box")
```
