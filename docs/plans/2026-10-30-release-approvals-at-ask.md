# Offer the level ask for wb release-approvals

Status: Proposed
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

### Increment A — the reading and the spec (not yet committed)

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
