# Retry the first append when a racing creator makes the open fail

Status: Completed
Created: 2026-10-28
Candidate: none — a defect found while investigating a flaky test, not a roadmap candidate
Specs: none

## Goal

Two writers that append to a file that does not exist yet must both succeed. Today one of them can
fail, and `tests/test_levellog.py` `ConcurrencyTest.test_parallel_appends_keep_every_line` fails about
half the time on this machine because of it.

## Scope

- `append_line` in `workbench/wbkit/safefs.py`: when the creating `os.open` fails with `ENOENT`,
  open once more.
- A deterministic regression test in `tests/test_safefs.py`.
- The sentence in the `safefs` module docstring that describes appending, so it states the retry.

## Non-goals

- No change to the flags, the held-descriptor design, the checks after the open (regular file, one
  link, size limit) or the one-`write`, synced append.
- No change to `levellog.py` or to the level-log format.
- No retry for any other error, and no loop, delay or sleep.
- No change to other `safefs` functions. Whether they have the same race is not examined here.
- No change to the test in `test_levellog.py`; it is the evidence that the fix works.

## Assumptions and constraints

- Root cause, found 2026-10-28 on Darwin 25.6.0 with Python 3.15.0: with several threads or processes
  creating one name through `openat(O_CREAT)` on a held directory descriptor, some opens return
  `ENOENT` although the directory exists. Measured outside the repository code: 713 of 1,200 opens
  failed across four racing threads, and 153 of 400 across four racing processes. Plain
  `O_WRONLY|O_APPEND|O_CREAT` fails as often, so `O_NOFOLLOW` and `O_NONBLOCK` are not the cause. A path
  based open with no `dir_fd` gave 0 of 1,200, and so did an open of a file that already existed.
- One retry is enough on that evidence: with one retry 0 of 2,400 racing opens failed, and with two
  retries 0 of 1,200. The first creator has made the file by the time the retry runs.
- A real `ENOENT` (the directory was removed) fails again on the retry and is raised through the
  existing `_os_error` path, so the error text and the exception type do not change.
- Linux behaviour was not measured. The retry is harmless where the race does not occur.
- `append_line` is used only by `workbench/levellog.py` (checked with a search of the tree).
- This edits a filesystem guard. The guard's refusals (symbolic link, directory, other hard link,
  size limit) must stay as they are.
- Discovery: graphify: skipped, no discovery tooling installed. One function with one caller, and the
  search above enumerated its use.

## Completion criteria

- The new test fails before the change and passes after it.
- `ConcurrencyTest.test_parallel_appends_keep_every_line` passes 100 of 100 runs in a loop.
- The existing `test_safefs.py` and `test_levellog.py` tests pass unchanged.
- The full runner `python3 -B -W error tests/run_all.py` passes.
- The docstring states the retry.

## Increments

### Increment A — Retry the creating open once on ENOENT

**Outcome:** `append_line` survives a creation race, and a test pins that.

**Dependencies:** none.

**Affected areas:** `workbench/wbkit/safefs.py`, `tests/test_safefs.py`.

**Steps:**

1. Write the regression test first. It patches `os.open` inside `safefs` so that the first call for
   the log name raises `FileNotFoundError` and later calls go to the real `os.open`, then calls
   `append_line` on a fresh directory and asserts the line is there once. A second test makes every
   open raise `ENOENT` and asserts `SafeFsError` with the existing "cannot open" text after exactly
   two calls.
2. Run them and see the first fail for the right reason (the unhandled `ENOENT`).
3. In `append_line`, open through a small local helper that tries `os.open` and, on `OSError` with
   `errno.ENOENT`, tries it once more; every other error and the second `ENOENT` go to the existing
   handlers unchanged.
4. Update the `safefs` docstring sentence about appending.
5. Run the two tests, then the loop of 100 runs of the concurrency test, then the full runner.

**Verification:** the commands in step 5, run and read, with the loop count recorded.

**Evidence that completes it:** the two new tests fail before and pass after; the loop result; the
full runner result; `git diff --check` clean.

## Verification for the plan as a whole

- The test-first record, the 100-run loop and the full runner, as in Increment A.
- The known flaky test is the one this plan fixes, so a runner failure in `test_levellog` after the
  change is a finding to report, not to retry.

## Risks and sensitive actions

- The change is in a guard that refuses unsafe files. The retry is a repeat of the same call with the
  same flags, so it opens nothing the first call could not; the checks that follow it are untouched.
- A retry could in principle hide a real `ENOENT` for one extra call. It does not, because a second
  `ENOENT` is raised unchanged.
- Security review: this materially touches the filesystem. The owner decides whether to run one with an
  installed module that provides `security-review`; none is run unless asked.
- No secrets, installs, pushes or deletions.

## Review record

No independent review. One happens only if the owner asks.

## Deferred work

- Whether other `safefs` functions that create through a directory descriptor have the same race.
- A measurement on Linux.

## Result

### Increment A — Retry the creating open once on ENOENT

Provenance: Darwin 25.6.0, Python 3.15.0, on top of `46c592c`, 2026-10-28.

- Tests first: the two new tests in `AppendCreateRaceTest` failed before the change. The first failed
  with the unhandled `ENOENT` raised as `SafeFsError`, and the second saw one open where two were
  expected. An earlier version of the tests failed for the wrong reason (a mock without `__name__`,
  then the `os.supports_dir_fd` capability check on the fake); both were fixed in the tests before the
  change was made.
- Change: `append_line` opens through the same call twice at most. Only `FileNotFoundError` is retried;
  every other error, and a second `ENOENT`, reaches the existing handler unchanged. The module
  docstring states it.
- After: `test_safefs` and `test_levellog` pass (75 tests). The concurrency test passed 100 of 100 runs
  in a loop, against 6 of 20 and 15 of 30 failing before. `python3 -B -W error tests/run_all.py`: 4,858
  tests in 10 roots, OK, with no failure of the formerly flaky test. `git diff --check` clean.
- Not done: Linux was not measured; other `safefs` functions were not examined for the same race;
  no security review was run.
- Next action: none in this plan once the commit is made; the plan can then be set to `Completed`.
