"""The state of every rendered file but the permissions file, for ``wb preview rerender`` and ``wb rerender``.

``attach`` renders the skills, agents, commands and the root file of a harness from the installed modules and records a hash
for each in the local manifest. When a source moves on, the rendered file stays behind. This module compares, for each file
the staging would produce and each file the manifest lists, the file on disk, the hash the manifest recorded and the staged
hash, and names the state (``docs/specs/harness-refresh.md``). It reads the project and writes nothing.

The staged hash is of the translated file, so the comparison goes through the renderer and not through the neutral source.
"""

import collections
import difflib

from .wbkit import display, safefs

CURRENT, APPLIED, STALE, EDITED, MISSING, NEW, UNRECORDED, ORPHANED = (
    "current", "applied", "stale", "edited", "missing", "new", "unrecorded", "orphaned")

# The states whose manifest entry a refresh writes, and the states a write has to act on (an applied file only changes the
# manifest). Created files are those a write makes.
RECORDS = (STALE, APPLIED, MISSING, NEW)
CREATES = (MISSING, NEW)
WRITES = (STALE,) + CREATES
REFUSED = (EDITED, UNRECORDED)
SHOWN_LINES = 40

# `old` is the hash of the file on disk or None; `new` the staged hash or None (an orphan has none); `data` the staged bytes
# (None for an orphan); `lines` the changed lines of a stale file as ``(sign, text)`` cut at `SHOWN_LINES`, and `more` how
# many were cut; `detail` is "present" or "already gone" for an orphan.
Row = collections.namedtuple("Row", "path state old new data lines more detail", defaults=(None, None, (), 0, ""))


def covered(path, exclude):
    """Whether one of the layout's exclude entries names `path` or a directory above it."""
    for entry in exclude:
        body = entry[:-1] if entry.endswith("/") else entry
        if path == body or path.startswith(body + "/"):
            return True
    return False


def _changed(old, new):
    """The changed lines of two texts as ``(sign, text)``, `SHOWN_LINES` of them at most, and the number cut."""
    before = old.decode("utf-8", "replace").splitlines()
    after = new.decode("utf-8", "replace").splitlines()
    found = []
    for line in list(difflib.unified_diff(before, after, n=0, lineterm=""))[2:]:
        if not line.startswith("@@"):
            found.append((line[0], line[1:]))
    return tuple(found[:SHOWN_LINES]), max(0, len(found) - SHOWN_LINES)


def classify(writer, listed, files, settings, exclude):
    """``(rows, problems)`` for the files in `files` (``harnessplan.Planned``) and the manifest's `listed` entries (dicts with
    ``path`` and ``hash``), leaving out the permissions file `settings`. The rows are sorted by path. `problems` is a list of
    lines, empty when nothing refuses the run.

    Every staged and listed path is read without following a link; a link at any of them, or above them, is refused whatever
    the content. A listed path the staging no longer has is orphaned before anything else is asked of it. The rest are tried
    in this order: equal to the staged bytes (current, or applied when the manifest records another hash or none), gone
    (missing, or new when the manifest does not list it), equal to the recorded hash (stale), anything else (edited when
    the manifest lists it, unrecorded when it does not)."""
    recorded = {item["path"]: item["hash"] for item in listed if item["path"] != settings}
    staged = {item.path: item for item in files if item.path != settings}
    problems, rows = [], []
    seen = {}
    for path in sorted(set(recorded) | set(staged)):
        try:
            seen[path] = writer.read_file(path)
        except safefs.SafeFsError as exc:
            problems.append("%s: %s; a refresh never follows a link or touches a file that is not regular"
                            % (display.ascii_text(path)[:200], display.ascii_text(str(exc))[:300]))
    for path in sorted(seen):
        state = seen[path]
        disk = state.hash if state else None
        if path not in staged:
            rows.append(Row(path, ORPHANED, disk, None, None, (), 0, "present" if state else "already gone"))
            continue
        item = staged[path]
        known = recorded.get(path)
        if disk == item.sha256:
            rows.append(Row(path, CURRENT if known == disk else APPLIED, disk, item.sha256, item.data))
        elif disk is None:
            rows.append(Row(path, MISSING if known is not None else NEW, None, item.sha256, item.data))
        elif known is not None and disk == known:
            lines, more = _changed(state.data, item.data)
            rows.append(Row(path, STALE, disk, item.sha256, item.data, lines, more))
        else:
            rows.append(Row(path, EDITED if known is not None else UNRECORDED, disk, item.sha256, item.data))
    for row in rows:
        if row.state in REFUSED:
            problems.append("%s: %s" % (display.ascii_text(row.path)[:200], _WHY[row.state]))
        elif row.state in CREATES and not covered(row.path, exclude):
            problems.append("%s: not covered by the harness's exclude lines, so git would see the file it would create"
                            % display.ascii_text(row.path)[:200])
    return rows, problems


class Changed(Exception):
    """A file differs from what the plan read; raised before anything is written."""


class Partial(Exception):
    """Creating a file failed after the path may have been made. `create_file` writes into the final name, so a failure
    midway can leave a short file there; the next run reads it as unrecorded or edited and refuses until it is removed."""


def recheck(writer, rows):
    """Read again every file a write acts on, without following a link, and raise `Changed` naming the first one that is not
    as the plan read it: a stale file with its old bytes, a created one still absent, an applied one still equal to the staged
    bytes. Nothing has been written when this is called."""
    for row in rows:
        if row.state not in RECORDS:
            continue
        found = writer.read_file(row.path)
        wanted = row.new if row.state == APPLIED else row.old
        if (found.hash if found else None) != wanted:
            raise Changed("%s changed after the plan was made" % display.ascii_text(row.path)[:200])


def write(writer, rows, done):
    """Write the rows in order, appending each path to `done` once it is on disk: a stale file is replaced with the hash the
    plan read, a new or missing one is created, and a current, applied or orphaned one is not touched (an applied file only
    takes its hash into the manifest, written by the caller). A failed create that may have left a file raises `Partial`."""
    for row in rows:
        if row.state == STALE:
            writer.replace_file(row.path, row.old, row.data)
            done.append(row.path)
        elif row.state in CREATES:
            mark = len(writer.written)
            try:
                writer.create_file(row.path, row.data)
            except (Exception, KeyboardInterrupt) as exc:
                # `create_file` records the path as soon as it has made the file, before it writes into it.
                if row.path in writer.written[mark:]:
                    done.append(row.path)
                    cause = "interrupted" if isinstance(exc, KeyboardInterrupt) else str(exc)
                    raise Partial("%s; %s may be partly written: remove it, then run again"
                                  % (cause, display.ascii_text(row.path)[:200])) from exc
                raise
            done.append(row.path)


_WHY = {
    EDITED: "edited since it was rendered, so a refresh would overwrite the change; move it aside or delete it and run "
            "again, which creates it from its source",
    UNRECORDED: "unrecorded: the manifest does not list it and the file there is not what the harness would write; move "
                "it aside or delete it and run again",
}
