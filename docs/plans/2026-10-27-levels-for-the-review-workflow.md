# Levels for the review engine's owner-run commands and the planning workflow

Status: In Progress
Created: 2026-10-27
Candidate: none (an owner request from the "Not built" list of `command-permissions.md`; no roadmap candidate names it)
Specs: command-permissions, module-contract, review-engine
Decisions: none yet; Increment B drafts one, `Proposed`

## Goal

The owner can do the planning workflow (draft, review, approve) from a place with no terminal, without setting any key to
`none`. Today the review engine's five owner-run arguments (`extend`, `reset`, `archive`, `prune`, `amend`) offer `block` only, so a
review that reaches its bound, or a decision to amend, stops the work until the owner is at a terminal. When the plan is done each of
them offers `block` and `ask`, as `approve-plan` does: an agent runs it with a digest of a preview the owner's harness prompt shows,
and the run is logged. Whether they also offer `none` is a decision of Increment B **(call: yes, for consistency with decision 3 of
`2026-10-26-a-level-for-every-command`; the owner decides)**. The owner also has a written map of every action in drafting, reviewing and
approving a roadmap, spec, design or plan, with the level that governs it and what blocks without a terminal.

## Scope

- A map of the workflow and its keys (Increment A).
- A decision record for the change to the module contract that the clarification note of `2026-10-26-a-level-for-every-command`
  says is needed (Increment B).
- The installer side: a field on a command's declaration naming the levels each owner-run argument offers, the key registry,
  the rendered rules, the launcher reading the level, the log (Increments C and D).
- The review engine's helper: a preview and digest for `extend` first, then for `reset`, `archive`, `amend` and `prune`
  (Increments E and F).
- The spec and development-guide text that these change (Increment G).

## Non-goals

- The owner-run arguments of other modules: `mempalace init` and `mine`, `remote-runner fetch-overwrite`. The mechanism is built
  so they can use it later; no key but the review engine's is changed here.
- `ask` for `submit-remote-job`, `push-shared-branch` and the installer commands that are not about the planning workflow
  (`upgrade`, `add`, `acknowledge`, `rerender`). Listed under Deferred.
- A new command to approve a roadmap, a spec or a design, or to accept a decision. No such command exists, by design: a spec and a
  roadmap have no status gate (`AGENTS.md`), a design is approved in conversation, and a decision is accepted by the owner's edit of
  its status. Increment A records this in the map. Whether to build `wb accept-decision` is an open question for the owner, not work
  here.
- Any change to `approve-plan`, which already offers `ask`, `delegated` and `none`.
- Setting any key to `none`, and changing the owner's settings file. Rendering a new level is the owner's act.

## Assumptions and constraints

- The terminal test for a module's owner-run argument is in the launcher (`commands.owner_refusal`, `workbench/commands.py`), while
  `command-permissions.md` says the helper checks its own terminal. Increment B reads both and records which is true before deciding.
  Until then this plan does not assume where the digest is computed.
- The first-party packages (`packages/workbench/review-engine`) are edited in a scratch copy and landed with `cp`, and the owner
  runs `release-approvals` after each landing. A landing changes the module's tree hash, and until `release-approvals` runs the command
  gate refuses every Bash call in the session (seen on 2026-10-27 with the `claude` module). Each package increment therefore
  stops at its landing for the owner. The core `workbench/` is edited directly.
- A new declaration field changes a module's declaration hash. The owner then runs `wb acknowledge`, `wb upgrade` (to confirm the
  declaration and re-pin the helper) and, to render a changed level, edits the personal settings and runs `wb rerender`. None of
  these can be run by an agent, and none is possible without a terminal. **This work is therefore finished at a terminal and takes
  effect only afterwards.**
- A reviewed document is hostile input and what a review reads can leave the machine (`review-engine.md`, "What leaves the
  machine"). Nothing here changes what is sent.
- Secrets stay out of every file this plan or its reviews read. No log, digest or host name is copied into a tracked file.
- The existing levels, defaults and the rule that an unknown or stale rendering reads `block` are unchanged.
- Discovery: skipped — no discovery tooling installed; the files above were read directly.

## Completion criteria

1. `command-permissions.md` holds a map of the planning workflow, every row checked against `wb settings` at the commit that wrote
   it.
2. A decision record for the module-contract change exists, `Proposed` until the owner accepts it, and Increments C to G were
   started only after it was `Accepted`.
3. A command's declaration can name the levels each of its owner-run arguments offers beyond `block`; a declaration that names a level
   for an argument that is not owner-run, names an unknown level, or names `delegated` is refused by `verify`.
4. `wb settings` prints a `level` line for each review-engine owner-run key, and offers `ask` for it; a level the table sets that the
   key does not offer reads `block` with a note.
5. At `ask`, `wb run review-engine extend <document> <n> --digest <32 hex>` extends the bound only when the digest equals the one
   the engine's preview prints for that review now; a stale, missing or wrong digest, a changed review, or an unrendered or stale
   rendering refuses with nothing written. At a terminal the owner's command works as before.
6. The same holds for `reset`, `archive`, `amend` and `prune`, with the digest bound to what each would change or delete.
7. Every run at `ask` that is not at a terminal leaves an attempt line before the helper runs and an outcome line after.
8. `python3 -B -W error tests/run_all.py` passes, apart from failures recorded as pre-existing, and each new test is shown to fail
   without its change.

## Increments

### Increment A — Map the planning workflow and its levels

**Outcome:** `command-permissions.md` has a section, "The planning workflow without a terminal", with one row per action in drafting,
reviewing and approving a roadmap, spec, design, plan or decision: the skill or command, the key that governs it, its level in the
default table, whether it needs a terminal, and what blocks. The section says plainly where there is no key (approving a roadmap,
spec or design; accepting a decision).
**Dependencies:** none.
**Affected areas:** `docs/specs/command-permissions.md`.
**Steps:**
1. Read the `draft-*`, `peer-review`, `evaluate-findings`, `request-review`, `delegate-approval` and `run-increment` skills and the
   review engine's command table, and list every command or edit each one performs.
2. Run `wb settings` and record the level of each key that the list reaches.
3. For each row, state whether an agent can run it with no terminal under the default table and under the owner's table as it is now,
   by reading the rendering and the command gate; test nothing by running an owner-run command.
4. Write the section. Mark what is read from the code and what is an inference.
**Verification:** `wb run code-work check`; `doccheck` and `refcheck` (silent is clean); every row compared with a fresh `wb settings`
output; `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-levels-for-the-review-workflow#A`.

### Increment B — Decide how a module's owner-run argument gets a level

**Outcome:** a decision record, `Proposed`, in `docs/decisions/`, that answers: where the terminal test and the level are read
(launcher or helper); the shape of the declaration field; how a preview and its digest are produced by a module (a new argument, its
name, what it prints, what it binds); how the level reaches the helper; how the log attempt is written before the helper runs; whether
`none` is offered; and the effect on the declaration hash and on installed projects. It states the alternatives rejected and the
consequences, the bad ones included. It supersedes nothing and leaves the clarification note of `2026-10-26-a-level-for-every-command`
unedited.
**Dependencies:** A (its map names the arguments and what blocks).
**Affected areas:** `docs/decisions/<date>-owner-run-arguments-take-a-level.md`, `docs/decisions/README.md`.
**Steps:**
1. Read `workbench/commands.py`, `workbench/launch.py`, `workbench/declarations.py`, `workbench/levels.py`, `workbench/levelrun.py`,
   the review engine's helper, `module-contract.md` and the accepted decisions on levels.
2. Draft the record from the template of the `draft-decision` skill, status `Proposed`.
3. Add its row to the index with the status `Proposed`.
4. Stop. **The owner accepts it; this plan does not.** Increments C to G wait for `Accepted`.
**Verification:** `doccheck` and `refcheck`; `git diff --check`; the record's evidence line names the files read and the commit.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-levels-for-the-review-workflow#B`.

### Increment C — Declare the levels of an owner-run argument and register the keys

**Outcome:** the declaration schema accepts the field Increment B chose; `verify` checks it; `levels.py` builds the key for a module's
owner-run argument with the levels the declaration names; `rendering` renders the `ask` rule for it; `wb settings` and the settings
reader treat it like any other key. Nothing changes for a declaration without the field.
**Dependencies:** B accepted.
**Affected areas:** `workbench/declarations.py`, `workbench/levels.py`, `workbench/rules.py`, `workbench/rendering.py`,
`workbench/harnessstage.py` (as needed), `workbench/settingscmd.py`, and tests under `tests/`; the specs this changes,
`docs/specs/module-contract.md` (the declaration schema, which rejects an unknown field) and `docs/specs/command-permissions.md`
(the levels such a key offers). No first-party package.
**Steps:**
0. Update `module-contract.md` and `command-permissions.md` in this commit, so no commit leaves a spec that contradicts the code.
1. Write the failing tests: a valid field, an unknown level, `delegated`, a level for a non-owner argument, a field on a command with
   no owner arguments, and the declaration hash changing with the field.
2. Add the field to the schema and to `verify`.
3. Build the registry entries, including the default (`block`) and the note when a table entry names a level the key does not offer.
4. Render the `ask` rule and the gate's entry for each such key; update the hand-kept key lists in the tests that list every key.
5. Run each new test against the old code to see it fail.
**Verification:** the new tests; `python3 -B -W error tests/run_all.py`; `wb check`; `wb run code-work check`; `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-levels-for-the-review-workflow#C`.

### Increment D — The launcher reads the level and logs the run

**Outcome:** `wb run <command> <argument>` for an owner-run argument that offers `ask` runs without a terminal only when the key reads
`ask` (the record, the table, the permissions file and the harness agree), passes what B decided to the helper, writes the attempt
line before the helper starts and the outcome line after, and otherwise refuses as today. At a terminal nothing changes.
**Dependencies:** C.
**Affected areas:** `workbench/commands.py`, `workbench/launch.py`, `workbench/levelrun.py`, `workbench/levellog.py`, tests, and
`docs/specs/command-permissions.md` and `docs/specs/module-contract.md` where the launcher's behaviour is described.
**Steps:**
0. Update those specs in this commit.
1. Write the failing tests with a fake helper: no terminal at `block` (refused), at `ask` with a good, a wrong and a missing digest, a
   stale rendering, a table that changed, a helper that fails, and an interrupt after the attempt line.
2. Implement the launcher change so that the attempt line is written before the helper is launched and an outcome line exists on every
   path.
3. Confirm that a refused run starts no helper and writes nothing to the project.
**Verification:** the new tests, each shown to fail without the change; the full suite; `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-levels-for-the-review-workflow#D`.
**Security review:** this increment and C change a trust boundary (who may run an owner-run argument, and how a digest binds it). The
owner is asked whether to run one after D, as `AGENTS.md` requires; it runs only on the owner's word.

### Increment E — `extend` with a preview and a digest

**Outcome:** the review engine declares the levels `extend` offers; it prints a read-only preview of an extension (the review, its
seal, the window, the bound now and after) and a digest of it; and at `ask` it extends the bound only when the digest it computes now
equals the one given.
**Dependencies:** D.
**Affected areas:** `packages/workbench/review-engine/helper/review-engine`, `packages/workbench/review-engine/module.json`, the
module's tests, `docs/specs/review-engine.md`. This is a first-party package: scratch copy, `cp` landing, then the owner's
`release-approvals`.
**Steps:**
1. In a scratch copy, write the failing tests with the fake bridge: the preview writes nothing; a correct digest extends; a wrong,
   stale or missing digest, a review that changed after the preview, a closed review and a bound that would pass the ceiling refuse
   with the state unchanged.
2. Implement the preview and the digest check inside the review's lock, so the digest is compared against the state that is written.
3. Land with `cp` and stop. **The owner runs `release-approvals`**, then `wb acknowledge` and `wb upgrade` for this clone.
4. Run the module's tests and the full suite.
**Verification:** `PYTHONPATH=. python3 -B -W error -m unittest discover -s packages/workbench/review-engine/tests -t packages/workbench/review-engine/tests`; the
full suite; `git diff --check`; `wb check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-levels-for-the-review-workflow#E`.

### Increment F — `reset`, `archive`, `amend` and `prune`

**Outcome:** the other four owner-run arguments offer `ask` the same way, each with a digest of what it would change or delete (for
`prune`, the list of reviews it would remove, so a digest of a different list is refused).
**Dependencies:** E.
**Affected areas:** the same as E, including `docs/specs/review-engine.md` for the four arguments.
**Steps:**
0. Update `review-engine.md` in this commit for the four arguments, as E does for `extend`.
1. Failing tests per argument, as in E; for `prune` also a list that changed between the preview and the run.
2. Implement each preview and digest check under the same lock rules as the argument's own change.
3. Land with `cp`, stop for `release-approvals`, `wb acknowledge` and `wb upgrade`, then run the checks.
**Verification:** as E.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-levels-for-the-review-workflow#F`.

### Increment G — Specs and guide

**Outcome:** the text states what is now true across the whole change. Increments C to F already updated the spec each one changed
(`module-contract.md`, `command-permissions.md`, `review-engine.md`), so this increment only consolidates: the "Not built" items for
the module arguments and for `extend` are removed from `command-permissions.md`, the map of Increment A is brought up to date, and
`installer-interface.md` and `development.md` match the code.
**Dependencies:** F.
**Affected areas:** `docs/specs/command-permissions.md`, `docs/specs/module-contract.md`, `docs/specs/review-engine.md`,
`docs/specs/installer-interface.md`, `docs/development.md`, `docs/decisions/README.md` (only if a status line changes after the owner
accepts).
**Steps:**
1. Compare each changed sentence with the code and with `wb settings`.
2. Update the map of Increment A where a row changed.
3. Run the document checks.
**Verification:** `doccheck`, `refcheck`, `wb run code-work check`, `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-levels-for-the-review-workflow#G`.

## Verification for the plan as a whole

`python3 -B -W error tests/run_all.py` from a scratch copy (about 6 to 10 minutes, in the background), `wb check`, `wb run code-work
check`, `doccheck` and `refcheck`. Then, by the owner at a terminal and not by an agent: `wb acknowledge`, `wb upgrade`, an edit of
`levels` in the personal settings, `wb preview rerender` and `wb rerender`. Last, one real `extend` at `ask` in this clone, run with
the digest the preview printed, and the log's two lines for it.

## Risks and sensitive actions

- **A trust boundary.** The launcher and a helper decide whether an agent may run something the owner reserved. A flaw here lets an
  agent change or delete a review record. Mitigations: the digest binds the exact review state; the compare happens under the lock;
  the rendering must be current; every path writes an outcome line. The owner is asked whether to run a security review after D.
- **A change to the module contract.** Installed projects with the old declaration keep working only if a declaration without the
  field behaves exactly as before; Increment C tests that.
- **First-party package edits** change the module's hash and stop the command gate until the owner runs `release-approvals`.
- **A digest the owner cannot read.** At `ask` the harness prompt shows the command and the digest, not the preview, as for
  `approve-plan` (`command-permissions.md`, "`approve-plan` at `ask` and `none`"). The agent must show the preview in the
  conversation first, and no code enforces that.
- **Nothing takes effect without a terminal step.** Rendering a level needs `wb rerender`. A person away from a terminal cannot
  turn this on; it has to be finished before they leave.
- **Irreversible actions.** `archive` and `prune` close and delete reviews. Tests run on scratch copies only; a real `prune` is run
  once, by the owner, at the end.

## Review record

Round 1, 2026-10-27, by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium), asked for by the
owner. Verdict: changes needed, one finding.

- **R1-F1 (major), applied.** The plan left every spec edit to Increment G, so `module-contract.md` (whose schema rejects an unknown
  field) would have been wrong after Increment C. Increments C, D, E and F now each update the spec they change, and G only
  consolidates.

One round of three was used. No second round was asked for: the finding was applied without a change of design. The review is not an
approval; the plan stays `Proposed` until the owner approves it.

## Deferred work

- `ask` for the installer commands that block remote work: `upgrade`, `add`, `acknowledge` and the accept-decision checkpoint, and for
  `submit-remote-job`, `push-shared-branch`. Each needs its own preview digest (`command-permissions.md`, "Not built").
- A `wb accept-decision` command, if the owner wants an agent to accept a decision at `ask`.
- The same field for `mempalace init` and `mine` and `remote-runner fetch-overwrite`.
- The rule that a command reaching more than one key takes the strictest level.

## Result

### Increment A — committed as 32ac021 (2026-10-27)

- **Done.** `docs/specs/command-permissions.md` has a new section, "The planning workflow without a terminal", before "Not built": a
  table of 19 actions in drafting, reviewing and approving (shipped level, the owner's level where it differs, whether a terminal is
  needed, what can block), the preconditions that make a relaxed level hold, and a list of what the map shows. Where a row has no key
  it says so (approving a roadmap, spec or design). The plan's status line is `In Progress`.
- **Verification run.** `wb settings`: every `level` line compared with its row, twice (at the start and after the edits);
  `wb run code-work check` (54 plans, no problems); `doccheck` and `refcheck` (silent); `git diff --check` (clean);
  `wb plan-status` (`approved`, unchanged); `wb check` (no problems, so the rendering is current today). Nothing owner-run was run.
- **Review.** One `reviewer` exchange of six. Seven findings, all applied: (1) blocking, the checkpoint `change-direction` had no row;
  (2) blocking, the `ask`, `delegated` and `none` rows omitted that they hold only once set and rendered, and the shipped and the
  owner's levels were mixed; (3) the accept-decision row now says the rule is guidance and not enforced; (4) the draft row names the
  commands each skill runs; (5) a note for `evaluate-findings`, re-approval of an edited plan and the skills outside the flow; (6) the
  `delegated` row names its further preconditions and marks its last clause an inference; (7) the section states that the code makes
  the terminal test in the launcher while the spec says the helper.
- **Found, not fixed.** The `draft-decision` skill rendered in this clone (`.claude/skills/draft-decision/SKILL.md`) is older than the
  packaged one: it says never to accept a record and has no `wb settings` route, while the package accepts at `accept-decision:
  none`. Refreshing it is the owner's `wb upgrade` and re-render; this increment did not touch it.
- **Not done.** Nothing in code. No owner-run command was run.

### Increment B — committed as ffeb43d (2026-10-27)

- **Done.** `docs/decisions/2026-10-27-owner-run-arguments-take-a-level.md`, status `Proposed`, and its row in
  `docs/decisions/README.md`. It decides: the launcher stays the one place that reads the terminal and the level (the helper has no
  terminal test, so the spec text is wrong); a `levels` field on a command (`ask` and `none`, never `delegated`) and a `preview`
  field naming a non-owner-run argument; the helper checks the digest inside its lock and the launcher requires it; the log attempt
  and outcome are written by the launcher; `none` is offered; `wb launch` stays terminal-only; the effect on the declaration hash.
- **Verification run.** `doccheck` and `refcheck` (silent), `git diff --check` (clean), `wb plan-status` (`approved`). No code and no
  test, because this increment is a document.
- **Review.** One `reviewer` exchange of six. Five findings: (1) blocking, `wb launch` has no `ask` rule, so a digest through
  that route would skip the prompt: applied (decision 7, launch stays terminal-only); (2) `launch.launch` prepares and starts the
  helper in one function, so the log attempt needs a change to `workbench/launch.py`: applied in the record (Increment D already
  lists that file, so the plan needs no edit); (3) what the digest binds and how `--digest` is parsed: applied
  (decision 8); (4) `ask` inherits the spelling limit: applied (decision 9, a recommendation to keep `prune` and `reset` at `block`);
  (5) evidence wording: confirmed, no change.
- **Not done.** Accepting the decision was the owner's act, made by the owner's edit of the record's status line and its index row on
  2026-10-27, before this commit; the agent wrote it `Proposed`.

### Increment C — committed as f1ef6cc (2026-10-27)

- **Done.** `workbench/declarations.py`: `Command` gains `levels` (`((argument, (level, ...)), ...)`) and `preview`, both defaulted
  so older constructions are unchanged; `_argument_levels` refuses a non-object, a key that is not an `owner` argument, an empty or
  non-list value, a level other than `ask` or `none` (`delegated` named in the message), a repeated level, `ask` without `preview`,
  `preview` without `ask`, and a `preview` that is not a declared argument, is owner-run, or is `describe`. `workbench/levels.py`:
  `_key` offers the declared levels after `block` and `registry` reads them from a fourth item of a command's tuple (only for an
  `owner` argument; the default stays `block`). `rendering.py`, `harnessstage.py` and `settingscmd.py` pass `command.levels`.
  `settings.py` and `levels.py` docstrings updated. Specs: `module-contract.md` (the two fields) and `command-permissions.md` (the
  offer, the not-yet-built launcher, the corrected "Not built" text that the terminal test is the launcher's).
  Tests: `tests/test_owner_argument_levels.py`, 29 tests.
- **Verification run.** The 29 new tests pass (`python3 -B -W error -m unittest tests.test_owner_argument_levels`). Against a scratch
  copy of HEAD's code, 13 of the first 25 failed and 5 errored; the rest pin behaviour that does not change. With the three callers
  reverted in a scratch copy, 2 of the 3 caller tests fail. `git diff --check`, `doccheck`, `refcheck`, `wb check` and
  `wb run code-work check` are clean. Full suite (`python3 -B -W error tests/run_all.py`, scratch copy of the final tree): 5710
  tests in 11 roots; one failure, the known intermittent `test_levellog.ConcurrencyTest.test_parallel_appends_keep_every_line`
  (a race creating `level-log`; it failed 3 of 8 runs on HEAD's code and 4 of 8 on this tree; this increment does not touch
  that code). Every other root passed.
- **Review.** One `reviewer` exchange of six, no blocking finding, four non-blocking, all applied: (1) `_key` built its offers from
  `LEVELS` and would offer `delegated` to a hand-built `Command`: now only `ask` and `none`, with a test; (2) no test went through
  the callers: `ThroughTheInstalledModule` runs `wb settings` and `current_table` on an installed module; (3) the hash tests compared
  two parses of one input: replaced by a check that a declaration without the fields carries no trace of them (the hash covers the
  declaration as written); (4) stale text in `settings.py` and one overstated sentence in `command-permissions.md`.
- **Not done.** Nothing takes effect yet: the launcher (Increment D) still refuses an owner-run argument without a terminal, and no
  first-party module declares the field. Not committed.

### Increment D — committed as dc7c17d (2026-10-28)

- **Done.** New `workbench/ownerargs.py`: `permit` lets `wb run` start an owner-run argument without a terminal only when the
  declaration gives that argument a level, `levelrun.level_now` reads the key `wb run <command> <argument>` at a level the
  declaration offers (so the record, table, permissions file and gate agree), the project and root match the request, and, at `ask`,
  the last two arguments are `--digest` and 32 lowercase hex; anything else refuses with today's terminal text. `run_logged` starts
  the helper with the arguments unchanged between an attempt line (`digest:<hex>` at `ask`) and an outcome line (`done`, or
  `refused` with the exit code or the exception). `launch.launch` gained a `before` callback, called after the pin and bytes are
  checked and the copy is written and just before the helper starts; if it raises, no helper starts. `commands.Request` carries
  `levels` and `preview`; `commands.run` imports `ownerargs` at call time because `levelrun` reaches `commands` through
  `approvalcmd`. `wb launch` is unchanged and stays terminal-only. Specs: `command-permissions.md` and `module-contract.md`.
  Tests: `tests/test_owner_argument_run.py`, 25 tests.
- **Verification run.** On the code before the change, the first 23 tests gave 18 failures and 1 error (the rest pin unchanged
  refusals). With the change all 25 pass, with `tests.test_run` and `tests.test_owner_run_code` (78 tests). `git diff --check`,
  `wb check`, `wb run code-work check`, `doccheck` and `refcheck` are clean. Full suite (`python3 -B -W error tests/run_all.py`,
  scratch copy taken before the last two tests and one spec sentence were added): 5733 tests in 11 roots, all OK. This run did not
  hit the known `levellog` flake.
- **Review.** One `reviewer` exchange of six (one used for B, one for C; this is the third, so three of six in all), no blocking
  finding, four non-blocking: (1) exit code 3 means both "outcome not logged" and a helper that exits 3: stated in the spec;
  (2) an interrupt between `levellog.begin` returning and the id being kept leaves an attempt with no outcome: accepted, the log's
  "unfinished" convention covers it; (3) missing tests: added a subdirectory run, a start failure after the attempt, and an exact
  outcome reason; the `--provides` form and a project or root mismatch have no test (the code paths are shared with the tested ones);
  (4) the spec lines read match the code.
- **Not done.** Nothing takes effect: no first-party module declares `levels`, and the helper does not yet check a digest
  (Increments E and F). Security review: a trust boundary changed (who may run an owner-run argument, and how a digest binds it);
  the owner asked for one on 2026-10-28 and a `security-reviewer` ran it on a scratch copy: no Critical, High or Medium finding;
  fail-closed on every exception path, the level is read for the launched project, the attempt precedes the helper and an outcome
  follows on every path, and `wb launch`, `wbkit.call` and `launch_captured` do not reach an owner-run argument. Four Low
  findings, none changed in this increment: (1) at `none` a looping agent can fill the 4 MiB level log, after which every run
  above `block` refuses until the owner rotates it (the same exposure as the other `none` keys); (2) exit code 3 is ambiguous
  (stated in the spec); (3) at `ask` the launcher proves only the digest's form, because the agent can run the preview itself, so
  the real checks are the harness prompt and the helper's recomputation (Increment E); (4) a helper runs with the caller's
  environment, as before. Outside this increment, read and not tested: `commands.launch_refusal` does not check that a
  `--root` belongs to the pinned project when the pin was typed by the owner (no declaration to compare); this predates D and is
  left to the owner to decide.

### Increment E — landed, not committed (2026-10-28)

- **Done.** In a scratch copy, then landed with `cp` into `packages/workbench/review-engine`: the helper gains `preview extend
  <document> <n>` (read-only, no lock: it prints the lines of the extension and ends with `digest: <32 hex>`, the first 32
  characters of the SHA-256 of those lines), and `extend <document> <n> --digest <hex>`: `run` strips a trailing `--digest <hex>`
  for `extend` only (a digest of another shape is refused before anything is read; a `--digest` elsewhere fails the count), and
  `extend`'s `make` recomputes the digest inside the lock, on the state about to be written, and compares it with
  `hmac.compare_digest`; a mismatch changes nothing. The digest binds the document and kind, the review key, the generation (every
  save raises it), the rounds and the window, the bound now, the number and the bound after. `module.json` adds the argument
  `preview`, `levels: {extend: [ask, none]}` and `preview: "preview"`; the skill gains one sentence on `preview`. `reset`, `archive`,
  `amend`, `decide` and `prune` take no digest yet (Increment F). Spec: `review-engine.md` (the table, the argument list and a
  paragraph "`extend` at a level"). Tests: `tests/test_review_digest.py` (24 tests) and two in `test_review_module.py`.
- **Verification run (scratch copy).** On the old helper 18 of the first 22 digest tests failed (the rest pin unchanged refusals).
  With the change the review-engine tests give 348 OK (`PYTHONPATH=. python3 -B -W error -m unittest discover -s
  packages/workbench/review-engine/tests -t packages/workbench/review-engine/tests`), again after the review fixes. Full suite
  (`python3 -B -W error tests/run_all.py`, scratch copy before the review fixes): 5758 tests in 11 roots; one failure, the known
  `test_levellog.ConcurrencyTest.test_parallel_appends_keep_every_line` flake; every other root passed, the review-engine root
  with 348.
- **Review.** One `reviewer` exchange (four of six in all), no blocking finding, four non-blocking: (1) the helper's docstring
  still said every command prints one JSON object: fixed; (2) the no-write test could not see a lock or directory created by
  `preview`: it now makes the lock raise; (3) a test name overclaimed: it now also covers an unsealed and a rolled-back review;
  (4) the skill names `preview extend <document> <n>` without `wb run review-engine`, because the module test restricts that
  spelling to the four commands the agent runs: left as is.
- **Not done, owner's steps.** After the landing the command gate refuses every Bash call until the owner runs
  `release-approvals`; then `wb acknowledge` and `wb upgrade` for this clone (the declaration hash changed), and, to use the level,
  an edit of the personal settings (`wb run review-engine extend: ask`) and `wb rerender`. Not changed here: the "Not built" items
  of `command-permissions.md` for `extend` (Increment G consolidates). No security review has been run for E.
