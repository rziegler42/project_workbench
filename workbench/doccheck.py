"""The document form of ``wb check``: names, statuses and candidate IDs of specs, roadmaps and
decisions, for a project that has the ``groundwork`` module.

The rules are in ``docs/specs/groundwork.md`` and in the READMEs the module writes into each area;
the decision to run them in the installer is ``docs/decisions/2026-10-21-installer-runs-document-
checks.md``. A project has the module when its committed manifest records the module ``groundwork``
of the package ``workbench``. Any other project, including one with a hand-written ``docs/specs``,
gets no report from here. A project with the module and none of the folders gets none either.

Everything read is untrusted repository content. The areas are listed and each document is read
through the writer, which follows no link and reads only a regular file. The count of documents, the
total bytes, the candidates in one roadmap, the lines of a header and the findings reported are all
bounded, and passing a bound is itself a problem that says what was not looked at. Nothing is
evaluated, and a name or heading is shown with its escapes removed.
"""

import datetime
import re
import unicodedata

from . import display, installed, manifest, projectfs, safefs

PACKAGE = "workbench"
MODULE = "groundwork"

MAX_FILES = 2000
MAX_BYTES = 4 * 1024 * 1024
MAX_CANDIDATES = 2000
MAX_HEADER = 40
MAX_REPORTED = 200

SPEC_STATUSES = ("Draft", "Current", "Superseded")
ROADMAP_STATUSES = ("Draft", "Active", "Archived")
DECISION_STATUSES = ("Proposed", "Accepted", "Rejected", "Superseded")

_SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_TOPIC = re.compile(r"\A%s\.md\Z" % _SLUG)
_DECISION = re.compile(r"\A([0-9]{4})-([0-9]{2})-([0-9]{2})-(%s)\.md\Z" % _SLUG)
_DATED = re.compile(r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}(-|\.md\Z)")
_ID = re.compile(r"\A%s\Z" % _SLUG)
_FENCE = re.compile(r"\A[ ]{0,3}(`{3,}|~{3,})")
_QUOTE = re.compile(r"\A[ ]{0,3}>")
_TWO = re.compile(r"\A[ ]{0,3}##[ \t]+(.*)")
_STATUS = re.compile(r"\A[ ]{0,3}Status:[ \t]*([A-Za-z][A-Za-z0-9_-]*)?")
_SUCCESSOR = re.compile(r"\bsuperseded by\b[: \t]*\S", re.I)
_CANDIDATE = re.compile(r"\A[ ]{0,3}###[ \t]+([^\s:]+)")
_LINE = 2000

# (folder, kind, statuses)
AREAS = (("docs/specs", "spec", SPEC_STATUSES),
         ("docs/roadmaps", "roadmap", ROADMAP_STATUSES),
         ("docs/decisions", "decision", DECISION_STATUSES))


def _shown(text):
    return display.ascii_text(text)[:120]


def has_module(writer):
    """Whether the committed manifest records the module. A manifest that cannot be read is not
    this module's to report: ``check`` reports it already."""
    try:
        state = writer.read_file(installed.MANIFEST)
        if state is None:
            return False
        document = manifest.parse(state.data)
    except (safefs.SafeFsError, projectfs.WriteConflict, manifest.ManifestError):
        return False
    return any(package["name"] == PACKAGE and any(m["name"] == MODULE for m in package["modules"])
               for package in document["packages"])


def _lines(text):
    """``(number, line, plain)`` for each line of `text`; `plain` is False inside a code fence and
    for a quoted line, which are not the document's own statements."""
    fence = None
    for number, line in enumerate(text.split("\n"), 1):
        line = line[:_LINE].rstrip("\r")
        match = _FENCE.match(line)
        if fence is None:
            if match:
                fence = match.group(1)
                yield number, line, False
                continue
        elif match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence) \
                and not line.lstrip(" ")[len(match.group(1)):].strip():
            fence = None
            yield number, line, False
            continue
        yield number, line, fence is None and not _QUOTE.match(line)


def _name_problem(kind, name):
    """What is wrong with the file name of a document of `kind`, or None."""
    if kind == "decision":
        match = _DECISION.match(name)
        if not match:
            return "a decision is named YYYY-MM-DD-<topic>.md in lowercase kebab-case"
        try:
            datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return "the date in a decision's name is not a date"
        return None
    if not _TOPIC.match(name):
        return "a %s is named <topic>.md in lowercase kebab-case" % kind
    if _DATED.match(name):
        return "a %s is named with no date" % kind
    return None


def _status_problems(kind, statuses, name, lines):
    """Problems with the status line of one document."""
    status, count, successor = None, 0, False
    for number, line, plain in lines:
        if number > MAX_HEADER:
            break
        if plain and _TWO.match(line):
            break
        if not plain:
            continue
        found = _STATUS.match(line)
        if found:
            count += 1
            status = status or (found.group(1) or "")
        if _SUCCESSOR.search(line):
            successor = True
    if count == 0:
        return ["%s has no status line near the top" % name]
    problems = []
    if count > 1:
        problems.append("%s has %d status lines near the top; there is one" % (name, count))
    if status not in statuses:
        listed = ", ".join(statuses[:-1]) + " or " + statuses[-1]
        problems.append("%s has the status %s; a %s is %s"
                        % (name, _shown(status) or "(none)", kind, listed))
    elif status == "Superseded" and not successor:
        problems.append("%s is Superseded and names no successor (write `Superseded by <name>`)"
                        % name)
    return problems


def _candidates(lines):
    """``[(number, id)]`` for the candidate headings under ``## Candidates``, and whether the list
    was cut at ``MAX_CANDIDATES``."""
    inside, found = False, []
    for number, line, plain in lines:
        if not plain:
            continue
        two = _TWO.match(line)
        if two:
            inside = two.group(1).strip().casefold() == "candidates"
            continue
        match = _CANDIDATE.match(line) if inside else None
        if match:
            if len(found) >= MAX_CANDIDATES:
                return found, True
            found.append((number, match.group(1)))
    return found, False


def _candidate_problems(name, lines):
    found, cut = _candidates(lines)
    problems, first = [], {}
    for number, each in found:
        if not _ID.match(each) or len(each) > 64:
            problems.append("%s line %d: the candidate ID %s is not a lowercase kebab-case slug"
                            % (name, number, _shown(each)))
        key = unicodedata.normalize("NFKC", each).casefold()
        if key in first:
            problems.append("%s line %d: the candidate ID %s repeats the one on line %d"
                            % (name, number, _shown(each), first[key]))
        else:
            first[key] = number
    if cut:
        problems.append("%s has more than %d candidates; the rest were not looked at"
                        % (name, MAX_CANDIDATES))
    return problems


def _area(writer, folder, kind, statuses, budget, problems):
    try:
        entries = writer.list_dir(folder, lenient=True)
    except (safefs.SafeFsError, projectfs.WriteConflict) as exc:
        problems.append("%s: cannot be listed: %s" % (folder, display.ascii_text(str(exc))[:160]))
        return
    seen = {}
    for name, entry_kind in entries or ():
        shown = "%s/%s" % (folder, _shown(name))
        if entry_kind == "dir":
            continue
        folded = name.casefold()
        if entry_kind == writer.BAD_NAME:
            problems.append("%s: the name is not usable" % shown)
            continue
        if not folded.endswith(".md") or folded == "readme.md":
            continue
        if folded in seen:
            problems.append("%s: collides with %s, which differs only in letter case"
                            % (shown, _shown(seen[folded])))
        seen[folded] = name
        if entry_kind != "file":
            problems.append("%s: is a %s, not a regular file, so it was not read"
                            % (shown, entry_kind))
            continue
        trouble = _name_problem(kind, name)
        if budget[0] <= 0 or budget[1] <= 0:
            problems.append("%s: not looked at; more than %d documents or %d bytes"
                            % (shown, MAX_FILES, MAX_BYTES))
            continue
        budget[0] -= 1
        try:
            state = writer.read_file("%s/%s" % (folder, name))
        except (safefs.SafeFsError, projectfs.WriteConflict) as exc:
            problems.append("%s: cannot be read: %s" % (shown, display.ascii_text(str(exc))[:160]))
            continue
        if state is None:
            continue
        budget[1] -= len(state.data)
        if trouble:
            problems.append("%s: %s" % (shown, trouble))
        lines = list(_lines(state.data.decode("utf-8", "replace")))
        problems.extend(_status_problems(kind, statuses, shown, lines))
        if kind == "roadmap":
            problems.extend(_candidate_problems(shown, lines))


def examine(writer):
    """``(problems, warnings)`` for the specs, roadmaps and decisions of the project `writer` holds.
    Both are empty for a project without the module."""
    if not has_module(writer):
        return [], []
    problems, budget = [], [MAX_FILES, MAX_BYTES]
    for folder, kind, statuses in AREAS:
        _area(writer, folder, kind, statuses, budget, problems)
    if len(problems) > MAX_REPORTED:
        extra = len(problems) - MAX_REPORTED
        problems = problems[:MAX_REPORTED] + ["%d more document problems are not listed" % extra]
    return problems, []
