# Command permissions

Status: Current

Written by plan `2026-10-26-command-permission-levels` (Increment H), which built it. It describes the levels table, the keys, the
log, the rendering record, the command gate and `approve-plan` at the levels `ask` and `none`. One key, `approve-plan`, is built
beyond `block`; every other key offers `block` only. Extending a review (`wb run review-engine extend`) was part of the design,
was not built, and is listed under "Not built". The design is `docs/decisions/2026-10-26-per-command-permission-levels.md`, as refined by
`docs/decisions/2026-10-26-permission-levels-as-built.md` (accepted), which states what stands, what changed and what was not built;
where the two differ on the defaults or the offered levels, this spec follows the later record.

The owner has since directed that every `wb` command has a level, with a default that suits that command and no key limited to
`block`. That direction is written under "Planned: a level for every command" and is not built; the sections before it describe the
code as it is. The decisions it supersedes are named there and are not yet superseded: only the owner accepts a replacement.

## Scope

How the owner chooses, command by command, whether an action needs the owner at a terminal, an owner's confirmation on a
channel without a terminal, a delegate's passing a gate, or nothing. It covers the table of levels, its keys, the levels a key
offers, the shipped defaults, how a level takes effect, the digest that binds a confirmation to what was previewed, the log, how
a harness renders it, and the command gate that protects the rendering.

## Non-goals

- Anything on the compiled hard-stop floor (`floor.py`) or added as a hard stop by a module. The table never names one.
- The actions governed by action review, `safe-git commit` and `remove`, and the push check
  (`2026-10-25-module-commands-and-the-approver`, `action-review.md`).
- A command that builds a table for the owner. The owner edits the personal settings by hand, as for checkpoints today.
- Changing what an approval means. As built, only the owner's act makes a decision `Accepted`; the planned revision lets the owner
  loosen that through the `accept-decision` key.

## Assumptions and constraints

- The owner's personal settings are a file in the guarded store that an agent cannot write through the harness's file tools
  (`workbench/settings.py`, `2026-10-19-guarded-store`). A project, a plan, a review, a module or an agent cannot supply an entry
  (`2026-10-19-mandatory-review-personal-delegation`). **The store is writable from a shell**, as it is at every level: an agent
  with a shell can write the approvals file or the rendering record without running `wb approve-plan`. That is a property of the
  store and is accepted (`2026-10-26-ask-level-command-gate`, the clarification note).
- A harness renders permission rules into local files when the owner attaches it, and a `deny` or `ask` rule is checked before an
  `allow` (`harness-modules.md`). The neutral rules hold only `ask` and `deny` (`2026-10-19-restrictive-only-permissions`). A table
  entry therefore takes effect in a harness only after the next attach.
- The terminal test is a mistake guard and not authentication: a process can open its own pseudo-terminal
  (`2026-10-20-preview-then-owner-run-write`). At `ask` and `none` it no longer applies, and the barrier is the harness's rule and
  the command gate, which read text (see "The command gate" and "Limits").
- Verified by the owner's trials, recorded in `harness-modules.md`: an `ask` prompt reaches the owner's remote channel and a Yes
  or No given there runs or refuses the command (Claude Code 2.1.310); a `PreToolUse` hook for `Bash` that exits 2 stops a wrapped
  command in auto and default mode and a hook that exits 0 leaves an `ask` rule in force (2.1.311).

## Behavior

### The levels

| Level | Who runs it | What makes it run |
|---|---|---|
| `block` | the owner, never the agent | the harness denies the agent; the command's own terminal test applies exactly where it applies today (`wb release-approvals` has none and keeps none) |
| `delegated` | the agent | a gate the command declares has passed |
| `ask` | the agent | the owner confirms a harness prompt, and the command carries the digest of its preview |
| `none` | the agent | nothing |

`none` is a level and not the absence of one: it means that the command needs no confirmation and no gate, and its run is still
logged. `delegated` sits in the order by convention; it is a gate the command declares and not a step between `ask` and `none`.

Strictness, from strictest to least strict: `block`, `ask`, `delegated`, `none`. It orders the levels and settles nothing between a
checkpoint and the table: a key's level is its table entry, else its checkpoint reading, else its shipped default (see "The table").

### The table

The personal settings accept `version` 1 and 2. Version 2 may hold an object `levels`, from a key to a level; in a version 1 file
`levels` is an unknown entry and is ignored. A new file is seeded at version 1, so the owner changes `version` to 2 by hand to
use `levels`. The table is the single source of a level: an entry wins over the key's checkpoint in either direction, so loosening
a key is one edit. A `checkpoints` entry in the file is only a fallback for a key the table does not name, and its word is read as a
level, `stop` as `block` and `delegate` as `delegated`; `wb settings` prints a `translated <key>: <word> read as <level>` line for
each such reading (it is not a problem, so it is not a `settings:` line). When a key is in both and they differ, `wb settings`
notes that the level applies. `delegate` still takes effect for `approve-plan` only; a `delegate` that cannot take effect has its own note
and no `translated` line.

A key is a process module's declared checkpoint name (`approve-plan`, `accept-decision` and the others), or the command in the `wb`
spelling: `wb install`, `wb adopt`, `wb add`, `wb upgrade`, `wb attach`, `wb approve`, `wb pin`, `wb recover`,
`wb release-approvals`, and `wb run <command> <argument>` for each owner-run argument that an installed module declares. The key
`approve-plan` is the checkpoint and the command; `wb acknowledge` is not a key, because the checkpoints
`acknowledge-first-tier` and `acknowledge-second-tier` set it. The registry (`workbench/levels.py`) is built from what the
installer knows, and no module is named there; two declarations that give one key are refused. A key is a lowercase name or words
separated by single spaces, at most 96 characters.

### Reading rules

1. A missing file is seeded as today. A damaged file, an unsupported version, a duplicated key or a `levels` that is not an object
   reads as `block` for the whole table, except for the agent-safe keys and the declared module arguments that are not owner-run: they
   keep their default `none`, so that the agent can still run `wb settings` and `wb check` to report the damage (the owner's decision,
   Increment C). An explicit `block` the owner wrote for such a key is therefore not honored while the file or the table is
   damaged, even when the damage is one mistyped key elsewhere; it applies again once the file is repaired and the harness is
   attached again, and a `deny` already rendered into an attached clone stays until then. A value that is not one of the four levels reads as `block` for that key. A key that is not a valid name blocks
   the whole table, because a mistyped key must never leave a default of `ask` in force. `wb settings` reports each.
2. A key with no table entry reads as its checkpoint reading if the file sets one, and otherwise as its shipped default (below).
3. A level the key does not offer reads as `block` with a note.
4. A key on the compiled floor is refused, with a problem, and ignored. A valid key that no installed module or the installer
   declares is noted and ignored.

### Which levels a key offers

- `block`: every key.
- `delegated`: `approve-plan` only, whose gate is a converged, sealed review of the exact bytes (`delegation.py`). The gate must
  pass at the moment of the run, and the run counts only while the table still reads `delegated`.
- `ask`: `approve-plan` only. `none`: `approve-plan`, every agent-safe action and every declared module argument that is not
  owner-run; no other key offers it yet. A key offers a level only from the version that builds it for that command; `accept-decision`
  and every other key offer `block` only.

### Shipped defaults

Every default is `block`, except the agent-safe actions and the declared module arguments that are not owner-run, which default to
`none` because an agent may run them today. The mechanism for another default exists (`levels._DEFAULTS`), and the default of `approve-plan` was
meant to become `ask` once a probe passed. The probe (below) showed that `ask` is bypassable by a script the agent writes and
runs, which the owner accepted in writing, and the owner left the default at `block`: `ask` and `none` are the owner's opt-in.

### The preview and the digest (`ask`)

`wb plan-status <plan> --digest` is the read-only preview. It prints what an approval would bind (the project, the approval
command's declaration and helper hashes, the plan's path, its region hash and what the approval does not cover) and a line
`digest: <32 hex>`, writes nothing and exits 0. The digest is the first 32 lowercase hexadecimal characters of the SHA-256 of that
canonical text, so a confirmation cannot be reused by another clone, after the approval command changed or for another plan.
(Twelve characters were proposed and rejected: the plan is attacker-controlled and 48 bits can be ground; the owner never types
the digest at `ask`.)

### `approve-plan` at `ask` and `none`

| Form | Level | Result |
|---|---|---|
| `wb approve-plan <plan>`, standard input and output terminals | any | the owner's terminal command, unchanged: the owner types the first 12 characters of the region hash |
| `wb approve-plan <plan> --digest <32 hex>` | `ask` | recorded when the digest matches the region it computes now |
| `wb approve-plan <plan>`, no terminal | `none` | recorded, with no digest |
| any other form without a terminal | `block`, `delegated` | refused: approving a plan is owner-run |
| `wb approve-plan <plan> --digest …` | not `ask` here | refused: a digest needs the level `ask` and its rendered rule |
| `wb approve-plan <plan> --digest …` | `none` | refused as an unknown argument |

Without a terminal the command, in order: reads the level now (see "Rendering"), recomputes the digest in its own process, resolves
the plan a second time and compares everything, checks that the level and the plan belong to one project, writes the log attempt,
records the approval, and writes the outcome. It writes no log entry and records nothing when an equal approval already exists
("already approved"). The record it writes is the one the terminal command writes. Exit codes: 0 recorded or already recorded, 1
refused with nothing written, 2 usage, 3 recorded but the outcome could not be logged, 130 interrupted.

The agent shows the preview in the conversation before it asks. No code enforces that, and the prompt shows the command and the
digest and not the preview. An `ask` therefore proves that the owner saw the command and a digest. It does not prove that they
read the plan.

### Rendering

At attach, a harness that provides `permissions` renders, for each key whose command it can match, a `deny` at `block` and at
`delegated` (the delegated command is a different, agent-safe command), an `ask` at `ask`, and nothing at `none`. Only the `wb`
spellings of a relaxed key are asked or opened (`wb <command>` and the guarded store's own `bin/wb <command>`); the interpreter
spellings (`python3 -m workbench …`) stay denied, because an `ask` for them would let a planted package run under the owner's yes.
The floor's `ask` rules and the deny on the guarded store are unchanged. If the harness cannot render the command gate (it must
provide `hooks` and its layout must describe `hooks.command_gate`), no key is relaxed and every key renders a `deny`.

An agent-safe key and a declared module argument that is not owner-run (Increment C) render a `deny`, in every spelling, bare and
with arguments, only when the owner has set the key to `block`; at its default `none` it renders nothing. Such a key is in the
rendered table, in the record's `keys` (as `deny`) and in the table digest only while it is not at its default, so the default table,
its digest and the command gate (which counts only keys at `ask` and `none`) are what they were before these keys had a level, and a
clone attached earlier keeps its record. Setting an agent-safe key to `block` after attach changes the digest, so a relaxed key then
reads `block` until the harness is attached again, as for any change to the table. The hook entry points `gate`, `agent-gate` and
`gate-command` are not keys, so a `deny` for another key never stops a rendered hook.

**The rendering record.** At attach, before the files, the installer writes `projects/<id>/rendering` in the guarded store, strict
JSON, format 2: `harness` (the module name), `permissions`, `gate`, `table_digest` (of the effective table rendered from), `file` and
`file_hash` (the permissions file), `shared` (`path` and `hash`: the shared project settings file the layout names, `null` if it
did not exist), and `keys` (every key of the registry: `deny`, `ask`, `none`, or `unruled` for a key with no command to match). A
harness that provides no `permissions` renders nothing and leaves no record.

A key reads as `ask` or `none` only while all of these hold when the command runs, and as `block` otherwise (`block` and
`delegated` do not depend on the record): the record exists, is sound and is format 2; it says `permissions` and `gate`; it names
the attached harness (the local manifest's); its table digest equals the digest of the effective table now; it lists the key with
the same rule; the permissions file hashes to `file_hash`; and the shared settings file hashes to `shared.hash` (a file created,
changed or removed since attach, or one that cannot be read as a regular file, makes the keys read `block`). If the shared file
cannot be read at attach, no gate is recorded. `wb check` reports a permissions file that differs from the record, and a shared
file that appeared, changed or vanished while a key is relaxed. Changing the table or a module takes effect at the next attach;
`wb attach` refuses a clone that already records a harness, so no command restores a relaxed key in an attached clone (see "Not
built").

### The command gate

When a key is relaxed and the layout describes it, attach renders a second `PreToolUse` hook, for the `Bash` tool, running `wb
gate-command <harness> || exit 2` with the time limit the layout gives (60 seconds; longer than the gate's own 10-second deadline),
in the same event as the edit gate's hook, and protects both settings files with an `Edit` deny in the relative, `**/` and absolute
spellings. The layout fields are `hooks.command_gate` (`tool`, `field`, `timeout`) and `local_settings.shared`.

`wb gate-command` is agent-safe. It reads one tool call as JSON on standard input and prints nothing and returns 0 to allow, or
prints one `refused:` line and returns 2 to block; every failure, a crash, a deadline, an oversize command (64 KiB), a NUL byte, a
wrong tool and a project that cannot be read, is a block. The relaxed keys are the table's and also every key the record says
was rendered at `ask` or `none`, so a table set back to `block` after attach does not open the gate. A command that names no word of
a relaxed command is allowed. A command that is exactly the simple command the `ask` rule matches, on the raw text with single
spaces and case kept (`wb approve-plan <path> [--digest <32 hex>]`, or the same through the store's `bin/wb`), is allowed, and the
harness then prompts. Every other command that names the word is blocked, however it is written: after case and Unicode folding;
after removing every character that is not a letter or a digit (so quote splicing, backslashes and punctuation do not hide it);
after decoding each static `$'…'` string as bash decodes it, tried at every position; and, when the command holds `$ ? * [ { ` or a
backtick, when the letters of the word fall in order within three times its length, with at least a third of them written out, an
escape sequence, a glob character or an expansion standing for a letter, and the inside of an expansion also dropped (it may expand
to nothing). A command with more than 64 `$'…'` strings is blocked. The agent-safe `delegate-approve-plan` is exempt from the
word test, but not from the in-order rule.

A key whose command is an ordinary word (`wb install`, `wb adopt`, `wb add`, `wb pin` and the other single-word owner-run keys,
as opposed to `approve-plan` and `wb run <command> <argument>`) is read in command position (built by Increment E; decision
`2026-10-27-command-gate-command-position`): the gate counts a command as naming it only when it holds a launcher and the word, in either order
(`echo install | xargs wb` passes the word to the launcher as data), where the launchers are `wb` (also the end of the store's `bin/wb`) and `workbench` (of `python3 -m workbench`; the last
words of `rules.SPELLINGS`). The folding, the skeleton, the decoding of `$'…'` and the in-order rule for expansions, globs and
escapes are applied to the pair, so `w""b install`, `wb inst""all` and `wb $'\x69nstall'` are blocked, and `npm install`, `git add`, a
commit message or a path that holds the word are allowed. The exact pair `preview <action>` for each action of
`rules.PREVIEW_ACTIONS` is removed before the search, as `delegate-approve-plan` is, for these keys only; the pattern rule still reads the text as written,
so a preview that holds an expansion or a glob (`--dir $PWD`) is blocked and is run with the path spelled out. A command that names the word with no launcher
before it, such as an alias or a script the agent wrote that wraps the call, is not seen; the classifier remains the barrier for
it, as for the other limits listed under "Limits".

### The log

Every run at a level other than `block` that goes on without a terminal appends two lines to `level-log` in the guarded store, never rewriting one: the attempt, with
a random operation identifier, the time, the key, the level and the evidence (`digest:<d>` at `ask`, `converged-<n>-of-<bound>` for a
delegated approval, empty at `none`); then the outcome, with the same identifier, the time, `done` or `refused`, and a reason of at
most 200 printable ASCII characters. Lines are tab-separated, at most 1,024 bytes, and written by one `write` to a descriptor opened
for append that refuses a link, a non-regular file and a file with another hard link; the writer never reads the file. The log holds
about 4 MiB; at the cap a run above `block` is refused with a message that names the log, and the owner rotates it by hand. The
attempt is written after every read-only check and just before the change; if it cannot be written the command does nothing; if the
outcome cannot be written after the change, the command says so on standard error and exits 3. `levellog.read` and `levellog.report`
list the operations and the attempts with no outcome as unfinished (a killed process leaves an attempt after it acted, so
"unfinished" does not mean "not approved"); no `wb` command prints the log yet, and the owner can read the plain-text file.

### `wb settings`

It prints the `checkpoint` and `cap` lines it always printed, then one `level <key>: <level>` line for every key it knows: the
declared checkpoints, then the installer's owner-run commands, then the agent-safe actions (`wb verify`, `wb preview install`,
`wb preview adopt`, `wb preview upgrade`, `wb preview add`, `wb launch`, `wb check`, `wb plan-status`, `wb settings`), then `wb run
<command> <argument>` for each argument the installed modules declare (an owner-run argument first), with the defaults and the
table applied. An agent-safe key and a declared argument that is not owner-run default to `none`; every other key defaults to `block`.
The hook entry points, the dispatcher words and `delegate-approve-plan` are not keys. As built by Increments A and C of the plan, a
`block` set on an agent-safe key is rendered as a `deny` at the next attach ("Rendering"); the table a harness renders and digests holds
an agent-safe key only when it is not at its default, so an attached clone's record is unchanged. After the `level` lines it prints one `translated <key>:
<word> read as <level>` line for each checkpoint word it read as a level because the table does not name the key (Increment B).
Problems and notes print as `settings:` lines. Two declarations that
give one key are a refusal.

## Planned: a level for every command

Not built, except where a paragraph says "built by Increment ..." (the plan `2026-10-27-a-level-for-every-command`; Increments A, B, C, D and E are
built). It is the owner's direction of 2026-10-26, recorded here so a plan can implement it. Calls marked **(call)** are the
author's and are not the owner's until the owner confirms them.

**Intent.** The owner chooses their own risk appetite, command by command, and may loosen any protection that is theirs to loosen.
A state in which an owner has set every key to `none`, and so has no protections left on the commands, is an outcome of that
freedom and not a feature: there is no master switch, profile or command that sets it.

**Coverage.** Every command and subcommand that `cli.py` routes has a key, the agent-safe ones included (`verify`, `preview install`,
`preview adopt`, `launch`, `check`, `run`, `plan-status`, `settings`), so the owner can tighten a command that is always allowed
today. The hook entry points `gate`, `agent-gate` and `gate-command` are the exception: the harness runs them, they are not keys and
they stay always allowed (the owner's decision). A test fails when `cli.py` routes any other command or subcommand with no key, as the test
in `rules.py` does for the owner-run and agent-safe split. A subcommand has a key when it is a different action (`wb preview
install`, `wb preview adopt`, `wb run <command> <argument>`). A word that only dispatches (`wb run`, `wb preview`) is not a key, and each action reaches
one key, so no parent can tighten or bypass an action beneath it; `delegate-approve-plan` reaches the key `approve-plan`. A flag that
changes only how a command reports, such as `--digest`, belongs to its command's key. Each argument a module declares for a command has a key, derived from the declaration with no new field
**(call)**: an owner-run argument defaults to `block`, any other declared argument to `none`, as an agent may run it today. The
contract has no read-only declaration, so none is used. An undeclared command or argument is refused and has no key.

**Defaults.** A default is what the command does today **(call)**. An agent-safe command, which only reads or runs a helper that
checks its own pin, defaults to `none`. The owner-run commands, the checkpoints and the owner-run module arguments keep their
default of `block`. `approve-plan` stays `block`; the default is not raised to `ask` (see "Shipped defaults").

**Levels offered.** Every key offers `block` and `none`, except the owner-run arguments of module commands (`wb run <command>
<argument>` where the argument is owner-run), which offer `block` only until a later plan gives the module contract a way to pass a
level to a helper (the clarification note of `2026-10-26-a-level-for-every-command`, and "Not built"). `delegated` stays `approve-plan` only, and `ask` is offered by a key once
that key has a preview digest of its own, built as `approve-plan`'s is. Until then a key is never limited to `block`, because it
offers `none`. The order of building the digests is for a plan **(call)**: `install` and `adopt` first, because they already have a
preview, then the module arguments and `extend` (the deferred Increment G). At `none` an owner-run command runs without a terminal
and without a harness `deny`; the command's own checks of its input and its log entry apply, and the terminal prompt does not.
`accept-decision` offers the same levels, and `AGENTS.md` says that the owner decides who accepts a decision.

**One table** (built by Increment B). The `levels` table is the only place a level is set. A version 1 file's `checkpoints` are read as a fallback for a
key the table does not mention, and a table entry wins in either direction, so loosening a key is one edit. The checkpoint words
`stop` and `delegate` are aliases, read from a version 1 file, for `block` and `delegated`; the `level` lines of `wb settings` print
only the four level names, and a `translated` line says what a checkpoint word was read as. This replaces the rule that a key's level is the stricter of its checkpoint reading and its
table entry **(call)**.

**One way to run at `none`** (built by Increment D; no command but `approve-plan` uses it yet). Two modules hold what every owner-run
command shares. The kit's `wbkit/levels.py` is the part that needs nothing else of the workbench: `may_run(level, terminal)` is true
at a terminal and, without one, only for the level `none` (a missing, unreadable or unknown level is no level, so only a terminal
runs), and the log's attempt and outcome lines and their append (`begin`, `finish`, `finish_refused`), which `levellog.py` calls
so that the installer and a helper write one format. Adding it did not change a kit function, so `wbkit.API` stays 1. The
installer's `levelrun.py` adds what needs the rendering record: `route` goes on at a terminal without reading anything, and
otherwise reads the key's level as `approve-plan`'s is read (`rendering.effective_level`: the record, the hashes and the gate must
hold) and refuses with the caller's text unless `may_run` says the command may go on; `logged` and `done` write the attempt after
every check and just before the change and the outcome after it, and write nothing for a run that changes nothing. `approve-plan`
uses `level_now`, `logged` and `done`, and its behavior is unchanged.

**Out of scope.** The compiled hard-stop floor is unchanged and is not a key (see "Non-goals").

**Decision.** `2026-10-26-a-level-for-every-command` (accepted by the owner on 2026-10-26) refines
`2026-10-26-per-command-permission-levels` and `2026-10-26-permission-levels-as-built` on the offered levels, the shipped defaults
and the checkpoint rule, and the note that `accept-decision` offers `block` only. `2026-10-19-restrictive-only-permissions` is not
changed: a level of `none` renders no rule, so the neutral rule list still holds only `ask` and `deny`.

**Left to the builder.** The order of the increments, each key's digest content, the wording of the notes, and the layout of
`wb settings` output, which is grouped by command.

### Planned acceptance criteria

P1. Every command and subcommand `cli.py` routes has a key, except `gate`, `agent-gate` and `gate-command`, and the drift test fails
when any other has none.
P2. With no settings, every agent-safe command reads `none` and every other key reads as it does today, `block`.
P3. A table entry sets the level of its key in either direction, whatever the key's checkpoint says; a version 1 `stop` or
`delegate` for a key the table does not mention reads as `block` or `delegated`, with a note.
P4. Every key except the owner-run arguments of module commands accepts `block` and `none`, and a level a key does not yet offer
reads as `block` with a note.
P5. With every such key set to `none`, no command refuses for want of a terminal or a harness `deny`, the floor still applies, and
each run that changes something is logged.
P6. `accept-decision` set to `none` lets an agent accept a decision, and at `block` it does not.

## Not built

- `none` for the owner-run arguments of module commands (`wb run mempalace init`, `mine`, `wb run remote-runner fetch-overwrite`
  and the review engine's `reset`, `archive`, `prune`, `amend`, `extend`). The helper checks its own terminal and the contract has no
  way to pass it a level. A later plan, after a decision on the module contract, would let the launcher pass the level and have the
  helper use the kit's level function. Until then these keys offer `block` only.
- `wb run review-engine extend` at `ask` and `none` (Increment G of the plan). The declaration schema (`declarations.py`) has no
  field for the levels an owner-run argument offers, and the installer may not name a module's command. A later plan needs: a field
  such as `levels` on a command, a decision for that change to the module contract, a helper that prints and checks a digest of the
  review's `status` and `n`, and the log attempt written before the helper is launched.
- The keys `reset`, `archive`, `prune`, `amend`, `acknowledge-second-tier`, `submit-remote-job` and `push-shared-branch`: each needs
  its own preview digest and offers `block` only. `accept-decision` offers `block` only; the planned revision above changes that.
- The rule that a command reaching more than one key takes the strictest level of them: each command reaches one key today.
- A command that re-renders an attached clone, so a table or module change leaves `ask` and `none` reading `block` until a new clone
  is attached.
- A provenance check inside `approve-plan`, managed settings, and a store whose approvals a shell cannot forge.

## Limits

These are accepted by the owner in writing (`2026-10-26-ask-level-spelling-limit`, `2026-10-26-ask-level-command-gate` and its
clarification note) and are tested where a test can show them (`tests/test_command_gate.py`).

- The gate reads text. A word whose letters are not in the text (base64, `rev`), a word built from variables whose parts lie farther
  apart than the window, a script file or program that makes the call (`python3 x.py` ran with no prompt in the owner's probe), a
  function or alias defined earlier, and a `*` standing for more than three letters are not seen.
- A command that merely names the word, such as a `grep` or a commit message, is blocked while a key is relaxed; the owner runs it.
- A hook is not a boundary. The `ask` rule and the gate are best-effort matches; the auto-mode classifier remained the barrier for the
  rest (it denied the script and base64 cases in the owner's probe, which the gate did not control).
- A store or settings file that cannot be read blocks every Bash call while a key is relaxed, `wb check` included; the recovery is
  the owner's terminal. "Yes, and don't ask again" writes an allow rule into the per-clone settings file, whose changed hash makes the
  keys read `block`.
- **Untested, as of this text:** that the `Monitor` tool or a skill's `!` shell run outside the `Bash` matcher and the `Bash(…)`
  rule; that a project-defined agent or skill file can set a permission mode that overrides an `ask` rule; user-level
  `disableAllHooks`; whether Claude Code applies a removal of a hook mid-session; and the settings edit, act, restore sequence end to
  end (the edit step was denied by a permission layer that was not identified). In this self-hosted repository the code the
  launcher runs is in the agent's write scope.

## Evidence

- Trial of an `ask` prompt: owner-run, Claude Code 2.1.310, 2026-10-26 (`harness-modules.md`, "An `ask` prompt answered from the
  remote channel").
- Trial of a Bash hook: owner-run, Claude Code 2.1.311, 2026-10-26 (`harness-modules.md`, "A Bash hook with an exit code and an `ask`
  rule").
- Probes of spellings of `approve-plan` at `ask`, before and after the command gate: owner-run, 2026-10-26; the first stopped the
  plan (`bash -c` approved a plan in auto mode); the second, at commit `2cfd762`, is in the Result of Increment J of the plan.
- Security reviews of the design and of the built code, read-only in effect, in the plan's Result for Increments D, J and H.

## Acceptance criteria

1. With no settings, or with a version 1 file, every key reads `block` except the agent-safe actions and the declared module
   arguments that are not owner-run, which read `none`, and the safety controls are unchanged: the floor, the
   harness `deny` rules, the guarded store and the terminal tests. `wb settings` prints the same checkpoint lines as before.
2. A table with an unknown key, a level that is not offered, a floor key, a duplicate key, a key that is not a valid name or a value of
   the wrong type is reported, and the affected key (or the whole table, for a bad key name) reads as `block`.
3. `delegated` for a key with no declared gate reads as `block` with a note. `delegated` for `approve-plan` behaves as the existing
   decision requires, and writes its log entry first.
4. At `ask`, `wb approve-plan <plan> --digest <32 hex>` approves the plan when the digest matches, and refuses, writing no approval,
   on a mismatch, a changed plan, a missing rendered rule, a changed harness file or shared settings file, and a missing or unwritable
   log. At `none` it runs with no digest and refuses a digest. At `block` it still refuses without a terminal.
5. At no level can a table entry cause a floor action to run.
6. A rendered harness holds a `deny` for a key at `block`, an `ask` for the `wb` spellings of a key at `ask`, none for a key at `none`,
   the command gate's hook when a key is relaxed, and the record says so. With no record, a damaged record, a table changed since
   attach, a harness without `permissions` or without the gate, or a settings file changed since attach, every relaxed key reads as
   `block`; `wb check` reports the difference.
7. The command gate blocks every wrapper, splice, escape and expansion form of the tests, allows the exact forms, and blocks on every
   failure; the stated limits pass and are pinned by tests.
8. Every run at `ask`, `delegated` or `none` that changes something leaves an attempt line and, on every path, an outcome line with
   the same identifier; a run at `block` and a run that changes nothing leave none. An attempt with no outcome is listed as
   unfinished.

## Review record

The design was reviewed by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-26, at
the owner's request: three rounds, the bound of 3, not extended, not converged; all five findings were applied. The plan's later
revisions (2 to 4) were not reviewed by a second reviewer; the engine was at its bound. The built code was reviewed by the `reviewer`
agent in rounds for each increment and by the `security-reviewer` agent for the design of the log, the design of the command gate and
the built code; none of the security reviews could run an experiment, and the strings they proposed were run by the author. See the
plan's Result.

The section "Planned: a level for every command" was reviewed on 2026-10-26 by the review engine (spec review `spec-5bcae25932e2d2fa`,
`ask-codex`, model `gpt-5.6-terra`, effort medium): one round of the bound of 3, one finding (a decision missing from the governing
list), applied. The owner approved that section on 2026-10-26 as the direction for a plan. The approval does not accept the
decisions it proposes to supersede, does not approve a plan and authorises no implementation. The author's calls marked **(call)**
were approved with it except where the owner says otherwise.

## Governing decisions and references

- Decisions: [2026-10-26-per-command-permission-levels](../decisions/2026-10-26-per-command-permission-levels.md),
  [2026-10-26-permission-levels-as-built](../decisions/2026-10-26-permission-levels-as-built.md),
  [2026-10-26-ask-level-spelling-limit](../decisions/2026-10-26-ask-level-spelling-limit.md),
  [2026-10-26-ask-level-command-gate](../decisions/2026-10-26-ask-level-command-gate.md),
  [2026-10-23-delegated-plan-approval](../decisions/2026-10-23-delegated-plan-approval.md),
  [2026-10-19-mandatory-review-personal-delegation](../decisions/2026-10-19-mandatory-review-personal-delegation.md),
  [2026-10-19-compiled-hard-stop-floor](../decisions/2026-10-19-compiled-hard-stop-floor.md),
  [2026-10-19-restrictive-only-permissions](../decisions/2026-10-19-restrictive-only-permissions.md),
  [2026-10-20-preview-then-owner-run-write](../decisions/2026-10-20-preview-then-owner-run-write.md),
  [2026-10-24-project-guarantees-a-floor](../decisions/2026-10-24-project-guarantees-a-floor.md).
- Specs: `trust-and-approval.md`, `code-work.md`, `installer-interface.md`, `harness-modules.md`.
- Plan: `docs/plans/2026-10-26-command-permission-levels.md`. References: none.
