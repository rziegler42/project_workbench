# Command permissions

Status: Current

Written by plan `2026-10-26-command-permission-levels` (Increment H), which built the levels table, the keys, the log, the
rendering record, the command gate and `approve-plan` at the levels `ask` and `none`, and extended by plan
`2026-10-27-a-level-for-every-command`, which built a level for every command (the section "A level for every command"): a key for
every command and subcommand the owner can govern, the agent-safe ones included, a default that suits each, and `none` for every
owner-run installer command and for `accept-decision`, and by the plan `2026-10-27-rerender-attached-harness`, which built
`wb rerender` ("Re-rendering an attached clone"), and by the plan `2026-10-27-levels-for-the-review-workflow`, which built `ask` and
`none` for the review engine's five owner-run arguments. `approve-plan` alone offers `delegated`, and it and those five offer `ask`. The keys that still offer
`block` only are listed under "Not built"; `wb rerender` offers it by design and is described in its own section. The design is `docs/decisions/2026-10-26-per-command-permission-levels.md`, as refined by
`docs/decisions/2026-10-26-permission-levels-as-built.md` and `docs/decisions/2026-10-26-a-level-for-every-command.md` (all accepted),
which state what stands, what changed and what was not built; where they differ on the defaults or the offered levels, this spec
follows the later record.

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
- Changing what an approval means. Only the owner's act makes a decision `Accepted`, unless the owner loosens that through the
  `accept-decision` key.

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
  command in auto and default mode and a hook that exits 0 leaves an `ask` rule in force (2.1.311). They ran under the owner's former
  configuration and have not been re-run since the reset of 2026-10-29; the note before the trials in `harness-modules.md` says
  what still holds.

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

A module can also declare a prompt that is not a key: a command's `asks` (an argument that is asked and not owner-run) and a
module's `ask_reads` (a read under the home directory) render as `ask` rules and are not levels, so the table does not carry them and
the approver cannot lower them from the personal settings (`trust-and-approval.md`, "Rendering rules"; built 2026-10-29 by plan
`2026-10-29-policy-and-module-asks`, increment B). `wb settings` prints no line for them.

A key is a process module's declared checkpoint name (`approve-plan`, `accept-decision` and the others), or the command in the `wb`
spelling: `wb install`, `wb adopt`, `wb add`, `wb upgrade`, `wb attach`, `wb rerender`, `wb approve`, `wb pin`, `wb recover`,
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
   attached again or re-rendered (`wb rerender`), and a `deny` already rendered into an attached clone stays until then. A value that is not one of the four levels reads as `block` for that key. A key that is not a valid name blocks
   the whole table, because a mistyped key must never leave a default of `ask` in force. `wb settings` reports each.
2. A key with no table entry reads as its checkpoint reading if the file sets one, and otherwise as its shipped default (below).
3. A level the key does not offer reads as `block` with a note.
4. A key on the compiled floor is refused, with a problem, and ignored. A valid key that no installed module or the installer
   declares is noted and ignored.

### Which levels a key offers

- `block`: every key.
- `delegated`: `approve-plan` only, whose gate is a converged, sealed review of the exact bytes (`delegation.py`). The gate must
  pass at the moment of the run, and the run counts only while the table still reads `delegated`.
- `ask`: `approve-plan`, and an owner-run argument of a module's command whose declaration names it in `levels` (below). `none`: `approve-plan`, `wb install`, `wb adopt` (built by Increment F), `wb upgrade` and `wb add` (built by Increment G), `wb approve` and `wb pin` (built by Increment H), `acknowledge-first-tier`, `acknowledge-second-tier`, `wb recover`, `wb attach` and `wb release-approvals` (built by Increment J), `accept-decision` (built by Increment K), every agent-safe action and
  every declared module argument that is not owner-run; the keys under "Not built" offer `block` only, and so does `wb rerender`. A key offers a level only
  from the version that builds it for that command.

**The levels an owner-run argument of a module's command offers** (decision `2026-10-27-owner-run-arguments-take-a-level`; the
declaration and the key are built by Increment C of the plan `2026-10-27-levels-for-the-review-workflow`, the launcher by its
Increment D). A command's declaration may give `levels`, an object that maps an `owner` argument to a non-empty list of different
levels from `ask` and `none`; the key `wb run <command> <argument>` then offers `block` and those levels, in the order `block`,
`ask`, `none`, and its default stays `block`. `delegated` is refused by `verify`, as are a key that is not an `owner` argument of
that command and an unknown level. A command that offers `ask` also gives `preview`, the name of a declared argument that is
neither owner-run nor `describe`; `verify` refuses `ask` without it and `preview` without `ask`. The preview argument is an
ordinary declared argument, so its key defaults to `none`. A command without these fields offers `block` only, as before, and
its declaration hashes as before. **The review engine declares it for its five owner-run arguments (`amend`, `archive`, `extend`, `prune`, `reset`, each `ask` and `none`, with `preview` as the preview argument; `review-engine.md`, "Owner-run commands"). No other first-party module does, so the owner-run arguments of `mempalace` and `remote-runner` offer `block` only.**
The terminal test and the level are read by the launcher, not by the helper. `wb run <command> <argument>`, with a command whose
argument offers a level (`ownerargs.py`, built by Increment D), runs an owner-run argument without a terminal only when the key
reads `ask` or `none` through `rendering.effective_level` (the record, the table, the permissions file and the command gate agree
and the key is listed) and the level is one the declaration offers; anything else reads `block` and the refusal is the one the
terminal test gives (`commands.owner_refusal`). At `ask` the last two arguments must be `--digest` and 32 lowercase hexadecimal
characters; the launcher checks their form and passes every argument to the helper unchanged, and does not compute or compare the
digest (the helper recomputes it inside the lock that guards its change, Increment E). The launcher writes the attempt line to the
level log after the pin and the bytes are checked and just before the helper starts (`launch.launch`'s `before`), key
`wb run <command> <argument>`, level and `digest:<hex>` at `ask`, and the outcome line after: `done` for exit 0, otherwise `refused`
with the exit code. If the attempt cannot be written the helper is not started; if the outcome cannot be written after the helper ran,
the exit code is 3 (a helper that itself exits 3 gives the same code; the line on standard error tells them apart). A run at a terminal reads no level and writes no entry. `wb launch` stays terminal-only for an owner-run argument at
every level, because the `ask` rule is rendered for the `wb run` spelling only.

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
reads `block` until the harness is attached again or re-rendered (`wb rerender`), as for any change to the table. The hook entry points `gate`, `agent-gate` and
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
before it, such as an alias or a script the agent wrote that wraps the call, is not seen; the auto-mode classifier was the barrier
for it, as for the other limits listed under "Limits", while auto mode was the owner's setting. The reset of 2026-10-29 ended that
setting, and no barrier for these cases is claimed here under factory defaults.

For these keys two more forms are not taken for the word (built by Increment I; decision `2026-10-27-command-gate-literal-arguments`).
A command that is exactly one literal `wb run <name> <arguments>`, matched in full on the raw text through `wb` or the store's `bin/wb`, with a
name of the form a pin or a command has that is not a launcher, a verb of `rules`, `python` or `python3`, and arguments that are plain tokens
(`[A-Za-z0-9._/:=@,+-]+`) or single-quoted strings (any character, a newline included), names the word only as data: `wb run` runs a
declared, pinned module command and never an owner-run verb. So `wb run safe-git commit --subject 'Add tests' -- tests/test_add.py`
passes with `wb add` relaxed, whatever words the subject and paths hold. An operator, a substitution, a double-quoted or escaped
argument, a trailing newline or any other form is judged as before, and `approve-plan` is not exempted, nor is `wb run --provides
<capability> <name> ...` (a name does not start with `-`). The keys `wb run <command> <argument>` are exempted only in the narrower way
described after this paragraph. And a launcher followed by the exact
token of a command that continues the word (`wb approve-plan` for `wb approve`, taken from `rules`) is removed before the search, as
`preview <action>` is, so relaxing `wb approve` does not block `wb approve-plan`; the token alone stays, so `A=approve-plan; wb ${A%-plan}`
is still seen however far apart they are, and the in-order rule still reads the text as written. What stays blocked with such a key relaxed: any other command that holds a launcher and the word
(`wb check tests/test_install.py`, `git diff workbench/install.py`, whose `workbench` is a launcher), `git commit -m 'add new base'`
for `wb add` (the skeleton joins `new base`), and a command with `$ ? * [ {` and scattered letters. The reason the gate prints for a
key at `none` does not name an `ask` rule: it says the form cannot be told from a call and that a path with `~` or `$VAR`, a wrapper or a
compound command is read that way.

A key `wb run <command> <argument>` (today the review engine's five) reads the first argument as data (built by Increment B of the plan
`2026-10-28-gate-reads-module-arguments`; decision `2026-10-28-gate-reads-module-arguments`, which refines the one above). A command that
is exactly one literal `wb run <command> <first> ...`, in the form above, whose `<command>` equals the key's and whose `<first>` is a plain
token other than the key's `<argument>`, is not searched for the key's words. The launcher takes the module's action from the first
argument alone and tests the owner-run list on it, so such a call never runs `<argument>`. With `extend` at `ask` or `none`, an agent can
therefore run `wb run review-engine preview extend <document> <n>` (and the other four previews), `status`, and a `decide` whose reason says
`extend`. The rule is applied per key: with `extend` and `reset` both relaxed, `wb run review-engine reset <document>` is freed for the `extend` key but still read for the `reset` key. Still judged as before: the exact simple form of the relaxed command (at `ask` the harness prompts), a quoted or otherwise non-plain first
token (`'extend'`, `ext''end`, `$'\x65xtend'`, which bash would turn into the argument), a double-quoted or substituted argument, a
compound or multi-line command, `wb run --provides`, and a differently named command that holds the same words, so a renamed pin of the
helper is not freed. The rule assumes that a module command takes its action from its first argument alone; a command whose helper took it
from a later position would need its key left out. The prompt of an `ask` shows the command and the digest and not the preview, so the
agent runs and shows the preview first (`review-engine.md`).

### The log

Every run at a level other than `block` that goes on without a terminal appends two lines (except `attach` and `release-approvals` where no level can be read, a run that changes nothing, and an acceptance at a terminal; see their paragraphs above, and "Accepting a decision through a command" for the command of `accept-decision`, whose runs without a terminal are logged) to `level-log` in the guarded store, never rewriting one: the attempt, with
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
`wb preview adopt`, `wb preview upgrade`, `wb preview add`, `wb preview rerender`, `wb preview release-approvals`, `wb launch`, `wb check`, `wb plan-status`, `wb settings`), then `wb run
<command> <argument>` for each argument the installed modules declare (an owner-run argument first), with the defaults and the
table applied. An agent-safe key and a declared argument that is not owner-run default to `none`; every other key defaults to `block`.
The hook entry points, the dispatcher words and `delegate-approve-plan` are not keys. As built by Increments A and C of the plan, a
`block` set on an agent-safe key is rendered as a `deny` at the next attach ("Rendering"); the table a harness renders and digests holds
an agent-safe key only when it is not at its default, so an attached clone's record is unchanged. After the `level` lines it prints one `translated <key>:
<word> read as <level>` line for each checkpoint word it read as a level because the table does not name the key (Increment B).
Problems and notes print as `settings:` lines. Two declarations that
give one key are a refusal.

## A level for every command

Built by the plan `2026-10-27-a-level-for-every-command`, Increments A to K, and described here as built. It is the owner's direction
of 2026-10-26. Calls marked **(call)** were approved with the section on 2026-10-26. Where a paragraph says "built by Increment ...",
that increment of the plan built it; the keys it did not build are under "Not built".

**Intent.** The owner chooses their own risk appetite, command by command, and may loosen any protection that is theirs to loosen.
A state in which an owner has set every key to `none`, and so has no protections left on the commands, is an outcome of that
freedom and not a feature: there is no master switch, profile or command that sets it.

**Coverage.** Every command and subcommand that `cli.py` routes has a key, the agent-safe ones included (`verify`, `preview install`,
`preview adopt`, `preview upgrade`, `preview add`, `preview rerender`, `preview release-approvals`, `launch`, `check`, `plan-status`, `settings`), so the owner can tighten a command that is always allowed
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

**Levels offered.** Every key offers `block` and `none`, except `wb rerender`, which offers `block` only for good (see "Re-rendering an
attached clone"), and the owner-run arguments of module commands (`wb run <command>
<argument>` where the argument is owner-run), which offer `block` only unless the command's declaration gives `levels` (built by
Increment C of the plan `2026-10-27-levels-for-the-review-workflow`; "Which levels a key offers"; only the review engine declares it).
`delegated` stays `approve-plan` only, and `ask` is offered by a key once
that key has a preview digest of its own, built as `approve-plan`'s is (for an owner-run argument of a module's command, once its
declaration names a `preview` argument; `verify` checks the name, and the digest the argument prints is the module's to build). Every key built by the plan offers `none`; the keys that still offer `block` only are listed under "Not built". Only the review engine's five owner-run arguments have a digest of their own and so offer `ask` besides `approve-plan` (built by Increments E and F of the plan `2026-10-27-levels-for-the-review-workflow`). At `none` an owner-run command runs without a terminal
and without a harness `deny`; the command's own checks of its input and its log entry apply, and the terminal prompt does not.
`accept-decision` offers `block`, `ask` and `none` (built by the plan `2026-10-29-accept-decision-at-ask`; "Accepting a decision through a command"). Since 2026-10-29 the groundwork policy block in `AGENTS.md` says that accepting a
decision is a checkpoint that stops by default and that the level `wb settings` prints for it says whether the agent may accept; the
`draft-decision` skill says what each level allows.

**One table** (built by Increment B). The `levels` table is the only place a level is set. A version 1 file's `checkpoints` are read as a fallback for a
key the table does not mention, and a table entry wins in either direction, so loosening a key is one edit. The checkpoint words
`stop` and `delegate` are aliases, read from a version 1 file, for `block` and `delegated`; the `level` lines of `wb settings` print
only the four level names, and a `translated` line says what a checkpoint word was read as. This replaces the rule that a key's level is the stricter of its checkpoint reading and its
table entry **(call)**.

**One way to run at `none`** (built by Increment D; `approve-plan`, `install`, `adopt`, `upgrade`, `add`, `approve` and `pin` use it). Two modules hold what every owner-run
command shares. The kit's `wbkit/levels.py` is the part that needs nothing else of the workbench: `may_run(level, terminal)` is true
at a terminal and, without one, only for the level `none` (a missing, unreadable or unknown level is no level, so only a terminal
runs), and the log's attempt and outcome lines and their append (`begin`, `finish`, `finish_refused`), which `levellog.py` calls
so that the installer and a helper write one format. Adding it did not change a kit function, so `wbkit.API` stays 1. The
installer's `levelrun.py` adds what needs the rendering record: `route` goes on at a terminal without reading anything, and
otherwise reads the key's level as `approve-plan`'s is read (`rendering.effective_level`: the record, the hashes and the gate must
hold) and refuses with the caller's text unless `may_run` says the command may go on; `logged` and `done` write the attempt after
every check and just before the change and the outcome after it, and write nothing for a run that changes nothing. `approve-plan`
uses `level_now`, `logged` and `done`, and its behavior is unchanged.

**`install` and `adopt` at `none`** (built by Increment F). The keys `wb install` and `wb adopt` offer `block` and `none`. The level is read
for the project the command is run from (the directory the agent works in, not the target, which is a new or adoptable directory), as
`levelrun.route` reads it: at a terminal nothing is read and the command asks for the digest as before; without one, `none` holds only
while the rendering record, the live hashes and the gate hold, and any other state refuses with the terminal-only message (and, when the
level could not be read at all, the reason). At `none` the command prints the plan and its digest, runs the same reads and checks (the
target, each source, the approval of every module, a second build of the plan that must give the same digest) and asks nothing; it
writes the attempt (`wb install` or `wb adopt`, `none`, `digest:<the 64 hexadecimal characters>`) just before the first write and the
outcome after the last, `done` with `written` for exit 0 and `refused` with the exit code when it stopped after writing (exit 3,
including a failed attach). If the attempt cannot be written, nothing is written. An outcome that cannot be written after the writes
exits 3 and says so. The level is read once, before the sources are fetched and the plan is built twice, as `approve-plan` reads it; a level or harness edit made
during those steps is not seen until the next run. The target is never the project the level was read for (a directory that holds
`.workbench` is refused), so there is no second project to compare it with, but a new directory inside that project, or a repository
that contains it, is accepted: the level is the owner's setting for the project the agent works in. An interrupt after the writes
exits 3 and says so. The command takes the same arguments and no flag; a run at a terminal is not logged. The harness's `deny` for
the command is removed only for the `wb` spelling, so `python3 -m workbench install` stays denied.

**`upgrade` and `add` at `none`** (built by Increment G). The keys `wb upgrade` and `wb add` offer `block` and `none`, and the level is read
as for `install`. Unlike `install`, these commands act on the project the level was read for, so the plan's project (the seed of its
manifest) must be that project: if it is not, the command refuses and writes nothing. At `none` and with no terminal, the command prints
the plan and its digest, runs every check it runs at a terminal (the acknowledgement of changed files, the approval of every module, a
second build of the plan that must give the same digest) and asks nothing. An unacknowledged change is refused as before, with nothing
written, and the log has no entry; `wb acknowledge` stays owner-run. The attempt (`wb upgrade` or `wb add`, `none`, `digest:<64 hex>`) is
written just before the first write and the outcome after the last: `done` with `written` for exit 0, `refused` for any other exit
(`refused before writing`, or `stopped after writing (exit 3)`). A run that has nothing to change writes no entry. If the attempt cannot
be written, nothing is written; an outcome that cannot be written after the writes exits 3 and says so. The command takes the same
arguments and no flag, and the `deny` is removed only for the `wb` spelling, as for `install`. `levelrun.apply_logged` is the one place
that writes the attempt and the outcome for these four commands.

**`approve` and `pin` at `none`** (built by Increment H). The keys `wb approve` and `wb pin` offer `block` and `none`. **At `none` an agent can
make a package or a helper trusted**, which is what the accepted decision `2026-10-26-a-level-for-every-command` records as the owner's
choice: an approval is what lets the installer verify and gate a package, and a pin is what lets `launch` run a helper. The level is read
by the command line for the project the working directory is in (`levelrun.route`); at a terminal nothing is read and the typed
confirmation applies as before. Without one, `none` holds only while the rendering holds, and any other state refuses with the
terminal-only message. At `none` the command prints what the owner would have been shown (the request of `approve`, the path, size and
hash of the helper for `pin`), asks nothing, runs the same checks (the package verifies, or the helper is read inside the project root; a
second read must give the same hashes) and writes the attempt (`wb approve` or `wb pin`, `none`, `digest:<the full tree hash of the
package or module, or the sha256 of the helper>`) just before the first record and the outcome after the last. `approve` is machine-wide
and compares no project; `pin` acts on the project named by its `<project-id>` and its `--root`, which must be the project the level was read for (the
same id and the same directory), or it refuses and writes nothing. An approval already on file changes nothing and writes no entry. The first-party approvals the installer
ships are not touched: only the package and module records of the approved content, the pin file and the level log are written. If
the attempt cannot be written nothing is recorded; an outcome that cannot be written after the records exits 3. `approve --source` fetches
into the cache before the attempt is written, as an `install` does. An approval that stops part way (a store error) exits 1 and says which
records it wrote, and its logged outcome reads `refused before writing`, which is then not exact; the stderr report is.
Limits, accepted for now: the connection and the cache write of `approve --source` happen before the attempt is logged, as for `install`, so
a fetch that fails or is already approved leaves no entry; `approve` is machine-wide, but the level is read for the project the working
directory is in, so an agent in any project where the owner set `wb approve` to `none` can approve for every project; and the level is
read once, before the fetch and the second verification, so a harness edit made in between is seen at the next run. `pin` reads its
`--root` as spelled and refuses one that names the project only through a link or `..`.

**`acknowledge`, `recover`, `attach` and `release-approvals` at `none`** (built by Increment J). The keys `acknowledge-first-tier`,
`acknowledge-second-tier`, `wb recover`, `wb attach` and `wb release-approvals` offer `block` and `none` (`ask` for `wb release-approvals` is
specified under "`wb release-approvals` at `ask`" and not built); the shipped defaults stay
`block`. The command line reads the level for the project the working directory is in (`levelrun.route`), as for the commands above.
*`acknowledge`* is governed by the checkpoint `acknowledge-first-tier` (the owner's choice): every path the command can list has a
baseline, so it is the manifest, a file under `.workbench/`, `AGENTS.md` or a seeded file, which are first-tier material, and the
real direction documents (roadmaps, specs, plans, decisions) are not baselined. The checkpoint stands for the command, so at `none`
the `wb acknowledge` `deny` is not rendered (the interpreter spellings stay denied) and the command gate guards the word
`acknowledge` in command position. **At `none` an agent can accept changes someone else made to the files that instruct and run
it, and move the pin of a helper whose file was edited, so that the launcher runs the new bytes (the same trust as `wb pin` at `none`).** `acknowledge-second-tier` offers `none` as the plan lists it, but `wb acknowledge` never lists a second-tier file, so it governs
no installer command today; it matters only to the agent's own checkpoint behavior. At `none` the command prints the same list and
digest, asks nothing, examines the project again (the digest must be the same) and writes the attempt (`acknowledge-first-tier`,
`none`, `digest:<64 hex>`) just before the baselines and the outcome after; the project listed must be the one the level was read
for, and nothing in the project is written. A run with nothing to acknowledge writes no entry. *`recover`* at `none` prints the same
examination and digest, asks nothing, examines again, and writes the attempt (`wb recover`, `none`, `digest:<64 hex>`) just before the
first removal and the outcome after; the same states are cleared and the same ones refused. The marker's record is unauthenticated
text and the marker of a failed `install` or `adopt` names no project and is in a new directory, so such a target is not compared with
the project the level was read for (the level is the owner's setting for the project the agent works in, as for `install`); a marker
that names a project (an unfinished `upgrade` or `add`) must name that one, which stops a mistake and not a forged marker. `attach`
acts on its target as `install` does and compares nothing; its log entry records the level of the project the command was run from. *`attach` and `release-approvals`* have no
terminal test and no digest, so at `none` the only change is that the `deny` is not rendered. A run without a terminal at a verified
`none` is logged (the attempt before the command is run, the outcome after: `done` with `written` for exit 0 and `refused` with
the exit code otherwise, a refusal included, because the command makes its own checks); a run at a terminal, at another level, or
where no level can be read (a directory that is no project) goes on exactly as before and writes no entry, so an agent that
runs from a directory where the level cannot be read (a directory with no project, a decoy `.git` with an unreadable manifest, a deleted
working directory) is not logged: the log is a record and not a control, and the owner who wants these runs refused where no level
is readable asks for that as a separate change; at a verified `none`
an attempt that cannot be written refuses the run and nothing is done, which these two commands did not do before. The attempt is
written after the launcher wrapper under `bin/` is refreshed, which every command does first, at a terminal or not. A refusal for a
level that could not be read carries the reason after the terminal-only text. `release-approvals`
writes the approvals shipped with the first-party packages, so at `none` an agent can make the first-party packages trusted.

**`accept-decision` at `none`** (built by Increment K; since 2026-10-30 it governs the command `groundwork accept`, see "Accepting a decision
through a command"). The checkpoint `accept-decision`, which the process module declares, offers `block`, `ask` and
`none` and defaults to `block`. The `draft-decision` skill tells the agent to run `wb settings` and to accept a record it drafted only
while the output holds the line `level accept-decision: ask` or `level accept-decision: none`, and then only by running `wb run groundwork
accept`, which writes the status line; on any other line, when the line is missing or when the command fails, it stops at `Proposed` and
asks the owner, and a file, a review or a reply is never that level. (Before the plan `2026-10-29-accept-decision-at-ask` the agent marked the record `Accepted` by editing it, at `none` only.) This repository's `AGENTS.md` says the same; the managed block that the groundwork module writes into other projects still says that only the
owner accepts a decision, which is stricter and wins there, so the skill's exception reaches a project only through its own `AGENTS.md`. **At `none` an agent can accept a decision,
and an accepted decision outranks the code** (`## Source of truth` in `AGENTS.md`); that is the owner's choice and it is not
logged. Nothing in the installer enforces the level, because accepting is an edit to a tracked file; the barrier is the guidance and
the owner's review of the commit.

**Out of scope.** The compiled hard-stop floor is unchanged and is not a key (see "Non-goals").

**Decision.** `2026-10-26-a-level-for-every-command` (accepted by the owner on 2026-10-26) refines
`2026-10-26-per-command-permission-levels` and `2026-10-26-permission-levels-as-built` on the offered levels, the shipped defaults
and the checkpoint rule, and the note that `accept-decision` offers `block` only. `2026-10-19-restrictive-only-permissions` is not
changed: a level of `none` renders no rule, so the neutral rule list still holds only `ask` and `deny`.

**Left to the builder.** The order of the increments, each key's digest content, the wording of the notes, and the layout of
`wb settings` output, which is grouped by command.

### Acceptance criteria of the plan

P1. Every command and subcommand `cli.py` routes has a key, except `gate`, `agent-gate` and `gate-command`, and the drift test fails
when any other has none.
P2. With no settings, every agent-safe command reads `none` and every other key reads as it does today, `block`.
P3. A table entry sets the level of its key in either direction, whatever the key's checkpoint says; a version 1 `stop` or
`delegate` for a key the table does not mention reads as `block` or `delegated`, with a note.
P4. Every key except `wb rerender` and the owner-run arguments of module commands accepts `block` and `none`, and a level a key
does not offer reads as `block` with a note.
P5. With every such key set to `none`, no command refuses for want of a terminal or a harness `deny`, the floor still applies, and
each run that changes something is logged.
P6. `accept-decision` set to `none` lets an agent accept a decision, and at `block` it does not.

As built: P1 is the drift test of `rules`/`levels` and the tests of the agent-safe keys (Increment A); P2 and P3 are the tests of the
registry, the settings and `wb settings` (Increments A and B); P4 is the offers tests of `test_levels`, `test_settings` and
`test_approve_levels`; P5 is `tests/test_install_levels.py`, `test_upgrade_levels.py`, `test_approve_pin_levels.py`,
`test_ack_recover_levels.py` and the command-gate tests, with the owner's trials in the plan's Result (Increments D to J); P6 is the
offers test for the key and the draft-decision skill test of the groundwork module (Increment K). P5 holds for every key that offers
`none`; it does not hold for the keys under "Not built" or for `wb rerender`, which offer `block` only. P6 is guidance, not enforcement: the test pins
what the skill says.

## Re-rendering an attached clone

Built by the plan `2026-10-27-rerender-attached-harness` (the design is [`harness-rerender.md`](harness-rerender.md)). A level in the
table is rendered into one file, the harness's permissions file, and into the rendering record, so a change to the table after attach
leaves `ask` and `none` reading `block` until both are rendered again. `wb rerender` does that for the harness the clone already
records; `wb check` names it (`rendering: out of date; the settings table differs from the rendered one (wb rerender)`, a warning
and not a problem, because the stale state is already safe).

- **The key `wb rerender`** is owner-run, defaults to `block` and offers `block` only. It is the second exception to decision 3 of
  `2026-10-26-a-level-for-every-command` (every key offers `block` and `none`), beside the owner-run arguments of module commands, and
  for a different reason, recorded in `2026-10-27-rerender-is-terminal-only` (accepted): at `none` the level would be read through the
  record, which reads `block` whenever the table or the permissions file differs, and those are the two ordinary reasons to run a
  re-render. A level written for it other than `block` reads as `block` with a note. It writes no level-log entry.
- **`wb preview rerender`** is the read-only plan and is its own agent-safe key, default `none`. So is **`wb preview release-approvals`**
  (the read-only preview of a release, built by Increment B of the plan `2026-10-30-release-approvals-at-ask`).
- **It runs only at a terminal**, on standard input and output, at every level; the owner types the first 12 characters of the
  preview's digest. Before the first write it rebuilds the plan and refuses unless the digest is the one confirmed.
- **The plan lists** each key whose rule moves, the files it changes (the permissions file, the local manifest, the rendering
  record, and the stale, new and missing rendered skills, agents and root file of
  [`harness-refresh.md`](harness-refresh.md)), every `allow` rule of the live file, which it keeps, and every other live entry the new file will not have,
  which it removes, each shown whole. It notes the shared settings file when the record watched another version of it: a re-render
  records that file as it is now and does not write it.
- **The write order** is the rendered files, the permissions file, the local manifest, then the record. The record is last, so a stop at any step leaves
  every relaxed key reading `block` and never looser. Exit 0 done or nothing to change, 1 refused or cancelled, 2 usage, 3 stopped
  after writing (the report lists what was and was not written), 130 interrupted before writing.
- **The local manifest is denied.** Every rendered permissions file denies the harness's write tool on
  `.workbench/local/harness.json` in the three spellings of the other protected files, with or without the edit gate hook, because the
  edited-file test of `wb rerender` trusts the hashes it records (plan `2026-10-28-protect-local-manifest`). The installer's own
  writes do not go through that tool. A clone gets the rule when its permissions file is next rendered, which `wb preview rerender`
  shows as a change of that file. The deny covers the harness's write tool and not a write by the shell.

## The planning workflow without a terminal

What an agent can do, and what stops it, when the owner has no terminal (a phone or the web). It covers drafting, reviewing and
approving a roadmap, spec, design, plan or decision. The "Key and level" column gives the shipped default, and says where the owner's
table (the personal settings as read on 2026-10-27, see the provenance below) differed: it differed for `approve-plan` only, which was
`ask`. Every owner-run key has the shipped default `block`. An `ask` prompt reaches the
owner's remote channel (see "Assumptions and constraints"), so a key at `ask` does not need a terminal; a command at `block` does, and
so does an edit of a file the owner makes themselves.

**Preconditions of every "no terminal" row that is not at its shipped default.** `ask`, `delegated` and `none` hold only after the
owner has set the level in the personal settings (version 2, `levels`) and the harness has been attached or re-rendered since
(`wb rerender`, which is terminal-only at every level). While the rendering is stale or missing, a relaxed key reads `block` and the
row falls back to the terminal command ("Rendering"). `wb check` says when the rendering is out of date.

*Provenance: the levels were read with `wb settings`, and the rows from this spec, `review-engine.md`, `trust-and-approval.md`,
`harness-modules.md`, `installer-interface.md` and the skills of this repository, at commit `3bd4185a121c` on 2026-10-27. Nothing
owner-run was run to build the table. A reading from the code or a spec is stated as such; an inference is marked.*

| Action | What does it | Key and level | Needs a terminal | What can block |
|---|---|---|---|---|
| Draft a roadmap, spec, decision or plan | the `draft-roadmap`, `draft-spec`, `draft-decision` and `draft-plan` skills. As rendered in this clone on 2026-10-27 they ran no command, except `wb run code-work check` for a plan, while the packaged `draft-decision` also ran `wb settings` (`none`); the clone has since been re-rendered and its `draft-decision` runs it too | no key for the edits; `wb run code-work check` and `wb settings` `none` | no | the edit gate (`wb gate`) refuses an edit while a plan under way is not approved (`harness-modules.md`, "The edit gate hook"); a decision is written `Proposed` and stops |
| Change a spec's or roadmap's direction | the checkpoint `change-direction` | `change-direction`, `block` only | no | an agent checkpoint, not a terminal gate: the agent stops and asks the owner in the conversation, and no installer command is behind it (`code-work.md`, "Checkpoints") |
| Brainstorm a design | the `brainstorm` skill: reads, asks, writes a spec | no key | no | nothing; the owner's approval of the design is their statement in the conversation |
| Read the plans | `wb run code-work plans`, `report`, `active`, `region`, `delegable`, `shared`; `wb plan-status` | `none` | no | nothing |
| Start a review | `wb run review-engine init`, `review-plan`, `review-spec`, `review-roadmap`, `review-adr` | `none` | no | the model bridge (`ask-codex`) must be installed, pinned and signed in on this machine, and `.workbench/review.json` must exist; the review spends one of the bound's rounds |
| Read a review | `wb run review-engine status`, `convergence` | `none` | no | nothing |
| Record what was done about a finding | `wb run review-engine decide` (once per finding) | `none` | no | a `blocker` or `major` finding with no decision refuses the next round |
| Ask a second reader | the `reviewer` agent (`request-review`) | no key; read-only | no | the reviewer-exchange cap (`wb settings`) |
| Raise the bound of a review | `wb run review-engine extend <document> <n>`; at `ask` also `--digest <32 hex>` after `wb run review-engine preview extend <document> <n>` | `wb run review-engine extend`, `block` (shipped) or `ask` or `none` | **yes at `block`**; no at `ask` or `none` | at the bound (3 rounds, ceiling 5) no further round runs until the owner extends it; at `ask` the owner's confirmation on the harness prompt, with the digest bound to the review as it is saved *(built by Increments E and F)* |
| Open a fresh window of rounds | `wb run review-engine reset <document>`, and at `ask` `--digest` after `preview reset` | `block` (shipped), `ask` or `none` | **yes at `block`**; no at `ask` or `none` | as `extend`; the plan recommends keeping it at `block`, because it discards the history of a window |
| Close a review | `wb run review-engine archive <document>`, and at `ask` `--digest` after `preview archive` | `block` (shipped), `ask` or `none` | **yes at `block`**; no at `ask` or `none` | a review stays open until the owner closes it; nothing else is stopped by it *(inference)* |
| Change a recorded decision | `wb run review-engine amend <document> <finding> …`, and at `ask` `--digest` after `preview amend` | `block` (shipped), `ask` or `none` | **yes at `block`**; no at `ask` or `none` | a wrong `decide` cannot be corrected by the agent unless the owner relaxes the level |
| Delete closed reviews | `wb run review-engine prune [--apply]`; at `ask` `prune --apply --digest` after `preview prune` | `block` (shipped), `ask` or `none` | **yes at `block`**; no at `ask` or `none` | nothing else is stopped by it; old reviews stay *(inference)*; the plan recommends keeping it at `block`; the plain list needs a digest too at `ask`, so an agent uses `preview prune` |
| Approve a plan, at a terminal | `wb approve-plan <plan>` | `approve-plan`, any level | **yes** | the owner types the first 12 characters of the region hash |
| Approve a plan, at `ask` | `wb approve-plan <plan> --digest <32 hex>` after `wb plan-status <plan> --digest` | `approve-plan`, `ask` (the owner's table on 2026-10-27) | no | the owner's confirmation on the harness prompt; the digest binds the plan, not what the owner read; a stale rendering makes the key read `block` |
| Approve a plan, at `delegated` | `wb delegate-approve-plan <plan>` | `approve-plan`, `delegated` | no | a converged, sealed review of the exact bytes (`trust-and-approval.md`), and the preconditions of the `delegate-approval` skill (a `peer-review` provider, a Risks section, no `Hard stop:` line); it counts only while the table reads `delegated`, so not while it reads `ask` *(the last clause is an inference from `trust-and-approval.md`)* |
| Approve a plan, at `none` | `wb approve-plan <plan>`, no terminal | `approve-plan`, `none` | no | nothing; the run is logged |
| Approve a roadmap, a spec or a design | none exists | no key | not applicable | a roadmap and a spec have no status gate (`AGENTS.md`); a design is approved by the owner's word in the conversation. Nothing records it |
| Accept a decision | the owner edits its `Status:` line and the index | `accept-decision`, `block`; offers `block`, `ask` and `none` | **yes, or an editor** *(inference)* | the rule that an agent may not accept one at `block` is guidance in `AGENTS.md` and the skill; the installer enforces nothing on an edit of the record, and the command `groundwork accept` ("Accepting a decision through a command") gives the checkpoint an `ask` level. The owner's other route is their own edit of the personal settings to `none` (a terminal or an editor), which lets the packaged `draft-decision` accept a record through that command; on 2026-10-27 the copy rendered in this clone said never to accept one and had no such route; the clone has since been re-rendered and its skill matches the package |

Three things this map shows:

- **Not blocked without a terminal:** drafting, starting and reading a review, and recording decisions, at their shipped levels; and
  approving a plan at `ask` (the owner's table as read on 2026-10-27, with the rendering then current), or at `delegated` or
  `none` once the owner sets and renders them.
- **Blocked without a terminal:** the five owner-run arguments of the review engine at their shipped level `block`, and accepting a
  decision. These five are the subject of the plan `2026-10-27-levels-for-the-review-workflow`, which built `ask` and `none` for
  them; the owner opts in per key in the personal settings and runs `wb rerender`. Accepting a decision has the command `groundwork accept` to give a level to ("Accepting a decision through a command").
- **Not blocked, once the owner sets a level:** any of the five at `ask` (with the preview digest) or `none`. Their read-only
  `preview <argument>` runs at either level too, and is not stopped by the command gate (see "The command gate").

Also, in the same flow:

- `evaluate-findings` runs no command; it applies a finding by editing the document and records it with `decide`.
- Editing an approved plan beyond its status line, review record and result voids its approval, and approving it again is a row above.
- `run-increment`, `security-review` and committing or pushing (`safe-git`, `push-shared-branch`) are not part of drafting,
  reviewing or approving, and are governed elsewhere.
- The "yes" in "Needs a terminal" for the review engine's owner-run arguments rests on `review-engine.md`, "Owner-run commands". In
  the code the test is made by the launcher (`commands.owner_refusal`), not the helper, as `review-engine.md` now says.

## Accepting a decision through a command

The decision `2026-10-29-accept-decision-offers-the-ask-level` (accepted on 2026-10-29) gives `accept-decision` the levels `block`, `ask`, `delegated` and
`none`. The plan `2026-10-29-accept-decision-at-ask` built `block`, `ask` and `none`, as this section says (Increments A to G, committed
on 2026-10-29 and 2026-10-30); a run through the real launcher and the harness prompt for the `ask` rule are the owner's checks, and
are recorded in that plan's Result. `delegated` for `accept-decision` is not built by that plan:
the accepted record leaves a delegated review's subject for a decision undecided, so `delegated` reads `block` here, as it does for
every key but `approve-plan`.

**The command.** The `groundwork` module ships one helper with two arguments, run with `wb run`. The installer names neither the
module nor the helper.

- `preview <record>` is agent-safe and read-only. It writes nothing and exits 0. `<record>` is a path relative to the project root that
  names a regular file under `docs/decisions/`, with no link followed.
- `accept <record>` is owner-run. It replaces the record's status line, and nothing else in the file, with `Status: Accepted by <approver>
  on <date>`, where `<approver>` is the owner's git identity, `Name <email>`, read as plan approvals read it
  (`trust-and-approval.md`, "The approver and how it was authorized") and `<date>` is today's date in the local zone.

**The key.** The declaration maps `accept` to the checkpoint `accept-decision` (`module-contract.md`, `commands[].checkpoint_of`). When
an installed process module declares that checkpoint, the key of `accept` is `accept-decision` and the key `wb run groundwork accept`
does not exist. When none does, `accept` keeps its own key `wb run groundwork accept`, which offers `block`, `ask` and `none` and
defaults to `block`, `wb settings` prints no `accept-decision` line, the `draft-decision` skill stops at `Proposed` as it does for any
level it does not find, and a level the owner wrote for `accept-decision` is noted as a key no module declares and ignored. The key
offers `block`, `ask` and `none`; `delegated` reads `block` with the note that it is not offered. The shipped default stays `block`.

| Form | Level | Result |
|---|---|---|
| `accept <record>`, standard input and output terminals | any | the owner's terminal command: the owner types the first 12 characters of the record's SHA-256; a `--digest` given at a terminal is checked the same way, and a run without one works as above |
| `accept <record> --digest <32 hex>` | `ask` | recorded when the digest equals the one the argument computes now |
| `accept <record>`, no terminal | `none` | recorded, with no digest |
| any other form without a terminal | `block`, `delegated` | refused: accepting a decision is owner-run |
| `accept <record> --digest …` | not `ask` here | refused: a digest needs the level `ask` and its rendered rule |

The last row is enforced by the launcher (plan `2026-10-29-accept-decision-at-ask`, Increment F), because the helper cannot tell its
level and would take a digest as the route `ask`: at `none` a run of a mapped argument whose last two arguments are `--digest` and
anything is refused before the helper starts, with nothing run and no entry written. Any other owner-run argument at `none` passes a
trailing digest on to its helper, as before.

**What `preview` prints.** Text, then a last line `digest: <32 lowercase hex>`: the project, the command and argument, the record's path,
its status line, the SHA-256 of its bytes, and what accepting does not cover (that the owner read the record; the index row). The digest
is the first 32 hexadecimal characters of the SHA-256 of that text, as for `plan-status --digest`, so a confirmation cannot be reused for
another project, another record or another content.

**What `accept` does, in order.** It takes the last two arguments `--digest <hex>` off at `ask` (the launcher checked their form,
`module-contract.md`), reads the identity first (so a missing or refused identity writes nothing), reads the record (bounded, no link
followed, regular file, one hard link), recomputes the digest, checks that the status is `Proposed`, replaces only the status line with
the kit's hash-checked replace (`Root.replace_file`, plan `2026-10-29-accept-decision-at-ask`, Increment D), reads the result back and
compares it with what it meant to write, and prints one result line. The replace compares the file's identity just before its rename and
the kit has no lock, so a write that lands in that short window is overwritten without notice, and the read-back cannot show it (the file
then holds the helper's bytes); the read-back confirms what the helper wrote, and the window is a known limit. The staged file is also
compared with its open descriptor just before the rename; a substitute swapped in after that comparison is installed, and the read-back,
which opens the result with the kit's no-follow reader and compares its bytes, shows it. The helper refuses and reports a result that
is not the bytes it meant to write. It refuses, with nothing written, a record whose bytes differ from the digest, a status that is not `Proposed`, a path that
is not under `docs/decisions/`, a link, a file over its bound, a status line that is missing or repeated, and a missing or refused
identity. A record that already reads `Accepted` is reported as such and not changed (exit 0) only after the digest check has passed, so a
changed record is refused whatever its status; at `none`, which has no digest, the check is on the status alone. Exit codes: 0 done or already accepted, 1
refused with nothing written, 2 usage.

**The log.** The launcher writes the attempt line before the helper starts and the outcome line after, for a run without a terminal, as
for every owner-run argument with a level ("The log"). For this key the helper prints, after its work, one JSON line of at most 512
bytes: `{"format": 1, "record": "<path>", "sha256": "<64 hex>", "approver": "<Name <email>>", "via": "ask" | "none"}`; the launcher checks
its form and that `via` is the level it ran at (it compares no digest: the helper recomputes it, and the attempt line holds the one the run was given), and writes the
route, the approver's email address and the record's hash into the outcome's reason, as `accepted by <email> via <route> sha256:<hex>`.
The email is printable ASCII of at most 100 characters (the grammar of `trust-and-approval.md`), so the reason stays within its 200
characters and the line within its 1,024 bytes; the name, which may be non-ASCII and up to 100 characters, is in the tracked status line
and not in the log. A missing, malformed, over-long or mismatching line, or an approver that does not pass the grammar, makes the
outcome `refused`, not `done`.
A run at a terminal reads no level and writes no entry, so a terminal acceptance is recorded by the tracked status line (the approver
and the date) and by git history only. The helper writes nothing to the guarded store. A run at a terminal prints no result line, with or without a
`--digest`. For a record that is already accepted the line names the approver of that run, and the entry reads like an acceptance
although nothing was changed (the helper's own text line says `already accepted`; the log keeps no such line).

**What stays outside the command.** The index row of `docs/decisions/README.md` is not written by the command; the `draft-decision` skill
tells the agent to update it afterwards, and the document check reports a row that disagrees with a status line. A hand edit of a status
line is possible and is not gated, and the document check does not treat it as unaccepted. An agent that edits a status line with its own
edit tool is held by the rule it follows and not by this gate, as it is for `accept-decision` today. At `none` the command runs and is
logged, while a hand edit of a status line is never gated and never logged; that is the difference between the two routes. At `ask` the
owner confirms a command and a digest, not that they read the record.

## `wb release-approvals` at `ask` (specified, not built)

The plan `2026-10-30-release-approvals-at-ask` builds this in its Increments B to D. The preview is built (Increment B); the digest
check, the offer of `ask` and the rendered rules are not built until Increments C and D are committed. Until then the key offers
`block` and `none` only, and `wb preview release-approvals` does not open the guarded store or write anything. The key `wb release-approvals` will offer `block`, `ask` and `none`, and defaults to
`block`. `delegated` is not built for it (the roadmap candidate `checkpoint-levels-beyond-block` stays open).

**How the existing parts treat it** (read on 2026-10-30, Increment A). The rendering is generic over the keys of the form
`wb <word>` of `rules.OWNER_RUN`: a key at `ask` renders an `ask` rule on the launcher spellings of the command and leaves the
interpreter spellings denied, and a key at `block` renders a `deny`, so the key needs only the offer of the level
(`levels._OFFERS`). The command gate reads the same keys generically: the exact simple command `wb release-approvals [<token> ...]`,
through `wb` or the guarded store's `bin/wb`, is what the `ask` rule matches, and `--digest <32 hex>` is such a token. The level of an
owner-run command with no terminal test is read by `levelrun.optional`, which returns a route only at a verified `none`; at `ask` and
at `block` it returns nothing and the command goes on as it always did, so the digest check below needs a reading that returns the
route at `ask` too, for this command alone and not for `attach`.

| Form | Level | Result |
|---|---|---|
| `wb release-approvals`, standard input and output terminals | not read | as today: it runs and needs no digest. A `--digest` at a terminal is refused: a digest is for a run without a terminal at `ask` |
| `wb release-approvals --digest <32 hex>`, no terminal | `ask` | writes the release, from the one release plan built now, when the digest equals that of the plan's preview |
| `wb release-approvals`, no terminal, no digest, a malformed digest or a wrong digest | `ask` | refused; nothing is written; the refusal names `wb preview release-approvals` |
| `wb release-approvals --digest …`, no terminal | `none` | refused before the run: a digest needs the level `ask`; nothing is written |
| `wb release-approvals`, no terminal | `none` | as today: it runs and is logged |
| `wb release-approvals` | `block` | the harness denies the agent; the command does not refuse itself, as today |
| any form without a terminal, in a directory where no level can be read | | as today: it runs and writes no entry (a `--digest` there is not checked) |

**The preview.** `wb preview release-approvals` is agent-safe and read-only. It builds the release plan and prints text: the number of
first-party packages and modules; for each package and module its declaration hash and tree hash in full (64 lowercase hexadecimal
characters each, so that the digest covers them whole and a change at any position changes it), and whether the record for those
hashes already exists in `workbench/shipped_approvals` or would be new; the approver and the time the records would carry; the shipped
records the release would leave stale, by their full keys; and a line that says what it does not cover. A last line `digest: <32 lowercase hex>` is the first 32 hexadecimal characters of the SHA-256 of that text, as
`wb plan-status --digest` computes it. A refused package refuses the preview with the reasons the release gives and no digest.

**What the command does at `ask`.** It builds the release plan once, takes the digest of that plan's preview text, compares it with the
one given and writes only on equality. It writes the records of that plan and does not read `packages/` again, because the kit has no
lock: a package changed after the plan was built is not released by the run, since the records name the hashes that were confirmed and
the changed tree no longer matches them. The attempt is written to the level log just before the write (`wb release-approvals`, `ask`,
`digest:<32 hex>`) and the outcome after (`done`, `written`).

**What it does not cover.** The digest binds the owner's confirmation to the hashes of the previewed release, the approver and the
time, not to the content of the packages: the owner who confirms trusts whatever the packages hold at those hashes, and reads the change
with `git diff` before confirming. The level is read for the project the working directory is in and counts only while the rendering
record is sound (`rendering.effective_level`); where it reads `block` because the record, the harness file or the command gate does not
agree, the command does not refuse itself and the harness's own rule is the barrier, as for the keys that already offer `none`.

## Not built

- `ask` for `wb release-approvals`, specified above and built by the plan `2026-10-30-release-approvals-at-ask`; until that plan's
  Increments B to D are committed the key offers `block` and `none` only.
- `delegated` for `accept-decision` and for the other seven keys that do not offer it (every key but `approve-plan`). The plan
  `2026-10-29-accept-decision-at-ask` built `ask` for `accept-decision` and left `delegated` reading `block`: the accepted record leaves
  undecided what a delegated review's subject is for a decision, and the roadmap candidate `checkpoint-levels-beyond-block` stays open.
- `ask` and `none` for the owner-run arguments of the other module commands (`wb run mempalace init`, `mine`, and
  `wb run remote-runner fetch-overwrite`). The declaration fields (`levels` and `preview`), the launcher that reads the level and logs the run,
  and the review engine's five (`extend`, `reset`, `archive`, `amend`, `prune`, each with a preview and a digest) are built by the plan
  `2026-10-27-levels-for-the-review-workflow`, Increments C to F. A module that wants them declares `levels` and a `preview` argument
  that prints a digest and checks it inside its own lock; until it does, its keys offer `block` only. Two limits of the review engine's
  keys are not built: the `prune` digest does not bind each review's rounds, decisions or generation (a pruned review is sealed and
  closed, so it cannot change between the preview and the apply), and the plain `prune` list cannot run at `ask` without a terminal (an
  agent uses `preview prune`).
- The keys `submit-remote-job` and `push-shared-branch`: each needs its own preview digest for `ask` and offers `block` only. The checkpoints `fetch-remote-output` and `change-direction` also offer `block` only: the plan
  built `none` for the installer commands and for `accept-decision`, and these two are agent checkpoints that no command of the
  installer runs, so a `none` for them has nothing to change. The accepted decision says no key should be limited to `block`; this
  list is the gap, and the owner decides whether a later plan closes it.
- The rule that a command reaching more than one key takes the strictest level of them: each command reaches one key today.
- `none` for `wb rerender`, if a way to authorize a stale rendering without a terminal is ever wanted: the key reads its level
  through the record that a re-render repairs (see "Re-rendering an attached clone"), and it needs its own decision.
- Picking up a module or package change in an attached clone: `upgrade` brings the installed files up to date and `wb rerender`
  then refreshes the rendered skills and agents (`harness-refresh.md`); the key it needs is the same `wb rerender`, `block` only.
- A provenance check inside `approve-plan`, managed settings, and a store whose approvals a shell cannot forge.

## Limits

These are accepted by the owner in writing (`2026-10-26-ask-level-spelling-limit`, `2026-10-26-ask-level-command-gate` and its
clarification note) and are tested where a test can show them (`tests/test_command_gate.py`).

- The gate reads text. A word whose letters are not in the text (base64, `rev`), a word built from variables whose parts lie farther
  apart than the window, a script file or program that makes the call (`python3 x.py` ran with no prompt in the owner's probe), a
  function or alias defined earlier, and a `*` standing for more than three letters are not seen.
- A command that merely names the word, such as a `grep` or a commit message, is blocked while a key is relaxed; the owner runs it.
  Two forms are exceptions: a literal `wb run` call for a single-word key, and a literal call of the key's own command whose first
  argument is a plain token other than the key's argument, for a `wb run <command> <argument>` key (see "The command gate"). A call of
  a differently named command that holds the words of such a key (`wb run safe-git commit --subject 'review-engine extend'`) stays
  blocked.
- A hook is not a boundary. The `ask` rule and the gate are best-effort matches; the auto-mode classifier remained the barrier for the
  rest (it denied the script and base64 cases in the owner's probe, which the gate did not control), while auto mode was the owner's
  setting. The reset of 2026-10-29 ended that setting, so for those cases no barrier is claimed here under factory defaults, and
  that was not tested.
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

The section "A level for every command" (then called "Planned: a level for every command") was reviewed on 2026-10-26 by the review engine (spec review `spec-5bcae25932e2d2fa`,
`ask-codex`, model `gpt-5.6-terra`, effort medium): one round of the bound of 3, one finding (a decision missing from the governing
list), applied. The owner approved that section on 2026-10-26 as the direction for a plan. The approval does not accept the
decisions it proposes to supersede, does not approve a plan and authorises no implementation. The author's calls marked **(call)**
were approved with it except where the owner says otherwise.

## Governing decisions and references

- Decisions: [2026-10-26-per-command-permission-levels](../decisions/2026-10-26-per-command-permission-levels.md),
  [2026-10-26-permission-levels-as-built](../decisions/2026-10-26-permission-levels-as-built.md),
  [2026-10-26-ask-level-spelling-limit](../decisions/2026-10-26-ask-level-spelling-limit.md),
  [2026-10-26-ask-level-command-gate](../decisions/2026-10-26-ask-level-command-gate.md),
  [2026-10-26-a-level-for-every-command](../decisions/2026-10-26-a-level-for-every-command.md),
  [2026-10-27-command-gate-command-position](../decisions/2026-10-27-command-gate-command-position.md),
  [2026-10-27-command-gate-literal-arguments](../decisions/2026-10-27-command-gate-literal-arguments.md),
  [2026-10-23-delegated-plan-approval](../decisions/2026-10-23-delegated-plan-approval.md),
  [2026-10-19-mandatory-review-personal-delegation](../decisions/2026-10-19-mandatory-review-personal-delegation.md),
  [2026-10-19-compiled-hard-stop-floor](../decisions/2026-10-19-compiled-hard-stop-floor.md),
  [2026-10-19-restrictive-only-permissions](../decisions/2026-10-19-restrictive-only-permissions.md),
  [2026-10-20-preview-then-owner-run-write](../decisions/2026-10-20-preview-then-owner-run-write.md),
  [2026-10-24-project-guarantees-a-floor](../decisions/2026-10-24-project-guarantees-a-floor.md).
- Specs: `trust-and-approval.md`, `code-work.md`, `installer-interface.md`, `harness-modules.md`.
- Plans: `docs/plans/2026-10-26-command-permission-levels.md`, `docs/plans/2026-10-27-a-level-for-every-command.md`.
  References: none.
