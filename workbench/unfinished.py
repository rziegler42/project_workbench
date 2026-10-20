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
import re
import unicodedata

from . import declarations, safefs

FORMAT = 1
COMMANDS = ("install", "upgrade", "add")
OPERATIONS = ("create", "replace")
_LOCAL = (".workbench", "local")

_HEX64 = re.compile(r"^[0-9a-f]{64}\Z")
_WORKBENCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}\Z")

TOP_KEYS = ("command", "dirs", "files", "format", "git", "project", "store", "workbench")
FILE_KEYS = ("after", "before", "op", "path")
GIT_KEYS = ("hash", "path")
STORE_KEYS = ("after", "path")

FileWrite = collections.namedtuple("FileWrite", "path op before after")
GitEntry = collections.namedtuple("GitEntry", "path hash")
StoreWrite = collections.namedtuple("StoreWrite", "path after")
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
        store.append(StoreWrite(path, _hex(item["after"], "a store hash")))
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
    _check_overlap(record)
    return record


def _document(record):
    return {
        "command": record.command, "dirs": list(record.dirs), "format": FORMAT,
        "files": [{"after": f.after, "before": f.before, "op": f.op, "path": f.path}
                  for f in record.files],
        "git": [{"hash": g.hash, "path": g.path} for g in record.git],
        "project": record.project,
        "store": [{"after": s.after, "path": s.path} for s in record.store],
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
    `store` is ``(path, after hash)``. Raises UnfinishedError when the plan cannot be recorded,
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
