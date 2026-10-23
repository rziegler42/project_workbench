"""What a harness module turns the installed modules into, shared by ``wb attach`` and the plan
of ``wb install``: the neutral input of every module, the translated files, the root file, the
permission rules, the exclude lines and the local manifest to write.

Nothing here reads or writes the project. ``stage`` takes the verified harness module, the
install-ordered modules and their snapshots, so the install preview, its digest and the later
write are built from the same bytes.
"""

import collections
import hashlib
import os

from . import declarations, harnessplan, installplan, localmanifest, manifest, neutral, target
from .wbkit import display, safefs
from .refusal import Refused

# Bytes of harness files one attach writes: the neutral tree, and the overrides, are each bounded
# by `neutral.MAX_TOTAL_BYTES`.
MAX_WRITE_BYTES = 2 * neutral.MAX_TOTAL_BYTES
_RESERVED = (".git", ".workbench")

# `token` is ``<package>/<module>``; `files` are ``harnessplan.Planned`` sorted by path; `exclude`
# the layout's entries; `document` the local manifest to write; `settings` the path of the
# permissions file or None; `reports` the translation's; `warnings` and `notes` are text.
Staged = collections.namedtuple(
    "Staged", "token version files settings exclude document reports warnings notes")


def default_home():
    """The home directory the rendered rules name: the account database's, not ``$HOME``."""
    return target._account_home()


# --- the neutral input of every module ---------------------------------------------------------


def _name_ok(name):
    return neutral._name_ok(name)


def _override(rest, data, who, overrides, owners):
    """Take the file at `rest` (below ``harness/<harness>/``) into `overrides`."""
    where = "%s: harness/<harness>/%s" % (who, "/".join(rest))
    kind = neutral.KINDS.get(rest[0])
    if kind is None:
        raise Refused(["%s: not under skills/, agents/ or commands/" % where])
    if kind == "skill":
        if len(rest) < 3 or not _name_ok(rest[1]):
            raise Refused(["%s: an override of a skill is skills/<name>/<file>" % where])
        name, inner = rest[1], "/".join(rest[2:])
    else:
        if len(rest) != 2 or not rest[1].endswith(".md") or not _name_ok(rest[1][:-3]):
            raise Refused(["%s: an override is %s/<name>.md" % (where, rest[0])])
        name, inner = rest[1][:-3], rest[1]
    key = (kind, name)
    if owners.setdefault(key, who) != who:
        raise Refused(["%s and %s both override %s/%s" % (owners[key], who, kind, name)])
    overrides.setdefault(key, {})[inner] = data


def _exclusions(data, who, excludes):
    where = "%s: harness/<harness>/manifest.json" % who
    try:
        document = declarations.parse_json(data)
    except ValueError as exc:
        raise Refused(["%s: %s" % (where, exc)])
    entries = document.get("exclude", []) if isinstance(document, dict) else None
    if not isinstance(entries, list):
        raise Refused(["%s: 'exclude' must be a list" % where])
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("item"), str) \
                or not isinstance(entry.get("reason"), str):
            raise Refused(["%s: each exclusion needs an 'item' and a 'reason'" % where])
        folder, _, name = entry["item"].partition("/")
        kind = neutral.KINDS.get(folder)
        if kind is None or not _name_ok(name):
            raise Refused(["%s: %s is not an item" % (where, display.ascii_text(entry["item"])[:80])])
        excludes.setdefault((kind, name), entry["reason"])


def inputs(modules, snaps, harness):
    """``(tree, overrides, excludes)`` from the snapshots of `modules`, in install order.

    The neutral tree is the union of every module's ``harness/neutral/``; one path in two modules
    is refused. An override is the module's files in ``harness/<harness>/`` for one item, and a
    second module overriding the same item is refused. Anything under ``harness/`` for another
    harness is left alone."""
    tree, overrides, excludes, owners, supplied = {}, {}, {}, {}, {}
    for module in modules:
        key = (module.package, module.name)
        who = "%s/%s" % key
        for rel, data in sorted(snaps[key].files.items()):
            parts = rel.split("/")
            if parts[0] != "harness" or len(parts) < 3:
                continue
            if parts[1] == "neutral":
                sub = "/".join(parts[2:])
                if sub in tree:
                    raise Refused(["%s and %s both supply harness/neutral/%s"
                                   % (supplied[sub], who, display.ascii_text(sub)[:120])])
                tree[sub] = data
                supplied[sub] = who
            elif parts[1] == harness:
                if parts[2:] == ["manifest.json"]:
                    _exclusions(data, who, excludes)
                else:
                    _override(parts[2:], data, who, overrides, owners)
    return tree, overrides, excludes


# --- the plan ----------------------------------------------------------------------------------


def check_paths(files):
    """No planned path is `.git` or `.workbench`, or under one, whatever its case; no two collide."""
    seen = set()
    for planned in files:
        top = planned.path.split("/")[0].casefold()
        if top in _RESERVED:
            raise Refused(["the harness would write %s, inside %s, which only git and the "
                           "workbench use" % (display.ascii_text(planned.path)[:120], top)])
        if planned.path in seen:
            raise Refused(["two harness files map to %s" % display.ascii_text(planned.path)[:120]])
        seen.add(planned.path)
    try:
        safefs.check_tree_paths(sorted(seen))
    except safefs.SafeFsError as exc:
        raise Refused([str(exc)])
    if sum(len(planned.data) for planned in files) > MAX_WRITE_BYTES:
        raise Refused(["the harness files are too large (over %d bytes)" % MAX_WRITE_BYTES])


def _gated(modules):
    """Whether an installed process module names the command that lists the plans under way, which is what the
    edit gate asks; with none there is nothing for the gate to guard and no hook is rendered."""
    return any(item.type == "process" and item.module.approval and item.module.approval.get("active")
               for item in modules)


def stage(store_root, harness, modules, snaps, source, version, home, root):
    """Translate and render for `harness` (a ``verify.Verified``), over `modules` in install
    order, whose snapshots are `snaps`. `source` is where the harness package came from and
    `home` the home directory the rendered rules name (None when it is not known) and `root` the project directory
    the rendered rules may name (the edit gate's hook protects its settings file by that path). Returns a
    ``Staged``; raises ``Refused``. Nothing is read from or written to a project."""
    layout = harness.module.layout
    tree, overrides, excludes = inputs(modules, snaps, harness.name)
    if sum(len(data) for files in overrides.values() for data in files.values()) \
            > neutral.MAX_TOTAL_BYTES:
        raise Refused(["the overrides are too large (over %d bytes)" % neutral.MAX_TOTAL_BYTES])
    warnings = []
    try:
        done = harnessplan.translate(neutral.read_items(tree), layout, overrides, excludes,
                                     provides=harness.module.provides)
        files = [harnessplan.render_root(layout)] + list(done.files)
        files = [item for item in files if item is not None]
        settings = None
        hook = _gated(modules)
        if hook and not ("hooks" in harness.module.provides and harnessplan.hook_described(layout)):
            if "hooks" in harness.module.provides:
                raise harnessplan.PlanError("the module provides hooks but its layout does not describe the hook "
                                            "(it needs targets, event, timeout and block_code)")
            warnings.append("this harness renders no edit gate hook, so a plan under way is not stopped from "
                            "edits except by instruction")
            hook = False
        if "permissions" in harness.module.provides:
            local = layout.get("local_settings", "none")
            if local == "none":
                raise harnessplan.PlanError("the module provides permissions but its layout has "
                                            "no local settings to render them into")
            if not home:
                raise harnessplan.PlanError("the home directory is not known, so the rules that "
                                            "name it cannot be written")
            data = harnessplan.render_permissions(
                [], layout, os.path.realpath(store_root), os.path.realpath(home),
                hook_for=harness.name if hook else None, root=os.path.realpath(root))
            settings = harnessplan.Planned(local["path"], data, harnessplan.FILE_MODE,
                                           hashlib.sha256(data).hexdigest(), "permissions")
            files.append(settings)
        else:
            warnings.append("this harness provides no permissions, so the hard stops and the "
                            "guarded store are enforced only by instruction")
            if hook:
                warnings.append("this harness renders no edit gate hook, because the hook is written into the "
                                "permissions file it does not provide")
    except (neutral.NeutralError, harnessplan.PlanError) as exc:
        raise Refused([str(exc)])
    files.sort(key=lambda planned: planned.path.encode("utf-8"))
    check_paths(files)
    try:
        document = {
            "files": [{"hash": item.sha256, "path": item.path} for item in files],
            "format": localmanifest.FORMAT, "harness": harness.name,
            "module_version": harness.version,
            "source": installplan.public_source(source),
            "tree": harness.tree_hash, "workbench": version}
        localmanifest.serialize(document)
    except (localmanifest.LocalManifestError, manifest.ManifestError) as exc:
        raise Refused(["the local manifest cannot be written: %s" % exc])
    return Staged("%s/%s" % (harness.package, harness.name), harness.version, files,
                  settings.path if settings else None, list(layout.get("exclude", ())), document,
                  done.reports, warnings, list(layout.get("notes", ())))
