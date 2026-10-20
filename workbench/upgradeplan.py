"""The upgrade plan: what an upgrade of an existing project would do, classified, and nothing else.

``build`` is a function of the project as it is now (``installed.read``, the baselines and a
read-only reader), the approved modules and the base. It writes nothing. It returns every
decision as a row, the file writes those decisions come to, the new manifest and the new
baselines. ``wb preview upgrade`` and ``wb upgrade`` call it with the same inputs.

The write set is the one an install of the same modules would write (``installplan.assemble``):
the base, each module's namespace, its ``writes`` and its slot ``fills``. The manifest never widens
it. The manifest supplies the installed hashes and nothing else, and its class for a path is
compared with the declared class, never believed. Each path of the desired state is classified
against its manifest entry and the disk (``repository-boundary.md``, "Classification on upgrade"):

* ``create`` there is no entry and nothing on disk; a block is inserted before its slot's marker;
* ``append`` a block whose slot has no marker in the file; the block and then the marker are added
  at the end;
* ``replace`` a module-owned file or a block that is as it was installed and now differs;
* ``skip`` nothing to do: unchanged, a seeded file (never touched), a block whose markers are gone
  ("slot gone"), or an entry with no counterpart ("left in place");
* ``conflict`` it is not the installer's to write: the path exists and is not recorded, the project
  edited or removed it, the class or slot differs, or the file cannot be read.

Nothing is deleted. A conflict and a skip keep the old manifest entry as it was, so the next
upgrade sees the same difference and a block the project removed is never put back. A file that
receives blocks is written once, whole, with the hash of the bytes read here as the one it must
still have. The manifest keeps the hash it recorded for a seeded file, whatever blocks it
receives, so a file the project has changed still reads as edited; that is a seeded file's normal
state. The caller refuses unless each such file equals its baseline
(``acknowledgement.differences(..., writes=written_paths(plan))``).
"""

import collections
import copy
import hashlib

from . import base as base_module
from . import blocks, display, installed, installplan, manifest, safefs

MODES = ("upgrade", "add")
MANIFEST = installed.MANIFEST

CREATE = "create"
APPEND = "append"
REPLACE = "replace"
SKIP = "skip"
CONFLICT = "conflict"

# `block` and `slot` are set for a slot block. `detail` says why for a skip or a conflict.
Row = collections.namedtuple("Row", "kind path block slot owner_class detail")
# `op` is "create" or "replace"; `expected` is the hash the file must still have for a replace.
Write = collections.namedtuple("Write", "op path data expected hash executable")
UpgradePlan = collections.namedtuple(
    "UpgradePlan", "mode rows writes dirs document manifest_bytes baselines")


class UpgradeError(Exception):
    """The upgrade cannot be planned. The message names the module or path."""


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _key(path, block):
    return (path.encode("utf-8"), block or "")


def written_paths(plan):
    """The project paths the plan writes, the manifest included."""
    return [w.path for w in plan.writes]


class _Build:
    def __init__(self, existing, reader):
        self.reader = reader
        self.rows = []
        self.writes = []
        self.document = copy.deepcopy(existing.document)
        self.record = {(e["path"], e.get("block", "")): e for e in self.document["files"]}
        self.files = {e.path: e for e in existing.entries if e.block is None}
        self.blocks = {(e.path, e.block): e for e in existing.entries if e.block is not None}
        self.matched = set()
        self.work = {}          # path -> [FileState or None, current bytes, why not]
        self.edited = collections.defaultdict(list)    # path -> [(who, slot, hash)]

    # --- helpers -------------------------------------------------------------------------

    def row(self, kind, path, block=None, slot=None, owner_class="", detail=""):
        self.rows.append(Row(kind, path, block, slot, owner_class, detail[:200]))

    def set_entry(self, path, owner_class, digest, block=None, slot=None):
        item = {"class": owner_class, "hash": digest, "path": path}
        if block is not None:
            item["block"], item["slot"] = block, slot
        self.record[(path, block or "")] = item

    def load(self, path):
        if path not in self.work:
            found, problem = installed.look(self.reader, path)
            if found is None:
                self.work[path] = [None, b"", problem or "the file is not there"]
            else:
                self.work[path] = [found, found.data, ""]
        return self.work[path]

    # --- files ---------------------------------------------------------------------------

    def file(self, path, item):
        """Classify one desired file. Returns "created", "entry" or "none" for its blocks."""
        owner = item["class"]
        original = installplan.without_blocks(item["data"]) if item["blocks"] else item["data"]
        digest = _sha(original)
        entry = self.files.get(path)
        if entry is None:
            found, problem = installed.look(self.reader, path)
            if problem:
                self.row(CONFLICT, path, owner_class=owner, detail=problem)
            elif found is not None:
                self.row(CONFLICT, path, owner_class=owner,
                         detail="it exists and the manifest does not record it")
            else:
                self.writes.append(Write("create", path, item["data"], None, _sha(item["data"]),
                                         item["x"]))
                self.set_entry(path, owner, digest)
                self.row(CREATE, path, owner_class=owner, detail=(
                    "with blocks: " + ", ".join("%s slot:%s" % (who, slot)
                                                for slot, who in item["blocks"])
                    if item["blocks"] else ""))
                return "created"
            return "none"
        self.matched.add((path, ""))
        if entry.owner_class != owner:
            self.row(CONFLICT, path, owner_class=owner, detail=(
                "the manifest records it as %s, the declaration says %s"
                % (entry.owner_class, owner)))
        elif owner == "seeded":
            self.row(SKIP, path, owner_class=owner, detail=(
                "" if digest == entry.hash else "a newer version exists; the project's file is "
                                                "not touched"))
        elif digest == entry.hash:
            self.row(SKIP, path, owner_class=owner)
        elif entry.state == installed.AS_INSTALLED:
            self.writes.append(Write("replace", path, item["data"], entry.current,
                                     _sha(item["data"]), item["x"]))
            self.set_entry(path, owner, digest)
            self.row(REPLACE, path, owner_class=owner)
        else:
            self.row(CONFLICT, path, owner_class=owner, detail=_why(entry))
        return "entry"

    # --- blocks --------------------------------------------------------------------------

    def block(self, path, item, slot, who, holder):
        """Classify one desired block. `holder` is "created", or the file's installed entry
        (None when the manifest has none)."""
        text, body = item["texts"][(who, slot)]
        digest = _sha(text)
        entry = self.blocks.get((path, who))

        def say(kind, detail=""):
            self.row(kind, path, who, slot, "slot block", detail)

        if entry is not None:
            self.matched.add((path, who))
        if holder == "created":
            self.set_entry(path, "slot block", digest, who, slot)
            say(CREATE, "in the new file")
            return
        if entry is not None:
            if entry.slot != slot or entry.owner_class != "slot block":
                say(CONFLICT, "the manifest records it in slot %s as %s"
                    % (entry.slot, entry.owner_class))
            elif entry.state == installed.GONE:
                say(SKIP, "slot gone")
            elif entry.state != installed.AS_INSTALLED:
                say(CONFLICT, _why(entry))
            elif entry.hash == digest:
                say(SKIP)
            elif _holder_problem(holder):
                say(CONFLICT, _holder_problem(holder))
            else:
                self.edit(path, who, slot, body, digest, blocks.replace, REPLACE, say)
            return
        if _holder_problem(holder):
            say(CONFLICT, _holder_problem(holder))
        else:
            self.place(path, who, slot, body, digest, say)

    def place(self, path, who, slot, body, digest, say):
        work = self.load(path)
        if work[0] is None:
            say(CONFLICT, work[2])
            return
        try:
            where = blocks.slot_state(work[1], slot, who)
        except blocks.BlockError as exc:
            say(CONFLICT, "the slot markers cannot be read: %s" % exc)
            return
        if where == blocks.PRESENT:
            say(CONFLICT, "the block is in the file and the manifest does not record it")
        elif where == blocks.OPEN:
            self.edit(path, who, slot, body, digest, blocks.insert, CREATE, say)
        else:
            self.edit(path, who, slot, body, digest, blocks.append, APPEND, say,
                      "the slot has no marker; the block and the marker are added at the end")

    def edit(self, path, who, slot, body, digest, operation, kind, say, detail=""):
        work = self.load(path)
        if work[0] is None:
            say(CONFLICT, work[2])
            return
        try:
            work[1] = operation(work[1], who, slot, body)
        except blocks.BlockError as exc:
            say(CONFLICT, "the slot markers cannot be edited: %s" % exc)
            return
        self.edited[path].append((who, slot, digest))
        self.set_entry(path, "slot block", digest, who, slot)
        say(kind, detail)

    def finish_files(self):
        for path, edits in sorted(self.edited.items()):
            state, data, _ = self.work[path]
            found = {(b.id, b.slot): b for b in blocks.scan(data).blocks}
            for who, slot, digest in edits:
                if (who, slot) not in found or _sha(found[(who, slot)].text) != digest:
                    raise UpgradeError("%s: the block %s slot:%s does not come out as the "
                                       "declaration gives it" % (path, who, slot))
            self.writes.append(Write("replace", path, data, state.hash, _sha(data), False))

    def left_in_place(self):
        for entry in self.files.values():
            if (entry.path, "") in self.matched:
                continue
            if entry.owner_class == "module-owned" and not entry.path.startswith(".workbench/"):
                self.row(CONFLICT, entry.path, owner_class=entry.owner_class,
                         detail="recorded as module-owned outside .workbench; never written")
            else:
                self.row(SKIP, entry.path, owner_class=entry.owner_class, detail="left in place")
        for entry in self.blocks.values():
            if (entry.path, entry.block) not in self.matched:
                self.row(SKIP, entry.path, entry.block, entry.slot, entry.owner_class,
                         "left in place")


def _holder_problem(holder):
    """Why the file a block would be written into may not be written, or "" when it may: the
    manifest must record it as a seeded file that is there and can be read. This holds for every
    edit, whether or not the block has an entry of its own."""
    if holder is None:
        return "the file is not recorded by the manifest"
    if holder.owner_class != "seeded":
        return "the manifest records the file as %s" % holder.owner_class
    if holder.state == installed.MISSING:
        return "the file was removed by the project; not restored"
    if holder.state == installed.UNREADABLE:
        return _why(holder)
    return ""


def _why(entry):
    if entry.state == installed.EDITED:
        return "edited by the project"
    if entry.state == installed.MISSING:
        return "removed by the project; not restored"
    if entry.state == installed.GONE:
        return "the markers are gone"
    return entry.detail or "it cannot be read"


def _new_dirs(reader, writes):
    """The directories a create would have to make, parents first, each once."""
    missing = set()
    for w in writes:
        if w.op != "create":
            continue
        parts = w.path.split("/")[:-1]
        for n in range(1, len(parts) + 1):
            prefix = "/".join(parts[:n])
            if prefix in missing:
                continue
            try:
                if reader.list_dir(prefix) is None:
                    missing.add(prefix)
            except safefs.SafeFsError as exc:
                raise UpgradeError("%s cannot be made: %s" % (display.ascii_text(prefix)[:80],
                                                              exc))
    return sorted(missing, key=lambda d: d.encode("utf-8"))


def _merge_packages(new, old, selected):
    """The new package records, plus the modules of the old ones that are no longer selected, so
    the manifest still says who owns the entries that are left in place."""
    merged = {p["name"]: p for p in new}
    for package in old:
        kept = [copy.deepcopy(m) for m in package["modules"]
                if (package["name"], m["name"]) not in selected]
        if not kept:
            continue
        if package["name"] in merged:
            target = merged[package["name"]]
            target["modules"] = sorted(target["modules"] + kept, key=lambda m: m["name"])
        else:
            merged[package["name"]] = dict(copy.deepcopy(package), modules=kept)
    return [merged[name] for name in sorted(merged)]


def build(existing, reader, baselines, selection, snapshots, base, workbench_version, mode):
    """Plan an upgrade (or an add) of the project `existing` (an ``installed.Installed``).

    `reader` has ``read_file`` (a ``projectfs.Writer``); `baselines` is the acknowledgement
    ``{path: sha256}``. Raises UpgradeError. Reads the project; writes nothing."""
    if mode not in MODES:
        raise UpgradeError("the mode is upgrade or add")
    try:
        installed.check_version(existing.document["workbench"], workbench_version)
    except installed.InstalledError as exc:
        raise UpgradeError(str(exc))
    try:
        files, fills = installplan.assemble(selection, snapshots, base)
    except installplan.PlanError as exc:
        raise UpgradeError(str(exc))
    work = _Build(existing, reader)
    for path in files.order:
        item = files.items[path]
        holder = work.file(path, item)
        if item["blocks"]:
            holder = "created" if holder == "created" else work.files.get(path)
            for slot, who in item["blocks"]:
                work.block(path, item, slot, who, holder)
    work.finish_files()
    work.left_in_place()

    if mode == "add":
        for row in work.rows:
            if row.kind == REPLACE:
                raise UpgradeError("add never replaces: %s differs from what is installed; "
                                   "use upgrade" % display.ascii_text(row.path)[:80])

    document = installplan.manifest_document(selection, files, fills, base,
                                             existing.document["seed"], workbench_version)
    selected = {(v.package, v.name) for v in selection.modules if v.type != "harness"}
    document["packages"] = _merge_packages(document["packages"], existing.document["packages"],
                                           selected)
    document["files"] = sorted(work.record.values(),
                               key=lambda e: _key(e["path"], e.get("block")))
    try:
        manifest_bytes = manifest.serialize(document)
    except manifest.ManifestError as exc:
        raise UpgradeError("the manifest cannot be written: %s" % exc)
    try:
        safefs.check_tree_paths(sorted(set(files.order) | {e["path"] for e in document["files"]}
                                       | {MANIFEST}))
    except safefs.SafeFsError as exc:
        raise UpgradeError(str(exc))
    writes = sorted(work.writes, key=lambda w: _key(w.path, None))
    dirs = _new_dirs(reader, writes)
    if _sha(manifest_bytes) != existing.manifest_hash:
        writes.append(Write("replace", MANIFEST, manifest_bytes, existing.manifest_hash,
                            _sha(manifest_bytes), False))
        work.row(REPLACE, MANIFEST, owner_class="module-owned",
                 detail="records this upgrade")
    new_baselines = dict(baselines)
    for w in writes:
        new_baselines[w.path] = w.hash
    rows = sorted(work.rows, key=lambda r: _key(r.path, r.block))
    return UpgradePlan(mode, tuple(rows), tuple(writes), tuple(dirs), document, manifest_bytes,
                       new_baselines)


# --- the digest and the preview text -----------------------------------------------------------


def store_writes(plan):
    """The guarded-store writes of an upgrade: ``((path, bytes),)``. Only the baselines change;
    the first-seen record is already there."""
    project = manifest.project_id(plan.document["seed"])
    return (("projects/%s/baselines" % project,
             installplan.json_store({"baselines": plan.baselines, "format": 1})),)


def _changes(existing, selection):
    """Each selected module with what its declaration did since it was installed."""
    old = {(p["name"], m["name"]): m for p in existing.document["packages"] for m in p["modules"]}
    out = []
    for v in selection.modules:
        before = old.get((v.package, v.name))
        record = {"declaration": v.declaration_hash, "name": v.name, "package": v.package,
                  "tree": v.tree_hash, "type": v.type, "version": v.version}
        if v.type == "harness":
            change = {"kind": "not recorded"}
        elif before is None:
            change = {"kind": "new"}
        elif (before["declaration"], before["tree"], before["version"]) == (
                v.declaration_hash, v.tree_hash, v.version):
            change = {"kind": "unchanged"}
        else:
            change = {"kind": "changed", "declaration": before["declaration"],
                      "tree": before["tree"], "version": before["version"]}
        record["change"] = change
        out.append(record)
    return out


def digest_fields(plan, existing, selection, identity):
    """Every field the owner approves, with explicit names. `identity` is the target's
    (device, inode). The workbench version is the one the new manifest records. The hash of each
    write is taken from its bytes, and a write whose recorded hash is not that is refused."""
    for w in plan.writes:
        if w.hash != _sha(w.data):
            raise UpgradeError("the write of %s does not match its hash"
                               % display.ascii_text(w.path)[:80])
    return {
        "command": plan.mode,
        "target": {"device": identity[0], "inode": identity[1]},
        "workbench": plan.document["workbench"], "recorded_workbench": existing.document["workbench"],
        "base": plan.document["base"], "manifest_before": existing.manifest_hash,
        "manifest_after": _sha(plan.manifest_bytes),
        "modules": _changes(existing, selection),
        "packages": plan.document["packages"],
        "rows": [{"kind": r.kind, "path": r.path, "block": r.block, "slot": r.slot,
                  "class": r.owner_class, "detail": r.detail} for r in plan.rows],
        "directories": list(plan.dirs),
        "writes": [{"op": w.op, "path": w.path, "mode": "x" if w.executable else "-",
                    "size": len(w.data), "hash": _sha(w.data), "expected": w.expected}
                   for w in plan.writes],
        "baselines": plan.baselines,
        "store_writes": [{"path": p, "hash": _sha(d)} for p, d in store_writes(plan)],
    }


def digest(plan, existing, selection, identity):
    return installplan.digest_of(digest_fields(plan, existing, selection, identity))


def _show(text):
    return display.ascii_text(str(text).replace("\\", "\\\\"))


def render(plan, existing, selection, target_path, identity, show_digest=False, approvals=None):
    """The preview text. Every name, path and package-supplied string is ASCII-escaped, and no
    existing file's content is printed, only hashes and reasons."""
    counts = collections.Counter(r.kind for r in plan.rows)
    lines = ["target: %s" % _show(target_path), "command: %s" % plan.mode, "state: existing",
             "workbench: %s (the project records %s)" % (
                 _show(plan.document["workbench"]), _show(existing.document["workbench"])),
             "summary: " + ", ".join("%d %s" % (counts[k], k) for k in
                                     (CREATE, APPEND, REPLACE, SKIP, CONFLICT) if counts[k])
             + "; %d file writes; %d store writes" % (len(plan.writes), len(store_writes(plan)))]
    changes = _changes(existing, selection)
    flags = ["%s module %s/%s" % (m["type"], _show(m["package"]), _show(m["name"]))
             for m in changes if m["type"] in ("harness", "process")]
    if flags:
        lines.append("high risk: " + "; ".join(flags))
    lines.append("modules:")
    for m in changes:
        change = m["change"]
        lines.append("  %s/%s %s (%s): %s" % (_show(m["package"]), _show(m["name"]),
                                              _show(m["version"]), m["type"], change["kind"]))
        lines.append("    declaration %s" % m["declaration"])
        lines.append("    tree %s" % m["tree"])
        found = (approvals or {}).get((m["package"], m["name"]))
        if found:
            lines.append("    approved by the %s record (%s)" % (_show(found[0]), _show(found[1])))
        if change["kind"] == "changed":
            lines.append("    was: version %s, declaration %s, tree %s" % (
                _show(change["version"]), change["declaration"], change["tree"]))
    was = {p["name"]: p for p in existing.document["packages"]}
    for package in plan.document["packages"]:
        lines.append("  package %s from %s" % (_show(package["name"]), _show(package["source"])))
        old = was.get(package["name"])
        if old is not None and (old["source"], old["ref"], old["commit"]) != (
                package["source"], package["ref"], package["commit"]):
            lines.append("    source changed from %s ref %s commit %s" % (
                _show(old["source"]), _show(old["ref"] or "(none)"),
                _show(old["commit"] or "(none)")))
    lines.append("paths:")
    for r in plan.rows:
        who = "" if r.block is None else " block %s slot:%s" % (_show(r.block), _show(r.slot))
        row = "  %s %s%s [%s]" % (r.kind, _show(r.path), who, r.owner_class or "-")
        if r.detail:
            row += " (%s)" % _show(r.detail)
        lines.append(row)
    if plan.dirs:
        lines.append("directories:")
        lines.extend("  create-dir %s" % _show(d) for d in plan.dirs)
    lines.append("file writes:")
    for w in plan.writes:
        row = "  %s %s %s %d bytes sha256 %s" % (w.op, _show(w.path), "x" if w.executable else "-",
                                                 len(w.data), w.hash)
        if w.expected:
            row += " (now %s)" % w.expected
        lines.append(row)
    appends = [r for r in plan.rows if r.kind == APPEND]
    if appends:
        lines.append("appended blocks (if you decline one, add this marker line where the block "
                     "should go instead):")
        for r in appends:
            lines.append("  %s: %s  for block %s" % (_show(r.path), base_module.marker(r.slot),
                                                      _show(r.block)))
    lines.append("guarded store:")
    for path, data in store_writes(plan):
        lines.append("  replace %s sha256 %s" % (path, _sha(data)))
    lines.append("git: not run; nothing is committed")
    if show_digest:
        lines.append("digest: %s" % digest(plan, existing, selection, identity))
    return "\n".join(lines) + "\n"
