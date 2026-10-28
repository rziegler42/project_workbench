---
name: freecad-mcp
description: Use when driving FreeCAD through the freecad-mcp server tools: choosing execute_code, execute_code_async or execute_code_headless, GUI-thread limits and timeouts, getting views, and testing a script headless first.
---

# FreeCAD through the MCP server

This skill is for using FreeCAD 1.1 through the open-source `freecad-mcp` server, version 0.1.28, whose tools appear in the session only when the server is connected to a running FreeCAD. If those tools are not available, stop and tell the owner; do not try to set the server up, write any client configuration or fetch anything. The tool names, arguments and limits below were read from the server's source at that version and can change in a later one, so check the tools the session lists. The server was not run for this module, so everything about its tools is marked as read; only the scripts you would send through it were checked, under `freecadcmd` on FreeCAD 1.1.4. The environment is in `freecad-python`, and viewing a result is in `freecad-image-to-model`. The tool table and examples are in `reference.md`.

## Choose the tool (read)

- **`execute_code`** runs Python on FreeCAD's GUI thread, so it can touch the document, the view and the selection. It returns the output and, by default, a screenshot in the view you name. Set `include_screenshot=False` when the code does not change how the model looks, to save tokens. It has a 90 s budget; pass `timeout` (at most 1800 s) for slow work such as importing a large STEP assembly. Without it, a call that runs out of time reports a timeout while the work keeps running and its result is lost.
- **`execute_code_headless`** runs a complete script in a separate `freecadcmd` process, on the machine of the MCP server. Use it for geometry that can crash or block FreeCAD: helical threads, lofts and sweeps, booleans with many faces. A native crash ends only that process. The script shares nothing with `execute_code`: import `FreeCAD` and `Part` in it, open documents from disk, print progress, and save the result with `doc.saveAs` or `Shape.exportBrep`. If the document is open in the GUI, call `reload_document` to show the result.
- **`execute_code_async`** runs Python in a background thread and returns a job id. Use it only for a long computation on shapes already fetched. It must not call `FreeCADGui`, touch the view or selection, create or edit objects, change properties, recompute or save: writing to a document from that thread can freeze FreeCAD's event loop until it is restarted. Hand every write to the GUI thread through the injected `commit(fn)`. Read progress with `get_async_status`.

## Test a script headless first

Test an unfamiliar call under `freecadcmd` or `execute_code_headless` before running it in the live session; the same script ran both ways in the examples. Guard the GUI lines with `if FreeCAD.GuiUp:`: `GuiUp` is true in `execute_code`, and under `freecadcmd` it is false and `ViewObject` is `None`.

## Keep the GUI thread free (read)

Never open a modal dialog with `exec()` from `execute_code`; it blocks the GUI thread. Use a task panel (see `freecad-gui-and-workbenches`). `run_fem_analysis` also runs the solver on the GUI thread and blocks every other call while it runs, so do not send requests in parallel; building the analysis by script is in `freecad-fem`. `get_rpc_status` answers even when the GUI thread is stuck, and a `stuck` state names the operation that is still running.

## Views (read)

`get_view` returns a screenshot of the active view without running code. Its views are Isometric, Front, Top, Right, Back, Left, Bottom, Dimetric and Trimetric, and it takes an optional `width`, `height` and `focus_object`. Choose the view that matches the reference when you compare a model with an image.

## Credentials

If the addon has an authentication token, the server needs it. Never put a token in a command line, a file in the project or a message; the server reads it from the `FREECAD_MCP_TOKEN` environment variable, which other users cannot see in a process list the way they can see arguments. Setting it up is the owner's.

## Common mistakes

| Mistake | Instead |
|---|---|
| Writing to a document from `execute_code_async` | Hand the write to `commit(fn)` |
| A long job in `execute_code` with the default budget | Pass `timeout`, or use the background or headless tool |
| Expecting `execute_code_headless` to see the open document | It starts fresh; open the file from disk |
| A modal dialog from `execute_code` | Use a task panel |
| Parallel calls during `run_fem_analysis` | Wait for it to finish |
| A token on a command line | The environment variable |
