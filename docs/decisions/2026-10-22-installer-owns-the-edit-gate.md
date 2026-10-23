# The installer owns the edit gate and its hook; the process module names what is under way

Status: Accepted by the owner on 2026-10-23
Date: 2026-10-22

## Context

A `Status: Approved` line is informational, and `plan-status` is a command an agent must choose to run, so nothing
stops an agent that goes on editing after its plan changed. The gate has to refuse an edit while a plan under way is
not approved. Two other things must hold: the installer knows nothing of plans
(`2026-10-22-plan-check-in-the-shipped-helper`), and a hook is code that runs at every tool call, so what may be
named there decides how much approving a module covers.

## Decision

The gate is the installer's command, `wb gate <harness>`, and the harness layout renders one fixed hook that runs
it, for Claude as `wb gate claude || exit 2`. The table of tools the hook covers and the input field that names each
one's file is the harness layout's data, under `hooks.targets`, and the installer holds no tool name. The process module declares, in data, which checkpoints and caps it has and which
of its command's arguments lists the plans under way; its pinned helper answers that question. The installer asks
the plan records whether each listed plan is approved. It reads no plan and names no module.

## Alternatives considered

- **A hook the module ships.** A module that could name any command at every tool call would widen what approval
  of that module covers, and the hook would have to know the plan format and the records. Rejected.
- **A check inside `safe-git`.** It runs at commit time, after the edits, and only for the one module. It stays a
  candidate as an addition, not as the gate.
- **No hook; instruction only.** What exists today. Rejected as the reason for this decision.

## Consequences

- The tool table lives in the harness layout, so a harness is added by data and not by an installer change (this
  departs from the first wording of the plan, which put the table in the installer).
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

The owner's live check was made on 2026-10-22 with Claude Code 2.1.307: the rendered hook blocked `Write`, `Edit` and
`NotebookEdit` with exit 2 while a plan was not approved and allowed a `Write` after approval. It found one gap, in the
deny on the rendered settings file, which did not hold from a subdirectory; plan
`2026-10-22-absolute-settings-deny` renders the absolute patterns as well, and the owner's recheck on 2026-10-23 (Claude Code 2.1.309) showed the permission
rule refusing the edit from a subdirectory. It is recorded in `docs/specs/harness-modules.md`.

Built, by increments B to G: the declaration fields and the `caps` setting, `wb settings`, `code-work active`, the
gate (`workbench/gate_hook.py`, with a total deadline of 10 seconds and refusal on any doubt, and with links followed
so an alias of the project root is not a way out), the layout's `hooks` description, the Claude module providing
`hooks`, the rendered hook and the deny on the rendered settings file and `.git/info/exclude`. Not built: an effect
of `delegate`, a project-level lowering of a cap, and a hook for another harness.
- Accepted on 2026-10-23 on this evidence: the owner's live check on 2026-10-22 (Claude Code 2.1.307) and the recheck
  of the settings file deny on 2026-10-23 (Claude Code 2.1.309; plan `2026-10-22-absolute-settings-deny`). Accepted
  without checking `MultiEdit`, `CLAUDE_PROJECT_DIR`, the hook's `PATH` when Claude is not started from a shell that
  has the launcher on it, or project against local settings precedence; `harness-modules.md`, "Evidence", lists them.
  The gate runs only while a plan is under way, so nothing but the deny guards the settings file at other times, and
  the deny covers the agent's file tools and not a shell.

## Related files and decisions

- `docs/specs/trust-and-approval.md`, `docs/specs/harness-modules.md`, `docs/specs/module-contract.md`
- [2026-10-22-installer-records-plan-approval-module-computes-region](2026-10-22-installer-records-plan-approval-module-computes-region.md)
- [2026-10-22-plan-check-in-the-shipped-helper](2026-10-22-plan-check-in-the-shipped-helper.md)
