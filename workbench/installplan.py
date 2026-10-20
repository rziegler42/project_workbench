"""The install write plan: everything an install would do, its digest and the preview text.

``build`` is a pure function. ``wb preview install`` and ``wb install`` both call it with the
same inputs, so what an agent previews is what the owner is shown and what is written. Nothing
here touches the disk, the network, git or the store.

The plan holds, in the order they are carried out: making a missing target, the install marker
``.workbench/local/incomplete``, the empty ``.git`` (when the target has none), the remaining
directories, then every file. The workbench writes the ``.git`` skeleton itself and never runs
git, so no program resolves a path inside the target; the marker still comes first so a failure
part-way is found by it. The files are the base (with the blocks modules fill into its slots), each
non-harness module's namespace copy, the files a module ``writes``, ``.workbench/.gitignore`` and
the committed manifest. A harness module is verified and approved but writes nothing and is not
in the manifest.

Hashes in the manifest: a seeded file records the hash of what the workbench or module supplied,
a slot block the hash of its block text. The acknowledgement baselines record the hash of the
bytes actually written, for every committed file.

The digest is SHA-256 over canonical JSON with explicit field names, so two different plans can
never encode alike.
"""

import collections
import hashlib
import json
import re

from . import base as base_module
from . import display, manifest, safefs

Action = collections.namedtuple("Action", "kind path owner_class mode size hash detail data")
PackageSource = collections.namedtuple("PackageSource", "name source ref commit tree")
# `modules`: the install-ordered ``verify.Verified`` records; `packages`: their PackageSource.
Selection = collections.namedtuple("Selection", "modules packages")
Plan = collections.namedtuple(
    "Plan", "target_identity state actions modules manifest seed project_id store_writes "
            "git_init digest")

MARKER_PATH = ".workbench/local/incomplete"
GIT_DETAIL = "an empty repository on branch main, written by the workbench; git is not run"
# What ``git init --template=`` leaves, in the order it is created: a directory has no content.
GIT_SKELETON = (
    ("objects", None), ("objects/info", None), ("objects/pack", None), ("refs", None),
    ("refs/heads", None), ("refs/tags", None),
    ("HEAD", b"ref: refs/heads/main\n"),
    ("config", b"[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n"
               b"\tbare = false\n\tlogallrefupdates = true\n"),
)
BASE_ORIGIN = "the base"


class PlanError(Exception):
    """The install cannot be planned. The message names the module or path."""


def public_source(source):
    """A source with any user name, password, query and fragment removed.

    The authority is everything up to the first ``/``, as git reads it, so a ``#`` or ``?`` inside
    the user information cannot hide the rest of it.
    """
    scheme, found, rest = source.partition("://")
    if not found or not scheme:
        return source
    authority, slash, path = rest.partition("/")
    host = re.split(r"[?#]", authority.rsplit("@", 1)[-1])[0]
    path = re.split(r"[?#]", path)[0]
    return "%s://%s%s%s" % (scheme, host, slash, path)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _block_id(verified):
    return "%s/%s" % (verified.package, verified.name)


# --- assembling the files --------------------------------------------------------


class _Files:
    """Committed files in the order they will be written, with who supplied each."""

    def __init__(self):
        self.order = []
        self.items = {}

    def add(self, path, data, owner_class, executable, origin):
        if path in self.items:
            earlier = self.items[path]["origin"]
            if earlier == BASE_ORIGIN or origin == BASE_ORIGIN:
                raise PlanError("%s writes %s, which the base writes" % (
                    origin if earlier == BASE_ORIGIN else earlier, path))
            raise PlanError("%s and %s both write %s" % (earlier, origin, path))
        self.order.append(path)
        self.items[path] = {"data": data, "class": owner_class, "x": executable,
                            "origin": origin, "blocks": [], "texts": {}}


def _marker_line(slot):
    return base_module.marker(slot).encode("ascii")


def _check_fill_text(data, who):
    for line in data.split(b"\n"):
        text = line.rstrip(b"\r")
        if text.startswith(b"<!-- @slot:") or text.startswith(b"<!-- BEGIN ") \
                or text.startswith(b"<!-- END "):
            raise PlanError("%s: a fill source holds a slot or block marker line" % who)


def _apply_fill(files, verified, slot_name, source_bytes, blocks):
    who = _block_id(verified)
    slot = slot_name[len("slot:"):]
    try:
        source_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise PlanError("%s: the fill for %s is not UTF-8 text" % (who, slot_name))
    _check_fill_text(source_bytes, who)
    wanted = _marker_line(slot)
    holders = []
    for path in files.order:
        item = files.items[path]
        if item["origin"] != BASE_ORIGIN and item["class"] != "seeded":
            continue
        if not path.endswith(".md"):
            continue
        count = sum(1 for line in item["data"].split(b"\n") if line.rstrip(b"\r") == wanted)
        if count:
            holders.append((path, count))
    if len(holders) != 1 or holders[0][1] != 1:
        raise PlanError("%s: the slot %s has %s" % (who, slot, (
            "no marker in any file written" if not holders else
            "its marker in more than one place (%s)" % ", ".join(p for p, _ in holders))))
    path = holders[0][0]
    if not source_bytes.endswith(b"\n"):
        source_bytes += b"\n"
    block = (("<!-- BEGIN %s slot:%s -->\n" % (who, slot)).encode("ascii") + source_bytes
             + ("<!-- END %s slot:%s -->\n" % (who, slot)).encode("ascii"))
    item = files.items[path]
    lines = item["data"].split(b"\n")
    at = next(i for i, line in enumerate(lines) if line.rstrip(b"\r") == wanted)
    item["data"] = b"\n".join(lines[:at]) + (b"\n" if at else b"") + block \
        + b"\n".join(lines[at:])
    item["blocks"].append((slot, who))
    item["texts"][(who, slot)] = (block, source_bytes)
    blocks.append({"block": who, "class": "slot block", "hash": _sha(block), "path": path,
                   "slot": slot})


def assemble(selection, snapshots, base):
    """The files and the blocks an install of `selection` over `base` would write, with no
    target: ``(files, blocks)``. For each file, ``items[path]`` holds the bytes (with its blocks
    in), the owner class, whether it is executable, who supplied it, ``blocks`` (the
    ``(slot, who)`` pairs) and ``texts`` ({(who, slot): (block text, body)}), which an upgrade
    needs to edit a project that already exists."""
    files = _Files()
    for rel in sorted(base.files):
        files.add(rel, base.files[rel], "seeded", False, BASE_ORIGIN)
    fills = []
    for verified in selection.modules:
        who = _block_id(verified)
        module = verified.module
        snap = snapshots.get((verified.package, verified.name))
        if snap is None:
            raise PlanError("%s has no snapshot" % who)
        if verified.type == "harness":
            if module.writes or module.fills:
                raise PlanError("%s is a harness module and declares writes or fills; a harness "
                                "module writes nothing committed" % who)
            continue
        for rel in sorted(snap.files):
            files.add(".workbench/%s/%s/%s" % (verified.package, verified.name, rel),
                      snap.files[rel], "module-owned", rel in snap.executable, who)
        for rel in module.writes:
            if rel == ".workbench" or rel.startswith(".workbench/"):
                raise PlanError("%s writes %s, inside .workbench, which only the workbench and "
                                "a module's own namespace use" % (who, rel))
            source = "files/" + rel
            files.add(rel, snap.files[source], "seeded", source in snap.executable, who)
        for slot, source in module.fills:
            fills.append((verified, slot, snap.files[source]))
    files.add(".workbench/.gitignore", manifest.BASE_IGNORE, "module-owned", False, BASE_ORIGIN)
    blocks = []
    for verified, slot, data in fills:
        _apply_fill(files, verified, slot, data, blocks)
    return files, blocks


# --- the manifest ------------------------------------------------------------------


def manifest_document(selection, files, blocks, base, seed, workbench_version):
    entries = []
    for path in files.order:
        item = files.items[path]
        original = item["data"]
        if item["blocks"]:
            original = without_blocks(original)
        entries.append({"class": item["class"], "hash": _sha(original), "path": path})
    entries.extend(blocks)
    entries.sort(key=lambda e: (e["path"].encode("utf-8"), e.get("block", "")))
    by_package = collections.defaultdict(list)
    for verified in selection.modules:
        if verified.type != "harness":
            by_package[verified.package].append({
                "declaration": verified.declaration_hash, "name": verified.name,
                "tree": verified.tree_hash, "version": verified.version})
    packages = []
    for source in sorted(selection.packages, key=lambda p: p.name):
        if source.name in by_package:
            packages.append({
                "commit": source.commit, "modules": sorted(by_package[source.name],
                                                           key=lambda m: m["name"]),
                "name": source.name, "ref": source.ref, "source": public_source(source.source),
                "tree": source.tree})
    return {"base": base.tree_hash, "files": entries, "packages": packages, "seed": seed,
            "version": manifest.VERSION, "workbench": workbench_version}


def without_blocks(data):
    """The file with every BEGIN/END block removed: what the base or module supplied."""
    out = []
    inside = False
    for line in data.split(b"\n"):
        if line.startswith(b"<!-- BEGIN "):
            inside = True
            continue
        if inside:
            if line.startswith(b"<!-- END "):
                inside = False
            continue
        out.append(line)
    return b"\n".join(out)


# --- the plan ------------------------------------------------------------------------


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False)


def digest_of(fields):
    """SHA-256 (hex) of the canonical JSON of the plan's fields, a dict with explicit names."""
    return hashlib.sha256(_json(fields).encode("ascii")).hexdigest()


def json_store(document):
    return (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def build(target, selection, snapshots, base, seed, workbench_version):
    """Build the whole plan. Raises PlanError; nothing is read or written."""
    if target.state == "existing":
        raise PlanError("the target is an existing project; use upgrade or add a module")
    try:
        project = manifest.project_id(seed)
    except manifest.ManifestError as exc:
        raise PlanError(str(exc))
    files, blocks = assemble(selection, snapshots, base)
    document = manifest_document(selection, files, blocks, base, seed, workbench_version)
    try:
        manifest_bytes = manifest.serialize(document)
    except manifest.ManifestError as exc:
        raise PlanError("the manifest cannot be written: %s" % exc)
    files.add(".workbench/manifest.json", manifest_bytes, "module-owned", False, BASE_ORIGIN)

    paths = [MARKER_PATH] + files.order
    try:
        safefs.check_tree_paths(paths)
    except safefs.SafeFsError as exc:
        raise PlanError(str(exc))

    git_init = target.state in ("new-missing", "new-empty")
    actions = []
    if target.state == "new-missing":
        actions.append(Action("make-target", ".", "scratch", "-", 0, "", "", None))
    actions.append(_file_action(MARKER_PATH, b"", "scratch", False, "install marker"))
    if git_init:
        actions.append(Action("git-init", ".git", "scratch", "-", _skeleton_size(),
                              _skeleton_hash(), GIT_DETAIL, None))
    made = {".workbench", ".workbench/local"}
    for directory in sorted({"/".join(p.split("/")[:n]) for p in files.order
                             for n in range(1, len(p.split("/")))} - made):
        actions.append(Action("create-dir", directory, "scratch", "-", 0, "", "", None))
    for path in files.order:
        item = files.items[path]
        detail = ", ".join("%s slot:%s" % (who, slot) for slot, who in item["blocks"])
        actions.append(_file_action(path, item["data"], item["class"], item["x"],
                                    ("with blocks: " + detail) if detail else ""))

    baselines = {a.path: a.hash for a in actions
                 if a.kind == "create-file" and a.path != MARKER_PATH}
    store_writes = (
        ("projects/%s/baselines" % project, json_store({"baselines": baselines, "format": 1})),
        ("projects/%s/seen" % project, json_store(
            {"format": 1, "kind": "path", "value": target.path})),
    )
    modules = tuple({
        "declaration": v.declaration_hash, "name": v.name, "package": v.package,
        "tree": v.tree_hash, "type": v.type, "version": v.version} for v in selection.modules)
    sources = tuple({"commit": s.commit, "name": s.name, "ref": s.ref,
                     "source": public_source(s.source), "tree": s.tree}
                    for s in sorted(selection.packages, key=lambda p: p.name))
    fields = {
        "command": "install",
        "target": {"device": target.identity[0], "inode": target.identity[1],
                   "state": target.state},
        "workbench": workbench_version, "base": base.tree_hash,
        "modules": list(modules), "packages": list(sources),
        "seed": seed, "project_id": project, "git_init": git_init,
        "actions": [{"kind": a.kind, "path": a.path, "class": a.owner_class, "mode": a.mode,
                     "size": a.size, "hash": a.hash, "detail": a.detail} for a in actions],
        "store_writes": [{"path": p, "hash": _sha(d)} for p, d in store_writes],
    }
    return Plan(target.identity, target.state, tuple(actions), modules, document, seed,
                project, store_writes, git_init, digest_of(fields))


def _skeleton_size():
    return sum(len(data) for _, data in GIT_SKELETON if data is not None)


def _skeleton_hash():
    return _sha(_json([[path, None if data is None else _sha(data)]
                       for path, data in GIT_SKELETON]).encode("ascii"))


def _file_action(path, data, owner_class, executable, detail):
    return Action("create-file", path, owner_class, "x" if executable else "-", len(data),
                  _sha(data), detail, data)


# --- the preview text --------------------------------------------------------------------


def _show(text):
    return display.ascii_text(str(text).replace("\\", "\\\\"))


def render(plan, target_path, show_digest=False):
    """The preview text. Every name, path and package-supplied string is ASCII-escaped."""
    lines = ["target: %s" % _show(target_path), "command: install",
             "state: %s" % plan.state]
    counts = collections.Counter(a.kind for a in plan.actions)
    summary = ", ".join("%d %s" % (counts[k], k) for k in
                        ("make-target", "create-dir", "create-file", "git-init") if counts[k])
    lines.append("summary: %s; %d store writes" % (summary, len(plan.store_writes)))
    flags = ["%s module %s/%s" % (m["type"], _show(m["package"]), _show(m["name"]))
             for m in plan.modules if m["type"] in ("harness", "process")]
    if flags:
        lines.append("high risk: " + "; ".join(flags))
    lines.append("modules:")
    for m in plan.modules:
        lines.append("  %s/%s %s (%s)" % (_show(m["package"]), _show(m["name"]),
                                           _show(m["version"]), m["type"]))
        lines.append("    declaration %s" % m["declaration"])
        lines.append("    tree %s" % m["tree"])
    for package in plan.manifest["packages"]:
        lines.append("  package %s from %s" % (_show(package["name"]), _show(package["source"])))
    lines.append("actions:")
    for a in plan.actions:
        row = "  %s %s" % (a.kind, _show(a.path))
        if a.kind == "create-file":
            row += " [%s] %s %d bytes sha256 %s" % (a.owner_class, a.mode, a.size, a.hash)
        if a.detail:
            row += " (%s)" % _show(a.detail)
        lines.append(row)
    lines.append("guarded store:")
    for path, data in plan.store_writes:
        lines.append("  write %s sha256 %s" % (path, _sha(data)))
    if plan.git_init:
        lines.append("git: creates %s" % GIT_DETAIL)
    else:
        lines.append("git: an existing .git is used as it is; no remote is recorded")
    lines.append("harness: not attached (attach is not built yet)")
    if show_digest:
        lines.append("digest: %s" % plan.digest)
    return "\n".join(lines) + "\n"
