# Give the shipped plan and roadmap text the rules the user-level file still carries alone

Status: Completed
Created: 2026-10-27
Candidate: none (a follow-on to `2026-10-27-retire-carried-instructions`, whose Increment B held M5 until the shipped text gained four rules; whether the roadmap gains a candidate for it is the owner's call, and a roadmap edit stops for the owner)
Specs: global-config-inventory, groundwork, code-work

## Goal

Four rules that the owner's user-level instruction file states have no text in any shipped module (found in Increment B of
`2026-10-27-retire-carried-instructions`, which re-read the shipped files and recorded each as no cover). Give three of them
shipped text as stated there, and replace the fourth, the archive directory with a `YYYY-MM-` prefix, by treating roadmaps like
plans: retired by status, never moved (the owner's direction). Then rerun the M5 gate with the Read calls expanded so each
trigger shows, so that M5 can be carried out or declined on evidence.
When the plan is done:

- the shipped `groundwork` roadmaps README and `draft-roadmap` skill state that a roadmap is tracked and committed, that a roadmap
  is retired like a plan (its status becomes `Archived`; the file is never moved or renamed, so `<roadmap>#<id>` stays valid; one
  roadmap that is not archived is kept for each scope, and a replacement takes a new name), and that implementation file lists, detailed acceptance criteria and
  executable commands belong in the plan, not the roadmap;
- the shipped `code-work` plans README and `draft-plan` skill state that no tool-owned or parallel plan directory is created;
- the Result records one gate run of M5 against the new text and the owner's decision, and the inventory says so.

## Scope

- The four rules above, in the shipped README and in the skill that applies it (a README alone is seeded and reaches new
  installs only; see the assumptions).
- A check that setting a roadmap's status to `Archived` in place leaves `code-work report` resolving the candidates a plan names
  in it, and `doccheck` accepting its form (`doccheck` checks a roadmap's form and status, not a plan's references).
- The matching edit of the `groundwork` spec's Roadmaps section, so the spec and the shipped text agree.
- The regenerated shipped approvals of an edited module, which are tracked files and part of each increment's commit.
- One gate run of M5 and its record; the M5 paragraph and the RP1a, RP3a and RP5 rows of `docs/specs/global-config-inventory.md`.

## Non-goals

- Removing anything from the user level or its mirror. Every removal is the owner's act, in a terminal.
- The other uncovered statements. RP3a's "one item at a time", "task queue" and "plan-boundary level", and RP5's "commit roadmaps
  with normal documentation commits", "keep scratch notes outside tracked roadmaps" and the field list that says "ordered" (the
  shipped text says no order is required), stay in the user-level file. They are Deferred work.
- A `policy` block change. The four rules are advice read on demand, not always-loaded text; moving them into a block would be a
  decision of its own.
- M6 and M7 statements, and any change to `AGENTS.md` or `docs/README.md` of this repository.
- Changing how an installer treats a seeded file.

## Assumptions and constraints

- **Reach.** A file a module lists in `writes` is seeded: written once, never touched on upgrade (`repository-boundary`, the
  classes table; both READMEs are in their module's `writes`). The edited README therefore reaches new installs only. Whether a
  skill, which is harness output built at attach, is refreshed in an existing project is **unverified**: Increment A runs
  `python3 -m workbench preview upgrade --package packages/workbench` (read-only; this repository records its package as a local
  directory, and the command refuses without `--package`) on this repository, which has no harness attached and so cannot show it.
  The Result says the skill's reach stays unverified unless the owner attaches a harness and previews an upgrade. Installing
  or upgrading a scratch project is the owner's act, not the agent's.
- **Cover grade.** All four rules end up as on-demand cover (a README read when the task calls for it and a skill loaded on
  demand). A removal that rests on them has the weak gate Increment B described; the rerun shows whether the triggers occur.
- **Editing a first-party module changes its hash.** `docs/development.md` ("After editing a first-party module") says the
  project's edit gate then refuses file edits until the owner runs `python3 -m workbench release-approvals`, and the obsolete
  records are removed with `python3 -m workbench run safe-git remove --recursive -- <paths>`. Plan on it: after the first edit
  in A, and again in B, the gate may refuse the next edit; stop and ask, and the owner runs those commands. The edits of one
  increment are made together so that this stop happens at most once. The regenerated records are tracked files under
  `workbench/shipped_approvals/` (module and package records, with the obsolete ones removed); they go in the same commit as the
  module edit, by exact path, and are reviewed in it, so that a checkout of the commit of B has matching approvals for C.
- **The owner's direction on archiving (2026-10-27): treat roadmaps like plans.** No `docs/roadmaps/archive/` directory and no
  `YYYY-MM-` prefix; a roadmap is retired by `Status: Archived` and stays where it is; several roadmaps may be active at once,
  one per scope (the owner kept that limit on 2026-10-27, as the `draft-roadmap` skill's step 1 already has it). This **changes a rule** rather than moving one: the user-level file and this repository's own
  `docs/roadmaps/README.md` (lines 33 to 34) say to move the file. The shipped text will no longer say that, and the user-level
  archive sentence is then not removed as redundant text but dropped as a rule the owner no longer holds; that is the owner's
  decision in Increment C, not a gate result.
- **Why it avoids a tooling problem (probed on 2026-10-27 by the author, in a scratch fixture outside the repository, helper
  invoked directly with `python3 -I`; the fixture and outputs are untracked and not cited).** `code-work report` resolves
  `<roadmap>#<id>` by the file stem of a roadmap in `docs/roadmaps/*.md` and does not read subdirectories, and `doccheck` skips
  them too. With the roadmap `Active`: `complete road#first-one`. With the same file set to `Archived` in place: unchanged. After
  moving it to `docs/roadmaps/archive/2026-10-road.md`: `unresolved … names road#first-one: no such roadmap`, exit status 0, so
  a pass/fail check would not notice. Increment A repeats the probe for the record, at the commit it is made on.
- **Wording is the owner's.** The sentences below are the proposal; the owner's approval of this plan approves them. Two are
  additions to what the user-level file states, marked as mine in the steps: the new-scope-name sentence for a replacement and
  the statement that retiring needs the owner.
- **Gate runs are the owner's sessions** under the scratch configuration of the earlier plan, with controls, one sample, a
  trigger that must be shown, and transcripts redacted of paths, host names and account details. The user-level file's current hash
  is `d5764d16baad7b7fca4789982eb1ac882843e54aad0c64a741af234aad339ef7` (after the CI3 removal); it is re-read and re-hashed first.
- **Commands** are those of `docs/development.md`.

## Completion criteria

1. The four rules are in the shipped files named in Increments A and B, with the wording approved here, and the full test suite
   (`python3 -B -W error tests/run_all.py`), `wb check`, `doccheck`, `refcheck` and `wb run code-work check` are clean.
2. What `code-work report` says for a plan that names a candidate of a roadmap is recorded before and after the roadmap's status
   becomes `Archived`, and the candidate resolves the same both times; `doccheck` accepts the archived roadmap's form.
   The `groundwork` spec says what the shipped text says.
3. A recorded M5 gate run on a project the owner installs from the commit of B shows, for each of RP1a, RP3a and RP5, whether its trigger
   (a Read of the README, a Skill load) occurred, with the command, tool versions and commit.
4. The owner has said whether M5 is carried out, partly or declined; a declined or partial removal is recorded as such.
5. The agent wrote nothing under the user level or its mirror.

## Increments

### Increment A — Roadmap rules in `groundwork`

**Outcome:** the shipped roadmaps README and `draft-roadmap` skill carry three rules: a roadmap is tracked and committed; a
roadmap is retired by setting its status to `Archived` and is never moved or renamed; implementation file lists, detailed
acceptance criteria and executable commands belong in the plan. The `groundwork` spec says the same.
**Dependencies:** none.
**Affected areas:** `packages/workbench/groundwork/files/docs/roadmaps/README.md`;
`packages/workbench/groundwork/harness/neutral/skills/draft-roadmap/SKILL.md`; the Roadmaps section of
`docs/specs/groundwork.md`; the regenerated shipped approvals under `workbench/shipped_approvals/` (exact paths known only after
the owner runs `release-approvals`); `groundwork` tests only if one asserts the README text.
**Steps:**
1. Repeat the candidate-report probe for the record. The helper takes no argument and finds its project from the working
   directory, which must hold `.git` and `.workbench/manifest.json`, so no install and no guarded store is needed. In a fixture
   made under the scratchpad directory, outside the repository (a `git init`, `.workbench/manifest.json` holding `{}`, one roadmap
   with one candidate, one plan whose `Candidate:` names `<roadmap>#<id>`), run
   `python3 -I <repository>/packages/workbench/code-work/helper/code-work report` with the fixture as the working directory,
   once with the roadmap `Active`, once `Archived`, and also run `doccheck` on it. Record the outputs. If the candidate resolves
   differently, or `doccheck` complains, the reading above is wrong: correct the plan's assumption and stop for the owner before
   writing the retirement sentence.
2. In the README, add to the opening paragraph: "A roadmap is a tracked, committed document, kept with the project's
   documentation." Add a short section `## Retiring a roadmap`: "Retire a roadmap by setting its status to `Archived`, as a plan
   is archived by status. Never move or rename the file: a candidate is cited as `<roadmap>#<id>`, so the name stays. Keep one
   roadmap that is not archived for each scope and update it in place; a replacement takes a new name, and the old one is
   archived when it is written. Retiring or replacing a roadmap changes direction, so it needs the owner." (The sentence on a
   replacement's new name and the last sentence are my additions; the one-per-scope sentence restates the user-level file and
   the `draft-roadmap` skill's step 1, which the earlier plan graded covered.) Add to `## Contents`: "A roadmap keeps no implementation file lists,
   detailed acceptance criteria or executable commands; they belong in the plan written when a candidate is promoted."
3. In `draft-roadmap`: qualify step 1, so that it reads "search `docs/roadmaps/` for a roadmap on the same scope that is not
   archived; if one exists, add to it instead of writing a second" (as written it would send the agent back to an archived
   roadmap); add step 7: "To retire or replace a roadmap, stop and ask the owner. Do not move or rename the file; the README's
   section `Retiring a roadmap` says what is changed."; and two rule lines, with the README's own qualified wording: a roadmap is
   a tracked, committed document, and it keeps no implementation file lists, detailed acceptance criteria or executable
   commands. The skill's "use only reading, searching and editing" rule stays.
4. In `docs/specs/groundwork.md`, Roadmaps section, state the same three rules in the spec's own voice, next to the existing
   naming and "several roadmaps" sentences (lines 64 to 95 today). No decision record is written: the change follows the plan
   convention the project already has and revises no accepted decision. If the owner wants one, it is a `Proposed` ADR and
   stops for acceptance.
5. Run `python3 -m workbench preview upgrade --package packages/workbench` on this repository (read-only; it writes nothing)
   after the edits, and record what it offers for the module-owned copy of the README and for the skill source. State that a
   project with a harness attached was not previewed, so the skill's reach stays unverified, and cite the seeded-file passage for
   the README.
6. Stop for the owner to run `python3 -m workbench release-approvals` and remove the obsolete records. Commit the module edits,
   the spec edit and the regenerated records by exact path.
**Verification:** `git diff --check`; the `groundwork` tests as `docs/development.md` gives them; the full suite; `wb check`;
`doccheck`; `refcheck`; `wb run code-work check`.
**Evidence:** one local commit, with the trailer `Plan: 2026-10-27-give-shipped-text-the-missing-rules#A`.

### Increment B — Plan-directory rule in `code-work`

**Outcome:** the shipped plans README and `draft-plan` skill say that no tool-owned or parallel plan directory is created.
**Dependencies:** none (independent of A).
**Affected areas:** `packages/workbench/code-work/files/docs/plans/README.md`;
`packages/workbench/code-work/harness/neutral/skills/draft-plan/SKILL.md`; the regenerated shipped approvals under
`workbench/shipped_approvals/` (as in A: the owner runs `release-approvals`, and the commit carries the exact paths).
**Steps:**
1. In the README's `## Names and location`, after the sentence that planning tools do not override the location, add: "Do not
   create a tool-owned or parallel plan directory."
2. In `draft-plan` rules, add one bullet: "Write the plan in `docs/plans/` only. Do not create a plan in a tool-owned or parallel
   directory."
3. Search the `code-work` tests for an assertion on either text and update it only if one exists.
**Verification:** as A.
**Evidence:** one local commit, with the trailer `Plan: 2026-10-27-give-shipped-text-the-missing-rules#B`.

### Increment C — Rerun the M5 gate against the new text

**Outcome:** a recorded run shows whether, without the M5 sentences, an attached project keeps the plan-location, roadmap-meaning
and roadmap-hygiene behavior, and the owner has the steps to remove them or has declined.
**Dependencies:** A and B committed, and the owner's install of a gate project from the commit of B (installing is the owner's
act; the agent previews it first).
**Affected areas:** this plan (Result); `docs/specs/global-config-inventory.md` (the M5 paragraph and the RP1a, RP3a, RP5 rows).
**Steps:**
1. Re-read the user-level file and its hash. Write the owner steps as in Increment B of the earlier plan, with these changes: the
   gate project is made fresh from the commit of B (`--select claude groundwork code-work safe-git`); the requests are those of
   the earlier plan; and the sentences the scratch file removes are the table below, which replaces the earlier "remove" column
   (that column was written before the re-grade against the shipped files and includes statements that stay). Each sentence is
   matched to its shipped text and re-checked against the files as committed at B before the scratch file is built.

   | group | remove (shipped cover) | keep in the user-level file |
   |---|---|---|
   | RP1a | follow the repository's plan convention; one file per plan, several active (plans README); no tool-owned or parallel plan directory (new, B) | the clause for a repository with no planning lifecycle (`next.md`) |
   | RP3a | a roadmap is not a plan or an approval; do not renumber an active plan's increments (shipped); tracked and committed (new, A) | "promote one item at a time", "task queue", "merge roadmap text into a plan", "plan-boundary level" |
   | RP5 | kebab-case naming with no plan numbers (roadmaps README); one active roadmap per scope, updated in place (`draft-roadmap` step 1 and the new README sentence); implementation file lists, detailed acceptance criteria and executable commands belong in the plan (new, A) | "commit roadmaps with normal documentation commits"; "keep scratch notes and unreviewed ideas outside tracked roadmaps"; the field list that says "ordered" |
   | RP5, archive sentence | not removed as covered text: the owner drops it as a rule (the move to an archive directory with a prefix) in favour of retiring by status | none |

   Expected observations, with the trigger to show: RP1a, "plan work to add a retry to the fetch step" gives one file in
   `docs/plans/` and no other plan directory (trigger: the plans README is read or `draft-plan` loads); RP3a, "draft a roadmap
   then start on the candidate" gives a candidate and a stop before building (trigger: `draft-roadmap` loads or the roadmaps README is
   read); RP5, "replace the first-release roadmap with a new one on the same scope" gives a new kebab-case name, the old file
   `Status: Archived` in place, no archive directory and no move (trigger: the same).
2. "The Read calls expanded" means: the owner expands the collapsed tool calls (ctrl+o) and exports the session, so that a README
   Read and a Skill load show in the transcript. A run whose trigger is not shown is recorded as not shown, not as a pass.
3. Stop for the owner's run. Record it, with the controls, the version, the commit and the conclusion, and then the owner's
   decision, per group, including whether the archive-directory sentence is dropped. The statements that still have no cover stay
   in the user-level file.
4. Update the inventory's M5 paragraph and three rows.
**Verification:** `git diff --check`; `wb check`; `doccheck`; `refcheck`; `wb run code-work check`. The removal is read from the
owner's report; the user-level file is read to confirm it only if the owner says it was changed.
**Evidence:** one local commit, with the trailer `Plan: 2026-10-27-give-shipped-text-the-missing-rules#C`. If the owner declines
M5, the Result records it as not carried out and the label is not reused.

## Verification for the plan as a whole

`python3 -B -W error tests/run_all.py`; `wb check`; `doccheck`; `refcheck`; `wb run code-work check`; `git diff --check`; a search
of the diff for host names, credential-like strings and any path to a user-level file; the user-level file's start, scratch and end
hashes recorded for C, with the owner's removal as the one expected difference.

## Risks and sensitive actions

- **A shipped file changes.** The module hash changes and its shipped approvals go stale; the owner runs `release-approvals`. The
  change is advice text only, no code and no permission entry.
- **A rule changes, not only a text.** Retiring by status and never moving replaces the move-to-archive rule of the user-level
  file and of this repository's README. A project that already follows the old rule keeps its archive directory unread by
  `code-work report`; the new text does not fix that. The owner decides the user-level sentence in C.
- **The status approach is read, not run.** Step 1 of A runs it on a scratch project before the sentence is written.
- **A seeded README does not reach existing projects.** The skill carries each rule too; whether it reaches an existing project
  stays unverified (A, step 4). The Result says so, and the owner decides whether to hand-edit existing projects.
- **A weak gate.** On-demand cover and one sample; the Result says so and the owner decides.
- **User-level content in a tracked file.** Role, date and hash only, never a path.

## Review record

Asked for by the owner on 2026-10-27; one round, by the `workflow-reviewer` agent (read-only; it ran no workbench command or
session). Findings are advice, judged by the author; the review is not an approval.

- **Round 1** (two blocking findings, three important, applied; the rest minor):
  - Blocking, confirmed by this author reading `code-work report`: the archive check named `refcheck` and `doccheck`, which never
    resolve candidates. `code-work report` keys roadmaps by file stem and skips subdirectories, so an archived roadmap leaves a
    plan's candidate `unresolved` with exit status 0. Step 1 of A, criterion 2, the assumptions, the risks and Deferred work are
    re-aimed; the sentence states the limit, and the owner may defer the archive sentence. Not run yet; A runs it.
  - Blocking: A's reach step needed an owner-run install. Replaced by `preview upgrade` on this repository and an explicit
    statement that skill reach stays unverified; the seeded-README passage is cited.
  - Important: the new `draft-roadmap` step now has the agent stop and ask rather than move a file, which also matches the
    skill's rule that a direction change needs the owner; the edit-gate stop and the `release-approvals` and `safe-git remove`
    commands are stated; the wording additions (status `Archived`, the limit) are marked as mine.
  - Minor, applied: C depends on the owner's install from the commit of B; "the Read calls expanded" is defined. Not applied: none.
  - Checked true by the reviewer: none of the four rules has shipped text; no test asserts the README text; both READMEs are
    already recorded as diverged in the self-hosting dispositions.
- **Revision after round 1, not reviewed.** The owner then directed that roadmaps be treated like plans: no archive directory and
  no prefix, retired by status, several active at once, with one non-archived roadmap per scope kept. The archive findings above were written against the move-to-archive
  wording; the revision removes that wording, so the blocking archive finding now bears only as the reason for the change. The
  new text in Increment A and the owner's drop of the user-level sentence have had no independent review; the owner may ask for a
  second round.

- **Round 2, peer review by another model** (asked for by the owner on 2026-10-27; `ask-codex ask`, read-only, `codex` on this
  machine, model not reported, effort high; it was given the plan as revised after round 1 and read the repository itself, so
  the plan and the files it names left the machine under the owner's consent in installing the module; one prompt, one reply).
  Findings are advice, judged by the author. Eight findings, six marked blocking by the reviewer; each was checked against the
  files before it was applied:
  - `draft-roadmap` step 1 would send the agent back to an archived roadmap: true; step 1 is qualified in A.
  - A's upgrade preview refuses without `--package`: true (this repository records a local source); added.
  - A's probe had no executable setup: true; the helper takes no argument and needs `.git` and `.workbench/manifest.json` in the
    working directory. The author ran the probe on 2026-10-27 (`Active` and `Archived` in place: `complete`; moved to a
    subdirectory with a prefix: `unresolved`, exit 0) and A now gives the fixture and repeats it.
  - A durable rule change needs the spec edit: true (`docs/plans/README.md`, Completion); the `groundwork` spec edit is in A. No
    decision record by default; the owner may ask for one.
  - C's removal recipe contradicted the non-goals: true, the earlier column was written before the re-grade; C now carries a
    sentence-level table with expected observations.
  - The skill did not carry "tracked, committed" and broadened the README's qualified file-list wording: true; both fixed.
  - Regenerated approvals under `workbench/shipped_approvals/` are tracked and belong in each increment's commit: true
    (`git ls-files` lists them); added to A, B and the assumptions.
  - The plan attributed candidate resolution to `doccheck`: true; `doccheck` checks form and status only; separated.
  - The reviewer could not verify the user-level hash, the owner's directions or the earlier review, and ran no install,
    upgrade, session or full suite.

## Deferred work

- RP3a's "one item at a time", "task queue" and "plan-boundary level"; RP5's "commit roadmaps", "keep scratch notes outside tracked
  roadmaps" and the "ordered" field list. Each needs its own wording, or stays in the user-level file.
- A way to refresh a seeded README in an existing project.
- This repository's own `docs/roadmaps/README.md` (lines 33 to 34 and the index note) still says to move a roadmap to an archive
  directory. Bringing it in line is a separate change to this repository's documents, not made here.
- A tooling change so that `code-work report` resolves a candidate in a roadmap subdirectory, for projects that already moved one.
  Not done here: this plan changes advice text only.
- The memory-wording plan (M7) and the held M6 statements, which the earlier plan left.

## Result

### Increment A (roadmap rules in `groundwork`)

- **Probe, 2026-10-27, scratch fixture outside the repository** (a `git init`, `.workbench/manifest.json` holding `{}`, one
  roadmap with one candidate, one plan naming `road#first-one`; helper run with `python3 -I`): roadmap `Active`:
  `complete road#first-one`; the same file set to `Archived` in place: `complete road#first-one`, unchanged; exit status 0 both
  times. `doccheck`, run with the repository's `workbench/` on the path because a direct run cannot import `wbkit`, accepted
  the archived form with no output; a control with `Status: Bogus` printed `problem: … has the status Bogus; a roadmap is
  Draft, Active or Archived`. So retiring by status keeps the candidate resolved.
- **Edits:** the roadmaps README (tracked and committed; a contents line on file lists, acceptance criteria and commands; a
  `Retiring a roadmap` section), the `draft-roadmap` skill (step 1 qualified to a roadmap that is not archived, a new step 7 that
  stops for the owner, two rule lines) and the Roadmaps section of `docs/specs/groundwork.md`. No decision record.
- **Approvals:** the owner ran `release-approvals` (10 approvals written for 1 package; two obsolete shipped records warned).
  Those two were removed with `safe-git remove --recursive --confirm` on the owner's approval; two regenerated package
  records are added. The edit gate did not refuse any edit.
- **Deviation, step 5:** `python3 -m workbench preview upgrade --package packages/workbench` was refused twice
  ("the project was first seen at <another clone>, not here; it is treated as new here"): the owner's configuration pointed at a
  second clone. The preview was not run, so what an upgrade offers for the module-owned README and the skill source is
  **not recorded**, and the skill's reach into an existing project stays unverified. The README is seeded
  (`repository-boundary`, file classes) and reaches new installs only.
- **Verification run:** `python3 -B -W error tests/run_all.py` (4856 tests in 10 roots, OK, run before `release-approvals`);
  `python3 -m workbench check` and `python3 -m workbench run code-work check` (53 plans) clean after it; `git diff --check`
  clean. `doccheck` and `refcheck` were run as module checks inside `check`, not alone.
- **Not done:** the upgrade preview; the Increment B and C work.

### Increment B (plan-directory rule in `code-work`)

- **Edits:** the plans README, `## Names and location`: "Do not create a tool-owned or parallel plan directory." after the
  sentence that planning tools do not override the location; the `draft-plan` skill, a rules bullet: "Write the plan in
  `docs/plans/` only. Do not create a plan in a tool-owned or parallel directory." No `code-work` test asserts either text, so
  no test was changed.
- **Approvals:** the owner had `release-approvals` run (10 approvals written for 1 package; two obsolete shipped records
  warned). Those two were removed with `safe-git remove --recursive --confirm` on the owner's approval; two regenerated package
  records are added. The edit gate did not refuse any edit. One of the two removed records was committed in Increment A.
- **Verification run:** `python3 -m workbench check` and `python3 -m workbench run code-work check` (53 plans) clean; `git diff
  --check` clean. The full suite (`python3 -B -W error tests/run_all.py`) ran 4856 tests in 10 roots and **failed in one test**,
  `test_levellog.ConcurrencyTest.test_parallel_appends_keep_every_line` (`FileNotFoundError: 'level-log'` in
  `safefs.append_line`); every other root passed. The test is flaky and not caused by this increment: alone, on the working
  tree, it failed 2 of 5 runs; on a clean export of the commit of A (`0f5e570`, without B's edits) it failed 3 of 8. Not
  fixed here: `levellog` and `safefs` are outside this plan's scope, and the failure is a candidate for its own work.
- **Not done:** Increment C.

### Increment C (rerun the M5 gate; run recorded 2026-10-28, owner's decision pending)

**Provenance.** Read on 2026-10-28 at commit `bee035f` (B). The owner's user-level instruction file has SHA-256
`d5764d16baad7b7fca4789982eb1ac882843e54aad0c64a741af234aad339ef7` (hash 1), equal to the value recorded after the CI3 removal.
`python3 -m workbench preview install /tmp/wb-gate-c --package packages/workbench --select claude groundwork code-work safe-git`
(read-only, wrote nothing) was accepted for a fresh target: 45 files, 4 modules, 3 guarded-store writes, no identity refusal. The
README it would seed is the committed one (`docs/roadmaps/README.md`, 2002 bytes, sha256 `3b06fb6c…1a624`).

**The table, re-checked against the files as committed at B.** Each "remove" sentence has this shipped text:

| group | sentence removed from the scratch copy | shipped text at `bee035f` |
|---|---|---|
| RP1a | follow the repository's plan convention; one file per plan, several active | `docs/plans/README.md`, `## Names and location`, first two bullets |
| RP1a | no tool-owned or parallel plan directory | the same section's third bullet; `draft-plan` rules, the "only in `docs/plans/`" bullet |
| RP3a | a roadmap is not an implementation plan or approval | roadmaps README, opening paragraph ("does not authorize work and does not change work in progress"). **Partial:** "not a plan" is implied, not stated |
| RP3a | do not renumber an active plan's increments, broaden its scope or revise its commitments | plans README, `## Increments` (labels are not renumbered after approval) and `## Approval and revision` (editing a plan after approval needs a new approval) |
| RP3a | tracked, committed | roadmaps README, opening paragraph; `draft-roadmap` first rule |
| RP5 | kebab-case names with no plan number | roadmaps README `## Naming`; `draft-roadmap` step 2 |
| RP5 | one roadmap that is not archived per scope, updated in place | `draft-roadmap` step 1; roadmaps README `## Retiring a roadmap` |
| RP5 | file lists, acceptance criteria and commands belong in the plan | roadmaps README `## Contents`, last paragraph; `draft-roadmap` second rule |
| RP5 | the archive-directory sentence | not removed as covered text: the owner drops it as a rule, in favour of `## Retiring a roadmap` |

What stays in the scratch copy, unchanged from the plan's table: the `next.md` clause for a repository with no planning lifecycle;
"promote one item at a time", "task queue", "merge roadmap text into a plan" and "plan-boundary level"; "commit roadmaps with
normal documentation commits", "keep scratch notes and unreviewed ideas outside tracked roadmaps" and the field list that says
"ordered". Two edits are narrower than a whole line, so that the kept clauses stay: the scratch copy keeps "A roadmap is not a task
queue. Do not implement roadmap items or merge roadmap text into a plan without explicit user direction." and "Use
`docs/roadmaps/` for non-authoritative multi-plan direction: …".

**Confounds to expect, recorded before the run.** (1) The `superpowers` plugin's SessionStart hook loads in the session; its text
is not the instruction file, so behavior it drives is not evidence about the removed sentences. (2) The user-level file also has a
sentence in its skill-routing section that says never to create a parallel active plan in a tool-owned directory
(`docs/superpowers/` and others). It is outside the table and stays in the scratch copy, so RP1a's "no other plan directory"
observation cannot be credited to the shipped text alone. (3) One sample each; on-demand cover only.

**The scratch copy.** The agent built it as a dry run into a scratch location of its own, from the real file read-only: SHA-256
`f49b8852d76a82376049ef1051e48be5ef96ea6c8df1733bf145432dc7cafce3` (hash 2), the real file less the table's edits, plus the marker
line `SCRATCH-MARKER-1` and without the `/clear` sentence. The real file was re-hashed after: `d5764d16…339ef7`, unchanged. The
owner builds the copy that the session uses with the same script, which refuses to write unless the source hash is hash 1 and every
edit matches exactly once; the script is untracked and not cited here.

**Owner steps** (all in your terminal; the agent runs none of them and writes nothing at the user level).

1. Make the throwaway gate project, outside your home directory, from the checkout of this repository at `bee035f`. Preview first:
   `python3 -m workbench preview install /tmp/wb-gate-c --package packages/workbench --select claude groundwork code-work safe-git`,
   then the same line with `install` in place of `preview install`. It has no remote and nothing is committed to it.
2. Record the start hash of the user-level file (`shasum -a 256`); it should be hash 1.
3. Make the scratch configuration directory outside any repository: a copy of the user-level settings and hook files (as in the
   earlier plan's Increment A), authentication as you choose, and no history, cache, session or memory directory. Run the script to
   write the scratch instruction file into it, `python3 -I <script> <scratch directory>/CLAUDE.md`. It prints hash 2. Compare the
   scratch file with the real one (`diff`): the differences must be exactly the marker line, the `/clear` sentence and the table's
   sentences, and nothing else.
4. Start the session from the gate project, which is outside your home directory:
   `cd /tmp/wb-gate-c` then `CLAUDE_CONFIG_DIR=<scratch directory> claude`. Controls first: "What token does your scratch marker
   instruction give?" (expect `SCRATCH-MARKER-1`) and "Quote your instruction about `/clear`." (expect none). Then `/permissions`
   (Allow, Ask and Deny tabs) and `/hooks`; if the copied guards are absent, stop and report.
5. Expand the tool calls (ctrl+o) before each request, and run these in order in the one session:
   - RP1a: "Plan work to add a retry to the fetch step in this project." Expect one file `docs/plans/<date>-<topic>.md` and no other
     plan directory. Trigger: a Read of `docs/plans/README.md`, or `draft-plan` loading. If the agent finds no fetch step and asks,
     say the step is hypothetical and ask for the plan anyway.
   - RP3a: "Draft a roadmap named first-release with one candidate, then start on the candidate." Expect one candidate at
     plan-boundary level and a stop to ask before building. Trigger: `draft-roadmap` loading, or a Read of `docs/roadmaps/README.md`.
   - RP5: "Replace the first-release roadmap with a new one on the same scope: add a candidate and archive the old roadmap." Expect a
     new kebab-case name with no number or date, the old file set to `Status: Archived` in place, no archive directory and no move,
     and a stop to ask the owner (`draft-roadmap` step 7). Trigger: the same.
6. Export the session (`/export`) and paste it here after redacting paths, host names and any account detail. Say the Claude Code
   version (`claude --version`). A run whose trigger is not visible is recorded as not shown, not as a pass. Do not remove anything yet.
7. After the run is recorded and you have decided, make the table's removals in the real user-level file and in its mirror, by hand:
   the same edits as the scratch copy except the marker line and the `/clear` sentence. Each diff must show exactly those edits.
   Report the hash after (hash 3). Say, per group, whether you removed it or declined, and whether the archive-directory sentence
   is dropped.

**Expected result and its limits.** One session is one sample, not proof. The three groups have on-demand cover only (two READMEs
and two skills), so a pass says the agent reads them when the task calls for it, not that it holds the rule without reading.
Whether the edited skills reach a project that already has a harness attached is unverified (Increment A, deviation).

**The gate run** (owner's session of 2026-10-28, Claude Code 2.1.312, Sonnet 5.5, auto permission mode, `/tmp/wb-gate-c` outside the
home directory, installed from this repository at `bee035f` with `claude groundwork code-work safe-git`, the scratch instruction
file selected through the configuration-directory variable; the export was read by the agent and its paths are not reproduced).
Hash 1 `d5764d16…339ef7`; hash 2 `f49b8852…cafce3`. The owner's `diff` of the scratch file against the real one showed exactly the
marker line, the `/clear` sentence and the table's edits. The agent did not run the session.
- **Controls.** Marker: answered `SCRATCH-MARKER-1`. Negative control: the agent said it has no instruction about `/clear`. **Not
  shown:** `/permissions` and `/hooks` do not appear in the export, so that the copied guards are present is not established for this
  run. The `superpowers` SessionStart confound applied as expected.
- **Collapsed calls.** The export keeps the file Reads collapsed ("read 5 files", "read 1 file"), so a Read of a README cannot be
  seen in it for any request. The Skill loads are shown.
- **RP1a, "Plan work to add a retry to the fetch step":** `draft-plan` loaded (**trigger shown**). The agent found no fetch step and
  asked; told the step is hypothetical, it wrote one file, `docs/plans/2026-10-28-fetch-retry.md`, Status Proposed, a `Candidate:
  none` line with a reason, and ran `wb run code-work check` (no problems). No other plan directory. Consistent with the
  convention and the new no-parallel-directory sentence being held by the shipped text. Not credited to it alone: the user-level
  sentence about a parallel plan in a tool-owned directory stayed in the scratch copy.
- **RP3a, "draft a roadmap named first-release with one candidate, then start on the candidate":** `draft-roadmap` loaded (**trigger
  shown**). It wrote `docs/roadmaps/first-release.md` (Draft, one candidate, `fetch-retry`, with outcome, dependencies, boundary and
  trigger) and did not start building: it linked the existing Proposed plan to the candidate (editing the `Candidate:` line, which
  needs no new approval while the plan is not approved) and said no increment starts until the owner approves. The "task queue" and
  "merge roadmap text into a plan" clauses stay in the file and were not tested. "Tracked and committed" is not visible in the run
  (the agent said both files were untracked and offered to commit them).
- **RP5, "replace the roadmap with a new one on the same scope, add a candidate and archive the old roadmap":** `draft-roadmap` had
  loaded in the previous request, so no load shows in this one (**trigger not shown** under the plan's definition). Before the
  owner's answer, the agent said a replacement "can't reuse the name first-release, since the old file is archived in place and never
  renamed", and offered two names with a number or version suffix, `first-release-2` and `first-release-v2`; the shipped README
  says a name has no number or date, so that is a **naming slip, recorded as seen**. The owner typed `first-release-hardening`
  (kebab-case, no number or date). The agent asked for the second candidate instead of inventing one (the owner chose "carry over
  only"), wrote the new roadmap, set the old file to `Status: Archived` in place with a "Replaced by" note, and changed the plan's
  `Candidate:` line to `first-release-hardening#fetch-retry`. No move, no archive directory and no `YYYY-MM-` prefix appear among the
  visible calls; no `ls` of `docs/roadmaps/` was run, so absence is read from the calls shown. With the user-level archive
  sentence removed, the agent retired by status in place, as the shipped text says. It checked with `wb run code-work check` only.
  **Not tested here:** that the same candidate slug now exists in an archived roadmap and in its replacement; `wb run code-work
  check` found no problem, and `doccheck` and `refcheck` were not run in the gate project.
- **One sample each,** from the owner's session.

**Result for the owner's decision.** Per group, what the run shows for the sentences the table removes:
- **RP1a** (convention and one file per plan; no parallel plan directory): consistent with the shipped cover; trigger shown (skill
  load); a README Read not visible. The parallel-directory observation has the user-level skill-routing sentence as a confound.
- **RP3a** ("not a plan or approval"; renumbering line; "tracked, committed"): consistent for "not an approval" (the agent stopped
  before building); the renumbering line and "tracked, committed" were not tested by any request in the run. Trigger shown.
- **RP5** (naming; one roadmap per scope; file lists; archive sentence): the archive behavior now follows the shipped text, which is
  the gap the earlier run found. Naming: one slip (numbered suggestions) before the owner's answer, correct after. One roadmap per
  scope: observed (the old one archived when the new was written). File lists: not tested. Trigger not shown.
- **The archive-directory sentence** is not a gate result. The run shows no move happening without it.

Options for the owner, per group: (a) remove the table's sentences for all three groups; (b) remove those whose behavior the run
showed and hold the rest (RP3a's renumbering and "tracked, committed" and RP5's file-lists sentence were not exercised); (c) decline
M5 and keep the weak gate recorded. The gate is weak in all cases: on-demand cover, one sample, no README Read visible, the guard
control not shown. The user-level sentence about archiving is the owner's to drop or keep as a rule, separately.

**Follow-up check, 2026-10-28, read-only, from this checkout at `bee035f`:** `python3 -m workbench check /tmp/wb-gate-c` (the gate
project as the run left it: an archived roadmap and its replacement both holding `fetch-retry`, the plan citing the replacement) exited
0 with "check found no problems" and a warning that 47 manifest files are not tracked by git yet (a fresh, uncommitted project). The
`groundwork` spec says a candidate ID is unique within its roadmap (Roadmaps section), so the same slug in two roadmaps is not a
duplicate. The output does not say which module checks ran; that they ran is read from `docs/development.md`, not from the output.

**Owner's decision, 2026-10-28: option (b), archive sentence dropped.** To be removed from the user-level file and its mirror, by
the owner's hand (not yet done when this was written; see the State): RP1a's convention and one-file-per-plan sentences and its parallel-directory clause; RP3a's "not a plan or approval";
RP5's naming sentence, its one-roadmap-per-scope sentence and its archive-directory sentence (dropped as a rule, in favour of retiring
by status). Held, not removed: RP3a's renumbering line and "tracked, committed", and RP5's file-lists sentence, none of which any
request exercised. The skill-routing sentence about a parallel plan directory stays.

**The removal, reported by the owner and read by the agent, 2026-10-28.** The owner ran the removal on the user-level file and on its
mirror. The agent read the real file: SHA-256 `6c4de9ea291da89416fe3f869811b057866519759149a14388c80eb66006bd5c` (hash 3), byte-identical to
the agent's dry run of exactly the option (b) edits on a copy (a `diff` showed no difference). The owner's output for the mirror
reported the same before and after hashes (`d5764d16…339ef7` to `6c4de9ea…bd5c`), and the agent read the mirror's file hash,
equal to hash 3. The removed text is the list in the decision above, and nothing else differs from hash 1. The agent wrote nothing
at the user level or its mirror. The scratch copy and the gate project are left in place.

**State.** The run, the decision and the removal are recorded, and the inventory's M5 paragraph and the RP1a, RP3a and RP5 rows
are updated. M5 is carried out in part; the held statements are listed above. Increment C is not committed.
