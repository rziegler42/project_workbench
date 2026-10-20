"""The record an unfinished write leaves in its marker ``.workbench/local/incomplete``.

``install``, ``upgrade`` and ``add`` write the marker first and remove it last. The marker holds
a strict JSON record of the plan being written: the command, the project id when known, the
workbench version, each file write (path, operation, the hash the file had before and the hash it
will have after), each directory the plan creates, the files of the ``.git`` skeleton with the
hash each will have, and each guarded-store write with the hash it will have. It is built after
the plan's digest is fixed from the same plan, so it never changes that digest.

The record is untrusted text, like the manifest: anyone who can write the project can edit it,
and it carries no authority. ``parse`` accepts nothing but the form ``build`` writes, bounded as
the manifest is, with the manifest's path rules. A marker that is empty (made by an earlier
version) or does not parse is "no record" and is never trusted.
"""

import collections
import hashlib
import json
import os
import re
import unicodedata

from . import declarations, display, projectfs, safefs, store as store_module

FORMAT = 1
MAX_ENTRIES = 10000          # files, directories, .git entries and store entries together
COMMANDS = ("install", "upgrade", "add")
OPERATIONS = ("create", "replace")
_LOCAL = (".workbench", "local")

_HEX64 = re.compile(r"^[0-9a-f]{64}\Z")
_WORKBENCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}\Z")

TOP_KEYS = ("command", "dirs", "files", "format", "git", "project", "store", "workbench")
FILE_KEYS = ("after", "before", "op", "path")
GIT_KEYS = ("hash", "path")
STORE_KEYS = ("after", "before", "path")

FileWrite = collections.namedtuple("FileWrite", "path op before after")
GitEntry = collections.namedtuple("GitEntry", "path hash")
StoreWrite = collections.namedtuple("StoreWrite", "path before after")
Record = collections.namedtuple("Record", "command project workbench dirs files git store")


class UnfinishedError(Exception):
    """The record cannot be built, or the marker's content is not a valid record."""


def sha(data):
    return hashlib.sha256(data).hexdigest()


# --- shape ---------------------------------------------------------------------


def _fail(what):
    raise UnfinishedError(what)


def _keys(item, expected, what):
    if not isinstance(item, dict) or set(item) != set(expected):
        _fail("%s has the wrong keys" % what)


def _hex(value, what, allow_none=False):
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not _HEX64.match(value):
        _fail("%s is not a SHA-256 in lowercase hex" % what)
    return value


def _fold(path):
    """The segments of `path` as a case-insensitive filesystem that also ignores trailing dots
    and spaces (Windows) and normalizes Unicode would compare them."""
    return tuple(unicodedata.normalize("NFC", part).rstrip(" .").casefold()
                 for part in path.split("/"))


def _project_path(value, what):
    """A project path under the manifest's rules, and never inside the local directory, however
    its case or spelling is varied."""
    try:
        safefs.validate_relpath(value)
    except safefs.SafeFsError as exc:
        _fail("%s: %s" % (what, exc))
    if _fold(value)[:len(_LOCAL)] == _LOCAL:
        _fail("%s is inside %s" % (what, "/".join(_LOCAL)))
    return value


def _git_path(value):
    """A path below ``.git``. The path rules refuse ``.git`` itself, so the rest is checked
    under a stand-in parent."""
    if not isinstance(value, str):
        _fail("a .git path is not text")
    try:
        safefs.validate_relpath("git/" + value)
    except safefs.SafeFsError as exc:
        _fail("a .git path: %s" % exc)
    return value


def _list(value, what):
    if not isinstance(value, list):
        _fail("%s is not a list" % what)
    if len(value) > MAX_ENTRIES:
        _fail("%s has more than %d entries" % (what, MAX_ENTRIES))
    return value


def _unique(paths, what):
    """No entry repeats, ignoring case and spelling."""
    if len({_fold(path) for path in paths}) != len(paths):
        _fail("%s repeat an entry" % what)


def _check_files(items):
    files = []
    for item in _list(items, "files"):
        _keys(item, FILE_KEYS, "a file entry")
        op = item["op"]
        if op not in OPERATIONS:
            _fail("a file entry has an unknown operation")
        before = _hex(item["before"], "a before hash", allow_none=True)
        if (op == "create") != (before is None):
            _fail("a file entry's before hash does not fit its operation")
        files.append(FileWrite(_project_path(item["path"], "a file path"), op, before,
                               _hex(item["after"], "an after hash")))
    _unique([f.path for f in files], "files")
    return tuple(files)


def _check_dirs(items):
    dirs = tuple(_project_path(item, "a directory path") for item in _list(items, "dirs"))
    _unique(dirs, "directories")
    return dirs


def _check_git(items):
    git = []
    for item in _list(items, "git"):
        _keys(item, GIT_KEYS, "a .git entry")
        git.append(GitEntry(_git_path(item["path"]),
                            _hex(item["hash"], "a .git hash", allow_none=True)))
    _unique([g.path for g in git], ".git entries")
    return tuple(git)


def _check_store(items):
    store = []
    for item in _list(items, "store"):
        _keys(item, STORE_KEYS, "a store entry")
        path = item["path"]
        try:
            safefs.validate_relpath(path)
        except safefs.SafeFsError as exc:
            _fail("a store path: %s" % exc)
        store.append(StoreWrite(path, _hex(item["before"], "a store before hash", allow_none=True),
                                _hex(item["after"], "a store hash")))
    _unique([s.path for s in store], "store entries")
    return tuple(store)


def _check_overlap(record):
    """A path is a file or a directory of the plan, not both, and no file is another's parent;
    compared as a case-insensitive filesystem would."""
    paths = [f.path for f in record.files]
    try:
        safefs.check_tree_paths(paths)
    except safefs.SafeFsError as exc:
        _fail("the files cannot all be written: %s" % exc)
    if {_fold(d) for d in record.dirs} & {_fold(p) for p in paths}:
        _fail("a path is both a file and a directory")
    files = {_fold(p) for p in paths}
    for directory in record.dirs:
        parts = _fold(directory)
        if any(parts[:depth] in files for depth in range(1, len(parts))):
            _fail("a directory is below a file")


def check(document):
    """The ``Record`` for a decoded document, or raise UnfinishedError."""
    _keys(document, TOP_KEYS, "the record")
    if document["format"] != FORMAT or isinstance(document["format"], bool):
        _fail("the record's format is not %d" % FORMAT)
    if document["command"] not in COMMANDS:
        _fail("the record's command is not one of %s" % ", ".join(COMMANDS))
    project = document["project"]
    if project is not None:
        _hex(project, "the project id")
    version = document["workbench"]
    if not isinstance(version, str) or not _WORKBENCH.match(version):
        _fail("the record's workbench version is not a plain token")
    record = Record(document["command"], project, version, _check_dirs(document["dirs"]),
                    _check_files(document["files"]), _check_git(document["git"]),
                    _check_store(document["store"]))
    if len(record.dirs) + len(record.files) + len(record.git) + len(record.store) > MAX_ENTRIES:
        _fail("the record has more than %d entries" % MAX_ENTRIES)
    _check_overlap(record)
    return record


def _document(record):
    return {
        "command": record.command, "dirs": list(record.dirs), "format": FORMAT,
        "files": [{"after": f.after, "before": f.before, "op": f.op, "path": f.path}
                  for f in record.files],
        "git": [{"hash": g.hash, "path": g.path} for g in record.git],
        "project": record.project,
        "store": [{"after": s.after, "before": s.before, "path": s.path} for s in record.store],
        "workbench": record.workbench,
    }


def _serialize(record):
    return (json.dumps(_document(record), sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


# --- building and reading ---------------------------------------------------------


def build(command, project, version, files, dirs=(), git=(), store=()):
    """The bytes of the marker for a plan.

    `files` are ``(path, op, before, after)``; `dirs` are the paths of directories the plan
    creates; `git` is the skeleton as ``(path, content or None)`` where None is a directory;
    `store` is ``(path, before hash or None, after hash)``; None means the entry is not there yet. Raises UnfinishedError when the plan cannot be recorded,
    which includes a record the reader would refuse (too large, a bad path); the caller then
    writes nothing.
    """
    record = Record(command, project, version, tuple(dirs),
                    tuple(FileWrite(*each) for each in files),
                    tuple(GitEntry(path, None if data is None else sha(data))
                          for path, data in git),
                    tuple(StoreWrite(*each) for each in store))
    data = _serialize(record)
    # What cannot be read back must not be written: read the record as a reader will.
    if parse(data) != record:
        _fail("the record does not read back as it was built")
    return data


def fingerprint(record):
    """The SHA-256 of the marker a record was read from (a record is accepted only in the
    canonical form, so it stands for exactly those bytes)."""
    return sha(_serialize(record))


def parse(data):
    """The ``Record`` in the marker's bytes. Raises UnfinishedError for an empty marker, one that
    is not exactly what ``build`` writes, or one over the manifest's size bound."""
    if not isinstance(data, bytes):
        _fail("the marker is not bytes")
    if not data:
        _fail("the marker is empty: it has no record")
    try:
        document = declarations.parse_json(data)
    except ValueError as exc:
        _fail("the marker is not a valid record: %s" % exc)
    record = check(document)
    if _serialize(record) != data:
        _fail("the marker is not in its canonical form")
    return record


# --- examining -------------------------------------------------------------------

BUDGET = 256 * 1024 * 1024       # bytes read in one examination; beyond it a path is not read
MAX_LISTED = 500

# `kind` is "file", "dir", "git" or "store"; `state` is before/after/other for a file,
# absent/empty/holds/other for a directory, absent/after/other for a .git entry, before/after/other
# for a store entry (before: absent for an install, the old baselines for an upgrade or add).
Item = collections.namedtuple("Item", "kind path state detail")
# `record` is None when the marker has no usable record, and `problem` says why. `files` is
# "before", "after" or "mixed" and `store` is "none", "all" or "partial"; both None without a record.
Examination = collections.namedtuple("Examination", "record problem items files store")


def _no_record(problem):
    return Examination(None, problem, (), None, None)


def _file_item(writer, entry, spent):
    if spent[0] > BUDGET:
        return Item("file", entry.path, "other", "not read: the examination's read budget is spent")
    try:
        state = writer.read_file(entry.path)
    except (safefs.SafeFsError, OSError) as exc:
        return Item("file", entry.path, "other", _short(exc))
    if state is None:
        return Item("file", entry.path, "before" if entry.op == "create" else "other",
                    "" if entry.op == "create" else "missing; it was to be replaced")
    spent[0] += len(state.data)
    if state.hash == entry.after:
        return Item("file", entry.path, "after", "")
    if entry.op == "replace" and state.hash == entry.before:
        return Item("file", entry.path, "before", "")
    return Item("file", entry.path, "other", "holds other content")


def _children(dirs):
    """{directory: names of the recorded directories directly below it}, in one pass."""
    found = collections.defaultdict(set)
    for directory in dirs:
        parent, _, name = directory.rpartition("/")
        found[parent].add(name)
    return found


def _dir_item(writer, path, children):
    """A recorded directory holds something when it has an entry that is neither the local
    directory of the marker nor another recorded directory (that one has its own item)."""
    ignore = set(children.get(path, ()))
    if path == ".workbench":
        ignore.add("local")
    try:
        holds = writer.dir_holds(path, ignore=ignore)
    except (safefs.SafeFsError, OSError) as exc:
        return Item("dir", path, "other", _short(exc))
    return Item("dir", path, "absent" if holds is None else "holds" if holds else "empty", "")


def _git_item(writer, entry):
    try:
        found = writer.git_entry(entry.path)
    except (safefs.SafeFsError, OSError) as exc:
        return Item("git", ".git/" + entry.path, "other", _short(exc))
    shown = ".git/" + entry.path
    if found is None:
        return Item("git", shown, "absent", "")
    kind, got = found
    if (kind == "dir") == (entry.hash is None) and got == entry.hash:
        return Item("git", shown, "after", "")
    return Item("git", shown, "other", "is not what the workbench wrote")


def _git_state(writer, record, items):
    """"before", "after", "other", or None when the plan made no .git."""
    if not record.git:
        return None
    try:
        top = writer.git_entry("")
    except (safefs.SafeFsError, OSError) as exc:
        items.append(Item("git", ".git", "other", _short(exc)))
        return "other"
    states = {item.state for item in items if item.kind == "git"}
    if top is None and states == {"absent"}:
        return "before"
    if top == ("dir", None) and states == {"after"}:
        return "after"
    items.append(Item("git", ".git", "other", "is not a directory" if top not in (
        None, ("dir", None)) else "is only partly written"))
    return "other"


def _store_item(tree, entry, spent):
    if spent[0] > BUDGET:
        return Item("store", entry.path, "other", "not read: the examination's read budget is spent")
    try:
        kind = tree.kind(entry.path) if os.path.lexists(tree.root) else None
        if kind is None:
            return Item("store", entry.path, "before" if entry.before is None else "other",
                        "" if entry.before is None else "missing; it held the old baselines")
        if kind != "file":
            return Item("store", entry.path, "other", "is not a file")
        data = tree.read(entry.path)
    except (safefs.SafeFsError, store_module.StoreError, OSError) as exc:
        return Item("store", entry.path, "other", _short(exc))
    spent[0] += len(data)
    if sha(data) == entry.after:
        return Item("store", entry.path, "after", "")
    if entry.before is not None and sha(data) == entry.before:
        return Item("store", entry.path, "before", "")
    return Item("store", entry.path, "other", "holds other content")


def _short(exc):
    return display.ascii_text(str(exc))[:200]


def _summary_files(record, items, git):
    files = [i.state for i in items if i.kind == "file"]
    dirs = [i.state for i in items if i.kind == "dir"]
    if "other" in dirs or not files:
        return "mixed"
    # A complete .git skeleton with no file written is a lone .git, which install accepts.
    if all(s == "before" for s in files) and git != "other" \
            and not any(s == "holds" for s in dirs):
        return "before"
    if all(s == "after" for s in files) and git in (None, "after"):
        return "after"
    return "mixed"


def examine(writer, store_root):
    """Read the marker's record and say what the project and the guarded store hold now.

    Read-only and bounded: every project path is read through no-follow descriptors, a
    regular file at a time, with a cumulative byte budget; the store is read through its own
    reader. Nothing in the project or the store is changed. A marker that has no usable record
    gives an ``Examination`` with ``record`` None and the reason.
    """
    try:
        held = writer.read_file(projectfs.MARKER)
    except (safefs.SafeFsError, OSError) as exc:
        return _no_record("the marker cannot be read: %s" % _short(exc))
    if held is None:
        return _no_record("the marker is not there")
    try:
        record = parse(held.data)
    except UnfinishedError as exc:
        return _no_record(display.ascii_text(str(exc))[:200])
    spent = [0]
    items = [_file_item(writer, entry, spent) for entry in record.files]
    children = _children(record.dirs)
    items += [_dir_item(writer, path, children) for path in record.dirs]
    items += [_git_item(writer, entry) for entry in record.git]
    git = _git_state(writer, record, items)
    tree = store_module.Tree(store_root)
    items += [_store_item(tree, entry, spent) for entry in record.store]
    stored = [i.state for i in items if i.kind == "store"]
    if not stored:
        store_summary = "partial"      # a record that names no store write is not one to trust
    elif all(s == "before" for s in stored):
        store_summary = "none"
    elif all(s == "after" for s in stored):
        store_summary = "all"
    else:
        store_summary = "partial"
    return Examination(record, "", tuple(items), _summary_files(record, items, git), store_summary)


def render(found, hint=True):
    """The examination as lines of ASCII text for a person to read (not printed with a prefix).
    `hint` ends them with the line that names `wb recover`; that command itself leaves it out."""
    if found.record is None:
        return ["the marker has no usable record (%s)" % found.problem,
                "restore any files the failed command wrote from version control or a copy and "
                "remove the marker yourself; `wb recover` needs a record and cannot help"]
    record = found.record
    project = record.project[:12] if record.project else "unknown"
    count = collections.Counter((i.kind, i.state) for i in found.items)
    lines = [
        "the marker records an unfinished %s (workbench %s, project %s); the record is "
        "unauthenticated text" % (record.command, display.ascii_text(record.workbench), project),
        "the project holds: files %s (%d before, %d after, %d other), store %s (%d of %d "
        "written)" % (found.files, count[("file", "before")], count[("file", "after")],
                      count[("file", "other")], found.store, count[("store", "after")],
                      len(record.store)),
    ]
    shown = []
    for item in found.items:
        if item.state == "other" or (item.state == "holds" and found.files != "after") or (
                found.files == "mixed" and item.kind in ("file", "git") and item.state == "after"):
            shown.append("  %s %s%s" % (
                "written" if item.state == "after" else item.state,
                display.ascii_text(item.path)[:160],
                " (%s)" % item.detail if item.detail else ""))
    if shown:
        lines.append("to deal with before `wb recover` can clear it:")
        lines += shown[:MAX_LISTED]
        if len(shown) > MAX_LISTED:
            lines.append("  and %d more" % (len(shown) - MAX_LISTED))
    if hint:
        lines.append("run `wb recover` yourself to clear the marker where this is safe")
    return lines
