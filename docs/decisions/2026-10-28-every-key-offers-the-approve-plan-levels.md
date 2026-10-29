# Eight more keys offer the levels that approve-plan offers

Status: Proposed
Date: 2026-10-28

## Context

`2026-10-26-a-level-for-every-command` (accepted) says no key is limited to `block`, but its decision 3 built less: every key
offers `block` and `none`, `delegated` is offered only where a command declares a gate (`approve-plan` only), and `ask` only
where a key has a read-only preview whose digest it requires. What was built (`docs/specs/command-permissions.md`, "Planned"
and the unbuilt list) leaves eight keys short of `approve-plan`, which offers all four levels:

- `block` only: `submit-remote-job`, `push-shared-branch`, `fetch-remote-output` and `change-direction`.
- `block` and `none` only: `accept-decision`, `wb release-approvals`, `acknowledge-first-tier` and `acknowledge-second-tier`.

On 2026-10-28 the owner said these eight should have the same levels and permissions as `approve-plan`. The roadmap candidate is
`workbench-v1#checkpoint-levels-beyond-block`. Today `delegate` takes effect for `approve-plan` only; every other checkpoint
reads `stop` (`docs/specs/trust-and-approval.md`, "Effective values"). Three of the eight are not commands at all
(`fetch-remote-output`, `change-direction`, `accept-decision`: the agent stops and asks in the conversation, or the owner edits a
file), and `wb release-approvals` runs where the spec says no level can be read.

The compiled hard-stop floor is not touched (`2026-10-19-compiled-hard-stop-floor`).

## Decision

Proposed; the owner decides. Nothing here is built; building it needs a plan the owner approves.

1. **Eight keys, four levels.** `submit-remote-job`, `push-shared-branch`, `fetch-remote-output`, `change-direction`,
   `accept-decision`, `release-approvals`, `acknowledge-first-tier` and `acknowledge-second-tier` each offer `block`, `ask`, `delegated` and `none`, except that `ask` is not offered for the three keys that run no command
   (decision 5). Their shipped defaults stay as they are (`block`). This refines decision 3 of `2026-10-26-a-level-for-every-command`, which the
   owner's direction overtakes for these keys; that record's text is not touched.
2. **What the levels mean is what `approve-plan` shows.** `ask`: the owner confirms on the harness prompt, bound to a digest from
   a read-only preview of the action. `delegated`: a converged, sealed review of the exact subject stands in for the owner's
   word, and only while the table reads `delegated`. `none`: nothing blocks it and the run is logged. A stale or missing
   rendering makes a relaxed key read `block`, as now.
3. **`delegate` is no longer `approve-plan` only.** It takes effect for each of the eight keys, and for no other checkpoint
   until a record says so. `wb settings` prints `delegated` for them, with no note that it has no effect.
4. **Keys that run a command** (`submit-remote-job`, `push-shared-branch`, `release-approvals`, `acknowledge-first-tier`,
   `acknowledge-second-tier`) each get a preview with a digest for `ask`, built as `approve-plan`'s is. For `delegated`, the review's subject is what the
   module's read-only `describe` reports (`2026-10-25-describe-interface-for-action-review`; the push is described by
   `safe-git describe push`). The review is the action-review engine's. *Author's call: this reuses the engine that exists for
   the purpose; nothing else is proposed.*
5. **Keys that run no command** (`fetch-remote-output`, `change-direction`, `accept-decision`) are rules the agent follows, read
   from `wb settings`, and the installer enforces nothing for them. `block` is the agent stopping to ask in the conversation;
   `none` is the agent proceeding; `delegated` is the agent proceeding on a converged review it names. **`ask` is not offered
   for these three**: with no command there is no preview to carry a digest. A table entry of `ask` for one of them reads as
   `block`, and `wb settings` says so in a `settings:` line, which is how it already treats a level a key does not offer (it
   prints that for `accept-decision` today). Building a command for each so that `ask` has a digest is not part of this
   record. *Author's call; the owner decides whether to accept it.*
6. **`release-approvals`.** It has no terminal test and keeps none, so what a level changes for it is whether the harness
   denies the agent and whether a run without a terminal is logged. Its level is read as `attach`'s is
   (`workbench/levelrun.py`, `optional` and `level_now`): from the rendering record in the guarded store for the project that
   holds the working directory, never from a file the project can write. Where no level can be read, the command runs as it
   always did. `ask` and `delegated` for it are built as for the other command keys (decision 4), and the digest binds the
   arguments of the run. *Author's call; read from the code, not run against a relaxed level.*
7. **Out of scope.** `wb rerender` (terminal only, `2026-10-27-rerender-is-terminal-only`), the order in which the previews are
   built, and each digest's content.

## Alternatives considered

- **Leave the eight as they are.** Rejected by the owner; it also contradicts decision 3 of
  `2026-10-26-a-level-for-every-command`, which says no key is limited to `block`.
- **Give only `ask` and `none`, and keep `delegated` for `approve-plan`.** Rejected by the owner, who asked for the same levels.
  It would be the safer course for `push-shared-branch` (see Consequences).
- **Give `delegated` only to the keys that do not act outward.** Not chosen; the owner's direction names all eight. Offered here
  so the owner can see what was set aside.
- **Build a command for each agent-only checkpoint so `ask` has a digest.** Not proposed: it adds three commands for a prompt the
  conversation already gives. Possible later.
- **Keep `release-approvals` at `block` and `none`.** Not chosen; the owner named it. The code shows its level can be read the
  way `attach`'s is, so it is not out of reach.
- **Edit the accepted records.** Not allowed. This record refines them, and the owner marks their status lines.

## Consequences

- Good: one set of four words and one meaning for every checkpointed key; the owner sets their own risk per key.
- Bad: `delegated` on `push-shared-branch` lets a review stand in for the owner at a step that cannot be taken back. The
  credential scan still runs, but the stop is the review's, not the owner's. The same holds, more weakly, for `submit-remote-job`.
- Bad: `delegated` or `none` on `accept-decision` lets an agent, or a reviewing model, accept a decision that then outranks the
  code. The default stays `block`.
- Bad: `none` on `push-shared-branch` removes the stop on a push. The log is the only record, and it can be written from a shell
  (`2026-10-26-ask-level-command-gate`).
- Bad: for the three agent-only keys nothing enforces the level; a wrong reading by the agent is not caught by the installer.
- Bad: five previews with digests, and a delegated route for each, are real work, and a security review is owed when built
  (authorization and a permission boundary). It runs only when the owner asks.
- Neutral: the trust-and-approval spec's statement that `delegate` takes effect for `approve-plan` only changes when this is built.

## Evidence

Read on 2026-10-28 at commit `a4969c8` (no tool version applies; nothing was run): `docs/specs/command-permissions.md` (the table
of actions around rows 512–532, the unbuilt list, and the sections on `acknowledge`, `recover`, `attach` and `release-approvals`);
`docs/specs/trust-and-approval.md` ("Delegated approval", "Checkpoint and cap settings", "Effective values"); the decision
`2026-10-26-a-level-for-every-command`; `docs/roadmaps/workbench-v1.md` (the candidate named above). On 2026-10-29 the code was read for decision 6:
`workbench/cli.py` (`_release`, `_unattended_call`) and `workbench/levelrun.py` (`level_now`, `optional`). Decision 6 follows
from that reading; `rendering.current_table` was not read, so that the store is the guarded one is inferred from its argument
name. No level was tested at any key.

## Related files and decisions

- `docs/specs/command-permissions.md`, `docs/specs/trust-and-approval.md`, `docs/roadmaps/workbench-v1.md`
- [2026-10-26-a-level-for-every-command](2026-10-26-a-level-for-every-command.md)
- [2026-10-26-per-command-permission-levels](2026-10-26-per-command-permission-levels.md)
- [2026-10-23-delegated-plan-approval](2026-10-23-delegated-plan-approval.md)
- [2026-10-25-describe-interface-for-action-review](2026-10-25-describe-interface-for-action-review.md)
- [2026-10-26-ask-level-command-gate](2026-10-26-ask-level-command-gate.md)
- [2026-10-27-rerender-is-terminal-only](2026-10-27-rerender-is-terminal-only.md)
- [2026-10-19-compiled-hard-stop-floor](2026-10-19-compiled-hard-stop-floor.md)
