"""The base: the content the workbench puts in every project before any module.

The base is the ``base/`` directory of the workbench distribution. It is part of the
workbench, trusted as the workbench code is, and is not a module: it has no type and no
approval record (``docs/specs/repository-boundary.md``, "The base"). It owns two slots,
``policy`` in ``AGENTS.md`` and ``docs-index`` in ``docs/README.md``, each marked by one
``<!-- @slot: <name> -->`` line.

``.workbench/.gitignore`` is the third base file. It is generated from
``manifest.BASE_IGNORE`` and is not stored here, so ``files`` and the tree hash cover the
stored files only.
"""

import os

from . import hashing
from .wbkit import safefs

DIRECTORY = "base"
BASE_SLOTS = ("docs-index", "policy")
SLOT_FILES = {"policy": "AGENTS.md", "docs-index": "docs/README.md"}


class BaseError(safefs.SafeFsError):
    """The base is missing, has a file that is not allowed, or lacks a slot marker."""


class Base:
    """``files`` maps each relative path to its bytes; ``tree_hash`` is the tree hash."""

    def __init__(self, files, tree_hash):
        self.files = files
        self.tree_hash = tree_hash


def marker(slot):
    return "<!-- @slot: %s -->" % slot


def load_base(distribution=None):
    """Read the base from `distribution` (default: this workbench) and hash it."""
    if distribution is None:
        from . import firstparty
        distribution = firstparty.default_distribution()
    path = os.path.join(distribution, DIRECTORY)
    try:
        info = hashing.hash_tree(path, "the base", keep=lambda rel: True)
    except safefs.SafeFsError as exc:
        raise BaseError("the base cannot be read: %s" % exc)
    for rel in info.files:
        try:
            safefs.validate_relpath(rel)
        except safefs.SafeFsError as exc:
            raise BaseError("the base has an unusable path: %s" % exc)
    if info.executable:
        raise BaseError("the base has an executable file: %s" % info.executable[0])
    for slot in BASE_SLOTS:
        data = info.contents.get(SLOT_FILES[slot])
        if data is None:
            raise BaseError("the base lacks %s, which holds the %s slot" % (SLOT_FILES[slot], slot))
        lines = data.decode("utf-8", "replace").split("\n")
        if lines.count(marker(slot)) != 1:
            raise BaseError("%s must hold the line %s exactly once" % (SLOT_FILES[slot], marker(slot)))
    return Base(dict(info.contents), info.hash)
