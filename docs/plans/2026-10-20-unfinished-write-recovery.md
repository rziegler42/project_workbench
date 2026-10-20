# Unfinished-write recovery

Status: Approved
Created: 2026-10-20
Candidate: none (follow-up to `workbench-v1#ownership-and-upgrade`: it closes limits recorded in
that plan's Result and is not a roadmap candidate)
Specs: installer-interface

## Goal

Make a failed or interrupted `install`, `upgrade` or `add` recoverable by a command instead of
by hand. Today the marker `.workbench/local/incomplete` is an empty file. After a failure the
owner is told to put files back from version control and delete the marker themselves, and a
rerun after that cannot tell which plan was half applied. The recorded consequence
(`2026-10-20-ownership-and-upgrade`, Result, "Known limits") is that a rerun can write a new
manifest while file conflicts from the failed run remain.

When this plan is done the marker records the plan that was being written. Every command that
meets a marker says which plan it was and, path by path, whether the project holds the state
before it, the state after it, or something else. A new owner-run command, `wb recover`, removes
the marker only in these states, and refuses every other with the list of paths to deal with:
files `before` and store `none`; files `after` and store `all`; and, for `upgrade` and `add` only,
files `after` and store `none`, where the project's old baselines still exist, so the project
differs from them and `wb acknowledge` then lists exactly the written paths for the owner to
accept. For `install` there are no old baselines, so files `after` with store `none` or `partial`
is refused with the advice to put the files back (the before state) and install again; the
workbench does not repair a store.

## Scope

- **Marker content.** The marker holds a strict JSON record of the plan: the command, the project
  id (when known), the workbench version, for every file write the path, operation, the hash the
  file had before (none for a create) and the hash it will have after, and for every guarded-store
  write (`install`'s entries, `upgrade`'s and `add`'s baselines) the store path and the hash it will
  have after, and every directory the plan creates (for `install`, `.workbench` and the module
  and namespace directories) and, when the plan makes the `.git` skeleton, each of its files with
  the hash it will have. The record is written when the marker is made, before any other write. A marker that
  is empty (made by an earlier version) or unreadable is reported as "no record" and is never trusted.
- **Examination.** A read-only function that reads the record and classifies each recorded project
  path through no-follow descriptors as `before`, `after` or `other`, and each recorded store entry
  by the guarded store's own read as `absent`, `after` or `other`. It summarises the files as
  `before`, `after` or `mixed`, and the store as `none`, `all` or `partial`. The store is written
  only after every file, so the combinations that occur are: files before and store none (nothing
  happened, or the owner restored them); files after and store none, partial or all.
- **Reporting.** The refusal `target.py` makes for a marker (all commands, including previews)
  names the plan and prints the examination. `wb recover` is named as the way forward.
- **`wb recover [<target> | --dir <path>]`.** Owner-run and terminal-only, as `acknowledge` is:
  the terminal check comes first, then the examination and a typed digest bound to the record, the
  examination and the target identity. After the answer the project is examined again and a
  different digest is refused. On an accepted state (above) it removes the marker (and the `local`
  directory only if it is empty and was made for it). In the files-`before` state it also removes
  each recorded directory that exists and is empty, deepest first, with `rmdir` only, so a
  failed `install` leaves the target as it was (empty, or a lone `.git`) and the install can be
  rerun. A recorded directory that holds anything, or a partly written `.git` skeleton, is
  `other`, so it is refused and listed. `recover` never writes a file, never removes a file other
  than the marker, never removes a non-empty directory, and never removes the target directory.
- **Scan limits from the E and F reviews** (separate increment): a path name the baseline scan
  cannot accept is listed as a difference and cannot be acknowledged, instead of making the whole
  scan refuse; the scan keeps a cumulative byte budget.

## Non-goals

- No automatic repair and no rollback. The workbench never deletes or restores project files; the
  owner puts files back from version control or a copy, as the failure message already says. The
  only removals are the marker and, from the before state, empty directories the plan itself
  recorded as created.
- No change to what a plan writes, its order, or its digest rules, other than the marker's bytes.
- No resume of a half-applied plan. After `recover` from the before state the owner runs the
  command again (the target is a new project again only for `install`; for `upgrade` and `add`
  it is the old project). From an after state nothing is rerun: the project is complete, and
  `install` is not repeated on it.
- No change to the acknowledgement baselines or the guarded store format.
- `attach`, `check` and the harness work stay in `claude-harness`.

## Assumptions and constraints

- Python standard library only; tests with `unittest`. Full suite:
  `python3 -B -W error -m unittest discover -s tests` (1143 tests today).
- The marker is untrusted text, like the manifest: anyone with write access to the project can
  edit it. It carries no authority. A forged marker can do no more than a hand-removed one:
  `recover` removes only the marker and recorded empty directories, and only after the owner types the digest of
  what was shown. Recorded paths pass the same relative-path rules as manifest paths, may not be
  under `.workbench/local`, and are read through no-follow descriptors only.
- The marker is written before the digest-bound plan is carried out and lives in
  `.workbench/local`, which acknowledgement ignores; its content must not change the plan's
  digest, so the record is built from the plan after the digest is fixed.
- A record is bounded (entry count and bytes) and refused beyond the bound, as the manifest is.
- Decided by me and approved with the plan: `recover` is a new command, not a flag on
  `upgrade`, because it must work for an unfinished `install` too and must not need a package.
- Discovery: graphify — skipped, this project has no discovery tooling. The files involved
  (`projectfs.py`, `target.py`, `install.py`, `upgrade.py`, `installplan.py`, `acknowledge.py`
  as the model for a terminal-only command, `cli.py`) were read for this plan.

## Completion criteria

1. After a forced failure at each stage of `install`, `upgrade` and `add` (files, store, marker
   removal) and after an interrupt, the marker holds a valid record and the failure report names
   `wb recover`.
2. A marker that is empty, truncated, oversized, has unknown keys, a path outside the project, a
   path under `local`, a duplicate path or a bad hash is reported as "no record" and never
   changes the examination into `before` or `after`.
3. The refusal for a marked target shows the examination; it is identical for `preview`,
   `upgrade`, `add`, `acknowledge` and `recover`.
4. `wb recover` removes the marker (and, from the before state, the recorded empty directories)
   in the accepted states of Scope, refuses any other without writing, refuses
   without both streams being terminals before anything is read, refuses when the project changed
   after the answer, and removes nothing but the marker and the recorded empty directories.
5. After `recover` from the before state, rerunning the same command gives the same project and
   store as an uninterrupted run (test: compare the tree and the store entries), for `install`,
   `upgrade` and `add`. After `recover` from an after state the project and store equal an
   uninterrupted run's without a rerun (`install` is not rerun; `upgrade` and `add` find nothing to
   change). From files `after` with store `none`, `acknowledge` accepts exactly the written paths
   and a following `upgrade` finds nothing to change.
5b. A failed `install` stopped at each point (marker only, after the directories, during each
   file of the `.git` skeleton, during the files) recovers from the before state to a target that
   `install` accepts again, or is refused with the paths to deal with; a partial `.git` skeleton is
   never accepted.
5a. Every ordering of a store failure is tested for each command: no store entry written, some
   written, all written with the marker not removed. Each gives the outcome Scope states, and
   `install` with files after and an incomplete store is refused with the restore advice.
6. The scan limits increment lists a hostile name as a difference and enforces the byte budget,
   each with a failing-then-passing test.
7. `docs/development.md` and `installer-interface.md` describe the marker record, the command and
   its exit codes; the full suite passes with `-W error`.

## Increments

### Increment A — The marker record

**Outcome:** the marker carries the plan; nothing reads it yet.
**Dependencies:** none.
**Affected areas:** new `workbench/unfinished.py` (`build(command, project, version, writes)`,
`parse(data)` raising `UnfinishedError`), `install.py`, `upgrade.py`, `installplan.py` (marker
bytes), `projectfs.py` (create the marker with its bytes), their tests.
**Steps:**
1. Failing tests for `build`/`parse`: a round trip; every case in criterion 2.
2. Include directories and the `.git` skeleton files in the record (taken from the install plan's
   `create-dir` and `git-init` actions; the skeleton's paths and hashes from `GIT_SKELETON`; its directories have no hash).
   Implement the strict record (canonical JSON, format number, bounds, project path rules shared
   with the manifest reader, store path rules shared with the guarded store, not copied).
3. Install and upgrade/add build the record from their final plan and create the marker with it.
   The marker action stays first in the order.
4. Tests that a forced failure leaves a marker whose record equals the plan, and that the plan's
   digest is unchanged by the record.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-20-unfinished-write-recovery#A`.

### Increment B — Examine and report

**Outcome:** a marked project is described instead of just refused.
**Dependencies:** A.
**Affected areas:** `unfinished.py` (`examine(writer)`, `render(...)`), `target.py` (the marker
refusal carries the report), `confirm.report_failure` and the `RECOVERY` texts (name `wb recover`).
**Steps:**
1. Failing tests: `before`, `after`, `mixed` and `other` (a link, a directory, an unreadable file
   at a recorded path); an unreadable or missing record; hostile strings rendered through
   `display.ascii_text`.
2. Implement `examine`; read each project path through no-follow descriptors, regular files only,
   with the size limits the project reader uses, and each store entry through the guarded store.
   Failing tests for every combination of files and store states in Scope.
3. Wire the report into the refusal, with the list capped like `acknowledge` (500).
4. Update the failure hints.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-20-unfinished-write-recovery#B`.

### Increment C — `wb recover`

**Outcome:** the owner clears a uniform unfinished write with a typed digest.
**Dependencies:** B.
**Affected areas:** new `workbench/recover.py` (modelled on `acknowledge.py`), `cli.py` (route
and usage), `projectfs.py` (remove the marker and an empty `local`), tests including a pty case
(`tests/support.drive_pty`).
**Steps:**
1. Failing tests: uniform before; uniform after; mixed; no record; not a terminal; a wrong or
   short answer; project changed after the answer; typed-ahead input discarded; nothing but the
   marker and the recorded empty directories removed (tree comparison); a marker that is a link or
   directory; a recorded directory that holds a file or link; each stop point of criterion 5b.
2. Implement `parse`, `examine`, `render`, `run` with the exit codes of `acknowledge`: 0 done or
   nothing to recover, 1 refused or cancelled, 3 removal failed, 130 interrupted.
3. Criterion 5 and 5a chain tests with `install`, `upgrade` and `add`, including the
   `recover`, `acknowledge`, `upgrade` chain.
**Verification:** new tests, a recorded pty hand run, the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-20-unfinished-write-recovery#C`.

### Increment D — Scan limits

**Outcome:** the E and F leftovers recorded in the earlier plan are closed.
**Dependencies:** none technical; ordered last because it is independent of A to C.
**Affected areas:** `acknowledgement.py` (`differences`, the walk), `acknowledge.py`
(refuse listing of un-acknowledgeable names), their tests.
**Steps:**
1. Failing tests: a name the scan cannot accept (non-UTF-8, control character) yields a
   difference with a reason and `acknowledge` shows it as not acknowledgeable instead of the
   whole scan refusing; a tree past the cumulative byte budget refuses with a clear message.
2. Implement both; keep the existing per-file and entry limits.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-20-unfinished-write-recovery#D`.

### Increment E — Documentation

**Outcome:** the specification and development guide match the build.
**Dependencies:** A to D.
**Affected areas:** `docs/specs/installer-interface.md`, `docs/development.md` (command table,
exit codes, limits), the earlier plan's Known limits (note, in its Result, that they are closed;
status and result edits only).
**Steps:** edit the docs; add a decision record only if the owner asks (the marker format is
recorded in the spec, not as a decision).
**Verification:** `git diff --check`; every claim in the new text matched to a test or a run.
**Evidence:** commit with trailer `Plan: 2026-10-20-unfinished-write-recovery#E`.

## Verification for the plan as a whole

- Full suite with `-W error`, run after every increment and recorded in the Result.
- A hand run in a pseudo-terminal of a forced failure, `recover`, and a rerun (recorded in the
  Result as the earlier plan did).
- An independent adversarial review of A to C by `security-reviewer` (hostile marker content,
  swapped target, links at recorded paths, an edited marker between the answer and the removal),
  because this reads untrusted text and removes a file. Findings are fixed or recorded.

## Risks and sensitive actions

- **A forged or stale marker misleads the owner.** Mitigation: the report states plainly that the
  record is unauthenticated text; `recover` only removes the marker; the owner reads the list and
  types the digest.
- **Partial store writes.** The store is written after the files and is not transactional.
  Mitigation: the record covers store entries; `recover` accepts only the states in Scope and
  never writes the store; the install case that cannot be repaired is refused with the restore
  advice rather than guessed at.
- **Recorded `before` hashes make `recover` look safer than it is.** A `before` state still
  needs the owner to have restored files; `recover` does not restore anything and says so.
- **The record could grow the marker beyond a sane size.** Bounded; refused beyond the bound.
- **Changing install's marker bytes touches the install path.** Covered by the existing install
  tests plus criterion 1; the marker stays first in the write order.
- Sensitive actions: file removal inside the project (the marker only), reading attacker-chosen
  paths. No network, no secrets, no new dependencies.

## Review record

Round 1 (`ask-codex review-plan`, model gpt-5.6-luna, medium effort), outcome `changes_needed`,
two major findings, both accepted and applied:

- R1-F1: criterion 5 asked for a rerun that is impossible after an after-state recovery (the
  target is then an existing project). Rewritten to separate before-state reruns from after-state
  completion.
- R1-F2: the record covered project files only. It now covers guarded-store writes, the
  examination classifies them, and `recover` states which file and store combinations it accepts
  and what it does for `install` where no old baselines exist.

Rounds used 1 of 3. R1-F1 and R1-F2 were recorded as `applied` by `ask-codex decide`.

Round 2 (same model, medium effort), outcome `changes_needed`, two major findings, both accepted
and applied:

- R2-F1: a failed `install` can leave `.workbench` and other empty directories, so the target is
  no longer empty and an install rerun is refused. The record now lists the directories the plan
  creates, and `recover` removes the recorded ones that are empty (`rmdir` only) from the before
  state. Non-goals and criteria 4 and 5b changed to match.
- R2-F2: the `.git` skeleton was not in the record. Its files and hashes are now recorded; a
  partly written skeleton is `other` and refused. Criterion 5b and the C tests cover each stop
  point.

Rounds used 2 of 3. R2-F1 and R2-F2 were recorded as `applied`. The owner chose not to run round 3 and approved the plan on 2026-10-20.

## Deferred work

- Resuming a half-applied plan from its record.
- A cumulative byte budget for the project reader (`installed.read`) as well as the scan, if
  the review of D shows it matters.
- Directory fsync, ownership and ACL preservation, and the other items under D in the earlier
  plan's Known limits.

## Result

### Increment A — done

- New `workbench/unfinished.py` (`build`, `parse`, `UnfinishedError`). The record is canonical
  JSON (format 1) with the command, project id, workbench version, directories, file writes
  (path, op, before, after), the `.git` skeleton (path, hash or none for a directory) and store
  writes (path, after). `parse` takes only the writer's own layout, goes through the manifest's
  JSON reader (1 MiB bound, duplicate keys and nesting refused), uses `safefs.validate_relpath`
  for project and store paths, refuses paths at or under `.workbench/local`, duplicates and a
  path that is both file and directory. An empty marker is "no record".
- `install.record_of` and `upgrade.record_of` build the record from the final plan after its
  digest is fixed; `installplan.py` is unchanged, so the digest and the rendered plan are
  unchanged. A plan that cannot be recorded is refused before anything is written. The marker
  stays first in the write order and is created with the record instead of empty bytes.
- Known difference: the rendered install plan still shows the marker action as 0 bytes; the
  file written is the record. The marker is bookkeeping and is not in the digest or baselines.
- Tests: `tests/test_unfinished.py` (18) and `tests/test_marker_record.py` (13): the record
  after a failure among the files, at the git skeleton, at the store and on an interrupt for
  `install`; after a file failure and a store failure for `upgrade` and `add`; the record
  against what an uninterrupted run writes; an unrecordable plan writes nothing. Full suite
  with `-W error`: 1174 tests, passing.
- Not covered by a test yet: an `upgrade` plan that creates a new directory (the record's
  `dirs` is covered for `install` only); the record's use is Increment B.
- Independent read-only review of A (`workflow-reviewer`): the record matched what the commands
  write; two hardening findings were fixed with tests. Paths are now compared as a
  case-insensitive, Unicode-normalizing filesystem would (NFC, case folded, trailing dots and
  spaces ignored): `.workbench/LOCAL/x` and `.workbench/local /x` are refused, duplicates and a
  file below another file or a directory below a file are refused on folded names. The reviewer
  could not run scratch experiments, so these rest on the new tests; the `security-reviewer`
  pass over A to C should try them again. A plan of more than about 5,000 files cannot be
  recorded (1 MiB bound) and is refused with nothing written; note this in Increment E.
  Suite after the fixes: 1177 tests, passing.

### Increment B — done, committed as `8208f2b`

- `unfinished.examine(writer, store_root)` and `render`. Each recorded file is read through
  `Writer.read_file` (no-follow, regular, one link) and classed before/after/other, with a
  cumulative read budget of 256 MiB (the rest is "not read"). Recorded directories are
  absent/empty/holds/other (`Writer.dir_holds`: child names that are recorded directories, and
  `local` under `.workbench`, do not count as content). The `.git` skeleton is read with the new
  `Writer.git_entry` (no-follow, regular files of at most 64 KiB). Store entries are read through
  `store.Tree`. Summaries: files before/after/mixed, store none/all/partial; any `other` makes
  files mixed and the store partial.
- Deviation from the plan, found by the first test run: for `upgrade` and `add` the baselines
  entry already exists before the write, so "absent/after/other" cannot describe it. Each
  recorded store write now also carries `before` (null for `install`, the hash of the existing
  baselines for `upgrade` and `add`), and a store entry is before/after/other. This changes the
  record format that Increment A introduced; nothing outside this plan reads it. `upgrade.
  record_of` now takes the store and reads the current baselines.
- A complete `.git` skeleton with no file written is "before" (a lone `.git` is a target that
  `install` accepts); a partial or foreign `.git` is "mixed" and listed.
- `target.open_target` builds the report when it meets a marker; `UnfinishedMarker` carries it as
  `report`, and the five places that print a target refusal now call `target.write_refusal`, so
  the text is identical for `preview`, `install`, `upgrade`, `add` and `acknowledge`.
- Hints: `RECOVERY`, `RECOVERY_FILES_DONE` and `confirm.report_failure` name `wb recover`, which
  is built in Increment C; until then the name is not a working command.
- Tests: `tests/test_unfinished_examine.py` (26) cover each stop point, links, a directory, a
  hard link, an unreadable file, a foreign store entry, a missing store, a foreign file in a
  recorded directory, the read budget, no-record markers, escaping, the 500 cap, no writes while
  examining, and the identical refusal across commands. Suite: 1203 tests, passing.
- Independent read-only review of B (`workflow-reviewer`, partial: it ran out of turns and could
  not run scratch code). Fixed with tests: a quadratic scan of recorded directories (a forged
  marker with ~100k directories hung every command; now one pass and a 10,000 entry cap in
  `parse`); the report listed directories that legitimately hold files after a finished write;
  a record with no files or no store writes read as "before"/"none" (now mixed/partial, so C
  must never treat them as safe); `upgrade.record_of` recorded a non-file baselines entry as
  absent (now refused before any write); store reads now count against the read budget. Added
  tests for `install`/`preview install` refusals, a `.git` link, a recorded directory that is a
  file, a FIFO, `dir_holds`/`git_entry`, and fd closing in `open_target`. Suite: 1217 tests,
  passing. Not exercised: case-insensitive variants of `dir_holds` ignore names.

### Increment C — done, not yet committed

- New `workbench/recover.py` (modelled on `acknowledge.py`), routed by `cli.py` and listed in the
  usage text. Terminal check first; then `unfinished.examine`, the rendering and a typed 12
  character digest. The digest covers the marker's canonical bytes (`unfinished.fingerprint`),
  the examination items, the removal steps, the summaries and the target's device and inode.
  After the answer the target is rechecked and examined again; a different digest, or a state
  that is no longer acceptable, removes nothing. Exit codes: 0 done or nothing to recover, 1
  refused or cancelled, 3 removal failed or interrupted, 130 interrupted at the prompt.
- Accepted states: files before with store none (marker and recorded empty directories go);
  files after with store all (marker goes); `upgrade` and `add` with files after and store none
  (marker goes, `wb acknowledge` is named). `install` with files after and store none or partial
  is refused with the advice to put the project back and install again. Everything else is
  refused with the paths to deal with, and nothing is written. A forged record with no files or
  no store writes, a partial or foreign `.git`, a marker that is a link or a directory, and a
  recorded directory that holds anything (also `.workbench/local` holding more than the marker)
  are refused.
- Removal order: recorded empty directories deepest first, then the marker, then (only when the
  plan made `.workbench`) `.workbench/local` and `.workbench`, so a directory that cannot be
  removed leaves the marker and the record in place. Only `rmdir` and the existing
  `remove_marker` are used (`Writer.remove_empty_dir` is new: no-follow walk, a link or file in
  the way is a conflict, the target cannot be named). The target directory is never removed.
- `target.open_target(..., marked=True)` returns a marked target as `existing`; every other
  refusal is unchanged (tested for a link, a file and the home directory).
- Known limits: the marker is unlinked by name a moment after the second examination, so a
  marker swapped inside that window is removed instead of the one shown (the same check-then-act
  limit as `replace_file`); the new marker is also just a marker. `recover` for an `install` is
  possible only from the before state, which means the owner has put things back by hand first.
- Tests: `tests/test_recover.py` (49): both from-before and from-after states for `install`,
  `upgrade` and `add` with the rerun compared to an uninterrupted run (tree and store entries);
  `recover`, `acknowledge`, `upgrade` chains for `upgrade` and `add`; each stop point of
  criterion 5b including every prefix of the `.git` skeleton; store none, partial and all; no
  record, link, directory and forged markers; recorded directories holding a file, a link or a
  directory; a swapped target; a project and a marker changed after the list; typed-ahead input;
  no terminals; usage; the exit codes 3 and 130; and three pty cases that run the real command
  in a pseudo-terminal. Suite with `-W error`: 1266 tests, passing.
- Hand run in a pseudo-terminal (forced failure of the first file of an install, `recover`, then
  the install again), 2026-10-20: the install exited 3 and named `wb recover`; `recover` showed
  `files before (8 before, 0 after, 0 other), store none (0 of 2 written)`, the nine removals
  (eight directories and the marker) and a digest; typing its first 12 characters printed
  `cleared the marker` and exited 0; the target held only `.git`; the install then exited 0.
- Independent read-only review of C (`workflow-reviewer`): no Critical or High findings; nothing
  but the marker and recorded empty directories can be removed. Two Low findings fixed with
  tests: the digest covered more removals than the 500 listed (now refused past 500, as
  `acknowledge` does), and a marker that vanished before the unlink, or an interrupt after it,
  was reported as "still there" (now counted as removed / reported as gone). Case-variant
  recorded paths are read as safe (`.WORKBENCH` is "holds" and refused) but have no test.
  Suite: 1269 tests, passing under `-W error`.
- Adversarial `security-reviewer` pass over A to C (scratch copy, real experiments): no
  Critical, High or Medium findings. Verified by experiment: case variants of `.workbench` (on a
  case-insensitive volume), hostile and bidi names, links and FIFOs at recorded paths and at the
  marker, a recorded directory or parent swapped for a link before and after the second
  examination (the outside tree survived), `.workbench/local` as a link, oversized, deeply
  nested and 9,000-directory records (0.2 to 0.4 s), a 15 MiB file at a recorded path. Two Low
  findings, both accepted: (1) a forged record can make `recover` remove empty directories the
  user made themselves, since `rmdir` only refuses non-empty ones; they are listed before the
  digest is typed and the record is shown as unauthenticated; (2) the marker is unlinked by
  name after the second examination (already recorded above). Not run: concurrent processes
  (swaps were simulated by patching), the full read budget, a pty run by the reviewer. A
  regression test for the case-variant refusal was added.
- Next: Increment D (scan limits).
