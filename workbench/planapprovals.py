"""Plan approval records and the two commands that use them: ``approve-plan`` and ``plan-status``.

The installer records what the project's declared approval command reports for a plan and reads no plan
itself (``approvalcmd.py``; ``docs/specs/trust-and-approval.md``, "Plan approval records"). The record is
``projects/<id>/plan-approvals`` in the guarded store, strict JSON::

    {"format": 2, "approvals": [{"plan": "<path in the project>", "region_hash": "<64 hex>",
                                 "declaration_hash": "<64 hex>", "helper_sha256": "<64 hex>",
                                 "approver": "<user>", "time": "<UTC>", "workbench_version": "<text>"}, ...]}

The file is ``format: 2`` when written; a ``format: 1`` file is read (it has no delegated entries). A format-2 entry
may also hold ``delegate``, an object that says which provider found the review converged (``delegation.py``;
"Delegated plan approval records"). Such an entry counts only while the owner's personal setting for the
checkpoint ``approve-plan`` reads ``delegate`` when it is read; an entry without ``delegate`` is never affected by
the setting.

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
import hashlib
import json
import os
import re
import stat

from . import __version__, approvalcmd, approvals, approve, levellog, levelrun, levels, settings
from .wbkit import display, jsonstrict, safefs

FORMAT = 2
FORMATS = (1, 2)
MAX_ENTRIES = 2000
CONFIRM_CHARS = 12
DIGEST_CHARS = 32
MAX_FILE_BYTES = 2 * 1024 * 1024

_HEX = re.compile(r"[0-9a-f]{64}\Z")
_DIGEST = re.compile(r"[0-9a-f]{32}\Z")
_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_REVIEW = re.compile(r"plan-[0-9a-f]{16}\Z")
_FIELDS = ("plan", "region_hash", "declaration_hash", "helper_sha256", "approver", "time", "workbench_version")
_DELEGATE = ("provider", "provider_declaration_hash", "provider_helper_sha256", "bridge", "model", "rounds_used",
             "bound", "review", "document_sha256")

Approval = collections.namedtuple("Approval", " ".join(_FIELDS + ("delegate",)), defaults=(None,))
Status = collections.namedtuple("Status", "state differs withdrawn", defaults=(False,))

APPROVED, CHANGED, NOT_APPROVED = "approved", "changed since approval", "not approved"

STATUS_USAGE = "usage: wb plan-status <plan> [--digest]\n"
APPROVE_USAGE = ("usage: wb approve-plan <plan>   (owner-run, terminal only)\n"
                 "       wb approve-plan <plan> --digest <32 hexadecimal characters>   (when it is set to ask)\n")
WITHDRAWN = "delegated approval withdrawn: approve-plan is not delegate"


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


def _delegate(value):
    """`value`, the ``delegate`` object of an entry, as a dict, or ``PlanApprovalError``."""
    if not isinstance(value, dict) or set(value) != set(_DELEGATE):
        raise PlanApprovalError("a plan approval has a bad delegate")
    for key in ("provider", "bridge"):
        _text(value, key)
    if value["model"] is not None:
        _text(value, "model", 200)
    for key in ("provider_declaration_hash", "provider_helper_sha256", "document_sha256"):
        if not isinstance(value[key], str) or not _HEX.match(value[key]):
            raise PlanApprovalError("a plan approval has a bad delegate %s" % key)
    for key in ("rounds_used", "bound"):
        if type(value[key]) is not int or not 1 <= value[key] <= 5:
            raise PlanApprovalError("a plan approval has a bad delegate %s" % key)
    if not isinstance(value["review"], str) or not _REVIEW.match(value["review"]):
        raise PlanApprovalError("a plan approval has a bad delegate review")
    return {key: value[key] for key in _DELEGATE}


def parse(data):
    """The entries of a plan approvals file as a list of ``Approval``, or ``PlanApprovalError``."""
    try:
        document = jsonstrict.parse_object(data, MAX_FILE_BYTES)
    except ValueError as exc:
        raise PlanApprovalError("the plan approvals file is not valid (%s)" % display.ascii_text(str(exc))[:80])
    if set(document) != {"format", "approvals"} or type(document["format"]) is not int \
            or document["format"] not in FORMATS or not isinstance(document["approvals"], list):
        raise PlanApprovalError("the plan approvals file does not have the expected format")
    if len(document["approvals"]) > MAX_ENTRIES:
        raise PlanApprovalError("the plan approvals file holds more than %d approvals" % MAX_ENTRIES)
    found = []
    for entry in document["approvals"]:
        allowed = [set(_FIELDS), set(_FIELDS) | {"delegate"}] if document["format"] == 2 else [set(_FIELDS)]
        if not isinstance(entry, dict) or set(entry) not in allowed:
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
                              _text(entry, "approver"), entry["time"], _text(entry, "workbench_version"),
                              _delegate(entry["delegate"]) if "delegate" in entry else None))
    return found


def serialize(entries):
    listed = []
    for entry in entries:
        item = entry._asdict()
        if item["delegate"] is None:
            del item["delegate"]
        listed.append(item)
    document = {"format": FORMAT, "approvals": listed}
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


def delegating(guarded, found):
    """Whether the owner's personal setting for the checkpoint ``approve-plan`` reads ``delegate`` now, for the
    process module `found` (a ``Resolved``). A missing, damaged or other value reads as not delegating."""
    effective = settings.effective(settings.load(guarded), found.checkpoints, ())
    return effective.checkpoints.get(settings.APPROVE_PLAN) == settings.DELEGATE


def status(entries, plan, region_hash, declaration_hash, helper_sha256, delegating=False):
    """The ``Status`` of `plan` against the values computed now. ``differs`` names what is not the same as in
    the newest entry for the plan, and is empty unless the state is ``changed since approval``. An entry with a
    delegate counts only when `delegating` is true; when it is not and such an entry equals all four values, the
    state is ``not approved`` and ``withdrawn`` is true."""
    wanted = Approval(plan, region_hash, declaration_hash, helper_sha256, "", "", "")
    counted = [entry for entry in entries if entry.delegate is None or delegating]
    if any(_same(entry, wanted) for entry in counted):
        return Status(APPROVED, ())
    if any(_same(entry, wanted) for entry in entries):
        return Status(NOT_APPROVED, (), True)
    named = [entry for entry in counted if entry.plan == plan]
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


def status_arguments(tokens):
    """``(plan, preview)`` for ``<plan>`` or ``<plan> --digest``, or None."""
    if len(tokens) == 2 and tokens[1] == "--digest" and not tokens[0].startswith("-"):
        return tokens[0], True
    plan = one_argument(tokens)
    return (plan, False) if plan is not None else None


def approve_arguments(tokens):
    """``(plan, digest)`` for ``<plan>`` (digest None) or ``<plan> --digest <32 hex>``, or None."""
    if len(tokens) == 3 and tokens[1] == "--digest" and not tokens[0].startswith("-") \
            and _DIGEST.match(tokens[2]):
        return tokens[0], tokens[2]
    plan = one_argument(tokens)
    return (plan, None) if plan is not None else None


def digest_of(resolved, plan, report):
    """The digest that binds a confirmation to what was previewed: the first 32 hexadecimal characters of the SHA-256 of
    the project, the approval command (declaration and helper), the plan's path, its region hash and what the approval
    does not cover. Another clone, another command or another plan gives another digest."""
    lines = ["approve-plan", resolved.project_id, resolved.declaration, resolved.helper_sha256, plan,
             report.region_hash] + ["unhashed:%s" % name for name in report.unhashed]
    return hashlib.sha256("\n".join(lines).encode("utf-8", "replace")).hexdigest()[:DIGEST_CHARS]


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
    """``plan-status <plan>``: one line on standard output. Exit 0 approved, 1 anything else, 2 usage.

    ``plan-status <plan> --digest`` is the read-only preview of ``approve-plan`` at the level ``ask``: it prints what an
    approval would bind and the digest that the approval must carry, and exits 0. It writes nothing."""
    parsed = status_arguments(tokens)
    if parsed is None:
        err.write(STATUS_USAGE)
        return 2
    argument, preview = parsed
    try:
        resolved, plan, report = _current(guarded, argument, cwd)
        entries = load(guarded, resolved.project_id)
    except (PlanApprovalError, approvalcmd.ApprovalError) as exc:
        return _refuse(err, str(exc))
    if preview:
        _describe(out, resolved, plan, report, entries)
        out.write("digest: %s\n" % digest_of(resolved, plan, report))
        return 0
    found = status(entries, plan, report.region_hash, resolved.declaration, resolved.helper_sha256,
                   delegating(guarded, resolved))
    shown = display.ascii_text(plan)
    if found.state == APPROVED:
        out.write("approved: %s\n" % shown)
        return 0
    if found.state == CHANGED:
        out.write("changed since approval: %s (%s)\n" % (shown, ", ".join(found.differs)))
    else:
        out.write("not approved: %s%s\n" % (shown, " (%s)" % WITHDRAWN if found.withdrawn else ""))
    return 1


def _describe(out, resolved, plan, report, entries):
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


def _show(out, resolved, plan, report, entries):
    _describe(out, resolved, plan, report, entries)
    out.write("\nThe approval binds this path, this region hash and the exact command above. Read the plan "
              "first.\nTo approve it, type the first %d characters of the region hash and press Enter.\n"
              "Anything else cancels and records nothing.\n> " % CONFIRM_CHARS)
    out.flush()


TERMINAL_ONLY = ("approving a plan is owner-run: standard input and output must both be terminals. "
                 "Run this command yourself, from your own terminal.")


def approve_plan(guarded, tokens, stdin, out, err, *, cwd=None):
    """``approve-plan <plan>``: owner-run, from a terminal; or, when the owner has set it to ``ask`` or ``none``, an
    agent's run without one (``docs/specs/command-permissions.md``). Exit 0 recorded or already recorded, 1 refused or
    cancelled with nothing written, 2 usage, 3 recorded but not logged, 130 interrupted. An interrupt of the run without a
    terminal logs a ``refused`` outcome; if it came after the record was written, the record stands."""
    parsed = approve_arguments(tokens)
    if parsed is None:
        err.write(APPROVE_USAGE)
        return 2
    argument, given = parsed
    if given is None and approve.is_terminal(stdin) and approve.is_terminal(out):
        return _approve_at_terminal(guarded, argument, stdin, out, err, cwd)
    return _approve_without_terminal(guarded, argument, given, out, err, cwd)


def _approve_without_terminal(guarded, argument, given, out, err, cwd):
    """The agent's run at ``ask`` (with the digest of the preview) or ``none`` (without one). Anything else is the
    terminal-only refusal. The attempt is written after every check and just before the record; the outcome follows."""
    try:
        start = cwd if cwd is not None else os.getcwd()
    except OSError as exc:
        return _refuse(err, "the working directory cannot be read: %s" % (exc.strerror or "unknown error"))
    try:
        level, ident, _ = levelrun.level_now(guarded, start, settings.APPROVE_PLAN)
    except levelrun.Refusal as exc:
        return _refuse(err, str(exc))
    if level == levels.NONE and given is not None:
        return _refuse(err, "approve-plan takes no digest at the level none: unknown argument --digest")
    if given is not None and level != levels.ASK:
        return _refuse(err, "approving a plan with a digest is owner-run unless the level of approve-plan is ask here "
                            "and its rendered rule is present: the owner approves a plan with `wb approve-plan <plan>` "
                            "from a terminal")
    if level not in (levels.ASK, levels.NONE) or (level == levels.ASK and given is None):
        return _refuse(err, TERMINAL_ONLY)
    try:
        resolved, plan, report = _current(guarded, argument, cwd)
        if resolved.project_id != ident:
            return _refuse(err, "the project the level was read for is not the project the plan belongs to; nothing was "
                                "recorded")
        if level == levels.ASK and given != digest_of(resolved, plan, report):
            return _refuse(err, "the digest does not match the plan as it is now; preview it again with "
                                "`wb plan-status <plan> --digest`; nothing was recorded")
        again, same_plan, second = _current(guarded, argument, cwd)
        if (again.declaration, again.helper_sha256, again.project_id, same_plan, second) != \
                (resolved.declaration, resolved.helper_sha256, resolved.project_id, plan, report):
            return _refuse(err, "the plan, the approval command or its declaration changed while the digest was "
                                "checked, so it no longer holds; nothing was recorded")
        entry = Approval(plan, report.region_hash, resolved.declaration, resolved.helper_sha256,
                         approve.approver_name(), approvals.utc_now(), __version__)
        written, op = levelrun.logged(
            guarded, settings.APPROVE_PLAN, level, lambda: add(guarded, resolved.project_id, entry),
            "digest:%s" % given if given else "",
            needed=not any(_same(item, entry) for item in load(guarded, resolved.project_id)))
    except levellog.LogError as exc:
        return _refuse(err, "%s; nothing was recorded" % exc)
    except (PlanApprovalError, approvalcmd.ApprovalError) as exc:
        return _refuse(err, str(exc))
    except KeyboardInterrupt:
        out.write("\ninterrupted: the plan approvals and the level log show what was done\n")
        return 130
    out.write("%s: %s (region %s)\n" % ("approved" if written else "already approved", display.ascii_text(plan),
                                        report.region_hash))
    try:
        levelrun.done(guarded, op)
    except levellog.OutcomeError as exc:
        err.write("the approval was recorded, but its outcome was not logged: %s\n" % display.clean(str(exc)))
        return 3
    return 0


def _approve_at_terminal(guarded, argument, stdin, out, err, cwd):
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
