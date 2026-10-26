"""What the owner's levels table renders into a harness, and the record attach keeps of it.

``docs/specs/command-permissions.md``, "Rendering". At attach a harness that provides ``permissions`` gets, for each key
whose command it can match, a ``deny`` at ``block`` and at ``delegated``, an ``ask`` at ``ask`` and nothing at ``none``.
The floor's ``ask`` rules and the guarded store's deny are not touched. Attach writes, in the guarded store, a record
of what it rendered; a key reads as ``ask`` or ``none`` only while that record, the table and the harness file all
agree, and as ``block`` otherwise. ``delegated`` and ``block`` do not depend on the record.

The record: ``{"format": 1, "harness": "<module name>", "permissions": true|false, "table_digest": <sha-256>,
"file": "<path of the permissions file>" | null, "file_hash": <sha-256> | null, "keys": {<every key>: "deny" | "ask" |
"none" | "unruled"}}``. ``unruled`` is a key with no command to match (a checkpoint that is not a command): it renders
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
FORMAT = 1
LOCAL_MANIFEST = localmanifest.PATH
_SHA = re.compile(r"[0-9a-f]{64}\Z")
RULES = ("deny", "ask", "none", "unruled")

Plan = collections.namedtuple("Plan", "keys ask open")


def key_patterns(key):
    """The shell patterns that deny the command `key` names (every spelling), or ``[]`` for a key with no command."""
    if key == levels.APPROVE_PLAN:
        return rules.owner_run_command_patterns(key)
    if key.startswith("wb run "):
        parts = key.split(" ")
        if len(parts) >= 4:
            return rules.command_owner_patterns(parts[2], [" ".join(parts[3:])])
        return []
    if key.startswith("wb ") and key[3:] in rules.OWNER_RUN:
        return rules.owner_run_command_patterns(key[3:])
    return []


def plan(table):
    """The ``Plan`` for the effective `table` (key to level): the rule each key renders, the patterns to ask and the
    patterns not to deny (those at ``ask`` and ``none``)."""
    keys, ask, opened = {}, [], []
    for key in table:
        patterns = key_patterns(key)
        level = table[key]
        if not patterns:
            keys[key] = "unruled"
        elif level == levels.ASK:
            keys[key] = "ask"
            ask.extend(patterns)
            opened.extend(patterns)
        elif level == levels.NONE:
            keys[key] = "none"
            opened.extend(patterns)
        else:
            keys[key] = "deny"
    return Plan(keys, ask, opened)


def digest(table):
    """A digest of the effective table, so a record says which table it rendered."""
    text = json.dumps(dict(table), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def table_of(guarded, checkpoints, commands):
    """The effective table (key to level) for the owner's settings, the declared `checkpoints` and the installed
    `commands` (``(name, owner-run arguments)``)."""
    return dict(settings.effective(settings.load(guarded), checkpoints, (), commands).levels)


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
        [(command.name, command.owner) for item in found for command in item.module.commands])
    return table, root, ident


def record_of(harness, provides_permissions, table, built, path, file_hash):
    """The record body for a harness `harness` (``<package>/<module>``) that wrote `path` with hash `file_hash`."""
    return {"format": FORMAT, "harness": harness, "permissions": bool(provides_permissions),
            "table_digest": digest(table), "file": path, "file_hash": file_hash, "keys": dict(built.keys)}


def serialize(record):
    return (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def write(guarded, project_id, record):
    guarded.write(RECORD % project_id, serialize(record))


def _valid(record):
    if not isinstance(record, dict) or record.get("format") != FORMAT or isinstance(record.get("format"), bool):
        return False
    if not isinstance(record.get("harness"), str) or not isinstance(record.get("permissions"), bool):
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


def _live_hash(root, path):
    try:
        with safefs.Root(root, "project root") as held:
            return hashlib.sha256(held.read_file(path)).hexdigest()
    except safefs.SafeFsError:
        return None


def _attached_harness(root):
    try:
        with safefs.Root(root, "project root") as held:
            document = localmanifest.parse(held.read_file(LOCAL_MANIFEST))
    except (safefs.SafeFsError, localmanifest.LocalManifestError):
        return None
    return document["harness"]


def effective_level(guarded, project_id, root, table, key):
    """The level of `key` now: its level in `table` unless that is ``ask`` or ``none``, which hold only while the
    record exists and is sound, names the attached harness and says it provides permissions, was rendered from this
    table, lists the key with the matching rule, and the harness file now hashes to the record's hash. Anything else,
    and a key or level that is not known, reads as ``block``."""
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
    if record["harness"] != _attached_harness(root):
        return levels.BLOCK
    if _live_hash(root, record["file"]) != record["file_hash"]:
        return levels.BLOCK
    return level
