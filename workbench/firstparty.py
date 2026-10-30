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
project. It is ``plan_release`` followed by ``write_release``: the plan verifies every package under ``packages/`` as
first-party, writes nothing and refuses if any module fails (``wb preview release-approvals`` prints it), and the write
records one module record per module and one package record per package of that plan with a fixed approver and time,
without reading the packages again, so running it twice gives identical files.
Records of earlier releases are left alone and reported, because deletion is not provided
here. A failure while verifying writes nothing; a write that fails part way can leave the
earlier records of that run on disk. They are valid and a rerun is idempotent.
"""

import collections
import hashlib
import os

from . import approvals, declarations, hashing, store, verify
from .wbkit import display, safefs

PACKAGES = "packages"
SHIPPED = os.path.join("workbench", "shipped_approvals")
RELEASE_APPROVER = "workbench-release"
RELEASE_TIME = "1970-01-01T00:00:00Z"

Found = collections.namedtuple("Found", "check source")
Release = collections.namedtuple("Release", "packages records warnings")
# The release plan: what a release would record, built once by ``plan_release`` and written by ``write_release`` without a second
# reading of the packages (``docs/specs/command-permissions.md``, "`wb release-approvals` at `ask`"). `recorded` is whether a valid
# shipped record for those hashes exists now; `stale` is the full keys of the shipped records that this release leaves behind.
PlannedModule = collections.namedtuple("PlannedModule", "name declaration_hash tree_hash recorded")
PlannedPackage = collections.namedtuple("PlannedPackage", "name declaration_hash tree_hash recorded modules")
ReleasePlan = collections.namedtuple("ReleasePlan", "packages approver time stale")


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
    """Write the shipped approvals for every package under ``packages/``: the plan, then the write of that plan."""
    distribution = distribution or default_distribution()
    return write_release(plan_release(distribution, approver, time), distribution)


def plan_release(distribution=None, approver=RELEASE_APPROVER, time=RELEASE_TIME):
    """The ``ReleasePlan`` for every package under ``packages/``: read and verify them, write nothing. ``ReleaseError`` when a
    package is refused, with the reasons."""
    distribution = distribution or default_distribution()
    packages_dir = os.path.join(distribution, PACKAGES)
    try:
        present = os.path.lexists(packages_dir)
        names = _package_dirs(packages_dir) if present else []
    except (safefs.SafeFsError, OSError) as exc:
        raise ReleaseError(str(exc))
    if not names:
        return ReleasePlan((), approver, time, ())

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

    shipped = shipped_tree(distribution)
    planned = []
    wanted = set()
    try:
        for name, decl, tree, modules in plan:
            members = []
            for module in modules:
                subject = "%s/%s" % (name, module.name)
                recorded = approvals.check_module(shipped, subject, module.declaration_hash, module.tree_hash).approved
                members.append(PlannedModule(module.name, module.declaration_hash, module.tree_hash, recorded))
                wanted.add(approvals.record_key("module", module.declaration_hash, module.tree_hash))
            recorded = approvals.check_package(shipped, name, decl, tree).approved
            planned.append(PlannedPackage(name, decl, tree, recorded, tuple(members)))
            wanted.add(approvals.record_key("package", decl, tree))
    except approvals.ApprovalError as exc:
        raise ReleaseError("could not plan the shipped approvals: %s" % exc)
    stale = _stale(os.path.join(distribution, SHIPPED), wanted)
    return ReleasePlan(tuple(planned), approver, time, tuple(stale))


def write_release(plan, distribution=None):
    """Write the records of `plan` (a ``ReleasePlan``) and nothing else: the packages are not read again, so a package changed
    after the plan was built is not released by it (the records name the hashes the plan holds, and the changed tree no longer
    matches them). Returns the ``Release``; the warnings name the shipped records the plan leaves stale."""
    distribution = distribution or default_distribution()
    if not plan.packages:
        return Release(0, 0, [])
    shipped_root = os.path.join(distribution, SHIPPED)
    try:
        os.makedirs(shipped_root, exist_ok=True)
        writer = _ShippedWriter(shipped_root)
        records = 0
        for item in plan.packages:
            for module in item.modules:
                approvals.record_module(writer, "%s/%s" % (item.name, module.name), module.declaration_hash,
                                        module.tree_hash, plan.approver, plan.time)
                records += 1
            approvals.record_package(
                writer, item.name, item.declaration_hash, item.tree_hash,
                [(m.name, m.declaration_hash, m.tree_hash) for m in item.modules], plan.approver, plan.time)
            records += 1
    except (safefs.SafeFsError, approvals.ApprovalError, OSError) as exc:
        raise ReleaseError("could not write the shipped approvals: %s" % exc)
    warnings = ["shipped record %s is not part of this release; remove it by hand" % key[:12] for key in plan.stale]
    return Release(len(plan.packages), records, warnings)


def _stale(shipped_root, wanted):
    """The full keys of the shipped records under `shipped_root` that are not in `wanted`, sorted; none when there is no
    shipped directory yet."""
    try:
        with safefs.Root(shipped_root, "shipped approvals") as root:
            entries = root.walk()
    except (safefs.SafeFsError, OSError):
        return []
    found = sorted(e.rel.split("/")[1] for e in entries
                   if e.rel.count("/") == 1 and e.rel.startswith(PACKAGES + "/"))
    return [key for key in found if key not in wanted]


def preview_text(plan):
    """The text a ``wb preview release-approvals`` prints before its digest line: the packages and modules a release would
    record with their hashes in full and whether each record exists now, the approver and time, the stale records, and what the
    preview does not cover. A stale key is a directory name of the shipped tree, so it is printed through ``display.clean``: a
    name that holds a newline or an escape cannot forge a line of the text, a digest line included. The names of packages and
    modules come from verified declarations and cannot hold one."""
    lines = ["release approvals", "packages: %d" % len(plan.packages),
             "modules: %d" % sum(len(item.modules) for item in plan.packages)]
    for item in plan.packages:
        lines.append("package %s declaration %s tree %s record %s"
                     % (item.name, item.declaration_hash, item.tree_hash, "recorded" if item.recorded else "new"))
        for module in item.modules:
            lines.append("  module %s declaration %s tree %s record %s"
                         % (module.name, module.declaration_hash, module.tree_hash,
                            "recorded" if module.recorded else "new"))
    lines.append("approver: %s" % display.clean(plan.approver))
    lines.append("time: %s" % display.clean(plan.time))
    lines.append("stale records: %d" % len(plan.stale))
    lines.extend("  %s" % display.clean(key) for key in plan.stale)
    lines.append("not covered: the content of the packages; read the change with git diff before confirming")
    return "\n".join(lines) + "\n"


def digest_of(text):
    """The first 32 hexadecimal characters of the SHA-256 of `text` (the digest line of a preview, as for a plan's)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
