"""The owner's personal settings, kept in the guarded store as the file ``settings``.

The document is strict JSON::

    {"checkpoints": {"<name>": "stop" | "delegate"}, "floor": ["<id>", ...], "version": 1}

* ``checkpoints`` names the checkpoints the owner has set. A checkpoint that is missing,
  malformed or set to anything but ``delegate`` reads as ``stop``, so with no settings
  every checkpoint stops. Checkpoint names are defined by a way of working, not here.
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

from . import declarations, floor, safefs

SETTINGS = "settings"
VERSION = 1
STOP, DELEGATE = "stop", "delegate"

_Settings = collections.namedtuple("_Settings", "checkpoints problems")


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
    return Settings({}, [problem])


def load(store):
    """Read the settings. Never raises for a bad file: the problems are returned."""
    try:
        kind = store.kind(SETTINGS)
        if kind is None:
            return Settings({}, [])
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
        if key not in ("checkpoints", "floor", "version"):
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
    return Settings(checkpoints, problems)


def initialize(store):
    """Seed the settings if missing, then load them. Returns the loaded settings."""
    seed(store)
    return load(store)
