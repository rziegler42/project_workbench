# The command gate reads the first argument of a module command as data

Status: Accepted by the owner on 2026-10-28

## Context

`2026-10-27-command-gate-literal-arguments` (accepted) leaves a literal `wb run <name> <args>` command alone when the relaxed key is a
single word (`wb install`, `wb add`, ...). It names the keys of the form `wb run <command> <argument>` (today the review engine's
`extend`, `reset`, `archive`, `amend` and `prune`, and `wb run mempalace init`) as not exempted, and the gate searches such a command
for the key's two words, command and then argument, in the folded text and in the skeleton.

The owner has set the five review-engine keys to `ask` (`2026-10-27-owner-run-arguments-take-a-level`). The read-only previews are
`wb run review-engine preview extend|reset|archive|amend|prune ...`. Each holds the key's two words, so the gate blocks it unless
it is the simple form the `ask` rule matches, which it is not. An agent therefore cannot show the owner the preview that the
digest binds, and the flow "the agent shows the preview, then runs the argument with `--digest`" works only if the owner runs the
preview. The same text match blocks any call that merely holds the two words in order, such as a `decide` whose reason says
`extend`. The gap was found in use on 2026-10-28 and is recorded in the Result of `2026-10-27-levels-for-the-review-workflow`.

None of these calls runs the relaxed argument. The launcher dispatches on the first argument only: `commands.py` refuses a first
argument the declaration does not list and tests the owner-run list on that same first argument. A call whose first argument is
`preview` never runs `extend`, and the helper's `preview extend` is read-only.

## Decision

Proposed. Nothing here is built; Increment B of `2026-10-28-gate-reads-module-arguments` builds it once the owner accepts this record.

1. **The first argument of the key's own command is read as data.** For a relaxed key `wb run <command> <argument>`, a command is
   not searched for the key's words when all of these hold: it is matched in full on the raw text by the form the accepted decision
   gives (`(wb|<the guarded store's bin/wb>) run <name>( <argument>)*`, with the same name and argument rules and the gate's
   64 KiB command cap; a name that starts with `-`, as in `wb run --provides <cap> ...`,
   does not match and stays searched); `<name>` equals the key's `<command>`; and its first argument is a
   plain token (`[A-Za-z0-9._/:=@,+-]+`, no quote, escape, expansion or glob) that is not the key's `<argument>`. The exemption is
   decided per key and is never an early return for the others.
2. **Only the key's own command is freed.** A differently named command that holds the words (a pin of the same helper under
   another name, or `wb run safe-git commit --subject 'extend review-engine'`) is judged as now.
3. **Everything else stays as it is.** A first argument in quotes or with a quote inside it, a double-quoted, escaped, substituted
   or globbed argument, a compound command, a newline outside quotes, a trailing newline, a `wb launch` spelling, the single-word
   keys, `approve-plan` and the exact simple form of the relaxed command are judged as the accepted decisions say. The levels, the
   rendering, the log, the launcher, the helper and the digests do not change.

This refines the accepted decision's point 1 (its last sentence, that the `wb run <command> <argument>` keys are not exempted). It
does not edit that record.

## Alternatives considered

- **Leave the gap and tell the owner to run the previews.** Safe, and nothing to build. Rejected: the point of the `ask` level is
  that the owner can drive the workflow from a phone, and the owner must then run every preview by hand in a terminal.
- **Rename the preview so its text does not hold the argument's word.** Rejected: the gate reads the skeleton, and `preview` of
  `extend` still spells `extend`; a rename only moves the word.
- **Exempt any `wb run <name> ...` command for these keys, whatever the name.** Rejected: it frees a pin of the same helper under
  another name, and a pin is owner-approved code whose first argument the gate has not been told about.
- **Read the module's declaration in the gate, and allow a first argument that is declared and not owner-run.** Stricter, but the
  gate does not read manifests, and `2026-10-21-module-code-lives-in-modules` keeps module knowledge out of the installer. Rejected
  for now.
- **Parse the shell properly.** Rejected for the reasons the accepted decision gives: a larger and riskier parser of untrusted text
  for a speed bump that is not a barrier.
- **Allow a quoted first argument.** Rejected: bash removes the quotes, so `'extend'` is the argument `extend`. The rule needs a
  plain first token so the gate never reads a quoted spelling of the key's argument as another one.

## Consequences

- Good: with a review-engine key at `ask` or `none`, an agent can run `wb run review-engine preview <argument> ...`, `status`,
  `decide` (whatever its reason says) and every other literal call of that command, so the owner sees the preview from a phone and
  the harness prompt then shows the digest for the owner-run argument.
- Good: the change is small and local to `judge`; the exact simple form of the relaxed command is still allowed, so its harness
  prompt still fires.
- Bad: the exempt form is a command the gate no longer reads for these keys. It is safe only because the launcher dispatches on the
  first argument and refuses an undeclared one, the first token must be plain, and the whole command is one literal call. If a
  module's helper ran another of its arguments from the text of its own arguments, the gate would not see it; that is the
  module's pinned code, which the owner approved, and the harness `deny` stays for the `python3 -m workbench` spellings.
- Bad, by design: the exemption is per key. With `extend` and `reset` both at `ask`, `wb run review-engine reset ...` is freed for
  the `extend` key but still judged for the `reset` key; a key left at `block` is protected by the launcher's terminal test, not
  by the gate.
- Bad: a call that holds the words in another command stays blocked while a key is relaxed, because only the key's own command is freed.
- Bad: a first argument written in quotes is blocked even when it is harmless, so an agent writes it plain.
- Bad: the gate has one more rule to keep in step with the declaration of the commands. A security review is owed when it is built
  (a permission boundary and a parser of untrusted text), and runs only when the owner asks.

## Evidence

Run on 2026-10-28 at commit `49cbf6201425dec8880736b5f702502716ef09d3` (Python 3.15.0): `judge` from `workbench/command_gate.py`,
called with `STORE_BIN` as in `tests/test_command_gate.py`, with the key `wb run review-engine extend` and then `wb run
review-engine reset`, on the cases of Increment B. With `extend` relaxed it blocked `preview extend <document> 4` and a `decide`
whose reason says `extend`, and allowed `preview reset`, `status`, and the exact simple form of `extend` with and without
`--digest`; with `reset` relaxed it blocked `preview reset <document>` and allowed the others. It blocked each quoted, compound,
substituted and trailing-newline spelling for the relaxed key. `wb run other preview extend` was allowed with `extend` relaxed,
because the command name is not `review-engine`. The cases were run through a probe script in the session's scratch directory, which
changed nothing in the tree. The reading of the launcher (`commands.py` dispatches on `args[0]`) and that the helper's `preview` is read-only (its docstring, in
`packages/workbench/review-engine/helper/review-engine`) are by reading, not by running. The
behavior proposed here was not built or tested.

## Related files and decisions

- `docs/specs/command-permissions.md`, "The command gate"; `workbench/command_gate.py`
- [2026-10-27-command-gate-literal-arguments](2026-10-27-command-gate-literal-arguments.md), refined here
- [2026-10-27-command-gate-command-position](2026-10-27-command-gate-command-position.md)
- [2026-10-27-owner-run-arguments-take-a-level](2026-10-27-owner-run-arguments-take-a-level.md)
- `docs/plans/2026-10-28-gate-reads-module-arguments.md`
