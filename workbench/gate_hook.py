"""``gate <harness>``: the edit gate, the command a harness's rendered hook runs.

It reads one tool call as JSON on standard input and decides whether a file edit may go ahead while a plan is under
way and not approved (``docs/specs/trust-and-approval.md``, "Checkpoint and cap settings, and the edit gate"). It
prints nothing and returns 0 to allow. It prints one ``refused:`` line on standard error and returns 2 to refuse,
because 2 is the only code the harness takes for a block; every other outcome, a crash included, is a refusal, and
a total deadline of ``DEADLINE`` seconds ends in a refusal too (a hook that is cut off by the harness lets the call
through).

The installer knows no plan format. The process module's declared ``active`` command names the plans under way
(``approvalcmd.active_plans``) and its ``region`` command gives each plan's hash, which is compared with the plan
approval records (``planapprovals``), the same split ``approve-plan`` uses. In order:

1. The input is one JSON object of at most ``MAX_INPUT`` bytes with a string ``cwd``, a string ``tool_name`` and an
   object ``tool_input``. The project is found from ``cwd``; none is a refusal.
2. A project with no installed process module that declares ``approval.active`` is allowed; more than one is refused.
3. ``active`` is run. No plan under way is an allow; a command that fails is a refusal.
4. The targets are read from ``tool_input`` by the table the harness module's layout declares under
   ``hooks.targets`` (``layout.py``); the installer holds no tool name. A tool outside it, a missing, empty or
   non-string field, a NUL and an overlong path are refusals. Every target is judged.
5. A target is placed against ``cwd`` with ``.`` and ``..`` folded lexically; a ``..`` that follows a link is a
   refusal. Containment in the root compares with case and Unicode folded. A target outside the root passes. Inside
   the root a link in any component that exists is a refusal, and the same plan spelled in another case is a
   refusal, not a pass. A target that is exactly a plan under way passes.
6. Any other target passes only when every plan under way is ``approved``; the first that is not stops the check.

Nothing is written in the project or the store beyond the bootstrap every command makes.
"""

import errno
import os
import signal
import stat
import threading
import time
import unicodedata

from . import approvalcmd, planapprovals
from .wbkit import display, jsonstrict

MAX_INPUT = 65536
DEADLINE = 10.0
MAX_TARGET = 4096

USAGE = "usage: wb gate <harness>\n"


class Refusal(Exception):
    """The call is not allowed; the message says why in one line."""


class _Deadline(BaseException):
    """The total deadline passed. Not an ``Exception``, so no handler in between can take it for a failure."""


# --- the input --------------------------------------------------------------------------------


def _read(stdin):
    stream = getattr(stdin, "buffer", stdin)
    data = stream.read(MAX_INPUT + 1)
    if isinstance(data, str):
        data = data.encode("utf-8", "surrogatepass")
    try:
        document = jsonstrict.parse_object(data, MAX_INPUT)
    except ValueError as exc:
        raise Refusal("the hook input is not one JSON object within %d bytes (%s)"
                      % (MAX_INPUT, display.ascii_text(str(exc))[:80]))
    cwd, tool, given = document.get("cwd"), document.get("tool_name"), document.get("tool_input")
    if not isinstance(cwd, str) or not isinstance(tool, str) or not isinstance(given, dict):
        raise Refusal("the hook input needs a string cwd, a string tool_name and an object tool_input")
    return cwd, tool, given


# --- placing a target -------------------------------------------------------------------------


def _fold(text):
    """`text` with case and Unicode variants folded, so another spelling of a name compares equal."""
    return unicodedata.normalize("NFKD", unicodedata.normalize("NFKD", text).casefold())


def _is_link(path):
    """Whether `path` is a symbolic link; False when it does not exist. Anything else unreadable is a refusal."""
    try:
        return stat.S_ISLNK(os.lstat(path).st_mode)
    except OSError as exc:
        if exc.errno in (errno.ENOENT, errno.ENOTDIR):
            return False
        raise Refusal("a component of a target cannot be examined: %s" % (exc.strerror or "unknown error"))


def _components(cwd, target):
    """The components of `target` placed against `cwd`, with ``.`` and ``..`` folded lexically. A ``..`` that
    would step out of a link is refused, because the file system would not step where the text does."""
    full = target if target.startswith("/") else cwd.rstrip("/") + "/" + target
    parts = []
    for piece in full.split("/"):
        if piece in ("", "."):
            continue
        if piece == "..":
            if parts:
                if _is_link("/" + "/".join(parts)):
                    raise Refusal("a target steps out of a link with '..'")
                parts.pop()
            continue
        parts.append(piece)
    return parts


def _check_cwd(cwd):
    if not cwd.startswith("/") or "\0" in cwd or len(cwd) > MAX_TARGET:
        raise Refusal("the working directory is not an absolute path")
    if cwd != "/" and any(piece in ("", ".", "..") for piece in cwd[1:].split("/")):
        raise Refusal("the working directory is not a plain absolute path")


def _target_text(tool, given, field):
    value = given.get(field)
    if not isinstance(value, str) or not value:
        raise Refusal("the %s call has no %s to place" % (display.ascii_text(tool)[:40], field))
    if "\0" in value:
        raise Refusal("the %s of the %s call holds a NUL byte" % (field, display.ascii_text(tool)[:40]))
    if len(value) > MAX_TARGET:
        raise Refusal("the %s of the %s call is longer than %d characters" % (field, display.ascii_text(tool)[:40],
                                                                               MAX_TARGET))
    return value


def _within(root_parts, parts):
    return len(parts) >= len(root_parts) and [_fold(p) for p in parts[:len(root_parts)]] == root_parts


def _resolved(parts):
    """The components of the path `parts` with every link in it followed, as far as it exists. A loop or a
    path that cannot be resolved is a refusal."""
    mode = getattr(os.path, "ALLOW_MISSING", None)
    if mode is None:
        raise Refusal("this Python cannot resolve a path that may not exist yet")
    try:
        return [piece for piece in os.path.realpath("/" + "/".join(parts), strict=mode).split("/") if piece]
    except (OSError, ValueError, RuntimeError) as exc:
        raise Refusal("a target cannot be resolved: %s" % display.ascii_text(str(exc))[:80])


def _judge(root_parts, plans, cwd, target):
    """``"outside"``, ``"plan"`` or ``"inside"`` for the path `target`, or ``Refusal``. `root_parts` are the folded
    components of the project root with its links followed. A target that lies outside as spelled is followed
    through its links, and is judged where it lands: an alias of the root is not a way out of the gate."""
    parts = _components(cwd, target)
    if not _within(root_parts, parts):
        parts = _resolved(parts)
        if not _within(root_parts, parts):
            return "outside"
    here = "/" + "/".join(parts[:len(root_parts)])
    for part in parts[len(root_parts):]:
        here = here.rstrip("/") + "/" + part
        if _is_link(here):
            raise Refusal("a component of the target is a symbolic link: %s" % display.ascii_text(part)[:80])
        if not os.path.lexists(here):
            break
    inner = parts[len(root_parts):]
    for plan in plans:
        named = plan.split("/")
        if [_fold(p) for p in inner] == [_fold(p) for p in named]:
            if inner != named:
                raise Refusal("the target spells the plan %s in another way" % display.ascii_text(plan)[:120])
            return "plan"
    return "inside"


# --- the decision -----------------------------------------------------------------------------


def _remaining(deadline):
    left = deadline - time.monotonic()
    if left <= 0:
        raise Refusal("the gate did not finish in time")
    return left


def _approved(guarded, found, plans, deadline):
    """Nothing when every plan in `plans` reads ``approved``; otherwise ``Refusal`` naming the first that does not."""
    entries = planapprovals.load(guarded, found.project_id)
    for plan in plans:
        rel = planapprovals.plan_path(found.root, found.root, plan)
        report = approvalcmd.region(guarded, found, rel, timeout=min(approvalcmd.TIMEOUT, _remaining(deadline)))
        state = planapprovals.status(entries, rel, report.region_hash, found.declaration, found.helper_sha256)
        if state.state != planapprovals.APPROVED:
            raise Refusal("the plan %s is %s%s; the owner approves it with `wb approve-plan %s`" % (
                display.ascii_text(rel), state.state, " (%s)" % ", ".join(state.differs) if state.differs else "",
                display.ascii_text(rel)))


def decide(guarded, table, cwd, tool, given, deadline):
    """Return when the call may go ahead; raise ``Refusal`` otherwise. `table` maps each tool the hook covers to the
    fields of its input that name a file it writes; a tool outside it is refused. `deadline` is a
    ``time.monotonic`` value."""
    _check_cwd(cwd)
    try:
        root, ident, installed = approvalcmd.installed_modules(cwd)
    except approvalcmd.ApprovalError as exc:
        raise Refusal(str(exc))
    declaring = [item for item in installed if item.module.approval and item.module.approval.get("active")]
    if not declaring:
        return
    if len(declaring) > 1:
        raise Refusal("more than one installed module declares an approval command that lists the plans under "
                      "way: %s" % ", ".join(sorted("%s/%s" % (item.package, item.module.name) for item in declaring)))
    try:
        found = approvalcmd.resolved(guarded, root, ident, declaring[0])
        plans = approvalcmd.active_plans(guarded, found, timeout=min(approvalcmd.TIMEOUT, _remaining(deadline)))
    except approvalcmd.ApprovalError as exc:
        raise Refusal(str(exc))
    if not plans:
        return
    fields = table.get(tool)
    if fields is None:
        raise Refusal("the tool %s is not one the gate reads a target from" % display.ascii_text(tool)[:40])
    targets = [_target_text(tool, given, field) for field in fields]
    root_parts = [_fold(p) for p in _resolved([p for p in root.split("/") if p])]
    places = [_judge(root_parts, plans, cwd, target) for target in targets]
    if all(place != "inside" for place in places):
        return
    try:
        _approved(guarded, found, plans, deadline)
    except (approvalcmd.ApprovalError, planapprovals.PlanApprovalError) as exc:
        raise Refusal(str(exc))


# --- the command ------------------------------------------------------------------------------


def _arm(seconds):
    """Start the total deadline; the handler to put back, or None when there is no timer to use here."""
    if not hasattr(signal, "setitimer") or threading.current_thread() is not threading.main_thread():
        return None

    def fire(signum, frame):
        raise _Deadline()

    previous = signal.signal(signal.SIGALRM, fire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    return previous


def _disarm(previous):
    if previous is not None:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def run(stdin, err, prepare, *, deadline=DEADLINE):
    """Decide the call on `stdin`. `prepare` returns ``(guarded store, table)``, or raises ``Refusal``. Returns 0 to
    allow; otherwise writes one ``refused:`` line to `err` and returns 2."""
    reason = None
    previous = None
    try:
        try:
            previous = _arm(deadline)
            started = time.monotonic()
            guarded, table = prepare()
            cwd, tool, given = _read(stdin)
            decide(guarded, table, cwd, tool, given, started + deadline)
        except Refusal as exc:
            reason = str(exc)
        except _Deadline:
            raise
        except Exception as exc:
            reason = "the gate failed (%s)" % type(exc).__name__
        finally:
            _disarm(previous)
    except _Deadline:
        reason = "the gate did not finish within %g seconds" % deadline
    if reason is None:
        return 0
    err.write("refused: %s\n" % display.clean(reason).replace("\n", " ")[:600])
    return 2
