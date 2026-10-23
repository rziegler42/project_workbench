"""``delegate-approve-plan``: a plan approved by a delegate, on the conditions the owner's setting and the plan allow.

An agent runs it; no harness denies it (``rules.AGENT_SAFE``). It writes the same ``plan-approvals`` record as
``approve-plan`` (``planapprovals.py``), with a ``delegate`` object that says which provider found the plan's review
converged. It checks, in this order, and stops at the first failure (``docs/specs/trust-and-approval.md``, "Delegated
plan approval records"):

1. the owner's personal setting for the checkpoint ``approve-plan`` reads ``delegate``, and nothing else sets it;
2. exactly one process module declares the approval command and exactly one module provides ``peer-review`` and declares
   ``convergence``, each held to the pin rules of ``wb run``;
3. the plan is read once, within the bound the helper's reader uses, and its SHA-256 is taken;
4. the region command reports the plan's region hash;
5. the process module says the plan is delegable;
6. the provider says the review of the plan converged, and that the bytes it reviewed are the bytes read in 3;
7. the plan is read and hashed again, the region command run again and both modules resolved again, and all are the
   same as before;
8. one entry is written and read back; nothing is written when an equal entry exists, whoever made it.

The installer reads no section of a plan: the process module's declared, pinned commands do. It hashes the file,
because the provider names the file it reviewed by that hash. Everything the commands print is data: it is
validated and never followed. Every refusal writes nothing.
"""

import hashlib
import os

from . import __version__, approvalcmd, approvals, approve, planapprovals
from .planapprovals import PlanApprovalError
from .wbkit import display, safefs

USAGE = "usage: wb delegate-approve-plan <plan>\n"
MAX_PLAN = 1024 * 1024


def _refuse(err, text):
    err.write("refused: %s\n" % display.clean(text).replace("\n", " "))
    return 1


def _setting(guarded):
    def check(process):
        if not planapprovals.delegating(guarded, process):
            raise approvalcmd.ApprovalError(
                "the checkpoint approve-plan is not set to delegate in the owner's personal settings, so the owner "
                "approves a plan with `wb approve-plan <plan>`; nothing was run")
    return check


def _bytes(root, plan):
    """The bytes of the plan, read once with no link followed, or ``PlanApprovalError``."""
    try:
        with safefs.Root(root, "project root") as held:
            return held.read_file(plan, MAX_PLAN)
    except safefs.SafeFsError as exc:
        raise PlanApprovalError("the plan %s cannot be read: %s" % (display.ascii_text(plan)[:80],
                                                                    display.clean(str(exc))[:200]))


def _facts(guarded, start, plan):
    """What the checks read, as a tuple that is compared whole the second time they run."""
    process, provider = approvalcmd.resolve_delegation(guarded, start)
    return (process.project_id, process.package, process.module, process.declaration, process.helper_sha256,
            provider.package, provider.module, provider.declaration, provider.helper_sha256,
            hashlib.sha256(_bytes(process.root, plan)).hexdigest(), approvalcmd.region(guarded, process, plan))


def delegate_approve_plan(guarded, tokens, out, err, *, cwd=None):
    """``delegate-approve-plan <plan>``. Exit 0 recorded or already recorded, 1 refused with nothing written, 2 usage."""
    argument = planapprovals.one_argument(tokens)
    if argument is None:
        err.write(USAGE)
        return 2
    try:
        start = cwd if cwd is not None else os.getcwd()
    except OSError as exc:
        return _refuse(err, "the working directory cannot be read: %s" % (exc.strerror or "unknown error"))
    try:
        process, provider = approvalcmd.resolve_delegation(guarded, start, check=_setting(guarded))
        plan = planapprovals.plan_path(process.root, start, argument)
        shown = display.ascii_text(plan)
        first = hashlib.sha256(_bytes(process.root, plan)).hexdigest()
        report = approvalcmd.region(guarded, process, plan)
        verdict = approvalcmd.delegable(guarded, process, plan)
        if verdict.document_sha256 != first:
            return _refuse(err, "the plan %s changed while the checks ran; nothing was recorded" % shown)
        if not verdict.delegable:
            return _refuse(err, "the plan %s is not delegable: %s" % (shown, display.ascii_text(verdict.reason)))
        review = approvalcmd.convergence(guarded, provider, plan)
        if not review.converged:
            return _refuse(err, "the review of the plan %s has not converged (%d of %d rounds); run another round or "
                                "the owner approves it" % (shown, review.rounds_used, review.bound))
        if review.document_sha256 != first:
            return _refuse(err, "the plan %s differs from the one that was reviewed; run another round, or the owner "
                                "approves it" % shown)
        now = (process.project_id, process.package, process.module, process.declaration, process.helper_sha256,
               provider.package, provider.module, provider.declaration, provider.helper_sha256, first, report)
        if _facts(guarded, start, plan) != now:
            return _refuse(err, "the plan, the approval command or the provider changed while the checks ran; "
                                "nothing was recorded")
        delegate = {"provider": provider.module, "provider_declaration_hash": provider.declaration,
                    "provider_helper_sha256": provider.helper_sha256, "bridge": review.bridge, "model": review.model,
                    "rounds_used": review.rounds_used, "bound": review.bound, "review": review.review,
                    "document_sha256": review.document_sha256}
        entry = planapprovals.Approval(plan, report.region_hash, process.declaration, process.helper_sha256,
                                       approve.approver_name(), approvals.utc_now(), __version__, delegate)
        written = planapprovals.add(guarded, process.project_id, entry)
        if written and not any(planapprovals._same(item, entry) and item.delegate == delegate
                               for item in planapprovals.load(guarded, process.project_id)):
            return _refuse(err, "the approval could not be read back from the record")
    except (PlanApprovalError, approvalcmd.ApprovalError) as exc:
        return _refuse(err, str(exc))
    if written:
        out.write("approved: %s (delegated, %d of %d rounds)\n" % (shown, review.rounds_used, review.bound))
    else:
        out.write("already approved: %s\n" % shown)
    return 0
