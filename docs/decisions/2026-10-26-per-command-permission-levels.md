# Each owner-run and checkpointed command gets one permission level in the owner's personal settings

Status: Accepted by the owner on 2026-10-26; decisions 2 and 6 and Question 2 refined by 2026-10-26-permission-levels-as-built
Date: 2026-10-26

## Context

The owner often works without a terminal. The owner-run commands (`install`, `adopt`, `add`, `upgrade`, `attach`,
`approve`, `pin`, `acknowledge`, `recover`, `approve-plan`, the review engine's `extend`, `reset`, `archive`, `prune`
and `amend`, `mempalace init` and `mine`, `remote-runner fetch-overwrite`) refuse unless standard input and output are
both terminals, and `approve-plan` also needs the first 12 characters of a digest typed back (`docs/development.md`,
command table). `release-approvals` is different: it is a maintainer's release-time command that needs no terminal
(`docs/specs/installer-interface.md`), and the harness denies it to the agent like the others. The harness denies every
command named here to the agent. A removal is also the owner's in a terminal until `safe-git` reviews it.

Two mechanisms already relax this, each for one case. A checkpoint can be `stop` or `delegate`, but `delegate` takes
effect for `approve-plan` only; every other checkpoint stops whatever its setting says
(`2026-10-23-delegated-plan-approval`, decision 6, and `wb settings`). Nothing lets the owner confirm any other
command remotely. A review that reaches its round cap with a finding in dispute, for instance, can be extended only from
a terminal.

Facts that bear on the choice:

- The terminal test is friction, not authentication. An agent can open a pseudo-terminal and type a digest it was
  shown, so only the harness's deny rules keep an agent from a command
  (`2026-10-20-preview-then-owner-run-write`).
- Review is mandatory, and a delegate may give a verdict only when the owner's personal setting for that checkpoint is
  `delegate`, a provider is installed and review converged. Delegation is never project policy
  (`2026-10-19-mandatory-review-personal-delegation`).
- The hard-stop floor is compiled in and can only be tightened. Neutral permission rules hold `ask` and `deny`, never
  `allow`, and a project cannot widen what an agent may do (`2026-10-19-compiled-hard-stop-floor`,
  `2026-10-19-restrictive-only-permissions`, `2026-10-24-project-guarantees-a-floor`).
- A prompt for a module command exists only where an `ask` rule raises one, and what prompts for the module commands is
  decided in `2026-10-25-module-commands-and-the-approver`. A reviewed action reports what it would do through a
  read-only `describe` (`2026-10-25-describe-interface-for-action-review`).

## Decision

This is a proposal. Nothing here is built, and writing it changes no behavior.

1. **One level per command.** The owner's personal settings, in the guarded store beside the checkpoints, hold a table
   from a command to one of four levels. A project, a plan, a review, a module or an agent cannot supply or change an
   entry.

   | Level | Meaning |
   |---|---|
   | `block` | Only the owner, from a terminal. The agent is denied the command. Today's owner-run behavior. |
   | `delegated` | The agent runs the command after a gate the command declares has passed. |
   | `ask` | The agent requests the command and the owner confirms it on a channel reachable without a terminal. |
   | `none` | The agent runs the command with no confirmation. |

   **The table's key** is the checkpoint's setting name where `code-work` declares one for the action (`approve-plan`,
   `push-shared-branch`, `submit-remote-job`, `acknowledge-first-tier` and the others in `docs/specs/code-work.md`,
   "Checkpoints"), and for an owner-run command that has no checkpoint it is the command in the `wb` spelling (for
   example `wb run review-engine extend`). A key that no installed module declares is refused when the table is read.
   When one command reaches more than one keyed action, the strictest level applies; from strictest to least strict
   the order is `block`, `ask`, `delegated`, `none`. A checkpoint and its command are not two settings: the checkpoint's
   name is the key, and the command inherits it.

2. **Each command ships a default level, and the owner may move it to any level the command offers.** The default is
   set by the strength the command needs. `block` is the default for a command that changes what the workbench trusts
   or runs, or that cannot be undone. `ask` is the default for a command that is previewed and recoverable. `delegated`
   is never a default: delegation is the owner's personal act and a project, a module or this record cannot grant it
   (`2026-10-19-mandatory-review-personal-delegation`). A command ships `ask` as its default only from the version in
   which its spec names the exact command form and the read-only preview digest it requires (decision 5). Until then
   its default is `block`, and the `ask` in Question 2 is its target. A command with no entry reads at its shipped
   default. A
   malformed, duplicated or contradictory entry reads as `block`, and so does a damaged table. The shipped defaults are
   in Question 2; any default looser than today's `block` is the owner's to accept there.
3. **The floor is not in the table.** What the compiled floor stops, and every hard stop a module adds, stay `block`
   whatever an entry says; an entry that tries to lower one is refused and reported. Every other command in scope,
   the trust-changing ones included, may be set to any level it offers. That is the owner's choice and the owner's risk,
   and the log in decision 7 records each run.
4. **`delegated` needs a declared gate.** A command may take `delegated` only if its module declares a gate for it, such
   as a converged, sealed review of the exact bytes (the pattern of `2026-10-23-delegated-plan-approval`), a read-only
   preview, or a hard ceiling. A level of `delegated` on a command with no declared gate is refused when the table is
   read. A delegated run counts only while the entry stands: when the table reads anything else at that moment, the
   run is refused and the owner's own route is the way, as decision 9 of that record already says for a plan approval.
   A gate that fails, is missing or is ambiguous gives no approval.
5. **`ask` uses the harness's permission prompt.** The harness renders an `ask` rule for the command, so the owner
   answers wherever the session reaches them. The installer then accepts the command from the agent without the
   terminal test, because the terminal test was never the control. The command refuses unless it carries the digest of
   its own read-only preview, so that a changed target fails and the prompt shows the exact command and digest. The
   owner's answer is the approval; the agent must show the preview in the conversation before it asks, and no code can
   enforce that. The prompt shows the command, not the preview, so `ask` proves that the owner saw the command and
   digest and not that they read the plan or the diff. For `approve-plan` the digest is the plan's hashed region, so
   an edit after the answer voids the approval. The owner accepts that residual risk by choosing `ask` there (Question
   1). Where a gate exists, `delegated` is the better setting for `approve-plan` and `ask` is the fallback.
6. **A command offers every level that makes sense and is doable, and its spec says which.** The rule: `block` is
   always offered; `delegated` only where the command declares a gate (decision 4); `ask` where the command has a
   read-only preview whose digest it can require; `none` wherever the command is not on the floor. A level a command
   does not offer is refused when the table is read. A command whose acceptance is the owner's own act, such as
   `accept-decision` (`AGENTS.md`), offers `block` and `ask` only, because a delegate or an unprompted agent accepting
   it would not be the owner's act. Each command's spec names its offered levels, and a test per command checks them.
7. **Every run at a level other than `block` is recorded** in an append-only entry that names the command, the level,
   the gate or confirmation and the outcome, in the guarded store, which the agent cannot write.
8. **Checkpoints become part of the table.** `stop` reads as `block` and `delegate` as `delegated`. Decision 6 of
   `2026-10-23-delegated-plan-approval`, that `delegate` takes effect for `approve-plan` only, would no longer hold: a
   checkpoint takes the level the table gives it, subject to decisions 3 and 4. The spec settles whether the old words
   stay as aliases or are migrated; the two vocabularies must not run side by side unlabelled.

### Questions for the owner

Answered by the owner on 2026-10-26, who then accepted the record:

1. **Is `ask` acceptable for `approve-plan`?** Yes, bound to the digest of the plan's hashed region, with `delegated`
   preferred where a gate exists and the residual risk accepted (decision 5).
2. **Which commands may be lowered?** All commands in scope, as far as a level makes sense and is doable (decisions 3
   and 6). The defaults are set to the strength each command needs (decision 2). **Still for the owner to accept:**

   | Target default | Keys |
   |---|---|
   | `block` | `acknowledge-first-tier` (instruction-bearing and executable files), `wb install`, `wb adopt`, `wb add`, `wb upgrade`, `wb attach`, `wb approve`, `wb pin`, `wb recover`, `wb release-approvals` (it writes the shipped first-party approval records, which are trust roots, and needs no terminal today), `wb run mempalace init`, `wb run mempalace mine`, `wb run remote-runner fetch-overwrite`, and `accept-decision` (offers `block` and `ask` only) |
   | `ask` | `approve-plan`, `wb run review-engine extend`, `wb run review-engine reset`, `wb run review-engine archive`, `wb run review-engine prune`, `wb run review-engine amend`, `acknowledge-second-tier`, `submit-remote-job`, `push-shared-branch` (a force push or a push of `main` stays on the floor) |

   No key ships `none` as a default; the level is offered and the owner may set it. `fetch-remote-output`,
   `change-direction` and the other checkpoints not named here keep `stop`, which reads as `block`, until a later
   change gives them a target.

   Today no command has a specified preview digest for an agent-run request, so every `ask` above is a target, and
   all of them read `block` until their spec defines the command form and the digest (decision 2). That contract
   exists in part for `approve-plan`, whose plan region is already hashed, and has to be written for the others,
   `push-shared-branch` among them (`push-check` is the nearest existing preview). An `ask` target is looser than
   today's `block` for those keys once built: the agent may request them and the owner confirms by prompt. Say if any
   should stay `block`. Commit and remove are governed by the action-review work and are not changed here.

   `docs/specs/code-work.md` lists `accept-decision` as delegable. `AGENTS.md` says only the owner accepts a decision,
   and ranks above the spec. This record follows `AGENTS.md`, so `accept-decision` offers `block` and `ask` only, and
   the checkpoint table in `code-work.md` would need that correction when the spec is revised.
3. **Is delegation ever a default?** Not in this proposal (decision 2).
4. **How is a partly superseded record marked?** Once this record is accepted, the status line of
   `2026-10-23-delegated-plan-approval` reads `Accepted by the owner on 2026-10-23; decision 6 superseded by
   2026-10-26-per-command-permission-levels`, its README row mirrors it, and nothing else in that record changes. If
   the document check rejects that wording, the fallback is a dated clarification note after its body, which the owner
   approves.

## Alternatives considered

- **Keep owner-run as it is and add only more `delegate` checkpoints.** Rejected: a gate fits some commands and not
  others. A round-cap `extend`, an `acknowledge` and a removal have no converged-review gate, so the owner would still
  need a terminal for them.
- **Let the agent run an owner-run command when the owner says so in chat.** Rejected: the system cannot tell the
  owner's words from the agent's or from text in a file, and an approval has to come from a channel the agent does not
  write.
- **Fix `block` for the trust-changing commands, and let a module list the commands eligible for `none`.** Rejected
  by the owner on 2026-10-26: the owner should be able to configure each command as they want, with defaults set to
  the right strength. The floor stays fixed, and the log records every run.
- **A project-level table.** Rejected: delegation and widening are the owner's, and a contributor could set them for
  everyone (`2026-10-19-mandatory-review-personal-delegation`, `2026-10-19-restrictive-only-permissions`).
- **A second AI approves everything (`delegated` for all).** Rejected: it can be steered by the same text as the
  first, and an action with no declared gate has nothing for it to check (`2026-10-19-compiled-hard-stop-floor`).
- **A flag such as `--yes`.** Rejected, as in `2026-10-20-preview-then-owner-run-write`: it removes the approval.
- **Leave the terminal test and add a phone terminal.** Not chosen: it moves the owner's setup, not the product, and
  does not help a session reached only through the harness.

## Consequences

- Good: the owner can work without a terminal for each command they choose, one command at a time, and the default
  loosens nothing.
- Good: the control is the harness's deny and `ask` rules and the owner's settings, which the agent cannot write, and
  not a typed digest an agent could produce.
- Good: one table replaces a checkpoint list and an owner-run list that grew separately.
- Bad: `ask` approves a command and a digest, not a reading. A hurried answer to a prompt becomes an approval. This is
  the residual risk, and Question 1 puts it to the owner.
- Bad: the owner can lower a trust-changing command such as `install` or `upgrade` to `none`, and an agent steered by
  hostile text could then change what the workbench trusts without a prompt. The floor and the log remain, and the
  default is `block`, but the protection for those commands is then the owner's setting and not the code. A setting that
  loosens them should be made on purpose.
- Bad: a shipped `ask` default for commands that are `block` today (Question 2) widens what an agent can request on a
  machine whose owner has not changed anything.
- Bad: the harness modules render an `ask` list beside the `deny` list, and every command that moves off `block` needs
  tests of the rendered rules, of the floor, and of a malformed table reading as `block`. The installer's owner-run
  list (`workbench/rules.py`) and the approver coverage in `2026-10-25-approver-coverage-for-the-module-commands`
  change with it.
- Bad: whether a prompt can be answered through the owner's remote channel is untested here. If it cannot, `ask`
  does not reach the case that motivates this record.
- Bad: new surface in the installer's settings reader and the log. A change to authorization, the guarded store and a
  permission boundary is owed a security review when it is built, which runs only when the owner asks.
- Neutral: the exact table format, the names of gates, the log fields and the migration of `stop` and `delegate` are
  for the spec and the plan. Building this needs a plan the owner approves.

## Evidence

Read on 2026-10-26, at commit `36c0970` of this repository: `docs/development.md` (command table), the decisions named
above, and the output of `python3 -m workbench settings` (only `approve-plan` is `delegate`; every other checkpoint is
`stop`; caps are 3, 1 and 6). Nothing was run to test an `ask` prompt, a remote confirmation or the rendered rules, and
nothing was built. The command lists were read from the documents, not from the code, and may be incomplete.

## Review record

Reviewed by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-26, at
the owner's request: three rounds, the bound of 3, not extended. Outcome: not converged. Each round returned major
findings: a wrong description of `release-approvals` (R1-F1), a table key that mixed checkpoints and commands (R2-F1),
`ask` defaults with no specified preview digest (R2-F2) and informal command names in the table (R3-F1). All four were
applied and checked against `installer-interface.md` and `code-work.md`. R3-F2, that the status-line change to the
2026-10-23 record edits an accepted record, was rejected: the decision skill allows it once this record is accepted,
and the owner agreed to the wording in Question 4. The text added for R3-F1 and R3-F2 was not reviewed again. The
owner accepted the record as written on 2026-10-26, knowing that the review did not converge and that those edits were
not reviewed again. The acceptance is the owner's, and a review is not an acceptance.

## Related files and decisions

- `docs/development.md`, `docs/specs/trust-and-approval.md`, `docs/specs/installer-interface.md`,
  `docs/specs/action-review.md`, `docs/specs/safe-git.md`, `docs/specs/review-engine.md`
- [2026-10-23-delegated-plan-approval](2026-10-23-delegated-plan-approval.md)
- [2026-10-19-mandatory-review-personal-delegation](2026-10-19-mandatory-review-personal-delegation.md)
- [2026-10-19-compiled-hard-stop-floor](2026-10-19-compiled-hard-stop-floor.md)
- [2026-10-19-restrictive-only-permissions](2026-10-19-restrictive-only-permissions.md)
- [2026-10-20-preview-then-owner-run-write](2026-10-20-preview-then-owner-run-write.md)
- [2026-10-24-project-guarantees-a-floor](2026-10-24-project-guarantees-a-floor.md)
- [2026-10-25-module-commands-and-the-approver](2026-10-25-module-commands-and-the-approver.md)
- [2026-10-25-describe-interface-for-action-review](2026-10-25-describe-interface-for-action-review.md)
