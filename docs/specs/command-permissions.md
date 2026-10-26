# Command permissions

Status: Draft

This spec states the design of `docs/decisions/2026-10-26-per-command-permission-levels.md`, which the owner accepted on
2026-10-26. It describes behavior that does not exist yet. Nothing in it is true of the code until the plan
`2026-10-26-command-permission-levels` is approved and complete. It becomes `Current` only then, and the existing specs
it touches (`trust-and-approval.md`, `code-work.md`, `installer-interface.md`,
`harness-modules.md`, `review-engine.md`) are edited at that time and not before.

## Scope

How the owner chooses, command by command, whether an action needs the owner at a terminal, an owner's confirmation
on a channel without a terminal, a delegate's passing a gate, or nothing. It covers the table of levels, its keys, the
levels a key offers, the shipped defaults, how a level takes effect for an action, the digest that binds a confirmation
to what was previewed, the log, and how a harness renders it.

## Non-goals

- Anything on the compiled hard-stop floor (`floor.py`) or added as a hard stop by a module. The table never names one.
- The actions governed by action review, `safe-git commit` and `remove`, and the push check. Their prompts are decided in
  `2026-10-25-module-commands-and-the-approver` and `docs/specs/action-review.md`.
- A command that builds a table for the owner. The owner edits the personal settings by hand, as for checkpoints today.
- Changing who accepts a decision or what an approval means. Only the owner's act makes a decision `Accepted`.

## Assumptions and constraints

- The owner's personal settings are a file in the guarded store that an agent cannot write
  (`workbench/settings.py`, `2026-10-19-guarded-store`). A project, a plan, a review, a module or an agent cannot supply
  an entry (`2026-10-19-mandatory-review-personal-delegation`).
- A harness renders permission rules into local files when the owner attaches it, and a `deny` or `ask` rule is
  checked before an `allow` (`harness-modules.md`). The neutral rules hold only `ask` and `deny`
  (`2026-10-19-restrictive-only-permissions`). So a table entry takes effect in a harness only after the next attach,
  and the rule that makes a prompt appear is a rendered rule and not a setting.
- **Unverified:** that an `ask` rule prompts in an interactive session and that the prompt can be answered from the
  owner's remote channel. `harness-modules.md` records only that an `ask` held in `-p` mode, where it is denied and not
  prompted. Increment A of the plan tests this, and an `ask` level means nothing until it is shown.
- The terminal test is a mistake guard and not authentication: a process can open its own pseudo-terminal
  (`2026-10-20-preview-then-owner-run-write`). What stops an agent from an owner-run command is the harness's deny rule.

## Behavior

### The levels

| Level | Who runs it | What makes it run |
|---|---|---|
| `block` | the owner, never the agent | the harness denies the agent; the command's own terminal test applies exactly where it applies today (`wb release-approvals` has none and keeps none) |
| `delegated` | the agent | a gate the command declares has passed |
| `ask` | the agent | the owner confirms a harness prompt, and the command carries the digest of its preview |
| `none` | the agent | nothing |

Strictness, from strictest to least strict: `block`, `ask`, `delegated`, `none`.

### The table

The personal settings gain an object `levels`, from a key to a level, and `version` becomes 2. A reader accepts
versions 1 and 2. Version 1 has no `levels`; its `checkpoints` read as `stop` = `block` and `delegate` = `delegated`.
When a key is in both `levels` and `checkpoints`, the stricter level applies and `wb settings` notes the difference.

A key is a checkpoint's setting name (`approve-plan`, `acknowledge-first-tier` and the others declared in
`code-work.md`, "Checkpoints"), or, for an owner-run action that has no checkpoint, the command in the `wb`
spelling (`wb install`, `wb run review-engine extend`). A key that no installed module or the installer declares is
refused with a note and ignored. A command that reaches more than one key takes the strictest level of them.

### Reading rules

1. A missing file is seeded as today. A damaged file, an unsupported version, a duplicated key, a key of the wrong
   type or a value that is not one of the four levels reads as `block` for the whole table, or for that key when the
   rest is sound, and is reported by `wb settings`.
2. A key with no entry reads as its shipped default (below).
3. A level the key does not offer (below) reads as `block` with a note.
4. A key on the compiled floor, or a hard stop a module adds, is not a key. An entry that names one is refused.

### Which levels a key offers

- `block`: every key.
- `delegated`: a key whose owner declares a gate, and only that. Today only `approve-plan` has one (a converged,
  sealed review of the exact bytes; `delegation.py`). The gate must pass at the moment of the run, and the run counts only
  while the table still reads `delegated`.
- `ask`: a key whose command has a read-only preview and takes its digest (below). Until a command's spec defines both,
  the key does not offer `ask`.
- `none`: every key that is not on the floor.
- `accept-decision` offers `block` and `ask` only: only the owner accepts a decision (`AGENTS.md`).

### Shipped defaults

A default is `block` or `ask`; `delegated` is never a default (`2026-10-19-mandatory-review-personal-delegation`).

| Default | Keys |
|---|---|
| `block` | `acknowledge-first-tier`, `wb install`, `wb adopt`, `wb add`, `wb upgrade`, `wb attach`, `wb approve`, `wb pin`, `wb recover`, `wb release-approvals`, `wb run mempalace init`, `wb run mempalace mine`, `wb run remote-runner fetch-overwrite`, `accept-decision` |
| `ask`, from the version that defines its preview digest; `block` until then | `approve-plan`, `wb run review-engine extend`, `wb run review-engine reset`, `wb run review-engine archive`, `wb run review-engine prune`, `wb run review-engine amend`, `acknowledge-second-tier`, `submit-remote-job`, `push-shared-branch` |

Every other checkpoint keeps `stop`, which reads as `block`. These defaults are the proposal's targets and are the owner's
to accept in the decision; the first slice of the plan builds `approve-plan` and `wb run review-engine extend` only.

### The preview and the digest (`ask`)

An action that offers `ask` has a read-only preview that an agent may run and that prints what the action would do.
The digest is the first 12 lowercase hexadecimal characters of the SHA-256 of the preview's canonical text. At `ask`
the command is accepted without the terminal test, and it:

1. requires the digest as an argument, recomputes the preview in its own process, and refuses on any difference, so a
   plan, a state or a target that changed after the owner answered is not approved;
2. refuses unless the rendering record (see "Rendering") shows the `ask` rule for it; otherwise it reads as `block`;
3. writes the log entry before it acts, and does nothing if the entry cannot be written.

At `none` the command is also accepted without the terminal test, but it needs no preview and takes no digest, so a key
that has no preview can still be set to `none`. It refuses, and reads as `block`, unless the rendering record (see
"Rendering") shows that attach rendered no rule for it, and it writes the log entry before it acts under the same
condition as step 3.

The agent shows the preview in the conversation before it asks. No code enforces that, and the prompt shows the command
and the digest and not the preview. An `ask` therefore proves that the owner saw the command and a digest. It does not
prove that they read the plan or the state.

For `approve-plan` the preview is the plan's path and hashed region, which the command already computes. For
`wb run review-engine extend` it is the review's `status` for the document: rounds used, the bound and ceiling, the
decisions, and the seal.

### Rendering

At attach, a harness that provides `permissions` renders, for each owner-run key, a `deny` at `block` and at
`delegated` (the delegated command is a different, agent-safe command, as `delegate-approve-plan` is today), an `ask`
at `ask`, and nothing at `none`. The floor's `ask` rules and the deny on the guarded store are unchanged and not affected
by the table. Only `ask` needs a rendered rule, the one that produces the prompt. `none` needs the absence of a `deny`, and `delegated`
and `block` need the `deny`.

**The rendering record.** At attach the installer writes, in the guarded store, a record the agent cannot write: the
harness's identity, whether it provides `permissions`, a digest of the effective table it rendered from, and, for each
key, the rule it rendered (`deny`, `ask` or none). A key's effective level is `block` unless all of these hold when the
command runs: the record exists and is readable; it names the attached harness and says it provides `permissions`; its
table digest equals the digest of the effective table now; and, for `ask`, it records an `ask` for the key and, for
`none`, it records no rule for the key. A missing, damaged or stale record, a table changed since attach, an unattached
harness or one without `permissions` therefore fails closed to `block`, and the owner repairs it by attaching again.
The record attests what attach rendered, not the current bytes of the harness's own file. `wb check` additionally
compares that file with what the record says and reports a difference, and an agent allowed edits to it remains the
limit stated in `harness-modules.md`. Changing the table takes effect in a harness at the next attach, which is the
owner's command.

### The log

Every run at a level other than `block` appends one line to `level-log` in the guarded store: the key, the level, the
gate or the digest, the time, and the outcome. The agent cannot write the store. The log is for the owner to read, is
not consulted to decide anything, and is not pruned by any command here.

### `wb settings`

It prints one `level <key>: <level>` line for every key it knows, with the default and the table already applied, and
keeps the existing `checkpoint <name>: stop|delegate` lines. Problems and notes print as `settings:` lines, as now.

## Acceptance criteria

1. With no settings, or with a version 1 file, every key reads at its shipped default, and the safety controls are
   unchanged: the floor, the harness `deny` rules, the guarded store and the terminal tests. Before the keys of
   increments F and G are built, every key reads as `block` and nothing that is owner-run today becomes runnable by an
   agent. After they are built, the only change is that `approve-plan` and `wb run review-engine extend` have an `ask`
   default, and an agent can run them only after the owner confirms a prompt, the digest matches and the harness has been
   re-attached so that the `ask` rule is rendered. Until it is, they read as `block`. The `checkpoint` lines of
   `wb settings` are unchanged.
2. A table with an unknown key, a level that is not offered, a floor key, a duplicate key or a value of the wrong type is
   reported, and the affected key reads as `block`.
3. `delegated` for a key with no declared gate is refused. `delegated` for `approve-plan` behaves as the existing
   decision requires.
4. At `ask`, `wb approve-plan <plan> --digest <12>` approves the plan when the digest matches the region it computes, and
   refuses, and writes no approval, on a mismatch, a changed plan, a missing rendered rule, a missing or unwritable log.
5. At `block`, the same command still refuses without a terminal. At no level can a table entry cause a floor action to run.
6. `wb run review-engine extend` follows the same rules with the review state's digest.
7. A rendered harness holds a `deny` for a key at `block`, an `ask` for a key at `ask`, and none for a key at `none`, and the
   rendering record says so. With no record, a damaged record, a table changed since attach, or a harness without
   `permissions`, every key reads as `block`; `wb check` reports a harness file that differs from the record.
8. Every run at `ask`, `delegated` or `none` leaves a log line; a run at `block` leaves none.
9. The trial of increment A shows an interactive `ask` can be answered through the owner's remote channel. If it cannot,
   this spec is revised and no key ships `ask`.

## Review record

Reviewed by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-26, at
the owner's request: three rounds, the bound of 3, not extended. Outcome: not converged. Round 1: the digest rules named
`none` (R1-F1), four review keys were bare names (R1-F2) and `block` assumed a terminal one command lacks (R1-F3).
Round 2: a migration criterion contradicted the `ask` defaults (R2-F1). Round 3: nothing authoritative told a command
that the harness was attached and rendered (R3-F1). All five were applied. The rendering record added for R3-F1 was
not reviewed again. This is a Draft: the owner has not accepted it as a description of built behavior.

## Governing decisions and references

- Decisions: [2026-10-26-per-command-permission-levels](../decisions/2026-10-26-per-command-permission-levels.md)
  (Accepted), [2026-10-23-delegated-plan-approval](../decisions/2026-10-23-delegated-plan-approval.md),
  [2026-10-19-mandatory-review-personal-delegation](../decisions/2026-10-19-mandatory-review-personal-delegation.md),
  [2026-10-19-compiled-hard-stop-floor](../decisions/2026-10-19-compiled-hard-stop-floor.md),
  [2026-10-19-restrictive-only-permissions](../decisions/2026-10-19-restrictive-only-permissions.md),
  [2026-10-20-preview-then-owner-run-write](../decisions/2026-10-20-preview-then-owner-run-write.md),
  [2026-10-24-project-guarantees-a-floor](../decisions/2026-10-24-project-guarantees-a-floor.md).
- Specs: `trust-and-approval.md`, `code-work.md`, `installer-interface.md`, `harness-modules.md`, `review-engine.md`.
- References: none.
