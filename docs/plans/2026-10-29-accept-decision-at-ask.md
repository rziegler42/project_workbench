# Accept a decision through a command, at the levels block, ask and none

Status: Proposed
Created: 2026-10-29
Candidate: none — the first part of workbench-v1#checkpoint-levels-beyond-block, which stays open: `delegated` for the eight keys and the other seven keys are not built here, and a completed plan that named the candidate would close it
Specs: command-permissions, trust-and-approval, groundwork, code-work, module-contract, module-boundary

## Goal

The owner directed that accepting a decision be configured like every other key
(`2026-10-29-accept-decision-offers-the-ask-level`, accepted). Today `accept-decision` offers `block` and `none` and is a rule the
agent follows; an `ask` entry reads as `block`. After this plan:

- the `groundwork` module ships a helper with two arguments: a read-only `preview` that prints what accepting a record would change and
  a digest of it, and an owner-run `accept` that replaces the record's status line;
- the key `accept-decision` offers `block`, `ask` and `none`, and the command is that key's command: at `block` the harness denies it to
  the agent, at `ask` the owner confirms the harness prompt for exactly the previewed digest, at `none` it runs without a terminal and is
  logged;
- the approver written into the status line is the owner's git identity, as for plan approvals;
- the `draft-decision` skill, the groundwork policy block and the seeded decisions README say what each level allows and name the command.

This plan does not close the roadmap candidate `checkpoint-levels-beyond-block`, and so does not name it as its candidate: the accepted
record gives `accept-decision` four levels, and `delegated` is not built here because the review's subject for a decision is undecided
(its "Not decided"). The candidate stays open until a later plan, after a decision on that subject, builds `delegated` and the other
seven keys. Until then `accept-decision` offers three of its four levels, and the specs say so.

## Scope

- Increment A: the specs only.
- Increment B: the identity reader, made available to a module's helper through the kit.
- Increment C: the declaration field that makes a module's owner-run argument the command of a checkpoint's key, and the installer code
  that reads it (registry, rendering, command gate, `wb settings`).
- Increment D: a hash-checked replace of one file in the kit, which the helper needs and the kit lacked (added after Increment E, first
  run, found it missing; the owner chose to build it in the kit).
- Increment E: the groundwork helper, its declaration and its tests.
- Increment F: the launcher refuses a digest at the level `none` for a mapped argument (added after the security review of
  Increment E found that the helper cannot refuse it, and the owner chose to fix it in the launcher).
- Increment G: the texts that say what each level allows, in the module and in this repository's installed copies.
- Increment H: the close-out record. The owner's own runs are listed there; they are not increments.

## Non-goals

- `delegated` for `accept-decision`, and for the other seven keys. The accepted record leaves "the `delegated` review's subject for a
  decision" undecided (its "Not decided"). A review's subject for each key is one design, made once for all eight keys in a later plan;
  until then `delegated` reads `block` here, as it does for every key but `approve-plan`. This is the owner's call to confirm at
  approval.
- The keys `submit-remote-job`, `push-shared-branch`, `release-approvals`, `acknowledge-first-tier` and `acknowledge-second-tier`
  (previews and digests), and the agent-only `fetch-remote-output` and `change-direction`.
- A change to the compiled hard-stop floor, to who may accept a decision, or to the document check beyond what Increment E names.
- Enforcing the level against an agent that edits a status line with its own edit tool. The accepted record states this limit; the rule
  the agent follows still governs it.
- Accepting a record that is not `Proposed`, and any change to an accepted record's text.

## Assumptions and constraints

- The accepted records are the authority: `2026-10-29-accept-decision-offers-the-ask-level` (what the command does),
  `2026-10-28-every-key-offers-the-approve-plan-levels` (what the levels mean), `2026-10-29-approvals-name-the-approver-by-git-identity`
  (the name written), `2026-10-27-owner-run-arguments-take-a-level` (the declared `levels` and `preview` this plan reuses).
- **The command is a module argument, not an installer command.** Decisions and the `draft-decision` skill belong to `groundwork`, and
  the installer names no module (`2026-10-21-module-code-lives-in-modules`). The existing mechanism already gives an owner-run argument
  `ask` and `none`, a preview argument, the digest form `--digest <32 hex>`, the level log and the terminal test (`ownerargs.py`,
  `launch.py`). What it does not give is a key named after a checkpoint, and that is Increment C.
- **The key.** A command may map an owner-run argument to a checkpoint name; the argument's key is then that checkpoint's key
  (`accept-decision`) and not `wb run groundwork accept`. The installer code names no module and no checkpoint. Two moments, two rules:
  - **At verification** a module's declaration is read alone, so the field is checked for form only: the argument is an owner-run
    argument of that command that offers a level, the checkpoint name has the form of one, and no two arguments claim one name. A
    checkpoint that no module declares cannot be refused there, because `groundwork` is supported without a process module.
  - **When the keys are built** (the registry) the mapping applies only if an installed process module declares the checkpoint.
    Otherwise the argument keeps its own key, `wb run groundwork accept`, offering `ask` and `none` and defaulting to `block`, and
    `wb settings` prints no `accept-decision` line, so the `draft-decision` skill stops at `Proposed` as it does for any level it does
    not find. A level the owner wrote for `accept-decision` is then noted as a key no module declares and ignored.
- **What `ask` binds.** The preview prints the project, the command and argument, the record's path relative to the project root, its
  status line and the SHA-256 of its bytes, and `digest: <32 hex>` over that canonical text, as `plan-status --digest` does. The `accept`
  argument recomputes the digest inside its own run, reads the record again (bounded, no link followed), and refuses unless the digest,
  the hash and the status `Proposed` all hold; it replaces only the status line, through the kit's hash-checked replace (`Root.replace_file`, built by Increment D), and
  verifies the result. The kit has no lock, so a window remains between the replace's last comparison and its rename; a write inside it is
  overwritten without notice, and the read-back cannot show it (it confirms only what the helper wrote).
- **The terminal form** is the owner's: the owner types the first 12 characters of the record's hash, as for a plan. It reads no level.
- **The log.** The accepted record says the acceptance is logged in the guarded store "with the approver, `via` and the digest, as the
  level log does for other keys". The level log records an attempt line (key, level, digest) before the helper starts and an outcome line
  after, for a run without a terminal only; a run at a terminal reads no level and writes no entry, for every owner-run key. This plan
  keeps both facts and adds one: on `accept` the helper prints, after its work, one bounded JSON line naming the record's path, the
  hash, the approver and the route (`ask` or `none`), and the launcher validates it (a mapped argument only) and writes it into the
  outcome line. A line that is missing, malformed or over its bound makes the outcome `refused`, not `done`. A terminal acceptance writes
  no log entry, and the tracked status line (approver and date) and git history are its record; Increment A states this and the owner
  confirms it at approval. The helper itself writes nothing to the guarded store.
- **The index row** of `docs/decisions/README.md` is not written by the command (the accepted record says it replaces the status line
  only). The skill tells the agent to update the row, and the document check already reports a row that disagrees with a status line.
- **The approver name.** A helper cannot import the installer, so the identity reader and grammar move into the kit
  (`workbench/wbkit/`), and `workbench/identity.py` becomes a thin caller of it. Behaviour and limits are unchanged.
- Editing any file under `packages/` makes the shipped approvals stale. The edit gate then refuses the next edit and the command gate
  refuses every shell command until the owner runs `wb release-approvals`. The edits of one increment are therefore made together, and
  an increment that changes more than one package file needs the owner's word for one scripted pass, as in `2026-10-29-approvals-name-the-approver`
  (Increments C and D) and `2026-10-29-policy-and-module-asks` (Increment C). Parser and format code that the live gates load
  (`declarations.py`, `levels.py`, `rendering.py`, `command_gate.py`) is changed in an order that never leaves a stored file unreadable.
- `tests/test_boundary.py` forbids the installer's tests from naming a harness or a module; `tests/test_module_test_imports.py` lets a
  module's tests import only `tests.support` and `tests.support_*`. The installer tests use synthetic modules and a synthetic checkpoint.
- A rule reaches an existing clone only after the owner's `wb rerender`, which is owner-run. The owner's personal settings already name
  `accept-decision` at `ask`, so that setting takes effect at the first re-render after this plan.

## Completion criteria

1. A command can map an owner-run argument to a checkpoint name; the mapping verifies, a mapping of an argument that is not an owner-run
   argument offering a level, a malformed name and a name claimed twice are refused, and a module that does not use it hashes as before.
   When an installed process module declares the checkpoint the key is the checkpoint's; when none does the argument keeps its own key,
   and a test shows the offers, the rendered rules and the gate's reading in both cases.
2. The key `accept-decision` offers `block`, `ask` and `none`; `wb settings` no longer says `ask` is not offered for it; `delegated` reads
   `block` with the note that it is not offered.
3. `groundwork` declares the helper, and a test over the real module shows: the preview prints a digest and writes nothing; `accept`
   replaces only the status line of a `Proposed` record, with the git identity and the date; it refuses a changed record, a wrong digest,
   a status that is not `Proposed`, a link, an oversized file and a missing identity; a `--digest` at the level `none` is refused before
   the helper starts; and a second run changes nothing. A non-terminal
   run writes an outcome line in the level log that names the approver, the route and the digest; a terminal run writes none.
4. The rendered rules, on the module's own Claude layout, deny the command at `block`, ask for it at `ask` for the exact spelling the
   launcher requires, and leave it at `none`.
5. The `draft-decision` skill, the policy block and the seeded decisions README say the same thing as the specs about each level, and no
   shipped text says that `ask` is not offered.
6. After the owner's releases, `wb verify packages/workbench`, `wb check` and `wb run code-work check` report no problems, the stale
   shipped records are removed with the owner's approval, and the whole `tests` root and every package test root pass.
7. After the owner's `wb upgrade` and `wb rerender`, the rendered permissions list the command as an `ask` rule. In a live session the
   owner sees the harness prompt for the command with the digest. These are the owner's runs.

## Increments

### Increment A — The specs

**Outcome:** the specs state the command, the key mapping, the levels, the preview, the digest, the refusals and the limits, so that
B to F are built against text.
**Dependencies:** none.
**Affected areas:** `docs/specs/command-permissions.md` ("Which levels a key offers", "The preview and the digest", a new section on
accepting a decision, "Not built"), `docs/specs/trust-and-approval.md` ("Checkpoint and cap settings", "Effective values"),
`docs/specs/groundwork.md`, `docs/specs/code-work.md`, `docs/specs/module-contract.md` (the new command field),
`docs/specs/module-boundary.md` (the identity reader in the kit).
**Steps:**
1. Write what the key offers (`block`, `ask`, `none`; `delegated` reads `block`), and strike `accept-decision` from every list that says
   it is a rule only or that `ask` reads as `block`.
2. Write the command: its two arguments, the forms at a terminal, at `ask` and at `none`, the exit codes (0 done or already accepted, 1
   refused with nothing written, 2 usage), and the table of refusals.
3. Write the digest's canonical text, what it binds and what it does not (it does not prove the owner read the record), the helper's
   result line, the outcome line that carries the approver, the route and the digest, and that a terminal acceptance writes no entry.
4. Write the new command field and its checks in the contract, and the kit's identity reader in the boundary.
5. Write the limits: the edit tool route, the index row, `delegated`, and the stated difference between `none` and a hand edit.
6. Run `wb check`, `wb run code-work check`, `doccheck` and `refcheck`.
**Verification:** the checks above report no problem; a search of `docs/` for `accept-decision` finds no sentence that contradicts the new
text; a read of each edited section against the two accepted records is recorded.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-accept-decision-at-ask#A`.

### Increment B — The identity reader in the kit

**Outcome:** a module's helper can read the owner's git identity with the same grammar and limits as the installer.
**Dependencies:** A.
**Affected areas:** a new module under `workbench/wbkit/`, `workbench/identity.py`, `tests/test_identity.py`, a kit test, the kit
sections of the specs. The kit is shipped to the modules that use it, so a package test of a shipped helper is not changed here.
**Steps:**
1. Read how the kit is copied into a module and what a helper may import, and record it. If a kit change would change the hash of a
   shipped helper that does not use it, stop and report.
2. Write the tests first: the existing identity tests are run against the kit's reader and against the installer's caller.
3. Move the reader, the grammar and `Identity` into the kit; `workbench/identity.py` keeps its public names and calls the kit.
4. Run the identity tests, `tests/test_wbkit*.py` and the whole `tests` root.
**Verification:** the identity tests pass unchanged against both names; the whole `tests` root passes; the plan approvals still print
`by Name <email>` (a test reads one).
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-accept-decision-at-ask#B`.

### Increment C — A checkpoint's command

**Outcome:** a command's owner-run argument can be the command of a declared checkpoint, and the key, the rules, the command gate and
`wb settings` follow.
**Dependencies:** A.
**Affected areas:** `workbench/declarations.py`, `workbench/levels.py`, `workbench/rendering.py`, `workbench/command_gate.py`,
`workbench/settings.py`, `workbench/harnessplan.py` if the rule list needs it, the launcher's outcome line (`workbench/launch.py`,
`workbench/ownerargs.py`, the level log), and their tests with a synthetic module and a synthetic checkpoint.
**Steps:**
1. Write the tests first: the field verifies; an unknown argument, an argument that is not owner-run or offers no level, a malformed
   checkpoint name and a checkpoint that two arguments claim are refused; with a synthetic process module that declares the checkpoint
   the key is the checkpoint's name, and without one the argument keeps its own key (offers `ask` and `none`, default `block`, no
   checkpoint line in `wb settings`, an owner entry for the checkpoint noted and ignored); the rendered `deny` at
   `block`, the `ask` rule at `ask` and the gate's reading are for the argument's spellings in every launcher spelling; `ask` and `none`
   are offered and `delegated` reads `block` with a note; a module without the field renders as before.
2. Add the field to the schema last in the order that keeps stored declarations readable, and bump nothing that a shipped declaration
   hashes over unless it uses the field.
3. Make the registry, `rendering.py` and `command_gate.py` read the mapping where they read `COMMAND_OF_CHECKPOINT`; keep that
   installer-command table for `acknowledge`.
4. Make `wb settings` stop saying `ask` is not offered for a key that offers it, and keep saying it for a key that does not.
5. Make the launcher read the helper's one result line for a mapped argument and write the approver, the route and the digest into the
   outcome line of the level log; a missing, malformed or over-long line, and a line whose route (`via`) is not the level the run had,
   makes the outcome `refused`. The line carries no digest and the launcher does not compare one: the helper recomputes it. Tests cover each case and the unchanged outcome line of every other key.
6. Run the whole `tests` root.
**Verification:** the new tests fail before and pass after; the whole `tests` root passes; `wb settings` output for this repository is
unchanged until Increment E.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-accept-decision-at-ask#C`.

### Increment D — A hash-checked replace in the kit

**Outcome:** a module's helper can replace one existing file of the project, if and only if it still has the bytes the helper read,
and the replace leaves no other change. The kit had no such function: `Root.read_if_present` reads without following a link and refuses
a file with more than one hard link, and `write_tree` replaces by an atomic rename, but nothing compares the file with what was read at
the moment of the rename; the installer's `replace_file` (`workbench/projectfs.py`) does, and a helper cannot import the installer.
Increment E, first run, stopped on this (the plan's "What `ask` binds" says it must).
**Dependencies:** none beyond A to C; it is built before E.
**Affected areas:** `workbench/wbkit/safefs.py` (one new method of `Root`), `tests/test_safefs.py`, the kit bullet of
`docs/specs/module-boundary.md`, and the sentence of `docs/specs/command-permissions.md` ("What `accept` does, in order") that names
"the hash-checked whole-file replace that `upgrade` uses". No file under `packages/` changes, so no release is needed.
**Steps:**
1. Write the tests first, over a real temporary tree: the replace succeeds and keeps the file's mode; it refuses a file whose bytes
   differ from the expected SHA-256, a link at any component, a file that is not regular, a file with more than one hard link, a file
   over the limit, a path outside the root, an absent file and a data argument that is not bytes; a file replaced or modified between
   the read and the rename (the existing `_fire` hooks of the kit's tests give the moment) is refused with nothing written; a failed
   replace leaves the original and no temporary file; a successful one returns the SHA-256 of what it wrote.
2. Add `Root.replace_file(rel, expected_sha256, data, limit=MAX_FILE_BYTES)`: descend with no-follow flags and keep the directory
   descriptors; read the target as `read_if_present` does; compare its SHA-256 with `expected_sha256`; stage the new bytes in an
   exclusively created sibling with the target's mode; fsync; compare the target's identity (device, inode, size, modification time) with
   the one taken before the read, immediately before a rename that names the held directory descriptor; remove the staged file on any
   failure. The window between that last comparison and the rename remains, because the kit has no lock: a write inside it is
   overwritten without notice, and a read-back cannot show it; the function's docstring and the spec say so.
3. Record the function in the kit bullet of the boundary spec (rule 5: the installer's `replace_file` and the `groundwork` helper both
   need it; the installer is not changed to call it here), and correct the sentence in `command-permissions.md` to name the kit's
   function and the window.
4. Run `tests/test_safefs.py`, `tests/test_boundary.py` and the whole `tests` root, then `wb check` and `wb run code-work check`.
**Verification:** the tests of step 1 fail before and pass after; the whole `tests` root passes; `wb check` and
`wb run code-work check` report no problems. Because the function writes to the filesystem on an untrusted path, the review of this
increment asks for the `reviewer` agent first; whether to run a security review is the owner's call at the checkpoint below.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-accept-decision-at-ask#D`.

**Checkpoint after D.** The function touches the filesystem and is the only write the helper makes. Ask the owner whether to run a
security review before E.

### Increment E — The groundwork helper

**Outcome:** the `groundwork` module ships `preview` and `accept` for a decision record, declared as the command of `accept-decision`.
**Dependencies:** B, C and D.
**Affected areas:** `packages/workbench/groundwork/helper/` (a new helper), `packages/workbench/groundwork/module.json`,
`packages/workbench/groundwork/tests/`, the shipped records.
**Steps:**
1. Write the tests first, over the real module with a fixed identity: the preview, `accept` at each form, and every refusal in the
   completion criteria; a record whose status is already `Accepted` is reported as such and not changed; the digest differs for another
   project, another record and another record content.
2. Write the helper from the kit: bounded read, no link, the status line found by the same rule the document check uses, one line
   replaced through `Root.replace_file` (Increment D), the result read back and compared.
3. Declare it: `ships`, a command with `preview` as a non-owner argument and `accept` as an owner-run argument that offers `ask` and
   `none` and maps to `accept-decision`.
4. Stop for the owner's word for one scripted pass if more than one package file changes, make the pass, and stop for the owner's
   `wb release-approvals` before anything is run or committed.
5. Run the module's tests, then the whole `tests` root and every package test root.
**Verification:** the tests of step 1 fail before and pass after; `wb verify packages/workbench` reports no refusal after the release;
`wb check` and `wb run code-work check` report no problems.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-accept-decision-at-ask#E`.

**Checkpoint after E.** The change touches authorization, the filesystem and a subprocess. Ask the owner whether to run a security
review before F.

### Increment F — Refuse a digest at the level none

**Outcome:** a run of a mapped owner-run argument at the level `none` that carries a trailing `--digest <32 hex>` is refused before the
helper starts, with nothing run and nothing written, as the forms table of `command-permissions.md` says ("a digest needs the level
`ask`"). Added after the security review of Increment E: the helper cannot tell its level, takes any matching digest as the route `ask`,
writes the record, and the launcher then logs the outcome `refused` because the route is not the level, so the audit log says the
opposite of what happened.
**Dependencies:** C and E.
**Affected areas:** `workbench/ownerargs.py` (`permit`), `tests/test_checkpoint_command_run.py`, and the forms table and "The log" of
`docs/specs/command-permissions.md`. No file under `packages/` changes, so no release is needed.
**Steps:**
1. Write the tests first, with the synthetic module and checkpoint: at `none` the digest form of a mapped argument is refused, the
   helper is not started, and no attempt or outcome line is written; without a digest the run is as before; at `ask` and `block` nothing
   changes; an owner-run argument that is not mapped still passes a trailing digest at `none` to its helper, as the review engine's
   arguments rely on.
2. In `permit`, for a mapped argument at a level that is not `ask`, refuse a trailing `--digest <32 hex>` with a reason that says a
   digest needs the level `ask`.
3. Correct the spec where it describes this refusal as built, and run the whole `tests` root.
**Verification:** the tests of step 1 fail before and pass after; the whole `tests` root passes; `wb check` and `wb run code-work check`
report no problems.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-accept-decision-at-ask#F`.

### Increment G — What each level allows

**Outcome:** every shipped text that says who accepts a decision says it by level and names the command.
**Dependencies:** E and F.
**Affected areas:** the `draft-decision` skill and the policy block of `groundwork`, `files/docs/decisions/README.md`, this
repository's `AGENTS.md` (written by the owner's `wb upgrade`, never by hand), the installed copies, the shipped records.
**Steps:**
1. Write the tests first: a test fails if a shipped text still says that `ask` is not offered, or if the skill and the policy block
   disagree about a level.
2. Edit the skill: at `block` stop at `Proposed`; at `ask` run `preview`, show it, and run `accept` with the digest for the owner to
   confirm; at `none` run `accept`; after any acceptance update the index row; `delegated` reads `block`.
3. Edit the policy block and the seeded README to match, with the same wording.
4. Stop for the owner's scripted-pass word and release as in E; then ask the owner to run `wb upgrade` and `wb rerender`, and read the
   results.
**Verification:** the tests of step 1; the module tests; the whole `tests` root; `wb check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-accept-decision-at-ask#G`, then a commit of the upgrade results.

### Increment H — The close-out

**Outcome:** the plan's Result records what was run, and the specs' "Not built" and the roadmap's remaining work are true.
**Dependencies:** G.
**Affected areas:** `docs/specs/command-permissions.md` ("Not built"), this plan's Result.
**Steps:**
1. Remove `ask` for `accept-decision` from "Not built", and record `delegated` for it and for the other seven keys as still not built,
   with the candidate still open and the decision on a delegated review's subject still owed.
2. Write the Result: each increment, the verification as run, what was not run, the review outcomes and the owner's runs from criterion 7.
3. Run `wb check`, `wb run code-work check`, `doccheck`, `refcheck` and the whole `tests` root.
**Verification:** the checks above report no problem; every completion criterion is marked met or not met with its evidence.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-accept-decision-at-ask#H`.

## Verification for the plan as a whole

The whole `tests` root and every package test root, `wb verify packages/workbench`, `wb check`, `wb run code-work check`, `doccheck`,
`refcheck` and `git diff --check`, after the owner's releases. Then, by the owner: `wb upgrade`, `wb rerender`, and a live session
that shows the harness prompt for the command at `ask`.

## Risks and sensitive actions

- **Authorization.** The command turns a document into an accepted decision, which outranks the code. A wrong digest check or a path
  that follows a link would accept or rewrite the wrong file. The helper recomputes everything itself, refuses links and checks the bytes
  it replaces. A security review is owed after D (the replace) and after E (the helper) and runs only when the owner asks.
- **The prompt proves little.** At `ask` the owner confirms a command and a digest, not that they read the record. The preview is shown
  in the conversation first, but nothing enforces that.
- **`none` and a hand edit.** At `none` the command runs without a terminal and is logged. A hand edit of a status line is never gated.
  The level is therefore a rule for the agent plus a mechanical gate on one route, not a boundary.
- **Kit change.** Moving the identity reader into the kit touches code the live gates load. Increment B checks the kit's copy rule first
  and keeps every stored file readable.
- **Shipped approvals go stale** at each package edit, and the command gate then refuses all shell commands until the owner releases.
  Each such edit stops for the owner. Nothing here works around a refusal.
- **Reach.** A new rule reaches a clone only after `wb rerender`. Until then the rule the agent follows is the only barrier.

## Review record

Reviewer: Codex through the review engine (`gpt-5.6-terra`), plan review `plan-36b235eec1ba4664`. Rounds: 3 of 3 (the bound). Each round
returned one major finding and no round returned none, so the review did not converge; the plan was not reviewed after the last fix.

- R1-F1 (applied): `delegated` is not built, yet the plan named the candidate. The plan now has `Candidate: none` with the reason, so
  completing it cannot close `checkpoint-levels-beyond-block`, and the Goal says `accept-decision` offers three of four levels until a
  later plan.
- R2-F1 (applied): a checkpoint mapping for a checkpoint no module declares. The plan now checks the field for form at verification and
  applies it when the keys are built only if an installed process module declares the checkpoint; otherwise the argument keeps its own
  key, and the criteria and tests say so.
- R3-F1 (applied): the accepted record's acceptance log needs the approver and the digest. The helper prints one bounded result line,
  the launcher validates it and writes approver, route and digest into the outcome line, and a terminal acceptance writes no entry.

Left for the owner: whether to extend the review for a fourth round on the last fix (`extend` is the owner's), the confirmation that a
terminal acceptance writes no log entry, and the confirmation that `delegated` waits for a decision on a review's subject.

## Deferred work

- `delegated` for `accept-decision` and the other seven keys: one design for the review's subject, and the matching change to
  `delegate` in `wb settings`.
- Previews and digests for `submit-remote-job`, `push-shared-branch`, `release-approvals`, `acknowledge-first-tier` and
  `acknowledge-second-tier`; commands or rules for `fetch-remote-output` and `change-direction`.
- Writing the index row from the command, if the owner wants the two kept in step mechanically.

## Result

### Increment A — specs written and reviewed (committed as `1d9f5fc`)

Changed (documents only): `docs/specs/command-permissions.md` (a new section "Accepting a decision through a command (specified, not
built)" holding the command, the key and its fallback, the forms table, the preview and digest, the order of `accept`, the refusals, the
log and the result line, and what stays outside; pointers in "A level for every command", in the table row for accepting a decision and
in "Not built"), `docs/specs/module-contract.md` (`commands[].checkpoint_of`), `docs/specs/module-boundary.md` (the identity reader in
the kit), `docs/specs/groundwork.md` and `docs/specs/code-work.md` (pointers that keep what is built separate from what is specified).
`docs/specs/trust-and-approval.md` needed no change: `delegate` stays `approve-plan` only, and the level log's text is in
`command-permissions.md`.

Choices the specs make that the plan left open, for review: the record must be a regular file under `docs/decisions/`; the date is the
local date; the result line is a JSON object of at most 512 bytes with the fields `format`, `record`, `sha256`, `approver` and `via`; the
field is named `checkpoint_of`; the kit's reader is `wbkit/identity.py`. Also found while reading: the kit is not copied into a module,
it is the workbench's own `wbkit` directory, so Increment B's first step is answered (no shipped helper's hash changes), and
`module-boundary.md` rule 5 for the kit is met by the installer and the groundwork helper.

Verification as run: `wb check` and `wb run code-work check` (73 plans) report no problems and `git diff --check` is clean, before and
after the review fixes. Nothing else was run; no code exists yet. A search of `docs/` for `accept-decision` found the sentences that say
"no command" or "governs no command" (lines of "The log", "Blocked without a terminal" and "`accept-decision` at `none`" in
`command-permissions.md`); each now says "today" or "as built" and points at the new section. The author read each edited section against
the two accepted records (`2026-10-29-accept-decision-offers-the-ask-level` and `2026-10-28-every-key-offers-the-approve-plan-levels`):
the command, the preview's digest, the status-line-only replace, the approver by git identity and the log are in the first; `delegated`
and the three agent-only keys are in the second and are left as that record says.

Review: the `reviewer` agent, one exchange, thirteen items, no blocking finding. Applied: the log paragraph and the "Blocked without a
terminal" bullet read "today" (items 1 and 2); the `none` paragraph says "as built" (3); how the approver is written in the log, since
the outcome reason is 200 ASCII characters and a name may be non-ASCII: the reason holds `accepted by <email> via <route> sha256:<hex>`
and the name stays in the status line (4); a terminal run with a `--digest` (5); the unexplained sentence about the other seven keys
removed (6); the difference between `none` and a hand edit (7); an already-accepted record is reported only after the digest check (8).
Not changed: item 10 (an existing inconsistency between lines 239 and 248 of `code-work.md`, outside this increment). Items 9, 11 and 12
found no problem. The reviewer could not run the checks or read the code; the claims about `plan-status --digest`, the `upgrade`
replace and the document check's status rule are the plan's own and are checked in D and E (the kit has no hash-checked replace; Increment D adds it). The choice in item 4 (the log names the email, not
the name) is the author's and is for the owner to confirm.

### Increment B — the identity reader in the kit (committed as `c725e22`)

Changed: `workbench/wbkit/identity.py` (new: the reader, the grammar and `Identity` moved unchanged; only its docstring header names the
kit), `workbench/identity.py` (re-exports `Identity`, `IdentityError`, `account_home`, `check`, `parse` and `read` from the kit),
`tests/test_wbkit_identity.py` (new: the former `tests/test_identity.py` with its import and docstring changed), `tests/test_identity.py`
(rewritten: the installer names are the kit objects, the grammar and the error are the same through both names, `approvals.identity` is
the installer module) and the kit bullet of `docs/specs/module-boundary.md` (no longer "specified, not built").

Step 1: the kit is not copied into a module; it is the workbench's own `wbkit` directory, found by file location (`module-boundary.md`,
"The kit"), so a new kit file changes no shipped helper's hash. Deviation from the plan's wording: the identity tests do not pass
unchanged against both names, because they patch `GIT_LOCATIONS`, `TIMEOUT`, `pwd` and `account_home` on the module object, which a
re-export cannot honour. The whole of them run against the kit module, and the installer module has the short test above. Every importer
uses only re-exported names (`read`, `parse`, `check`, `IdentityError`, `Identity`), and a test that patches `identity.read` still works.

Verification as run: `python3 -m unittest tests.test_wbkit_identity tests.test_identity` (49 tests, OK; the kit test failed with an
import error before the kit module existed); `python3 tests/run_all.py` (6081 tests in 13 roots, OK). The test that plan approvals print
`by Name <email>` is in `tests/test_planapprovals.py` and ran in the whole run.

Review: the `reviewer` agent, one exchange, no blocking finding. Applied: the stale "specified, not built" kit bullet (1); the deviation
recorded here (2); step 1 recorded here (3). Not changed: the spacing of `_SET_NAME =` (4), which the moved code had before. The reviewer
could not run anything.

### Increment C — a checkpoint's command (committed as `02098d4`)

Changed: `workbench/declarations.py` (`Command.checkpoint_of`, checked for form: an owner-run argument that offers a level, a name of
the checkpoint form, no name claimed twice), `workbench/levels.py` (`checkpoint_commands`; the registry gives a mapped argument the
checkpoint's key and no key of its own, only when the checkpoint is one the process module declares; the offers of a key that gains
`ask` are listed in level order), `workbench/rendering.py` (`Table`, a dict that carries `command_of`; `plan` and `table_of` use it;
`digest` also hashes the mapping when there is one), `workbench/command_gate.py`, `settingscmd.py`, `harnessstage.py`, `commands.py`
(`Request.checkpoint_of`), `levelrun.py` (`level_of_command`), `ownerargs.py` (the key of a mapped argument, and the result line),
`launch.py` (`launch_captured` takes `before`), `docs/specs/module-contract.md` (`checkpoint_of` is built), and the tests
`tests/test_checkpoint_command.py` and `tests/test_checkpoint_command_run.py`, which use a synthetic module and checkpoint only.

Deviations and choices, for the owner: (1) The plan's step 5 and the spec say the launcher checks that the digest the run was given is
the one the attempt line names. The result line has no digest field, and the attempt evidence and the run's arguments come from one
request, so that check could never fail; it is not built. On the owner's word the plan's step 5 and the spec's sentence in
`command-permissions.md` ("The log") were corrected to say so; that edit changes the plan's region, so the approval needs renewing. (2) The launcher checks the result line for every argument a declaration maps, also when no process
module declares the checkpoint and the argument keeps its own key; it then runs the helper captured, as the mapped path does. (3) A
mapped argument's helper runs with standard input closed, standard output read here (64 KiB) and a 300 s limit; an over-limit or
timed-out run is stopped and logged `refused`, although the helper may already have changed the record (a `refused` outcome can follow a
change). (4) A run that exits 0 without a valid last line is `refused` with exit 3. Increment E must print the line also for an
already-accepted record (the owner decided so on 2026-10-30) (exit 0), or the launcher must be taught that case; the spec does not yet say which. (5) The approver in the
log is the email only (as the spec says); the digest is on the attempt line, not the outcome line.

Verification as run: the new tests failed before the code (26 failures and 23 errors in the first file) and pass after;
`python3 tests/run_all.py` (6158 tests in 13 roots, OK, before the review fix below); `wb check` and `wb run code-work check` (73
plans) clean; `git diff --check` clean; `wb settings` for this repository unchanged (`accept-decision` still reads `block`).

Review: the `reviewer` agent, one exchange. Finding 1 (blocking): the rendering record's table digest did not cover which argument a
checkpoint was rendered for, so an upgrade that remapped the argument would leave a valid-looking record. Applied: `digest` hashes the
mapping when there is one (a table with none hashes as before), with tests. Findings 2 to 5: recorded above as (4), (1), (2) and (3).
Applied: the over-limit and timeout tests (5), the `levels.py` docstring (9). Findings 6 to 8 found no bypass, wrong level or change
for a module that does not use the field. The reviewer could not run anything. Not checked by anyone: whether `wb upgrade` or
`wb rerender` already invalidates a record when a module's declaration changes; the digest fix makes that moot for this field.

### Increment E — stopped before any change (the plan was amended to add Increment D)

Started on the owner's word (with the scripted pass, and `wb release-approvals` run beforehand). Reading the kit for the replace that
step 2 and "What `ask` binds" rely on found that the kit has none: `replace_file` is in `workbench/projectfs.py`, which a helper cannot
import, and the kit's `write_tree` takes no expected hash. Nothing under `packages/` or `tests/` was changed. The plan says to stop and
report; the owner chose to build the function in the kit, as its own increment, and the plan was amended accordingly (this Increment D
and the later labels shifted by one). A first report said a hard-linked record would go unchecked; that was wrong, since
`Root.read_if_present` refuses a file with more than one hard link. What is missing is the comparison at the moment of the rename.
The shipped approvals released before this stop are unaffected, since no package file changed.

### Increment D — a hash-checked replace in the kit (committed as `246ace4`; the security-review fix below is a second commit)

Changed: `workbench/wbkit/safefs.py` (`Root.replace_file`; a `read` test seam in `_read_present`, the same stage `read_file` has, a
no-op outside tests; `import hashlib`; a docstring bullet), `tests/test_safefs.py` (`ReplaceFileTest`, 25 tests), the kit bullet of
`docs/specs/module-boundary.md` and the sentence in `docs/specs/command-permissions.md` ("What `accept` does, in order"). No file under
`packages/` changed.

Deviations, for the owner: (1) The review found that the first wording ("the read-back is what notices it") was false: a write that
lands between the last identity comparison and the rename is overwritten, the file then holds exactly the bytes the helper wrote, and a
read-back passes. The docstring, both specs and two sentences of this plan (step 2 and "What `ask` binds") now say the window is silent
and a read-back cannot show it. Editing those sentences changes the plan's region, so the approval needs renewing. (2) The identity
compared before the rename is the one taken before the read, not the one the read itself saw; a change between the two is refused
(the safe side), and the docs say "taken before the read". (3) A read-only file is refused (`os.access`, real uid), a policy beyond "the
bytes match" that the docstring and spec state.

Verification as run: the new tests failed first with `AttributeError` (no `replace_file`) and one failed until the `read` seam existed;
`python3 -m unittest tests.test_safefs tests.test_boundary` (93 tests, OK); `python3 tests/run_all.py` (6187 tests in 13 roots, OK,
run on the final files); `wb check` and `wb run code-work check` (73 plans) clean; `git diff --check` clean.

Review: the `reviewer` agent, one exchange. Finding 1 (blocking, wording): applied, deviation (1). Finding 2 (identity wording): applied,
deviation (2). Finding 3 (`os.access`): kept, documented, deviation (3). Finding 4 (test gaps): applied, tests for a hard link added
before the rename, a failing rename and a failing write of the staged file; the gap between the first stat and the read has no seam and
is covered by the final identity comparison. Finding 5 (a flaky swap test): applied, the replacement file now differs in size. The
reviewer could not run anything. Whether to run a security review is the owner's call at the checkpoint after D.

Security review (asked for by the owner after the commit): the `security-reviewer` agent, one exchange, on a copy in its scratch
directory. No blocking finding. It tried link, directory, FIFO, hard-link and same-size-rewrite swaps at the `read` and
`before_replace` stages, mode bits, failing write, fsync, fchmod and rename, a pre-planted staged name and a shrinking file; each was
refused with the old bytes kept and no staged file left. Medium, applied: the staged sibling's name is visible in the directory from its
creation, and the descriptor was closed before the rename, so a same-user process with write access to the directory could substitute
the staged file (a link, or other bytes) and the call returned success. The function now keeps the descriptor open and compares the
staged name with it (regular file, same device and inode, one link, the size written) immediately before the rename; three tests cover
a link, other bytes and a removed staged file (they failed first). A substitute swapped in after that comparison is still installed; unlike
a write to the record, a read-back through the no-follow reader shows it, and Increment E's helper must make that read-back. The spec
statements and the docstrings say so. Low, not changed: `replace_file` fires only the `read` and `before_replace` stages (not
`validated`), no test relies on `validated` for it; a failed rename followed by a failed unlink can leave the staged file (best effort,
as for a killed process); a shared writable mapping might change bytes without a visible timestamp change, which the module's timestamp
limit covers; a directory renamed after its descriptor was held still receives the write through the descriptor, with no link followed.
The reviewer could not run `git status` or read the test body.

### Increment E — the groundwork helper (not yet committed)

Changed: `packages/workbench/groundwork/helper/groundwork` (new: `preview <record>` and `accept <record> [--digest <hex>]`),
`packages/workbench/groundwork/module.json` (ships the helper; the command `groundwork` with `preview`, and `accept` owner-run,
offering `ask` and `none`, mapped to `accept-decision`), `packages/workbench/groundwork/tests/test_decision_accept_helper.py` (new, 48
tests), `packages/workbench/groundwork/tests/test_groundwork_module.py` (four expectations: the helper is shipped, `commands` is
declared), `tests/support_helpers.py` (the kit's `identity` is registered for helper tests) and the sentence in
`docs/specs/command-permissions.md` about a terminal run and an already-accepted record. The new files were written into `packages/`
by the owner-approved scripted passes (three: the build, the review fixes, the security-review fix), each followed by the owner's
`wb release-approvals`.

Choices and deviations, for the owner: (1) The record must be a `.md` file directly under `docs/decisions/` (not nested), stricter than
"under". (2) The result line's `sha256` is the hash of the record as the digest bound it (the bytes before the status line changed), not
of the bytes after; the spec says "the record's hash". (3) For an already-accepted record the line names the approver of that run and
the launcher logs it like an acceptance although nothing changed (the owner decided the line is printed; the spec now says so). (4) A
`--digest` given at a terminal is checked and needs no typing, and a terminal run prints no result line; the spec's "checked the same
way" read this way (the reviewer called the wording ambiguous). (5) The status line is found by a copy of the document check's rule
(the helper cannot import `doccheck`); a test compares the two on 24 documents, by the count of status lines. (6) A name that
JSON-escapes past 512 bytes (about 70 non-ASCII characters) cannot accept, and is refused before anything is written. (7) A failure
after the replace (a read-back that differs or cannot be read) exits 1 with "the record was replaced ... look at <record>", not
"nothing written". (8) The kit has no lock, so a write to the record in `replace_file`'s last window is overwritten without notice
(Increment D); the helper's read-back confirms only what it wrote. (9) The shipped approvals went stale at each package edit and
the owner released three times; `wb release-approvals` now warns of six shipped records not part of this release: four untracked,
written by the intermediate releases, and two tracked (`63fe163a…`, `b0ad94d0…`); the two current ones are untracked (`a6a3758f…`,
`b9be9135…`). Removing the stale records, and committing the current ones under `workbench/shipped_approvals/packages/`, is for the
owner to approve and has not been done. (11) Security review finding 1, for the owner: at the level `none` a `--digest` is taken by the
helper as route `ask`, so the record is written and the launcher then logs the outcome `refused` (the route is not the level); the spec
row says such a run is refused with nothing written. Only the launcher can refuse it before the helper starts (`ownerargs.permit`); that
is outside this increment; the owner chose to fix it in the launcher, and the plan gained Increment F for it. (10) A hand-run test that loaded a helper
from `packages/` without `-B` left a `__pycache__` there, which made the workbench stop recognising the `claude` harness (every gate
refused) until the owner removed it; every hand-run of a test since uses `-B`, and `tests/run_all.py` already writes no bytecode.

Verification as run: the new tests failed first with the helper absent (`LookupError`), then passed (42, then 47 after the review
fixes, 48 after the security review); the two behaviour tests added by the review failed against the first packaged helper; eight hand-made mutants of the helper (no
digest check, no `Proposed` check, no code-fence rule, no expected hash, wrong route, no read-back, no typed-hash check, no digest check
for an accepted record) were each caught by 1 to 15 failing tests. The groundwork root passes (244 tests). `python3 -B -W error
tests/run_all.py`: 6232 tests in 13 roots OK before the review fixes, 6237 after them, then 6238 tests in 13 roots OK on the final files.
`wb verify packages/workbench` reports no refusal; `wb check` and `wb run code-work check` (73 plans) are clean; `git diff --check` is clean.
Not run: the helper through the real launcher at `ask` and `none` (the launcher's reading of the result line is tested with a synthetic
module in Increment C, and the real module's declaration is checked here), and a run at a real terminal.

Review: the `reviewer` agent, one exchange, no blocking finding. Applied: a terminal run prints no result line (1); the message after a
failed read-back (3); the tests (4): a closed handle in `tree()`, mixed line endings, a byte-order mark, a status line over 2000
characters, the 40-line header edge, more documents in the parity test, and a terminal run of an accepted record. Recorded, not
changed: (2) the already-accepted line, deviation (3); (5) the long-name limit, deviation (6). The reviewer could not run anything or read
`Root.replace_file`.

Security review (asked for by the owner at the checkpoint after E): the `security-reviewer` agent, one exchange, on a copy in its
scratch directory with the kit's identity replaced by a fixed one. No critical or high finding. It tried status lines of every form
(line endings, a byte-order mark, a status line on line 41, one in a fence or a quotation, Unicode line separators, 30,000 random
documents against `doccheck`: no disagreement on the count or the word), links, hard links, directories and FIFOs as records, hostile
manifests and names, the three routes, digest reuse, a file that grows or is swapped before the rename, the size bound and the
preview. Applied: the digest text cut the record's path to 200 characters, so two records with identical bytes and the same first 200
characters of their path shared a digest; the path is no longer cut (a test fails against the old helper). Recorded for the owner:
deviation (11) above. Noted, no change: text after `Proposed` on the status line is dropped but shown in the preview and bound by the
digest; a status line inside an HTML comment is accepted, as `doccheck` reads it; a stdout failure after the replace was not tested;
the end-to-end `wb run` through the real launcher, the real level log and a real terminal were not run.

### Increment F — refuse a digest at the level none (not yet committed)

Changed: `workbench/ownerargs.py` (`permit`: for a mapped argument at a level other than `ask`, a run whose second-to-last argument is
`--digest` is refused before the helper starts, whatever follows it, with a reason that says a digest needs the level `ask`; the
module docstring says so), `tests/test_checkpoint_command_run.py` (in `AtNone`: four digest forms, a digest with no record, a digest
that is not among the last two arguments, and a digest at a terminal; in `AtBlock`: a digest is refused as before; a new class
`AnArgumentThatIsNotMapped`: an unmapped owner-run argument still passes a trailing digest at `none` to its helper; the stub helper
now records its arguments) and the paragraph after the forms table in `docs/specs/command-permissions.md`. No file under `packages/`
changed, so no release.

Choices, for the owner: (1) The refusal reads the second-to-last argument alone (`--digest` followed by anything), wider than the
plan's "a trailing `--digest <32 hex>`", so a malformed or empty digest cannot reach the helper at `none` either. (2) The condition is
"a mapped argument at a level other than `ask`", not "at `none`"; `block` and `delegated` are refused earlier for another reason, so
today it applies to `none` alone. (3) A digest that is not among the last two arguments is not refused by the launcher; the real
helper takes a digest only as the last two of exactly four arguments and refuses any other count as a usage error. The launcher's
refusal therefore depends on the helper's strict argument count: a helper that later takes a digest elsewhere needs `permit` changed
with it. (4) The plan's "The log" of the spec needed no edit; the paragraph after the forms table carries the change.

Verification as run: the new `AtNone` test failed first (the helper started and the digest reached it); `python3 -B -m unittest
tests.test_checkpoint_command_run tests.test_checkpoint_command tests.test_approve_levels` (123 tests, OK) and, after the review's
test additions, `tests.test_checkpoint_command_run` (36 tests, OK); `python3 -B -W error tests/run_all.py`: 6241 tests in 13 roots OK
(run before the review's test-only additions; the whole suite was not run again after them); `wb check` and `wb run code-work check`
(73 plans) clean; `git diff --check` clean.

Review: the `reviewer` agent, one exchange, no blocking finding. Applied: the stub helper records its arguments, so the unmapped test
shows the digest was passed on (7); tests for a digest with no record, a digest not among the last two arguments and a digest at
`block` (7). Recorded: the dependence on the helper's argument count, choice (3) (1). Findings 2, 3, 4, 5, 6 and 8 found nothing to
change. The reviewer could not run anything.
