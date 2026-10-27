"""The owner's personal settings, kept in the guarded store as the file ``settings``.

The document is strict JSON::

    {"caps": {"<name>": <integer>}, "checkpoints": {"<name>": "stop" | "delegate"},
     "floor": ["<id>", ...], "levels": {"<key>": "block" | "ask" | "delegated" | "none"},
     "version": 1 | 2}

``levels`` exists only in version 2 (``docs/specs/command-permissions.md``). The reader accepts versions 1 and 2.

* ``checkpoints`` names the checkpoints the owner has set. A checkpoint that is missing,
  malformed or set to anything but ``delegate`` reads as ``stop``, so with no settings
  every checkpoint stops. Checkpoint names are defined by a way of working, not here.
* ``levels`` is optional. It maps a key to the level the owner chose. A value that is not one of the four levels,
  a key that is not valid, or a ``levels`` that is not an object reads as ``block``. In this version a key is a
  checkpoint the process module declares; ``stop`` reads as ``block`` and ``delegate`` as ``delegated``, a key set
  in both takes the table entry, and a checkpoint is only a fallback for a key the table does not name. ``delegated``, ``ask`` and ``none`` are offered by ``approve-plan``; ``none`` is also offered
  by an agent-safe action and a declared module argument that is not owner-run (``levels``); any other key reads a level
  it does not offer as ``block`` with a note.
* ``caps`` is optional. It holds the owner's value for each loop cap a process module declares.
  The loader keeps a valid name with an integer value; ``effective`` judges the value against
  the module's ceiling and falls back to the module's default with a note.
* ``floor`` is a copy of the compiled floor's ids, written at seeding so the owner and a
  harness can read it. It is informational: nothing reads it to decide what applies,
  and deleting or emptying it changes nothing (see ``floor.py``).

A missing file is seeded. A damaged file is never overwritten: it is reported and every
checkpoint behaves as ``stop`` until the owner repairs it.

Limit, accepted on purpose: between the check that the file is absent and the atomic write
of the seed, a file created in that moment is replaced. Only the owner's own account can
create it, and the loss is a hand edit made in the same instant.
"""

import collections
import json
import re

from . import declarations, floor, levels as keyset
from .wbkit import safefs

SETTINGS = "settings"
VERSION = 1  # the version written at seeding
VERSIONS = (1, 2)  # the versions the reader accepts
STOP, DELEGATE = "stop", "delegate"
BLOCK, ASK, DELEGATED, NONE = keyset.BLOCK, keyset.ASK, keyset.DELEGATED, keyset.NONE
LEVELS = keyset.LEVELS  # strictest first
# A key is a checkpoint name or a command in the ``wb`` spelling, for example ``wb install``.
_KEY_RE = re.compile(r"[a-z][a-z0-9-]*( [a-z][a-z0-9-]*)*\Z")
MAX_KEY = 96
_FLOOR_IDS = frozenset(stop.id for stop in floor.FLOOR)
# The one checkpoint for which ``delegate`` has an effect (``wb delegate-approve-plan``); any other name stops.
APPROVE_PLAN = keyset.APPROVE_PLAN

_Settings = collections.namedtuple("_Settings", "checkpoints problems caps levels levels_blocked")
Effective = collections.namedtuple("Effective", "checkpoints caps notes levels translated", defaults=((),))


strictest = keyset.strictest


class Settings(_Settings):
    def checkpoint(self, name):
        """"delegate" only when the owner set exactly that; otherwise "stop"."""
        if not isinstance(name, str):
            return STOP
        return DELEGATE if self.checkpoints.get(name) == DELEGATE else STOP


def _seed_document():
    return {"checkpoints": {}, "floor": [stop.id for stop in floor.FLOOR], "version": VERSION}


def seed(store):
    """Write the settings if there is nothing at their path. True when written."""
    if store.kind(SETTINGS) is not None:
        return False
    text = json.dumps(_seed_document(), sort_keys=True, indent=2) + "\n"
    store.write(SETTINGS, text.encode("utf-8"))
    return True


def _default(problem):
    return Settings({}, [problem], {}, {}, True)


def load(store):
    """Read the settings. Never raises for a bad file: the problems are returned."""
    try:
        kind = store.kind(SETTINGS)
        if kind is None:
            return Settings({}, [], {}, {}, False)
        if kind != "file":
            return _default("settings are not a regular file (%s); every checkpoint stops" % kind)
        data = store.read(SETTINGS)
    except safefs.SafeFsError as exc:
        return _default("settings cannot be read (%s); every checkpoint stops" % exc)
    try:
        document = declarations.parse_json(data)
    except ValueError as exc:
        return _default("settings are damaged (%s); every checkpoint stops" % exc)

    problems = []
    version = document.get("version")
    if isinstance(version, bool) or version not in VERSIONS:
        return _default("settings have an unsupported version; every checkpoint stops")
    known = ("caps", "checkpoints", "floor", "version") + (("levels",) if version == 2 else ())
    for key in sorted(document):
        if key not in known:
            problems.append("settings have an unknown entry %s, which is ignored"
                            % declarations._shown(key))
    checkpoints = {}
    given = document.get("checkpoints", {})
    if not isinstance(given, dict):
        problems.append("settings 'checkpoints' is not an object; every checkpoint stops")
        given = {}
    for name in sorted(given):
        value = given[name]
        if not declarations.NAME_RE.match(name) or len(name) > 64:
            problems.append("settings name a checkpoint that is not valid: %s"
                            % declarations._shown(name))
        elif value not in (STOP, DELEGATE) or not isinstance(value, str):
            problems.append("settings checkpoint %r must be 'stop' or 'delegate'; it stops" % name)
        else:
            checkpoints[name] = value
    caps = {}
    given = document.get("caps", {})
    if not isinstance(given, dict):
        problems.append("settings 'caps' is not an object; every cap uses its default")
        given = {}
    for name in sorted(given):
        value = given[name]
        if not declarations.NAME_RE.match(name) or len(name) > 64:
            problems.append("settings name a cap that is not valid: %s" % declarations._shown(name))
        elif type(value) is not int:
            problems.append("settings cap %s must be an integer; its default applies" % name)
        else:
            caps[name] = value
    levels, levels_blocked = {}, False
    if "levels" in document and version == 2:
        given = document["levels"]
        if not isinstance(given, dict):
            problems.append("settings 'levels' is not an object; every key reads as block")
            levels_blocked = True
            given = {}
        for key in sorted(given):
            value = given[key]
            if len(key) > MAX_KEY or not _KEY_RE.match(key):
                problems.append("settings name a level key that is not valid: %s; every key reads as block"
                                % declarations._shown(key))
                levels_blocked = True
            elif key in _FLOOR_IDS:
                problems.append("settings name a floor action, %s, which the table cannot set; it is refused"
                                % declarations._shown(key))
            elif not isinstance(value, str) or value not in LEVELS:
                problems.append("settings level for %s must be one of %s; it reads as block"
                                % (declarations._shown(key), ", ".join(LEVELS)))
                levels[key] = BLOCK
            else:
                levels[key] = value
    return Settings(checkpoints, problems, caps, levels, levels_blocked)


def effective(loaded, checkpoints, caps, commands=(), agent=True):
    """The values that apply to a process module that declares ``checkpoints`` (names) and ``caps``.

    A checkpoint is ``delegate`` only when declared, set to exactly that and named ``approve-plan``: delegation
    takes effect for no other checkpoint, which stops with a note. A cap is the owner's
    value when it is an integer from 1 to the ceiling, otherwise the default. Each ignored or
    replaced entry adds a note; the loader's own problems are not repeated here.

    ``levels`` holds a level for every key of ``levels.registry(checkpoints, commands)``, where `commands` is a
    sequence of ``(command name, owner-run arguments)`` or ``(command name, owner-run arguments, all declared
    arguments)`` of the installed commands; with `agent` false the keys of the agent-safe actions are left out (the table
    a harness renders holds none until one is rendered). A key's level is its table entry,
    else its checkpoint reading, else its default; an entry for a level the key does not offer reads as ``block`` with
    a note, and an entry for a key that is not in the registry is noted and ignored.
    """
    notes = []
    declared = set(checkpoints)
    for name in sorted(loaded.checkpoints):
        if name not in declared:
            notes.append("settings set a checkpoint the process module does not declare: %s; it is ignored"
                         % declarations._shown(name))
    values = {}
    for name in checkpoints:
        values[name] = loaded.checkpoint(name)
        if values[name] == DELEGATE and name != APPROVE_PLAN:
            values[name] = STOP
            notes.append("settings set the checkpoint %s to delegate; delegation has no effect for it, so it stops"
                         % declarations._shown(name))
    keys = keyset.registry(checkpoints, commands, agent)
    levels, translated = {}, []
    for name, key in keys.items():
        levels[name] = _level(loaded, key, values, notes, translated)
        if name in values:
            values[name] = DELEGATE if levels[name] == DELEGATED else STOP
    for name in sorted(loaded.levels):
        if name not in keys:
            notes.append("settings set a level for a key this version does not know: %s; it is ignored"
                         % declarations._shown(name))
    known = {cap.name for cap in caps}
    for name in sorted(loaded.caps):
        if name not in known:
            notes.append("settings set a cap the process module does not declare: %s; it is ignored"
                         % declarations._shown(name))
    numbers = {}
    for cap in caps:
        given = loaded.caps.get(cap.name)
        if given is None:
            numbers[cap.name] = cap.default
        elif 1 <= given <= cap.ceiling:
            numbers[cap.name] = given
        else:
            numbers[cap.name] = cap.default
            notes.append("settings cap %s is %s; it must be from 1 to %d, so the default %d applies"
                         % (cap.name, given if abs(given) < 10 ** 12 else "out of range", cap.ceiling, cap.default))
    return Effective(values, numbers, notes, levels, tuple(translated))


def _level(loaded, key, checkpoint_values, notes, translated):
    """The level of the registry `key`: its table entry if it has one, else its checkpoint reading, else its default.

    The table is the single source of a level (``docs/specs/command-permissions.md``): an entry wins in either direction,
    whatever the key's checkpoint says. A checkpoint set in a version 1 file is only a fallback for a key the table does
    not name, and its word is read as a level, ``stop`` as block and ``delegate`` as delegated; the reading is added to
    `translated` as ``(key, word, level)``, which ``wb settings`` prints, and is not a note because it is not a problem.
    A level the key does not offer reads as block with a note. A damaged file or table reads every key as block except the
    keys of what an agent may run today (``key.agent``), which keep their default: the agent must still be able to run
    ``wb settings`` and ``wb check`` to report the damage (the owner's decision for increment C of the plan).
    """
    name = key.name
    if key.agent and loaded.levels_blocked:
        return key.default
    reading = None
    if name in loaded.checkpoints and name in checkpoint_values:
        reading = DELEGATED if checkpoint_values[name] == DELEGATE else BLOCK
    entry = BLOCK if loaded.levels_blocked else loaded.levels.get(name)
    if entry is not None:
        if entry not in key.offers:
            notes.append("settings set the level of %s to %s; that level is not offered for it in this version, "
                         "so it reads as block" % (declarations._shown(name), entry))
            entry = BLOCK
        if reading is not None and reading != entry:
            notes.append("settings give %s the checkpoint reading %s and the level %s; the level applies"
                         % (declarations._shown(name), reading, entry))
        return entry
    if reading is not None:
        word = loaded.checkpoints[name]
        if not (word == DELEGATE and reading == BLOCK):  # a delegate that cannot take effect has its own note
            translated.append((name, word, reading))
        return reading
    return key.default


def initialize(store):
    """Seed the settings if missing, then load them. Returns the loaded settings."""
    seed(store)
    return load(store)
