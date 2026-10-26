# Delegated plan approval is written by the installer, from a sealed review of the same bytes

Status: Accepted by the owner on 2026-10-23; decision 6 superseded by 2026-10-26-per-command-permission-levels
Date: 2026-10-23

## Context

The accepted record `2026-10-19-mandatory-review-personal-delegation` lets a delegate give the verdict on a plan only
when the owner's personal setting for `approve-plan` is `delegate`, a `peer-review` provider is installed and approved,
and review converged within the round cap. The review engine now exists (plan `2026-10-23-review-engine`): it stores
each round's findings, the reviewer's verdict and its own reading of them, and it records no approval and grants no
authority. Nothing writes a delegated approval, and two specs disagree about who would:

- `code-work.md` says the delegation helper is "implemented with" the process module.
- `trust-and-approval.md` says the helper that writes into the guarded store is a component of the workbench that no
  module ships, and that the agent must not write the store.

Two facts shape the answer. A plan approval is bound to the plan's hashed region, which excludes the status line, the
review record and the result, and only the process module knows those section names. A review's rounds record a hash
of the whole file the reviewer read, and the review record is written into the plan after the review, which changes the
file.

## Decision

1. **The installer writes the delegated record.** A new command, `wb delegate-approve-plan <plan>`, is run by the agent
   and is not owner-run. It writes into the same `plan-approvals` record as `wb approve-plan`, in the guarded store. A
   module never writes a plan approval record; only the installer does. A module's existing writes to the store are
   unchanged and are not approvals: the review engine keeps its seal key, its rollback marks and its lock there. The
   installer learns facts only through declared, pinned commands, as it does for `region` and `active`, and treats
   their output as data.
2. **Three facts decide, each from the module that owns it.** The process module says whether the plan is delegable and
   what its hashed region is. A module that provides `peer-review` and declares a `convergence` argument says, from its
   sealed state, whether the last review of the plan converged and which file hash that round read. The owner's
   personal settings say whether `approve-plan` is `delegate`. A missing, malformed or contradictory answer is no
   approval.
3. **The review must be of exactly the bytes being approved.** The installer hashes the plan file itself and requires it
   to equal the last round's hash. No module learns another's section names. The agent therefore asks for the approval
   after the converging round and before it writes the plan's review record. An approval asked for later is refused,
   and the agent reviews once more or the owner approves. The approval still binds the hashed region, so the status
   line, the review record and the result can change afterwards.
4. **Convergence is strict.** The last round has no `blocker` or `major` finding, no meaningful finding of the window
   is pending, the reviewer's verdict and the engine's reading both say no meaningful changes, the state is sealed and
   not rolled back, and the rounds used do not exceed the bound. A rejected finding does not make a review converge,
   because the last round must itself be clean.
5. **Delegability is the process module's judgement and defence in depth.** A plan with no single Risks section, or
   whose Risks section carries a line that begins `Hard stop:`, is not delegable. A plan can omit the line; the real
   control is that hard stops stop at the time of the action.
6. **`delegate` takes effect for `approve-plan` only.** Every other checkpoint stops whatever its setting says, and
   `wb settings` shows the ignored value with a note. A project, a plan or a review cannot supply the setting.
7. **The record names its delegate.** An entry gains an optional `delegate` object with the provider module, its
   declaration and helper hashes, the bridge, the model (null when unknown), the rounds used and the bound, the review
   key and the file hash. The file moves to `format: 2`; the reader accepts 1 and 2. The four values that decide
   `approved` are unchanged, so `wb plan-status` and the edit gate read a delegated approval like an owner's.
8. **The owner's `wb approve-plan` is unchanged**, and an owner approval is never replaced by a delegated one: an entry
   that equals all four values is not added again, whoever made it.
9. **A delegated entry counts only while the setting stands.** When `wb plan-status` or the edit gate reads an entry
   that has a `delegate` object, it counts as an approval only if the owner's personal setting for `approve-plan` reads
   `delegate` at that moment. A setting that is `stop`, missing or damaged withdraws the approval: the plan reads `not
   approved`, with the reason, and the owner's own `wb approve-plan` is the way to approve it. An owner's entry is not
   affected by the setting. The provider's declaration and helper hashes in the entry are provenance and are not
   checked when the entry is read.

## Relation to accepted decisions

This record supersedes none of them. It narrows one rule and fulfils one reservation.

- **`2026-10-19-guarded-store` (narrowed).** That record says the agent must not write the store and that the owner
  records an approval by running a command themselves, which the agent's permissions deny. For the owner's own
  `approve-plan` nothing changes. For a delegated approval, the agent runs `wb delegate-approve-plan`, and the
  installer's code, not the agent, writes the record. The agent still has no write access to the store: the harness's
  deny rule on store writes is unchanged, and no module writes it. The authority is not the agent's: it is the owner's
  standing choice, the personal setting `delegate` for `approve-plan`, which is itself kept in the store, together with
  a sealed review that converged. This is an exception to "the owner runs the command", authorized by the owner's
  setting and by `2026-10-19-mandatory-review-personal-delegation`, and bounded by decisions 2 to 6. If the owner does
  not want that exception, the alternative is to keep delegated approval owner-run, which leaves the checkpoint at
  `stop`.
- **`2026-10-22-installer-records-plan-approval-module-computes-region` (fulfilled).** Its decision 5 says every
  approval is the owner's "for now" and that delegated approval waits for a `peer-review` provider and "a later
  decision about its record". This is that decision. Its decisions 1 to 4 stand: `approve-plan` is owner-run, the
  record binds four values, and the process module's helper computes the region. Its rejected alternative, a module
  command that writes the record so that "an agent could approve its own plan", is still rejected: here the installer
  writes, and only when the owner's setting, a sealed clean review of the same bytes and the delegability line allow it.
- **`2026-10-19-mandatory-review-personal-delegation` (carried out).** Decisions 2 to 6 are its conditions made
  mechanical.

## Alternatives considered

- **The process module writes the record** (what `code-work.md` says). Rejected: it needs a module to write the guarded
  store, which the agent's harness denies writes to, and every process module would repeat the writer.
- **Bind the review to the plan's hashed region.** Rejected: the review engine would need to know a plan's section
  names, or call the process module, and the installer could not check a claim it cannot compute. The same-bytes rule
  needs only a hash both sides can compute, at the price of an order for the agent.
- **A project-level switch for delegation.** Rejected by the accepted record: a contributor could set it for everyone.
- **Delegate every checkpoint at once.** Rejected: each checkpoint has its own risk; the others need their own plans.
- **Keyword matching on the Risks section.** Rejected: owners' plans routinely say "no push, no install, no secret",
  which would mark every plan not delegable.

## Consequences

- The installer gains one command, a format-2 reader and writer, and a rule for one checkpoint name. It names no
  module; the boundary test guards that.
- The review engine and the process module each gain one read-only argument, and the contract gains two optional
  declaration fields.
- A delegated approval is weaker than the owner's: a plan written to steer the reviewer can get a clean review, and
  the reviewer and the author can share a blind spot. The owner's setting, a sealed clean last round, the delegability
  line, the hard stops at the action and the gate's reading of the record limit that; none removes it.
- A review that was not sealed on this machine, for example one committed by a teammate, gives no delegated approval
  until the owner resets it.
- Turning delegation off takes effect at once for plans approved by a delegate, because the setting is read when the
  entry is read (decision 9). It does not undo work already done under an approval.
- **Accepted risk: a provider that changes afterwards.** If the `peer-review` provider is changed, replaced or removed
  after a delegated approval, the approval stays valid and its recorded provider hashes no longer describe the
  installed provider. What was approved is bound by the plan's region and the process module's helper, not by the
  reviewer, and the approval was given while the provider was approved and pinned. An owner who distrusts a provider
  turns delegation off, or approves the plan again with `wb approve-plan`.

## Review record

Three rounds of 3, 2026-10-23, `ask-codex review-adr`, model `gpt-5.6-luna`, effort medium (asked for by the owner).
Outcome: changes needed in all three; round 1 one blocker, round 2 two blockers, round 3 one major, all applied. The
bound is used, so the fix for round 3 was not re-checked by Codex.

- R1-F1 (blocker, applied): the record had an agent-run command write the guarded store without saying how that
  relates to `2026-10-19-guarded-store` (the agent must not write the store; the owner records an approval) and
  `2026-10-22-installer-records-plan-approval-module-computes-region` (every approval is the owner's for now). The
  section "Relation to accepted decisions" now says that the record supersedes neither, narrows the first (the installer
  writes, on the owner's standing setting and a sealed clean review, and the deny rule on store writes is unchanged),
  fulfils the reservation in the second, and gives the alternative of keeping delegated approval owner-run. The decisions
  index also lists the record.
- R2-F1 (blocker, applied): the Context said the review engine "records no verdict", but each stored round holds the
  reviewer's verdict and the engine's reading. It records no approval and grants no authority; the Context says so, and
  the same wording was corrected in `trust-and-approval.md`, `code-work.md` and `review-engine.md`.
- R2-F2 (blocker, applied): decision 1 said "a module never writes the store", but the review engine keeps its seal key,
  rollback marks and lock there. Decision 1 now says a module never writes a plan approval record, and that a module's
  existing store writes are unchanged and are not approvals; the trust spec says the same.
- R3-F1 (major, applied): the entry records the provider's hashes but only the four owner-approval values decide
  `approved`, so a changed or removed provider, or delegation turned off, left a delegated approval valid, and the
  record did not say so. At the owner's choice: decision 9 makes a delegated entry count only while the personal setting
  for `approve-plan` reads `delegate` when the entry is read, and the provider's hashes stay provenance, with the
  provider-drift risk accepted and stated in the consequences. The plan's choice 8, criterion 5 and increment D, and the
  trust spec, say the same.

The review is not an acceptance; the owner accepted the record on 2026-10-23, as written.

## Verification

The acceptance criteria are in plan `2026-10-23-delegated-approval` (criteria 2 to 7) and in `trust-and-approval.md`,
"Delegated plan approval records". The decision is verified when the plan is `Completed`: every refusal writes nothing,
a delegated approval is read as `approved` by `wb plan-status` and the gate, and a security pass has run.

## Related files and decisions

- `docs/specs/trust-and-approval.md`, `docs/specs/code-work.md`, `docs/specs/review-engine.md`,
  `docs/specs/module-contract.md`, `docs/specs/installer-interface.md`
- `docs/plans/2026-10-23-delegated-approval.md`
- [2026-10-19-mandatory-review-personal-delegation](2026-10-19-mandatory-review-personal-delegation.md)
- [2026-10-19-guarded-store](2026-10-19-guarded-store.md)
- [2026-10-22-installer-records-plan-approval-module-computes-region](2026-10-22-installer-records-plan-approval-module-computes-region.md)
- [2026-10-22-model-calls-go-through-vendor-bridges](2026-10-22-model-calls-go-through-vendor-bridges.md)
- [2026-10-21-module-code-lives-in-modules](2026-10-21-module-code-lives-in-modules.md)
