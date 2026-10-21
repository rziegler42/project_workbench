"""``wb code-work <subcommand> [args]``: run the module's pinned helper from inside a project.

The caller need not know the project ID. This finds the project from the working directory with
the kit's finder, reads its ID from the committed manifest with the kit's reader and hands the pinned
helper named ``code-work`` to the launcher, which refuses unless the helper's bytes are the ones the
owner pinned. It runs no git and no program of its own, and it writes nothing of its own (the
launcher keeps a transient copy of the helper in the guarded store while it runs). Only the helper's
read-only subcommands are accepted, and anything after the subcommand goes to the helper unchanged.
"""

import os

from . import launch, pins
from .wbkit import display, project

NAME = "code-work"
SUBCOMMANDS = ("check", "plans", "report")
USAGE = "usage: wb code-work %s\n" % "|".join(SUBCOMMANDS)


class DispatchError(Exception):
    """Nothing was run; the message says why."""


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
        root = project.find_root(start)
        ident = project.read_id(root)
        if NAME not in pins.load(guarded, ident):
            raise DispatchError(
                "the %s helper is not pinned for this project; its owner pins the module's "
                "shipped helper with `pin`, or `acknowledge` after a change, and nothing was run"
                % NAME)
        return launch.launch(guarded, ident, NAME, root, list(args), stdout=stdout)
    except (DispatchError, project.ProjectError, launch.LaunchError, pins.PinError) as exc:
        err.write("refused: %s\n" % display.clean(str(exc)))
        return 1
