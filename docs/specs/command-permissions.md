# Command permissions

Status: Current

Written by plan `2026-10-26-command-permission-levels` (Increment H), which built it. It describes the levels table, the keys, the
log, the rendering record, the command gate and `approve-plan` at the levels `ask` and `none`. One key, `approve-plan`, is built
beyond `block`; every other key offers `block` only. Extending a review (`wb run review-engine extend`) was part of the design,
was not built, and is listed under "Not built". The design is `docs/decisions/2026-10-26-per-command-permission-levels.md`.

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
- Changing who accepts a decision or what an approval means. Only the owner's act makes a decision `Accepted`.

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

Strictness, from strictest to least strict: `block`, `ask`, `delegated`, `none`. A key's level is the stricter of its checkpoint
reading and its table entry.

### The table

The personal settings accept `version` 1 and 2. Version 2 may hold an object `levels`, from a key to a level; in a version 1 file
`levels` is an unknown entry and is ignored. A new file is seeded at version 1, so the owner changes `version` to 2 by hand to
use `levels`. A version 1 file reads its `checkpoints` as `stop` = `block` and `delegate` = `delegated`. When a key is in both,
the stricter applies and `wb settings` notes a difference.

A key is a process module's declared checkpoint name (`approve-plan`, `accept-decision` and the others), or the command in the `wb`
spelling: `wb install`, `wb adopt`, `wb add`, `wb upgrade`, `wb attach`, `wb approve`, `wb pin`, `wb recover`,
`wb release-approvals`, and `wb run <command> <argument>` for each owner-run argument that an installed module declares. The key
`approve-plan` is the checkpoint and the command; `wb acknowledge` is not a key, because the checkpoints
`acknowledge-first-tier` and `acknowledge-second-tier` set it. The registry (`workbench/levels.py`) is built from what the
installer knows, and no module is named there; two declarations that give one key are refused. A key is a lowercase name or words
separated by single spaces, at most 96 characters.

### Reading rules

1. A missing file is seeded as today. A damaged file, an unsupported version, a duplicated key or a `levels` that is not an object
   reads as `block` for the whole table. A value that is not one of the four levels reads as `block` for that key. A key that is
   not a valid name blocks the whole table, because a mistyped key must never leave a default of `ask` in force. `wb settings`
   reports each.
2. A key with no entry reads as its shipped default (below).
3. A level the key does not offer reads as `block` with a note.
4. A key on the compiled floor is refused, with a problem, and ignored. A valid key that no installed module or the installer
   declares is noted and ignored.

### Which levels a key offers

- `block`: every key.
- `delegated`: `approve-plan` only, whose gate is a converged, sealed review of the exact bytes (`delegation.py`). The gate must
  pass at the moment of the run, and the run counts only while the table still reads `delegated`.
- `ask` and `none`: `approve-plan` only. A key offers a level only from the version that builds it for that command; `accept-decision`
  and every other key offer `block` only.

### Shipped defaults

Every default is `block`. The mechanism for another default exists (`levels._DEFAULTS`), and the default of `approve-plan` was
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

### The log

Every run at a level other than `block` appends two lines to `level-log` in the guarded store, never rewriting one: the attempt, with
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
declared checkpoints, then the installer's owner-run commands, then `wb run <command> <argument>` for the installed modules'
owner-run arguments, with the defaults and the table applied. Problems and notes print as `settings:` lines. Two declarations that
give one key are a refusal.

## Not built

- `wb run review-engine extend` at `ask` and `none` (Increment G of the plan). The declaration schema (`declarations.py`) has no
  field for the levels an owner-run argument offers, and the installer may not name a module's command. A later plan needs: a field
  such as `levels` on a command, a decision for that change to the module contract, a helper that prints and checks a digest of the
  review's `status` and `n`, and the log attempt written before the helper is launched.
- The keys `reset`, `archive`, `prune`, `amend`, `acknowledge-second-tier`, `submit-remote-job` and `push-shared-branch`: each needs
  its own preview digest and offers `block` only. `accept-decision` offers `block` only because only the owner accepts a decision.
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

1. With no settings, or with a version 1 file, every key reads `block`, and the safety controls are unchanged: the floor, the
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

## Governing decisions and references

- Decisions: [2026-10-26-per-command-permission-levels](../decisions/2026-10-26-per-command-permission-levels.md),
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
