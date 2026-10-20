"""The hard-stop floor: actions that always stop for the owner.

The floor is compiled into the installer on purpose. A file could be damaged or
edited by a hostile commit, so nothing here reads a file, and ``effective_stops`` is
the single place stops are combined. A module may add a stop; nothing may remove one,
whatever its source (a module, committed project policy, a plan, a review or a
delegate). The personal settings hold a copy of the floor for the owner to read and
for harnesses to render, but that copy is never consulted to decide what applies.

Changing the floor needs a new workbench version.
"""

import collections
import re

Stop = collections.namedtuple("Stop", "id description")

# The five entries of docs/specs/trust-and-approval.md, "Hard stops and the floor".
FLOOR = (
    Stop("force-or-rewrite-history", "force operations and rewriting history that has been pushed"),
    Stop("delete-or-overwrite-files",
         "deleting uncommitted project files, or overwriting an existing or tracked file "
         "with fetched content"),
    Stop("publish-or-deploy", "publishing or deploying"),
    Stop("touch-secrets", "anything touching secrets"),
    Stop("install-dependencies", "installing dependencies"),
)

_ID = re.compile(r"^[a-z][a-z0-9-]{0,63}\Z")
MAX_DESCRIPTION = 200


class FloorError(Exception):
    """A stop was malformed, collided with the floor, or something tried to remove one."""


def _squash(stop_id):
    # `publish-or-deploy` and `publishordeploy` are the same stop to a reader.
    return re.sub(r"[^a-z0-9]", "", stop_id.casefold())


def _checked(stop):
    # Exactly a Stop, then rebuilt from plain values: a subclass could answer one way
    # when checked and another way when shown.
    if type(stop) is not Stop:
        raise FloorError("a stop must be a Stop(id, description): %r" % (stop,))
    if not isinstance(stop.id, str) or not _ID.match(stop.id):
        raise FloorError("a stop id is lowercase kebab-case, at most 64 characters: %r"
                         % (stop.id,))
    text = stop.description
    if not isinstance(text, str) or not text or len(text) > MAX_DESCRIPTION or not text.isprintable():
        raise FloorError("a stop description is non-empty printable text of at most %d "
                         "characters (stop %r)" % (MAX_DESCRIPTION, stop.id))
    return Stop(str(stop.id), str(text))


def effective_stops(additions=(), removals=()):
    """The floor followed by the added stops, sorted by id. Never fewer than the floor.

    `removals` exists so a request to remove a stop has one place to be refused: it must
    be an empty list or tuple, and anything else raises.
    """
    if isinstance(additions, (str, bytes)):
        raise FloorError("additions must be a list of stops")
    if not isinstance(removals, (list, tuple)):
        raise FloorError("a hard stop cannot be removed or relaxed: %r" % (removals,))
    if removals:
        raise FloorError("a hard stop cannot be removed or relaxed: %s"
                         % ", ".join(repr(item) for item in removals))
    floor_keys = {_squash(stop.id) for stop in FLOOR}
    added = {}
    for stop in additions:
        stop = _checked(stop)
        if _squash(stop.id) in floor_keys:
            raise FloorError("stop %r repeats a floor entry" % stop.id)
        if added.get(stop.id, stop) != stop:
            raise FloorError("stop %r is added twice with different text" % stop.id)
        added[stop.id] = stop
    squashed = {}
    for stop in added.values():
        if squashed.setdefault(_squash(stop.id), stop.id) != stop.id:
            raise FloorError("stops %r and %r differ only in punctuation" % (squashed[_squash(stop.id)], stop.id))
    return FLOOR + tuple(added[key] for key in sorted(added))
