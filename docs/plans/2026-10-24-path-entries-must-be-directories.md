# Trust only a PATH entry that is an existing directory

Status: In Progress
Created: 2026-10-24
Candidate: none (closes the first two items of the Deferred work in plan `2026-10-24-containment-of-missing-paths`; no roadmap candidate names it)
Specs: review-engine

## Goal

Five programs build the `PATH` a child is started with from the caller's `PATH`, keeping an entry that is absolute and
outside the project. Three of them keep an entry that does not exist: the shared kit (`wbkit.call.trusted_entries`), the
`ask-codex` helper (`trusted_entries`) and the `safe-git` helper (`trusted_path_entries`). `mempalace` and `remote-runner`
already keep an existing directory only.

The security review of plan `2026-10-24-containment-of-missing-paths` found a Low case that this leaves open. Python's
non-strict `os.path.realpath` drops a `..` that follows a component that does not exist, textually. For an entry such as
`<project>/a/../../pwn` with `<project>/a` missing, `is_inside` says "outside". If `<project>/a` is later made a link into
the project, the same string reaches a directory inside the project. A missing entry is the only way to get that case, and
a missing entry is never useful to a child, so the narrowing closes it without a rule about `..`.

When this plan is done:

- the kit, `ask-codex` and `safe-git` keep a `PATH` entry only when it is an existing directory (a link to one counts),
  and each has a test that fails before the change and passes after it for the `..` case and for a plain missing entry;
- `mempalace` and `remote-runner`, which were not changed in code, have a test that pins the same case, so a later edit
  cannot reopen it;
- the spec states the rule.

## Scope

- `workbench/wbkit/call.py` and `tests/test_kit_call.py` (increment A).
- `packages/workbench/ask-codex/helper/ask-codex` and its tests (increment B).
- `packages/workbench/safe-git/helper/safe-git` and its tests (increment C).
- Tests only in `packages/workbench/mempalace/` and `packages/workbench/remote-runner/` (increment D).
- The spec, the approval release and the plan record (increment E).

## Non-goals

- A rule that rejects a `..` component. See choice 1.
- A shared copy of the containment function. See choice 3.
- Resolving each entry and passing the resolved directory to the child, as `mempalace` does. That changes the text of the
  `PATH` the child sees and is a separate decision (Deferred work).
- Any change to `is_inside`, `outermost_boundary`, `trusted_which` or `environment`.
- A security review. It runs only if the owner asks.

## Assumptions and constraints

- Python 3.11 minimum, standard library only; tests with `unittest`; the full suite is
  `python3 -B -W error tests/run_all.py`.
- `tests/` names no first-party module, helper or path (`tests/test_boundary.py`); the kit test uses synthetic names.
- The filter is the one `remote-runner` ships: `os.path.isdir(entry)` before `is_inside`. `isdir` follows links and is
  `False` for a missing path or one that cannot be examined, so the filter fails closed.
- Editing a module's tree, tests included, stales its shipped approval. B to D therefore leave the full suite with
  "shipped approvals are stale" skips for those modules until the owner runs `release-approvals` in E. I run it only on the
  owner's exact words, and delete stale records only after a preview and "remove them".
- Discovery tooling: graphify: skipped — not installed in this project. The scope was found on 2026-10-24 by listing the
  definitions of `trusted_entries` and `trusted_path_entries` under `packages` and `workbench` and reading each: five
  definitions, two already filtering with `isdir`.

### Choices (made by me; the owner may change any)

1. **Directories only, and no `..` rule.** The deferred item proposed rejecting an entry with a `..` component. For an
   entry that exists, the filesystem resolves `..` the same way `realpath` did, so the rule adds nothing; for one that does
   not exist, the directory filter already drops it. The test pins the attack string, and a reviewer can ask for the extra
   rule if they want a second layer. The cost of the rule would be a rejected, unusual but legitimate `PATH`.
2. **The `remote-runner` form, not the `mempalace` form.** Test the entry as written and pass it on as written. Resolving
   closes a change of a link between the check and the use, which exists today and is not new here (Deferred work).
3. **Five copies stay.** A helper that imports the kit is allowed by `module-boundary`, but these helpers are standalone
   files today and the kit's API version would then bind them. Moving them is a larger change and is not part of this one.
4. **`safe-git` keeps its fallback.** It uses `FALLBACK_PATH` when no entry is trusted. An environment whose every entry
   is dropped therefore gets the fallback, as it does today when every entry is inside the project.

## Completion criteria

1. In the kit, `ask-codex` and `safe-git`, a missing `PATH` entry, a file, and the string `<project>/a/../../pwn` with
   `<project>/a` missing are not in the trusted entries and not in the child's `PATH`; an existing directory outside the
   project, and a link to one, are kept.
2. In `mempalace` and `remote-runner`, the same inputs give the same inclusion or exclusion decision, pinned by a test.
   They keep their existing difference in how a kept link is shown: `mempalace` passes the resolved directory and
   `remote-runner` passes the entry as written.
3. Each new test for criterion 1 was seen to fail on the old function and pass on the new one.
4. The spec states that a `PATH` entry must be an existing directory.
5. The full suite is green in all roots with no stale-approval skips after the owner's `release-approvals`; `doccheck`,
   `refcheck` and `git diff --check` print nothing.

## Increments

### Increment A — The shared kit

**Outcome:** `wbkit.call.trusted_entries` keeps only existing directories.
**Dependencies:** none.
**Affected areas:** `workbench/wbkit/call.py` (`trusted_entries`, its docstring), `tests/test_kit_call.py`.
**Steps:**
1. Test first, in `tests/test_kit_call.py`: with a `PATH` of a missing project entry, the attack string above, a file
   and the outside directory, `trusted_entries` returns the outside directory only; a link to an outside directory is
   kept. Run them and see the first fail.
2. Add `os.path.isdir(entry)` to the condition, before `is_inside`, and say so in the docstring.
**Verification:** `env PYTHONPATH=.:tests python3 -B -W error -m unittest tests.test_kit_call tests.test_kit_call_launcher tests.test_boundary`.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-path-entries-must-be-directories#A`.

### Increment B — `ask-codex`

**Outcome:** the `ask-codex` helper keeps only existing directories.
**Dependencies:** none.
**Affected areas:** `packages/workbench/ask-codex/helper/ask-codex` (`trusted_entries`), the helper tests beside
`test_askcodex_run.py` (class `Environment`).
**Steps:** as A. The fake program records the `PATH` it receives; it must be the outside directory only.
**Verification:** the module's tests (`env PYTHONPATH=.:packages/workbench/ask-codex/tests python3 -B -W error -m unittest
discover -s packages/workbench/ask-codex/tests -t packages/workbench/ask-codex/tests`).
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-path-entries-must-be-directories#B`.

### Increment C — `safe-git`

**Outcome:** the `safe-git` helper keeps only existing directories.
**Dependencies:** none.
**Affected areas:** `packages/workbench/safe-git/helper/safe-git` (`trusted_path_entries`), tests beside
`test_safegit_git.py` (class `Path`).
**Steps:** as B. Add a case where every entry is dropped and the fallback `PATH` is used (choice 4).
**Verification:** the module's tests (about two minutes).
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-path-entries-must-be-directories#C`.

### Increment D — Pin the case in `mempalace` and `remote-runner`

**Outcome:** the two modules that already filter have a test for the same inputs.
**Dependencies:** none.
**Affected areas:** tests only, in `packages/workbench/mempalace/tests/` and `packages/workbench/remote-runner/tests/`.
**Steps:**
1. In each module, add one test with the inputs of criterion 1. It asserts the inclusion or exclusion of each entry, and
   for a kept link the form that module already passes (resolved in `mempalace`, as written in `remote-runner`). It passes
   on the current code; the point is that it fails if the `isdir` filter is removed. Show that by removing the filter in a scratch copy of the helper and running the test
   against it, not in the tree.
**Verification:** each module's tests.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-path-entries-must-be-directories#D`.

### Increment E — Spec, approvals and record

**Outcome:** the spec says what is built, the shipped approvals match the changed modules, and the plan records it.
**Dependencies:** A to D.
**Affected areas:** `docs/specs/review-engine.md` and any other spec that describes the `PATH` entries a helper trusts
(found by a search), `workbench/shipped_approvals/` (by `release-approvals`), this plan's Result, and the Deferred work of
`docs/plans/2026-10-24-containment-of-missing-paths.md` only if it needs a pointer.
**Steps:**
1. Update the spec sentence: an entry must be absolute, an existing directory and outside the project.
2. The owner runs, or asks me to run, `python3 -m workbench release-approvals`. Remove stale records only after a preview
   and the owner's "remove them".
3. Run the full suite, `doccheck`, `refcheck` and `git diff --check`.
4. Fill the Result.
**Verification:** the full suite passes with no stale-approval skip; the document checks print nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-path-entries-must-be-directories#E`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots; `git diff --check` and the document checks print nothing.
- A search of `packages` and `workbench` for `def trusted_entries` and `def trusted_path_entries` shows five definitions,
  each testing `isdir`, and a search of the tests shows the attack string in each place.
- No live recheck is planned; each change is in a path the tests exercise with a fake program.

## Risks and sensitive actions

- **A dropped entry.** A `PATH` entry that does not exist, or cannot be examined, is no longer passed to the child. A
  program there was never found anyway; the helper's "not found" message applies.
- **Approvals.** B to D stale up to five shipped records. `release-approvals` is owner-run; I run it only on "Run it for me".
- **A mistaken claim that `..` is moot.** Choice 1 rests on reasoning about how `realpath` and the kernel resolve `..`. The
  test in A uses the attack string with a real link created afterwards, so the claim is tested and not only argued.
- Nothing is pushed by this plan.

## Review record

Round 1 of 3, `ask-codex review-plan`, 2026-10-24 (model `gpt-5.6-luna`, effort medium), outcome changes needed, one finding.

- R1-F1 (major, completion criterion 2): "the same result" cannot hold, because `mempalace` passes the resolved directory
  and `remote-runner` the entry as written. Accepted; criterion 2 and the increment D step now require the same
  inclusion or exclusion decision and allow the existing difference in form. The change is to the plan's wording only.

The owner decided R1-F1 as applied. The review was not archived. The owner approved the plan on 2026-10-24, after round 1
and without a second round.

## Deferred work

- Passing the resolved directory of each entry to the child, as `mempalace` does, in the other four places, to close a
  link that changes between the check and the use.
- One shared containment function, if the five standalone copies ever become a kit import (choice 3).

## Result

- Increment A: `wbkit.call.trusted_entries` now also requires `os.path.isdir(entry)`. Two new tests in
  `tests/test_kit_call.py` (class `FindsWbOutsideTheProject`) failed on the old function and pass now. The failure showed
  the attack string `<project>/a/../../pwn` reaching the child's `PATH`. The second test also makes `a` a link into the
  project afterwards and shows the same text then names `<project>/pwn`, so the Low case was real and is closed by the
  directory filter alone (choice 1). `tests.test_kit_call`, `tests.test_kit_call_launcher` and `tests.test_boundary` (53
  tests) and the `review-engine` module (325), which uses the kit, pass; `git diff --check` prints nothing. `ask-codex`
  also uses the kit, and its suite is not run until B. Next: B.
- Increment B: the `ask-codex` helper's `trusted_entries` now also requires `os.path.isdir(entry)`. Two new tests in
  `test_askcodex_run.py` (class `Environment`) failed on the old function, where the program's `PATH` held the attack
  string, the missing entries and the file, and pass now: only the link and the outside directory reach the program, and
  the second test shows the same text names `<project>/pwn` once `a` becomes a link. The module's 94 tests pass;
  `git diff --check` prints nothing. The module's shipped approval is stale until E. Next: C.
- Increment C: the `safe-git` helper's `trusted_path_entries` now also requires `os.path.isdir(entry)`. Three new tests
  in `test_safegit_git.py` (class `Path`) failed on the old function and pass now: the existing-directory filter (the
  attack string, a missing entry, a file and a missing entry outside the repository were kept before), the attack string
  with a link made afterwards, and an environment whose every entry is dropped, which now gets `FALLBACK_PATH` (before,
  the missing entries were kept, the fallback was not used and the run was refused). The module's 262 tests pass;
  `git diff --check` prints nothing. The module's shipped approval is stale until E. Next: D.
