"""The approval gate: is a verified selection approved on this machine?

``check_selection`` takes the result of ``verify.verify_packages`` for a selection and
answers, module by module in install order, whether each has an approval. The selection is
approved only when every module is. It only reads: the guarded store and the shipped
approvals are never written, and an installer that finds the selection unapproved has
written nothing.

A module is approved by, in this order:

1. a ``module`` record bound to its subject (``<package>/<module>``), declaration hash
   and tree hash; or
2. for a module of type ``module`` only, a ``package`` record bound to the package's
   current declaration hash and whole-package tree hash that also lists this module with
   exactly these two hashes.

Only a module whose type is exactly ``module`` may use a package record. Every other
type (``harness``, ``process``, or anything else a result might carry) needs a record of its
own, as the spec says for harness and process modules. A first-party package is looked up in
the shipped approvals first and then the guarded store (``firstparty.py``); any other package
only in the guarded store.

Limits, recorded on purpose:

* The gate approves what ``verify`` hashed, not what an installer reads later. It ties
  nothing to the disk at install time, so an installer must write from the exact bytes that
  were verified, or verify and gate again from the same snapshot immediately before writing.
  A file swapped in between would otherwise be installed unapproved.
* The gate trusts the result it is given, including each package's ``first_party`` flag. The
  installer must set that flag from ``firstparty.is_first_party``; the gate does not recheck
  where the package lives. A shipped record matches only the exact subject and hashes it
  was made for, so claiming first-party for other bytes gains nothing, and claiming
  third-party only loses the shipped lookup.
* A malformed result (wrong shapes, not produced by ``verify``) is not approved.

The gate is fail closed. A refused verification result passes through as refused and
nothing is looked up. An empty selection is not approved: nothing was chosen, and an
installer must not treat that as permission. A module the result does not describe is not
approved.

Nothing calls this yet outside tests; the installer that will write a project calls it
first.
"""

import collections

from . import firstparty

# `via` is "module" or "package" (which record approved it); `source` is "shipped" or
# "store". Both are None when the module is not approved.
ModuleGate = collections.namedtuple("ModuleGate", "package name type approved via source reason")
Gate = collections.namedtuple("Gate", "approved modules reason")


def _refused(reason):
    return Gate(False, (), reason)


def check_selection(store, result, distribution=None):
    """Decide whether every module of a verified selection is approved."""
    try:
        return _check_selection(store, result, distribution)
    except (TypeError, AttributeError, IndexError, KeyError, ValueError):
        return _refused("the verification result is malformed, so nothing is approved")


def _check_selection(store, result, distribution):
    if not getattr(result, "accepted", False):
        return _refused("verification was refused, so nothing was looked up")
    if not result.order:
        return _refused("no modules were selected")
    verified = {(m.package, m.name): m for m in result.modules}
    packages = {info.name: info for info in result.packages}
    out = []
    for key in result.order:
        module = verified.get(tuple(key))
        info = packages.get(key[0]) if module is not None else None
        if module is None or info is None:
            out.append(ModuleGate(key[0], key[1], None, False, None, None,
                                  "the verification result does not describe this module"))
            continue
        out.append(_check_module(store, module, info, distribution))
    approved = all(item.approved for item in out)
    return Gate(approved, tuple(out), "" if approved else "some modules are not approved")


def _check_module(store, module, info, distribution):
    subject = "%s/%s" % (module.package, module.name)
    found = firstparty.check_module(store, subject, module.declaration_hash, module.tree_hash,
                                    info.first_party, distribution)
    if found.check.approved:
        return ModuleGate(module.package, module.name, module.type, True, "module", found.source, "")
    reason = found.check.reason
    if module.type != "module":
        return ModuleGate(module.package, module.name, module.type, False, None, None,
                          "a %s module needs an approval of its own: %s" % (module.type, reason))
    package = firstparty.check_package(store, module.package, info.declaration_hash,
                                       info.tree_hash, info.first_party, distribution)
    if package.check.approved:
        listed = (module.name, module.declaration_hash, module.tree_hash)
        if listed in package.check.record.modules:
            return ModuleGate(module.package, module.name, module.type, True, "package",
                              package.source, "")
        return ModuleGate(module.package, module.name, module.type, False, None, None,
                          "the approved package does not list this module with these hashes")
    return ModuleGate(module.package, module.name, module.type, False, None, None,
                      "module: %s; package: %s" % (reason, package.check.reason))
