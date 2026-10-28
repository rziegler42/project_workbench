"""``wb run`` of an owner-run argument without a terminal, for an argument whose declaration offers a level.

``docs/specs/command-permissions.md`` ("The levels an owner-run argument of a module's command offers") and the decision
``2026-10-27-owner-run-arguments-take-a-level``. ``commands.run`` refuses an owner-run argument unless standard input and
output are terminals. When that refusal would apply, it asks ``permit`` first, and ``permit`` lets the run go on only when:

* the command's declaration gives that argument a level (``levels``), and the owner's key ``wb run <command> <argument>``
  reads that level now for the project that holds the working directory (``levelrun.level_now``, so the rendering record,
  the table, the permissions file and the command gate must agree and the key must be listed); and
* at ``ask``, the last two arguments are ``--digest`` and 32 lowercase hexadecimal characters. The launcher does not compute
  or compare the digest: the helper recomputes it inside the lock that guards its change and refuses unless it is equal.

Anything else reads ``block`` and the refusal is the one ``commands.owner_refusal`` gives. ``run_logged`` then starts the helper
with the arguments unchanged. It writes the attempt line after the pin and the bytes are checked and just before the helper
starts (``launch.launch``'s `before`), and the outcome line after. A run at a terminal never comes here, and ``wb launch``
(``commands.launch_refusal``) never asks: it stays terminal-only for an owner-run argument at every level.
"""

import collections
import os
import re

from . import commands, launch, levellog, levelrun, levels
from .wbkit import display

DIGEST = re.compile(r"[0-9a-f]{32}\Z")

Permit = collections.namedtuple("Permit", "key level evidence")


def _digest(arguments):
    """The digest an ``ask`` run carries as its last two arguments, or None."""
    if len(arguments) >= 3 and arguments[-2] == "--digest" and DIGEST.match(arguments[-1]):
        return arguments[-1]
    return None


def permit(guarded, request, start, reason):
    """The ``Permit`` for a run of `request` without a terminal, or ``CommandError(reason)``. Nothing is written."""
    word = request.arguments[0]
    offered = dict(request.levels).get(word, ())
    if not offered:
        raise commands.CommandError(reason)
    key = "wb run %s %s" % (request.name, word)
    try:
        level, ident, root = levelrun.level_now(guarded, start, key)
        same = ident == request.project_id and os.path.realpath(root) == os.path.realpath(request.root)
    except (levelrun.Refusal, OSError):
        raise commands.CommandError(reason)
    if not same or level not in offered:
        raise commands.CommandError(reason)
    if level != levels.ASK:
        return Permit(key, level, "")
    digest = _digest(request.arguments)
    if digest is None:
        raise commands.CommandError(
            "%s of the command %s is at the level ask: run `wb run %s %s %s` and give the digest it prints as the last two "
            "arguments, --digest followed by 32 lowercase hexadecimal characters"
            % (commands._shown(word), commands._shown(request.name), commands._shown(request.name),
               commands._shown(request.preview), commands._shown(word)))
    return Permit(key, level, "digest:" + digest)


def run_logged(guarded, request, allowed, stdout, err):
    """Start the helper of `request` with its arguments unchanged between an attempt line and an outcome line. Returns the
    helper's exit code, or 3 when it ran and its outcome could not be logged. ``LaunchError`` when it did not start,
    also when the attempt cannot be written."""
    started = []

    def attempt():
        try:
            started.append(levellog.begin(guarded, allowed.key, allowed.level, allowed.evidence))
        except (levellog.LogError, ValueError) as exc:
            raise launch.LaunchError("%s; nothing was run" % display.clean(str(exc)))

    try:
        code = launch.launch(guarded, request.project_id, request.name, request.root, request.arguments,
                             stdout=stdout, kit=request.kit, before=attempt)
    except BaseException as exc:
        if started:
            levellog.finish_refused(guarded, started[0], str(exc) if isinstance(exc, Exception) else type(exc).__name__)
        raise
    word = request.arguments[0]
    try:
        if code == 0:
            levelrun.done(guarded, started[0], "ran")
        else:
            levellog.finish_refused(guarded, started[0], "the helper exited with %d" % code)
    except levellog.OutcomeError as exc:
        err.write("the %s ran, but its outcome was not logged: %s\n" % (display.clean(word), display.clean(str(exc))))
        return 3
    except KeyboardInterrupt:
        err.write("the %s ran, but it was interrupted before its outcome was logged\n" % display.clean(word))
        return 3
    return code
