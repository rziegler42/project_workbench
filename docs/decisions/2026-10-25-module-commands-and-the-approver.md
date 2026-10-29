# What prompts for the module commands, so the owner's approver can review them

Status: Accepted by the owner on 2026-10-25; question 1 replaced for safe-git remove and remote-runner submit and fetch by 2026-10-29-workbench-asks-for-remove-submit-and-fetch
Date: 2026-10-25

## Context

The owner's approver is a `PermissionRequest` hook at the user level. It reviews a command before it runs, logs a verdict, and
for two rules can allow it. It sees a command only when an `ask` rule raised a prompt for it, and it matches the raw text of the
command against the spellings of the global helpers (`claude-workflow`, `remote-runner`, `ask-codex archive`) and plain
`git push` (`docs/specs/global-config-inventory.md`, F-A1 and F-B1).

The module commands that replace those helpers are `wb run safe-git commit` and `remove`, and the `remote-runner` module's
`submit` and `fetch`. The project's render holds no `ask` for them (the inventory's F-B2, read on 2026-10-25), and
`docs/specs/remote-runner.md` says its module renders none and defers the question; `docs/specs/safe-git.md` states no
`ask` for them. Whether they prompt is therefore decided by the owner's own `allow` rules and
`auto` mode, which the workbench never writes (`2026-10-19-restrictive-only-permissions`). Replacing a global helper by its
module (moves M9, M14 and M16 of the inventory) would remove the prompt and, with it, the approver's review, unless something
raises a prompt for the module spelling and the approver learns that spelling.

Two constraints bear on the choice. A project guarantees a floor, its own `deny` and `ask` rules among it, under any global
setup, and does not write the user level (`2026-10-24-project-guarantees-a-floor`). And the approver is the owner's
enforcement point: model calls go through vendor bridges and the enforcement point stays in the owner's configuration
(`2026-10-22-model-calls-go-through-vendor-bridges`).

Whether a global `PermissionRequest` hook fires on a prompt that a project `ask` raised, in an interactive session, is not
known. The 2026-10-24 trial ran `-p`, where an `ask` is denied and not prompted.

## Decision

The owner chose **option 2** for Question 1 and **option 1 (not delegated)** for Question 2, and accepted the record on
2026-10-25. The choices are set out below. Nothing here is built, and nothing at the user level changes by writing this record.

**Question 1: what raises a prompt for the module commands.** One of:

1. **The workbench renders an `ask`** for `wb run safe-git commit` and `remove` and for `wb run remote-runner submit` and
   `fetch`. It is a change to the `safe-git` and `remote-runner` modules and their specs, and so a separate plan; the neutral
   rules may hold an `ask` (`2026-10-19-restrictive-only-permissions`). The prompt
   then holds in every attached project under any global setup (it is part of the floor), and the approver sees it where the
   F-B1 test shows that the global hook fires.
2. **The owner adds global `ask` entries** for those four spellings at the user level, beside the entries for the global
   helpers. No workbench change. The prompt and the approver's review apply on the owner's machine only, and are not a
   guarantee of the project.
3. **The owner accepts** that the module commands prompt only by the owner's `allow` rules and `auto` mode, and that the
   approver may not review them. A project without the owner's global settings gets no prompt from the workbench for them,
   and the approver sees none. Moves M9, M14 and M16 are then decided again, with that loss named.

**Question 2: whether the module commit spelling is delegated** the way `claude-workflow-commit` is, so that the approver can
allow a commit on a favorable verdict without asking the owner. This applies only if the prompt in Question 1 exists.

1. **Not delegated.** Every commit prompts the owner and carries the approver's verdict. This is the default of the plan.
2. **Delegated**, as the global spelling is, to keep today's behavior.

## Alternatives considered

- **Add the module spellings to the approver without deciding what prompts.** Rejected: the approver sees only commands that an
  `ask` raised, so the spellings would match nothing the owner cannot already see.
- **A project-rendered hook that does the approver's work.** Rejected: the enforcement point stays in the owner's configuration
  (`2026-10-22-model-calls-go-through-vendor-bridges`), and the workbench does not write a harness's global configuration.
- **Delegate the module commit spelling by default.** Rejected as a default: delegation widens what runs unprompted, and this
  record does not make that choice for the owner.

## Consequences

- **Option 1:** a prompt on every commit, removal, remote submit and fetch in every attached project, whoever owns it. That is
  more prompting than today for a person who relies on the approver's delegation, and it is the only option that is part of
  the floor. It needs its own plan, with tests of the rendered rules.
- **Option 2:** nothing changes in a project and the owner keeps the review on their own machine. A clone on another machine,
  or another person, gets no prompt from the workbench. It is an owner step and costs a user-level edit that the agent cannot
  make.
- **Option 3:** the least work. The approver does not review the module commands at all, and its review of a commit, removal
  or remote job ends when its global helper goes. The owner keeps the global helpers in place, or accepts that loss.
- **Question 2:** an undelegated commit asks the owner every time; a delegated one does not, when the verdict allows it.
- In every option the approver's rubric and rule edits (stage 1 of M1) are owner steps. The plan
  `2026-10-25-approver-coverage-for-module-spellings` proceeds past this record only under option 2.

## Verification

Read only. On 2026-10-25, at commit `9116d9a` of this repository (the inventory spec's F-B2 and M1 text was then edited in
the same increment to cite this record), the inventory spec, `safe-git.md`, `remote-runner.md`, the
accepted decisions named above and the plan were read; no command was run to test a prompt. The F-B1 behavior (a global hook
firing on a project `ask` in an interactive session) is untested, and the plan's Increment C records its test.

## Related files and decisions

- `docs/specs/global-config-inventory.md` (F-A1, F-B1, F-B2, move M1), `docs/specs/safe-git.md`, `docs/specs/remote-runner.md`
- `docs/plans/2026-10-25-approver-coverage-for-module-spellings.md`
- `2026-10-19-restrictive-only-permissions`, `2026-10-22-model-calls-go-through-vendor-bridges`,
  `2026-10-24-project-guarantees-a-floor`
