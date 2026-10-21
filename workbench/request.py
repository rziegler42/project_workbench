"""The approval request: what the owner is shown before approving a package or a module.

``docs/specs/trust-and-approval.md`` asks for the declaration "in plain terms": the type,
what the module provides, requires and blocks, the paths it writes, every hook or
executable it ships, and the helpers it expects. This module builds that text and nothing
else; it approves nothing and writes nothing.

Rules this text follows, because the owner decides from it and a package wrote its content:

* Nothing a package controls is shortened. A path, a layout value or a list is shown in
  full, one item to a line, so the end of a long value or the tail of a long list is never
  hidden. Large lists are announced by count first.
* The identity of the thing, its risk flags, its size counts and both hashes come first.
  The long details follow, so a long list cannot push them out of sight.
* Every package-supplied string is shown as ASCII: a character outside printable ASCII
  appears as an escape such as ``\\u0443``, so a lookalike letter cannot pass for a Latin
  one, and control, invisible and bidirectional characters cannot steer the terminal.
* A module of type ``harness`` or ``process``, or one that blocks a core capability (an
  unprefixed name), is flagged high risk at the top of its entry. A harness or process
  module also always needs an explicit approval of its own, and a package request marks it.
* A command the module offers is listed with its helper, how it starts and the first arguments it
  allows. The pin, not this text, decides what runs.
* The text is built from a declaration that has already been verified and the hashes the
  verifier computed, and the files with the owner execute bit come from the same tree walk
  that was hashed (``Verified.executable``). Nothing here reads a file.
"""

import json

from .wbkit import display

NEEDS_OWN_APPROVAL = ("harness", "process")
INLINE_LIMIT = 6        # more entries than this get a header with a count and one line each
NAMES_IN_REASON = 5     # more core blocks than this are summarised by count in the risk line
MAX_NESTING = 40


def _shown(value):
    return display.ascii_text(value)


def _version(version):
    # The parsed form is a tuple of integers; anything else is shown as given.
    if isinstance(version, (tuple, list)) and all(
            isinstance(n, int) and not isinstance(n, bool) for n in version):
        try:
            return ".".join(str(n) for n in version)
        except ValueError:
            return "<a number too large to show>"
    return _shown(version)


def is_core(capability):
    """A core capability is an unprefixed name; third-party names are ``<package>:<name>``."""
    return ":" not in capability


def high_risk(module):
    """The reasons a module is high risk, as a list; empty when it is not."""
    reasons = []
    if module.type in NEEDS_OWN_APPROVAL:
        reasons.append("it is a %s module, which always needs an explicit approval of its own"
                       % _shown(module.type))
    core = [cap for cap in module.blocks if is_core(cap)]
    if len(core) > NAMES_IN_REASON:
        reasons.append("it blocks %d core capabilities (listed under blocks)" % len(core))
    elif core:
        reasons.append("it blocks core capability %s" % ", ".join(_shown(c) for c in core))
    return reasons


def _under(rel, item):
    return rel == item or rel.startswith(item + "/")


def _section(label, values):
    """A short list on one line; a long one as a counted header and one line per entry."""
    values = list(values)
    if not values:
        return ["  %s: none" % label]
    if len(values) <= INLINE_LIMIT:
        return ["  %s: %s" % (label, ", ".join(values))]
    return ["  %s (%d):" % (label, len(values))] + ["    " + value for value in values]


def _command(command):
    """One declared command: its name, helper, how it starts and which first arguments it allows."""
    how = "python, kit %d" % command.kit if command.runtime == "python" else _shown(command.runtime)
    allowed = ("first argument one of %s" % ", ".join(_shown(a) for a in command.arguments)
               if command.arguments else "takes no argument")
    return "%s runs %s as %s; %s" % (_shown(command.name), _shown(command.helper), how, allowed)


def _check(check):
    """One declared check: its helper, the kit API it runs through and the pin name it needs."""
    return "%s runs through kit API %d; the owner pins it as %s" % (
        _shown(check.helper), check.kit, _shown(check.pin_name))


def _leaves(value, prefix, out, depth=0):
    if depth > MAX_NESTING:
        out.append("%s = <nested too deeply to show>" % prefix)
    elif isinstance(value, dict):
        if not value:
            out.append("%s = {}" % prefix)
        for key in sorted(value, key=str):
            _leaves(value[key], "%s.%s" % (prefix, _shown(key)) if prefix else _shown(key),
                    out, depth + 1)
    elif isinstance(value, (list, tuple)):
        if not value:
            out.append("%s = []" % prefix)
        for index, item in enumerate(value):
            _leaves(item, "%s[%d]" % (prefix, index), out, depth + 1)
    else:
        try:
            text = json.dumps(value, sort_keys=True)
        except (ValueError, TypeError):
            text = "<a value that cannot be shown>"
        out.append("%s = %s" % (prefix, _shown(text)))


def _layout_lines(layout):
    out = []
    _leaves(layout, "", out)
    return ["    " + line.lstrip(".") for line in out]


def render_module(package, module, hashes, source=None, executable=()):
    """The request for one module. `hashes` has ``declaration_hash`` and ``tree_hash``.

    `executable` is the set of the module's executable files, ``Verified.executable``.
    """
    executable = set(executable)
    in_ships = {rel for rel in executable if any(_under(rel, item) for item in module.ships)}
    other = sorted(executable - in_ships)
    lines = []
    risks = high_risk(module)
    if risks:
        lines.append("HIGH RISK: " + "; ".join(risks))
    lines.append("module %s/%s %s" % (_shown(package), _shown(module.name), _version(module.version)))
    lines.append("  type: %s" % _shown(module.type))
    if module.type in NEEDS_OWN_APPROVAL:
        lines.append("  approval: needs an explicit approval of its own")
    lines.append("  description: %s" % _shown(module.description))
    if source:
        lines.append("  from: %s" % _shown(source))
    lines.append("  declaration hash: %s" % _shown(hashes.declaration_hash))
    lines.append("  tree hash:        %s" % _shown(hashes.tree_hash))
    leaf_count = len(_layout_lines(module.layout)) if module.layout is not None else 0
    lines.append("  size: provides %d, requires %d, blocks %d, slots %d, fills %d, writes %d, "
                 "ships %d, other executables %d, helpers %d, layout entries %d" % (
                     len(module.provides), len(module.requires), len(module.blocks),
                     len(module.slots), len(module.fills), len(module.writes),
                     len(module.ships), len(other), len(module.helpers), leaf_count))
    lines.extend(_section("provides", [_shown(c) for c in module.provides]))
    lines.extend(_section("requires", [
        "%s (soft)" % _shown(cap) if soft else _shown(cap) for cap, soft in module.requires]))
    lines.extend(_section("blocks", [
        "%s (core capability)" % _shown(cap) if is_core(cap) else _shown(cap)
        for cap in module.blocks]))
    lines.extend(_section("slots it owns", [_shown(s) for s in module.slots]))
    lines.extend(_section("slots it fills", [
        "%s from %s" % (_shown(slot), _shown(src)) for slot, src in module.fills]))
    lines.extend(_section("writes into the project", [_shown(p) for p in module.writes]))
    ships = []
    for item in module.ships:
        kind = "executable" if any(_under(rel, item) for rel in in_ships) else "code-bearing"
        ships.append("[%s] %s" % (kind, _shown(item)))
    lines.extend(_section("ships code or executables", ships))
    lines.extend(_section("commands it offers", [_command(c) for c in module.commands]))
    lines.extend(_section("checks it offers (run by wb check)", [_check(c) for c in module.checks]))
    lines.extend(_section("other executable files in the module (installed via files/ or "
                          "harness/)", [_shown(rel) for rel in other]))
    lines.extend(_section("helpers it expects on PATH", [_shown(h) for h in module.helpers]))
    if module.layout is not None:
        lines.append("  harness layout:")
        lines.extend(_layout_lines(module.layout))
    return "\n".join(lines)


def render_package(name, version, package_hashes, entries, source=None):
    """The request for a package and all of its modules.

    `entries` is a list of ``(module, hashes, executable)`` where `hashes` is the module's
    verified record and `executable` is its ``Verified.executable`` as a set.
    """
    needing = [_shown(m.name) for m, _, _ in entries if m.type in NEEDS_OWN_APPROVAL]
    flagged = [_shown(m.name) for m, _, _ in entries if high_risk(m)]
    lines = ["package %s %s" % (_shown(name), _version(version))]
    if source:
        lines.append("  from: %s" % _shown(source))
    lines.append("  declaration hash: %s" % _shown(package_hashes.declaration_hash))
    lines.append("  tree hash:        %s" % _shown(package_hashes.tree_hash))
    lines.append("  modules: %d" % len(entries))
    lines.extend(_section("needing an explicit approval of their own", needing))
    lines.extend(_section("high risk", flagged))
    lines.append("  Approving this package approves exactly these modules with these hashes.")
    for module, hashes, executable in entries:
        lines.append("")
        lines.append(render_module(name, module, hashes, None, executable))
    return "\n".join(lines)
