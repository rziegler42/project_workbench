"""``wb check``: report what is wrong with this clone's harness files. Read-only.

The report, from ``repository-boundary.md`` and ``installer-interface.md``:

* a clone with no harness attached is valid and is reported as "none attached";
* files of a harness other than the attached one;
* generated files whose hash differs from the local manifest, or that are missing;
* extra files under the directories the attached harness generates into (strays).

Everything is read through the no-follow reader and nothing is written. The local manifest is
scratch (``repository-boundary.md``): its hashes say a file is the one attach wrote, not that it is
safe, and the report says so. The checks that ask git what is tracked are separate.
"""

import collections

from . import display, localmanifest, projectfs, safefs, sources, target

# Paths each harness is known to use, for the files of one harness found beside another and for the
# strays. `roots` are top-level names, `generated` the directories attach fills. A harness not
# listed here has no stray scan, and its files are not recognised in another clone.
HARNESSES = {
    "claude": {"roots": ("CLAUDE.md", ".claude"),
               "generated": (".claude/skills", ".claude/agents", ".claude/commands"),
               "shallow": ((".claude", ("settings.json",)),)},
    "opencode": {"roots": ("opencode.json", ".opencode"), "generated": ()},
    "codex": {"roots": (".codex",), "generated": ()},
}
MAX_ENTRIES = 5000
MAX_DEPTH = 8
LISTED = 40

Command = collections.namedtuple("Command", "target")
Report = collections.namedtuple("Report", "harness problems warnings")


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


def _strays(writer, harness, recorded):
    known = {item["path"] for item in recorded["files"]}
    found, budget = [], [MAX_ENTRIES]
    for rel in HARNESSES.get(harness, {}).get("generated", ()):
        _files_of(writer, rel, found, budget)
    problems = []
    for path, why in found:
        if why is not None:
            problems.append("%s: %s" % (_shown(path), why))
        elif path not in known:
            problems.append("%s: not a file attach wrote" % _shown(path))
    if budget[0] < 0:
        problems.append("more than %d entries under the harness directories; not all were looked at"
                        % MAX_ENTRIES)
    return problems


def _shallow(writer, harness, recorded):
    """Warnings for entries directly under a harness directory that attach did not write. They
    are warnings because the harness itself, or the owner, may keep files there; a hook is code,
    so the warning names it."""
    known = {item["path"] for item in recorded["files"]}
    skip = set(HARNESSES.get(harness, {}).get("generated", ()))
    warnings = []
    for rel, allowed in HARNESSES.get(harness, {}).get("shallow", ()):
        try:
            entries = writer.list_dir(rel, lenient=True)
        except safefs.SafeFsError:
            continue  # the recorded files under it are reported as unreadable
        for name, _ in entries or ():
            path = rel + "/" + name
            if path not in known and path not in skip and name not in allowed:
                warnings.append("%s: not written by attach; the harness may run or read it"
                                % _shown(path))
    return warnings


def _others(writer, attached):
    """Top-level names that belong to a harness other than `attached` (None for no harness)."""
    try:
        names = {name for name, _ in writer.list_dir("", lenient=True) or ()}
    except safefs.SafeFsError as exc:
        return [], ["the project directory cannot be listed: %s" % display.ascii_text(str(exc))[:200]]
    found = []
    for harness, table in sorted(HARNESSES.items()):
        if harness == attached:
            continue
        found.extend((harness, name) for name in table["roots"] if name in names)
    return found, []


def examine(writer):
    """The ``Report`` for the project `writer` holds. Reads only."""
    problems, warnings = [], []
    try:
        recorded = localmanifest.read(writer)
    except localmanifest.LocalManifestError as exc:
        problems.append("%s: %s" % (localmanifest.PATH, display.ascii_text(str(exc))[:200]))
        return Report(None, problems, warnings)
    attached = recorded["harness"] if recorded else None
    others, trouble = _others(writer, attached)
    problems.extend(trouble)
    for harness, name in others:
        text = "%s belongs to the harness %s" % (_shown(name), harness)
        if attached is None:
            warnings.append(text + ", and no harness is attached to this clone")
        else:
            problems.append(text + ", not to the attached %s" % display.ascii_text(attached)[:40])
    if recorded:
        problems.extend(_drift(writer, recorded))
        problems.extend(_strays(writer, attached, recorded))
        warnings.extend(_shallow(writer, attached, recorded))
    return Report(attached, problems, warnings)


def _listed(err, prefix, items):
    for item in items[:LISTED]:
        err.write("%s: %s\n" % (prefix, display.clean(item)))
    if len(items) > LISTED:
        err.write("%s: and %d more\n" % (prefix, len(items) - LISTED))


def run(guarded, command, out, err):
    """Report and return the exit code: 0 for no problem, 1 for a problem or a refusal."""
    try:
        with target.open_target(command.target, guarded.root) as held:
            if held.state != "existing":
                err.write("refused: the target is not an existing project\n")
                return 1
            report = examine(projectfs.Writer(held))
            path = held.path
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
        _listed(err, "warning", report.warnings)
        _listed(err, "problem", report.problems)
        if report.problems:
            out.write("check found %d problem%s\n" % (len(report.problems),
                                                       "" if len(report.problems) == 1 else "s"))
        else:
            out.write("check found no problems\n")
        out.flush()
    except BrokenPipeError:
        pass
    return 1 if report.problems else 0
