# The command gate reads a single-word command in command position, not the word alone

Status: Accepted by the owner on 2026-10-27
Date: 2026-10-27

## Context

`2026-10-26-ask-level-command-gate` (accepted) has the gate block every Bash command that names a word of a relaxed command, unless
the command is exactly the simple command the `ask` rule matches. It accepted the false blocks as a consequence: "a command that
names `approve-plan` for any reason other than running it is blocked". That is a small cost for `approve-plan`, a word that appears
almost nowhere else.

`2026-10-26-a-level-for-every-command` (accepted) lets the owner set any key to `none`, including `wb install`, `wb adopt`,
`wb upgrade`, `wb add`, `wb approve`, `wb pin` and `wb attach`. The words of those keys are everyday words. Run against the built
gate with `wb install` relaxed (`workbench/command_gate.py`, `judge`; Python 3.14.4, commit `3d2567b`), these are blocked: `wb
preview install ...` (the agent's own read-only preview), `npm install`, `git commit -m 'install deps'`, `ls docs/install.md` and
`python3 -m workbench install ...`; only `wb install ...` itself is allowed. With `wb add` relaxed, `git add` would be blocked the
same way. So a `none` on any of these keys would stop the agent from doing ordinary work, which the earlier decision never
intended, and the plan `2026-10-27-a-level-for-every-command` cannot build `install` and the keys after it on the gate as it is.

## Decision

Accepted by the owner on 2026-10-27. Nothing here is built; Increment E of the plan `2026-10-27-a-level-for-every-command` builds it.

1. **A single-word command key is read in command position.** For a relaxed key of the form `wb <word>`, the gate counts a command
   as naming it only when a launcher spelling comes before the word, in order: `wb`, the guarded store's own `bin/wb`, or
   `workbench` (as in `python3 -m workbench`). Every existing way of hiding the word applies to the pair, not to the word alone:
   case and Unicode folding, the skeleton (every character that is not a letter or a digit removed), decoded `$'...'` strings, and
   the in-order rule for expansions, globs and escapes. A command that names the pair and is not exactly the simple command the `ask`
   rule matches is blocked as now.
2. **The keys already read as several words are unchanged.** `approve-plan` is still read as the word alone, as the earlier decision
   has it, because it is distinctive, and `wb run <command> <argument>` is still read as its words in order.
3. **The preview of an action is exempt, as `delegate-approve-plan` is.** `wb preview <action>` is agent-safe and has its own key;
   the gate removes the exact token pair `preview <action>` for the actions `rules.PREVIEW_ACTIONS` names before it searches, and
   the in-order rule still reads the text as written.
4. **Nothing else changes.** The levels, the rendering, the record, the log, the `ask` rule, the 64 KiB and `$'` limits, the failure
   to a block and the accepted limits of the earlier decision and its note stand.

## Alternatives considered

- **Leave the gate as it is and accept the false blocks.** An owner who relaxes `wb install` would lose `npm install`, `git add`-like
  commands and any message holding the word. Rejected: it makes `none` unusable for the common words.
- **Keep `install`, `adopt` and the rest at `block` only.** The plan would drop Increments E to H. Rejected by the owner's direction
  that no key be limited to `block`; it remains the fallback if this decision is not accepted.
- **Match on the launcher alone** (block any command that names `wb` while a key is relaxed). Rejected: it blocks `wb check` and
  every command the agent runs.
- **Hand the guarded words to the harness only** (rely on the `ask` rule and the classifier). Rejected for the reason the earlier
  decision gives: an unmatched command is decided by the classifier in auto mode.

## Consequences

- Good: a relaxed `wb install`, `wb add` and the others no longer block `npm install`, `git add`, a commit message or a file name,
  and `wb preview install` still runs.
- Bad: a command that spells the launcher and the word apart, in order, in ordinary text is still blocked, for example a commit
  message holding `wb` and later `install`. This is a smaller class than now.
- Bad: a command that names the word without a launcher before it is not seen. Something that builds the launcher at run time
  (`W=w; ${W}b install`), a script, a function or an alias that wraps the call is not seen. These are within the limits the earlier
  decision and its note already accept (a word built at run time; script and file indirection), but the word `install` alone no longer
  stops `sh -c 'x install'` where `x` is an alias or a script the agent wrote. The classifier remains the barrier for those.
- Bad: the gate has one more rule to keep in step with `levels` and `rules` (the launcher spellings and the preview actions), and a
  test pins that.
- Neutral: a security review is owed when it is built (a permission boundary and a parser of untrusted text), and runs only when
  the owner asks.

## Evidence

Read and run on 2026-10-27 at commit `3d2567b` (Python 3.14.4): `workbench/command_gate.py` (`words`, `forms`, `judge`); `judge` run
with the relaxed key list `["wb install"]` on the commands above, which returned the blocking reason for each of them except `wb
install --dir x` and the commands that name neither `install` nor `wb`. The behavior of the proposed rule was not built or tested.

## Related files and decisions

- `docs/specs/command-permissions.md`, "The command gate"; `workbench/command_gate.py`
- [2026-10-26-ask-level-command-gate](2026-10-26-ask-level-command-gate.md)
- [2026-10-26-a-level-for-every-command](2026-10-26-a-level-for-every-command.md)
- `docs/plans/2026-10-27-a-level-for-every-command.md`

## Clarification note, 2026-10-27 (approved by the owner on 2026-10-27)

Decision 1 says a launcher spelling comes before the word, in order. The security review of Increment E found that this lets a
literal word reach a literal launcher as data, with the word first: `echo install | xargs wb`, `for w in install; do wb $w; done`,
`set -- install; wb "$@"`. The earlier word-alone rule blocked each of them; the in-order rule allowed them (shown by running
`judge`, commit `3d2567b` plus the uncommitted increment, Python 3.14.4). The increment therefore counts the launcher and the word in
either order: a command that holds both is blocked unless it is exactly the call the `ask` rule matches. The cost is that a compound
command holding both, such as `npm install && wb check`, is blocked and is run as two calls. The rest of the decision is unchanged,
and the text above is not edited.
