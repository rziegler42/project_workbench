"""Plan approval records and the two commands that use them: ``approve-plan`` and ``plan-status``.

The installer records what the project's declared approval command reports for a plan and reads no plan
itself (``approvalcmd.py``; ``docs/specs/trust-and-approval.md``, "Plan approval records"). The record is
``projects/<id>/plan-approvals`` in the guarded store, strict JSON::

    {"format": 1, "approvals": [{"plan": "<path in the project>", "region_hash": "<64 hex>",
                                 "declaration_hash": "<64 hex>", "helper_sha256": "<64 hex>",
                                 "approver": "<user>", "time": "<UTC>", "workbench_version": "<text>"}, ...]}

A plan is ``approved`` when an entry equals all four of its path, the region hash the command reports now, the
process module's declaration hash and the helper's pinned SHA-256. If only some other entry names the plan it is
``changed since approval``; otherwise ``not approved``. An approval equal to an entry in all four is not added
again; one that differs adds an entry and the older ones stay. Reading fails closed, and a file is written whole
and atomically. The typed text of ``approve-plan`` is friction, not authentication: the barrier is the
harness's deny rule on the command.

``<plan>`` is read relative to the current directory (or absolute) and converted to a path relative to the
project root: it is refused if it is empty, holds a NUL or a ``..``, is outside the root, has a link in any
component (the last included) or is not a regular file. The same plan named two ways gets one path.
"""

import collections
import json
import os
import re
import stat

from . import __version__, approvalcmd, approvals, approve
from .wbkit import display, jsonstrict, safefs

FORMAT = 1
MAX_ENTRIES = 2000
CONFIRM_CHARS = 12
MAX_FILE_BYTES = 2 * 1024 * 1024

_HEX = re.compile(r"[0-9a-f]{64}\Z")
_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_FIELDS = ("plan", "region_hash", "declaration_hash", "helper_sha256", "approver", "time", "workbench_version")

Approval = collections.namedtuple("Approval", " ".join(_FIELDS))
Status = collections.namedtuple("Status", "state differs")

APPROVED, CHANGED, NOT_APPROVED = "approved", "changed since approval", "not approved"

STATUS_USAGE = "usage: wb plan-status <plan>\n"
APPROVE_USAGE = "usage: wb approve-plan <plan>   (owner-run, terminal only)\n"


class PlanApprovalError(Exception):
    """A record or a plan path is unusable, or the owner's answer was not given; nothing was written."""


# --- the record -------------------------------------------------------------------------------


def _file(project_id):
    return "projects/%s/plan-approvals" % project_id


def _text(entry, key, limit=64):
    value = entry[key]
    if not isinstance(value, str) or not value or len(value) > limit or not value.isprintable():
        raise PlanApprovalError("the plan approvals file has a bad %s" % key)
    return value


def parse(data):
    """The entries of a plan approvals file as a list of ``Approval``, or ``PlanApprovalError``."""
    try:
        document = jsonstrict.parse_object(data, MAX_FILE_BYTES)
    except ValueError as exc:
        raise PlanApprovalError("the plan approvals file is not valid (%s)" % display.ascii_text(str(exc))[:80])
    if set(document) != {"format", "approvals"} or type(document["format"]) is not int \
            or document["format"] != FORMAT or not isinstance(document["approvals"], list):
        raise PlanApprovalError("the plan approvals file does not have the expected format")
    if len(document["approvals"]) > MAX_ENTRIES:
        raise PlanApprovalError("the plan approvals file holds more than %d approvals" % MAX_ENTRIES)
    found = []
    for entry in document["approvals"]:
        if not isinstance(entry, dict) or set(entry) != set(_FIELDS):
            raise PlanApprovalError("a plan approval has the wrong fields")
        plan = entry["plan"]
        if not isinstance(plan, str) or not safefs.relpath_ok(plan):
            raise PlanApprovalError("a plan approval names an unsafe path")
        for key in ("region_hash", "declaration_hash", "helper_sha256"):
            if not isinstance(entry[key], str) or not _HEX.match(entry[key]):
                raise PlanApprovalError("a plan approval has a bad %s" % key)
        if not isinstance(entry["time"], str) or not _TIME.match(entry["time"]):
            raise PlanApprovalError("a plan approval has a bad time")
        found.append(Approval(plan, entry["region_hash"], entry["declaration_hash"], entry["helper_sha256"],
                              _text(entry, "approver"), entry["time"], _text(entry, "workbench_version")))
    return found


def serialize(entries):
    document = {"format": FORMAT, "approvals": [entry._asdict() for entry in entries]}
    return (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def load(store, project_id):
    """Every approval of the project, or ``[]`` when there is no file. Anything unusable is refused."""
    rel = _file(project_id)
    try:
        found = store.kind(rel)
        if found is None:
            return []
        if found != "file":
            raise PlanApprovalError("the plan approvals entry is not a regular file (%s)" % found)
        return parse(store.read(rel))
    except safefs.SafeFsError as exc:
        raise PlanApprovalError("the plan approvals file cannot be read: %s" % display.clean(str(exc))[:200])


def _same(entry, wanted):
    return (entry.plan, entry.region_hash, entry.declaration_hash, entry.helper_sha256) == \
        (wanted.plan, wanted.region_hash, wanted.declaration_hash, wanted.helper_sha256)


def add(store, project_id, approval):
    """Record `approval`. Returns True when it was written and False when an identical approval (the same
    plan, region hash, declaration hash and helper hash) was already recorded, in which case the first record is
    kept and nothing is written."""
    entries = load(store, project_id)
    if any(_same(entry, approval) for entry in entries):
        return False
    if len(entries) >= MAX_ENTRIES:
        raise PlanApprovalError("the plan approvals file already holds %d approvals" % MAX_ENTRIES)
    data = serialize(entries + [approval])
    parse(data)  # nothing is written that a read would refuse
    try:
        store.write(_file(project_id), data)
    except safefs.SafeFsError as exc:
        raise PlanApprovalError("the plan approvals file cannot be written: %s" % display.clean(str(exc))[:200])
    return True


def status(entries, plan, region_hash, declaration_hash, helper_sha256):
    """The ``Status`` of `plan` against the values computed now. ``differs`` names what is not the same as in
    the newest entry for the plan, and is empty unless the state is ``changed since approval``."""
    wanted = Approval(plan, region_hash, declaration_hash, helper_sha256, "", "", "")
    if any(_same(entry, wanted) for entry in entries):
        return Status(APPROVED, ())
    named = [entry for entry in entries if entry.plan == plan]
    if not named:
        return Status(NOT_APPROVED, ())
    newest = named[-1]
    differs = tuple(label for label, then, now in (
        ("the plan's region", newest.region_hash, region_hash),
        ("the process module's declaration", newest.declaration_hash, declaration_hash),
        ("the approval command's helper", newest.helper_sha256, helper_sha256)) if then != now)
    return Status(CHANGED, differs)


# --- the plan's path --------------------------------------------------------------------------


def plan_path(root, cwd, argument):
    """`argument` as a path relative to the project `root`, or ``PlanApprovalError``. The file is not opened."""
    shown = display.ascii_text(argument)[:80]
    if not argument or "\0" in argument:
        raise PlanApprovalError("the plan path is empty or holds a NUL byte")
    if any(part == ".." for part in argument.split("/")):
        raise PlanApprovalError("the plan path %s holds a '..'" % shown)
    full = os.path.normpath(argument if os.path.isabs(argument) else os.path.join(cwd, argument))
    prefix = root.rstrip(os.sep) + os.sep
    if not full.startswith(prefix):
        raise PlanApprovalError("the plan %s is not inside the project at %s" % (shown, display.ascii_text(root)[:120]))
    rel = full[len(prefix):]
    try:
        parts = safefs.validate_relpath(rel)
    except safefs.SafeFsError as exc:
        raise PlanApprovalError("the plan path %s is refused: %s" % (shown, display.clean(str(exc))[:120]))
    here = root
    for index, part in enumerate(parts):
        here = os.path.join(here, part)
        try:
            info = os.lstat(here)
        except OSError as exc:
            raise PlanApprovalError("the plan %s cannot be used: %s" % (shown, exc.strerror or "unknown error"))
        if stat.S_ISLNK(info.st_mode):
            raise PlanApprovalError("the plan path %s has a link in it (%s)" % (shown, display.ascii_text(part)[:60]))
        last = index == len(parts) - 1
        if (last and not stat.S_ISREG(info.st_mode)) or (not last and not stat.S_ISDIR(info.st_mode)):
            raise PlanApprovalError("the plan %s is not a regular file" % shown)
    return rel


# --- the commands -----------------------------------------------------------------------------


def one_argument(tokens):
    """The plan argument of a command that takes exactly one argument and no option, or None."""
    if len(tokens) != 1 or tokens[0].startswith("-"):
        return None
    return tokens[0]


def _refuse(err, text):
    err.write("refused: %s\n" % display.clean(text))
    return 1


def _current(guarded, argument, cwd):
    """``(resolved, plan, report)`` for the plan `argument`, or ``PlanApprovalError`` / ``ApprovalError``."""
    try:
        start = cwd if cwd is not None else os.getcwd()
    except OSError as exc:
        raise PlanApprovalError("the working directory cannot be read: %s" % (exc.strerror or "unknown error"))
    resolved = approvalcmd.resolve(guarded, start)
    plan = plan_path(resolved.root, start, argument)
    return resolved, plan, approvalcmd.region(guarded, resolved, plan)


def plan_status(guarded, tokens, out, err, *, cwd=None):
    """``plan-status <plan>``: one line on standard output. Exit 0 approved, 1 anything else, 2 usage."""
    argument = one_argument(tokens)
    if argument is None:
        err.write(STATUS_USAGE)
        return 2
    try:
        resolved, plan, report = _current(guarded, argument, cwd)
        entries = load(guarded, resolved.project_id)
    except (PlanApprovalError, approvalcmd.ApprovalError) as exc:
        return _refuse(err, str(exc))
    found = status(entries, plan, report.region_hash, resolved.declaration, resolved.helper_sha256)
    shown = display.ascii_text(plan)
    if found.state == APPROVED:
        out.write("approved: %s\n" % shown)
        return 0
    if found.state == CHANGED:
        out.write("changed since approval: %s (%s)\n" % (shown, ", ".join(found.differs)))
    else:
        out.write("not approved: %s\n" % shown)
    return 1


def _show(out, resolved, plan, report, entries):
    out.write("approve plan %s\n" % display.ascii_text(plan))
    out.write("  project:           %s\n" % display.ascii_text(resolved.root))
    out.write("  approval command:  %s/%s (declaration %s, helper %s)\n" % (
        display.ascii_text(resolved.package), display.ascii_text(resolved.module),
        resolved.declaration[:CONFIRM_CHARS], resolved.helper_sha256[:CONFIRM_CHARS]))
    if report.unhashed:
        out.write("  NOT covered by the approval (changing these later is not seen):\n")
        for name in report.unhashed:
            out.write("    - %s\n" % display.ascii_text(name))
    else:
        out.write("  the command names no part of the plan as outside the approval\n")
    out.write("  region hash:      %s\n" % report.region_hash)
    older = [entry for entry in entries if entry.plan == plan]
    if older:
        out.write("  this plan already has %d earlier approval%s; the newest was recorded %s\n" % (
            len(older), "" if len(older) == 1 else "s", older[-1].time))
    out.write("\nThe approval binds this path, this region hash and the exact command above. Read the plan "
              "first.\nTo approve it, type the first %d characters of the region hash and press Enter.\n"
              "Anything else cancels and records nothing.\n> " % CONFIRM_CHARS)
    out.flush()


def approve_plan(guarded, tokens, stdin, out, err, *, cwd=None):
    """``approve-plan <plan>``: owner-run, terminal only. Exit 0 recorded or already recorded, 1 refused or
    cancelled with nothing written, 2 usage, 130 interrupted."""
    argument = one_argument(tokens)
    if argument is None:
        err.write(APPROVE_USAGE)
        return 2
    if not (approve.is_terminal(stdin) and approve.is_terminal(out)):
        return _refuse(err, "approving a plan is owner-run: standard input and output must both be terminals. "
                            "Run this command yourself, from your own terminal.")
    try:
        resolved, plan, report = _current(guarded, argument, cwd)
        entries = load(guarded, resolved.project_id)
        _show(out, resolved, plan, report, entries)
        if stdin.readline(200).strip() != report.region_hash[:CONFIRM_CHARS]:
            out.write("cancelled: nothing was recorded\n")
            return 1
        again, same_plan, second = _current(guarded, argument, cwd)
        if (again.declaration, again.helper_sha256, again.project_id, same_plan, second) != \
                (resolved.declaration, resolved.helper_sha256, resolved.project_id, plan, report):
            return _refuse(err, "the plan, the approval command or its declaration changed while the approval "
                                "was shown; nothing was recorded")
        written = add(guarded, resolved.project_id, Approval(
            plan, report.region_hash, resolved.declaration, resolved.helper_sha256, approve.approver_name(),
            approvals.utc_now(), __version__))
    except (PlanApprovalError, approvalcmd.ApprovalError) as exc:
        return _refuse(err, str(exc))
    except KeyboardInterrupt:
        out.write("\ninterrupted: nothing was recorded\n")
        return 130
    out.write("%s: %s (region %s)\n" % ("approved" if written else "already approved", display.ascii_text(plan),
                                        report.region_hash))
    return 0
