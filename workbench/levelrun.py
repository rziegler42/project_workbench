"""How an owner-run command of the installer runs at the level ``none``, and writes what it did to the level log.

``docs/specs/command-permissions.md``, "Planned: a level for every command". A command that is owner-run runs from a
terminal. When the owner has set its key to ``none`` it also runs without one, and then two things are shared by every
such command, which is what this module is for:

* ``route``: at a terminal the command goes on as it always has (its own typed confirmation applies). Without one,
  the key's level is read as ``approve-plan``'s is: ``none`` or ``ask`` holds only while the rendering record exists and
  is sound, names the attached harness, rendered the command gate, was rendered from this table and lists the key, and the
  harness's settings files still hash to the record (``rendering.effective_level``). Anything else reads ``block`` and the
  command refuses with the text the caller gives. The kit's ``may_run`` is the pure decision.
* ``logged`` and ``done``: the attempt is written after every check and just before the change, the outcome after it,
  and a run that changes nothing writes no entry. If the attempt cannot be written the command does nothing.

``planapprovals.py`` uses both for ``approve-plan``; ``apply_logged`` is the same for the writes of ``install``, ``adopt``,
``upgrade`` and ``add``. Do not call ``rendering.effective_level``
for an agent-safe key from here: it reads ``block`` for a key the table leaves out at its default.
"""

import collections

from . import approvalcmd, approve, levellog, levels, rendering
from .wbkit import display, levels as kit


class Refusal(Exception):
    """The command may not run without a terminal, or its level could not be read; nothing was done. The text is the
    caller's to print after ``refused: ``."""


# `terminal` is true when both streams are terminals; `level`, `project_id` and `root` are None then, because nothing was
# read.
Route = collections.namedtuple("Route", "terminal level project_id root")


def level_now(guarded, start, key):
    """``(level, project id, project root)`` of `key` for the project that holds the directory `start`, as the rendering
    record allows it now. ``Refusal`` when the project or an installed declaration cannot be used."""
    try:
        table, root, ident = rendering.current_table(guarded, start)
    except (approvalcmd.ApprovalError, levels.RegistryError) as exc:
        raise Refusal(str(exc))
    return rendering.effective_level(guarded, ident, root, table, key), ident, root


def route(guarded, start, key, stdin, out, terminal_only):
    """A ``Route`` for the owner-run command `key`. At a terminal nothing is read. Otherwise the level is read and the
    command may go on only if the kit's ``may_run`` says so; if not, ``Refusal(terminal_only)``.

    The level was read for the project that holds `start`. A command that then finds the project it acts on some other
    way must compare it with ``Route.project_id`` and refuse if they differ, as ``approve-plan`` does."""
    if approve.is_terminal(stdin) and approve.is_terminal(out):
        return Route(True, None, None, None)
    level, ident, root = level_now(guarded, start, key)
    if not kit.may_run(level, False):
        raise Refusal(terminal_only)
    return Route(False, level, ident, root)


def logged(guarded, key, level, change, evidence="", needed=True):
    """Run `change()` between an attempt and an outcome. Returns ``(result, op)``; `op` is None when `needed` is false
    (the command would change nothing, so no entry is written). ``levellog.LogError`` before `change` is called when the
    attempt cannot be written. If `change` raises, a ``refused`` outcome naming it is written and the exception goes on;
    on success the caller writes the outcome with ``done`` once it has said what happened. A ``refused`` outcome can follow a
    change that was made (an interrupt after the write): it means the command did not finish, not that nothing changed."""
    op = levellog.begin(guarded, key, level, evidence) if needed else None
    try:
        result = change()
    except BaseException as exc:
        if op is not None:
            levellog.finish_refused(guarded, op, str(exc) if isinstance(exc, Exception) else type(exc).__name__)
        raise
    return result, op


def done(guarded, op, reason="recorded"):
    """Write the ``done`` outcome for `op`, if there is one. ``levellog.OutcomeError`` when it cannot be written after the
    change was made."""
    if op is not None:
        levellog.finish(guarded, op, "done", reason)


def apply_logged(guarded, route, key, digest, apply, err, refuse):
    """Run `apply` (the writes of an installer command; it returns the exit code) between an attempt and an outcome, and
    return the exit code. The evidence is the digest of the plan. If the attempt cannot be written nothing is written
    (`refuse(err, text)` says so). An exit code other than 0 is a ``refused`` outcome: the run did not finish. If the
    outcome cannot be written after the writes were made, or the run is interrupted before it is, the exit code is 3."""
    word = key.split()[-1]
    try:
        code, op = logged(guarded, key, route.level, apply, "digest:%s" % digest if digest else "")
    except levellog.LogError as exc:
        return refuse(err, "%s; nothing was written" % exc)
    try:
        if code == 0:
            done(guarded, op, "written")
        else:
            levellog.finish_refused(guarded, op, "refused before writing" if code == 1 else
                                    "interrupted before writing" if code == 130 else "stopped after writing (exit %d)" % code)
    except levellog.OutcomeError as exc:
        err.write("the %s was written, but its outcome was not logged: %s\n" % (word, display.clean(str(exc))))
        return 3
    except KeyboardInterrupt:
        err.write("the %s was written, but it was interrupted before its outcome was logged\n" % word)
        return 3
    return code


def optional(guarded, start, key, stdin, out):
    """For a command that has no terminal test (``attach``, ``release-approvals``): the ``Route`` when it runs without a
    terminal at a verified ``none`` for the project that holds `start`, so that the run is logged; ``None`` otherwise, and the
    command goes on exactly as it always did (at a terminal, at another level, or where no level can be read)."""
    if approve.is_terminal(stdin) and approve.is_terminal(out):
        return None
    try:
        level, ident, root = level_now(guarded, start, key)
    except (Refusal, OSError):
        return None
    return Route(False, level, ident, root) if level == levels.NONE else None
