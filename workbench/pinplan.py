"""Pin plan: the pins an install, add, upgrade or acknowledge makes for the helpers modules declare.

A module declares the helpers it offers as ``commands`` and ``checks``. The launcher runs a helper
only when a pin holds its exact bytes (``pins.py``). The owner who types the digest of an install,
add or upgrade has confirmed those bytes, so the installer pins them in the same step and the owner
does not type ``pin`` for each. ``wanted`` says which pins a set of modules implies, ``changes`` how
they differ from the pins that exist, and ``apply`` the pins that result. Nothing here reads or
writes the project or the store; the callers do, and put the changes in the digest the owner types.

A pin follows the bytes of the confirmed plan. A helper the plan does not write keeps the pin it has,
so a pulled edit stays refused until ``acknowledge`` accepts it. A pin is created for such a helper
only when none exists.
"""

import collections

from . import pins

Wanted = collections.namedtuple("Wanted", "name path sha256 kit declaration")
# `old` is the pin that exists under the name, or None for a created pin.
Change = collections.namedtuple("Change", "action pin old")

CREATE, UPDATE, REPLACE = "create", "update", "replace"


def declared(module):
    """``(pin name, helper path in the module, kit or None)`` for each command and check of `module`.

    A command is pinned under its name and a check under the last segment of its helper path, as the
    launcher's callers look them up. Only a Python helper runs through the kit."""
    found = [(c.name, c.helper, c.kit if c.runtime == "python" else None) for c in module.commands]
    found += [(c.pin_name, c.helper, c.kit) for c in module.checks]
    return found


def wanted(modules, hash_of):
    """The pins `modules` (``verify.Verified`` records) imply, as ``Wanted``.

    `hash_of(path)` is the SHA-256 the helper at a project path will have, or None when the plan
    cannot say; a helper without one is left out. A harness module writes nothing here and
    declares nothing that is pinned."""
    found = []
    for verified in modules:
        if verified.type == "harness":
            continue
        for name, helper, kit in declared(verified.module):
            path = ".workbench/%s/%s/%s" % (verified.package, verified.name, helper)
            digest = hash_of(path)
            if digest is not None:
                found.append(Wanted(name, path, digest, kit, verified.declaration_hash))
    return found


def changes(held, wanted_pins, who, now, written):
    """The ``Change`` for each wanted pin that differs from `held` (``{name: Pin}``), by name.

    `written` is the set of project paths the plan writes. Absent: created. Equal: nothing. A helper
    the plan does not write keeps its pin, unless the pin holds the same bytes under a different kit.
    Otherwise the pin is updated (same path) or replaced (another path, such as one the owner typed)."""
    found = []
    for want in sorted(wanted_pins):
        pin = pins.Pin(want.name, want.path, want.sha256, who, now, want.kit, want.declaration)
        old = held.get(want.name)
        if old is None:
            found.append(Change(CREATE, pin, None))
        elif (old.path, old.sha256, old.kit, old.declaration) == (
                want.path, want.sha256, want.kit, want.declaration):
            continue
        elif want.path not in written and not (old.path, old.sha256) == (want.path, want.sha256):
            continue
        elif old.path == want.path:
            found.append(Change(UPDATE, pin, old))
        else:
            found.append(Change(REPLACE, pin, old))
    return found


def apply(held, made):
    """`held` with every change of `made` applied: a new ``{name: Pin}``."""
    result = dict(held)
    for change in made:
        result[change.pin.name] = change.pin
    return result


def fields(made):
    """The changes as plain data for the digest the owner types. The time is left out: it is fixed
    once for the command and is in the bytes of the pins file, whose hash the digest holds as well."""
    out = []
    for change in made:
        row = {"action": change.action, "name": change.pin.name, "path": change.pin.path,
               "sha256": change.pin.sha256, "kit": change.pin.kit, "pinned_by": change.pin.pinned_by,
               "declaration": change.pin.declaration}
        if change.old is not None:
            row["was"] = {"path": change.old.path, "sha256": change.old.sha256,
                          "kit": change.old.kit, "pinned_by": change.old.pinned_by,
                          "declaration": change.old.declaration}
        out.append(row)
    return out


def lines(made, show):
    """Preview lines for `made`. `show` cleans a string to ASCII."""
    out = []
    for change in made:
        pin = change.pin
        row = "  %s pin %s: %s sha256 %s %s" % (
            change.action, show(pin.name), show(pin.path), pin.sha256,
            "kit %d" % pin.kit if pin.kit is not None else "run directly")
        if change.old is None or change.old.declaration != pin.declaration:
            row += ", declaration %s" % pin.declaration[:12]
        if change.old is not None:
            row += " (was %s sha256 %s, %s%s, made by %s)" % (
                show(change.old.path), change.old.sha256[:12],
                "kit %d" % change.old.kit if change.old.kit is not None else "run directly",
                ", declaration %s" % (change.old.declaration or "none")[:12]
                if change.old.declaration != pin.declaration else "",
                show(change.old.pinned_by))
        out.append(row)
    return out
