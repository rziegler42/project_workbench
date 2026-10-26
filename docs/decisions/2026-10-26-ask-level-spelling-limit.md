# At the ask and none levels the harness's rule is the only barrier, and its limit is accepted

Status: Proposed
Date: 2026-10-26

## Context

`2026-10-26-per-command-permission-levels` lets the owner set a command to `ask` or `none`, so an agent can run it
without a terminal. Today an owner-run command is stopped three ways: the harness denies the agent's spelling of it, the
command refuses without a terminal on standard input and output, and `approve-plan` also needs a typed digest. The
terminal test is friction and not authentication, because an agent can open a pseudo-terminal
(`2026-10-20-preview-then-owner-run-write`). At `ask` and `none` the terminal test no longer applies, so the only barrier
left is the harness's own rule, which matches the command text the agent submits.

A Bash rule is a best-effort text match and not a boundary (`docs/specs/harness-modules.md`, "Evidence"). A spelling the
rule does not name is not stopped by it: a path-qualified `wb`, the guarded store's own `bin/wb`, `bash -c` and `env wb`
are examples. A shell edit of the harness's permissions file that removes the `ask` rule is a second way round, because the
file sits in the project and its edit deny covers the harness's file tools and not a shell. For a command at `block` these
gaps were closed by the terminal test; at `ask` and `none` they are not. A design-stage security review
(`docs/plans/2026-10-26-command-permission-levels.md`, Result of Increment D) rated this the one high finding. It was a
review by reading: the reviewer's scratch write was refused, so nothing it reported was tested.

Increment A of the plan tried an `ask` prompt for a plain `echo` rule in a throwaway project: the prompt reached the owner's
remote channel, and a Yes or No given there ran or refused the command (`docs/specs/harness-modules.md`, "An `ask` prompt
answered from the remote channel"). It did not try a spelling the rule does not name.

## Decision

This is a proposal. Nothing here is accepted until the owner says so.

The owner accepts, before `ask` ships for any key, that at `ask` and `none` the barrier is the harness's rule and is a
best-effort text match. The workbench narrows it as far as it can and does not claim more:

1. Attach renders the `ask` pattern for the guarded store's own `bin/wb` path as well as for the spellings in
   `rules.SPELLINGS`.
2. A command read at `ask` or `none` re-reads the harness's permissions file and refuses unless it hashes to the hash in the
   rendering record in the guarded store, so a shell edit that removed the rule is seen when the command runs.
3. The rendering record lists every key, and a key it does not list, a damaged record, a table that changed since attach or
   a harness that provides no `permissions` all read as `block`.
4. The digest that binds an `ask` to what was previewed is 32 hexadecimal characters of a canonical text that also holds the
   project's identifier, the declaration hash and the helper hash.
5. `none` is opt-in and is never a default. `ask` ships as a default only for the two keys of increments F and G.
6. Increment F's code is committed first and the probe is its last step, run on a copy and recorded. `approve-plan` reads
   `ask` only after an attach renders the `ask` rule, so nothing becomes runnable by committing the code. Until the probe is
   recorded, `ask` is not offered as a default to anyone else, and the plan's Result says so. If a spelling that the pattern
   does not cover approves a plan without a prompt, the plan stops and is revised, and `ask` does not ship for
   `approve-plan` until the owner decides.

What remains, and what the owner accepts: another spelling that no pattern names can run the command at `ask` or `none`
without a prompt, and the harness's file can be changed between the hash and the prompt. An agent that can do either can
approve a plan or extend a review for the project it works in, which is what a terminal and a typed digest stop today.

## Alternatives considered

- **Hold `ask` until the spelling bypass is tested on a copy.** The cautious order, and the plan already requires the probe
  after F. Rejected as the gate for building F, because the probe needs F's code; it is kept as step 6 above and as a stop
  condition.
- **Never relax a terminal-only command.** Safe, and the owner keeps the terminal. Rejected by the owner's request: they
  often work with no terminal, and the point of the design is to approve a plan and extend a review from the remote channel.
- **Make the command check how it was invoked** (its command line or parent process). Rejected: an agent controls both, so
  the check would look like a boundary and would not be one.
- **Allow only `ask` and never `none`.** Narrower, and `none` is opt-in already. Kept open: the owner can decline `none` in
  their settings, and no key ships at `none`.

## Consequences

- Good: the owner can approve a plan and extend a review from a prompt, and the gaps the workbench can close cheaply are
  closed; everything fails closed to `block` when the record, the table or the file does not agree.
- Bad: for these two commands the strength of the barrier falls from "a terminal and a typed digest" to "a prompt on a text
  match". The residual is not testable away; it is stated and accepted here.
- Bad: after a table or module change in an attached clone, `ask` and `none` read `block`, and `wb attach` refuses a clone
  that already records a harness, so no command restores them. That is safe and unfinished; it needs a command to re-render
  or to rewrite the record, which is a later plan and the owner's decision.
- The log of every run above `block` (`docs/specs/command-permissions.md`, "The log") records what ran, but it is read after
  the fact and prevents nothing.

## Evidence

- The design-stage review: the `security-reviewer` agent, 2026-10-26, at commit `dac9139`, by reading the files; it ran no
  probe (its scratch write was refused) and did not read `commands.owner_refusal`, `declarations.parse_json`, the review
  engine or the attach code. Recorded in the plan's Result for Increment D.
- The prompt trial: owner-run, Claude Code 2.1.310, 2026-10-26, repository head `1a731fa`, reported by the owner;
  recorded in `docs/specs/harness-modules.md`.
- The statement that a Bash rule is not a boundary: `docs/specs/harness-modules.md`, "Evidence".
- The built mitigations (items 1 to 3): increments D and E of the plan, committed as `85b1514` and `2f12a6a`; tests in
  `tests/test_rendering.py` and `tests/test_levellog.py`. Item 1 is tested only by the presence of the rendered pattern, not
  against a live harness.
