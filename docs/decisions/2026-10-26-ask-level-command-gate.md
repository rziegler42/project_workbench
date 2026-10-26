# A command gate stops Bash commands that name a relaxed command unless the ask rule can fire on them

Status: Proposed
Date: 2026-10-26

## Context

`2026-10-26-ask-level-spelling-limit` accepted that at the `ask` and `none` levels the harness's rule is the only barrier
to an agent running `approve-plan`, and that the rule is a text match. It listed mitigations (the guarded store's own `bin/wb`
pattern, a live hash of the harness file, a record that fails closed) and required a probe of the spellings the rule does not
name, with the plan stopping if one ran the approval without a prompt.

The probe was run by the owner on 2026-10-26 (Claude Code 2.1.311, repository commit `230ae7e`). Three spellings prompted by
the rendered rule. `bash -c 'wb approve-plan <plan> --digest <d>'` did not match any rule: in default mode it prompted only
with the harness's generic "requires approval", and in **auto mode it ran with no prompt and recorded the approval**. Auto
mode decides a command that no rule names by itself. This is the stop condition of the earlier decision, shown and not read.
The result and the stored evidence are in the Result of Increment F of `docs/plans/2026-10-26-command-permission-levels.md`.

At `block` the same spelling is still stopped, because the command needs a terminal. Only `ask` and `none` are affected.

The harness already runs one hook for the edit tools: a `PreToolUse` command that exits 2 to block, the only blocking code,
rendered by the installer and verified for file edits (`docs/specs/harness-modules.md`, "The edit gate hook").

## Decision

This is a proposal. Nothing here is accepted until the owner says so.

When any key is at `ask` or `none`, attach renders a second `PreToolUse` hook for the Bash tool, which runs `wb gate-command
<harness>`. The command gate reads the tool call and:

1. allows a command that contains no word of a relaxed command (for `approve-plan`, the word `approve-plan`);
2. allows a command that is one simple command, with no shell control character and no quote around the word, that one of the
   rendered `ask` patterns matches, so the harness's `ask` rule then prompts the owner;
3. blocks every other command that names such a word, whatever wraps it (`bash -c`, `sh -c`, `env`, `eval`, `xargs`, a
   command substitution, a variable assignment, a path to `wb`);
4. blocks on any failure, a missing field, an oversized input or a crash.

The rendering record names the gate, and a key at `ask` or `none` reads `block` unless the record says the gate was rendered and
the harness file still hashes to the record. The default of `approve-plan` becomes `ask` only after the probe is repeated in
auto mode and passes, and after this decision is accepted. Increment I of the plan tries the two unverified assumptions first
(that a Bash hook blocks in auto mode, and that a hook that exits 0 leaves the `ask` rule in force); if either fails the plan
stops and the owner chooses between the alternatives below.

What stays a limit, and what the owner accepts: the gate reads text. A command that builds the word at run time (a variable
expansion, a decoded string) is not seen and, in auto mode, can be decided by the classifier. A command that merely names the
word, such as a `grep` or a commit message, is blocked until the owner runs it. A hook is not a boundary: an agent that can
edit the harness file in a way the live hash does not see, or that finds a channel the hook does not cover, defeats it.

This record adds to `2026-10-26-ask-level-spelling-limit`; it replaces its item 6 (the probe is repeated after the gate) and
makes the gate the main mitigation in place of the pattern list. Items 1 to 5 stand. The owner decides, when accepting this
record, whether to mark the earlier one `Superseded by` it.

## Alternatives considered

- **Accept the bypass and ship `ask` as an opt-in.** The cheapest; the owner would know that in auto mode a wrapper spelling can
  approve a plan. Rejected as the default path: it leaves the demonstrated hole open for the one command that is meant to need
  the owner. It remains available if the trial in Increment I fails.
- **Drop remote approval and keep the terminal.** The safest, and it gives up what the design was for. It remains available.
- **More patterns** (`Bash(bash -c *approve-plan*)`, `env`, `sh -c`). Rejected: a list of wrappers is open-ended, and an unmatched
  command is still decided by the classifier in auto mode.
- **Make the command check how it was invoked.** Rejected before and still: the agent controls its parent and its environment.
- **Always render the Bash hook, whatever the levels.** Stricter, and it would block a harmless command that names the word in
  every project. Rejected: render it only when a key is relaxed, so a project that keeps everything at `block` is unchanged.

## Consequences

- Good: the demonstrated bypass is closed in the way that does not depend on the classifier, using a block the project has
  already verified for file edits, and the owner's prompt still comes from the harness's own `ask` rule.
- Bad: a command that builds the word at run time is not stopped; the earlier decision's limit stays, narrower.
- Bad: false blocks. A command that names `approve-plan` for any reason other than running it is blocked in a project where
  the key is relaxed, and the agent cannot reread or search for the word with a shell. The owner runs such a command.
- Bad: the Claude harness module's layout changes, so its shipped approvals go stale until the owner runs
  `release-approvals`, and an installed project must be attached again to get the hook. Attach refuses a clone that already
  records a harness, so an existing clone needs a new one until a later plan adds a command to re-render.
- Bad: a hook that exits 2 only blocks while `wb` can start. `|| exit 2` covers a failure of the command; a hook that cannot
  start in the shell at all is not covered (`docs/specs/harness-modules.md`).

## Evidence

- The probe: owner-run, Claude Code 2.1.311, repository commit `230ae7e`, throwaway project `/tmp/probe-project`; the owner
  pasted each session, and the plan state and the level log were read afterwards. Recorded in the plan's Result for
  Increment F. The `env wb` spelling was not run in auto mode.
- The edit gate's behavior: `docs/specs/harness-modules.md`, "The edit gate hook" (exit 2 blocks; verified for the edit tools).
- The trial of Increment I: owner-run, Claude Code 2.1.311, repository head `174d62f`, a throwaway folder with a hand-written
  Bash hook that exits 2 on a word and an exact `ask` rule. A hook that exits 2 stopped `sh -c`, `bash -c` and `env` in auto mode
  and `bash -c` in default mode, with no prompt; a hook that exited 0 left the `ask` rule firing in both modes; a word the hook
  could not see (`echo probe""word`) ran with no prompt in auto mode. Recorded in `docs/specs/harness-modules.md`, "A Bash hook
  with an exit code and an `ask` rule". One run of each case.
- What the trial does not show: it used `echo`, not `wb`; the hook was a hand-written script matching one word, not the rendered
  `wb gate-command`; the `ask` rule was an exact string and not the rendered wildcard `Bash(wb approve-plan *)`; rule 2 of the
  decision (one simple command that an `ask` pattern matches) was exercised only as an exact match; a missing script, a JSON
  answer and a subagent's call were not tried. The record therefore does not prove the gate. Increment J's tests and its repeated
  probe are the test of the built gate.
