"""The keys the owner's ``levels`` table may name, the levels each offers and its default.

``docs/specs/command-permissions.md`` ("Which levels a key offers", "Shipped defaults"). The registry is built from
what the installer knows: the owner-run commands of ``rules.OWNER_RUN``, the checkpoints a process module declares,
the agent-safe actions and the arguments of the installed commands. No module is named here
(``2026-10-21-module-code-lives-in-modules``). A hard stop of the compiled floor is never a key.

A level is offered by a key only from the increment that builds it for that key; until then the key offers
``block`` only. In this version ``approve-plan`` also offers ``delegated`` (``wb delegate-approve-plan`` is its
gate), ``ask`` (a digest of its preview) and ``none``; ``wb release-approvals`` offers ``ask`` (a digest of the preview of its
release, ``2026-10-30-release-approvals-at-ask``) and ``none``; no other key offers ``ask`` unless an installed command's
declaration gives its owner-run argument ``levels`` (``declarations.ARGUMENT_LEVELS``) and ``checkpoint_of`` maps that
argument to the key (then the checkpoint offers the levels the argument does; ``checkpoint_commands``), and ``none`` is offered by the owner-run
installer commands, ``accept-decision`` and the keys of ``_OFFERS``. An agent-safe key and a declared argument that is not
owner-run offer ``none`` and default to it; every other default is
``block``: the shipped default of ``approve-plan`` becomes ``ask`` only after the probe the decision
``2026-10-26-ask-level-spelling-limit`` requires is recorded.
"""

import collections

from . import floor, rules

BLOCK, ASK, DELEGATED, NONE = "block", "ask", "delegated", "none"
LEVELS = (BLOCK, ASK, DELEGATED, NONE)  # strictest first
APPROVE_PLAN = "approve-plan"

Key = collections.namedtuple("Key", "name offers default agent", defaults=(False,))

# Owner-run commands whose levels the declared checkpoints set, so the command spelling is not a key of its own: a
# checkpointed action uses its checkpoint's name (the first and second tier of ``acknowledge``).
CHECKPOINTED_COMMANDS = ("acknowledge",)
# The checkpoint whose level governs a command that is not a key of its own. ``wb acknowledge`` lists only paths that have a
# baseline (the manifest, the files under ``.workbench/``, ``AGENTS.md``, seeded files), which are first-tier material, so the
# first-tier checkpoint is its key (the owner's choice, ``docs/specs/command-permissions.md``, "One way to run at ``none``").
CHECKPOINT_ACKNOWLEDGE = "acknowledge-first-tier"
COMMAND_OF_CHECKPOINT = {CHECKPOINT_ACKNOWLEDGE: "acknowledge"}


class RegistryError(ValueError):
    """Two declarations give one key, so a level could not say which of them it sets."""

# The levels beyond ``block`` that a key offers in this version, by key.
_OFFERS = {APPROVE_PLAN: (DELEGATED, ASK, NONE), "wb install": (NONE,), "wb adopt": (NONE,), "wb upgrade": (NONE,),
           "wb add": (NONE,), "wb approve": (NONE,), "wb pin": (NONE,),
           "acknowledge-first-tier": (NONE,), "acknowledge-second-tier": (NONE,), "wb recover": (NONE,),
           "wb attach": (NONE,), "wb release-approvals": (ASK, NONE), "accept-decision": (NONE,)}
# The shipped default of a key that is not ``block``; none yet among the owner-run keys.
_DEFAULTS = {}
# An agent-safe action, and a declared module argument that is not owner-run, is one an agent may run today, so it
# defaults to ``none`` (``docs/specs/command-permissions.md``, "A level for every command"). Until the
# increment that renders a ``deny`` for it, a ``block`` here is read and reported but is not enforced.
_AGENT_OFFERS = (NONE,)


def strictest(*given):
    """The strictest of the given levels (``block`` strictest, ``none`` least strict)."""
    return min(given, key=LEVELS.index)


def _key(name, agent=False, declared=()):
    """The key `name`. `declared` is the levels, beyond ``block``, that a command's declaration gives an owner-run
    argument (``declarations.ARGUMENT_LEVELS``); a key is offered them after the levels of ``_OFFERS``."""
    if agent:
        return Key(name, (BLOCK,) + _AGENT_OFFERS, NONE, True)
    fixed = _OFFERS.get(name, ())
    extra = tuple(level for level in (ASK, NONE) if level in declared and level not in fixed)
    offers = tuple(sorted(fixed + extra, key=LEVELS.index)) if extra and fixed else fixed + extra
    return Key(name, (BLOCK,) + offers, _DEFAULTS.get(name, BLOCK))


def checkpoint_commands(checkpoints, commands):
    """``{checkpoint: "wb run <command> <argument>"}`` for each ``checkpoint_of`` mapping of `commands` that applies: the
    checkpoint is one of the process module's declared `checkpoints`, and the argument is owner-run and offers a level.
    A mapping to a checkpoint nobody declares does not apply, and its argument keeps its own key. ``RegistryError`` when two
    arguments claim one declared checkpoint. `commands` are the entries ``registry`` takes; the mapping is their fifth item,
    ``((argument, checkpoint), ...)`` (``2026-10-29-accept-decision-at-ask``)."""
    declared = set(checkpoints)
    found = {}
    for entry in commands:
        owner = entry[1]
        leveled = {argument for argument, wanted in (entry[3] if len(entry) > 3 else ()) if wanted}
        for argument, checkpoint in (entry[4] if len(entry) > 4 else ()):
            if checkpoint in declared and argument in owner and argument in leveled:
                key = "wb run %s %s" % (entry[0], argument)
                if checkpoint in found and found[checkpoint] != key:
                    raise RegistryError("more than one declaration gives the key %s" % checkpoint)
                found[checkpoint] = key
    return found


def agent_keys():
    """The keys of the agent-safe actions, in the ``wb`` spelling, in the order of ``rules.AGENT_SAFE``.

    A hook entry point, a word that only dispatches (``preview`` and ``run``; each action beneath ``preview`` has a key,
    and a module's arguments have theirs) and an action that reaches another action's key
    (``delegate-approve-plan``) are not keys, so no action reaches two keys and a parent cannot tighten or bypass an
    action beneath it."""
    names = []
    for command in rules.AGENT_SAFE:
        if command in rules.HOOK_ENTRY_POINTS or command in rules.REACHES_ANOTHER_KEY:
            continue
        if command == "preview":
            names.extend("wb preview " + action for action in rules.PREVIEW_ACTIONS)
        elif command not in rules.DISPATCHERS:
            names.append("wb " + command)
    return tuple(names)


def registry(checkpoints=(), commands=(), agent=True):
    """The keys, in order, as ``{name: Key}``.

    First the process module's declared `checkpoints`, in declaration order; then one key for each owner-run
    command of ``rules.OWNER_RUN`` in the ``wb`` spelling (``approve-plan`` is the checkpoint of that name); then,
    with `agent` true, one for each agent-safe action (``agent_keys``); then ``wb run <command> <argument>`` for each
    declared argument of `commands`, a sequence of ``(command name, owner-run arguments)``,
    ``(command name, owner-run arguments, all declared arguments)`` or that with a fourth item, the command's ``levels``
    as ``((argument, (level, ...)), ...)``, and a fifth, its ``checkpoint_of`` as ``((argument, checkpoint), ...)`` (an
    argument so mapped to one of `checkpoints` has that checkpoint as its key and no key of its own, see
    ``checkpoint_commands``): an owner-run argument defaults to ``block`` and any
    other declared argument to ``none`` (with `agent` false the keys of the arguments that are not owner-run are left out
    with those of the agent-safe actions). Two declarations of one key are refused (``RegistryError``). A repeated
    checkpoint is one key, and a floor action is not a key.
    """
    names = []
    names.extend((name, False) for name in checkpoints)
    names.extend((APPROVE_PLAN if command == APPROVE_PLAN else "wb " + command, False) for command in rules.OWNER_RUN
                 if command not in CHECKPOINTED_COMMANDS)
    if agent:
        names.extend((name, True) for name in agent_keys())
    declared, declared_offers = [], {}
    own = {key: checkpoint for checkpoint, key in checkpoint_commands(checkpoints, commands).items()}
    for entry in commands:
        command, owner = entry[0], entry[1]
        arguments = entry[2] if len(entry) > 2 else ()
        declared.extend(("wb run %s %s" % (command, argument), False) for argument in owner
                        if "wb run %s %s" % (command, argument) not in own)
        for argument, wanted in (entry[3] if len(entry) > 3 else ()):
            if argument in owner:
                key = "wb run %s %s" % (command, argument)
                declared_offers[own.get(key, key)] = tuple(wanted)
        if agent:
            declared.extend(("wb run %s %s" % (command, argument), True) for argument in arguments
                            if argument not in owner)
    counted = [name for name, _ in declared]
    repeated = sorted({name for name in counted if counted.count(name) > 1})
    if repeated:
        raise RegistryError("more than one declaration gives the key %s" % repeated[0])
    names.extend(declared)
    ids = {stop.id for stop in floor.FLOOR}
    keys = collections.OrderedDict()
    for name, agent_safe in names:
        if name not in keys and name not in ids:
            keys[name] = _key(name, agent_safe, declared_offers.get(name, ()))
    return keys
