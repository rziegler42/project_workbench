# The permission levels as built: what stands, what changed and what was not built

Status: Accepted by the owner on 2026-10-26
Date: 2026-10-26

## Context

`2026-10-26-per-command-permission-levels` (accepted) set out a design before anything was built. Plan
`2026-10-26-command-permission-levels` then built part of it, and its trials and reviews changed several points. The accepted
record still says things the build does not do, and an accepted record is never rewritten. The two later records
(`2026-10-26-ask-level-spelling-limit` and `2026-10-26-ask-level-command-gate`) already cover the `ask` barrier; this record covers
the rest: the defaults, the offered levels, what was not built, and how a reader should take the earlier text.

What the build and its trials showed, with the evidence in the plan's Result and in `docs/specs/command-permissions.md`:

- The owner's probe showed that `bash -c 'wb approve-plan …'` approved a plan with no prompt in auto mode when only an `ask` rule
  stood in the way. A command gate (a second hook) was built; the repeated probe showed the wrapper forms blocked, and a script
  that makes the call running unprompted, which the owner accepted in writing.
- The review engine's declaration has no field for the levels an owner-run argument offers, and the installer may not name a
  module's command, so `wb run review-engine extend` at `ask` could not be built within the plan.

## Decision

This is a proposal. Nothing here is accepted until the owner says so. It states, point by point, how to read
`2026-10-26-per-command-permission-levels` now.

**What stands unchanged.** The four levels and their order (decision 1); the table lives in the owner's personal settings in the
guarded store and a project, plan, review, module or agent cannot supply an entry (decision 1); the floor is never in the table
(decision 3); `delegated` needs a declared gate and counts only while the table still reads it (decision 4); `ask` uses the
harness's permission prompt and needs the digest of a read-only preview (decision 5); every run above `block` is recorded in an
append-only log in the guarded store (decision 7); a stop reads as `block` and a delegate as `delegated` (decision 8, the
vocabulary).

**What changed.**

1. **The defaults (decision 2 and Question 2).** Every key ships `block`. `ask` is the owner's opt-in; no key ships `ask` or `none`
   as a default, and the targets in Question 2 are not in force. The owner chose this after the probe showed that `ask` can be
   bypassed by a script that makes the call (`2026-10-26-ask-level-command-gate`, the clarification note). A default can still be
   set for a key in code (`levels._DEFAULTS`), as a decision of its own.
2. **The offered levels (decisions 3 and 6).** Only `approve-plan` offers `ask`, `none` and `delegated`, beyond `block`. Every
   other key offers `block` only, the trust-changing commands included, and a level a key does not offer reads as `block` with a
   note. A key offers a level only from the version that builds it for that command. `accept-decision` offers `block` only (the
   record said `block` and `ask`): no agent-run acceptance command or preview exists, and `AGENTS.md` makes acceptance the owner's act.
3. **The digest (decision 5).** It is 32 hexadecimal characters (not the plan's hashed region alone) of a canonical text that also
   holds the project identifier, the approval command's declaration and helper hashes, the plan's path and what the approval does
   not cover. The preview is `wb plan-status <plan> --digest`. The first 12 characters that the owner types back at a terminal are the
   region hash's, as before, and are not the digest.
4. **How `ask` takes effect (decision 5).** The installer drops the terminal test at `ask` and `none`, and in its place requires the
   rendering record, the live hashes of the harness's settings files, and the command gate; the agent's `ask` rule names only the `wb`
   spellings and the interpreter spellings stay denied. A harness that cannot render the gate relaxes no key.
5. **The keys (decision 1).** `wb acknowledge` is not a key; the checkpoints `acknowledge-first-tier` and `acknowledge-second-tier`
   set it. The rule that a command reaching more than one key takes the strictest of them is not built, because each command
   reaches one key.
6. **Decision 8 and `2026-10-23-delegated-plan-approval`, decision 6.** `delegate` still takes effect for `approve-plan` only, as
   before. The table makes that generic (a key takes `delegated` only if it offers it) but no other key does, so the rule that decision 6
   states is unchanged in effect. The status-line wording the accepted record proposed for that record stands as the owner made it.
7. **The log (decision 7).** Two lines, an attempt written just before the change and an outcome after, and nothing for a run that
   changes nothing. A module command could not write its attempt after its checks, since the installer cannot know what the helper
   will do; it would write it before launching the helper (not built).

**What was not built.** `wb run review-engine extend` at `ask` and `none`, and the keys `reset`, `archive`, `prune`, `amend`,
`acknowledge-second-tier`, `submit-remote-job` and `push-shared-branch`: each needs its own preview digest. `extend` also needs a field
in the module declaration for the levels an owner-run argument offers, which is a change to the declaration contract and needs its own
decision. They keep `block`. A command to re-render an attached clone, a provenance check in `approve-plan`, managed settings and a
store whose approvals a shell cannot forge are deferred (`docs/plans/2026-10-26-command-permission-levels.md`, "Deferred work").

**How to read the accepted record.** It stands as the design and the reasons. Where it differs from the list above, this record and
`docs/specs/command-permissions.md` say what is true. Once the owner accepts this record, the status line of
`2026-10-26-per-command-permission-levels` may name it (for example `Accepted by the owner on 2026-10-26; decisions 2 and 6 and
Question 2 refined by 2026-10-26-permission-levels-as-built`), with its README row mirroring that; the owner makes that edit.

## Alternatives considered

- **Leave the accepted record as it is and rely on the spec.** The spec is current, but a reader of the decisions would still see
  defaults and offered levels that do not hold. Rejected: the record is what readers cite.
- **Supersede the accepted record wholesale.** Rejected: its reasons and the decisions that stand are still right, and replacing it
  would hide that.
- **Edit the accepted record.** Not allowed: an accepted decision is never rewritten.

## Consequences

- Good: a reader of the decisions finds, in one place, what the build changed and what it left out, with pointers to the spec and the
  evidence.
- Bad: three records now describe the permission levels, and a reader needs all of them. The spec is the one to read for what is true.
- The owner still decides whether to mark `2026-10-26-ask-level-spelling-limit` `Superseded` by
  `2026-10-26-ask-level-command-gate` (the latter says its items 1 to 5 stand and replaces item 6), and whether to edit the status
  line of the accepted record as proposed above.

## Evidence

- The built behavior and its tests: `docs/specs/command-permissions.md` ("Not built", "Limits", "Acceptance criteria"), commit
  `a36b4a8`; the code in `workbench/levels.py`, `workbench/settings.py`, `workbench/levellog.py`, `workbench/rendering.py`,
  `workbench/command_gate.py` and `workbench/planapprovals.py`, with `tests/test_levels.py`, `tests/test_settings.py`,
  `tests/test_levellog.py`, `tests/test_rendering.py`, `tests/test_command_gate.py` and `tests/test_approve_levels.py`.
- The probes and trials: the plan's Result for Increments A, F, I, J and H, and `docs/specs/harness-modules.md` (the `ask` prompt
  trial, Claude Code 2.1.310; the Bash hook trial, 2.1.311).
- The deferral of `extend`: the plan's Result for Increment G (stopped at its step 4) and Revision 4.
