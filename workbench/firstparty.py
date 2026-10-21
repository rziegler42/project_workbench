"""First-party packages and their release-time approvals.

The workbench distribution is a directory (the repository root) that holds the code in
``workbench/``, the first-party packages in ``packages/`` and the approvals made for them
in ``workbench/shipped_approvals/``. The shipped approvals have the same layout and the
same records as the guarded store (``packages/<key>/approval.json``) and are read with the
same checks, but only from the installed workbench: they are never copied into the store.
Shipping with the workbench counts as explicit approval
(``docs/specs/trust-and-approval.md``); the distribution is the trust root for them, and
it is version-pinned.

A package is first-party only when all of these hold, otherwise it is treated as
third-party:

* its directory lies directly inside the distribution's ``packages/`` directory and is
  not a symbolic link,
* its declared name equals its directory name, and
* a shipped package record for that name matches the package's current declaration hash
  and tree hash.

A package copied elsewhere, or a third-party package that reuses a first-party name, fails
the first test. A first-party package changed since release fails the last one, so it loses
the right to unprefixed names and its modules are checked against the guarded store like any
other package. The records are trusted because the distribution is: they count as approval
only if the owner reviews what the release changed in them.

``release_approvals`` is the release-time generator. It is not a command for users of a
project. It verifies every package under ``packages/`` as first-party, writes nothing if
any module fails, and otherwise writes one module record per module and one package record
per package with a fixed approver and time, so running it twice gives identical files.
Records of earlier releases are left alone and reported, because deletion is not provided
here. A failure while verifying writes nothing; a write that fails part way can leave the
earlier records of that run on disk. They are valid and a rerun is idempotent.
"""

import collections
import os

from . import approvals, declarations, hashing, store, verify
from .wbkit import safefs

PACKAGES = "packages"
SHIPPED = os.path.join("workbench", "shipped_approvals")
RELEASE_APPROVER = "workbench-release"
RELEASE_TIME = "1970-01-01T00:00:00Z"

Found = collections.namedtuple("Found", "check source")
Release = collections.namedtuple("Release", "packages records warnings")


class ReleaseError(Exception):
    """The release could not be generated; nothing was written."""


class _Shipped(store.Tree):
    what = "shipped approvals"


class _ShippedWriter(store.Store):
    what = "shipped approvals"


def default_distribution():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def shipped_tree(distribution):
    return _Shipped(os.path.join(distribution, SHIPPED))


def is_first_party(package_path, distribution=None):
    distribution = distribution or default_distribution()
    if not isinstance(package_path, str) or not package_path or "\0" in package_path:
        return False
    # A trailing slash would make islink follow the link, so it is dropped first.
    if os.path.islink(package_path.rstrip("/") or "/"):
        return False
    real = os.path.realpath(package_path)
    if os.path.dirname(real) != os.path.realpath(os.path.join(distribution, PACKAGES)):
        return False
    name = os.path.basename(real)
    try:
        declaration, tree = _package_hashes(real, name)
    except (safefs.SafeFsError, declarations.DeclarationError, ReleaseError, ValueError, OSError):
        return False
    return approvals.check_package(shipped_tree(distribution), name, declaration, tree).approved


def _both(shipped, stored):
    return approvals.Check(False, None, "shipped: %s; guarded store: %s"
                           % (shipped.reason, stored.reason))


def _found(shipped_check, check_in_store):
    if shipped_check is not None and shipped_check.approved:
        return Found(shipped_check, "shipped")
    stored = check_in_store()
    if stored.approved:
        return Found(stored, "store")
    if shipped_check is None:
        return Found(stored, None)
    return Found(_both(shipped_check, stored), None)


def check_module(store_, subject, declaration_hash, tree_hash, first_party, distribution=None):
    """Shipped records first for a first-party package, then the guarded store."""
    shipped = None
    if first_party:
        shipped = approvals.check_module(shipped_tree(distribution or default_distribution()),
                                         subject, declaration_hash, tree_hash)
    return _found(shipped,
                  lambda: approvals.check_module(store_, subject, declaration_hash, tree_hash))


def check_package(store_, subject, declaration_hash, tree_hash, first_party, distribution=None):
    shipped = None
    if first_party:
        shipped = approvals.check_package(shipped_tree(distribution or default_distribution()),
                                          subject, declaration_hash, tree_hash)
    return _found(shipped,
                  lambda: approvals.check_package(store_, subject, declaration_hash, tree_hash))


# --- release-time generator -----------------------------------------------------


def _package_dirs(packages_dir):
    with safefs.Root(packages_dir, "first-party packages") as root:
        entries = root.walk()
    names = []
    for entry in entries:
        if "/" in entry.rel:
            continue
        if entry.kind != "dir":
            raise ReleaseError("%s/%s is not a package directory (%s)"
                               % (packages_dir, entry.rel, entry.kind))
        names.append(entry.rel)
    return sorted(names)


def _package_hashes(path, name):
    with safefs.Root(path, "package") as root:
        document = declarations.parse_json(root.read_file("package.json"))
    if document.get("name") != name:
        raise ReleaseError("package %r: the directory name and the package name differ" % name)
    return hashing.declaration_hash(document), hashing.tree_hash(path, what="package")


def release_approvals(distribution=None, approver=RELEASE_APPROVER, time=RELEASE_TIME):
    """Write the shipped approvals for every package under ``packages/``."""
    distribution = distribution or default_distribution()
    packages_dir = os.path.join(distribution, PACKAGES)
    try:
        present = os.path.lexists(packages_dir)
        names = _package_dirs(packages_dir) if present else []
    except (safefs.SafeFsError, OSError) as exc:
        raise ReleaseError(str(exc))
    if not names:
        return Release(0, 0, [])

    plan = []
    problems = []
    for name in names:
        path = os.path.join(packages_dir, name)
        try:
            result = verify.verify_package(path, first_party=True, harness_required=False)
            if not result.accepted:
                problems.extend(str(problem) for problem in result.problems)
                continue
            decl, tree = _package_hashes(path, name)
        except (safefs.SafeFsError, declarations.DeclarationError, ReleaseError, ValueError) as exc:
            problems.append(str(exc))
            continue
        plan.append((name, decl, tree, result.modules))
    if problems:
        raise ReleaseError("nothing was written; first-party packages were refused:\n  "
                           + "\n  ".join(problems))

    shipped_root = os.path.join(distribution, SHIPPED)
    try:
        os.makedirs(shipped_root, exist_ok=True)
        writer = _ShippedWriter(shipped_root)
        wanted = set()
        records = 0
        for name, decl, tree, modules in plan:
            for module in modules:
                record = approvals.record_module(
                    writer, "%s/%s" % (name, module.name), module.declaration_hash,
                    module.tree_hash, approver, time)
                wanted.add(approvals.record_key("module", record.declaration_hash, record.tree_hash))
                records += 1
            record = approvals.record_package(
                writer, name, decl, tree,
                [(m.name, m.declaration_hash, m.tree_hash) for m in modules], approver, time)
            wanted.add(approvals.record_key("package", record.declaration_hash, record.tree_hash))
            records += 1
        warnings = _stale(writer, wanted)
    except (safefs.SafeFsError, approvals.ApprovalError, OSError) as exc:
        raise ReleaseError("could not write the shipped approvals: %s" % exc)
    return Release(len(plan), records, warnings)


def _stale(writer, wanted):
    try:
        with safefs.Root(writer.root, "shipped approvals") as root:
            entries = root.walk()
    except safefs.SafeFsError:
        return []
    found = sorted(e.rel.split("/")[1] for e in entries
                   if e.rel.count("/") == 1 and e.rel.startswith(PACKAGES + "/"))
    return ["shipped record %s is not part of this release; remove it by hand" % key[:12]
            for key in found if key not in wanted]
