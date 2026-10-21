"""Verify packages and a selection of their modules, all or nothing.

``verify_packages`` runs the per-module checks (declaration, files, hashes) on every
module of every package given. When a selection is given and nothing was refused,
it then runs the set checks on the selected modules only: type counts, requirements,
conflicts and cycles, and it works out the install order. With no selection only the
per-module checks run. If any step fails for any module the whole result is refused,
and it then carries no hashes and no order. Nothing here writes.

A selected module is named ``<module>``, or ``<package>/<module>`` when two given
packages hold a module of the same name.

Rules applied to the selection (``module-contract``):

* at most one ``harness`` and one ``process`` module; exactly one harness when
  `harness_required` (the default);
* a ``requires`` entry is hard unless marked soft. A requirement for a harness
  capability, and a slot fill, are always soft. A hard requirement with no provider
  among the selected modules is a problem naming the unselected modules that could
  supply it; a soft one is a warning. A module is never its own provider;
* a module's ``blocks`` conflicts with any other selected module that provides the
  capability, whichever is listed first; a module never conflicts with itself;
* ``slots`` are provided as ``slot:<name>``, and a slot has one owner among the
  selected modules. The base owns ``policy`` and ``docs-index``: they are always present, a
  fill or requirement of either is met, and a module that owns either is refused;
* a helper not found on ``PATH`` is a warning. Looking it up does not run it.

Install order is the selected harness module, then the process module, then the rest.
Within a group a module follows the modules of that group it requires (a slot fill
counts as a requirement). An edge to a module in another group does not affect the
order and is not an error. A cycle through any modules is a problem and names the
cycle.
"""

import collections
import shutil

from . import base, declarations, hashing, modulefiles
from .wbkit import safefs

# `module` is the parsed Module the hashes were taken for, and `executable` the module's files
# with the owner execute bit, from the same walk that produced the tree hash. A caller that
# shows a person what is being approved renders from these, not from a fresh read.
Verified = collections.namedtuple(
    "Verified", "package name version declaration_hash tree_hash type module executable")
# The hashes of a whole package, taken for the approval gate, and whether it was given as
# first-party.
PackageInfo = collections.namedtuple("PackageInfo",
                                     "name declaration_hash tree_hash first_party package")
Result = collections.namedtuple("Result", "accepted problems warnings modules order packages")


def verify_package(path, select=None, harness_required=True, first_party=False,
                   which=shutil.which):
    """Verify one package; `first_party` says whether it may provide unprefixed names."""
    return verify_packages([path], select, harness_required,
                           [path] if first_party else (), which)


def verify_packages(paths, select=None, harness_required=True, first_party=(),
                    which=shutil.which):
    """Verify the packages at `paths`; return a ``Result``.

    `select` is None (per-module checks only) or a list of module names.
    `first_party` lists the paths, as given, of packages that may provide unprefixed
    capability names; by default none do. `which` finds a helper on ``PATH``.
    """
    if not paths or isinstance(paths, str):
        raise ValueError("paths must be a non-empty list of package paths")
    if select is not None and (isinstance(select, str)
                               or not all(isinstance(name, str) for name in select)):
        raise ValueError("select must be a list of module names")
    problems = []
    warnings = []
    verified = []
    infos = []
    modules = {}
    declared = {}
    first = set(first_party)

    for path in paths:
        loaded = declarations.load_package(path, path in first)
        problems.extend(loaded.problems)
        package = loaded.package
        if package is None:
            continue
        if package.name in declared:
            problems.append(declarations.DeclarationError(
                "package", package.name, "name", "two of the given packages are named %r"
                % package.name))
            continue
        declared[package.name] = package.modules
        try:
            infos.append(PackageInfo(package.name, hashing.declaration_hash(package.declaration),
                                     hashing.tree_hash(path, what="package"), path in first, package))
        except (safefs.SafeFsError, OSError) as exc:
            problems.append(declarations.DeclarationError("package", package.name, "hash", str(exc)))
        for module in loaded.modules:
            result = modulefiles.verify_module(path, package.name, module)
            problems.extend(result.problems)
            warnings.extend("module '%s' (package '%s'): %s" % (module.name, package.name, text)
                            for text in result.warnings)
            if not result.problems:
                modules[(package.name, module.name)] = module
                verified.append(Verified(package.name, module.name, module.declaration["version"],
                                         result.declaration_hash, result.tree_hash, module.type, module,
                                         tuple(result.executable)))

    order = ()
    if select is not None:
        selected = _resolve(select, declared, problems)
        if problems:
            warnings.append("selection checks were not made because of the problems above")
        else:
            order = _check_set(selected, modules, harness_required, which, problems, warnings)

    if problems:
        return Result(False, problems, warnings, (), (), ())
    return Result(True, problems, warnings, tuple(verified), tuple(order), tuple(infos))


def _resolve(select, declared, problems):
    selected = []
    for name in select:
        if "/" in name:
            package, _, module = name.partition("/")
            found = [(package, module)] if module in declared.get(package, ()) else []
        else:
            found = [(package, name) for package in sorted(declared) if name in declared[package]]
        if not found:
            problems.append(declarations.DeclarationError(
                "selection", repr(name)[1:-1], "select",
                "no module %r in the given packages" % (name,)))
        elif len(found) > 1:
            problems.append(declarations.DeclarationError(
                "selection", repr(name)[1:-1], "select", "%r is ambiguous: use one of %s"
                % (name, ", ".join("%s/%s" % key for key in found))))
        elif found[0] not in selected:
            selected.append(found[0])
    return selected


_BASE_CAPABILITIES = frozenset("slot:" + slot for slot in base.BASE_SLOTS)


def _provided(module):
    return set(module.provides) | set("slot:" + slot for slot in module.slots)


def _requirements(module):
    """The module's requirements: (capability, soft), with each slot fill as a soft one."""
    found = list(module.requires)
    known = set(cap for cap, _ in found)
    for slot, _ in module.fills:
        if slot not in known:
            found.append((slot, True))
    return found


def _always_soft(capability):
    # A slot fill is soft too, but it enters as a soft requirement (see _requirements).
    return capability in declarations.HARNESS_CAPABILITIES


def _label(key):
    return "%s/%s" % key


def _problem(subject, rule, message):
    return declarations.DeclarationError("selection", subject, rule, message)


def _check_set(selected, modules, harness_required, which, problems, warnings):
    chosen = [(key, modules[key]) for key in selected]
    keys = [key for key, _ in chosen]
    provided = {key: _provided(module) for key, module in chosen}

    for mtype, required in (("harness", harness_required), ("process", False)):
        of_type = [_label(key) for key, module in chosen if module.type == mtype]
        if len(of_type) > 1:
            problems.append(_problem(mtype, mtype + "-count", "more than one %s module is "
                                     "selected: %s" % (mtype, ", ".join(of_type))))
        elif required and not of_type:
            problems.append(_problem(mtype, mtype + "-count", "no %s module is selected"
                                     % mtype))

    owners = collections.defaultdict(list)
    for key, module in chosen:
        for slot in module.slots:
            owners[slot].append(_label(key))
    for slot, who in sorted(owners.items()):
        if len(who) > 1:
            problems.append(_problem("slot:" + slot, "slot-owner", "more than one selected "
                                     "module owns the slot: %s" % ", ".join(who)))

    for key, module in chosen:
        for slot in module.slots:
            if slot in base.BASE_SLOTS:
                problems.append(declarations.DeclarationError(
                    "module", module.name, "slot-owner", "owns slot %r, which the base owns"
                    % slot, key[0]))

    named = collections.defaultdict(list)
    for key, module in chosen:
        for command in module.commands:
            named[command.name].append(_label(key))
    for name, who in sorted(named.items()):
        if len(who) > 1:
            problems.append(_problem("command:" + name, "command-name", "more than one selected "
                                     "module declares the command %r: %s" % (name, ", ".join(who))))

    pins = collections.defaultdict(list)
    for key, module in chosen:
        for command in module.commands:
            pins[declarations.fold_name(command.name)].append((command.name, "command", _label(key)))
        for entry in module.checks:
            pins[declarations.fold_name(entry.pin_name)].append((entry.pin_name, "check", _label(key)))
    for folded, users in sorted(pins.items()):
        if len(users) > 1 and not (all(kind == "command" for _, kind, _ in users)
                                   and len({name for name, _, _ in users}) == 1):
            problems.append(_problem("pin:" + folded, "pin-name", "one pin name is used more than "
                                     "once across commands and checks: %s" % ", ".join(
                                         "%s %r in %s" % (kind, name, who) for name, kind, who in users)))

    deps = {key: set() for key in keys}
    for key, module in chosen:
        for capability, soft in _requirements(module):
            providers = [other for other in keys if other != key and capability in provided[other]]
            deps[key].update(providers)
            if providers or capability in _BASE_CAPABILITIES:
                continue
            if soft or _always_soft(capability):
                warnings.append("module '%s' (package '%s'): nothing selected provides %r"
                                % (module.name, key[0], capability)
                                + ("; affected items are skipped"
                                   if capability in declarations.HARNESS_CAPABILITIES else ""))
                continue
            could = sorted(_label(other) for other, m in modules.items()
                           if other not in selected and capability in _provided(m))
            hint = ("; selecting one of %s would supply it" % ", ".join(could) if could
                    else "; add a package that provides it")
            problems.append(declarations.DeclarationError(
                "module", module.name, "requires", "hard requirement %r has no provider "
                "among the selected modules%s" % (capability, hint), key[0]))

    reported = set()
    for key, module in chosen:
        for capability in module.blocks:
            for other in keys:
                if other == key or capability not in provided[other]:
                    continue
                marker = (frozenset((key, other)), capability)
                if marker in reported:
                    continue
                reported.add(marker)
                problems.append(declarations.DeclarationError(
                    "module", module.name, "blocks", "blocks %r, which module '%s' (package '%s') "
                    "provides" % (capability, other[1], other[0]), key[0]))

    for key, module in chosen:
        for helper in module.helpers:
            try:
                found = which(helper)
            except OSError:
                found = None
            if found is None:
                warnings.append("module '%s' (package '%s'): helper %r was not found on PATH"
                                % (module.name, key[0], helper))

    cycle = _find_cycle(keys, deps)
    if cycle:
        problems.append(_problem("requires", "cycle", "requirements form a cycle: %s"
                                 % " -> ".join(_label(key) for key in cycle)))
        return ()
    return _install_order(chosen, deps)


def _find_cycle(keys, deps):
    remaining = set(keys)
    changed = True
    while changed:
        changed = False
        for key in keys:
            if key in remaining and not (deps[key] & remaining):
                remaining.discard(key)
                changed = True
    if not remaining:
        return None
    # Every module left has a requirement that is also left, so following them repeats.
    key = next(k for k in keys if k in remaining)
    path = [key]
    while True:
        key = next(k for k in keys if k in deps[key] and k in remaining)
        if key in path:
            return path[path.index(key):] + [key]
        path.append(key)


def _install_order(chosen, deps):
    rank = {"harness": 0, "process": 1, "module": 2}
    group = {key: rank[module.type] for key, module in chosen}
    order = []
    for level in (0, 1, 2):
        waiting = [key for key, _ in chosen if group[key] == level]
        while waiting:
            ready = next(k for k in waiting
                         if not any(group[d] == level and d in waiting for d in deps[k]))
            waiting.remove(ready)
            order.append(ready)
    return order
