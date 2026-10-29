# Verify that a created file is the one that was written

Status: Proposed
Created: 2026-10-28
Candidate: none — the Lows of the owner-requested security review of Increment C of `2026-10-28-close-rerender-lows`, not a roadmap candidate
Specs: harness-refresh

## Goal

`Writer.create_file` writes a private sibling, links it to the final name and lists the path as written. The security review of
that change (no Critical, High or Medium finding) left three Lows:

- **Low 1.** Whoever can write in the project directory can replace the sibling between the fill and the link, with a symlink, a
  hard link to another file or a file of their own. `os.link` then makes the final name that object, `create_file` returns
  normally and lists the path as created and whole. Nothing outside the project is written, chmod'd or overwritten, and later
  reads refuse a link or a second hard link, but the claim "created, whole" is not checked. After this plan `create_file`
  confirms that the final name is the file it wrote, and refuses and does not list the path when it is not.
- **Low 2.** On a filesystem without hard links the create fails closed with a generic "cannot create" error. After this plan
  the error says that hard links are unsupported.
- **Low 3.** The spec says a later read "names" the stray second name after a crash, but the read names only the final path; the
  `create_file` docstring does not mention that the sibling is a 0644 file or the swap window.

## Scope

- `workbench/projectfs.py` (`Writer.create_file`) and its tests in `tests/test_projectfs.py`.
- `docs/specs/harness-refresh.md` ("Limits as built", the bullet on a new file written whole or not at all).

## Non-goals

- The same check in `Writer.replace_file`, which has the same window and the same premise (an attacker who writes in the project
  directory). Recorded under Deferred work.
- A fallback that copies the data on a filesystem without hard links: that would bring back a partly written file.
- Removing whatever sits at the final name after a failed check. The tool never deletes what it did not verify it wrote.
- Any change to who may call `create_file`, to the modes written or to the order of writes.

## Assumptions and constraints

- **My call (marked):** the check compares the device and inode that `fstat` gave the open sibling with `lstat` of the final name
  after the link, and requires a regular file with two links. A mismatch raises `WriteConflict` and does not list the path. It
  does not remove the object at the final name: the next run reads it and refuses a link or a second hard link, and a plain file
  of the attacker's would be read as an existing file or caught by the upgrade read-back hash.
- A path-based check after the link is still a check in time: an attacker could swap the final name again afterwards. This plan
  narrows the window and makes the claim honest; it does not close a race against someone who can write the directory.
- The reviewer ran on macOS only and could not read the diff or run Linux or a filesystem without hard links. Increment A tests
  on this machine; Linux behaviour of `os.link(..., follow_symlinks=False)` is not tested here.
- `workbench/` and `tests/` may not name a module, helper, harness or path other than the installer's own
  (`tests/test_boundary.py`).
- Nothing is run for security: no new dependency, no secret, no network. discovery tooling: skipped — none installed.

## Completion criteria

1. A sibling swapped for a symlink, for a hard link to another file or for another regular file before the link makes
   `create_file` raise `WriteConflict`, leaves the other file's content, mode and link count unchanged, and does not list the path.
2. An unswapped create behaves as before: the file is whole, has one link, takes the umask as before and leaves no sibling.
3. A failed link on a filesystem without hard links reports that hard links are unsupported and leaves nothing behind.
4. The spec and the docstring state what is checked, what is not, and what a later read names.
5. The full suite and `wb check` pass.

## Increments

### Increment A — Check the identity of the linked file (Low 1, Low 3)

**Outcome:** after the link, `create_file` confirms the final name is a regular file with the device and inode of the file it
wrote and two links; otherwise it raises `WriteConflict` and does not list the path. The docstring and the spec say what is checked.
**Dependencies:** none.
**Affected areas:** `workbench/projectfs.py`; `tests/test_projectfs.py`; `docs/specs/harness-refresh.md`.
**Steps:**
1. Write the tests first, using the `projectfs_filled` hook to swap the sibling: for a symlink to a file outside the project, for
   a hard link to a file outside, and for a different regular file. Each expects `WriteConflict`, the outside file unchanged, and
   `rel` absent from `written`. See them fail (today the call returns and lists the path).
2. In `create_file` keep `(st_dev, st_ino)` from `os.fstat(fd)` before the descriptor is closed; after `os.link`, `lstat` the final
   name relative to the directory descriptor and compare. Make the tests pass.
3. Confirm the existing tests still pass: whole-or-nothing, one link, umask, the conflict cases.
4. Correct the docstring (the 0644 sibling, what is checked after the link, the remaining window) and the spec: a later read
   refuses the finished file by its final path, and removing the stray sibling clears it.
**Verification:** the new tests red then green; `tests.test_projectfs`, `tests.test_adopt`, `tests.test_refresh`, `tests.test_rerender`;
the full suite `python3 -B -W error tests/run_all.py`; `git diff --check`; `wb check`; `wb run code-work check`; a `reviewer` pass.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-verify-created-file-identity#A`.

### Increment B — Say that hard links are unsupported (Low 2)

**Outcome:** when `os.link` fails with `EPERM`, `ENOTSUP` or `EMLINK`, the error says the filesystem does not support hard links
there; nothing is left behind and the path is not listed.
**Dependencies:** Increment A (same code).
**Affected areas:** `workbench/projectfs.py`; `tests/test_projectfs.py`; `docs/specs/harness-refresh.md`.
**Steps:**
1. Write the test first: make `os.link` raise each of the three errors and expect the message and no leftover sibling; see it fail.
2. Map those errors in `create_file`; any other error keeps the generic message.
3. Say in the spec that the message names the cause.
**Verification:** the new test red then green; `tests.test_projectfs`; `git diff --check`; `wb check`; `wb run code-work check`; a
`reviewer` pass.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-verify-created-file-identity#B`.

## Verification for the plan as a whole

The full suite `python3 -B -W error tests/run_all.py`, `wb check` and `git diff --check` after Increment B.

## Risks and sensitive actions

- `create_file` is shared by install, adopt, add, upgrade and rerender; a wrong check would refuse a good create. The
  existing tests for every caller cover the unswapped path, and a link count other than two (another legitimate hard link made in
  the same instant) is refused, which fails closed.
- The check touches filesystem trust, so each increment gets the `reviewer` pass. A second security review runs only if the owner
  asks.
- Nothing is pushed or published by this plan.

## Review record

Empty until a review is asked for.

## Deferred work

- The same identity check in `Writer.replace_file`, which has the same window; a separate plan if the owner wants it.
- Linux and a real filesystem without hard links are untested.
- The `Partial` message in `refresh.write` still says "may be partly written", and `tests/test_projectfs.py` lacks `import unittest.mock`;
  both cosmetic and not part of this plan.

## Result

### Increment A

- **Done.** `Writer.create_file` keeps `os.fstat` of the sibling and, after the link, reads the final name without following a
  link: it must be a regular file with the same device and inode and two links, else `WriteConflict`, the path is not listed and
  the object there is left alone. Docstring and the spec bullet say what is checked and that a later read refuses by the final
  path. The spec also notes the two-link condition assumes honest link counts and was tried on macOS (APFS) only.
- **Tests (red first).** Three swap tests (symlink to an outside file, hard link to an outside file, another regular file) failed
  with "WriteConflict not raised" before the change and pass after. A fourth, added after review, makes a second hard link to the
  sibling (link count 3) so the count clause is covered on its own.
- **Verification as run.** `tests.test_projectfs.WriterTest tests.test_adopt tests.test_refresh tests.test_rerender
  tests.test_boundary` 214 tests OK; the full suite 5928 tests in 12 roots OK (started before the fourth test and the spec note
  were added, which were then covered by the targeted run); `git diff --check`, `wb check`, `wb run code-work check` clean.
- **Review.** One `reviewer` exchange, no blocking finding. Applied: the link-count test and the spec note. Not applied: asserting
  the outside file's link count (it differs by case) and what is left at the final name after a refusal (documented, a non-goal).
  Kept the link-count clause as the plan chose.
- **Not done.** Linux and a filesystem that reports link counts oddly were not tried.

### Increment B

- **Done.** A failed `os.link` with `EPERM`, `ENOTSUP` or `EMLINK` now raises `SafeFsError` "cannot create <path>: the filesystem
  does not allow hard links there (<OS text>)"; any other error keeps the generic message, and a conflict is still a
  `WriteConflict`. The spec bullet names the message.
- **Tests (red first).** One test over the three errors (message names hard links, not a `WriteConflict`, no sibling left, path not
  listed) failed before the change; a second checks that another error (`EIO`) keeps the generic message.
- **Scope touch.** The tests need `unittest.mock`, so `import unittest.mock` was added to `tests/test_projectfs.py`. That also
  fixes the older test that errored when the file ran alone, so the "Deferred work" line saying the import is missing is now stale.
  The plan's Deferred work was not edited (an approved plan changes only in status, review record and result).
- **Verification as run.** `tests.test_projectfs tests.test_adopt tests.test_refresh tests.test_rerender tests.test_boundary`
  250 tests OK; the full suite 5931 tests in 12 roots OK; `git diff --check`, `wb check`, `wb run code-work check` clean.
- **Review.** One `reviewer` exchange, no blocking finding. `EPERM` can also come from a sandbox denial, but the OS text stays in
  the message and the failure is closed, so the mapping was kept. No caller or test matches the old text.
- **Not done.** Only mocked errors were tried; no real filesystem without hard links, and no Linux.

### Plan as a whole

Both increments are done (A `c91d26e`; B uncommitted until the owner says commit). Completion criteria 1 to 5 are met on this machine
by the suite and the checks above. Deferred: the same identity check in `replace_file`, Linux, and the cosmetic `Partial` wording.
