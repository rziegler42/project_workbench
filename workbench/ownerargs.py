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
import sys

from . import commands, identity, launch, levellog, levelrun, levels
from .wbkit import display, jsonstrict, safefs

DIGEST = re.compile(r"[0-9a-f]{32}\Z")

# `checked` is true for an argument that a declaration maps to a checkpoint (``checkpoint_of``): its helper prints one result
# line, which ``run_logged`` checks and writes into the outcome.
Permit = collections.namedtuple("Permit", "key level evidence checked", defaults=(False,))

RESULT_FIELDS = frozenset(("format", "record", "sha256", "approver", "via"))
RESULT_FORMAT = 1
MAX_RESULT = 512  # bytes of the line, without its newline
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
OUTPUT_LIMIT = 64 * 1024  # of the helper's standard output, for a mapped argument
TIMEOUT = 300  # seconds


class ResultError(ValueError):
    """The helper's result line is missing, malformed, over its bound or does not match the run."""


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
    try:
        level, ident, root, key = levelrun.level_of_command(guarded, start, "wb run %s %s" % (request.name, word))
        same = ident == request.project_id and os.path.realpath(root) == os.path.realpath(request.root)
    except (levelrun.Refusal, OSError):
        raise commands.CommandError(reason)
    if not same or level not in offered:
        raise commands.CommandError(reason)
    checked = word in dict(request.checkpoint_of)
    if level != levels.ASK:
        return Permit(key, level, "", checked)
    digest = _digest(request.arguments)
    if digest is None:
        raise commands.CommandError(
            "%s of the command %s is at the level ask: run `wb run %s %s %s` and give the digest it prints as the last two "
            "arguments, --digest followed by 32 lowercase hexadecimal characters"
            % (commands._shown(word), commands._shown(request.name), commands._shown(request.name),
               commands._shown(request.preview), commands._shown(word)))
    return Permit(key, level, "digest:" + digest, checked)


def result(output, level):
    """``(email, sha256)`` from the last line of the helper's standard output `output` (bytes), which must be one JSON object
    of at most ``MAX_RESULT`` bytes with exactly the fields ``format`` (the integer 1), ``record`` (a relative path), ``sha256``
    (64 lowercase hexadecimal characters), ``approver`` (a git identity in the grammar of ``identity``) and ``via`` (the level
    the run had). ``ResultError`` otherwise (``docs/specs/command-permissions.md``, "Accepting a decision through a command")."""
    lines = output.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    if not lines:
        raise ResultError("the helper printed no result line")
    line = lines[-1]
    if len(line) > MAX_RESULT:
        raise ResultError("the result line is longer than %d bytes" % MAX_RESULT)
    try:
        found = jsonstrict.parse_object(line, MAX_RESULT)
    except ValueError:
        raise ResultError("the last line the helper printed is not a result line")
    if set(found) != RESULT_FIELDS:
        raise ResultError("the result line does not have exactly the fields %s" % ", ".join(sorted(RESULT_FIELDS)))
    if type(found["format"]) is not int or found["format"] != RESULT_FORMAT:
        raise ResultError("the result line has a format other than %d" % RESULT_FORMAT)
    if not isinstance(found["record"], str) or not safefs.relpath_ok(found["record"]):
        raise ResultError("the result line names a record that is not a relative path")
    if not isinstance(found["sha256"], str) or not _SHA256.match(found["sha256"]):
        raise ResultError("the result line has a hash that is not 64 lowercase hexadecimal characters")
    if found["via"] != level:
        raise ResultError("the result line names a route other than the level %s the run had" % level)
    try:
        approver = identity.parse(found["approver"])
    except identity.IdentityError:
        raise ResultError("the result line has an approver that is not a git identity")
    return approver.email, found["sha256"]


def _emit(stream, data):
    """Write `data` (bytes) to `stream`, a binary or a text stream."""
    try:
        stream.write(data)
    except TypeError:
        stream.write(data.decode("utf-8", "replace"))
    try:
        stream.flush()
    except (OSError, ValueError):
        pass


def _run_checked(guarded, request, attempt, stdout, err):
    """Run the helper of a mapped argument with its standard output read here. The output and the end of its error text go
    on to the caller. Returns ``(exit code, output, problem)``, where `problem` is the reason the run did not finish (the output
    was over its limit, or it ran out of time) or ``None``; ``LaunchError`` when it did not start."""
    found = launch.launch_captured(guarded, request.project_id, request.name, request.root, request.arguments,
                                   limit=OUTPUT_LIMIT, timeout=TIMEOUT, kit=request.kit, before=attempt)
    _emit(stdout if stdout is not None else sys.stdout, found.stdout)
    if found.stderr:
        _emit(err, found.stderr)
    if found.over:
        return 1, found.stdout, "the helper printed more than %d bytes and was stopped" % OUTPUT_LIMIT
    if found.timed_out:
        return 124, found.stdout, "the helper did not finish in %d seconds and was stopped" % TIMEOUT
    return found.code, found.stdout, None


def run_logged(guarded, request, allowed, stdout, err):
    """Start the helper of `request` with its arguments unchanged between an attempt line and an outcome line. Returns the
    helper's exit code, or 3 when it ran and its outcome could not be logged, or (for a mapped argument) its result line was
    not right: the outcome is then ``refused``. ``LaunchError`` when it did not start, also when the attempt cannot be written."""
    started = []

    def attempt():
        try:
            started.append(levellog.begin(guarded, allowed.key, allowed.level, allowed.evidence))
        except (levellog.LogError, ValueError) as exc:
            raise launch.LaunchError("%s; nothing was run" % display.clean(str(exc)))

    output, problem = b"", None
    try:
        if allowed.checked:
            code, output, problem = _run_checked(guarded, request, attempt, stdout, err)
        else:
            code = launch.launch(guarded, request.project_id, request.name, request.root, request.arguments,
                                 stdout=stdout, kit=request.kit, before=attempt)
    except BaseException as exc:
        if started:
            levellog.finish_refused(guarded, started[0], str(exc) if isinstance(exc, Exception) else type(exc).__name__)
        raise
    word = request.arguments[0]
    refused, done = problem, "ran"
    if refused is None and code != 0:
        refused = "the helper exited with %d" % code
    if refused is None and allowed.checked:
        try:
            email, sha256 = result(output, allowed.level)
            done = "accepted by %s via %s sha256:%s" % (email, allowed.level, sha256)
        except ResultError as exc:
            refused, code = "the helper's result line was refused: %s" % exc, 3
            err.write("the %s ran, but %s; its outcome is logged as refused\n" % (display.clean(word), refused))
    try:
        if refused is None:
            levelrun.done(guarded, started[0], done)
        else:
            levellog.finish_refused(guarded, started[0], refused)
    except levellog.OutcomeError as exc:
        err.write("the %s ran, but its outcome was not logged: %s\n" % (display.clean(word), display.clean(str(exc))))
        return 3
    except KeyboardInterrupt:
        err.write("the %s ran, but it was interrupted before its outcome was logged\n" % display.clean(word))
        return 3
    return code
