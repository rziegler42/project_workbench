# accept-decision offers the ask level, through a preview command

Status: Proposed
Date: 2026-10-29

## Context

`2026-10-28-every-key-offers-the-approve-plan-levels` (accepted on 2026-10-29) gives eight keys the levels that `approve-plan`
offers. Its decision 5 makes an exception for the three keys that run no command, `fetch-remote-output`, `change-direction` and
`accept-decision`: they are rules the agent follows, read from `wb settings`, and `ask` is not offered for them, because with no
command there is no preview to carry the digest that `ask` binds to. An `ask` entry for one of them reads as `block`, and `wb
settings` says so. That record adds that building a command for each, so that `ask` has a digest, "is not part of this record" and is
"possible later".

On 2026-10-29 the owner directed that accepting a decision should be configured like every other key: `block`, `ask`,
`delegated` or `none`. Today `accept-decision` offers only `block` and `none`
(`workbench/levels.py`, `_OFFERS`), and the `draft-decision` skill lets an agent accept only while `wb settings` prints `level
accept-decision: none`.

## Decision

1. **`accept-decision` offers `block`, `ask`, `delegated` and `none`.** This replaces the carve-out for this one key in decision 5
   of the eight-key record. Everything else in that record, including the carve-out for `fetch-remote-output` and
   `change-direction`, stands.
2. **`ask` works as it does for `approve-plan`.** A read-only preview of the record to be accepted prints a digest of what the
   owner will be asked to accept: the record's path, its status line and the hash of its bytes. The accepting command carries that
   digest, and the owner confirms the harness prompt for exactly that digest.
3. **The tracked status line is the acceptance, and the command writes it.** What makes a decision `Accepted` is the status line in
   the tracked file, because every clone shares it and a record in the guarded store is local to one machine. The accepting command,
   run at `ask`, reads the record (bounded, no link followed), checks that its hash equals the preview's digest and that its status is
   `Proposed`, then replaces only the status line with `Status: Accepted by <approver> on <date>`, using the same hash-checked
   whole-file replace that `upgrade` uses, and refuses if anything differs. It logs the acceptance in the guarded store, with the
   approver, `via` and the digest, as the level log does for other keys. The approver is written as in
   `2026-10-29-approvals-name-the-approver-by-git-identity`. A hand edit of a status line by the owner stays possible and is not
   gated, and the document check does not treat it as unaccepted.
4. **The accepted eight-key record is not edited.** After the owner accepts this record, that record's status line gains a clause
   naming it.

## Alternatives considered

- **Leave `ask` reading as `block` for `accept-decision`** (the accepted record's decision 5). Rejected by the owner.
- **Build `ask` for all three keys that run no command.** Not chosen: the owner named `accept-decision` only, and the other two are
  conversational stops with no document to digest.
- **Offer `delegated` and `none` only.** Not chosen: it keeps `accept-decision` unlike every other key, which is what the owner
  asked to end.

## Consequences

- **Good:** accepting a decision gets the same mechanical confirmation as approving a plan, and the agent can no longer accept one by
  reading a setting alone when the level is `ask`.
- **Bad:** a new command pair, its tests and spec text, and an installer that writes a status line in a tracked document. It adds
  scope to the eight-key build, so `workbench-v1#checkpoint-levels-beyond-block` gains a part.
- **Limit:** the gate covers the command route. An agent that edits a status line with its own edit tool is held by the rule it
  follows and not by this gate, as it is for `accept-decision` today.
- **Interaction:** the `draft-decision` skill and the `groundwork` policy block say who accepts in terms of the level. They are
  corrected in the same plan so that all three agree.
- **Not decided:** the `delegated` review's subject for a decision, and who may accept when several people share a repository.

## Evidence

Read on 2026-10-29 at commit `5ee1ecce8efa83194f118748666a84fab4be6960`, workbench 0.1.0: the text of decision 5 of
`2026-10-28-every-key-offers-the-approve-plan-levels`; `workbench/levels.py`, `_OFFERS`; the `draft-decision` skill of the
`groundwork` module; and the owner's direction in session on 2026-10-29. Nothing was run to test a preview, because none exists.
