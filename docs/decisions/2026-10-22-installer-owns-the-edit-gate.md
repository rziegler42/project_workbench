# The installer owns the edit gate and its hook; the process module names what is under way

Status: Proposed
Date: 2026-10-22

## Context

A `Status: Approved` line is informational, and `plan-status` is a command an agent must choose to run, so nothing
stops an agent that goes on editing after its plan changed. The gate has to refuse an edit while a plan under way is
not approved. Two other things must hold: the installer knows nothing of plans
(`2026-10-22-plan-check-in-the-shipped-helper`), and a hook is code that runs at every tool call, so what may be
named there decides how much approving a module covers.

## Decision

The gate is the installer's command, `wb gate claude`, and the Claude harness layout renders one fixed hook that runs
it as `wb gate claude || exit 2`. The process module declares, in data, which checkpoints and caps it has and which
of its command's arguments lists the plans under way; its pinned helper answers that question. The installer asks
the plan records whether each listed plan is approved. It reads no plan and names no module.

## Alternatives considered

- **A hook the module ships.** A module that could name any command at every tool call would widen what approval
  of that module covers, and the hook would have to know the plan format and the records. Rejected.
- **A check inside `safe-git`.** It runs at commit time, after the edits, and only for the one module. It stays a
  candidate as an addition, not as the gate.
- **No hook; instruction only.** What exists today. Rejected as the reason for this decision.

## Consequences

- The installer gains two commands, `wb settings` and `wb gate`, and the settings file a `caps` key.
- Another harness needs its own `wb gate <harness>` input shape and its own hook form; none is built here.
- The gate stops a mistaken agent and not a hostile one: it is advice against shell writes and a `Status:` edit.
- An exit code other than 2 does not block, so the rendered command forces 2 and the gate bounds itself under
  the harness's timeout. A `wb` that is not on the hook's `PATH` blocks every edit while a plan is under way
  (and, because of `|| exit 2`, every edit at all); that is a failure the owner can see and fix.

## Verification

Plan `2026-10-22-checkpoint-settings-and-caps`, increments E and F, and its criterion 9, an owner-run check of the
rendered hook in a scratch project with the installed Claude. Accepting this decision is the owner's act, after
that evidence.

## Related files and decisions

- `docs/specs/trust-and-approval.md`, `docs/specs/harness-modules.md`, `docs/specs/module-contract.md`
- [2026-10-22-installer-records-plan-approval-module-computes-region](2026-10-22-installer-records-plan-approval-module-computes-region.md)
- [2026-10-22-plan-check-in-the-shipped-helper](2026-10-22-plan-check-in-the-shipped-helper.md)
