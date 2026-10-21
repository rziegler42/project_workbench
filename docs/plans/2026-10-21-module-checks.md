# Module checks and the groundwork move

Status: Completed
Created: 2026-10-21

Candidate: workbench-v1#module-checks
Specs: docs/specs/module-boundary.md, docs/specs/module-contract.md, docs/specs/groundwork.md

## Goal

A module declares `checks`; `wb check` runs each recorded module's pinned check helpers through the launcher
and prints their bounded report lines under the module's name, by the rules of `module-boundary.md` ("Module
checks" and "Declaration schema"). The document checks (`doccheck`, `refcheck`, `refindex`) and their tests
leave the installer and become single-file check helpers of the `groundwork` module over the kit. The rules
they report do not change.

## Scope

- The `checks` field: parse, shape and refusals, and the pin-name rule across commands and checks (the
  check half left out of `module-commands`).
- The kit pieces a document check needs and the kit does not have yet (see the assumptions).
- A check runner: resolve each recorded module's checks, launch them, and turn their output into bounded,
  cleaned report lines; wire it into `wb check` after its own checks.
- Moving `doccheck`, `refcheck` and `refindex` into `groundwork` as helpers, with their tests, and removing
  them from the installer and from `check.py`.
- Showing a module's checks in the approval request, as `module-commands#G` did for commands.
- A security pass: the runner reads hostile helper output, and the helpers read hostile repository content.

## Non-goals

- A change to any rule a document check reports (names, statuses, candidate IDs, the reference index).
- `module-harness-paths`: the harness table in `check.py` and the settings path in `layout.py` stay as they
  are. Only the document-check calls leave `check.py`.
- A check with `arguments` or a `runtime` other than the kit's Python runner; checks are always kit helpers
  without arguments.
- A check that writes. `wb check` stays read-only and agent-safe.
- The `code-work-*` plans.

## Assumptions and constraints

- Python 3.14, standard library only; `python3 -B -W error tests/run_all.py` is the full test command
  (2194 tests in 3 roots at the start).
- The accepted decision `2026-10-21-module-code-lives-in-modules` supersedes
  `2026-10-21-installer-runs-document-checks`, so the move the specification held back is now allowed.
- A check helper is one file. The launcher copies the single hashed file into a private directory and the
  runner loads only the kit beside it, so a helper cannot import a sibling. `doccheck`, `refcheck` and
  `refindex` (about 640 lines together) therefore become two helpers, `helper/doccheck` and
  `helper/refcheck`, with the small part of `refindex` that `refcheck` reads (`parse` and its field checks)
  inlined in the second. `refindex.serialize` and `check_document` are used only by `test_refindex.py` and
  describe the format `groundwork.md` fixes; increment E settles whether they move with the tests or are
  dropped, and records which.
- Today the checks use installer code that is not in the kit: `projectfs.Writer` (`read_file`, `list_dir`),
  `gitindex`, `manifest.parse` and `installed.MANIFEST`. Increment B confirms which of these the kit must
  gain and adds only those, as additions that do not change `API`. If one cannot be added without changing an
  existing kit function's behaviour, the plan stops and asks the owner whether to raise `API`.
- A project that has `groundwork` but has not pinned its check helpers gets a **problem** from `wb check`,
  not a skip (specification, behaviour 4). For this repository the owner pins them.
- A change to any file of a first-party module, including its `tests/`, changes its tree hash, so the owner
  runs `python3 -m workbench release-approvals` and approves removing stale records (E, F). I do not run it.
- Subagents have the limits recorded in the earlier plans; an increment that renames and deletes may need the
  owner to commit by hand.
- Discovery tooling: none in this project (`graphify: skipped — the repository has no graph tooling`). Impact
  was taken from a repository search: `doccheck` and `refcheck` are called only from `workbench/check.py`;
  `refindex` only from `refcheck`; tests are `test_doccheck.py`, `test_refcheck.py`, `test_refindex.py`,
  `test_check.py` and `test_groundwork_*.py`.

## Completion criteria

- A module with a valid `checks` list verifies; every refusal in the specification is refused naming the
  module and the field, and a pin name used twice across commands and checks is refused naming both modules.
- `wb check` runs the recorded modules' checks in manifest order after its own, prints cleaned, bounded lines
  under the module name, and treats an unpinned, changed, failing or malformed helper as a problem while the
  other checks still run.
- `doccheck`, `refcheck`, `refindex`, their tests and their calls in `check.py` are gone from the installer;
  `groundwork` ships and declares the two helpers, and `wb check` on a project with `groundwork` reports what
  it reported before (shown by the moved tests passing unchanged in substance).
- The approval request lists a module's checks.
- The security pass is recorded with what was accepted and not fixed; the specifications describe what is
  built; the full suite passes.

## Increments

### Increment A — The `checks` field and the pin-name rule

Outcome: a module may declare `checks`; the verifier checks them and refuses a pin name used twice.
Dependencies: none.
Affected areas: `workbench/declarations.py`, `workbench/verify.py`, `workbench/rules.py` if a rule name is
added, `tests/test_declarations.py`, `tests/test_verify.py`, `docs/specs/module-contract.md`.

1. Tests first: a valid list (up to 16 entries) verifies; an unknown field, a wrong type, a missing `helper`
   or `kit`, a `kit` that is not an integer from 1, a `helper` not in `ships`, two entries naming one helper
   (or one that differs only in case), a helper that is also a command's, and a pin name that is not in the
   helper-name form are each refused naming the module and `checks`. Across selected modules, a pin name
   given twice by commands or checks in one module or two is refused naming both modules (rule
   `command-name` is extended or a sibling rule is added, whichever keeps messages distinct).
2. Add `Check` and the `checks` field to `parse_module`, with the same helper-path rules as `commands`.
3. Show that the field and rule appear in the module contract's field table, "Concrete schema" and "Set
   checks"; remove the "not built yet" mark for `checks` only.

Verification: the new tests, then the full suite. Evidence: each refusal has a test; the first-party modules
still verify unchanged.

### Increment B — Kit additions for document checks

Outcome: a kit helper can read a project's tracked-file set, list a directory leniently and learn which
modules the committed manifest records, without importing the installer.
Dependencies: none (independent of A).
Affected areas: `workbench/wbkit/`, `workbench/gitindex.py`, `workbench/doccheck.py` is not yet touched,
`tests/test_wbkit*.py`, `docs/specs/module-boundary.md` ("The kit").

1. Re-read the three helpers' uses of `Writer`, `gitindex`, `manifest` and `installed`, and write down the
   exact calls needed. Anything the kit already has is reused.
2. Tests first, in `tests/`, for each addition: the no-follow behaviour (a link in place of a file, folder or
   `.git`), bounds, and refusal text that does not repeat hostile content.
3. Add the pieces to the kit as new functions, move the `.git/index` parser there if that is the smaller
   change, and have the installer's `gitindex` call it, so the code exists once. Do not change an existing
   kit function's behaviour; if that proves necessary, stop (see the assumptions).

Verification: the kit tests, `test_check.py` unchanged and passing, the full suite. Evidence: the installer's
own `wb check` reports the same as before.

### Increment C — The check runner

Outcome: a function that, for a project, returns the report of every recorded module's checks without yet
being called by `wb check`.
Dependencies: A, B.
Affected areas: new `workbench/checks.py`, `workbench/launch.py` (bounded capture), `workbench/commands.py`
only if a resolver helper is shared, `tests/test_checks.py`, `tests/test_launch.py`.

1. Tests first, on synthetic modules with a recording helper: manifest order (modules by package then module
   name by code point, then the `checks` list), independent of install order; the runner uses the pin named
   by the last segment of the helper path and refuses when the pin's path or kit differs from the
   declaration, as `commands.resolve` does; an unpinned helper, a helper whose bytes changed, a non-zero
   exit, a line that is not `problem: ` or `warning: `, output that is not text and a helper that writes
   nothing are each handled as specified. Exit 0 with empty output is valid and reports nothing. Every other
   case is a problem of `wb check` itself, worded "the check <name> failed" with the cleaned start of the
   output (an unpinned or changed helper says so instead). The other checks still run.
2. Bounds and cleaning: each line cleaned with the kit's display functions; at most a fixed number of lines
   and bytes taken per check, a bound that is passed is reported as a line saying so; a helper cannot produce
   a line that looks like the installer's own.
3. Bound the execution itself, test-first: `launch.launch` today runs `subprocess.run` with no timeout and
   no cap, so captured output could grow without limit before the runner sees it. Add an optional capped
   capture to the launcher (read the helper's standard output through a pipe up to a byte cap, and kill the
   process group when the cap or an overall time limit is passed), keeping the current behaviour when the
   option is absent so `wb run` is unchanged. Tests: endless output, a helper that sleeps past the limit,
   output exactly at and one byte over the cap, and a helper that ignores its pipe being closed; each ends
   with the process gone and a problem reported.
4. Implement `checks.run_all(guarded, root)` returning, per module, its `problem`/`warning` lists. It reads
   the declaration the same way `commands.resolve` does (installed `module.json`, declaration hash equal to
   the manifest's) and launches each check through `launch.launch(..., kit=N)` with the project root as the
   working directory and stdout captured.

Verification: `test_checks.py`, then the full suite. Evidence: a recording helper proves what ran, in what
order, and that nothing ran for a refused check.

### Increment D — `wb check` runs the module checks

Outcome: `wb check` prints the module checks' lines and counts their problems.
Dependencies: C.
Affected areas: `workbench/check.py`, `tests/test_check.py`, `docs/development.md`.

1. Tests first: the module's lines appear under its name after the installer's own, a module problem makes
   `wb check` exit 1 and counts in "check found N problems", a warning does not, an unpinned helper is a
   problem and the rest still run, a project with no module checks prints exactly what it printed before.
2. Call `checks.run_all` from `examine`/`run` after the installer's own checks; extend `Report` with the
   module sections; keep the existing output lines unchanged.
3. Record the behaviour in `docs/development.md`.

Verification: `test_check.py`, the full suite. Evidence: output of `wb check` on a synthetic project before
and after for a project without module checks is byte-identical.

### Increment E — `doccheck` moves into `groundwork`

Outcome: `groundwork` ships and declares `helper/doccheck`; the installer no longer runs the document form.
Dependencies: D.
Affected areas: new `packages/workbench/groundwork/helper/doccheck`, `module.json`,
`packages/workbench/groundwork/tests/`, `workbench/doccheck.py` (removed), `workbench/check.py`,
`tests/test_doccheck.py` (moved), `tests/test_check.py`, `tests/test_groundwork_*.py`,
`workbench/shipped_approvals/`.

1. Tests first: move `test_doccheck.py` into the module, rewritten to run the helper through the runner on a
   synthetic project (the rules tested are unchanged). Settle what happens to `test_groundwork_module.py` and
   `test_groundwork_fixture.py`: move the first; keep the second where `tests/support_install.py` imports it,
   or move it with a re-export. Record the choice.
2. The old gate (reports only when the committed manifest records `workbench/groundwork`; a project with the
   module and none of the folders gets none) must survive the move. It becomes structural, because the
   runner starts a helper only for a recorded module, and the helper keeps the second half itself. Tests:
   a project whose manifest lacks `groundwork` runs no helper and prints nothing, even with a hand-written
   `docs/specs`; a project with the module and no folders prints nothing; both are part of the line-for-line
   comparison.
   Write the helper as one file over the kit, with the same bounds and the same messages, printing
   `problem:` / `warning:` lines; declare it in `checks` with `kit` 1; remove `doccheck` and its call from the
   installer in the same commit, so there is never a commit where neither runs.
3. The owner runs `release-approvals` and approves removing stale records, then pins the helper for this
   repository (`pin` with the helper's name `doccheck` and `--kit 1`; the exact command is given in the
   increment's Result). I do not run either.

Verification: the moved tests, `test_check.py`, the full suite after the owner's steps. Evidence: after the
pin, `wb check` on this repository reports what it reported before, and the helper's output for a fixed
fixture equals the installer's former output, line for line.

### Increment F — `refcheck` and `refindex` move into `groundwork`

Outcome: `groundwork` ships `helper/refcheck`; the installer no longer reads the reference index.
Dependencies: E.
Affected areas: new `packages/workbench/groundwork/helper/refcheck`, `module.json`, the module's `tests/`,
`workbench/refcheck.py` and `workbench/refindex.py` (removed), `tests/test_refcheck.py` and
`tests/test_refindex.py` (moved), `tests/test_check.py`, `workbench/shipped_approvals/`.

1. Tests first: as E, including the no-`groundwork` and no-folder cases (`refcheck` used
   `doccheck.has_module`; the helper keeps its own check of the folder and the structural gate), for the
   reference rules; the index parser's refusals (entry and field named, value
   never repeated) are tested against the helper.
2. One file over the kit: the reader of `docs/references/index.json`, the tracked-set comparison and the
   `.workbench/local` rule. Remove the three installer modules and their calls.
3. The owner runs `release-approvals`, approves removing stale records, and pins `refcheck` with `--kit 1`.
   I do not run either.

Verification: as E. Evidence: the same line-for-line comparison on a reference fixture, and `wb check` on
this repository after the pin.

### Increment G — The approval request lists a module's checks

Outcome: `request.render_module` lists the helpers a module contributes as checks.
Dependencies: A.
Affected areas: `workbench/request.py`, `tests/test_request.py`, `docs/specs/trust-and-approval.md`.

1. Tests first, as for commands: none, shown in full, hostile strings cleaned to ASCII, a long list, and the
   section after the hashes.
2. Add a "checks it offers" section beside "commands it offers", each string through `_shown`.

Verification: `test_request.py`, the full suite. Evidence: the real `groundwork` module renders its two
helpers. (Run this increment after F so the real module has checks to show.)

### Increment H — Security pass, specification and result

Outcome: the runner and the two helpers are reviewed adversarially, the specifications describe what is
built, and the plan's result is recorded.
Dependencies: F, G.
Affected areas: `docs/specs/module-boundary.md`, `docs/specs/module-contract.md`, `docs/specs/groundwork.md`,
`docs/development.md`, this plan's review record and result.

1. Run the `security-reviewer` agent. The brief asks it to try: helper output with forged `problem:` lines,
   ANSI and bidi text, NUL, huge or unterminated lines and endless output; a helper that exits non-zero after
   printing; a check name that collides with an installer line; two modules in the manifest listed out of
   order; a `.workbench/<package>` link; a pin whose path or kit differs; a helper replaced between hash and
   run; and, for the two helpers, hostile repository content: links in place of `docs/` folders, huge or
   deeply nested directories, names with control or Unicode-fold characters, a huge reference index, a
   `.git/index` with a bad checksum or an enormous entry count, a tracked file that is a link, and a
   `.workbench/local` path in a title.
2. Fix each finding test-first; have a second pass try to bypass the fixes.
3. Bring the specifications in line (the "not built yet" marks, the inventory rows for the document checks and
   their tests, `groundwork.md`'s statement of where the checks run) and record the behaviour in
   `docs/development.md`. Write the Result.

Verification: the full suite; both passes recorded. Evidence: the review record lists what was accepted and
not fixed.

## Verification

After every increment: `python3 -B -W error tests/run_all.py`, `git diff --check`, and a check that no
`__pycache__` is under `packages/`. After E and F: the owner's `release-approvals`, then the suite again.

## Risks and sensitive actions

- **A check helper runs a program on every `wb check`.** It comes only from a module the manifest records,
  whose installed declaration matches the recorded hash, with bytes that match an owner-set pin whose path
  and kit equal the declaration. The security pass in H is aimed at the runner and at the report form.
- **A silent skip would hide damage.** An unpinned or changed helper is a problem, so after E `wb check` on a
  project with `groundwork` fails until the owner pins `doccheck` (and after F `refcheck`). Pinning is an
  explicit owner step in E and F (the pin store is not touched by `release-approvals`); the change in behaviour is recorded in `docs/development.md`.
- **A helper can produce endless output or hang.** Increment C bounds the capture and the run time in the
  launcher; the security pass tries it.
- **The helpers read hostile content.** The kit's no-follow readers and the bounds are the defence; the moved
  tests plus the security pass check them in their new place.
- **A sensitive action for the owner:** `release-approvals` after E and F, and `pin` for the helpers, which
  stay owner-run.
- **Output drift on the move.** The line-for-line comparison in E and F is the guard; any intended change is
  a separate plan.
- **Not tested in this plan:** Linux and Windows; a venv `sys.executable`; a very large project on a slow disk
  (the bounds are tested, not their timing).

## Review record

Codex review (`ask-codex review-plan`, model gpt-5.6-luna, medium effort), round 1 of 3, outcome
`changes_needed`, four findings. Applied by the author; the owner records each with `ask-codex decide`:

- **R1-F1 (major), applied.** The launcher has no timeout or output cap. Increment C now adds a bounded
  capture to `launch.launch` and its tests.
- **R1-F2 (major), applied.** Pinning the new helpers is now an explicit owner step in E and F with its
  evidence.
- **R1-F3 (major), applied.** Increment C states that exit 0 with empty output is valid and every other
  malformed case is a problem.
- **R2-F1 (major), applied.** Round 2 of 3. The groundwork gate is now stated for E and F: structural in the
  runner, plus the helpers' own no-folder quiet, with no-`groundwork` regression tests in the comparison.
  Recorded by the owner with `ask-codex decide R2-F1 applied`.
- **R1-F4 (minor), rejected.** The plan already ends with `## Deferred work` and `## Result` (the plan format
  names them "Deferred work" and "Result"); the reviewer's copy appears to have stopped at the review
  record.

Approved by the owner on 2026-10-21, after two Codex rounds (a third was offered and not run).

Security pass (increment H, `security-reviewer` run in a scratch copy, then a second pass that tried to bypass
the fixes). Fixed test-first:

- **High, fixed.** `gitindex.parse` counted only file paths against `MAX_PATH_BYTES`, but kept a string for each
  new ancestor directory, so a 4 KB path of 2,000 directories used about 4.7 MB. Both `wb check` and `refcheck`
  read the index this way. Directory names now count against the bound, each with `DIR_COST` (64) for the
  string and its set slot. The second pass measured at most 700 MB for the worst shape and 151 MB for a
  200,000-file, depth-8 tree, which is still accepted.
- **Low, fixed.** `launch_captured` did not stop the helper on an interrupt (it runs in its own session). The
  `finally` now kills it if it is still running.
- **Low, fixed.** `jsonstrict` repeated a duplicate key in its message, and a float token without a bound.
  The key is no longer repeated and the token is cut to 40 characters.

Accepted, not fixed:

- `refcheck`'s `.workbench/local` test in titles and notes is best effort; `.workbench%252Flocal` and
  `.workbench/x/../local` pass it. The text is only shown, never opened.
- Names and statuses (up to 120 characters, cleaned to ASCII) are shown in problem lines, so a hostile file
  name can read as an instruction to an agent. Inherent in naming the file; the lines sit under the module's name.
- A helper that detaches into a new session with `setsid` survives `_kill`, and a child that prints after its
  parent exits is dropped. This is a limit of the pin model: a pinned helper is trusted code, not sandboxed.
- A deleted manifest makes `wb check` run no module checks (no module is recorded, so none may run).
- `_kill` after a reaped helper could in theory hit a recycled process group (microsecond window, existing).
- A second exception inside `launch_captured`'s `finally` skips the remaining cleanup.
- Per-string memory beyond `DIR_COST` is not counted exactly; the bound is on the order of 0.6 GB for a 16 MiB
  index at worst.
- Not tested: case and Unicode-fold name collisions and invalid UTF-8 names (the macOS filesystem folds or
  rejects them), a file changing during a read (by reading only), and Linux.

Everything else in the attack list held, by test: forged and escaped lines, 200 and 201 lines, the 256 KiB
limit to the byte, the timeout, a helper that ignores `SIGTERM`, symlinked `.workbench` folders, a helper
swapped after hashing, links and fifos in `docs/`, a bad index checksum, a huge count, JSON bombs and a
configured `fsmonitor` that never ran.

## Deferred work

- `module-harness-paths`: the harness table and settings path leave the installer.
- Checks for modules other than `groundwork`.
- A faster path for projects with many checks (all checks start a Python interpreter each).

## Result

### Increment A

`declarations.parse_module` reads a `checks` list (`Check(helper, kit)` with a `pin_name` property, the last path
segment; `Module` gains `checks` after `commands`). Refused, naming the module and `checks`: more than 16
entries, an unknown field (so no `runtime` or `arguments`), a missing or non-integer `kit` (1 to 999999), a
helper that is not an item of `ships` or below one, one helper twice (or differing in case), a helper that is
also a command's, a pin name outside the helper-name form, two checks with one pin name, and a pin name equal to
a command name of the module (case and Unicode folded). `modulefiles` requires a check helper to be a file of the
module. `verify` adds rule `pin-name` across the selected modules for any collision that involves a check
(folded); command-only duplicates keep rule `command-name`. `module-contract.md` marks the field and the rule
built and `wb check` running a check not built. 13 new tests in `test_declarations.py`, `test_modulefiles.py`
and `test_verify.py`; `test_request.py` gains `checks=()` in two fixtures. No first-party module declares
`checks` yet, so no approval changed.
Verification: `python3 -B -W error tests/run_all.py`: 2207 tests in 3 roots, OK (2194 before); no `__pycache__`
under `packages/`. Not reviewed independently; H covers it.

### Increment B

Re-reading the three modules showed what they take from the installer: `writer.read_file` (absent is None,
a hard-linked file is refused), `writer.list_dir(..., lenient=True)`, `writer.git_bytes`, `gitindex`,
`declarations.parse_json` (for the index) and `manifest.parse` (for the module gate). The kit now has:
`Root.read_if_present`, `Root.list_dir` with `BAD_NAME`, `Root.git_bytes`, `wbkit/gitindex.py` (the parser, moved;
`workbench/gitindex.py` keeps `read(writer)` and calls it) and `wbkit/jsonstrict.py` (moved from
`declarations`, which calls it with its own byte limit). Existing kit functions are unchanged and `API` stays 1.
Not added: a reader of the manifest's modules, because the gate is structural (the runner starts a helper only
for a recorded module, `commands.resolve`-style, in installer code in C). Correction to the assumptions:
`refindex.parse` compares the bytes with `refindex.serialize`, so F inlines `serialize` too, together with the
few formatting helpers it takes from `manifest` (`_sorted_by`, `_path_key`, `_line`); they stay in the
installer's `manifest` and are copied into the helper, not added to the kit. 24 new tests in
`tests/test_kit_readers.py` (links at every component, a file where a directory belongs, hard links, size and
path limits, a closed root, bad names, the index through a held root, strict JSON refusals);
`tests/test_gitindex.py` patches the kit's limits; `test_kit.py` lists `struct`. `module-boundary.md` lists the
new readers.
Verification: `python3 -B -W error tests/run_all.py`: 2231 tests in 3 roots, OK (2207 before); one earlier run of
the same command printed `FAILED: tests` and two reruns passed, so a flaky test is possible and is not
identified; no `__pycache__` under `packages/`. Not reviewed independently; H covers it.

### Increment C

`launch.launch_captured(guarded, project_id, name, root, args, *, limit, timeout, kit=None, cwd=None)` runs a
pinned helper like `launch` (a shared `_prepare` does the pin, hash and private copy, so the checks are the
same) with its standard input closed, its standard output read in the caller up to `limit` bytes and for
`timeout` seconds, and the last 4 KiB of its standard error kept. It starts the helper in its own session,
and stops its whole process group at the end, on passing either bound and also after a clean exit, so a
child that kept the pipe open is not left running. It returns `Captured(code, stdout, stderr, over,
timed_out)`; `launch` and `wb run` are unchanged.
`workbench/checks.py` has `run_all(guarded, root)`: it reads the committed manifest (none: no sections; unreadable:
one `manifest` section with a problem), takes each recorded module's checks from its installed `module.json`
through `commands.installed_module` (split out of `commands._declared`, same messages), in manifest order
sorted by package and module, and for each check requires the pin named by the last segment of the helper path
to record exactly `.workbench/<package>/<module>/<helper>` and the declared kit, then launches it from the
project root with a 256 KiB and 120 second bound. Exit 0 with empty output is clean; every other case is a
problem worded "the check <name> failed ..." (non-zero exit with the start of its output or the last line of
its error, a line not in the report form, output not text or without a final newline, over the byte bound,
over the time bound), or "... is not pinned", "... not the declared helper", "... kit" or "... did not run";
more than 200 lines keep the first 200 and add a problem. A refused or failing check does not stop the
others; a module whose declaration hash changed is a problem for that module only. Returned lines are
cleaned ASCII of at most 300 characters and carry no prefix, for D to print under the module's name.
36 new tests: 23 in `test_checks.py` and 13 in `test_launch.py` for the captured launch (no orphan process
is left). `module-boundary.md` states the bounds.
Verification: `python3 -B -W error tests/run_all.py`: 2267 tests in 3 roots, OK (2231 before); no
`__pycache__` under `packages/`. Not reviewed independently; H covers it (the security pass should try a helper
that detaches into a new session and holds the pipe, and output that arrives just under the time bound).

### Increment D

`check.run` calls `checks.run_all(guarded, path)` after the installer's own checks and `Report` gained a
`modules` field (default `()`, so `examine` is unchanged and still read-only). Each module's lines are printed
as `warning: <package>/<module>: <text>` and `problem: <package>/<module>: <text>`, after the installer's own
lines; module problems count in "check found N problems" and make the exit code 1, warnings do not. The
existing output lines are unchanged. 5 new tests in `test_checks.py` (class `Command`, through `cli.main`):
lines under the module name, problem counted, warning alone exits 0, an unpinned helper is a problem while the
other check still runs, and a project without module checks prints exactly the earlier text (examine patched).
The 40-line display bound is shared, so a module that floods the report can push later lines into "and N more";
the count is always complete. `docs/development.md` records the behaviour.
Verification: `python3 -B -W error tests/run_all.py`: 2272 tests in 3 roots, OK (2267 before).

### Increment E

`groundwork` now ships `helper/doccheck` and declares it in `checks` (`kit` 1). The helper is the old
`workbench/doccheck.py` over the kit: one file, the same rules, bounds and messages, reading through
`Root.list_dir` and `Root.read_if_present` and printing one `problem:` line per finding. It no longer tests
whether the module is recorded: the runner starts a helper only for a recorded module, and a project with the
module and none of the folders prints nothing. One difference in the output: the report is capped at 200 lines
(199 findings and the "more document problems are not listed" line) where the installer's was 201, so the
runner's own 200-line bound is never what cuts it. The kit's reader also refuses a hard-linked document,
which the installer's did not; it is reported as "cannot be read".
`workbench/doccheck.py`, `tests/test_doccheck.py` and `tests/test_groundwork_module.py` are removed (with
`claude-workflow remove`, the plan naming them). `check.examine` no longer calls it, and `check.run` reports the
module sections after the installer's own. `refcheck` kept the one thing it took from `doccheck`: a private
`_has_module`, until F moves it. Tests: `groundwork/tests/test_doccheck_helper.py` (69 tests, the old document
rules run on the helper in process; the manifest-presence tests are gone because the runner is the gate) and
`groundwork/tests/test_groundwork_module.py` (moved; imports `support_install` only, as
`test_module_test_imports` requires, and gained an end-to-end test: `wb check` with the helper pinned reports a
badly named spec under `workbench/groundwork`, and without a pin reports the check as not pinned). New shared
support: `tests/support_doccheck.py` (loads the helper by path, with the kit as `wbkit`) and
`tests/support_docs.py` (the manifest and file fixture `test_refcheck.py` used from `test_doccheck.py`, until F).
`code-work`'s two agreement tests compare with the groundwork helper through `support_doccheck`.
`test_groundwork_fixture.py` stays where `support_install` imports it. `tests/test_checks.py` gained the
case the old gate needed: a recorded module that is not `groundwork` and hand-written `docs/specs` print nothing.
Evidence: the old module (from `HEAD`, with the gate bypassed) and the helper return the same list on a fixture of nine
findings across all three areas, and 0 on this repository's own documents.
Verification: `python3 -B -W error tests/run_all.py`: 2263 tests in 4 roots, OK. 103 tests in `tests/` and 3 in
`claude/tests` skip with "the shipped approvals are stale", because this change alters `groundwork`'s tree hash
(the one other skip is the macOS filesystem one). They run again after the owner's step, and the full suite
must be run again then.

Owner steps, not run by me:
1. `python3 -m workbench release-approvals`, then approve removing the stale records (`claude-workflow remove
   --recursive` on the previewed paths).
2. In a project that installs `groundwork`, pin the helper:
   `python3 -m workbench pin <project-id> doccheck .workbench/workbench/groundwork/helper/doccheck --root <dir> --kit 1`.
   This repository has no `.workbench/manifest.json`, so there is nothing to pin here and `wb check` cannot be
   compared against this repository; the fixture comparison above stands in for it.
Not reviewed independently; H covers it (the security pass should run the helper against hostile documents:
links, fifos, huge files, deep folders, and a name that is not valid UTF-8).

### Increment F

`groundwork` now also ships `helper/refcheck` and declares it in `checks` (`kit` 1). It is one file over the
kit holding the index reader and serializer from `workbench/refindex.py` (the strict shape, `parse`
comparing the bytes with `serialize`, the formatting helpers `_sorted_by`, `_path_key` and `_line` inlined) and
the comparison from `workbench/refcheck.py`; the tracked set comes from the kit's `gitindex.read`. It
prints `problem:` and `warning:` lines, at most 200 (problems first, then a "more findings are not listed"
line), and prints one problem if `.git/index` cannot be read. It no longer tests for the module: the runner is
the gate, and a project with no references prints nothing.
Differences from the installer's output, both from the kit's reader: a reference that is a link, not a regular file,
or hard-linked is reported as "cannot be read: <reason>" where the installer said "is a link or not a regular
file, so it was not read". The installer no longer reports the missing-index problem itself; the helper does,
under the module's name. `workbench/refcheck.py`, `workbench/refindex.py`, `tests/test_refcheck.py` and
`tests/test_refindex.py` are removed (with `claude-workflow remove`, the plan naming them) and `check.py` no
longer calls them. Tests: `groundwork/tests/test_refindex_reader.py` (the old reader tests, on the helper) and
`test_refcheck_helper.py` (the old rules, in process, with a hand-made tracked set; the no-module test and
the end-to-end class are gone), and three end-to-end tests in `test_groundwork_module.py` through
`wb check` with real git: a good index passes and a changed file is reported, a tracked reference with no
index is reported only once `refcheck` is pinned, and a repository that names a program (`fsmonitor`,
`hooksPath`) runs none. `tests/support_docs.py` is now a plain directory fixture and the documents the
helper tests write; `tests/support_doccheck.py` loads either helper.
Evidence: the old modules (from `HEAD`, loaded in process with the gate bypassed) and the helper produce the same
`serialize` bytes, the same five problems and one warning on a fixture index covering a changed hash, a missing
file, an entry git does not track, a tracked file with no entry, a note naming `.workbench/local` and a
missing license, the same two lines for a non-canonical index, and the same empty result on this repository.
Verification: `python3 -B -W error tests/run_all.py`: 2260 tests in 4 roots, OK. 104 tests skip with "the shipped
approvals are stale", because this change alters `groundwork`'s tree hash; the full suite must be run again
after the owner's step.

Owner steps, not run by me:
1. `python3 -m workbench release-approvals`, then approve removing the stale records.
2. In a project that installs `groundwork`, pin the second helper:
   `python3 -m workbench pin <project-id> refcheck .workbench/workbench/groundwork/helper/refcheck --root <dir> --kit 1`.
   This repository has no manifest, so there is nothing to pin here.
Not reviewed independently; H covers it (hostile index, links at every path component, huge files, entries that
claim the index or README, a git index naming programs).

### Increment G

`request.render_module` has a section "checks it offers (run by wb check)", after "commands it offers" and
the hashes: one line per check, `<helper> runs through kit API <n>; the owner pins it as <name>`, every string
through `_shown`, listed one to a line like the other sections and `none` for no check. 5 new tests in
`test_request.py`: none, shown in full, a hostile helper cleaned to ASCII, 16 checks one to a line, and the
section after the hashes and the commands. `trust-and-approval.md` says the request lists checks;
`module-contract.md` now marks the `checks` field built, including the request and `wb check`.
Evidence: the real `groundwork` renders `checks it offers (run by wb check)` with `helper/doccheck` and
`helper/refcheck`, each through kit API 1 and pinned under its own name.
Verification: `python3 -B -W error tests/run_all.py`, 2265 tests in 4 roots, OK (2260 before). This change does not touch any module's tree
hash, so no `release-approvals` step is needed. Not reviewed independently; H covers it.

### Increment H

The security pass is recorded in the review record above: one High and two Low findings fixed with
regression tests (`test_gitindex.py`, `test_launch.py`, `test_kit_readers.py`), the rest accepted with
reasons. The specifications already described the built behaviour after A to G, so no further change was
needed to them. The change touches the installer's kit (`workbench/wbkit`) and no module tree, so no
`release-approvals` step is needed.
Verification: `python3 -B -W error tests/run_all.py`, 2269 tests in 4 roots (2265 before). One run failed in the `tests` root and four later runs passed, so it is the same unidentified intermittent failure noted after B; its output was not captured.

## Outcome

All of A to H are done. `Status` is `Completed`; the owner archives or decides it.
