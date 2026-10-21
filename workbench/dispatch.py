"""``wb code-work <subcommand> [args]``: run the module's pinned helper from inside a project.

The caller need not know the project ID. This finds the project from the working directory,
reads its ID from the committed manifest and hands the pinned helper named ``code-work`` to the
launcher, which refuses unless the helper's bytes are the ones the owner pinned. It runs no git and
no program of its own, and it writes nothing of its own (the launcher keeps a transient copy of the
helper in the guarded store while it runs). Only the helper's read-only subcommands are accepted,
and anything after the subcommand goes to the helper unchanged.
"""

import os
import stat

from . import launch, manifest, pins
from .wbkit import display, safefs

NAME = "code-work"
SUBCOMMANDS = ("check", "plans", "report")
MANIFEST = ".workbench/manifest.json"
MAX_DEPTH = 64
USAGE = "usage: wb code-work %s\n" % "|".join(SUBCOMMANDS)


class DispatchError(Exception):
    """Nothing was run; the message says why."""


def find_root(start):
    """The nearest directory at or above `start` that holds a `.git` directory and a regular
    `.workbench/manifest.json` in a real `.workbench` directory. Links never count."""
    here = start
    for _ in range(MAX_DEPTH):
        try:
            git = os.lstat(os.path.join(here, ".git"))
            inner = os.lstat(os.path.join(here, ".workbench"))
            document = os.lstat(os.path.join(here, *MANIFEST.split("/")))
        except OSError:
            git = None
        if git is not None and stat.S_ISDIR(git.st_mode) and stat.S_ISDIR(inner.st_mode) \
                and stat.S_ISREG(document.st_mode):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    raise DispatchError("this is not inside a workbench project (no .git with %s at or above %s)"
                        % (MANIFEST, display.ascii_text(start)[:200]))


def project_id(root):
    """The project ID recorded in the manifest at `root`."""
    try:
        with safefs.Root(root, "project root") as project:
            document = manifest.parse(project.read_file(MANIFEST))
        return manifest.project_id(document["seed"])
    except (safefs.SafeFsError, manifest.ManifestError) as exc:
        raise DispatchError("the project manifest cannot be used: %s" % exc)


def accepted(args):
    """Whether `args` begin with one of the read-only subcommands."""
    return bool(args) and args[0] in SUBCOMMANDS


def run(guarded, args, err, *, cwd=None, stdout=None):
    """Run the helper for `args` (the subcommand, then its arguments). Returns the helper's exit
    code, 2 for a usage error, or 1 with a ``refused:`` line when nothing was run."""
    if not accepted(args):
        err.write(USAGE)
        return 2
    try:
        try:
            start = cwd if cwd is not None else os.getcwd()
        except OSError as exc:
            raise DispatchError("the working directory cannot be read: %s"
                                % (exc.strerror or "unknown error"))
        root = find_root(start)
        ident = project_id(root)
        if NAME not in pins.load(guarded, ident):
            raise DispatchError(
                "the %s helper is not pinned for this project; its owner pins the module's "
                "shipped helper with `pin`, or `acknowledge` after a change, and nothing was run"
                % NAME)
        return launch.launch(guarded, ident, NAME, root, list(args), stdout=stdout)
    except (DispatchError, launch.LaunchError, pins.PinError) as exc:
        err.write("refused: %s\n" % display.clean(str(exc)))
        return 1
