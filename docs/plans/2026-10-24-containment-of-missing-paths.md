# Make the containment check fail closed for a path that does not exist yet

Status: In Progress
Created: 2026-10-24
Candidate: none (a defect fix found while building the plan `2026-10-24-agent-confinement`; it is not a roadmap item)
Specs: review-engine

## Goal

Four programs decide whether a `PATH` entry or a program lies inside the project, and so may not be trusted. Each uses
an `is_inside(path, boundary)` that walks up from the path and compares every ancestor with the boundary. When the path
(or a part of it) does not exist, `os.path.samefile` raises `FileNotFoundError`, an `OSError`, and the function returns
`False`: "outside". An entry such as `<project>/bin` that is missing today is therefore trusted. A program put there
later, by the project or by a process the project controls, is found and run with the owner's authority.

The `mempalace` helper was fixed on 2026-10-24 after a security review found this. The same function is still wrong in
four places. The shared kit was shown on 2026-10-24 to return `False` for a missing directory inside a repository.

When this plan is done:

- `is_inside` returns `True` for a path that does not exist yet when an existing ancestor of it is the boundary or
  below it, and `True` when a part of the path cannot be examined, in all four places;
- each place has a test that fails before the change and passes after it;
- `review-engine.md` no longer documents the old behaviour as a limit.

## Scope

- `workbench/wbkit/call.py` and `tests/test_kit_call.py` (increment A).
- `packages/workbench/ask-codex/helper/ask-codex` and its tests (increment B).
- `packages/workbench/safe-git/helper/safe-git` and its tests (increment C).
- `packages/workbench/remote-runner/helper/remote-runner` and its tests (increment D).
- The spec sentence, the full suite, the approval release and the plan record (increment E).

## Non-goals

- Any other change to how a `PATH` is built. In particular the helpers keep a missing entry that is outside the
  project, as they do now. `mempalace` also drops entries that are not directories; that is a separate narrowing and is
  deferred.
- `mempalace`, which is already fixed, and its tests.
- A shared copy of the function for the helpers. Each helper stays one standalone file, as the module boundary asks.
- Any change to `outermost_boundary`, `trusted_which` or `environment`.

## Assumptions and constraints

- Python 3.11 minimum, standard library only; tests with `unittest`; the full suite is
  `python3 -B -W error tests/run_all.py`.
- `tests/` names no first-party module, helper or path (`tests/test_boundary.py`); the kit tests use synthetic names.
- The three helper files are copies by design; the fix is the body already shipped in `mempalace`
  (`packages/workbench/mempalace/helper/mempalace`, `is_inside`), with its docstring, so a reader can diff the four.
- Editing a module's tree stales its shipped approval. Each of B to D therefore leaves the full suite with the
  "shipped approvals are stale" skips for that module until the owner runs `release-approvals` in increment E. I run it
  only on the owner's exact words.
- Discovery tooling: graphify: skipped — not installed in this project. The scope was found by a search of `packages`,
  `workbench`, `tests` and `docs` for `is_inside` on 2026-10-24 and by reading each of the five definitions; the search
  lists exactly four unfixed definitions beside the fixed one, and the kit is called from `workbench/commands.py` and
  `wbkit` only.

### Choices (made by me; the owner may change any)

1. **The `mempalace` body, unchanged.** A `FileNotFoundError` on an ancestor is skipped and the walk continues; any other
   `OSError` returns `True`. The alternative, `os.path.lexists` checks, repeats the race the walk already has.
2. **One increment per module.** Each module's tree is a separate package with its own approval record and suite, so
   one commit each can be reviewed and reverted alone. The cost is four small commits.
3. **Failing closed on an unreadable ancestor.** A `PATH` entry under a directory the caller cannot examine is now
   dropped from the trusted list. The alternative, trusting it, is the bug. The cost is a lost entry in an unusual
   setup, and a missing program there is reported by the helper's existing "not found" message.

## Completion criteria

1. In each of the four places, `is_inside` is `True` for a missing path below the boundary, for the boundary itself, and
   when `os.path.samefile` raises `PermissionError`; it is `False` for an existing path outside, and for a missing path
   whose existing ancestors are outside.
2. In each of the four places, a missing `PATH` entry inside the project is not in the trusted entries and so is not
   passed to the child, and a program created there afterwards is never run.
3. Each new test was seen to fail on the old function and pass on the new one.
4. `review-engine.md` states the fixed behaviour.
5. The full suite is green in all roots with no stale-approval skips after the owner's `release-approvals`; `doccheck`,
   `refcheck` and `git diff --check` print nothing.

## Increments

### Increment A — The shared kit

**Outcome:** `wbkit.call` treats a missing path inside the project as inside.
**Dependencies:** none.
**Affected areas:** `workbench/wbkit/call.py` (`is_inside`), `tests/test_kit_call.py`.
**Steps:**
1. Test first, in `tests/test_kit_call.py`, class `FindsWbOutsideTheProject`: a `PATH` of a missing `<project>/bin`
   then `self.outside` runs the outside `wb`, and the program created in `<project>/bin` after the call setup is never
   run; a direct test of `call.is_inside` for the criterion 1 cases, with `samefile` patched to raise `PermissionError`.
   Run them and see the first and last fail.
2. Replace the body of `is_inside` and its docstring with the `mempalace` version.
**Verification:** `env PYTHONPATH=.:tests python3 -B -W error -m unittest tests.test_kit_call tests.test_kit_call_launcher tests.test_boundary`.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-containment-of-missing-paths#A`.

### Increment B — `ask-codex`

**Outcome:** the `ask-codex` helper's containment check fails closed.
**Dependencies:** A (for the test wording only).
**Affected areas:** `packages/workbench/ask-codex/helper/ask-codex` (`is_inside`), the helper tests under
`packages/workbench/ask-codex/tests/` beside `test_askcodex_run.py`.
**Steps:**
1. Test first: with `PATH` of a missing project entry, a missing deeper one and the outside directory, the fake
   program's recorded `PATH` is the outside directory only (the `mempalace` test
   `test_a_missing_entry_inside_the_project_is_never_passed_on_to_the_child` is the model), and a direct
   `is_inside` test for criterion 1. See them fail.
2. Replace the body of `is_inside` and its docstring with the `mempalace` version.
**Verification:** the module's tests (`env PYTHONPATH=.:packages/workbench/ask-codex/tests python3 -B -W error -m unittest
discover -s packages/workbench/ask-codex/tests -t packages/workbench/ask-codex/tests`).
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-containment-of-missing-paths#B`.

### Increment C — `safe-git`

**Outcome:** the `safe-git` helper's containment check fails closed.
**Dependencies:** none.
**Affected areas:** `packages/workbench/safe-git/helper/safe-git` (`is_inside`), tests beside
`test_safegit_git.py` (`test_path_is_only_the_trusted_entries` is the model).
**Steps:** as B, in this module's test style. The recorded `PATH` is the one `git` is started with.
**Verification:** the module's tests (about two minutes).
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-containment-of-missing-paths#C`.

### Increment D — `remote-runner`

**Outcome:** the `remote-runner` helper's containment check fails closed.
**Dependencies:** none.
**Affected areas:** `packages/workbench/remote-runner/helper/remote-runner` (`is_inside`; `trusted_entries` keeps its
existing `isdir` filter), tests beside the profile tests.
**Steps:** as B. The test also covers an existing directory entry that is a link into the project.
**Verification:** the module's tests.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-containment-of-missing-paths#D`.

### Increment E — Spec, approvals and record

**Outcome:** the spec says what is built, the shipped approvals match the changed modules, and the plan records it.
**Dependencies:** A to D.
**Affected areas:** `docs/specs/review-engine.md` (the limit sentence at its "PATH entry that does not exist yet"),
`workbench/shipped_approvals/` (by `release-approvals`), this plan's Result, and the Deferred work of
`docs/plans/2026-10-24-agent-confinement.md` only if its status, review record or result needs a pointer.
**Steps:**
1. In the spec, replace the sentence that says `wbkit.call` treats a missing `PATH` entry as outside the project with
   one that says it treats it as inside, and say that the helpers do the same.
2. The owner runs, or asks me to run, `python3 -m workbench release-approvals`. Remove stale records only after a
   preview and the owner's "remove them".
3. Run the full suite, `doccheck`, `refcheck` and `git diff --check`.
4. Fill the Result.
**Verification:** the full suite passes with no stale-approval skip; the document checks print nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-containment-of-missing-paths#E`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots; `git diff --check` and the document checks print nothing.
- A search of `packages`, `workbench` and `docs` for `def is_inside` shows five identical bodies, and a search of the
  tests shows a missing-entry test in each place.
- No live recheck is planned; each change is in a path that the tests exercise with a fake program.

## Risks and sensitive actions

- **A dropped entry.** See choice 3.
- **Approvals.** B to D stale three shipped records. `release-approvals` is owner-run; I run it only on "Run it for me".
- **Copies drift.** Five copies of the function remain by design; the verification search is what catches a sixth.
- Nothing is pushed by this plan. A security review of the walk (symlink loops, case-insensitive volumes) is done only if
  the owner asks.

## Review record

Round 1 of 3, `ask-codex review-plan`, 2026-10-24 (model `gpt-5.6-luna`, effort low), outcome converged with one minor
finding. The tool also flagged `verdict_mismatch: true` (its own verdict field disagreed with the summary); I did not
investigate it.

- R1-F1 (minor, Increment A verification): the boundary test sat on a separate line and read as a second shell command.
  Accepted; the command is now one line that includes `tests.test_boundary`.

The owner approved the plan on 2026-10-24, after this review.

## Deferred work

- Dropping a `PATH` entry that is not a directory in `ask-codex`, `safe-git` and the kit, as `mempalace` and
  `remote-runner` do.
- One shared containment function if the module boundary ever allows a helper to import from the kit.

## Result

- Increment A: `wbkit.call.is_inside` now has the `mempalace` body. Two new tests in `tests/test_kit_call.py` failed on
  the old function (a missing in-project entry was passed to the child; a missing path below the boundary read as
  outside) and pass now. `tests.test_kit_call`, `tests.test_kit_call_launcher` and `tests.test_boundary` (51 tests), the
  `ask-codex` module (90) and the `review-engine` module (325), which use the kit, pass.
- Increment B: the `ask-codex` helper's `is_inside` has the same body. Two new tests in `test_askcodex_run.py`
  (class `Environment`) failed on the old function and pass now; the module's 92 tests pass. The module's shipped
  approval is stale until the owner runs `release-approvals` (increment E). Next: C.
