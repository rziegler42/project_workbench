# The command gate leaves a literal `wb run` command and a sibling command name alone

Status: Accepted by the owner on 2026-10-27

## Context

`2026-10-27-command-gate-command-position` (accepted, with its clarification note) has the gate block a Bash command that holds a
launcher spelling (`wb`, `workbench`) and the word of a relaxed single-word key (`wb install`, `wb add`, `wb pin`, ...) in either
order, unless the command is exactly the simple command the `ask` rule matches. The words are read in the folded text and in the
skeleton (the text with every character that is not a letter or a digit removed). The decision judged the cost small, as it was
for a rare word like `approve-plan`.

Running the built gate (`workbench/command_gate.py`, `judge`; Python 3.14.4, commit `2a0dea7`) with the keys the plan has made
relaxable shows the cost is not small:

- With `wb add` relaxed, `wb run safe-git commit --expected-head <40 hex> --subject 'Add tests' -- tests/test_add.py` is blocked,
  and so is `... --subject 'Fix padding'`. With `wb install` relaxed, a commit of `workbench/install.py`, or one whose subject holds
  `Install`, is blocked; the same for `wb upgrade` and `Upgrade`, and for `wb pin` with `pin`, `mapping`, `shipping` or `spinner`.
  `wb run safe-git commit` is how the project makes every commit, so an owner who relaxes any of these keys stops the agent from
  committing. The owner trial of Increments F and G did not run a commit and missed it.
- With `wb approve` relaxed, `wb approve-plan docs/plans/a.md` is blocked, because `approve-plan` holds `approve`. It stays blocked
  when `approve-plan` is relaxed too, because each key is judged alone.
- The skeleton also joins letters across words: `git commit -m 'add new base'` is blocked with `wb add` relaxed, because `new base`
  becomes `newbase` and holds `wb`; and `git diff workbench/install.py` is blocked with `wb install` relaxed, because `workbench`
  is a launcher spelling and `install` follows. This decision does not change either (see "Alternatives considered").

None of these commands runs the relaxed command. In the first, `wb run` dispatches only to a declared module command and never to
an owner-run `wb` verb, and its arguments reach that command's pinned helper as text.

## Decision

Accepted by the owner on 2026-10-27. Nothing here is built; Increment I of the plan `2026-10-27-a-level-for-every-command` builds it.

1. **A literal `wb run` command is not searched for a single-word key.** For a relaxed key of the form `wb <word>` (not
   `approve-plan`, not `wb run <command> <argument>`; the exemption is decided per key and is never an early return for the
   others), a command is allowed when it is matched in full (`fullmatch`, so no trailing newline) on the raw text by
   `(wb|<the guarded store's bin/wb>) run <name>( <argument>)*`, where `<name>` is `[A-Za-z0-9][A-Za-z0-9._+-]{0,63}` (the name
   rule of a pin or a command) and is not a launcher spelling or a verb of `rules`, and each `<argument>` is either a plain token
   (`[A-Za-z0-9._/:=@,+-]+`) or one single-quoted string with no quote inside, which may hold any other character, a newline and
   a carriage return included (bash reads a single-quoted string literally). The text is matched as written, so a folded or
   Unicode lookalike of `wb` does not match and is judged as now. Such a command names the word only as data, because `wb run`
   dispatches to a declared, pinned module command and never to an owner-run verb, and its arguments reach the helper as `argv`.
   A command with an operator, a newline outside quotes, a redirection, a substitution, a double-quoted or backslash-escaped
   argument, or any other form is judged as it is now. The keys `wb run <command> <argument>` (`wb run mempalace init`) and
   `approve-plan` are not exempted.
2. **A sibling command name is removed before the search for its prefix key.** For a key `wb <word>`, the exact token of another
   `wb` command that `rules` names and that begins with `<word>-` (today `approve-plan` for `wb approve`) is removed from the
   folded text before the search, as `delegate-approve-plan` is removed for `approve-plan`. The in-order rule still reads the text
   as written, so `wb approve${X}` and `wb approve"-plan"` are still seen. The sibling keeps its own rule: a key and a deny when
   it is owner-run, or none when it is agent-safe.
3. **The block message names what happened.** For a key at `none` it does not mention an `ask` rule; it says the command names the
   word in a form the gate cannot tell from a call, and that a path with `~` or `$VAR` and a compound command are read that way.
   `judge` is given the level of each relaxed key for this.
4. **Nothing else changes.** The levels, the rendering, the log, the 64 KiB and `$'` limits, the failure to a block, the skeleton
   and the in-order, either-order and pattern rules, and the accepted limits of the earlier decisions and the clarification note
   stand.

## Alternatives considered

- **Leave the gate and tell the owner not to relax common words.** Rejected: it makes the keys the plan builds unusable, against the
  owner's direction that no key be limited to `block`.
- **Exempt only `wb run safe-git commit`.** Smaller, but it names a module in the installer, which `2026-10-21-module-code-lives-in-modules`
  forbids unless the name comes from a declaration, and it leaves `wb run code-work check --files install.py` blocked. Rejected.
- **Parse the shell properly and judge the command position.** Rejected: a shell parser here is a larger, riskier parser of untrusted
  text than the gate's folding, and the gate is a speed bump, not a barrier.
- **Read the word only as a whole token and drop the skeleton.** Rejected: the skeleton is what catches `wb inst""all`.
- **Build the skeleton within each whitespace-separated piece** (so `new base` is not `wb`). Rejected after review: bash deletes a
  backslash followed by a newline, so `w\<newline>b install` runs `wb install` and no piece holds `wb`; fixing that needs the
  continuation removed first, and the gain is one rare false block.
- **A small tokenizer that judges the launcher and the word as adjacent tokens**, instead of the either-order rule. It would remove
  the `workbench/install.py` and `new base` false blocks, but the clarification note's `echo install | xargs wb` needs a rule for
  data that reaches a launcher, so it is a larger change to a parser of untrusted text and needs its own decision.
- **Allow `<name>` only when a module declares it.** Possible through the manifest, and stricter; rejected for now because the
  gate does not read the manifest, and a name that is not declared fails in `wb run` and runs nothing.
- **Judge `wb approve-plan` by its own key only.** That is point 2; the exemption is limited to names `rules` gives, so it cannot be
  used to hide the word `approve` in any other spelling.

## Consequences

- Good: a relaxed `wb add`, `wb install`, `wb upgrade`, `wb pin` or `wb approve` no longer stops `wb run safe-git commit` or any
  other `wb run <name>` call with literal arguments, whatever words its subject or paths hold, and no longer stops `wb approve-plan`.
- Bad, still true: the exemption is only that one form. With a key such as `wb install` relaxed, `wb check tests/test_install.py`,
  `wb plan-status docs/plans/x-install.md`, `git diff workbench/install.py` (the launcher `workbench` and the word), `git commit -m
  'add new base'` for `wb add`, and any command with `$ ? * [ {` and scattered letters stay blocked. Relaxing a common word is
  still costly, and the owner may leave such a key at `block`.
- Bad: a commit subject with an apostrophe cannot be single-quoted, so the agent rewords it; and with `approve-plan` relaxed,
  `wb run safe-git commit --subject 'approve-plan docs'` stays blocked.
- Bad: the exempt form is a command the gate no longer reads for these keys. It is safe only because `wb run` runs declared module
  commands and never an owner-run verb, and because the arguments are literal. If a module's helper ran `wb install` from its own
  arguments, the gate would not see it: that is the module's pinned code, which the owner approved, and the harness `deny` stays
  for `python3 -m workbench` spellings.
- Bad: the gate has more rules to keep in step with `rules` and `levels`, and more to review. A security review is owed when it is
  built (a permission boundary and a parser of untrusted text), and runs only when the owner asks.
- Bad: a compound command that holds both a launcher and the word (`npm install && wb check`) is still blocked and is run as two
  calls, as the clarification note says; a quoted double-string argument to `wb run` is also not exempt, so an agent writes the
  commit subject in single quotes.

## Evidence

Run on 2026-10-27 at commit `2a0dea7` (Python 3.14.4): `judge` from `workbench/command_gate.py` with the relaxed keys named above on
the commands in "Context" (the reviewer of this record also traced the code by reading and found the backslash-newline gap in the
dropped point, by reasoning, without running it), which returned the blocking reason for each (the commit commands for `wb add`, `wb install`, `wb upgrade`
and `wb pin`; `wb approve-plan` with `wb approve` relaxed, alone and with `approve-plan` relaxed too; `git commit -m 'add new
base'` with `wb add`). The owner trial of Increments F and G (2026-10-27, recorded in the plan's Result) showed the gate allowing
`git add -A` and `wb preview install` and blocking `echo install; wb check`, and ran no commit. The behavior proposed here was not
built or tested.

## Related files and decisions

- `docs/specs/command-permissions.md`, "The command gate"; `workbench/command_gate.py`
- [2026-10-27-command-gate-command-position](2026-10-27-command-gate-command-position.md)
- [2026-10-26-ask-level-command-gate](2026-10-26-ask-level-command-gate.md)
- [2026-10-26-a-level-for-every-command](2026-10-26-a-level-for-every-command.md)
- `docs/plans/2026-10-27-a-level-for-every-command.md`
