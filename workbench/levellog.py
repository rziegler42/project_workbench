"""The level log: what ran above ``block``, kept in the guarded store as the file ``level-log``.

``docs/specs/command-permissions.md``, "The log". Every run at a level other than ``block`` appends two lines, never
rewriting one. The attempt (``begin``) is written after the command's read-only checks and immediately before the
change of state; if it cannot be written the command does nothing. The outcome (``finish``) is written on every path
after it; if it cannot be written after the change was made, ``OutcomeError`` says so and the caller exits non-zero.
A run that changes nothing writes no entry.

A line is tab-separated ASCII, at most 1,024 bytes::

    A <id> <time> <key> <level> <evidence>
    O <id> <time> done|refused <reason>

The reason is last and opaque: it is cleaned of anything that is not printable ASCII and cut to 200 characters, so it
holds no tab or newline. The writer never reads the log (it appends through ``safefs.append_line``), so a damaged log
cannot stop a run; the log holds about 4 MiB (the size is read before the write, so concurrent writers can pass the
limit by a line each, and the next run then refuses), and a full log refuses a run above ``block`` with a message that names
it. The owner rotates it by hand. The agent cannot write the store; the log is for the owner to read and decides
nothing. "Unfinished" (an attempt with no outcome) does not mean "not approved": a killed process leaves an attempt with
no outcome after the change was made.
"""

import collections
import re
import secrets

from . import approvals, levels
from .wbkit import display, levels as kit, safefs

# The line formats, the limits and the errors are the kit's, so that a helper writes the same log
# (``wbkit/levels.py``); this module adds the installer's clock and identifiers, and reads the file.
LOG = kit.LOG
MAX_BYTES = kit.MAX_BYTES
MAX_LINE = kit.MAX_LINE
MAX_REASON = kit.MAX_REASON
MAX_KEY = kit.MAX_KEY
_ID = re.compile(kit.ID_PATTERN + r"\Z")
_KEY = re.compile(kit.KEY_PATTERN + r"\Z")
_EVIDENCE = re.compile(kit.EVIDENCE_PATTERN + r"\Z")
_TIME = re.compile(kit.TIME_PATTERN + r"\Z")
OUTCOMES = kit.OUTCOMES
LogError, LogFull, OutcomeError = kit.LogError, kit.LogFull, kit.OutcomeError


Operation = collections.namedtuple("Operation", "op time key level evidence outcome outcome_time reason")
Read = collections.namedtuple("Read", "operations unfinished problems")


def _append(guarded, line):
    kit.append(guarded.root, line, MAX_BYTES)


def begin(guarded, key, level, evidence=""):
    """Write the attempt line and return its operation identifier. ``ValueError`` writes nothing."""
    op = secrets.token_hex(8)
    _append(guarded, kit.attempt_line(op, approvals.utc_now(), key, level, evidence))
    return op


def finish(guarded, op, outcome, reason=""):
    """Write the outcome line for `op`. ``ValueError`` writes nothing; ``OutcomeError`` when it cannot be written."""
    line = kit.outcome_line(op, approvals.utc_now(), outcome, reason)
    try:
        _append(guarded, line)
    except LogError as exc:
        raise OutcomeError(str(exc))


def finish_refused(guarded, op, reason):
    """Write a ``refused`` outcome for a command that is already refusing. A failure to write it is not reported
    again: the attempt stays listed as unfinished."""
    try:
        finish(guarded, op, "refused", reason)
    except OutcomeError:
        pass


def read(guarded):
    """The log as ``Read(operations, unfinished, problems)``. A damaged line is a problem, not a refusal.

    An operation pairs an attempt with its first outcome; a second outcome for one identifier, an outcome with no
    attempt and a line that is not a record are problems and change nothing already read.
    """
    problems = []
    try:
        kind = guarded.kind(LOG)
        if kind is None:
            return Read([], [], [])
        if kind != "file":
            return Read([], [], ["the level log is not a regular file (%s)" % kind])
        data = guarded.read(LOG)
    except safefs.SafeFsError as exc:
        return Read([], [], ["the level log cannot be read: %s" % display.clean(str(exc))[:200]])
    attempts, order, outcomes = {}, [], {}
    for number, raw in enumerate(data.split(b"\n")[:-1] if data.endswith(b"\n") else data.split(b"\n"), 1):
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            problems.append("line %d is not ASCII" % number)
            continue
        if len(raw) + 1 > MAX_LINE:
            problems.append("line %d is longer than %d bytes" % (number, MAX_LINE))
            continue
        fields = text.split("\t", 5)
        if fields[:1] == ["A"] and len(fields) == 6 and _ID.match(fields[1]) and _TIME.match(fields[2]) \
                and _KEY.match(fields[3]) and fields[4] in levels.LEVELS and fields[4] != levels.BLOCK \
                and _EVIDENCE.match(fields[5]):
            if fields[1] in attempts:
                problems.append("line %d repeats the attempt %s" % (number, fields[1]))
            else:
                attempts[fields[1]] = fields[2:]
                order.append(fields[1])
            continue
        fields = text.split("\t", 4)
        if fields[:1] == ["O"] and len(fields) == 5 and _ID.match(fields[1]) and _TIME.match(fields[2]) \
                and fields[3] in OUTCOMES:
            if fields[1] not in attempts:
                problems.append("line %d is an outcome for no attempt" % number)
            elif fields[1] in outcomes:
                problems.append("line %d is a second outcome for %s; the first stands" % (number, fields[1]))
            else:
                outcomes[fields[1]] = fields[2:]
            continue
        problems.append("line %d is not a record" % number)
    operations, unfinished = [], []
    for op in order:
        time, key, level, evidence = attempts[op]
        done = outcomes.get(op)
        item = Operation(op, time, key, level, evidence, done[1] if done else None, done[0] if done else None,
                         done[2] if done else None)
        (operations if done else unfinished).append(item)
    return Read(operations, unfinished, problems)


def report(found):
    """The lines an owner reads for a ``Read``, cleaned. Anything printed here came from a file.
    ``Operation.reason`` is the file's text, uncleaned; a consumer other than this function cleans it itself."""
    lines = []
    for item in found.operations:
        lines.append(display.clean("%s %s %s %s %s: %s %s" % (item.time, item.op, item.key, item.level, item.evidence,
                                                              item.outcome, item.reason)).rstrip())
    for item in found.unfinished:
        lines.append(display.clean("unfinished: %s %s %s %s %s" % (item.time, item.op, item.key, item.level,
                                                                    item.evidence)))
    if found.unfinished:
        lines.append("unfinished does not mean the change was not made: a process that was stopped leaves an attempt "
                     "with no outcome after it acted")
    for text in found.problems:
        lines.append(display.clean("problem: " + text))
    return lines
