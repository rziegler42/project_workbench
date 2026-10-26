"""The keys the owner's ``levels`` table may name, the levels each offers and its default.

``docs/specs/command-permissions.md`` ("Which levels a key offers", "Shipped defaults"). The registry is built from
what the installer knows: the owner-run commands of ``rules.OWNER_RUN``, the checkpoints a process module declares
and the owner-run arguments of the installed commands. No module is named here
(``2026-10-21-module-code-lives-in-modules``). A hard stop of the compiled floor is never a key.

A level is offered by a key only from the increment that builds it for that key; until then the key offers
``block`` only. In this version ``approve-plan`` also offers ``delegated`` (``wb delegate-approve-plan`` is its
gate), and no key offers ``ask`` or ``none``. Every default is ``block``: a table can only make a key stricter or
equal to what it reads without one.
"""

import collections

from . import floor, rules

BLOCK, ASK, DELEGATED, NONE = "block", "ask", "delegated", "none"
LEVELS = (BLOCK, ASK, DELEGATED, NONE)  # strictest first
APPROVE_PLAN = "approve-plan"

Key = collections.namedtuple("Key", "name offers default")

# The levels beyond ``block`` that a key offers in this version, by key.
_OFFERS = {APPROVE_PLAN: (DELEGATED,)}
# The shipped default of a key that is not ``block``; none yet.
_DEFAULTS = {}


def strictest(*given):
    """The strictest of the given levels (``block`` strictest, ``none`` least strict)."""
    return min(given, key=LEVELS.index)


def _key(name):
    return Key(name, (BLOCK,) + _OFFERS.get(name, ()), _DEFAULTS.get(name, BLOCK))


def registry(checkpoints=(), commands=()):
    """The keys, in order, as ``{name: Key}``.

    First the process module's declared `checkpoints`, in declaration order; then one key for each owner-run
    command of ``rules.OWNER_RUN`` in the ``wb`` spelling (``approve-plan`` is the checkpoint of that name); then
    ``wb run <command> <argument>`` for each owner-run argument of `commands`, a sequence of
    ``(command name, owner-run arguments)``. A repeated key is one key, and a floor action is not a key.
    """
    names = []
    names.extend(checkpoints)
    names.extend(APPROVE_PLAN if command == APPROVE_PLAN else "wb " + command for command in rules.OWNER_RUN)
    for command, arguments in commands:
        names.extend("wb run %s %s" % (command, argument) for argument in arguments)
    ids = {stop.id for stop in floor.FLOOR}
    keys = collections.OrderedDict()
    for name in names:
        if name not in keys and name not in ids:
            keys[name] = _key(name)
    return keys
