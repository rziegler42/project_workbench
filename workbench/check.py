"""``wb check``: report what is wrong with this clone's harness files. Read-only.

The report, from ``repository-boundary.md`` and ``installer-interface.md``:

* a clone with no harness attached is valid and is reported as "none attached";
* files of a harness other than the attached one;
* generated files whose hash differs from the local manifest, or that are missing;
* extra files under the directories the attached harness generates into (strays);
* what git tracks: tracked files that look like harness output or scratch, tracked documents that
  link or import into untracked content, tracked files that differ from the committed manifest in a
  way their owner class does not allow, and whether the manifest is committed;
* after those, what the installed modules' own checks report (``checks``), such as the form of the
  specs, roadmaps and decisions and the reference index from a module that offers such a check.

Everything is read through the no-follow reader and nothing is written. The local manifest is
scratch (``repository-boundary.md``): its hashes say a file is the one attach wrote, not that it is
safe, and the report says so. Git is never run: what it tracks is read from ``.git/index`` itself
(``gitindex``), because a repository can name programs git would run.
"""

import collections
import hashlib

from . import (__version__, checks, gitindex, harnesses, installed, localmanifest, manifest, pointers, projectfs,
               rendering, sources, target)
from .wbkit import display, safefs

# Top-level paths that are scratch, not content: nothing tracked may live there.
SCRATCH = (".workbench/local", ".debug")
DOCUMENTS = (".md", ".markdown")
MAX_ENTRIES = 5000
MAX_DEPTH = 8
MAX_DOCUMENTS = 5000
MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
MAX_LOOKUPS = 5000
LISTED = 40

Command = collections.namedtuple("Command", "target")
# `manifest` is a sentence about the committed manifest, or None when git could not be asked.
# `modules` are the ``checks.Section`` of the installed modules, run after the installer's own checks.
Report = collections.namedtuple("Report", "harness problems warnings manifest modules",
                                defaults=(None, ()))


def parse(tokens):
    """A ``Command`` from ``[<target> | --dir <path>]``; a ``sources.UsageError`` otherwise."""
    positional = dir_option = None
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "":
            raise sources.UsageError("an argument may not be empty")
        if token == "--dir":
            if dir_option is not None:
                raise sources.UsageError("--dir was given twice")
            dir_option = sources._value(tokens, index, token)
            index += 2
        elif token.startswith("-"):
            raise sources.UsageError("unknown option %s" % token)
        else:
            if positional is not None:
                raise sources.UsageError("more than one target was given")
            positional = token
            index += 1
    try:
        return Command(target.choose(positional, dir_option))
    except target.TargetUsage as exc:
        raise sources.UsageError(str(exc))


def _shown(path):
    return display.ascii_text(path)[:120]


def _files_of(writer, rel, found, budget, depth=0):
    """Add every non-directory below `rel` to `found`; directories are walked, never links."""
    try:
        entries = writer.list_dir(rel, lenient=True)
    except safefs.SafeFsError as exc:
        found.append((rel, "unreadable: %s" % display.ascii_text(str(exc))[:200]))
        return
    for name, kind in entries or ():
        budget[0] -= 1
        if budget[0] < 0:
            return
        path = rel + "/" + name
        if kind == "dir" and depth < MAX_DEPTH:
            _files_of(writer, path, found, budget, depth + 1)
        elif kind == "dir":
            found.append((path, "nested too deeply to look at"))
        else:
            found.append((path, None))


def _drift(writer, recorded):
    problems = []
    for item in recorded["files"]:
        path = item["path"]
        try:
            state = writer.read_file(path)
        except safefs.SafeFsError as exc:
            problems.append("%s: cannot be read: %s" % (_shown(path), display.ascii_text(str(exc))[:200]))
            continue
        if state is None:
            problems.append("%s: missing; `wb attach` is for a clone with no harness, so restore "
                            "it or use a new clone" % _shown(path))
        elif state.hash != item["hash"]:
            problems.append("%s: differs from what attach wrote" % _shown(path))
    return problems


def _strays(writer, facts, recorded):
    """Problems for files below the directories attach generates into that it did not write. A path
    the layout tolerates, or anything below one, is not one, even below such a directory."""
    known = {item["path"] for item in recorded["files"]}
    tolerated = facts["tolerated"]
    found, budget = [], [MAX_ENTRIES]
    for rel in facts["generated"]:
        _files_of(writer, rel, found, budget)
    problems = []
    for path, why in found:
        if why is not None:
            problems.append("%s: %s" % (_shown(path), why))
        elif path not in known and not any(path == each or path.startswith(each + "/")
                                           for each in tolerated):
            problems.append("%s: not a file attach wrote" % _shown(path))
    if budget[0] < 0:
        problems.append("more than %d entries under the harness directories; not all were looked at"
                        % MAX_ENTRIES)
    return problems


def _shallow(writer, facts, recorded):
    """Warnings for entries directly under a harness directory that attach did not write. They
    are warnings because the harness itself, or the owner, may keep files there; a hook is code,
    so the warning names it. A directory attach generates into is not scanned here (``_strays``
    does), and a tolerated path, or a directory that holds one, is not reported."""
    known = {item["path"] for item in recorded["files"]}
    skip = set(facts["generated"])
    tolerated = set(facts["tolerated"])
    warnings = []
    for rel in facts["directories"]:
        if rel in skip:
            continue
        try:
            entries = writer.list_dir(rel, lenient=True)
        except safefs.SafeFsError:
            continue  # the recorded files under it are reported as unreadable
        for name, _ in entries or ():
            path = rel + "/" + name
            if (path not in known and path not in skip and path not in tolerated
                    and not any(each.startswith(path + "/") for each in tolerated)):
                warnings.append("%s: not written by attach; the harness may run or read it"
                                % _shown(path))
    return warnings


def _generated(tracked, found=None):
    """Problems for tracked paths that look like harness output or scratch."""
    found = harnesses.known() if found is None else found
    roots = [(root, "output of the harness %s" % harness)
             for harness, facts in sorted(found.items()) for root in facts["roots"]]
    roots.extend((root, "scratch") for root in SCRATCH)
    problems = []
    for path in sorted(tracked.files):
        folded = path.casefold()
        for root, what in roots:
            if folded == root.casefold() or folded.startswith(root.casefold() + "/"):
                problems.append("%s: tracked by git, but it looks like %s" % (_shown(path), what))
                break
    return problems


def _exists(writer, rel, cache):
    parent, _, name = rel.rpartition("/")
    if parent not in cache:
        try:
            cache[parent] = {each for each, _ in writer.list_dir(parent, lenient=True) or ()}
        except safefs.SafeFsError:
            cache[parent] = set()
    return name in cache[parent]


def _scratch_path(rel, found):
    folded = rel.casefold()
    roots = list(SCRATCH)
    for facts in found.values():
        roots.extend(facts["roots"])
    return any(folded == root.casefold() or folded.startswith(root.casefold() + "/")
               for root in roots)


def _pointers(writer, tracked, found):
    """Problems for tracked Markdown documents that link or import into untracked content."""
    documents = sorted(path for path in tracked.files if path.lower().endswith(DOCUMENTS))
    problems, cache, spent, lookups, unread = [], {}, 0, 0, 0
    complete = len(documents) <= MAX_DOCUMENTS
    for path in documents[:MAX_DOCUMENTS]:
        try:
            state = writer.read_file(path)
        except safefs.SafeFsError:
            unread += path not in tracked.links
            continue
        if state is None:
            continue
        spent += len(state.data)
        if spent > MAX_DOCUMENT_BYTES:
            complete = False
            break
        seen = set()
        for raw, is_import in pointers.references(state.data.decode("utf-8", "replace")):
            where = pointers.target_of(path, raw, is_import)
            key = raw if where == pointers.OUTSIDE else where
            if where is None or key in seen:
                continue
            seen.add(key)
            if where == pointers.OUTSIDE:
                problems.append("%s: points outside the project: %s" % (_shown(path), _shown(raw)))
                continue
            if where in tracked.files or where in tracked.dirs:
                continue
            lookups += 1
            if lookups > MAX_LOOKUPS:
                complete = False
                break
            if _scratch_path(where, found) or _exists(writer, where, cache):
                problems.append("%s: points to %s, which git does not track"
                                % (_shown(path), _shown(where)))
        if not complete:
            break
    if unread:
        problems.append("%d tracked document%s could not be read, so %s not looked at"
                        % (unread, "" if unread == 1 else "s", "it was" if unread == 1 else "they were"))
    if not complete:
        problems.append("more documents or references than are looked at; not all were looked at")
    return problems


def _recorded(writer, tracked):
    """(sentence about the manifest, problems, warnings) for the committed manifest and the files
    it records."""
    try:
        present = writer.read_file(installed.MANIFEST) is not None
    except safefs.SafeFsError as exc:
        return ("manifest: cannot be read",
                ["%s: cannot be read: %s" % (installed.MANIFEST,
                                             display.ascii_text(str(exc))[:200])], [])
    if not present:
        return "manifest: none", [], []
    committed = installed.MANIFEST in tracked.files
    sentence = ("manifest: tracked by git" if committed else
                "manifest: not tracked by git, so it is not committed and other clones do not "
                "share it")
    try:
        held = installed.read(writer, __version__)
    except installed.InstalledError as exc:
        return sentence, ["%s: %s" % (installed.MANIFEST, display.ascii_text(str(exc))[:200])], []
    problems, loose = [], 0
    for entry in held.entries:
        if entry.path not in tracked.files:
            loose += 1
            continue
        where = _shown(entry.path)
        if entry.state == installed.UNREADABLE:
            problems.append("%s: cannot be read as a plain file: %s"
                            % (where, display.ascii_text(entry.detail)[:120]))
        elif entry.owner_class == "module-owned" and entry.state in (installed.EDITED,
                                                                      installed.MISSING):
            problems.append("%s: a module-owned file that %s the manifest" % (
                where, "differs from" if entry.state == installed.EDITED else "is missing from"))
        elif entry.owner_class == "slot block" and entry.state == installed.EDITED:
            problems.append("%s: the block %s differs from the manifest" % (where, _shown(entry.block)))
    warnings = []
    if loose:
        warnings.append("%d file%s the manifest records %s not tracked by git yet" % (
            loose, "" if loose == 1 else "s", "is" if loose == 1 else "are"))
    return sentence, problems, warnings


def _tracked_report(writer, found):
    """(manifest sentence, problems, warnings) from what git tracks; nothing runs git."""
    try:
        tracked = gitindex.read(writer)
    except gitindex.GitIndexError as exc:
        return None, [".git/index: %s" % display.ascii_text(str(exc))[:200]], []
    problems = _generated(tracked, found)
    warnings = ["%s: a link that git tracks; where it points is not checked" % _shown(path)
                for path in sorted(tracked.links)]
    problems.extend(_pointers(writer, tracked, found))
    sentence, more_problems, more_warnings = _recorded(writer, tracked)
    return sentence, problems + more_problems, warnings + more_warnings


def _others(writer, attached, found):
    """Top-level names that belong to a harness other than `attached` (None for no harness)."""
    try:
        names = {name for name, _ in writer.list_dir("", lenient=True) or ()}
    except safefs.SafeFsError as exc:
        return [], ["the project directory cannot be listed: %s" % display.ascii_text(str(exc))[:200]]
    owned = []
    for harness, facts in sorted(found.items()):
        if harness == attached:
            continue
        owned.extend((harness, name) for name in facts["roots"] if name in names)
    return owned, []


def _unknown(harness, loaded):
    shown = display.ascii_text(harness)[:40]
    if harness in loaded.refused:
        return "%s is declared by more than one first-party package, so its files were not scanned" % shown
    return "%s is not a harness this workbench knows, so its files were not scanned" % shown


def examine(writer, distribution=None):
    """The ``Report`` for the project `writer` holds. Reads only. The harnesses are the first-party ones
    of `distribution` (default: the running workbench's)."""
    problems, warnings = [], []
    loaded = harnesses.load(distribution)
    found = loaded.found
    try:
        recorded = localmanifest.read(writer)
    except localmanifest.LocalManifestError as exc:
        problems.append("%s: %s" % (localmanifest.PATH, display.ascii_text(str(exc))[:200]))
        sentence, more_problems, more_warnings = _tracked_report(writer, found)
        return Report(None, problems + more_problems, warnings + more_warnings, sentence)
    attached = recorded["harness"] if recorded else None
    others, trouble = _others(writer, attached, found)
    problems.extend(trouble)
    for harness, name in others:
        text = "%s belongs to the harness %s" % (_shown(name), harness)
        if attached is None:
            warnings.append(text + ", and no harness is attached to this clone")
        else:
            problems.append(text + ", not to the attached %s" % display.ascii_text(attached)[:40])
    if recorded:
        problems.extend(_drift(writer, recorded))
        if attached in found:
            problems.extend(_strays(writer, found[attached], recorded))
            warnings.extend(_shallow(writer, found[attached], recorded))
        else:
            warnings.append(_unknown(attached, loaded))
    sentence, tracked_problems, tracked_warnings = _tracked_report(writer, found)
    problems.extend(tracked_problems)
    warnings.extend(tracked_warnings)
    return Report(attached, problems, warnings, sentence)


def _listed(err, prefix, items):
    for item in items[:LISTED]:
        err.write("%s: %s\n" % (prefix, display.clean(item)))
    if len(items) > LISTED:
        err.write("%s: and %d more\n" % (prefix, len(items) - LISTED))


def _rendering_drift(guarded, writer):
    """Problems for the harness's permissions file when it differs from the record attach kept in the guarded store
    (``rendering.py``). No record, or a project that cannot be read here, gives none: the other checks say so."""
    try:
        project = manifest.project_id(installed.read(writer, __version__).document["seed"])
    except (installed.InstalledError, manifest.ManifestError, KeyError):
        return []
    record = rendering.read(guarded, project)
    if record is None or record["file"] is None:
        return []
    try:
        state = writer.read_file(record["file"])
    except safefs.SafeFsError:
        return []  # the manifest check already says the file cannot be read
    if state is None or hashlib.sha256(state.data).hexdigest() == record["file_hash"]:
        return []  # a missing file is already reported as missing
    return ["%s: differs from the rendering record attach kept in the guarded store, so a key at ask or none reads "
            "as block" % _shown(record["file"])]


def run(guarded, command, out, err, distribution=None):
    """Report and return the exit code: 0 for no problem, 1 for a problem or a refusal."""
    try:
        with target.open_target(command.target, guarded.root) as held:
            if held.state != "existing":
                err.write("refused: the target is not an existing project\n")
                return 1
            writer = projectfs.Writer(held)
            report = examine(writer, distribution)
            report = report._replace(problems=list(report.problems) + _rendering_drift(guarded, writer))
            path = held.path
        report = report._replace(modules=checks.run_all(guarded, path))
    except target.TargetError as exc:
        return target.write_refusal(err, exc)
    except safefs.SafeFsError as exc:
        err.write("refused: %s\n" % display.clean(str(exc)))
        return 1
    try:
        if report.harness is None:
            out.write("harness: none attached in %s\n" % display.ascii_text(path))
        else:
            out.write("harness: %s attached in %s\n" % (display.ascii_text(report.harness)[:40],
                                                          display.ascii_text(path)))
            out.write("the local manifest is a scratch record: a file that matches it is the one "
                      "attach wrote, not a file known to be safe\n")
        out.write("%s\n" % (report.manifest or "manifest: not known, git's index could not be read"))
        warnings, problems = list(report.warnings), list(report.problems)
        for section in report.modules:
            warnings.extend("%s: %s" % (section.label, line) for line in section.warnings)
            problems.extend("%s: %s" % (section.label, line) for line in section.problems)
        _listed(err, "warning", warnings)
        _listed(err, "problem", problems)
        if problems:
            out.write("check found %d problem%s\n" % (len(problems), "" if len(problems) == 1 else "s"))
        else:
            out.write("check found no problems\n")
        out.flush()
    except BrokenPipeError:
        pass
    return 1 if problems else 0
