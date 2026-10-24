"""``agent-gate <harness> <agent>``: the guard a confined agent's rendered hook runs on every call of that agent.

``docs/specs/harness-modules.md``, "The agent gate". It reads one tool call as JSON on standard input and decides
whether the agent may make it. It prints nothing and returns 0 to allow. It prints one ``refused:`` line on standard
error and returns 2 to refuse, because 2 is the only code the harness takes for a block; every other outcome, a crash
included, is a refusal, and a total deadline of ``gate_hook.DEADLINE`` seconds ends in a refusal too (a hook that is
cut off by the harness lets the call through).

The limits come from the installed module's neutral item for the agent (``.workbench/<package>/<module>/harness/
neutral/agents/<agent>.md``), read after its hash equals the one the committed manifest records, and never from the
rendered agent file, which the agent's own file tools could edit. The layout of the harness gives the tool names that
write or run and the template of the scratch directory. In order, for every call:

1. The input is one JSON object of at most ``gate_hook.MAX_TRANSPORT`` bytes with a string ``cwd``, a string
   ``session_id``, a string ``tool_name`` and an object ``tool_input``.
2. The agent is declared by exactly one installed module, and declares ``writes`` or ``run``.
3. The scratch directory is filled from the layout's template, the user id, ``cwd`` and ``session_id``; a part that
   cannot be filled is a refusal. A working directory or project root at or below the template's literal leading
   part (the part before its first placeholder) is a refusal, since the agent can build a project there.
4. The tool is one the layout gives ``edit`` and the agent holds by ``writes``, or one it gives ``shell`` and the agent
   holds by ``run``; any other tool is a refusal.
5. An edit's ``file_path`` is a plain absolute path, spelled as the scratch directory is spelled, strictly below it,
   with no link in any part that exists. A part that does not exist yet is placed against the scratch directory and is
   not counted as outside it.
6. A command is a string of at most ``MAX_COMMAND`` characters from a closed safe set, split on single spaces, and
   equal token for token to one pinned pattern. A ``{scratch}/<name>`` token must be the scratch directory's own path
   to ``<name>`` by the rules of step 5. Nothing is run, expanded or parsed by a shell here.

Nothing is written in the project or the store.
"""

import errno
import hashlib
import os
import re
import stat

from . import approvalcmd, gate_hook, harnesses, manifest, neutral
from .gate_hook import Refusal
from .wbkit import display, project, safefs

MAX_COMMAND = 1000
MAX_TARGET = gate_hook.MAX_TARGET
USAGE = "usage: wb agent-gate <harness> <agent>\n"

_SESSION = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_NOT_ALNUM = re.compile(r"[^A-Za-z0-9]")
BASH_FIELDS = ("command", "description", "timeout", "run_in_background")
_PLACEHOLDER = re.compile(r"\{(uid|cwd_key|session_id)\}")
SAFE_COMMAND = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._/-:=+@% ")
AGENT_DIR = ".workbench/%s/%s/harness/neutral/agents/%s.md"
EDIT_FIELD = "file_path"


# --- the declared agent -----------------------------------------------------------------------


def declared(cwd, agent):
    """``(project root, neutral.Item)`` of the confined agent `agent` that exactly one installed module of the project holding
    `cwd` declares, or ``Refusal``. The module's ``module.json`` and the agent's file must each equal the hash the
    manifest records."""
    try:
        root, _, installed = approvalcmd.installed_modules(cwd)
    except approvalcmd.ApprovalError as exc:
        raise Refusal(str(exc))
    found = []
    try:
        with safefs.Root(root, "project root") as held:
            hashes = {entry["path"]: entry["hash"] for entry in manifest.parse(held.read_file(project.MANIFEST))["files"]}
            for item in installed:
                rel = AGENT_DIR % (item.package, item.module.name, agent)
                if rel not in hashes:
                    continue
                data = held.read_file(rel, limit=neutral.MAX_ITEM_BYTES)
                if hashlib.sha256(data).hexdigest() != hashes[rel]:
                    raise Refusal("%s has changed since it was installed" % display.ascii_text(rel)[:200])
                found.append((rel, data))
    except (safefs.SafeFsError, manifest.ManifestError) as exc:
        raise Refusal(display.clean(str(exc))[:300])
    if len(found) != 1:
        raise Refusal("%d installed modules declare the agent %s; exactly one is needed"
                      % (len(found), display.ascii_text(agent)[:64]))
    try:
        items = neutral.read_items({"agents/%s.md" % agent: found[0][1]})
    except neutral.NeutralError as exc:
        raise Refusal("the agent %s cannot be read: %s" % (display.ascii_text(agent)[:64], display.clean(str(exc))[:200]))
    item = items[0]
    if not (item.writes or item.run):
        raise Refusal("the agent %s declares no writes and no run, so it is not a confined agent"
                      % display.ascii_text(agent)[:64])
    return root, item


# --- the scratch directory and the paths below it ----------------------------------------------


def scratch_parts(template, cwd, session):
    """The components of the scratch directory the layout's `template` names for this session, or ``Refusal``."""
    if not _SESSION.match(session):
        raise Refusal("the session id is not plain letters, digits, '_' and '-'")
    gate_hook.check_cwd(cwd)
    if not cwd.isascii():
        raise Refusal("the working directory has a character the scratch directory's name cannot be derived from")
    key = _NOT_ALNUM.sub("-", cwd)
    values = {"uid": str(os.getuid()), "cwd_key": key, "session_id": session}
    filled = _PLACEHOLDER.sub(lambda match: values[match.group(1)], template)
    return [piece for piece in filled.split("/") if piece]


def keep_out(template, path):
    """Refuse a `path` (a project root or working directory) at or below the literal leading part of the scratch
    `template`, the part before its first placeholder. The confined agent can write there, so a project it builds
    there, with a manifest and agent file of its own making, would otherwise be taken for the installed one."""
    literal = []
    for part in template.split("/")[1:]:
        if "{" in part:
            break
        literal.append(part)
    shown = [piece for piece in path.split("/") if piece]
    for spelling in (shown, [piece for piece in os.path.realpath(path).split("/") if piece]):
        if [gate_hook.fold(p) for p in spelling[:len(literal)]] == [gate_hook.fold(p) for p in literal]:
            raise Refusal("the project lies inside the directory the confined agent can write in")


def _examined(parts):
    """Refuse a link in any part of the absolute path `parts` that exists. The first part that does not exist ends
    the walk; any other error while examining a part is a refusal and never an "outside"."""
    here = ""
    for part in parts:
        here += "/" + part
        try:
            if stat.S_ISLNK(os.lstat(here).st_mode):
                raise Refusal("a part of the path is a symbolic link: %s" % display.ascii_text(part)[:80])
        except OSError as exc:
            if exc.errno in (errno.ENOENT, errno.ENOTDIR):
                return
            raise Refusal("a part of the path cannot be examined: %s" % (exc.strerror or "unknown error"))


def place(path, scratch):
    """Return when the text `path` is a plain absolute path strictly below the scratch directory `scratch` (its
    components), spelled as `scratch` is spelled, with no link in any part that exists; else ``Refusal``."""
    if not isinstance(path, str) or not path:
        raise Refusal("the call has no path to place")
    if len(path) > MAX_TARGET or any(ord(c) < 32 or ord(c) == 127 for c in path):
        raise Refusal("the path is too long or holds a control character")
    if not path.startswith("/"):
        raise Refusal("the path is not absolute")
    parts = path[1:].split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise Refusal("the path has an empty part, '.' or '..'")
    n = len(scratch)
    if parts[:n] == scratch:
        if len(parts) == n:
            raise Refusal("the path is the scratch directory itself, not a file below it")
    elif len(parts) >= n and [gate_hook.fold(part) for part in parts[:n]] == [gate_hook.fold(part) for part in scratch]:
        raise Refusal("the path spells the scratch directory in another way")
    else:
        raise Refusal("the path is not below the scratch directory")
    _examined(parts)


# --- a command --------------------------------------------------------------------------------


def _matches(tokens, pattern, scratch):
    """Whether the split command `tokens` equals `pattern` token for token; a ``{scratch}/<name>`` token equals
    the scratch directory's path to ``<name>``, whose parts are then examined."""
    pieces = pattern.split(" ")
    if len(pieces) != len(tokens):
        return False
    inside = "/" + "/".join(scratch) + "/"
    named = []
    for piece, token in zip(pieces, tokens):
        if piece.startswith(neutral.SCRATCH_PREFIX):
            if token != inside + piece[len(neutral.SCRATCH_PREFIX):]:
                return False
            named.append(token)
        elif piece != token:
            return False
    for token in named:
        place(token, scratch)
    return True


def command_allowed(command, patterns, scratch):
    """Return when `command` matches one of `patterns`; else ``Refusal``."""
    if not isinstance(command, str) or not command:
        raise Refusal("the call has no command to match")
    if len(command) > MAX_COMMAND:
        raise Refusal("the command is longer than %d characters" % MAX_COMMAND)
    if not set(command) <= SAFE_COMMAND:
        raise Refusal("the command holds a character outside letters, digits, . / _ - : = + @ %% and spaces")
    tokens = command.split(" ")
    if "" in tokens:
        raise Refusal("the command has an empty token")
    if not any(_matches(tokens, pattern, scratch) for pattern in patterns):
        raise Refusal("the command matches none of the agent's pinned commands")


# --- the decision ------------------------------------------------------------------------------


def decide(facts, agent, document):
    """Return when the call in `document` (the hook input) may go ahead; ``Refusal`` otherwise. `facts` is the
    harness layout's ``agent_gate`` entry: ``(edit tool names, shell tool names, scratch template)``."""
    cwd, session = document.get("cwd"), document.get("session_id")
    tool, given = document.get("tool_name"), document.get("tool_input")
    if not (isinstance(cwd, str) and isinstance(session, str) and isinstance(tool, str)
            and isinstance(given, dict)):
        raise Refusal("the hook input needs a string cwd, a string session_id, a string tool_name and an object "
                      "tool_input")
    edits, shells, template = facts
    scratch = scratch_parts(template, cwd, session)
    keep_out(template, cwd)
    root, item = declared(cwd, agent)
    keep_out(template, root)
    if tool in edits and item.writes:
        place(given.get(EDIT_FIELD), scratch)
    elif tool in shells and item.run:
        if not set(given) <= set(BASH_FIELDS):
            raise Refusal("the shell call has a field the guard does not know: %s"
                          % display.ascii_text(sorted(set(given) - set(BASH_FIELDS))[0])[:40])
        command_allowed(given.get("command"), item.run, scratch)
    else:
        raise Refusal("the tool %s is not one the agent %s holds" % (display.ascii_text(tool)[:40],
                                                                     display.ascii_text(agent)[:64]))


def run(stdin, err, prepare, agent, *, deadline=gate_hook.DEADLINE):
    """Decide the call on `stdin`. `prepare` returns the harness's ``agent_gate`` entry, or raises ``Refusal``. The
    exit code is ``gate_hook.guard``'s."""

    def body(limit):
        facts = prepare()
        document, _ = gate_hook.document(stdin)
        decide(facts, agent, document)

    return gate_hook.guard(err, body, deadline=deadline)


def known(distribution, harness):
    """The ``agent_gate`` entry of the known harness `harness`, or ``Refusal``."""
    facts = harnesses.known(distribution).get(harness)
    if not facts or not facts.get("agent_gate"):
        raise Refusal("%s is not a known harness whose layout declares a per-agent hook and scratch directory"
                      % display.ascii_text(harness)[:64])
    return facts["agent_gate"]
