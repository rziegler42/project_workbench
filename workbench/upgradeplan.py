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
    "UpgradePlan", "mode rows writes document manifest_bytes baselines")


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
        self.rows.append(Row(kind, path, block, slot, owner_class,
                             display.ascii_text(detail)[:200]))

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
    if _sha(manifest_bytes) != existing.manifest_hash:
        writes.append(Write("replace", MANIFEST, manifest_bytes, existing.manifest_hash,
                            _sha(manifest_bytes), False))
        work.row(REPLACE, MANIFEST, owner_class="module-owned",
                 detail="records this upgrade")
    new_baselines = dict(baselines)
    for w in writes:
        new_baselines[w.path] = w.hash
    rows = sorted(work.rows, key=lambda r: _key(r.path, r.block))
    return UpgradePlan(mode, tuple(rows), tuple(writes), document, manifest_bytes,
                       new_baselines)
