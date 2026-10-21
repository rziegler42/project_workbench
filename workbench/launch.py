"""The launcher: run a pinned helper only if its bytes still match the pin.

``launch <id> <name> --root <project-dir> -- <args>`` takes the helper's location only from
the pin (``pins.py``), never from the caller:

1. It reads ``<root>/<pinned path>`` through the safe reader: the root must be a real
   directory, no symbolic link is followed on the way, and the file must be a regular one.
2. It hashes the bytes and compares them with the pinned hash.
3. It writes those exact bytes to a new file in ``bin/run/`` in the guarded store (a fresh
   private directory, mode 0700, file mode 0700) and runs that file with the arguments, with
   no shell. What runs is what was hashed, so a file swapped after the check changes nothing.
4. It removes the copy afterwards, also when the run fails or is interrupted.

A Python helper whose pin records a kit API number is run through the fixed runner (``runner.py``) in
an isolated interpreter instead of being run directly; the runner checks the number and loads the kit
(``docs/specs/module-boundary.md``). Without a number the copy is run as it is. The number comes
from the pin, which the owner set, never from the caller or the project.

A missing pin, a missing or unreadable helper, a symbolic link, a non-regular file, a path
outside the root or a hash difference runs nothing and exits 1 with a reason beginning
``refused:``. A helper that does run returns its own exit code, so a helper that exits 1 looks
the same as a refusal by exit code alone; the refusal text on standard error tells them apart.

Limits, on purpose: this is a pin check, not a sandbox. The helper runs with the caller's
privileges and environment. The copy is a path in a private directory of the guarded store,
which only the same account can write; a process under that account could replace it between
the write and the run (it can already do anything the helper can). The helper's executable
bit in the project is not needed: the copy is always runnable. A helper that reads files
next to itself will not find them next to the copy, so a pinned helper should be a single
self-contained file, or locate its project through the working directory.

``install_wrapper`` writes ``bin/wb``, a short script that runs this workbench, when the guarded
store is initialized (see the end of this module).
"""

import os
import shutil
import subprocess
import sys
import uuid

from . import pins, store
from .wbkit import display, safefs

# Test seam: called after the helper is hashed and before the copy is written.
_after_hash = None

WRAPPER_NAME = "wb"
RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runner.py")


class LaunchError(Exception):
    """Nothing was run; the message says why."""


def _make_copy(guarded, name, data):
    """Write `data` as an executable file in a fresh private directory under ``bin/run``.

    Returns ``(path, directory)``; the caller removes `directory` when done.
    """
    try:
        root_fd = safefs.open_root(guarded.root, "guarded store")
    except safefs.SafeFsError as exc:
        raise LaunchError(str(exc))
    descriptors = [root_fd]
    try:
        bin_fd = safefs._open_dir("bin", root_fd, guarded.root + "/bin")
        descriptors.append(bin_fd)
        try:
            os.mkdir("run", store.DIR_MODE, dir_fd=bin_fd)
        except FileExistsError:
            pass
        run_fd = safefs._open_dir("run", bin_fd, guarded.root + "/bin/run")
        descriptors.append(run_fd)
        store._check_directory(run_fd, guarded.root + "/bin/run")
        ident = uuid.uuid4().hex
        os.mkdir(ident, store.DIR_MODE, dir_fd=run_fd)
        directory = os.path.join(guarded.root, "bin", "run", ident)
        try:
            dir_fd = safefs._open_dir(ident, run_fd, directory)
            descriptors.append(dir_fd)
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o700,
                         dir_fd=dir_fd)
            try:
                view = memoryview(data)
                while view:
                    view = view[os.write(fd, view):]
                os.fchmod(fd, 0o700)
                os.fsync(fd)
            finally:
                os.close(fd)
        except BaseException:
            shutil.rmtree(directory, ignore_errors=True)
            raise
        return os.path.join(directory, name), directory
    except (safefs.SafeFsError, OSError) as exc:
        raise LaunchError("cannot prepare the helper to run: %s" % (getattr(exc, "strerror", None) or exc))
    finally:
        for fd in descriptors:
            os.close(fd)


def _command(path, args, kit):
    """The command line: the private copy itself, or, for a Python helper that declared a kit API
    number, the fixed runner (isolated interpreter) that checks the number and runs the copy."""
    rest = [str(a) for a in args]
    if kit is None:
        return [path] + rest
    return [sys.executable, "-I", RUNNER, str(kit), path] + rest


def launch(guarded, project_id, name, root, args, *, stdin=None, stdout=None, stderr=None, kit=None):
    """Run the pinned helper. Returns its exit code. Raises LaunchError if it was not run.

    How it runs is the pin's: a pin that records a kit API number runs the helper through the runner,
    which refuses unless that number equals the workbench's kit API; a pin without one runs it as it
    is. `kit` is what the caller expects, and a caller that expects another way is refused; None
    accepts whatever the pin records."""
    if kit is not None and (type(kit) is not int or kit < 1 or not sys.executable):
        raise LaunchError("the kit API number or the Python interpreter is not usable; nothing was run")
    try:
        pin = pins.lookup(guarded, project_id, name)
    except pins.PinError as exc:
        raise LaunchError(str(exc))
    if kit != pin.kit and kit is not None:
        raise LaunchError("the helper %s is pinned to run %s, not as asked; nothing was run" % (
            display.ascii_text(name)[:64],
            "through kit API %d" % pin.kit if pin.kit is not None else "directly"))
    kit = pin.kit
    try:
        with safefs.Root(root, "project root") as project:
            data = project.read_file(pin.path)
    except safefs.SafeFsError as exc:
        raise LaunchError("the helper %s cannot be read: %s" % (display.ascii_text(name)[:64], exc))
    digest = pins.hash_bytes(data)
    if digest != pin.sha256:
        raise LaunchError(
            "the helper %s has changed since it was pinned (pinned %s, now %s); it was not run. "
            "Review it and pin it again with `pin`." % (
                display.ascii_text(name)[:64], pin.sha256[:12], digest[:12]))
    if _after_hash is not None:
        _after_hash()
    path, directory = _make_copy(guarded, name, data)
    try:
        try:
            done = subprocess.run(_command(path, args, kit), stdin=stdin, stdout=stdout,
                                  stderr=stderr)
        except (OSError, ValueError) as exc:
            # ValueError: an argument holds a NUL byte, which no process can be given.
            raise LaunchError("the helper could not be run: %s" % (getattr(exc, "strerror", None) or exc))
        return done.returncode if done.returncode >= 0 else 128 - done.returncode
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def run(guarded, project_id, name, root, args, err):
    """The ``launch`` command: returns the helper's exit code, or 1 if nothing was run."""
    try:
        pins.check_id(project_id)
        pins.check_name(name)
        return launch(guarded, project_id, name, root, args)
    except (LaunchError, pins.PinError) as exc:
        err.write("refused: %s\n" % display.clean(str(exc)))
        return 1


# --- the `wb` wrapper -----------------------------------------------------------

# Python runs in isolated mode (-I): the current directory and PYTHONPATH are not put on the
# module search path, so a project that ships its own `workbench` package, or a `json.py`, cannot
# take the place of this workbench or the standard library. The workbench directory is added by
# hand. `python3 -m workbench` run from inside an untrusted project is exposed to exactly that.
WRAPPER = ("#!/bin/sh\n"
           "# Generated by project-workbench. It is rewritten whenever the guarded store is\n"
           "# initialized, so do not edit it.\n"
           "WORKBENCH_DIR='%s'\n"
           "export WORKBENCH_DIR\n"
           "exec python3 -I -c 'import os, runpy, sys; sys.path.insert(0, os.environ[\"WORKBENCH_DIR\"]); "
           "runpy.run_module(\"workbench\", run_name=\"__main__\", alter_sys=True)' \"$@\"\n")

# Test seam: how another `wb` is looked for on PATH.
find_command = shutil.which


def wrapper_text(distribution):
    """The text of ``bin/wb`` for a distribution directory, or raise LaunchError."""
    if (not isinstance(distribution, str) or not os.path.isabs(distribution)
            or not distribution.isprintable() or "'" in distribution):
        raise LaunchError("the workbench directory cannot be written into a script safely")
    return WRAPPER % distribution


def install_wrapper(guarded, distribution):
    """Write ``bin/wb`` if it is missing or different; return warnings, never raise.

    The name `wb` is kept as the specs state it. When the wrapper is written (the first
    time, or after the workbench directory moved) and another command named `wb` is found on
    ``PATH`` that is not this wrapper, a warning names it. The check is not repeated on every
    command, which would be noise for a command an agent runs often. Nothing is put on
    ``PATH``.
    """
    warnings = []
    wrapper = os.path.join(guarded.root, "bin", WRAPPER_NAME)
    wrote = False
    try:
        wanted = wrapper_text(distribution).encode("utf-8")
        found = guarded.kind("bin/" + WRAPPER_NAME)
        if found not in (None, "file"):
            raise LaunchError("bin/%s is not a regular file (%s)" % (WRAPPER_NAME, found))
        if found is None or guarded.read("bin/" + WRAPPER_NAME) != wanted:
            safefs.write_tree(guarded.root, {"bin/" + WRAPPER_NAME: wanted},
                              executable={"bin/" + WRAPPER_NAME})
            wrote = True
    except (LaunchError, safefs.SafeFsError) as exc:
        warnings.append("the `wb` launcher was not written: %s" % display.clean(str(exc)))
    other = find_command(WRAPPER_NAME) if wrote else None
    if other:
        try:
            same = os.path.samefile(other, wrapper)
        except OSError:
            same = False
        if not same:
            warnings.append("another command named `wb` is on your PATH at %s; the workbench "
                            "launcher is %s" % (display.ascii_text(other), display.ascii_text(wrapper)))
    return warnings
