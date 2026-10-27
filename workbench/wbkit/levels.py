"""Permission levels for a command, and the level log's lines: what an owner-run command and a helper share.

The owner's personal settings give each command a level (``docs/specs/command-permissions.md``): ``block``, ``ask``,
``delegated`` or ``none``. This module holds the part that needs nothing else of the workbench:

* ``may_run``: given a level the caller has already read and verified, and whether standard input and output are
  terminals, may the command run? A terminal always may (the command's own prompt applies); without one only ``none``
  does. A level that is missing, unreadable or not one of the four is treated as no level, so only a terminal runs.
  The caller reads the level and checks the rendering record; a kit function cannot, and does not guess.
* the log's lines and their append: ``attempt_line``, ``outcome_line``, ``begin``, ``finish`` and ``finish_refused``.
  A line is tab-separated ASCII of at most 1,024 bytes (``A <id> <time> <key> <level> <evidence>`` and
  ``O <id> <time> done|refused <reason>``). The writer appends through ``safefs.append_line`` and never reads the file,
  so a damaged log cannot stop a run; it refuses a link, a non-regular file and a second hard link. The attempt is
  written before the change and the outcome after it; a run that changes nothing writes no entry.

It imports the standard library and the kit only, and knows no module. Adding to it does not raise ``wbkit.API``.
"""

import datetime
import os
import re

from . import display, safefs

BLOCK, ASK, DELEGATED, NONE = "block", "ask", "delegated", "none"
LEVELS = (BLOCK, ASK, DELEGATED, NONE)  # strictest first

LOG = "level-log"
MAX_BYTES = 4 * 1024 * 1024
MAX_LINE = 1024
MAX_REASON = 200
MAX_KEY = 96
OUTCOMES = ("done", "refused")
# Whole-string patterns, used with ``re.fullmatch``; the installer compiles its own copies to read the log.
ID_PATTERN = r"[0-9a-f]{16}"
KEY_PATTERN = r"[a-z][a-z0-9-]*( [a-z][a-z0-9-]*)*"
EVIDENCE_PATTERN = r"[A-Za-z0-9._:/-]{0,128}"
TIME_PATTERN = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"


class LogError(Exception):
    """The attempt could not be written, so the command must do nothing."""


class LogFull(LogError):
    """The log is at its limit."""


class OutcomeError(Exception):
    """The outcome could not be written after the change was made."""


def is_terminal(stream):
    """True when `stream` is a terminal; a stream that cannot say is not one."""
    try:
        return os.isatty(stream.fileno())
    except (AttributeError, OSError, ValueError):
        return False


def may_run(level, terminal):
    """True when a command whose verified level is `level` may run, `terminal` saying whether both of its streams are
    terminals (the result of ``is_terminal``; only ``True`` counts, so a stream or a string passed by mistake is not a
    terminal). Only the level ``none`` runs without one."""
    return terminal is True or (isinstance(level, str) and level == NONE)


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id():
    return os.urandom(8).hex()


def _check_header(op, time):
    if not isinstance(op, str) or not re.fullmatch(ID_PATTERN, op):
        raise ValueError("a log operation identifier is 16 hexadecimal characters")
    if not isinstance(time, str) or not re.fullmatch(TIME_PATTERN, time):
        raise ValueError("a log time is YYYY-MM-DDTHH:MM:SSZ")


def attempt_line(op, time, key, level, evidence=""):
    """The attempt line as bytes. ``ValueError`` for a key, level or evidence the log would not read back."""
    _check_header(op, time)
    if not isinstance(key, str) or len(key) > MAX_KEY or not re.fullmatch(KEY_PATTERN, key):
        raise ValueError("a log key must be a valid key name of at most %d characters" % MAX_KEY)
    if level not in LEVELS or level == BLOCK:
        raise ValueError("only a level other than block is logged")
    if not isinstance(evidence, str) or not re.fullmatch(EVIDENCE_PATTERN, evidence):
        raise ValueError("log evidence must be at most 128 characters of letters, digits and . _ : / -")
    return ("A\t%s\t%s\t%s\t%s\t%s\n" % (op, time, key, level, evidence)).encode("ascii")


def outcome_line(op, time, outcome, reason=""):
    """The outcome line as bytes. ``ValueError`` for an identifier or outcome the log would not read back. The reason is
    cleaned to printable ASCII and cut, so it holds no tab or newline."""
    _check_header(op, time)
    if outcome not in OUTCOMES:
        raise ValueError("a log outcome is done or refused")
    text = display.ascii_text(reason)[:MAX_REASON]
    return ("O\t%s\t%s\t%s\t%s\n" % (op, time, outcome, text)).encode("ascii")


def append(root_path, line, max_bytes=None):
    """Append `line` to the log below the existing directory `root_path`. ``LogFull`` at the limit, ``LogError`` otherwise."""
    try:
        safefs.append_line(root_path, LOG, line, MAX_BYTES if max_bytes is None else max_bytes, MAX_LINE)
    except safefs.FullError:
        raise LogFull("the level log %s is full; the owner rotates it by hand, and nothing was done" % LOG)
    except safefs.SafeFsError as exc:
        raise LogError("the level log %s cannot be written: %s" % (LOG, display.clean(str(exc))[:200]))


def begin(root_path, key, level, evidence=""):
    """Write the attempt line and return its operation identifier. ``ValueError`` writes nothing."""
    op = new_id()
    append(root_path, attempt_line(op, utc_now(), key, level, evidence))
    return op


def finish(root_path, op, outcome, reason=""):
    """Write the outcome line for `op`. ``ValueError`` writes nothing; ``OutcomeError`` when it cannot be written."""
    line = outcome_line(op, utc_now(), outcome, reason)
    try:
        append(root_path, line)
    except LogError as exc:
        raise OutcomeError(str(exc))


def finish_refused(root_path, op, reason):
    """Write a ``refused`` outcome for a command that is already refusing. A failure to write it is not reported
    again: the attempt stays listed as unfinished."""
    try:
        finish(root_path, op, "refused", reason)
    except OutcomeError:
        pass
