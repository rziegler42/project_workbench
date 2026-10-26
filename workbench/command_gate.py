"""``gate-command <harness>``: the command gate, the Bash hook a harness's rendered settings run when a key is at
``ask`` or ``none``.

``docs/decisions/2026-10-26-ask-level-command-gate.md`` (with its clarification note) and the plan
``2026-10-26-command-permission-levels``, Increment J. At ``ask`` and ``none`` the terminal test no longer applies, so the
barrier is the harness's own ``ask`` rule, which matches the command text. A command that no rule names (``bash -c '...'``)
is decided by the harness's classifier in auto mode. This gate reads one Bash tool call as JSON on standard input and:

* allows a command that names no word of a relaxed command;
* allows a command that is exactly the simple command the ``ask`` rule matches, on the raw text with single spaces and case
  kept (``wb approve-plan <path> [--digest <32 hex>]``, or the same through the guarded store's own ``bin/wb``), so the
  harness then prompts the owner;
* blocks every other command that names such a word, in its folded text or in its *skeleton* (the folded text with every
  character that is not a letter or a digit removed, so quote splicing, a backslash or a punctuation mark does not hide the
  word), also after the static ``$'...'`` strings are decoded as bash decodes them, and every command that holds ``$'`` or
  ``$"`` while the word's letters appear in the skeleton in order;
* blocks on a malformed input, an oversized command, a failure to find the project and any crash or deadline.

It prints nothing and returns 0 to allow, or one ``refused:`` line and 2 to block (the only code a harness takes for a
block; ``gate_hook.guard`` makes every failure a block). The exact token ``delegate-approve-plan`` is removed before the
search: it is the agent-safe delegated command.

What it cannot see, and the owner accepted in writing (a ``*`` is allowed to stand for at most three letters, so ``wb appr*``
with a file named ``approve-plan`` in the directory is not seen either): a word built at run time (variables, ``printf`` escapes, a decoded
string), a script file that holds the call and is then run, a function or alias defined earlier, and a settings file edited
and restored between two commands. A hook is a speed bump and not a boundary.
"""

import re

from . import gate_hook
from .wbkit import display

USAGE = "usage: wb gate-command <harness>\n"
MAX_COMMAND = 64 * 1024
RELAXED = ("ask", "none")
# The agent-safe command whose name contains the word of ``approve-plan``.
EXEMPT = ("delegate-approve-plan",)
_TOKEN = r"[A-Za-z0-9._/:=-]+"
_PATH = r"[A-Za-z0-9._/][A-Za-z0-9._/-]*"
_DIGEST = r"[0-9a-f]{32}"

Refusal = gate_hook.Refusal


def words(key):
    """The words of the command `key` names, in order: ``approve-plan``; ``wb run <command> <argument>`` gives both."""
    if key == "approve-plan":
        return ["approve-plan"]
    parts = key.split(" ")
    if parts[:2] == ["wb", "run"] and len(parts) >= 4:
        return parts[2:]
    if parts[0] == "wb" and len(parts) == 2:
        return [parts[1]]
    return []


def forms(key, store_bin):
    """The compiled patterns of the exact simple commands the ``ask`` rule of `key` matches, through ``wb`` and through the
    guarded store's own ``bin/wb`` (`store_bin`)."""
    heads = ["wb", re.escape(store_bin)]
    if key == "approve-plan":
        return [re.compile("%s approve-plan %s( --digest %s)?" % (head, _PATH, _DIGEST)) for head in heads]
    found = words(key)
    if not found:
        return []
    tail = " ".join(re.escape(word) for word in found)
    middle = " run " if key.startswith("wb run ") else " "
    return [re.compile("%s%s%s(?: %s)*" % (head, middle, tail, _TOKEN)) for head in heads]


def _folded(text):
    return gate_hook.fold(text)


_ANSI_C = re.compile(r"\$'((?:[^'\\]|\\.)*)'", re.DOTALL)
_SIMPLE = {"a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v",
           "\\": "\\", "'": "'", '"': '"', "?": "?"}
_ESCAPE = re.compile(r"\\(?:x([0-9a-fA-F]{1,2})|u([0-9a-fA-F]{1,4})|U([0-9a-fA-F]{1,8})|([0-7]{1,3})|(.))", re.DOTALL)


def _escape(match):
    hexa, short, long_, octal, other = match.groups()
    try:
        if hexa:
            return chr(int(hexa, 16))
        if short:
            return chr(int(short, 16))
        if long_:
            return chr(int(long_, 16))
        if octal:
            return chr(int(octal, 8) & 0xFF)
    except (ValueError, OverflowError):
        return ""
    return _SIMPLE.get(other, "\\" + other)


def decoded_views(text):
    """`text` and, for every place a ``$'`` starts a string that closes, `text` with that one string decoded as bash decodes
    it. A ``$'`` is tried at every position, because a stray one earlier in the command (``echo '$'``, ``"$'"``) would pair
    with the wrong quote if the text were decoded from left to right in one pass."""
    views = [text]
    for at in range(len(text)):
        if text.startswith("$'", at):
            match = _ANSI_C.match(text, at)
            if match:
                views.append(text[:at] + _ESCAPE.sub(_escape, match.group(1)) + text[match.end():])
    return views


_ESCAPE_TOKEN = re.compile(r"\\(?:x[0-9a-fA-F]{1,2}|u[0-9a-fA-F]{1,4}|U[0-9a-fA-F]{1,8}|[0-7]{1,3})")
_WILD = "\0"
_GLOB_CLASS = re.compile(r"\[[^\]]*\]")
_GLOB_STAR = 3  # a ``*`` can stand for many letters; this many are allowed for (more would block most globs)
# Characters that let a command spell a word without writing it: parameter and command expansion, and the glob and
# brace characters. When one is present the letters of a guarded word are looked for in order.
_PATTERN_CHARS = "$?*[{`"
# The letters of a guarded word must fall within this many times the word's length, so a long command that happens to
# hold the letters scattered through it is not taken for a spelling of the word.
_WINDOW = 3


def _skeleton(text):
    return "".join(char for char in text if char.isalnum())


def _in_order(text, pieces):
    """Whether the `pieces` occur in `text` one after another."""
    at = 0
    for piece in pieces:
        found = text.find(piece, at)
        if found < 0:
            return False
        at = found + len(piece)
    return True


def _subsequence(text, letters):
    """Whether the characters of `letters` occur in `text` in order, not necessarily next to each other, all within a
    stretch of ``_WINDOW`` times their number. A ``\0`` in `text` (an escape sequence or a glob character, which can
    stand for any letter) matches any character."""
    width = _WINDOW * len(letters)
    for start in range(len(text)):
        if text[start] != letters[0] and text[start] != _WILD:
            continue
        chars = iter(text[start:start + width])
        if all(any(char == wanted or char == _WILD for char in chars) for wanted in letters):
            return True
    return False


def _names(folded, skeleton, pieces):
    """Whether the command text names the words `pieces`, as written or by its skeleton."""
    return _in_order(folded, pieces) or _in_order(skeleton, [_skeleton(piece) for piece in pieces])


def judge(command, keys, store_bin):
    """``None`` when `command` may go ahead, or the reason it may not. `keys` are the relaxed keys."""
    text = command.strip()
    views = []
    for version in decoded_views(text):
        folded = _folded(version)
        for token in EXEMPT:
            folded = re.sub(r"(?<![a-z0-9-])%s(?![a-z0-9-])" % re.escape(_folded(token)), " ", folded)
        views.append((folded, _skeleton(folded)))
    spelled = _ESCAPE_TOKEN.sub(_WILD, views[0][0])
    spelled = _GLOB_CLASS.sub(_WILD, spelled).replace("?", _WILD).replace("*", _WILD * _GLOB_STAR)
    wild = "".join(char for char in spelled if char.isalnum() or char == _WILD)
    pattern = any(char in text for char in _PATTERN_CHARS)
    for key in keys:
        pieces = [_folded(word) for word in words(key)]
        if not pieces:
            continue
        if any(_names(folded, skel, pieces) for folded, skel in views):
            if any(form.fullmatch(text) for form in forms(key, store_bin)):
                continue
            return ("the command names %s, which the owner has set to ask or none here, and is not exactly the simple "
                    "command the ask rule matches; run it as `wb %s ...` on its own" % (
                        display.ascii_text(" ".join(pieces))[:80], " ".join(pieces)[:60]))
        if pattern and _subsequence(wild, _skeleton("".join(pieces))):
            return ("the command uses an expansion, a pattern or an escape and holds the letters of %s in order, so it "
                    "may spell a command that the owner has set to ask or none here"
                    % display.ascii_text(" ".join(pieces))[:80])
    return None


def run(stdin, err, prepare, tool, field, *, deadline=gate_hook.DEADLINE):
    """Decide the tool call on `stdin`. `tool` and `field` come from the harness's layout. `prepare(cwd)` returns
    ``(table, store bin path)`` or raises ``Refusal``. Returns 0 to allow; otherwise one ``refused:`` line and 2."""

    def body(limit):
        cwd, name, given, _ = gate_hook._read(stdin)
        gate_hook.check_cwd(cwd)
        if name != tool:
            raise Refusal("the tool %s is not the one this gate reads" % display.ascii_text(name)[:40])
        command = given.get(field)
        if not isinstance(command, str):
            raise Refusal("the %s call has no %s to read" % (display.ascii_text(name)[:40], field))
        if "\0" in command or len(command) > MAX_COMMAND:
            raise Refusal("the command holds a NUL byte or is longer than %d characters" % MAX_COMMAND)
        table, store_bin = prepare(cwd)
        relaxed = [key for key, level in table.items() if level in RELAXED]
        reason = judge(command, relaxed, store_bin)
        if reason:
            raise Refusal(reason)

    return gate_hook.guard(err, body, deadline=deadline)
