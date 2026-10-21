"""The runner: start a Python helper with the kit, after checking the kit version it declared.

The launcher runs ``python3 -I <this file> <kit number> <copy of the helper> <arguments...>``. The
isolated interpreter puts neither the current directory, nor the script's directory, nor ``PYTHONPATH`` on
the search path. This file reaches the kit only from its own location, by loading
``wbkit/__init__.py`` as the module ``wbkit`` with the kit's directory as its package location. No
directory is added to the search path, so the rest of the workbench cannot be imported by name and a
``wbkit.py`` anywhere else is never read. Then the kit number is compared with ``wbkit.API``, exactly,
and only on a match is the helper read once from a regular file, compiled as text and run, as ``__main__``, with ``sys.argv`` set to the copy's path and
the arguments. Nothing the helper does is caught: its exit code, and a traceback if it fails, reach the
caller as they would from the helper run alone.

Anything that stops the helper from running prints a ``refused:`` line to standard error and exits 1,
the launcher's own refusal form. The helper's code has not been imported when that happens.
"""

import importlib.util
import os
import stat
import sys
import types


def refuse(text):
    sys.stderr.write("refused: %s\n" % text)
    raise SystemExit(1)


def load_kit():
    """The kit that sits beside this file, registered as the module `wbkit`."""
    here = os.path.dirname(os.path.realpath(__file__))
    directory = os.path.join(here, "wbkit")
    init = os.path.join(directory, "__init__.py")
    if not os.path.isfile(init):
        refuse("the workbench kit is missing; nothing was run")
    try:
        spec = importlib.util.spec_from_file_location("wbkit", init, submodule_search_locations=[directory])
        kit = importlib.util.module_from_spec(spec)
        sys.modules["wbkit"] = kit
        spec.loader.exec_module(kit)
    except Exception as exc:
        sys.modules.pop("wbkit", None)
        refuse("the workbench kit cannot be loaded (%s); nothing was run" % type(exc).__name__)
    return kit


def wanted_number(text):
    """The kit number the caller named, or None when it is not a plain positive integer."""
    if text.isascii() and text.isdigit() and len(text) <= 9 and int(text) >= 1 and text == str(int(text)):
        return int(text)
    return None


def read_script(path):
    """The helper's bytes, read once from a regular file, or a refusal. The same bytes are compiled and run,
    so nothing can change between the check and the run, and `runpy.run_path` (which would run a zip
    archive's `__main__.py`, or a directory's) is never used on the path."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as exc:
        refuse("the helper cannot be opened (%s); nothing was run" % type(exc).__name__)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            refuse("the helper is not a regular file; nothing was run")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            data = handle.read()
    finally:
        os.close(descriptor)
    if data[:4] == importlib.util.MAGIC_NUMBER or b"\0" in data:
        refuse("the helper is an archive or compiled code, not a script; nothing was run")
    try:
        # Source given to `compile` as text ignores a coding cookie, so what runs is what the bytes spell.
        return data.decode("utf-8")
    except UnicodeDecodeError:
        refuse("the helper is not UTF-8 text; nothing was run")


def main(argv):
    if len(argv) < 3:
        refuse("the runner needs a kit number and a helper; nothing was run")
    wanted = wanted_number(argv[1])
    if wanted is None:
        refuse("the kit number %s is not a positive integer; nothing was run" % ascii(argv[1])[:40])
    kit = load_kit()
    have = getattr(kit, "API", None)
    if type(have) is not int:
        refuse("this workbench's kit has no integer API version; nothing was run")
    if have != wanted:
        refuse("this helper needs kit API %d; this workbench has %d" % (wanted, have))
    source = read_script(argv[2])
    sys.argv = [argv[2]] + list(argv[3:])
    main_module = types.ModuleType("__main__")
    main_module.__file__ = argv[2]
    sys.modules["__main__"] = main_module
    exec(compile(source, argv[2], "exec"), main_module.__dict__)


if __name__ == "__main__":
    main(sys.argv)
