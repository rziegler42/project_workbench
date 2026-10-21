"""A snapshot of a module: its files read once, and proved to be what was approved.

The gate approves what ``verify`` hashed. An install must therefore write those bytes and no
others. ``take`` reads every file of the module directory once, hashes the bytes it holds,
and refuses unless the tree hash and the declaration hash equal the verified ones. The caller
verifies and gates the selection first, then takes the snapshots, and writes from them; nothing
reads the package again afterwards.
"""

import collections

from . import declarations, hashing
from .wbkit import safefs

Snapshot = collections.namedtuple("Snapshot", "package module files executable")


class SnapshotError(safefs.SafeFsError):
    """The module is not the one that was verified and approved."""


def take(module_root, verified):
    """Read the module at `module_root` once and return a ``Snapshot``.

    `verified` is the ``verify.Verified`` record the gate approved.
    """
    label = "%s/%s" % (verified.package, verified.name)
    try:
        info = hashing.hash_tree(module_root, "module", keep=lambda rel: True)
    except safefs.SafeFsError as exc:
        raise SnapshotError("module %s cannot be read: %s" % (label, exc))
    if info.hash != verified.tree_hash:
        raise SnapshotError("module %s changed after it was verified: its files no longer "
                            "match the approved tree hash" % label)
    try:
        declaration = declarations.parse_json(info.contents.get("module.json", b""))
        current = hashing.declaration_hash(declaration)
    except (ValueError, safefs.SafeFsError):
        raise SnapshotError("module %s has a module.json that cannot be read" % label)
    if current != verified.declaration_hash:
        raise SnapshotError("module %s changed after it was verified: its declaration no "
                            "longer matches the approved hash" % label)
    return Snapshot(verified.package, verified.name, dict(info.contents),
                    frozenset(info.executable))
