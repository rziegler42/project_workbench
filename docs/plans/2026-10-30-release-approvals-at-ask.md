# Offer the level ask for wb release-approvals

Status: Completed
Created: 2026-10-30
Candidate: none — the `wb release-approvals` part of workbench-v1#checkpoint-levels-beyond-block, which stays open: `delegated` for it and for the other keys, and `ask` for the keys that are not this one, are not built here, and a completed plan that named the candidate would close it
Specs: command-permissions, trust-and-approval

## Goal

`wb release-approvals` offers `block` and `none` today. At `block` the harness denies the agent and the owner runs it; at `none` the
agent runs it with nothing to confirm, which lets an agent make the first-party packages trusted after editing them. The owner wants
the middle level: at `ask` an agent reads a preview of exactly what a release would write, shows it, and runs the command with the
digest of that preview, and the harness prompts the owner to confirm that command, as `groundwork accept` does for a decision.

When the plan is done, `wb release-approvals` offers `block`, `ask` and `none`, defaulting to `block`; `wb preview release-approvals`
prints what a release would write, and nothing, with a digest; at `ask` the command without a terminal refuses unless it carries the
digest it recomputes now; the rendered rules ask for it at `ask` and deny it at `block`; and the owner has run it once at `ask` in a
live session and seen the prompt.

## Scope

- A read-only preview of the release (`wb preview release-approvals`): the packages and modules it would record, each one's
  declaration hash and tree hash as a new value or as the value already recorded, the approver and time the records would carry, and
  the shipped records that this release would leave stale. It ends with a digest, the first 32 hexadecimal characters of the SHA-256
  of that text, as `wb plan-status --digest` does.
- `wb release-approvals --digest <32 hex>`: at a level of `ask` and with no terminal the command recomputes the preview inside the
  command and writes only when the digest equals it; any other form without a terminal at `ask` is refused. A run at a terminal goes on
  as it does today.
- The key `wb release-approvals` offers `ask` besides `block` and `none`; the rendered rules, the command gate, `wb settings` and the
  level log treat it as they treat the keys that already offer `ask`.
- The specs, the command table and the shipped texts say what each level of the key allows.

## Non-goals

- `delegated` for this key or any other, and `ask` for any other key. This plan does not implement the roadmap candidate
  `checkpoint-levels-beyond-block`, which asks that each key offer all four levels, and it names no completion for it: the candidate
  allows a plan per key, and this plan builds the `ask` level of one key, as the plan `2026-10-29-accept-decision-at-ask` did for
  `accept-decision`. The owner's approval of this plan is the owner's direction for that narrower scope; `delegated` for this key stays
  open under Deferred work and in the candidate.
- Changing what a release writes, the approver it records, or the verification of a package before it is released.
- Changing `none` for this key. A run at `none` goes on as it does today.
- Making `ask` the shipped default: the default stays `block`.
- Any change under `packages/`. The command lives in the installer, so no package is edited and no release follows.
- The owner's personal settings. The owner sets the level and runs `wb rerender`.

## Assumptions and constraints

- Read from the code on 2026-10-30: the command is `firstparty.release_approvals`, routed by `cli.py` through `_unattended_call`; it
  has no terminal test and no digest; `levels._OFFERS` gives the key `none` only; `wb approve-plan` is the one installer command whose
  key offers `ask`. How its `ask` rule is rendered and how the command gate matches it are read in Increment A before anything is
  written, and the plan changes if that reading differs.
- The level is read for the project the working directory is in (`levelrun`), as for the other keys. Where no level can be read (a
  directory that is not a project) the command goes on as today and writes no entry; this plan does not change that. The owner may want
  it refused there as a separate change, which the command-permissions spec already records as unrequested.
- A digest binds the owner's confirmation to the previewed hashes, not to the owner's reading of the packages. The preview shows what
  changed as hashes and as which records are new, and says that it does not show the files; the owner reads the change with `git diff`
  before confirming. This is the same limit `groundwork accept` states ("not covered").
- The command gate matches text, so the `ask` rule must be matched by an exact simple command: `wb release-approvals --digest <hex>`
  on its own. The launcher spelling, the interpreter spellings and the absolute-`wb` spelling follow the rule the other keys use.
- The approver and time of a release are constants of the code (`RELEASE_APPROVER`, `RELEASE_TIME`); the digest covers them, so a
  change of either changes the digest.
- Editing any file under `workbench/` does not make shipped approvals stale (they hash `packages/`), so this plan needs no release by
  the owner. A `wb rerender` is needed once for the rendered rules, and it is the owner's.

## Completion criteria

1. The preview prints the packages and modules it would record with their hashes, the stale records, the approver and time, and a
   digest, and writes nothing (a test compares the tree before and after). The digest changes when any hash, the approver, the time or
   the stale list changes, and not when nothing does.
2. At a level of `ask` without a terminal, the command refuses with no digest, a malformed digest and a wrong digest, and writes
   nothing; with the right digest it writes what the preview said, from the one plan it checked, and logs an attempt and an outcome that name the key, the level and
   the digest. At a terminal, at `none` and at `block` it behaves as before.
3. The key `wb release-approvals` offers `block`, `ask` and `none`, defaults to `block`, and `wb settings` prints it. The tests show the
   offers, the rendered rules (an `ask` rule for the exact spellings at `ask`; a `deny` at `block`; no `deny` at `none`, as today)
   and the command gate's reading in each case.
4. The specs and the command table say what each level allows; no text says that the key offers `block` and `none` only.
5. `wb check`, `wb run code-work check`, `wb verify packages/workbench` and the whole `tests` root pass.
6. After the owner's `wb rerender`, the rendered permissions list the command as an `ask` rule, and in a live session the owner has
   seen the harness prompt for `wb release-approvals --digest <hex>` and the release it recorded. This is the owner's run.

## Increments

### Increment A — Read the existing `ask` path and write the spec

**Outcome:** the spec says exactly what `ask` means for this key, and the plan's later increments are checked against a reading of the
code and not a guess.
**Dependencies:** none.
**Affected areas:** `docs/specs/command-permissions.md` (a section "`wb release-approvals` at `ask`" and the lines that say the key
offers `block` and `none`), `docs/specs/trust-and-approval.md` (the rendering rules and the table of who may run what, if they list
the key), and this plan's Result.
**Steps:**
1. Read how the key `approve-plan` gets its `ask` rule and its digest, and how the other owner-run keys get their `none`: `rules.py`,
   `rendering.py`, `levels.py`, `levelrun.py`, `command_gate.py`, `settingscmd.py` and the tests that pin them. Write down, in the
   Result, each place the new key would need a change and any that this plan does not list; if one is missing, stop and tell the owner
   before editing the plan.
2. Write the spec section: the forms (terminal, `ask` with a digest, `none`, `block`), the preview text and what the digest covers and
   does not cover, the log entries, and the rule that the level is read for the working directory's project and that a directory with
   no readable level goes on as today.
3. Update every statement in the specs that gives the key as `block` and `none` only.
**Verification:** `wb check`; `wb run code-work check`; the Result lists the places read and the places to change.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-30-release-approvals-at-ask#A`.

### Increment B — The preview

**Outcome:** `wb preview release-approvals` prints what a release would write, with a digest, and writes nothing.
**Dependencies:** A.
**Affected areas:** `workbench/firstparty.py` (a function that builds the release plan without writing, shared with
`release_approvals` so the preview and the write cannot differ), `workbench/cli.py` and `workbench/preview.py` or its dispatch,
`workbench/rules.py` (the preview action list), the tests.
**Steps:**
1. Write the tests first: the preview text for a scratch distribution; the tree unchanged after it; the digest stable for the same
   input and changed by a changed hash, approver, time or stale record; a refused package refuses the preview as it refuses the
   release.
2. Split `release_approvals` into a plan step, which reads and verifies the packages and returns the release plan (the hashes, the
   approver, the time, the stale list), and a write step, which takes that plan and writes its records and nothing else. The preview
   runs the plan step; `release_approvals` is the plan step followed by the write step on the plan it returned. The write step does
   not read the packages again.
3. Add the preview action with the text of the spec, ending with `digest: <32 hex>`.
**Verification:** the new tests; the existing release tests; the tests of `rules.py` that pin the preview actions.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-30-release-approvals-at-ask#B`.

### Increment C — The digest check at `ask`

**Outcome:** at `ask` without a terminal the command writes only with the digest of the preview it recomputes now.
**Dependencies:** B.
**Affected areas:** `workbench/cli.py` (`_release`, `_unattended_call`), `workbench/levelrun.py` (reading the level at `ask`), and the
tests.
**Steps:**
1. Write the tests first: no digest, a malformed digest and a wrong digest are refused and write nothing; the right digest writes and
   logs an attempt and an outcome with the key, the level and `digest:<32 hex>`; a digest at `none` and at `block` goes through the
   rule the spec states (a digest at `none` is refused before the run, as it is for a module's mapped argument); a terminal run is
   unchanged; a directory with no readable level goes on as today.
   Add a test of the window: a package file changed after the plan was built and its digest checked, and before the write, must
   leave the written records equal to the plan that was checked (the records then name the hashes the owner confirmed, and the changed
   tree no longer matches them, so it is not trusted); a test seam between the check and the write makes this deterministic.
2. Parse `--digest <32 hex>` as the last two arguments; build the release plan once inside the command; compare the digest of that
   plan's preview text; write only on equality, and write from that same plan and never from a second reading of `packages/`.
3. Write the attempt before the write and the outcome after, as the other levelled runs do.
**Verification:** the new tests; `tests.test_levelrun` and the tests that cover `none` for this key.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-30-release-approvals-at-ask#C`.

### Increment D — The level, the rules and the gate

**Outcome:** the key offers `ask`, and the rendered rules and the command gate treat it as they treat the other keys that offer `ask`.
**Dependencies:** C.
**Affected areas:** `workbench/levels.py` (`_OFFERS`), `workbench/rules.py` and `workbench/rendering.py` (the `ask` rule and the
`deny` by level), `workbench/command_gate.py`, `workbench/settingscmd.py`, and the tests of each.
**Steps:**
1. Write the tests first: the offers and the default of the key; the rendered rules at `block`, `ask` and `none` for each spelling;
   the command gate accepting the exact `ask` command and refusing a command that names it in another form; `wb settings` printing the
   level.
2. Give the key `ask` in `_OFFERS` and render the rules from the level, following what Increment A recorded.
3. Run the test that fails when a routed command is in neither list, and the drift tests.
4. Before committing, stop and ask the owner whether to run a security review (this change touches authorization: who may make the
   first-party packages trusted, the digest check of Increment C and the rendered rules and gate of this increment). An installed
   module provides `security-review`. Record the owner's answer in the Result; if the owner says yes, run the review of C and D
   together, judge the findings with `evaluate-findings`, fix the ones applied and run the verification again before the commit.
**Verification:** the new tests; `tests.test_levels`, `tests.test_rendering`, `tests.test_command_gate`, `tests.test_settingscmd`;
the owner's answer on the security review recorded in the Result, and its outcome if one was run.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-30-release-approvals-at-ask#D`.

### Increment E — The texts

**Outcome:** every text that lists the levels of the key says what each allows.
**Dependencies:** D.
**Affected areas:** `docs/development.md` (the command table), the specs that Increment A listed, and `docs/roadmaps/workbench-v1.md`
(the sentence of `checkpoint-levels-beyond-block` that names `wb release-approvals` among the keys that offer `block` and `none`
only; a roadmap edit stops for the owner's word).
**Steps:**
1. Search the documents for the key and for its levels; list every hit.
2. Change each to say `block`, `ask` and `none`, and what the preview and the digest are.
3. Stop and ask the owner before editing the roadmap; leave it listed under Deferred if the owner does not say.
**Verification:** the search of step 1 shows no text that says the key offers `block` and `none` only; `wb check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-30-release-approvals-at-ask#E`.

### Increment F — The close-out and the owner's runs

**Outcome:** the Result records what was run, and the owner's live run is recorded.
**Dependencies:** E.
**Affected areas:** this plan's Result, `docs/specs/command-permissions.md` ("Not built").
**Steps:**
1. Remove `ask` for this key from "Not built".
2. Ask the owner to run `wb rerender`, and read the rendered permissions for the `ask` rule.
3. With the level set to `ask`, change a file under `packages/` in a scratch copy or a throwaway edit, run the preview, show it, run
   the command with the digest, and record whether the owner saw the prompt and what the release wrote. Undo the throwaway edit and
   release again, so the shipped records are the real ones.
4. Write the Result with every criterion marked met or not met, and run `wb check`, `wb run code-work check`, `wb verify
   packages/workbench` and the whole `tests` root.
**Verification:** the checks of step 4; every completion criterion marked with its evidence.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-30-release-approvals-at-ask#F`.

## Verification for the plan as a whole

`wb check`; `wb run code-work check`; `wb verify packages/workbench`; `python3 -B -W error tests/run_all.py`; no file under
`packages/` changed by the plan; and the owner's live run of Increment F.

## Risks and sensitive actions

- **Trust.** A release makes the first-party packages trusted. At `ask` the owner confirms a digest of hashes, not the packages'
  content: a hasty confirmation trusts whatever the agent edited. The preview names what changed and the owner is told to read the
  diff; the plan does not make that automatic.
- **A change between the check and the write.** The kit has no lock over `packages/`. The command therefore plans once, checks the
  digest of that plan and writes that plan; a package edited after the plan is built is not released by it, because the records
  name the hashes that were confirmed and the edited tree no longer matches them. Increment C tests this window.
- **A change to who may trust the packages.** The plan touches authorization, so repository policy asks the owner whether to run a
  security review. Increment D stops for that question before its commit and records the answer.
- **A new path through the gate.** The command gate matches text, so a new `ask` rule must not let a different spelling through or
  refuse the one the plan promises. Increment D tests both, and the owner's live run checks the real harness.
- **Stale approvals during the plan.** None: no file under `packages/` is edited, so the shipped approvals stay valid. Increment F's
  throwaway edit does make them stale on purpose and is undone and re-released in the same increment.
- **The live run changes the shipped records.** Increment F says so and ends with the real records; a deletion of stale records goes
  through the owner's approval of the listed paths.
- **A directory with no readable level** keeps running the command as before; the plan records that and does not close it.

## Review record

Reviewer: Codex through the project's bridge (`ask-codex`), model `gpt-5.6-terra`, effort `medium`, with `wb run review-engine`.
Rounds: 3 of the bound of 3. Outcome: round 3 converged, with no meaningful finding. A review is not an approval.

- **R1-F1 (major), rejected.** The finding said the plan omits `delegated` for this key although the roadmap candidate requires four
  levels. The plan names no candidate and says it does not implement the candidate, which allows a plan per key, as the earlier plan for
  the decision key did. The non-goals now state that the owner's approval of this plan is the owner's direction for the narrower
  scope, and that `delegated` stays open.
- **R1-F2 (major), applied.** The plan touches authorization and had no checkpoint for the owner's question about a security
  review. Increment D now stops for that question before its commit and records the answer, and the risks section says so.
- **R2-F1 (major), applied.** Planning twice (once for the digest check, once for the write) left a window between the check and
  the write. The command now builds one release plan, checks its digest and writes from that same plan with no second read of the
  packages; Increment C tests the window with a seam, and the risks section records it.

Left for the owner: the approval of the plan, and the question of a security review at Increment D.

## Deferred work

- **`delegated` for `wb release-approvals`** and for the other keys, which waits on the decision about what a delegated review's
  subject is.
- **Refusing the command where no level can be read**, which the specs record as a separate change the owner may ask for.
- **A preview that lists the changed files** and not only the changed hashes. It would need a baseline the command does not keep.
- **`ask` for the other keys** that offer `block` and `none` only: `acknowledge-first-tier`, `acknowledge-second-tier` and the
  installer commands.
- **The roadmap sentence**, if the owner does not allow its edit in Increment E.

## Result

### Increment A — the reading and the spec (committed as `c6c6d7d`)

Changed: `docs/specs/command-permissions.md` only: a new section "`wb release-approvals` at `ask` (specified, not built)" (the reading
below, a table of forms, the preview, what the command does at `ask`, and what the digest does not cover), a note on the offers of the
key in the paragraph on `acknowledge`, `recover`, `attach` and `release-approvals` at `none`, and an entry under "Not built".
`docs/specs/trust-and-approval.md` names the key in its list of owner-run commands and in its release paragraph and says nothing about
levels, so it was not changed.

The reading, as run on 2026-10-30 (`rules.py`, `rendering.py`, `levels.py`, `levelrun.py`, `command_gate.py`, `cli.py`,
`firstparty.py`; the tests were listed, not read):
- **`rendering.plan`** is generic: a key `wb <word>` of `rules.OWNER_RUN` at `ask` renders an `ask` rule on the `wb` spellings and
  leaves the interpreter spellings denied; at `block` it renders a `deny`. So Increment D needs the offer of `ask` in `levels._OFFERS`
  and no new rendering code for this key; `rules.py` and `rendering.py` need no edit unless a test shows otherwise.
- **`command_gate`** is generic for such keys: `words` and `forms` give the exact simple command `wb release-approvals [<token> ...]`,
  through `wb` or the guarded store's `bin/wb`, and `--digest <32 hex>` is a `_TOKEN`. So the gate needs no edit; Increment D tests it.
- **`levelrun.optional`**, which `cli._unattended_call` uses, returns a route only at a verified `none`; at `ask` it returns `None` and
  the command goes on as it always did. Increment C therefore needs a new reading (a function beside `optional`) that returns the route
  at `ask` and at `none`, used by `_release` only, so that `attach` is unchanged. This is the one place the plan's list needs
  sharpening; it was already in Increment C's affected areas ("`levelrun.py` (reading the level at `ask`)").
- **`firstparty.release_approvals`** reads and verifies the packages and writes in one function; Increment B splits it.
- **Not read in detail, to be read in the increment that needs it:** `settingscmd.py` (how it prints the offered levels) in D; the
  tests that pin the key: `tests/test_levels.py`, `test_rendering.py`, `test_ack_recover_levels.py`, `test_approve_levels.py`,
  `test_permissions.py`, `test_firstparty.py`, `test_owner_run_arguments.py` and `tests/support.py`.

Choices written into the spec, for the owner: (1) a `--digest` at `none` is refused before the run, as for a module's mapped argument; (2)
a `--digest` at a terminal is refused, and a terminal run without one is as today (so the plan's "a terminal run goes on as it does
today" holds; the review showed that checking a digest at a terminal has no level to read there); (3) the digest enforcement counts
only while the level reads `ask` through the rendering record, so where it reads `block` because the record is stale the command does
not refuse itself, as it never did, and the harness's own rule is the barrier; (4) the preview prints every hash in full and not the
path of the distribution: the digest covers the hashes whole, which the plan's criterion 1 needs.

Places the later increments need that the reading above did not list (from the review, each read in the code):
- **Increment C.** `cli.py` lines 100 to 101 add `release-approvals` to the parser with no arguments, so `--digest` is a usage error
  before any level is read; the parser and the `USAGE` string change. `_unattended_call` wraps the whole call between an attempt and an
  outcome with evidence `""`; at `ask` the attempt must come after the plan is built and checked and carry `digest:<32 hex>`, so the
  command builds and checks the plan first and calls `levelrun.apply_logged` around the write only.
- **Increment B.** Adding `release-approvals` to `rules.PREVIEW_ACTIONS` makes `levels.agent_keys` derive an agent-safe key `wb
  preview release-approvals`, `command_gate.PREVIEW_ACTIONS` derive from it (the gate strips the pair `preview <action>`),
  `rendering.key_patterns` read it, and `cli._preview` and the `USAGE` lines (which say preview takes install, adopt, upgrade, add or
  rerender) change. Tests pin the list: `tests/test_levels.py`, `tests/test_command_gate.py` and `tests/test_rerender.py`. The specs
  that list the preview actions (`installer-interface.md`, and `command-permissions.md` near its list of agent-safe keys) change too.
- **Increment E (statements that still give the key as `block` and `none` only, left for E because the key does not offer `ask` until D;
  a deviation from step 3 of this increment, recorded here).** `command-permissions.md`: the list of what each level offers
  ("Which levels a key offers"), the paragraph that says every key offers `block` and `none` and that only the review engine's five
  offer `ask` besides the plan key, the line P4, the table row that says the key "has none and keeps none" (it has no terminal test; at
  `ask` it refuses without a digest), the lines that say it has "no terminal test and no digest", and the log exception for `attach`
  and `release-approvals` (at `ask` the run is logged). `installer-interface.md`: the lines that call it a release-time command that needs no
  terminal.
- **Read in D:** `settingscmd.py` has nothing key-specific (a grep found only a generic loop over the effective levels), and the tests
  that pin the key were listed and not read; Increment D reads them before it edits.

Verification as run: `wb check` and `wb run code-work check` (75 plans): no problems. No file under `packages/` changed.

Review: the `reviewer` agent, one exchange. It confirmed the reading of the code (the rendering and the gate are generic, so the key
needs only the offer of `ask`; `levelrun.optional` returns a route only at `none`). One blocking finding, applied: the preview printed
12-character prefixes of the hashes, so the digest could not change with every hash, and the spec overstated what it binds; the preview
now prints the hashes in full. Applied: the terminal row (the digest is refused at a terminal); the places for Increments B, C and E
recorded above. Recorded: the tests were listed and not read (a gap in step 1, to be closed in the increment that needs each).

### Increment B — the preview (committed as `d7556b8`)

Changed: `workbench/firstparty.py` (`release_approvals` is now `plan_release` followed by `write_release`; the new `ReleasePlan`,
`PlannedPackage` and `PlannedModule` hold the hashes in full, whether each record exists now, the approver, the time and the stale
keys; `preview_text` and `digest_of` build the text and its digest; the write takes the plan and does not read `packages/` again;
`_stale` returns full keys and takes the path), `workbench/cli.py` (`preview release-approvals`, with no argument, refused as a
usage error when one is given; the usage text), `workbench/rules.py` (`PREVIEW_ACTIONS`, which gives the agent-safe key `wb preview
release-approvals` and feeds the command gate), `tests/test_firstparty.py` (a class `PreviewTest`, 12 tests), `tests/test_levels.py` (a
test for the new key and the pinned key list), `tests/test_command_gate.py` (the preview is not the owner-run command) and the
documents that list the preview actions (`docs/development.md`, `docs/specs/installer-interface.md`, `docs/specs/command-permissions.md`:
the two lists of agent-safe keys and the entry for the preview). No file under `packages/` changed, so no release.

The preview text: `release approvals`, the counts of packages and modules, a line per package and an indented line per module with
its declaration hash and tree hash in full and `record new` or `record recorded`, `approver:`, `time:`, `stale records: <n>` and the
full keys, `not covered: ...`, then the last line `digest: <32 hex>`, the first 32 characters of the SHA-256 of the text before it.
On this repository it prints one package, 12 modules and 0 stale records, and left the tree unchanged.

Choices, for the owner: (1) the preview does not open the guarded store and does not install the launcher wrapper (it first opened the
store as the other previews do; the review showed that creating the store and seeding the settings are writes, and nothing in the
preview needs the store, so it was dropped, and a test shows a missing store is not created); (2) a plan with no packages prints a
preview of nothing with a digest, and the write of it writes nothing, as the release did; (3) the stale list is computed at plan time
and the write reports it from the plan; since the records of the plan are in the wanted set, it equals the list the old code computed
after writing; (4) module lines are indented under their package and do not repeat its name, and the digest covers the order; (5) the
safe walk of the shipped tree refuses an entry whose name holds a control character, and `_stale` returns an empty list when the walk
is refused, as the old code did, so a name that could forge a line of the preview never reaches it; the text prints the stale keys,
the approver and the time through `display.clean` as well, and a test builds a plan with such names to show it.

Verification as run: the new tests failed first (the plan and write functions did not exist and the preview action was refused), then
`python3 -B -m unittest discover -s tests -t tests -p test_firstparty.py`: 54 tests OK; `test_levels.py`: 34 tests OK;
`python3 -B -W error tests/run_all.py` before the key list was updated: 6265 tests in 13 roots with three failures, all in
`tests/test_levels.py` and all because the new agent-safe key was not in the pinned key list, which the test change fixes; the whole
suite is run again after the review. `wb preview release-approvals` run on this repository: output as above, tree unchanged.

Review: the `reviewer` agent, one exchange, no blocking finding. Applied: (1) a test that a damaged record in the shipped tree does not
refuse the preview and reads as `record new`, and does not make the release refuse where it did not (the `approvals.check_*`
functions return a `Check` and do not raise); (2) the preview no longer opens the guarded store, with a test; (3) the printed names go
through `display.clean`, with the test above (a name with a newline is refused earlier by the safe walk); (4) command gate tests that
`wb preview release-approvals` does not hide a release in the same command (`;`, `&&`, `|`, and the reverse order); (5) the section
of the spec now says the preview is built and the rest is not. Recorded: the old `release_approvals` could not be compared by the
reviewer (it had no diff); the structure, the idempotence and the no-package case are covered by the existing release tests, which
pass unchanged. A mutation check the reviewer named, for each of the digest over a prefix, the write re-reading the packages and the
stale list dropped from the text, fails a test.

After the review's changes: `python3 -B -W error tests/run_all.py`: 6269 tests in 13 roots, all OK; `wb check`, `wb run code-work check`
(75 plans) and `wb verify packages/workbench`: no problems. No file under `packages/` changed.

### Increment C — the digest check at `ask` (committed as `eba9a2b`)

Changed: `workbench/cli.py` (`--digest` on the parser and the usage text; `_release` reads the level and applies the rules below;
`_release_report` and `_release_approvals` share the report), `workbench/levelrun.py` (`unattended`, beside `optional`, which still
serves `attach` alone), `tests/test_release_ask.py` (new, 14 tests), `docs/development.md` and `docs/specs/command-permissions.md`
(the digest check is built; the offer of `ask` is Increment D's). No file under `packages/` changed.

The rules as built: at a terminal a run goes on as it did and a `--digest` is refused; without a terminal at a verified `none` it runs
and is logged as before and a `--digest` is refused before the run ("a digest needs the level ask"); at a verified `ask` a missing or
malformed digest is refused with the way to the preview, `plan_release` is built once (a refused package refuses with its reasons),
the digest of its preview text is compared with the one given, a wrong one is refused with nothing written and no log entry, and the
right one is written from that same plan through `levelrun.apply_logged` (the attempt, with `digest:<32 hex>`, just before the write,
and the outcome after; if the attempt cannot be written nothing is written); at `block` or where no level can be read it goes on as it
always did (a `--digest` is not checked there).

Choices, for the owner: (1) a malformed digest is a refusal with exit 1 and a reason, not a usage error with exit 2; (2) at `block` and
where no level can be read a `--digest` is ignored, as the spec's stated limit says: the command never refused itself there and the
harness's rule is the barrier, so a stale rendering record that reads `block` while the harness file still holds the `ask` rule would
run an agent's `--digest` unchecked after the owner's confirmation of the prompt; Increment D's rules and the owner's `wb rerender`
keep the record and the file in agreement; (3) until Increment D the key does not offer `ask`, so the check is tested through a patch
of the level reading (`levelrun.level_now`) and not through the owner's settings.

Verification as run: the new tests failed first (the parser took no `--digest`, and without one the command at `ask` still wrote);
`python3 -B -m unittest tests.test_release_ask tests.test_ack_recover_levels`: 55 tests OK (14 new; the existing release tests at
`none`, which mock `firstparty.release_approvals`, pass unchanged); two hand-made mutants, each reverted, were caught: the write
re-planning (`firstparty.release_approvals` in place of `write_release`) fails the test of the window, and a skipped comparison fails
the wrong-digest and the earlier-digest tests. The whole suite is run after the review.

Review: the `reviewer` agent, one exchange, adversarial, no blocking finding; it found no way to write a release at a verified `ask`
without the digest of the plan the command built now (abbreviated options are off, `wb run` has no route to `_release`, the plan is
built once and the same plan is written). Applied: (F2) a test at `block`, with and without a digest, that the command goes on and
logs nothing, which pins choice 2; (F3) a refusal after a part-way write now says that records written before the failure remain
and that a rerun repeats the release (the level log still says `refused`; `apply_logged` takes no reason, and the old release
could leave earlier records too); (F4) the format refusal is told from the wrong-digest refusal, the failed-attempt test checks the
message and an empty log, and the no-level test checks that the release was written. Recorded, not applied: (F1) the check fails open
where the level cannot be read for the working directory (outside a project, or a stale or unreadable rendering record), which the
spec states as a limit. Refusing there was weighed and not done: the command has no terminal test and the owner's own `!` runs have
no terminal either, so refusing unattended runs where the level is not a verified `ask` or `none` would refuse the owner's runs at the
default level `block`; the harness's `ask` prompt on the command text still applies, and the owner sees a bare command with no
digest in it. Criterion 2 therefore holds where the level is verified for the working directory's project. A directory that is
no project, and a project whose rendering record is not sound, remain as exposed as before this plan. (F5) argparse accepts
`--digest=<hex>` and a repeated `--digest` (the last is checked, logged and used, so there is no bypass); Increment D tests how the
command gate matches those spellings. The reviewer could not run anything.

One consequence for the owner: at a verified `ask` the owner's own run without a terminal (the `!` prefix) needs the digest too; a run
at a terminal does not.

After the review's changes: `python3 -B -W error tests/run_all.py`: 6284 tests in 13 roots, all OK; `wb check` and `wb run code-work
check` (75 plans): no problems. No file under `packages/` changed.

### Increment D — the level, the rules and the gate (committed as `a3b4007`)

Changed: `workbench/levels.py` (`_OFFERS` gives `wb release-approvals` the offers `ask` and `none`, after `block`; the module docstring
says so; `_DEFAULTS` is untouched, so the default stays `block` and the digest of the default table is unchanged), `tests/test_release_ask.py`
(a class `AtAskFromTheOwnersSettings`: the level is the owner's setting, with no patch of the level reading), `tests/test_levels.py`,
`tests/test_approve_levels.py` and `tests/test_ack_recover_levels.py` (the pinned offers of the key), `tests/test_command_gate.py` (what
the gate lets reach the harness prompt and what it refuses), and the status wording of `docs/specs/command-permissions.md` and
`docs/development.md`. The rendering and the command gate needed no edit, as the reading of Increment A said: they are generic for a key
`wb <word>` of `rules.OWNER_RUN`. No file under `packages/` changed.

The new tests (12, with the pinned ones updated): `wb settings` prints `level wb release-approvals: ask`; the plan's `ask`, `open` and
`deny` lists at `ask`, `block` and `none`; the rendered file's `permissions.ask` and `permissions.deny` lists at each level (the launcher
spellings asked at `ask`, denied at `block`, in neither at `none`, the interpreter spellings denied at all three); at `ask` with the real
setting a bare run is refused and the right digest writes with the log naming it; `--digest=<hex>` and a repeated `--digest` are checked by
the last value; the gate lets the exact plain-token forms reach the prompt and refuses `;`, `&&`, `|`, `$(...)`, a quoted digest and
`bash -c`; a setting of `ask` for a key that does not offer it (`wb attach`) is still read as `block`; and a harness file edited after
attach makes the level read `block`, so the command goes on unchecked, which pins the stated limit.

A fact for the owner, found by the review and confirmed with `wb settings`: the owner's personal settings already say `ask` for
`wb release-approvals` (and for `wb upgrade`, `wb attach`, `wb approve` and `acknowledge-first-tier`, which still read `block` because they
do not offer it). Until this increment that `ask` was noted and read as `block`; with it the key reads `ask` in the effective table. In
this clone the command gate reads that table, so it already refuses a command that names the word in any form but the exact simple one;
the rendered permissions and the digest requirement take effect only after the owner's `wb rerender`, which Increment F asks for. After it,
the owner's own run without a terminal (the `!` prefix) needs the digest as well.

Verification as run: the new tests failed first (the key did not offer `ask`, so the owner's setting read `block`); `python3 -B -m unittest
tests.test_release_ask tests.test_levels tests.test_command_gate tests.test_approve_levels tests.test_ack_recover_levels`: 232 tests OK;
`tests.test_release_ask` after the review's added tests: 26 tests OK. The whole suite is running (it was started before the review's
tests were added to `test_release_ask.py`, which are run on their own as above).

Review: the `reviewer` agent, one exchange, no blocking finding. It confirmed that nothing else needs to change in code (rendering,
`harnessplan.render_permissions` and the gate are generic; the interpreter spellings stay denied at `ask` and `none`; the default and
its digest are unchanged), that no spelling reaches the command without the prompt that the stated limits of the gate do not already
allow, and that no other test pinned the offers. Applied: a test that parses the rendered file's `ask` and `deny` lists at each level
(the gap it found; a string search could not tell `ask` from `deny`). Recorded, not applied: no test drives `command_gate.run` with the
real table (every gate test gives `judge` its keys; the owner's live run in Increment F covers the real harness); the statements in the
specs that still give the key as `block` and `none` only, and the dated reading of Increment A, are Increment E's. The reviewer could
not run anything.

Security review (plan step 4): the owner asked for it ("run it"). The `security-reviewer` agent reviewed B to D, ran experiments on a copy
with a fake home and a throwaway store, and then, after the fixes, made an independent second look.
- **Medium, fixed.** An agent could force the verified level to read `block` (edit the harness file or `.workbench/local/harness.json`
  with a shell write, edit the seed of the manifest, or run from a directory that is no project or from a nested decoy), which skipped the
  digest check: the bare command wrote the release with no log entry, and the prompt showed a bare command. Fix: where there is no terminal
  and the verified level could not be read, the owner's own setting in the guarded store (`cli._owner_says_ask`) decides; at `ask` the digest
  is required, checked and logged as at a verified `ask`. A setting that is not `ask` goes on as before, so the owner's runs at the default
  `block` are not refused. Tests: the harness file edited, the local manifest removed and a directory that is no project each need the digest
  (they failed before the fix and fail again if the rule is switched off), and `block` with a setting that is not `ask` goes on as before.
- **Low, fixed:** a repeated `--digest` is refused (the prompt shows the whole command; the command checks one digest); a write that fails part
  way exits with 4 and the level log reads `stopped after writing (exit 4)`, and a failure before any record exits with 1 and reads `refused
  before writing` (`ReleaseError.written`); a shipped tree that cannot be listed makes the preview say `stale records: unreadable` and the
  release add a warning that stale records are not reported (the writes are unchanged).
- **Low, recorded and not fixed:** a record planted for other hashes still makes the write fail part way (exit 4, logged honestly); an agent
  that can plant a record can write valid ones directly, so the trust is held by the owner's review of the commit that holds the records,
  as the specs say.
- **Second look, no Critical, High or Medium.** It confirmed the fixes hold (297 tests, and 16 constructed cases, including variants of the
  key and of the option, a version 1 settings file and another key set to an invalid level). Three Lows: (1) a damaged settings file, or
  any invalid key name in its `levels`, makes `_owner_says_ask` answer no, so the command fails open if the verified level is also
  unreadable; the agent cannot damage the store, so the owner would have to. The owner decided (after the author recommended it) that it
  fails closed: a damaged file reads as `ask` for this key where there is no terminal and the verified level cannot be read, the refusal
  says the settings are damaged and to run `wb settings`, and a missing file (which every command seeds) is sound; three tests (a file that
  is not JSON, a `levels` that is not an object, an invalid key name) failed first and pass; (2) with the setting at `none` and the verified level unreadable the run is not logged: rejected, because the
  spec records as the owner's earlier decision that a run where no level can be read is not logged and that the log is a record and not a
  control; (3) the release did not warn when the stale list was unreadable: fixed above.
- **What remains, stated in the spec:** a shell write to the owner's settings in the guarded store, to a harness file that removes the `ask`
  rule, or to the shipped records themselves is not stopped by an edit tool and the hook is not a boundary; the harness's prompt and the
  owner's review of the commit are the barrier.

After the security fixes and the fail-closed change: `python3 -B -W error tests/run_all.py`: 6307 tests in 13 roots, all OK; `wb check`
and `wb run code-work check` (75 plans): no problems. No file under `packages/` changed.

### Increment E — the texts (committed as `f044c33`)

Changed, all documents: `docs/specs/command-permissions.md`, `docs/specs/installer-interface.md`, `docs/specs/terms.md`,
`docs/specs/code-work.md` and `docs/development.md`. The search (step 1) was made by a read-only agent, because the command gate at the
owner's level `ask` refuses a shell search that names the key; it listed 60-odd lines, each marked still true, partly true or stale, and
each location was read before it was edited. Changed, with the stale statement they replace: the list of keys that offer `ask` and the
opening paragraph of `command-permissions.md` (the key now offers it, as does `accept-decision`, which the list had also omitted); the
row of the table of levels ("has none and keeps none" now says what happens at `ask`); the "Which levels a key offers" list; the log
paragraph, the `Levels offered` paragraph, the paragraph on `acknowledge`, `recover`, `attach` and `release-approvals` (the offers, the
digest and the owner's own settings read where the verified level cannot be) and the dated reading of Increment A (now says
`levelrun.unattended` was built); the table row, the paragraph and the rules in `installer-interface.md` (the arguments, the levels,
`--digest`, the rendered `ask` rule at `ask`); the list of what an owner may set in `terms.md`; the checkpoint list of `code-work.md`
(`accept-decision` offers `ask`); and in `development.md` the paragraphs on the release-time command (the digest, the preview that lists
stale records) and the sentence on `accept-decision` that still said it offers `block` and `none`.

Left for the owner (step 3): the two sentences of `docs/roadmaps/workbench-v1.md` under `checkpoint-levels-beyond-block` that still say
the key is one of the three that offer `block` and `none` only (about line 666) and that `wb release-approvals` "needs a decision on where
its level is read from" (about line 678). A roadmap edit stops for the owner's word. Left alone because they are still true or are other
plans' history: `harness-modules.md` and `trust-and-approval.md` (they name the key in the deny list and describe the review of the
diff, and defer the levels to `command-permissions.md`), and the entry under "Not built", which stays until the owner's live run in
Increment F.

Verification as run: `wb check` and `wb run code-work check` (75 plans): no problems.

Review: the `reviewer` agent, one exchange, no blocking finding. It repeated the search itself (with a search tool that may name the key)
and judged every hit against the code: the offers, the lists of keys that offer `ask` (only `approve-plan` and the release key through
`_OFFERS`, `accept-decision` and the review engine's five through their declarations), the digest rules, the owner-settings fallback and
the log entries all hold. Applied: the opening of the section still said that the statements elsewhere were Increments E and F, so it
now says E corrected them and F is the live run (1); the exit codes of `development.md` now also name 3 and 130 for a logged run (2).
Recorded: whether a duplicated key in the settings counts under "not JSON" was not checked by the reviewer (3); the spec names the
causes it lists, and a duplicate is read by `declarations.parse_json`, which refuses it as a damaged file. The roadmap sentences and the
entry under "Not built" are left as stated above.

### Increment F — the close-out and the owner's live run (committed with the trailer `#F`)

Changed: the entry for the key under "Not built" in `docs/specs/command-permissions.md` is removed (it is built and the live run is
recorded here), `docs/roadmaps/workbench-v1.md` (the two sentences of `checkpoint-levels-beyond-block`, edited with the owner's word and
committed on their own: the key is no longer one of those that offer `block` and `none` only, and its level source is no longer an open
decision; the candidate stays open and nothing is written as complete), and this Result.

The live run, 2026-10-30, with the owner's `wb rerender` already done (read in `.claude/settings.local.json`: the `ask` rules for the
launcher spelling and for the guarded store's `bin/wb` spelling of the key are rendered): `wb preview release-approvals` printed one
package, 12 modules, 13 records all `recorded`, 0 stale and `digest: 16dfb6816d2c92bee43f2f61aebbf61a`, and wrote nothing; then `wb
release-approvals --digest 16dfb6816d2c92bee43f2f61aebbf61a` ran as a command of its own and printed `wrote 13 approvals for 1 first-party
packages`; the tree was unchanged (the release is idempotent), and the level log holds the pair `wb release-approvals ask
digest:16dfb681...` and `done written`. The owner did not notice a prompt on the first run and could not say whether one appeared. The same
command was run again, with the owner watching, and the owner saw the harness prompt: the second pair of lines in the log is the same.

Deviation from step 3 of this increment, chosen with the owner's word ("do live run") after the author recommended it: the run did not first
make a throwaway edit under `packages/`. With nothing changed the release rewrites identical records, so the run shows the prompt, the
digest check and the log line without making the shipped approvals stale and then releasing again. The write of a release that changes
records is covered by the tests (the preview, the digest, the window between the check and the write, and the part-way failure), not by the
live run.

Not run: the bare command with no digest in a live session (the tests cover its refusal at a verified `ask`, where the settings are damaged
and where the verified level is forced to `block`).

Completion criteria, each marked met or not met:
1. **Met.** The preview prints the packages and modules with their full hashes, whether each record exists, the approver, the time and
   the stale records, and a digest, and writes nothing; the digest changes with a hash, the approver, the time and the stale list
   (`PreviewTest`, Increment B; the live preview wrote nothing).
2. **Met.** At a verified `ask` without a terminal the command refuses with no, a malformed or a wrong digest and writes nothing; with the
   right digest it writes the plan it checked and logs the attempt and the outcome naming the key, the level and the digest; a terminal, `none` and
   `block` behave as before (`tests/test_release_ask.py`, Increments C and D; two live runs). The security review added that the owner's own
   settings decide where the verified level cannot be read, and that damaged settings read as `ask` for the key.
3. **Met.** The key offers `block`, `ask` and `none` and defaults to `block`; `wb settings` prints it; the rendered file holds the `ask`
   rules at `ask`, the `deny` at `block` and neither at `none`; the gate's reading of the exact forms and of the refused ones is tested
   (Increment D).
4. **Met.** The specs, the development guide and the roadmap say what each level allows (Increment E and the roadmap edit); the reviewer's
   search found no remaining statement that the key offers `block` and `none` only.
5. **Met, as run.** `wb check`, `wb run code-work check` (75 plans) and `wb verify packages/workbench` report no problems; the whole `tests`
   root and every package test root pass: `python3 -B -W error tests/run_all.py`: 6307 tests in 13 roots, all OK.
6. **Met.** After the owner's `wb rerender` the rendered permissions list the command as an `ask` rule, and in a live session the
   owner saw the harness prompt for `wb release-approvals --digest <hex>` on the second run, and the release it recorded is in the level log.

Open for the owner: `delegated` for this key and for the other keys that do not offer it (the roadmap candidate stays open); the
`brainstorm` gap and the follow-up of the plan `2026-10-30-close-the-superpowers-retirement`; and a push of the local commits, which needs the
owner's word.
