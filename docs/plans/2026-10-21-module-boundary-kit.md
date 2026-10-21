# The kit and the maintainer directories

Status: Approved
Created: 2026-10-21
Candidate: workbench-v1#module-boundary-kit
Specs: module-boundary, module-contract, trust-and-approval, installer-interface, terms

## Goal

Build the base that lets module-specific code leave the installer, and nothing that moves it yet.
`docs/specs/module-boundary.md` and the decision `2026-10-21-module-code-lives-in-modules` say the
installer holds mechanism only. A module's helper is one file, so it cannot reuse the installer's careful
reading code, and a module has no place for its tests. This plan supplies both.

When this plan is done:

- the installer's reading code lives in a standard-library package, `wbkit` (the kit), at
  `workbench/wbkit/`: `safefs`, `display`, project finding and the project ID. The installer imports it
  from there, and its behaviour and tests are unchanged apart from import paths;
- the kit exposes `wbkit.API`, an integer, and imports only the standard library and itself;
- the launcher can start a Python helper through a fixed runner that checks the kit version the caller
  names, gives the helper `import wbkit` without putting any directory on the search path, and passes the
  helper's exit code through. No command exposes this yet;
- the verifier accepts `tests/` and `tools/` in a module, counts them in the tree hash and the approval,
  and the install copies neither;
- `python3 -B -W error tests/run_all.py` runs the installer's tests and every module's, and the `claude`
  module's own test file has moved into the module as the proof.

## Scope

- **The kit:** create `workbench/wbkit/`; move `workbench/safefs.py` and `workbench/display.py` into it;
  move project finding (`dispatch.find_root`) and the project ID (`manifest.project_id` and the reading
  of the manifest's `seed`) into it; add `API`.
- **The runner:** `workbench/runner.py`, and a `kit` parameter on `launch.launch`.
- **Maintainer directories:** `modulefiles.py` and the verifier account for `tests/` and `tools/`.
- **Test discovery:** `tests/run_all.py`; `docs/development.md` and `README.md` name it.
- **The proof:** `tests/test_claude_module.py` moves to `packages/workbench/claude/tests/`.
- **Documents:** amend `module-boundary.md` for how the runner reaches the kit (see Assumptions), and
  mark the parts of `module-contract.md` that this plan builds as built.

## Non-goals

- `commands`, `checks`, `wb run` and any change to `wb check`. Those are `module-commands` and
  `module-checks`.
- Moving any module code. `doccheck`, `refcheck`, `refindex`, `dispatch.py` and the `code-work` entries
  stay where they are, and so do the `code-work` and `groundwork` tests.
- The report form for module checks. A function enters the kit only when two users need it, and the first
  user of the report form is `module-checks`.
- The boundary test (no first-party names in `workbench/` or `tests/`). It cannot pass until the last move.
- Any change to the pins, approvals, the guarded store or the `code-work-plans` plan.

## Assumptions and constraints

- Standard library only; the tests are `unittest`. The full suite stays green after every increment, with
  the 108 stale-approval skips, until the owner runs `release-approvals` in increment G.
- **The runner reaches the kit without a search-path entry.** The specification says the runner adds the
  kit's directory to the search path. Because the kit is a package inside `workbench/`, that would also
  expose every other installer module as a top-level import. The plan instead has the runner load
  `workbench/wbkit/__init__.py` by file location as the module `wbkit` (with its own directory as the
  package's search location) and register it in `sys.modules`, so the helper's `import wbkit` and
  `import wbkit.safefs` work and no directory is added to the search path. This is stricter than the
  specification's wording; increment D amends the specification, which the owner's approval of this plan
  covers.
- The kit imports only the standard library and its own modules, by relative import. A test reads the
  kit's source and fails on any other import. Nothing in the kit names a module, a document kind or a harness.
- The runner and the kit are files of the workbench, like the launcher. A module cannot ship or shadow
  them; the runner finds the kit from its own file location and from nothing else.
- A `__pycache__` under `packages/` fails verification, so every run of the tests passes `-B` and
  `run_all.py` sets `sys.dont_write_bytecode` first.
- Moving `safefs` and `display` changes many imports (41 and 27 files in `workbench/`, 16 and 1 in
  `tests/`). Tests that patch these by dotted name (`mock.patch("workbench.safefs...")`) must be
  rewritten to the new name; a missed one fails loudly.

## Completion criteria

1. `workbench/safefs.py` and `workbench/display.py` no longer exist; the same code is in
   `workbench/wbkit/`, and nothing else in the repository defines the no-follow reader.
2. A test fails if any file under `workbench/wbkit/` imports anything but the standard library or the kit.
3. `wbkit.API` is an integer. Through the launcher's `kit` parameter, a helper whose caller names the
   same number runs and can `import wbkit` and `import wbkit.safefs`; a different number, a missing
   kit, or no `kit` for a runner start runs nothing, prints a `refused:` line and exits 1.
4. A helper run through the runner gets `sys.argv` as the specification states, its exit code reaches the
   caller unchanged, and a hostile `wbkit.py`, `json.py` or `sitecustomize.py` in the project or the
   current directory, or a hostile `PYTHONPATH`, is never imported.
5. A module with `tests/` and `tools/` verifies, the directories are in the tree hash, and a project that
   installs the module does not contain them. A module with any other unlisted directory is still refused.
6. `python3 -B -W error tests/run_all.py` runs the tests in `tests/` and in each `packages/*/*/tests/`,
   a package-local test shows it ran, two modules may each have a test file of the same name, and
   the package verifies after the run.
7. Every existing test still passes, unchanged in what it asserts.
8. The independent security review of the runner and the kit loading has no open Critical or High finding.

## Increments

### Increment A — The kit package and `display`

**Outcome:** `workbench/wbkit/` exists with `__init__.py` (`API = 1`) and `display.py`, moved with
`git mv`. The installer imports `display` from the kit. The test that the kit imports only the standard
library and itself exists and passes.
**Dependencies:** none.
**Affected areas:** `workbench/wbkit/`, `workbench/display.py` (removed), the 27 installer files that
import `display`, `tests/test_request.py` (the only test that touches it), a new `tests/test_kit.py`.
**Steps:**
1. Write `tests/test_kit.py`: `wbkit.API` is an integer; every source file under `workbench/wbkit/` imports
   only the standard library or the kit, by parsing it with `ast`; the kit names no module in the
   repository's module list (read from `packages/workbench/package.json` and the shipped directory).
   Because `display` has no test of its own, add characterization tests for `clean` and `ascii_text`
   (control characters, bidirectional and invisible characters, length) before moving it.
2. Move `display.py` into `workbench/wbkit/`, add `__init__.py`, and change each installer and test import.
3. Run the whole suite.
**Verification:** the new test fails before the move and passes after; `python3 -B -W error -m unittest
discover -s tests` passes with the same skip count.
**Evidence:** one local commit with the trailer `Plan: 2026-10-21-module-boundary-kit#A`.

### Increment B — `safefs` moves into the kit

**Outcome:** `safefs` is `workbench/wbkit/safefs.py`. Every import and every patch by dotted name is
updated. Behaviour is identical.
**Dependencies:** A.
**Affected areas:** `workbench/wbkit/safefs.py`, the 41 installer files and 16 test files that use it.
**Steps:**
1. Move the file with `git mv` and change imports mechanically, with the full suite as the check.
2. Search for the old dotted name in strings (patches, messages, documents under `docs/` that cite the path)
   and update each.
3. Confirm the kit test from A still passes: `safefs` imports only the standard library.
**Verification:** the full suite; a repository search for `workbench.safefs`, `workbench/safefs` and
`from . import safefs` finds only intended uses.
**Evidence:** one local commit, trailer `Plan: 2026-10-21-module-boundary-kit#B`.

### Increment C — Project finding and the project ID in the kit

**Outcome:** `wbkit.project` offers `find_root(start)` (the `lstat`-only finder with the 64-level limit,
returning the root or raising a kit error), `project_id(seed)` (the seed check and the SHA-256 derivation)
and `read_id(root)` (reads the committed manifest through the no-follow reader and derives the ID from its
`seed`). `dispatch.py` uses `find_root` and `read_id`, and `dispatch.find_root` is gone. The derivation
exists once, in the kit: `manifest.project_id` stays as the installer's name for it, a one-line wrapper that
turns the kit's seed error into `ManifestError`, so its seven installer callers (`acknowledge`, `attach`,
`dispatch`, `installplan`, `upgrade` twice, `upgradeplan`) and the nine test files that call it need no
change.
**Dependencies:** B.
**Affected areas:** `workbench/wbkit/project.py`, `workbench/dispatch.py`, `workbench/manifest.py` (the
wrapper), `tests/test_dispatch.py` (the cases for the finder stay and now exercise the kit), a new kit test
file. The callers of `manifest.project_id` are listed above and are checked, not changed.
**Steps:**
1. Write the kit tests first, copying the finder's cases from `tests/test_dispatch.py` (`.git` file, link
   at `.workbench`, link at the manifest, depth 64 and 65, escape in the start path) and adding a
   differential test: for every manifest the existing tests build, `read_id` equals
   `manifest.project_id(manifest.parse(...)["seed"])`.
2. Move the finder and the ID derivation; keep `manifest.parse` in the installer, since it is the
   writer-side validator and `declarations` is installer code. Make `manifest.project_id` the wrapper
   described above, and add a test that `manifest.py` contains no `hashlib` call of its own for the ID
   (the derivation is not duplicated) and that a bad seed still raises `ManifestError`.
   A repository search for `project_id(` confirms each caller still resolves to the one derivation.
3. State in the module docstring what `read_id` does not validate, so a helper does not take it for the
   installer's full parse.
**Verification:** the kit tests; `tests/test_dispatch.py` and `tests/test_manifest.py` unchanged in what
they assert; the full suite.
**Evidence:** one local commit, trailer `Plan: 2026-10-21-module-boundary-kit#C`.

### Increment D — The runner, the version check and the specification amendment

**Outcome:** `workbench/runner.py` and a `kit` parameter on `launch.launch`. With `kit=None` the launcher
runs the private copy as today. With an integer it runs `sys.executable -I <runner> <kit> <copy> <args>`.
The runner finds the kit from its own location, refuses on a missing kit, a non-integer `API` or a
mismatch, then registers the kit as `wbkit`, sets `sys.argv`, and calls `runpy.run_path(copy,
run_name="__main__")` without catching anything. `module-boundary.md` is amended to describe this.
**Dependencies:** A (the runner needs `wbkit.API`; B and C add content it need not wait for).
**Affected areas:** `workbench/runner.py`, `workbench/launch.py`, a new `tests/test_runner.py`,
`docs/specs/module-boundary.md`, `docs/specs/trust-and-approval.md` ("Pinned helpers") if it cites the
launch command line.
**Steps:**
1. Write `tests/test_runner.py` first, with a fake helper that records what it sees: it imports `wbkit`
   and `wbkit.safefs`; `sys.path` has no new entry and no `wbkit` directory; `sys.argv`; an exit code of 0,
   3 and a signal; a raised exception reaches the caller as a traceback; a `SystemExit("text")`.
2. Hostile cases: a `wbkit.py`, `json.py` and `sitecustomize.py` in the project and in the current
   directory, and a hostile `PYTHONPATH`, none imported.
3. Refusal cases: the kit number differs, is zero, is a string, is missing; the kit directory removed from
   a copy of the distribution; the runner run with no arguments. Each exits 1 with `refused:` and does not
   import the helper (the fake helper writes a file on import; the file must not exist).
4. Implement the runner and the launcher change.
5. Amend `module-boundary.md`: "How a helper reaches the kit" describes the file-location load, not a
   search-path entry, and the acceptance criterion says the same.
**Verification:** the new tests; `tests/test_launch.py` unchanged; the full suite.
**Evidence:** one local commit, trailer `Plan: 2026-10-21-module-boundary-kit#D`.

### Increment E — The maintainer directories

**Outcome:** `tests/` and `tools/` are reserved directories in the verifier. They are in the tree hash and
the approval, and the install never copies them.
**Dependencies:** none.
**Affected areas:** `workbench/modulefiles.py` (`RESERVED_DIRS`), the verifier and install tests, the
maintainer-directory text in `docs/specs/module-contract.md` (its lines 11, 198, 216, 295 and 363 at the time of
writing: the introduction, the verification step, "Module layout", "Module files" and the first new acceptance
criterion).
**Steps:**
1. Write the tests first on a synthetic module: it verifies with `tests/test_x.py` and `tools/build.py`;
   a change to a file in either changes the tree hash; the install writes neither; a module with an
   unlisted `docs/` directory is still refused; a symbolic link inside `tests/` is refused; an
   empty `tests/` is ignored like any empty directory.
2. Add the two names to `RESERVED_DIRS` and check every place that lists or copies reserved directories.
3. In `module-contract.md`, remove "not built yet" and "once built" from every maintainer-directory
   occurrence listed above and say in the introduction that they are built; leave the `commands`, `checks`
   and pin-name markers as they are until their later plans. A search for "built" in the file confirms
   which marks remain.
**Verification:** the new tests; the full suite. The shipped approvals stay stale until G.
**Evidence:** one local commit, trailer `Plan: 2026-10-21-module-boundary-kit#E`.

### Increment F — One test command, and the `claude` tests move

**Outcome:** `tests/run_all.py` exists, `docs/development.md` and `README.md` name it as the full-test
command, and `tests/test_claude_module.py` is `packages/workbench/claude/tests/test_claude_module.py`,
run by it.
**Dependencies:** E.
**Affected areas:** `tests/run_all.py`, `docs/development.md`, `README.md`,
`packages/workbench/claude/tests/` (new), `tests/test_claude_module.py` (removed), the one assertion in
that test that lists the module's directory, a new `tests/support_harness.py`, the three installer test
files that define the fixtures it takes (`tests/test_harnessplan.py`, `tests/test_neutral.py`,
`tests/test_layout.py`), and the sentence in `module-boundary.md` that names the shared test support.
**Steps:**
1. Write `tests/test_run_all.py` first, using a temporary copy of the repository's layout: two fake
   modules each with a `tests/test_helper.py`, one failing test in a third root; the run reports each
   root by name, runs both same-named files, exits non-zero for the failure, and leaves no `__pycache__`
   under the fake packages.
2. Implement `run_all.py`: set `sys.dont_write_bytecode`, put the repository root on the search path so
   module tests can `from tests import support`, discover each root as its own start and top-level
   directory, clear the previous root's test modules from `sys.modules` between roots, and exit
   non-zero if anything fails.
3. The `claude` test imports fixtures from three other test modules (`items` from `test_harnessplan`,
   `SKILL` and `tree` from `test_neutral`, `CLAUDE` from `test_layout`), which a module's tests may not
   do. Move those four definitions into `tests/support_harness.py`, have the three installer test files
   import them from there, and amend `module-boundary.md` so that the shared test support is
   `tests/support.py` and `tests/support_*.py`. Then move the `claude` test, fix its path constants,
   change its assertion on the directory listing to include `tests`, and run it only through
   `run_all.py`.
4. Add a test that every file under `packages/*/*/tests/` imports from `tests` only `support` or a
   `support_*` module (read with `ast`), so the rule is enforced and not assumed.
5. Update the commands in `docs/development.md` and `README.md`; the focused one-file form keeps working
   for `tests/` and gains the module form.
**Verification:** `python3 -B -W error tests/run_all.py` passes with a count that equals the old total
(2038 plus this plan's new tests); the package still verifies after the run, with no `__pycache__`.
**Evidence:** one local commit, trailer `Plan: 2026-10-21-module-boundary-kit#F`.

### Increment G — Security pass, release and the result

**Outcome:** an independent adversarial review of the runner and the kit loading has run, its findings
are fixed or recorded, the owner has released the approvals, and the plan's Result is written.
**Dependencies:** A to F.
**Affected areas:** this plan (review record and Result), tests added for each finding, the shipped
approvals (owner-run).
**Steps:**
1. This review is the `security-review` skill's adversarial verification of a change that handles
   untrusted input and runs a subprocess, which the owner's standing instructions require; it is not the
   Codex plan review that `AGENTS.md` reserves for the owner's request. To remove doubt, it starts only
   when the owner says to start increment G. Ask the `security-reviewer` agent to try to bypass the runner and the kit load: a `wbkit` in every
   place the helper's process could find it, an environment that changes how Python starts, a kit with a
   stale `__pycache__`, a link in place of the kit, a helper that rewrites `sys.modules`, a `kit` value of
   an unusual type, argument and path edge cases. Fix each finding with a regression test that fails first.
2. The owner runs `release-approvals`. I do not run it.
3. Run the whole suite and the new `run_all.py`; the 108 stale-approval skips should be gone.
4. Write the Result and the review record; list what is left for `module-commands`.
**Verification:** the full suite with no skips; the security review's report.
**Evidence:** one local commit, trailer `Plan: 2026-10-21-module-boundary-kit#G`.

## Verification for the plan as a whole

`python3 -B -W error tests/run_all.py`, with no skips after the release; `git diff --check`; a repository
search shows no `workbench.safefs` or `workbench.display` left; a package under `packages/` verifies after
the run; the security review's findings are closed.

## Risks and sensitive actions

- **The runner starts code from a project's pinned bytes with the kit, in a hostile directory.** This is
  the security-sensitive part; increment G is its review, and the specification's tests are the
  criteria. It is still a pin check and not a sandbox.
- **A wide mechanical move** (`safefs`, `display`) across about 90 files. The full suite and a repository
  search are the checks; the moves are their own increments so a regression is easy to place.
- **Loading the kit by file location** departs from the specification's wording and is amended in D.
  If the owner prefers the search-path form, only D changes.
- **The shipped approvals stay stale** through F, as they have since B of `code-work-plans`; the owner
  releases them in G. No `release-approvals` is run by the agent.
- Increment F removes a test file from `tests/`, which is a deletion of a tracked file; it is a move, made
  with `git mv`, and committed with the new path in the same commit.

## Review record

Rounds 1 and 2 of 3, 2026-10-21, requested by the owner: Codex (`gpt-5.6-luna`, medium effort, read-only).
The review is archived and not converged by the tool's count, because round 2 still had one major finding.
All findings were applied, none rejected, and the fixed plan was not reviewed again.

- Round 1, two major findings, both applied. Increment C missed the seven installer callers and nine test
  files of `manifest.project_id`; `manifest.project_id` now stays as a wrapper over the kit. Increment F
  missed that the `claude` test imports fixtures from three other test modules; they move to
  `tests/support_harness.py` and a test enforces the import rule.
- Round 2, one major and one minor finding, applied. Increment G is clarified as the `security-review`
  skill's adversarial pass, not the plan review that `AGENTS.md` reserves for the owner's request, and it
  starts only when the owner says to start G. Increment E lists every maintainer-directory mark in
  `module-contract.md` to clear.

Approved by the owner on 2026-10-21, including the amendment to `module-boundary.md` that increment D
makes (the runner loads the kit by file location and adds no directory to the search path).

## Deferred work

- **`module-commands`:** `commands`, `wb run`, the pin-path check, and removing `dispatch.py` and the
  `code-work` entries in `cli.py` and `rules.py`; the `code-work` tests move into the module.
- **`module-checks`:** `checks`, the report form (added to the kit with its first user), the parsing in
  `wb check`, and the move of `doccheck`, `refcheck` and `refindex` with their tests into `groundwork`.
- **`module-harness-paths`:** the harness table and settings path from the module's `layout`, and the
  boundary test.
- **`code-work-plans`:** its increments F to H are reconsidered after `module-commands`.
- **Discovery tooling:** none in this project (`graphify: skipped — the repository has no graph tooling`).
  The impact of the two moves was taken from a repository search: 41 and 27 installer files and 16 and 1
  test files import `safefs` and `display`.

## Result

### Increment A

`workbench/wbkit/` exists with `__init__.py` (`API = 1`) and `display.py`, moved with `git mv`.
`tests/test_kit.py` (13 tests after review) checks that `API` is an integer, that every kit source imports only the
standard library or the kit (`ast`, relative imports at level 1 only), that the kit makes no dynamic import,
that it names no first-party module or harness, that the old `workbench/display.py` is gone, and
characterizes `clean` and `ascii_text` (control, bidirectional, zero-width, combining, no-break and filler
characters, a plain space, non-ASCII text, non-string input). The tests failed before the move (no
`wbkit`) and pass after. 26 installer files and `tests/test_request.py` import `display` from the kit; a
parenthesised import list lost only that name, and `docs/development.md` names the new path.
Verification: `python3 -B -W error -m unittest discover -s tests`: 2051 tests, OK, skipped=108 (before review; the rerun is below) (the stale
shipped approvals, until G). Two things for the commit: the move is a rename, and the commit helper has
refused a deletion combined with additions before, so a refusal there needs the owner's decision.

Review (read-only `workflow-reviewer`): no Critical, High or functional Medium finding, and the import rewrite,
the launcher path and the references to the old path were checked sound. Two Low gaps in `tests/test_kit.py`,
both fixed: the dynamic-import check only matched two call names, so it now forbids the indirect modules
and names above and is tested on text that breaks each rule; and `sys.stdlib_module_names` needs Python
3.10, so the test falls back to a list of the modules the kit uses. Not caught by the check, by design:
`getattr(__builtins__, ...)` tricks, which a reviewer of a kit change reads for. The commit must list the
three new paths (`workbench/wbkit/__init__.py`, `workbench/wbkit/display.py`, `tests/test_kit.py`) with the
removed `workbench/display.py`.

### Increment B

`workbench/wbkit/safefs.py` holds the code of the old `workbench/safefs.py`, byte for byte (copied, not
`git mv`, so the commit helper sees a plain add and a plain delete; the old file was removed with
`claude-workflow remove`). 53 files changed: the installer and test imports now read `from .wbkit import
safefs` (tests: `from workbench.wbkit import safefs`), merged with the existing `display` import where there was
one; five parenthesised lists lost only that name and were re-wrapped; `tests/test_safefs.py` and
`tests/test_doccheck.py` use the new dotted name for the import and the patch. `tests/test_kit.py` now also
asserts that `workbench/safefs.py` is gone from the installer and present in the kit. A repository search for
`workbench.safefs`, `workbench/safefs` and `from . import safefs` finds only this plan and the completed older
plans, which are history.
Verification: `python3 -B -W error -m unittest discover -s tests`: 2051 tests, OK, skipped=108.
