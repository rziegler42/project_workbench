"""The acknowledgement baselines and the first-seen record, read, and a project compared with them.

``install`` writes two entries in the guarded store for a project (``repository-boundary.md``)::

    projects/<id>/baselines   {"baselines": {"<path>": "<sha256 hex>"}, "format": 1}
    projects/<id>/seen        {"format": 1, "kind": "path", "value": "<resolved target path>"}

Both are read here with the strictest rule that is cheap: the bytes must be exactly what the
installer writes (sorted keys, two-space indent, ASCII, one final line feed), so an edited,
re-ordered or padded file is refused rather than interpreted. A missing entry reads as ``None``;
whether that is acceptable is ``check_known``'s decision.

``differences`` compares a project with its baselines and returns each difference. The scope is
what ``trust-and-approval.md`` names: the manifest, every file under ``.workbench/`` outside
``local/``, and the files the command is about to write into. A file added or removed counts; a
link, a directory or another kind of file where a file is expected is a difference with that
reason. Nothing is followed and nothing is written; the project is read through the writer's
no-follow reader, so a swapped parent is a refusal and not a read of another place.
"""

import collections
import json
import re

from . import declarations, display, projectfs, safefs

FORMAT = 1
MANIFEST = ".workbench/manifest.json"
WORKBENCH = ".workbench"
LOCAL = "local"
MAX_WALKED = 20000      # entries visited under .workbench/ before the walk gives up
MAX_DEPTH = 32

_ID = re.compile(r"\A[0-9a-f]{64}\Z")
_HEX = re.compile(r"\A[0-9a-f]{64}\Z")

CHANGED = "changed"
ADDED = "added"
REMOVED = "removed"

# `baseline` and `current` are SHA-256 hex digests or None; `reason` is "" for a plain change of
# content and otherwise says why the path could not be hashed.
Difference = collections.namedtuple("Difference", "path kind baseline current reason")


class AcknowledgementError(Exception):
    """An entry is malformed, the project is not known here, or the project cannot be read."""


class UnknownProject(AcknowledgementError):
    """The store has no baselines for this project, or first saw it at another path."""


def _check_id(project_id):
    if not isinstance(project_id, str) or not _ID.match(project_id):
        raise AcknowledgementError("the project id is 64 lowercase hex digits")
    return project_id


def _canonical(document):
    return (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True)
            + "\n").encode("ascii")


def _load(guarded, project_id, name):
    """The parsed JSON object of `projects/<id>/<name>`, or None when the entry is absent."""
    rel = "projects/%s/%s" % (_check_id(project_id), name)
    try:
        found = guarded.kind(rel)
        if found is None:
            return None
        if found != "file":
            raise AcknowledgementError("the %s entry is not a regular file (%s)" % (name, found))
        data = guarded.read(rel)
    except safefs.SafeFsError as exc:
        raise AcknowledgementError("the %s entry cannot be read: %s" % (name, exc))
    try:
        document = declarations.parse_json(data)
        again = _canonical(document)
    except (ValueError, TypeError) as exc:
        raise AcknowledgementError("the %s entry is not valid (%s)" % (name, exc))
    if again != data:
        raise AcknowledgementError("the %s entry is not in the form install writes" % name)
    return document


def _is_format(value):
    return isinstance(value, int) and not isinstance(value, bool) and value == FORMAT


def read_baselines(guarded, project_id):
    """``{path: sha256 hex}`` for the project, or None when it has no baselines here."""
    document = _load(guarded, project_id, "baselines")
    if document is None:
        return None
    if set(document) != {"baselines", "format"} or not _is_format(document["format"]) \
            or not isinstance(document["baselines"], dict):
        raise AcknowledgementError("the baselines entry does not have the expected format")
    for path, digest in document["baselines"].items():
        if not safefs.relpath_ok(path):
            raise AcknowledgementError("the baselines name an unsafe path: %s"
                                       % display.ascii_text(path)[:80])
        if not isinstance(digest, str) or not _HEX.match(digest):
            raise AcknowledgementError("the baseline of %s is not a SHA-256 digest"
                                       % display.ascii_text(path)[:80])
    return dict(document["baselines"])


def read_seen(guarded, project_id):
    """The path where the project was first seen, or None when there is no record."""
    document = _load(guarded, project_id, "seen")
    if document is None:
        return None
    if set(document) != {"format", "kind", "value"} or not _is_format(document["format"]) \
            or document["kind"] != "path":
        raise AcknowledgementError("the first-seen entry does not have the expected format")
    value = document["value"]
    if not isinstance(value, str) or not value.startswith("/") or "\0" in value \
            or value != value.rstrip("/") and value != "/":
        raise AcknowledgementError("the first-seen entry does not hold an absolute path")
    return value


def check_known(baselines, seen, resolved_path):
    """Refuse a project this machine does not know at this place: one with no baselines, no
    first-seen record, or a record of another path. A copied or moved project is a new one."""
    if baselines is None:
        raise UnknownProject("this machine holds no acknowledgement baselines for the project; "
                             "it is treated as new here")
    if seen is None:
        raise UnknownProject("this machine holds no record of where the project was first seen")
    if seen != resolved_path:
        raise UnknownProject("the project was first seen at %s, not here; it is treated as new "
                             "here" % display.ascii_text(seen)[:200])


# --- comparing -------------------------------------------------------------------------------


def _current(reader, rel):
    """(hash, reason) of the file at `rel`: the hash is None when it is not there or not a plain
    file, and the reason says why when it is not a plain file."""
    try:
        state = reader.read_file(rel)
    except projectfs.WriteConflict:
        return None, "not a regular file"
    except safefs.SafeFsError as exc:
        return None, "unreadable (%s)" % display.ascii_text(str(exc))[:80]
    return (None, "") if state is None else (state.hash, "")


def _walk(reader, rel, depth, found):
    """Add to `found` {path: kind} for every entry below `rel`, but not below `local/` at the
    top of ``.workbench``."""
    if depth > MAX_DEPTH:
        raise AcknowledgementError("%s is nested more than %d directories deep" % (rel, MAX_DEPTH))
    try:
        entries = reader.list_dir(rel)
    except safefs.SafeFsError as exc:
        raise AcknowledgementError("cannot list %s: %s" % (rel, exc))
    for name, kind in entries or ():
        path = "%s/%s" % (rel, name)
        if rel == WORKBENCH and name == LOCAL:
            continue
        found[path] = kind
        if len(found) > MAX_WALKED:
            raise AcknowledgementError("more than %d entries under %s" % (MAX_WALKED, WORKBENCH))
        if kind == "dir":
            _walk(reader, path, depth + 1, found)


def differences(reader, baselines, writes=()):
    """Every difference between the project and `baselines`, sorted by path.

    `reader` has ``read_file`` and ``list_dir`` (a ``projectfs.Writer``). The scope is the
    manifest, each file under ``.workbench/`` outside ``local/`` and each path in `writes`.
    A path the command would create that is not there and has no baseline is no difference."""
    for path in writes:
        if not safefs.relpath_ok(path):
            raise AcknowledgementError("not a project path: %s" % display.ascii_text(path)[:80])
    listing = {}
    _walk(reader, WORKBENCH, 0, listing)
    scope = set(writes) | {MANIFEST}
    scope.update(path for path, kind in listing.items() if kind != "dir")
    scope.update(path for path in baselines if path.startswith(WORKBENCH + "/")
                 and not path.startswith("%s/%s/" % (WORKBENCH, LOCAL)))
    found = []
    for path in sorted(scope):
        kind = listing.get(path)
        if kind is not None and kind != "file":
            now, reason = None, ("a directory" if kind == "dir" else
                                 "a link" if kind == "symlink" else "not a regular file")
        else:
            now, reason = _current(reader, path)
        was = baselines.get(path)
        if was is None and now is None and not reason:
            continue
        if was is not None and now is None and not reason:
            found.append(Difference(path, REMOVED, was, None, ""))
        elif was is None:
            found.append(Difference(path, ADDED, None, now, reason))
        elif now != was or reason:
            found.append(Difference(path, CHANGED, was, now, reason))
    return found
