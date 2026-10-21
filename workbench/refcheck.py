"""The reference form of ``wb check``: the tracked reference index against the files git tracks.

The rules are in ``docs/specs/groundwork.md`` ("Indexes") and
``docs/decisions/2026-10-21-reference-index-format.md``; the checks run in the installer, for a
project that has the ``groundwork`` module, by ``docs/decisions/2026-10-21-installer-runs-document-
checks.md``. It reports:

* an entry whose file is not tracked, is missing, is not a regular file (a link in place of a file
  among them), or whose content does not hash to the recorded value;
* a tracked file under ``docs/references/`` that the index has no entry for;
* an index that is missing, untracked or not in its canonical form (``refindex`` reads it);
* a title or note that names a path into ``.workbench/local``, which a tracked file may not do;
* as warnings, a reference over 2 MiB, the indexed references over 50 MiB in all, and an entry
  with no license.

``index.json`` and the area's ``README.md`` are metadata, not references. What git tracks is the
``Tracked`` set read from ``.git/index`` by ``gitindex``, so no program runs. Every file is read
through the writer, which follows no link; the bytes read are bounded, and passing the bound is a
problem that says what was not looked at. A path and every other value read from the repository is
shown with its escapes removed, and a message never repeats an index value.
"""

from . import display, doccheck, projectfs, refindex, safefs

FILE_WARN = 2 * 1024 * 1024
FOLDER_WARN = 50 * 1024 * 1024
MAX_READ = 128 * 1024 * 1024
MAX_LISTED = 50
LOCAL = ".workbench/local"


def _shown(path):
    return display.ascii_text(path)[:120]


def _split(path):
    """The name below the area for a tracked `path`, or None when it is outside the area."""
    prefix = refindex.AREA.casefold() + "/"
    if not path.casefold().startswith(prefix):
        return None
    return path[len(prefix):]


def _is_metadata(rest):
    return rest.casefold() in tuple(name.casefold() for name in refindex.METADATA)


def _tracked_files(tracked):
    return sorted(path for path in tracked.files
                  if _split(path) is not None and not _is_metadata(_split(path)))


def _read_index(writer, tracked, problems):
    """The parsed index, or None with the reason added to `problems`."""
    path = refindex.PATH
    try:
        state = writer.read_file(path)
    except (safefs.SafeFsError, projectfs.WriteConflict) as exc:
        problems.append("%s: cannot be read: %s" % (path, display.ascii_text(str(exc))[:160]))
        return None
    if state is None:
        return None
    if path not in tracked.files:
        problems.append("%s: exists but git does not track it, and the tracked index is a tracked "
                        "file" % path)
        return None
    try:
        return refindex.parse(state.data)
    except refindex.RefIndexError as exc:
        problems.append("%s: %s" % (path, display.ascii_text(str(exc))[:200]))
        return None


def _entry(writer, tracked, entry, spent, problems, warnings):
    """Check one entry against its file; `spent` is the running count of bytes read."""
    name = _shown(entry["file"])
    for field in ("title", "notes"):
        if LOCAL in entry[field].casefold():
            problems.append("%s: its %s names a path into %s, which is not tracked; cite an "
                            "untracked reference by URL, date and hash" % (name, field, LOCAL))
    if not entry["license"]:
        warnings.append("%s: no license is recorded" % name)
    if entry["file"] not in tracked.files:
        problems.append("%s: the index has an entry for it, but git does not track it" % name)
        return
    if entry["file"] in tracked.links:
        problems.append("%s: git tracks a link in place of the file" % name)
        return
    if spent[0] >= MAX_READ:
        spent[1] = True
        return
    try:
        state = writer.read_file(entry["file"])
    except projectfs.WriteConflict:
        problems.append("%s: is a link or not a regular file, so it was not read" % name)
        return
    except safefs.SafeFsError as exc:
        problems.append("%s: cannot be read: %s" % (name, display.ascii_text(str(exc))[:160]))
        return
    if state is None:
        problems.append("%s: is missing" % name)
        return
    spent[0] += len(state.data)
    spent[2] += len(state.data)
    if state.hash != entry["sha256"]:
        problems.append("%s: its content differs from the hash in the index" % name)
    if len(state.data) > FILE_WARN:
        warnings.append("%s: %d bytes, over the %d a reference file should not exceed; keep it "
                        "untracked" % (name, len(state.data), FILE_WARN))


def examine(writer, tracked):
    """``(problems, warnings)`` for the reference index of the project `writer` holds, given what
    git tracks. Both are empty for a project without the module, and for one with the module and
    no references."""
    if not doccheck.has_module(writer):
        return [], []
    problems, warnings = [], []
    files = _tracked_files(tracked)
    document = _read_index(writer, tracked, problems)
    if document is None:
        if files and not problems:
            problems.append("%s: there is no index, but git tracks %d reference file%s"
                            % (refindex.PATH, len(files), "" if len(files) == 1 else "s"))
        elif files:
            problems.append("%d tracked reference file%s %s not compared with an index"
                            % (len(files), "" if len(files) == 1 else "s",
                               "was" if len(files) == 1 else "were"))
        return problems, warnings
    spent = [0, False, 0]  # bytes read, whether the bound was passed, bytes of indexed references
    indexed = set()
    for entry in document["entries"]:
        indexed.add(entry["file"])
        _entry(writer, tracked, entry, spent, problems, warnings)
    if spent[1]:
        problems.append("more than %d bytes of references; the rest were not looked at" % MAX_READ)
    if spent[2] > FOLDER_WARN:
        warnings.append("%s: the indexed references total %d bytes, over the %d a project should "
                        "keep" % (refindex.AREA, spent[2], FOLDER_WARN))
    lacking = [path for path in files if path not in indexed]
    for path in lacking[:MAX_LISTED]:
        problems.append("%s: git tracks it, but the index has no entry for it" % _shown(path))
    if len(lacking) > MAX_LISTED:
        problems.append("%d more tracked reference files have no entry in the index"
                        % (len(lacking) - MAX_LISTED))
    return problems, warnings
