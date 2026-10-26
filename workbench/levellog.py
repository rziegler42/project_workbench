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
from .wbkit import display, safefs

LOG = "level-log"
MAX_BYTES = 4 * 1024 * 1024
MAX_LINE = 1024
MAX_REASON = 200
MAX_KEY = 96
_ID = re.compile(r"[0-9a-f]{16}\Z")
_KEY = re.compile(r"[a-z][a-z0-9-]*( [a-z][a-z0-9-]*)*\Z")
_EVIDENCE = re.compile(r"[A-Za-z0-9._:/-]{0,128}\Z")
_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
OUTCOMES = ("done", "refused")


class LogError(Exception):
    """The attempt could not be written, so the command must do nothing."""


class LogFull(LogError):
    """The log is at its limit."""


class OutcomeError(Exception):
    """The outcome could not be written after the change was made."""


Operation = collections.namedtuple("Operation", "op time key level evidence outcome outcome_time reason")
Read = collections.namedtuple("Read", "operations unfinished problems")


def _append(guarded, line):
    try:
        safefs.append_line(guarded.root, LOG, line, MAX_BYTES, MAX_LINE)
    except safefs.FullError:
        raise LogFull("the level log %s is full; the owner rotates it by hand, and nothing was done" % LOG)
    except safefs.SafeFsError as exc:
        raise LogError("the level log %s cannot be written: %s" % (LOG, display.clean(str(exc))[:200]))


def begin(guarded, key, level, evidence=""):
    """Write the attempt line and return its operation identifier. ``ValueError`` writes nothing."""
    if not isinstance(key, str) or len(key) > MAX_KEY or not _KEY.match(key):
        raise ValueError("a log key must be a valid key name of at most %d characters" % MAX_KEY)
    if level not in levels.LEVELS or level == levels.BLOCK:
        raise ValueError("only a level other than block is logged")
    if not isinstance(evidence, str) or not _EVIDENCE.match(evidence):
        raise ValueError("log evidence must be at most 128 characters of letters, digits and . _ : / -")
    op = secrets.token_hex(8)
    line = "A\t%s\t%s\t%s\t%s\t%s\n" % (op, approvals.utc_now(), key, level, evidence)
    _append(guarded, line.encode("ascii"))
    return op


def finish(guarded, op, outcome, reason=""):
    """Write the outcome line for `op`. ``ValueError`` writes nothing; ``OutcomeError`` when it cannot be written."""
    if not isinstance(op, str) or not _ID.match(op):
        raise ValueError("a log operation identifier is 16 hexadecimal characters")
    if outcome not in OUTCOMES:
        raise ValueError("a log outcome is done or refused")
    text = display.ascii_text(reason)[:MAX_REASON]
    line = "O\t%s\t%s\t%s\t%s\n" % (op, approvals.utc_now(), outcome, text)
    try:
        _append(guarded, line.encode("ascii"))
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
