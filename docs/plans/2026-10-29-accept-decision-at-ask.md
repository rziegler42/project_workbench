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
- Increment D: the groundwork helper, its declaration and its tests.
- Increment E: the texts that say what each level allows, in the module and in this repository's installed copies.
- Increment F: the real-module checks and the close-out record. The owner's own runs are listed there; they are not increments.

## Non-goals

- `delegated` for `accept-decision`, and for the other seven keys. The accepted record leaves "the `delegated` review's subject for a
  decision" undecided (its "Not decided"). A review's subject for each key is one design, made once for all eight keys in a later plan;
  until then `delegated` reads `block` here, as it does for every key but `approve-plan`. This is the owner's call to confirm at
  approval.
- The keys `submit-remote-job`, `push-shared-branch`, `release-approvals`, `acknowledge-first-tier` and `acknowledge-second-tier`
  (previews and digests), and the agent-only `fetch-remote-output` and `change-direction`.
- A change to the compiled hard-stop floor, to who may accept a decision, or to the document check beyond what Increment D names.
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
  the hash and the status `Proposed` all hold; it replaces only the status line, through the kit's hash-checked whole-file replace, and
  verifies the result. If the kit has no such replace, Increment D stops and reports.
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
   a status that is not `Proposed`, a link, an oversized file and a missing identity; and a second run changes nothing. A non-terminal
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
B to E are built against text.
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
   outcome line of the level log; a missing, malformed, over-long or mismatching line (the digest it names is not the one the run was
   given) makes the outcome `refused`. Tests cover each case and the unchanged outcome line of every other key.
6. Run the whole `tests` root.
**Verification:** the new tests fail before and pass after; the whole `tests` root passes; `wb settings` output for this repository is
unchanged until Increment D.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-accept-decision-at-ask#C`.

### Increment D — The groundwork helper

**Outcome:** the `groundwork` module ships `preview` and `accept` for a decision record, declared as the command of `accept-decision`.
**Dependencies:** B and C.
**Affected areas:** `packages/workbench/groundwork/helper/` (a new helper), `packages/workbench/groundwork/module.json`,
`packages/workbench/groundwork/tests/`, the shipped records.
**Steps:**
1. Write the tests first, over the real module with a fixed identity: the preview, `accept` at each form, and every refusal in the
   completion criteria; a record whose status is already `Accepted` is reported as such and not changed; the digest differs for another
   project, another record and another record content.
2. Write the helper from the kit: bounded read, no link, the status line found by the same rule the document check uses, one line
   replaced, the result read back and compared.
3. Declare it: `ships`, a command with `preview` as a non-owner argument and `accept` as an owner-run argument that offers `ask` and
   `none` and maps to `accept-decision`.
4. Stop for the owner's word for one scripted pass if more than one package file changes, make the pass, and stop for the owner's
   `wb release-approvals` before anything is run or committed.
5. Run the module's tests, then the whole `tests` root and every package test root.
**Verification:** the tests of step 1 fail before and pass after; `wb verify packages/workbench` reports no refusal after the release;
`wb check` and `wb run code-work check` report no problems.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-accept-decision-at-ask#D`.

**Checkpoint after D.** The change touches authorization, the filesystem and a subprocess. Ask the owner whether to run a security
review before E.

### Increment E — What each level allows

**Outcome:** every shipped text that says who accepts a decision says it by level and names the command.
**Dependencies:** D.
**Affected areas:** the `draft-decision` skill and the policy block of `groundwork`, `files/docs/decisions/README.md`, this
repository's `AGENTS.md` (written by the owner's `wb upgrade`, never by hand), the installed copies, the shipped records.
**Steps:**
1. Write the tests first: a test fails if a shipped text still says that `ask` is not offered, or if the skill and the policy block
   disagree about a level.
2. Edit the skill: at `block` stop at `Proposed`; at `ask` run `preview`, show it, and run `accept` with the digest for the owner to
   confirm; at `none` run `accept`; after any acceptance update the index row; `delegated` reads `block`.
3. Edit the policy block and the seeded README to match, with the same wording.
4. Stop for the owner's scripted-pass word and release as in D; then ask the owner to run `wb upgrade` and `wb rerender`, and read the
   results.
**Verification:** the tests of step 1; the module tests; the whole `tests` root; `wb check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-accept-decision-at-ask#E`, then a commit of the upgrade results.

### Increment F — The close-out

**Outcome:** the plan's Result records what was run, and the specs' "Not built" and the roadmap's remaining work are true.
**Dependencies:** E.
**Affected areas:** `docs/specs/command-permissions.md` ("Not built"), this plan's Result.
**Steps:**
1. Remove `ask` for `accept-decision` from "Not built", and record `delegated` for it and for the other seven keys as still not built,
   with the candidate still open and the decision on a delegated review's subject still owed.
2. Write the Result: each increment, the verification as run, what was not run, the review outcomes and the owner's runs from criterion 7.
3. Run `wb check`, `wb run code-work check`, `doccheck`, `refcheck` and the whole `tests` root.
**Verification:** the checks above report no problem; every completion criterion is marked met or not met with its evidence.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-accept-decision-at-ask#F`.

## Verification for the plan as a whole

The whole `tests` root and every package test root, `wb verify packages/workbench`, `wb check`, `wb run code-work check`, `doccheck`,
`refcheck` and `git diff --check`, after the owner's releases. Then, by the owner: `wb upgrade`, `wb rerender`, and a live session
that shows the harness prompt for the command at `ask`.

## Risks and sensitive actions

- **Authorization.** The command turns a document into an accepted decision, which outranks the code. A wrong digest check or a path
  that follows a link would accept or rewrite the wrong file. The helper recomputes everything itself, refuses links and checks the bytes
  it replaces. A security review is owed after D and runs only when the owner asks.
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
replace and the document check's status rule are the plan's own and are checked in D. The choice in item 4 (the log names the email, not
the name) is the author's and is for the owner to confirm.

### Increment B — the identity reader in the kit (not yet committed)

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
