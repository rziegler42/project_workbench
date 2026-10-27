"""What the owner's levels table renders into a harness, and the record attach keeps of it.

``docs/specs/command-permissions.md``, "Rendering". At attach a harness that provides ``permissions`` gets, for each key
whose command it can match, a ``deny`` at ``block`` and at ``delegated``, an ``ask`` at ``ask`` and nothing at ``none``.
The floor's ``ask`` rules and the guarded store's deny are not touched. Attach writes, in the guarded store, a record
of what it rendered; a key reads as ``ask`` or ``none`` only while that record, the table and the harness file all
agree, and as ``block`` otherwise. ``delegated`` and ``block`` do not depend on the record.

The record: ``{"format": 2, "harness": "<module name>", "permissions": true|false, "gate": true|false,
"table_digest": <sha-256>, "file": "<path of the permissions file>" | null, "file_hash": <sha-256> | null,
"shared": {"path": <the shared project settings file> | null, "hash": <sha-256> | null}, "keys": {<every key>:
"deny" | "ask" | "none" | "unruled"}}``. ``gate`` says the command gate's Bash hook was rendered (``command_gate.py``);
without it a key reads ``block``, because at ``ask`` and ``none`` the rule alone is a text match the classifier can walk around.
``shared`` is the shared settings file the layout names: its hash is taken at attach (``null`` when it did not exist), and
a file that is created, changed or removed later makes ``ask`` and ``none`` read ``block``. ``unruled`` is a key with no command to match (a checkpoint that is not a command): it renders
nothing, and is never read as ``none``. The record attests what attach rendered; the live file is hashed when a command
runs, so an edit after attach is seen. A harness that provides no ``permissions`` renders nothing and leaves no
record, which reads as ``block``.
"""

import collections
import hashlib
import json
import re

from . import declarations, levels, localmanifest, rules, settings
from .wbkit import safefs

RECORD = "projects/%s/rendering"
FORMAT = 2
LOCAL_MANIFEST = localmanifest.PATH
_SHA = re.compile(r"[0-9a-f]{64}\Z")
RULES = ("deny", "ask", "none", "unruled")

Plan = collections.namedtuple("Plan", "keys ask open deny", defaults=((),))

# The single-word agent-safe actions that have a key (``levels.agent_keys``), as the word after ``wb``.
_AGENT_WORDS = frozenset(key[3:] for key in levels.agent_keys() if " " not in key[3:])


def key_patterns(key):
    """The shell patterns that deny the command `key` names (every spelling), or ``[]`` for a key with no command.

    A key is an owner-run command, an agent-safe action (``wb check``, ``wb preview install``) or an argument a module
    declares (``wb run <command> <argument>``). A hook entry point, a dispatcher word and a checkpoint that is not a
    command have no patterns."""
    if key == levels.APPROVE_PLAN:
        return rules.owner_run_command_patterns(key)
    if key.startswith("wb run "):
        parts = key.split(" ")
        if len(parts) >= 4:
            return rules.command_owner_patterns(parts[2], [" ".join(parts[3:])])
        return []
    if key.startswith("wb preview "):
        action = key[len("wb preview "):]
        return rules.owner_run_command_patterns("preview " + action) if action in rules.PREVIEW_ACTIONS else []
    if key.startswith("wb ") and (key[3:] in rules.OWNER_RUN or key[3:] in _AGENT_WORDS):
        return rules.owner_run_command_patterns(key[3:])
    return []


def _wb_forms(patterns):
    """The patterns spelled with the launcher ``wb``. The interpreter spellings (``python3 -m workbench``) stay denied at
    ``ask`` and ``none``: a prompt for them would let a planted package run under the owner's yes."""
    return [pattern for pattern in patterns if pattern.startswith("wb ")]


def plan(table, gated=True):
    """The ``Plan`` for the effective `table` (key to level): the rule each key renders, the patterns to ask and the
    patterns not to deny (those at ``ask`` and ``none``, and only their ``wb`` spellings). With `gated` false the harness
    cannot render the command gate, so no key is relaxed and every command renders a ``deny``."""
    keys, ask, opened, denied = {}, [], [], []
    for key in table:
        patterns = key_patterns(key)
        level = table[key]
        if not patterns:
            keys[key] = "unruled"
        elif level == levels.ASK and gated:
            keys[key] = "ask"
            ask.extend(_wb_forms(patterns))
            opened.extend(_wb_forms(patterns))
        elif level == levels.NONE and gated:
            keys[key] = "none"
            opened.extend(_wb_forms(patterns))
        else:
            keys[key] = "deny"
            denied.extend(patterns)
    return Plan(keys, ask, opened, denied)


def digest(table):
    """A digest of the effective table, so a record says which table it rendered."""
    text = json.dumps(dict(table), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def table_of(guarded, checkpoints, commands):
    """The effective table (key to level) for the owner's settings, the declared `checkpoints` and the installed
    `commands` (``(name, owner-run arguments, all declared arguments)``, the last optional).

    An agent-safe key, and a declared argument that is not owner-run, is in it only when its level is not its default
    ``none``: a key at ``none`` renders nothing, so it must not change the digest a record says it rendered from, and the
    command gate must not count it as relaxed. The default table is therefore the one it was before those keys had a
    level, and a key the owner sets to ``block`` is in it and renders a ``deny``."""
    keys = levels.registry(checkpoints, commands)
    table = settings.effective(settings.load(guarded), checkpoints, (), commands).levels
    return {name: level for name, level in table.items() if not (keys[name].agent and level == levels.NONE)}


def current_table(guarded, start):
    """``(table, root, project id)`` for the project that holds the directory `start`: the effective table built from
    the installed modules' process checkpoints and commands, as ``harnessstage.stage`` builds it at attach. ``ApprovalError``
    when the project or an installed declaration cannot be used; ``levels.RegistryError`` when two declarations give one
    key."""
    from . import approvalcmd
    root, ident, found = approvalcmd.installed_modules(start)
    table = table_of(
        guarded,
        tuple(name for item in found if item.module.type == "process" for name in item.module.checkpoints),
        [(command.name, command.owner, command.arguments) for item in found for command in item.module.commands])
    return table, root, ident


def record_of(harness, provides_permissions, table, built, path, file_hash, gate=False, shared=None):
    """The record body for a harness `harness` (the module name) that wrote `path` with hash `file_hash`, with the
    command gate rendered or not, and `shared` the path of the shared settings file or None. The shared file's hash is
    filled in by ``attach`` when it writes the record (``with_shared_hash``)."""
    return {"format": FORMAT, "harness": harness, "permissions": bool(provides_permissions), "gate": bool(gate),
            "table_digest": digest(table), "file": path, "file_hash": file_hash,
            "shared": {"path": shared, "hash": None}, "keys": dict(built.keys)}


UNREADABLE = "unreadable"


def with_shared_hash(record, project_root):
    """`record` with the hash of the shared settings file as it is now in the project at `project_root`: ``None`` when it
    does not exist. A file that cannot be read as a regular file (a link, a directory, one that is too large) cannot be
    watched, so the record then says no gate was rendered and every key reads ``block``."""
    shared = record.get("shared") or {}
    path = shared.get("path")
    if path is None:
        return record
    found = live_hash(project_root, path)
    if found == UNREADABLE:
        return dict(record, gate=False, shared={"path": path, "hash": None})
    return dict(record, shared={"path": path, "hash": found})


def serialize(record):
    return (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def write(guarded, project_id, record):
    guarded.write(RECORD % project_id, serialize(record))


def _valid(record):
    if not isinstance(record, dict) or record.get("format") != FORMAT or isinstance(record.get("format"), bool):
        return False
    if not isinstance(record.get("harness"), str) or not isinstance(record.get("permissions"), bool) \
            or not isinstance(record.get("gate"), bool):
        return False
    shared = record.get("shared")
    if not isinstance(shared, dict) or set(shared) != {"path", "hash"}:
        return False
    if shared["path"] is not None and (not isinstance(shared["path"], str) or not safefs.relpath_ok(shared["path"])):
        return False
    if shared["hash"] is not None and (not isinstance(shared["hash"], str) or not _SHA.match(shared["hash"])):
        return False
    if not isinstance(record.get("table_digest"), str) or not _SHA.match(record["table_digest"]):
        return False
    path, file_hash = record.get("file"), record.get("file_hash")
    if path is not None and (not isinstance(path, str) or not safefs.relpath_ok(path)):
        return False
    if file_hash is not None and (not isinstance(file_hash, str) or not _SHA.match(file_hash)):
        return False
    keys = record.get("keys")
    return isinstance(keys, dict) and all(isinstance(k, str) and v in RULES for k, v in keys.items())


def read(guarded, project_id):
    """The record, or ``None`` when it is missing, not a regular file, damaged or of another form."""
    rel = RECORD % project_id
    try:
        if guarded.kind(rel) != "file":
            return None
        record = declarations.parse_json(guarded.read(rel))
    except (safefs.SafeFsError, ValueError):
        return None
    return record if _valid(record) else None


def live_hash(root, path):
    """The SHA-256 of the regular file `path` below the project `root`; ``None`` when it, or a directory above it, is not
    there; ``UNREADABLE`` when something is there that cannot be read as a regular file (a link, a directory, a file with
    another hard link, one over the size limit). Absent and unreadable are different: only absent matches a record that
    saw no file."""
    try:
        with safefs.Root(root, "project root") as held:
            data = held.read_if_present(path)
    except safefs.SafeFsError:
        return UNREADABLE
    return None if data is None else hashlib.sha256(data).hexdigest()


def _attached_harness(root):
    try:
        with safefs.Root(root, "project root") as held:
            document = localmanifest.parse(held.read_file(LOCAL_MANIFEST))
    except (safefs.SafeFsError, localmanifest.LocalManifestError):
        return None
    return document["harness"]


def effective_level(guarded, project_id, root, table, key):
    """Not for an agent-safe key or a declared module argument that is not owner-run: ``table_of`` leaves such a key out
    while it is at its default ``none``, and a key missing from `table` reads as ``block`` here, so asking would read
    ``block`` for a command that is allowed.

    The level of `key` now: its level in `table` unless that is ``ask`` or ``none``, which hold only while the
    record exists and is sound, names the attached harness, says it provides permissions and rendered the command gate,
    was rendered from this table, lists the key with the matching rule, and the harness file and the shared settings
    file now hash to the record's hashes. Anything else, and a key or level that is not known, reads as ``block``."""
    level = table.get(key) if isinstance(table, dict) else None
    if level not in levels.LEVELS:
        return levels.BLOCK
    if level not in (levels.ASK, levels.NONE):
        return level
    record = read(guarded, project_id)
    if record is None or not record["permissions"] or record["table_digest"] != digest(table):
        return levels.BLOCK
    if record["keys"].get(key) != level or record["file"] is None or record["file_hash"] is None:
        return levels.BLOCK
    if not record["gate"] or record["harness"] != _attached_harness(root):
        return levels.BLOCK
    if live_hash(root, record["file"]) != record["file_hash"]:
        return levels.BLOCK
    shared = record["shared"]
    if shared["path"] is not None and live_hash(root, shared["path"]) != shared["hash"]:
        return levels.BLOCK
    return level
