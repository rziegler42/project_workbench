# Get the full suite green on macOS

Status: Approved
Created: 2026-10-24
Candidate: none (four failures in completed work, found by the full suite on this machine after the `mempalace` merge)
Specs: mempalace

## Goal

The full suite (`python3 -B -W error tests/run_all.py`) ran on this macOS machine on 2026-10-24 over 3,956 tests in 9
roots and had four failures. None came from the documentation-only plan that was open at the time. The owner ran the
same suite on another computer before the merge, so the cause of three of them is the platform and not the code.

When this plan is done:

- the three `mempalace` tests that fail here pass here, and still pass where they passed before;
- the one intermittent `test_delegation` failure is either explained and fixed with a test that fails without the fix,
  or recorded as not reproduced after a stated bounded attempt, with what was tried;
- one full run on this machine is green, with the totals recorded.

## Scope

- Increment A: the `mempalace` module's test support and one test, both under `packages/workbench/mempalace/tests/`.
- Increment B: an investigation of the intermittent failure in `tests/test_delegation.py`, with a fix only if a cause is
  found.

## Non-goals

- Any change to `packages/workbench/mempalace/helper/mempalace`. The program passes the right environment; the tests
  are what assume a platform.
- Any change to a spec, a decision, or the roadmap.
- Any change to a root other than `mempalace` and, in increment B only, the installer root's `tests/test_delegation.py`,
  `workbench/approvalcmd.py` and `workbench/launch.py` (`launch_captured`, which `approvalcmd._capture` calls).
- A retry, a skip or a longer timeout added to make the delegation test pass. A failure is explained or left recorded.

## Assumptions and constraints

- Python standard library only; tests with `unittest`; the full suite takes about 7 minutes and is run with
  `run_in_background`, with no pipe, and read with `grep -E "^(==|Ran|OK|FAIL|ERROR|FAILED)" <output file>`. No source is
  edited while it runs.
- Editing files under `packages/workbench/mempalace/` stales that module's shipped approval. `release-approvals` is the
  owner's; I run it only on "Run it for me", and delete stale records only after a preview and "remove them".
- Observed on 2026-10-24 (Python 3.14.6, macOS, Darwin 25.6.0): a bare `env -i python3 -c "import os; print(sorted(os.environ))"`
  prints `__CF_USER_TEXT_ENCODING` among six variables, so the system gives every process that variable; the program
  under test did not pass it.
- The `mempalace` module suite failed the same three tests on a rerun (145 tests, 2 failures and 1 error). The
  `test_delegation` module passed in 12 of 12 isolated runs of 75 tests, each about 61 seconds, so the earlier failure
  is not a plain test-order or timing defect of the module on its own.
- Discovery tooling: graphify: skipped — not installed in this project; the scope was found by reading the three
  failing tests, `support_mempalace.py` and `workbench/approvalcmd.py`.

### Choices (made by me; the owner may change any)

1. **Drop the platform's variable in the fake program's recorder, not in the expected sets.** The fake in
   `support_mempalace.py` records `dict(os.environ)`. It would record that dict without the one key
   `__CF_USER_TEXT_ENCODING`, removed by exact name. Both environment tests then keep asserting the exact set the
   program passes, on every platform. The alternative, adding the key to both expected sets on macOS only, puts a
   platform branch in two tests. Cost: if the program ever passed that exact variable on purpose, the tests would not
   see it; the helper builds its environment from a fixed list, so this cannot happen by accident.
2. **Unique folder names by position, not by transformed text.** The failing test builds a folder per config name and
   per kind of obstacle, and two names that differ only in case (`.gitignore`, `.GitIgnore`) give the same folder on a
   case-insensitive volume. The folder name would start with the position of the case in the loop, so no two names
   can meet. The cases keep their file names, so the case variants still exercise the program. The alternative,
   skipping the case variants on macOS, would remove the cases that matter most there.
3. **The intermittent failure gets a bounded investigation, not a promised fix.** Increment B states the attempt in
   advance (below). If the cause is not found within it, the plan records that and the failure stays open under
   Deferred work. This is a change in how the plan can end, and the owner may prefer to drop B and open a candidate for
   it instead.

## Completion criteria

1. `env PYTHONPATH=. python3 -B -W error -m unittest discover -s packages/workbench/mempalace/tests -t packages/workbench/mempalace/tests`
   passes on this machine (145 tests).
2. The two environment tests still assert the exact set of variables the program passes, and a variable other than the
   one named in choice 1 would still fail them.
3. The case-variant names `ENTITIES.JSON`, `Mempalace.YAML` and `.GitIgnore` are still exercised for each of the five
   kinds of obstacle.
4. For `test_delegation`: a cause is found and a test that failed before the fix passes after it, or the attempt in
   increment B is recorded with its outcome and the failure is listed under Deferred work.
5. `python3 -B -W error tests/run_all.py` is green in all roots on this machine, with the totals recorded.
6. `release-approvals` reports no stale record for `mempalace`; `doccheck`, `refcheck` and `git diff --check` print
   nothing.

## Increments

### Increment A — Make the `mempalace` tests independent of macOS

**Outcome:** the three failing tests pass on macOS, with the same assertions.
**Dependencies:** none.
**Affected areas:** `packages/workbench/mempalace/tests/support_mempalace.py` (the fake program's recorder),
`packages/workbench/mempalace/tests/test_mempalace_owner.py` (the folder names in
`test_a_project_config_that_is_a_link_a_directory_or_shared_is_refused_so_the_program_cannot_write_through_it`).
**Steps:**
1. Run the module suite and see the same three failures: two `AssertionError`s naming `__CF_USER_TEXT_ENCODING` and one
   `FileExistsError` on `corpus-_GitIgnorelink_to_a_file`.
2. In the recorder, build `env` from `os.environ` without the key `__CF_USER_TEXT_ENCODING`, with a comment saying the
   system adds it to every process.
3. In the folder test, derive each folder name from a running position and the label, so that two names differing only
   in case cannot meet; remove the `.replace` chain that tried to separate them.
4. Run the module suite and see 145 pass. Run `tests.test_mempalace_run` and `tests.test_mempalace_owner` alone as well.
5. Check by hand that the exact-set assertions are unchanged in the diff, and that the five kinds of obstacle and the
   thirteen names remain in the loop.
6. Ask the owner for `release-approvals` (the edited test tree stales the shipped approval); preview and remove stale
   records only on the owner's word.
**Verification:** the module suite passes; `git diff --check` prints nothing; `release-approvals` reports nothing stale for
`mempalace`.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-green-the-full-suite#A`; the suite's count.

### Increment B — Find the cause of the intermittent delegation failure, or record the limit

**Outcome:** the failure "the convergence command's report is not one line ending in a newline" is explained and fixed
with a regression test, or the attempt below is recorded with its result.
**Dependencies:** A (so the full-suite runs below are not obscured by the three known failures).
**Affected areas:** this plan's Result and Deferred work; `tests/test_delegation.py` and, only if the cause is there, `workbench/approvalcmd.py` (the report
parsers) or `workbench/launch.py` (`launch_captured`, which runs a command and captures its output). No package file
is expected to change.
**The bounded attempt (in this order, stopping at the first reproduction):**
1. Read the test that exercises the convergence command and the code that captures its output, and list every way the
   captured bytes could lack a single trailing newline: a short read, a stop at the output limit or the deadline, a fake
   that writes in two parts, or a pipe closed before the last write. Record the list.
2. Run `tests.test_delegation` ten times while two copies of the same module run beside it as load. The earlier failure
   happened inside the full run, which also runs other roots, so load is the difference to test.
3. Run the full suite twice more in the background, one after the other, and read each result with the `grep` filter.
**Steps if reproduced:** write a test that fails the same way, with the cause fixed in the smallest place, and run the
module, then the full suite.
**Steps if not reproduced:** record the list from 1, the number of runs and what load was applied in the plan's Result,
and add the failure to Deferred work. Make no change to a test or a source file for it.
**Verification:** if reproduced, the new test failed before the fix and passes after it, and `python3 -B -W error -m
unittest tests.test_delegation` passes; otherwise the Result holds the record above and `doccheck`, `refcheck` and
`git diff --check` print nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-green-the-full-suite#B`. It holds the fix and its test if
the cause was found, and otherwise only the plan's Result and Deferred work.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots on this machine, run once more after both increments
  with nothing edited while it runs.
- `doccheck`, `refcheck` and `git diff --check` print nothing.
- No run on another computer is planned; the owner ran the suite there before the merge and may rerun it.

## Risks and sensitive actions

- **A test change can hide a real defect.** Choice 1 removes one variable by exact name from what the fake records, so a
  program that passed any other variable still fails the exact-set assertions. Choice 2 keeps every case.
- **The intermittent failure may not reproduce.** Then the plan ends with a record and an open item, which the owner
  has to accept, and a green full run proves only that this run was green.
- Sensitive actions: `release-approvals` and the removal of stale records are the owner's; I run them only on "Run it
  for me" and "remove them". Nothing is committed or pushed without the owner's word. Reviews run only when the owner
  asks.

## Review record

Rounds 1 to 3 of 3, 2026-10-24, `ask-codex review-plan`, model `gpt-5.6-luna`, effort medium (asked for by the owner).
Outcome: converged. Two findings, both major, both applied:

- R1-F1: increment B could end with no commit, against the rule that an increment produces exactly one. B now always
  produces one commit: the fix and its test if the cause is found, otherwise the plan's Result and Deferred work.
- R2-F1: B allowed a fix in the command-capture helper while the non-goals named only two files. `workbench/launch.py`
  (`launch_captured`, which `approvalcmd._capture` calls) is now named in both places.

Round 3 found nothing and checked both edits. Closed with `ask-codex archive` at 2026-10-24T16:27:18Z after 3 of 3
rounds, 2 decisions applied and 0 rejected, on the owner's word. A correction made while evaluating round 1: the
isolated `test_delegation` runs were 12 of 12, not 9 of 9.

## Deferred work

- The `mempalace` project scoping gap and the wording issues against the global memory rules, which are the roadmap
  candidate `mempalace-scoping` and are not part of this plan.
- The `test_delegation` failure, if increment B does not reproduce it.

## Result

Empty until the plan is implemented.
