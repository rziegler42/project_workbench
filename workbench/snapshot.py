"""A snapshot of a module: its files read once, and proved to be what was approved.

The gate approves what ``verify`` hashed. An install must therefore write those bytes and no
others. ``take`` reads every file of the module directory once, hashes the bytes it holds,
and refuses unless the tree hash and the declaration hash equal the verified ones. The caller
verifies and gates the selection first, then takes the snapshots, and writes from them; nothing
reads the package again afterwards.

The maintainer directories (``tests/``, ``tools/``) are hashed with the rest of the tree, so a
change to them fails the snapshot, but their bytes are not kept: nothing an install writes can
come from them.
"""

import collections

from . import declarations, hashing, modulefiles
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
        info = hashing.hash_tree(module_root, "module", keep=lambda rel: not modulefiles.is_maintainer(rel))
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
                    frozenset(rel for rel in info.executable if not modulefiles.is_maintainer(rel)))
