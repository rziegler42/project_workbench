# Self-hosting: agreement with installer output, and retiring the old template

Status: In Progress
Created: 2026-10-25
Candidate: workbench-v1#self-hosting
Specs: repository-boundary

## Goal

The roadmap candidate `self-hosting` has two jobs: show, by a test, that this repository's hand-maintained files agree
with what the installer would generate, and retire the old template (`claude_project_template`). Discovery for this plan
found that the candidate cannot be done as written, and why:

- **The installer cannot be run on this repository.** A target must be a missing directory, an empty directory, or one
  holding only a real `.git` (`docs/specs/installer-interface.md`, "The target"). This repository holds 390 tracked files.
  The commands for an existing project (`upgrade`, `add`, `acknowledge`) need a manifest, a store record and baselines
  that only a first `install` makes. So this repository cannot become an installed project today, and the roadmap's third
  job, approving its own plans with `wb approve-plan` (and gating its own edits), needs a new way in that no candidate
  names.
- **"Agreement" cannot mean equal bytes.** A scratch `preview install` of all nine first-party modules into a temporary
  directory (2026-10-25) planned 61 files, 76 directories and 3 store writes. Seven of the files are _seeded_
  (`AGENTS.md`, `docs/README.md`, `docs/plans/README.md` and the four `docs/*/README.md` of `groundwork`), and a seeded
  file is the owner's to change after install. This repository's versions differ in size from the seeds
  (`docs/plans/README.md` 3,574 bytes against 5,193; `docs/decisions/README.md` 8,424 against 1,059; `AGENTS.md` 6,009
  against 5,177), and `docs/references/README.md` does not exist here at all. Every other file is module-owned and lives
  under `.workbench/`, which this repository does not have.

When this plan is done:

1. **A tripwire records the relation.** A test in the installer root installs the nine first-party modules into a scratch
   directory and gives every seeded path one recorded disposition for this repository: `identical`, `diverged` (the owner's
   edit, with a one-line reason) or `absent` (with a reason). It fails when the installer plans a seeded path that has no
   disposition, or when a recorded disposition no longer holds (an `identical` file has changed on either side, a
   `diverged` or `absent` one has become identical or has appeared or gone). A change to a module's seeds therefore
   forces a decision about this repository.
2. **The old template is retired as a source.** No tracked document or tool here depends on it. The roadmap says so, the
   untracked `.template-manifest` stays excluded, and what remains is the owner's: archiving the old repository and
   removing its mentions from `~/.claude`, which the plan names and does not do.
3. **The missing way in has a candidate.** The roadmap gains `adopt-existing-repository`, and `self-hosting` is narrowed
   to what is true now, so the roadmap no longer promises what the installer cannot do.

The plan does not install into this repository, does not make it an installed project and does not approve its plans
with `wb approve-plan`.

## Scope

- Increment A: one new test file in `tests/`, its data file under `tests/fixtures/`, and the line that registers
  nothing (the runner discovers `tests/`). No change to `workbench/` or to any package.
- Increment B: `docs/roadmaps/workbench-v1.md` (the `self-hosting` entry, a new `adopt-existing-repository` entry, the
  "Current state" sentence on the old template, and the order list), `docs/specs/repository-boundary.md` (one sentence
  that this repository's seeded files may differ and a test records how), and this plan's record.

## Non-goals

- A new installer command or option, including any way to install into a non-empty directory. That is
  `adopt-existing-repository`, which needs its own brainstorming, spec change, decision and security review.
- Changing a seeded file of this repository to match the installer, or the reverse. The test records the relation as it
  is; each `diverged` file is a choice for the owner, listed under Deferred work.
- Creating `.workbench/`, a manifest or a store record here. Moving `.debug/`. Rendering harness files.
- Editing `~/.claude` or the owner's global rules (`global-config-migration`), or any action on the old repository
  itself (the owner's).
- A security review. It runs only if the owner asks.

## Assumptions and constraints

- Python 3.11 minimum, standard library only. The root's tests run with
  `env PYTHONPATH=.:tests python3 -B -W error -m unittest discover -s tests -p 'test_self_hosting.py'`; the full suite is
  `python3 -B -W error tests/run_all.py` (about 4 minutes, run in the background).
- Tests never touch the real store (`tests/support.py`), so the scratch install uses the same temporary-root support the
  other install tests use (`tests/support_install.py`), not the owner-run commands. The test installs from
  `packages/workbench` as first-party, the way the existing install tests do.
- The tracked `.gitignore` and `docs/` are read through the working tree, not git, so the test also runs in a copy of the
  repository without `.git`. It reads no untracked file (`.claude/`, `.template-manifest`, `.debug/`), because nothing
  tracked may depend on untracked content.
- A new test file adds no file to a module, so no shipped approval goes stale. `docs/specs/` and the roadmap are not
  module trees.
- Facts observed on 2026-10-25 with `preview install` into a scratch directory (nothing written there): the figures in the
  Goal. They are re-derived by the test, not trusted from this plan.
- Discovery tooling: graphify: skipped — not installed in this project. The scope was found by reading the roadmap entry,
  `docs/development.md`, the earlier plans and decisions that name `self-hosting`, and a scratch `preview install`.

### Choices (made by me; the owner may change any)

1. **Agreement is a recorded disposition per seeded path, not equal bytes.** The installer's own spec lets the owner edit a
   seeded file, so equality would fail on the first edit and mean nothing. The alternative, making this repository's files
   equal the seeds, would replace seven documents the owner wrote with shorter generic ones. A tripwire keeps the
   decision visible without changing any document.
2. **Module-owned files are out of the comparison.** They exist only under `.workbench/`, which this repository does not
   have, and the installer writes them from the package bytes already tested elsewhere. The test compares the seeded set and
   the slot blocks' presence, and says so.
3. **Do not add an `adopt` path in this plan.** It is a new owner-run installer command that writes into a directory with
   content, which is the riskiest class of change the workbench has. Folding it into a plan titled "proof and retirement"
   would hide it. I split it out as a roadmap candidate, and `self-hosting` keeps the two jobs that can be done now.
   The alternative, letting this plan grow into adoption, would make it far larger than any earlier plan. If you want
   adoption first, say so and I will draft that plan instead.
4. **The old template is retired by documentation and the owner's act, not by deleting anything here.** `.template-manifest`
   is an untracked, excluded file; I do not remove it, and the plan does not touch the old repository.
5. **The roadmap edit rides in this plan.** The corrected entry is the direct consequence of the discovery above, so it is
   increment B and not a separate plan.

## Completion criteria

1. A test exists that installs the nine first-party modules into a scratch directory, lists the planned seeded paths, and
   asserts that each has exactly one recorded disposition and that the recorded disposition holds in this repository.
2. The test was seen to fail when a disposition was removed, when a recorded `identical` file was changed, and when an
   invented seeded path was added to the data; and to pass on the real data.
3. The roadmap's `self-hosting` entry matches what the installer can do, a new `adopt-existing-repository` entry exists
   with outcome, dependencies, boundary and promotion trigger, and "Current state" says the old template is retired as
   a source and what remains is the owner's.
4. `docs/specs/repository-boundary.md` says in one sentence that this repository's seeded files may differ from the
   installer's and where the relation is recorded.
5. The full suite is green in all roots with no new skip; `doccheck`, `refcheck` and `git diff --check` print nothing.
   The document checks are run from the module's source in this repository, as the earlier plans of this repository did:
   `env PYTHONPATH=workbench python3 -B packages/workbench/groundwork/helper/doccheck` and `.../refcheck`. They need no
   installed project and write nothing.

## Increments

### Increment A — The tripwire for seeded files

**Outcome:** a test records, per seeded path, how this repository relates to installer output, and fails on drift.
**Dependencies:** none.
**Affected areas:** `tests/test_self_hosting.py` (new), `tests/fixtures/self_hosting_dispositions.json` (new).
**Steps:**
1. Test first. Build a scratch install plan of all nine first-party modules with the support in `tests/support_install.py`,
   and read from it the seeded paths and their bytes. Write the data file with one entry per seeded path:
   `{"path", "disposition": "identical|diverged|absent", "reason"}` (a reason for `diverged` and `absent`). Initial
   entries come from the discovery in the Goal; `docs/references/README.md` is `absent` with the reason that this
   repository holds no references, and every other seeded path is `diverged` unless it is byte-equal.
2. Assertions: (a) the set of planned seeded paths equals the set in the data file; (b) each `identical` path is byte-equal
   to the seed; (c) each `diverged` path exists and is not byte-equal; (d) each `absent` path does not exist; (e) the slot
   markers the installer plans in `AGENTS.md` and `docs/README.md` are listed by name, so a new slot also forces a
   decision. Each failure message names the path and says what to record.
3. Run it and see it fail three ways: remove one entry, mark a `diverged` file `identical`, add an invented path. Then
   restore the data and see it pass. Run the root's other install tests to confirm the support was not changed.
**Verification:** `env PYTHONPATH=.:tests python3 -B -W error -m unittest discover -s tests -p 'test_self_hosting.py'`;
`git diff --check`.
**Evidence:** the one local commit, trailer `Plan: 2026-10-25-self-hosting#A`.

### Increment B — Roadmap, spec sentence and record

**Outcome:** the roadmap and the spec say what is true, and the plan records the result.
**Dependencies:** A.
**Affected areas:** `docs/roadmaps/workbench-v1.md`, `docs/specs/repository-boundary.md`, this plan's Review record and
Result.
**Steps:**
1. Roadmap: rewrite the `self-hosting` outcome and boundary to the two jobs done here (the tripwire and the retirement as a
   source), move "approving this repository's own plans with `wb approve-plan`" and the edit gate to a new
   `adopt-existing-repository` entry (outcome: this repository becomes an installed project; dependencies:
   `self-hosting`; boundary: a way to install into a repository that has content, with its own spec change, decision and
   security review; promotion trigger: the owner chooses it). Update the "Current state" sentences "The old template is
   retired at `self-hosting`" and the "installer is not run on its own repository" constraint, and the ordered list.
2. Spec: one sentence in `repository-boundary` that this repository's seeded files may differ from installer output, with
   the test and data file named.
3. Run the full suite, `doccheck`, `refcheck` and `git diff --check`. Fill the Result and set the status to `Completed`.
**Verification:** the full suite passes; the document checks print nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-25-self-hosting#B`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots; `git diff --check` and the document checks print nothing.
- `git grep -n "claude_project_template"` in tracked non-plan files lists only the history in two decisions and the
  roadmap, none of which a tool reads.
- Not verified, by design: that the installer works on a repository with content, that this repository's plans can be
  approved with the command, and a live check that an agent follows the new `mempalace` rules (see Deferred work).

## Risks and sensitive actions

- **A test that proves little.** A tripwire records a relation; it does not show the repository is correct. The Goal says
  so, and the Result must not call the repository "self-hosted".
- **A roadmap that now promises less.** Narrowing `self-hosting` changes direction the owner approved earlier; the plan's
  approval covers that edit, and nothing else in the roadmap moves.
- **The test reads the working tree of this repository.** In a copy without the same documents it would fail; that is the
  point of a tripwire, and it is stated in the test's message.
- **No sensitive action.** Nothing is installed, approved, pushed or deleted by this plan.

## Review record

Round 1 of 3, `ask-codex review-plan`, 2026-10-25 (model `gpt-5.6-luna`, effort medium), outcome changes needed, one
finding.

- R1-F1 (major, Completion criterion 5 and the verification steps): the plan requires `doccheck` and `refcheck`, which an
  earlier plan skipped on the ground that they run in an installed project. Accepted in part: they do run here from the
  module's source with `PYTHONPATH=workbench` (they were run that way on this plan and on the previous one, and print
  nothing), so the plan now states that command in criterion 5 instead of dropping the checks. The earlier plan's
  statement was about the installed-project form, not about this one. The owner decided R1-F1 as applied. The review was
not archived. The owner approved the plan on 2026-10-25 after round 1 and without a second round.

## Deferred work

- `adopt-existing-repository` (roadmap): installing the workbench into this repository, the edit gate here and
  `wb approve-plan` for its own plans.
- Each `diverged` seeded file: whether to bring this repository's text and the seed together, a decision per file.
- A live check that an agent follows the order of stores and the wing rule of the `mempalace` module; best done once the
  modules are installed here.
- The owner's: archiving `claude_project_template` and removing its mentions from `~/.claude/CLAUDE.md`
  (`global-config-migration`).

## Result

- Increment A: `tests/test_self_hosting.py` and `tests/fixtures/self_hosting_dispositions.json`. The test runs
  `preview` on the nine first-party modules into a scratch directory (nothing written), reads the seven seeded paths and the
  slot blocks of `AGENTS.md` and `docs/README.md` from its output, and checks each against one record. Six paths are
  recorded `diverged` with a reason and `docs/references/README.md` is `absent`; none is `identical`. It has 3 tests and
  they pass. Run on the real data with a record removed, a `diverged` file marked `identical`, and an invented path added,
  it fails each time (checked with a scratch script, not committed); a second test pins the messages for those three
  and for a wrong `absent`, a new seeded path and a changed slot list. Like the other tests that use the real package it
  skips while the shipped approvals are stale, so it does not run in that window. `test_boundary`,
  `test_module_test_imports` and `test_maintainer_dirs` pass; `doccheck` and `git diff --check` print nothing. The full
  suite has not been run yet (B). Next: B.
