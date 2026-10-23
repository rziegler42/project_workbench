"""The owner's personal settings, kept in the guarded store as the file ``settings``.

The document is strict JSON::

    {"caps": {"<name>": <integer>}, "checkpoints": {"<name>": "stop" | "delegate"},
     "floor": ["<id>", ...], "version": 1}

* ``checkpoints`` names the checkpoints the owner has set. A checkpoint that is missing,
  malformed or set to anything but ``delegate`` reads as ``stop``, so with no settings
  every checkpoint stops. Checkpoint names are defined by a way of working, not here.
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

from . import declarations, floor
from .wbkit import safefs

SETTINGS = "settings"
VERSION = 1
STOP, DELEGATE = "stop", "delegate"
# The one checkpoint for which ``delegate`` has an effect (``wb delegate-approve-plan``); any other name stops.
APPROVE_PLAN = "approve-plan"

_Settings = collections.namedtuple("_Settings", "checkpoints problems caps")
Effective = collections.namedtuple("Effective", "checkpoints caps notes")


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
    return Settings({}, [problem], {})


def load(store):
    """Read the settings. Never raises for a bad file: the problems are returned."""
    try:
        kind = store.kind(SETTINGS)
        if kind is None:
            return Settings({}, [], {})
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
    if document.get("version") != VERSION or isinstance(document.get("version"), bool):
        return _default("settings have an unsupported version; every checkpoint stops")
    for key in sorted(document):
        if key not in ("caps", "checkpoints", "floor", "version"):
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
    return Settings(checkpoints, problems, caps)


def effective(loaded, checkpoints, caps):
    """The values that apply to a process module that declares ``checkpoints`` (names) and ``caps``.

    A checkpoint is ``delegate`` only when declared, set to exactly that and named ``approve-plan``: delegation
    takes effect for no other checkpoint, which stops with a note. A cap is the owner's
    value when it is an integer from 1 to the ceiling, otherwise the default. Each ignored or
    replaced entry adds a note; the loader's own problems are not repeated here.
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
    return Effective(values, numbers, notes)


def initialize(store):
    """Seed the settings if missing, then load them. Returns the loaded settings."""
    seed(store)
    return load(store)
