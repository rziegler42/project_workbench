"""What an existing project holds now, read without trusting it.

``read`` parses ``.workbench/manifest.json`` with the strict reader, applies the version rule, and
looks at the file or block behind every manifest entry. The manifest is untrusted text: it says
what was installed and with which hashes, and it is compared with the disk, never believed about
it. Nothing here writes, and nothing follows a link.

The state of an entry:

* ``as-installed`` the file (with its recorded blocks taken out) or the block is as it was written;
* ``edited`` it is there and different;
* ``missing`` the file is not there;
* ``gone`` a block whose markers are no longer in the file (the file is there);
* ``unreadable`` it cannot be read as a plain file, or its markers cannot be scanned. The
  ``detail`` says why, so a hostile file is reported by name and is not an exception.

A file entry whose path also holds recorded blocks is hashed with those blocks taken out, which is
what the manifest recorded. Blocks that are not recorded stay in the bytes, so they show as an
edit.

The workbench version rule (``installer-interface.md``): dotted decimal numbers compared
numerically, trailing zero parts ignored. A project written by a higher version, or a version of
either side that is not dotted decimal, is refused.
"""

import collections
import hashlib
import re

from . import blocks, display, manifest, projectfs, safefs

MANIFEST = ".workbench/manifest.json"
LOCAL = ".workbench/local"

AS_INSTALLED = "as-installed"
EDITED = "edited"
MISSING = "missing"
GONE = "gone"
UNREADABLE = "unreadable"

_VERSION = re.compile(r"\A[0-9]{1,9}(\.[0-9]{1,9}){0,7}\Z")

# One manifest entry and what is on disk behind it. `block` is the block id for a slot block and
# None for a file; `hash` is the recorded hash; `current` is the hash found now, or None.
Entry = collections.namedtuple("Entry", "path block owner_class hash state current detail")
Installed = collections.namedtuple("Installed", "document manifest_hash entries")


class InstalledError(Exception):
    """The project cannot be read as an installed project; nothing is changed."""


def version_key(text):
    """The comparable form of a dotted decimal version, or raise InstalledError."""
    if not isinstance(text, str) or not _VERSION.match(text):
        raise InstalledError("the workbench version %s is not a dotted decimal number"
                             % display.ascii_text(str(text))[:40])
    parts = [int(part) for part in text.split(".")]
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def check_version(recorded, running):
    """Refuse a project written by a higher workbench version than the one running."""
    if version_key(recorded) > version_key(running):
        raise InstalledError("the project was written by workbench %s, which is newer than %s"
                             % (display.ascii_text(recorded)[:40], display.ascii_text(running)[:40]))


def _read_manifest(held):
    try:
        state = held.read_file(MANIFEST)
    except safefs.SafeFsError as exc:
        raise InstalledError("the manifest cannot be read: %s" % exc)
    if state is None:
        raise InstalledError("the project has no manifest")
    try:
        document = manifest.parse(state.data)
    except manifest.ManifestError as exc:
        raise InstalledError("the manifest is not valid: %s" % exc)
    return document, state.hash


def _check_paths(document):
    paths = [item["path"] for item in document["files"]]
    try:
        safefs.check_tree_paths(sorted(set(paths)))
    except safefs.SafeFsError as exc:
        raise InstalledError("the manifest names paths that cannot all be written: %s" % exc)
    for path in paths:
        if path == MANIFEST or path == LOCAL or path.startswith(LOCAL + "/"):
            raise InstalledError("the manifest names a path it may not: %s"
                                 % display.ascii_text(path)[:80])


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _strip(data, scan, wanted):
    """`data` with the recorded blocks (those whose (id, slot) is in `wanted`) taken out."""
    out, at = [], 0
    for block in scan.blocks:
        if (block.id, block.slot) in wanted:
            out.append(data[at:block.start])
            at = block.end
    out.append(data[at:])
    return b"".join(out)


def _look(held, path):
    """(FileState or None, detail): `detail` is non-empty when the path is unreadable."""
    try:
        return held.read_file(path), ""
    except projectfs.WriteConflict:
        return None, "not a regular file, or a link on the way"
    except safefs.SafeFsError as exc:
        return None, display.ascii_text(str(exc))[:120]


def read(held, workbench_version):
    """The ``Installed`` view of the project behind `held`, a ``projectfs.Writer``."""
    document, manifest_hash = _read_manifest(held)
    check_version(document["workbench"], workbench_version)
    _check_paths(document)

    by_path = collections.OrderedDict()
    for item in document["files"]:
        by_path.setdefault(item["path"], []).append(item)

    entries = []
    for path, items in by_path.items():
        found, problem = _look(held, path)
        recorded = {(item["block"], item["slot"]) for item in items if "block" in item}
        scan, scan_problem = None, ""
        if found is not None and recorded:
            try:
                scan = blocks.scan(found.data)
            except blocks.BlockError as exc:
                scan_problem = "the slot markers cannot be read: %s" % display.ascii_text(
                    str(exc))[:100]
        for item in items:
            block_id = item.get("block")
            entries.append(_entry(path, item, block_id, found, problem, scan, scan_problem,
                                  recorded))
    entries.sort(key=lambda e: (e.path.encode("utf-8"), e.block or ""))
    return Installed(document, manifest_hash, tuple(entries))


def _entry(path, item, block_id, found, problem, scan, scan_problem, recorded):
    def make(state, current=None, detail=""):
        return Entry(path, block_id, item["class"], item["hash"], state, current, detail)

    if problem:
        return make(UNREADABLE, detail=problem)
    if found is None:
        return make(MISSING)
    if block_id is None:
        if not recorded:
            current = found.hash
        elif scan_problem:
            return make(UNREADABLE, detail=scan_problem)
        else:
            current = _sha(_strip(found.data, scan, recorded))
        return make(AS_INSTALLED if current == item["hash"] else EDITED, current)
    if scan_problem:
        return make(UNREADABLE, detail=scan_problem)
    mine = [b for b in scan.blocks if b.id == block_id and b.slot == item["slot"]]
    if not mine:
        return make(GONE)
    current = _sha(mine[0].text)
    return make(AS_INSTALLED if current == item["hash"] else EDITED, current)
