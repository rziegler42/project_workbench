# Refresh the rendered skills and agents of an attached clone

Status: Completed
Created: 2026-10-28
Candidate: none (an owner request, found when a rendered skill stayed behind its source after `wb upgrade`; no roadmap candidate names it)
Specs: harness-refresh, harness-rerender, installer-interface, command-permissions

## Goal

An owner whose installed modules changed (after `wb upgrade`) can bring the rendered skills, agents and root file of an attached
clone up to date with one owner-run command, `wb rerender`, and can see beforehand, with `wb preview rerender`, which rendered
files are behind. When the plan is done the design in `docs/specs/harness-refresh.md` is built, its acceptance criteria 1 to 9
pass, and the specs say it as built.

## Scope

- A per-file state for every staged file except the permissions file (current, applied, stale, edited, missing, new, unrecorded,
  orphaned), tried in the spec's order after a link check of every staged and listed path.
- `wb preview rerender` listing those states with old and new hash, the changed lines of a stale file and one digest that covers
  the permissions file, the other files, the manifest and the record.
- `wb rerender` writing it all under the one digest the owner types at a terminal: stale files replaced, new and missing files
  created, the manifest, then the rendering record. Nothing is written when any file is edited, unrecorded or a link.
- A re-read of every file to replace or create, and a rebuild of the plan, immediately before the first write.
- One line printed by `wb upgrade` after it wrote a module's harness items, naming `wb preview rerender`. It stages and writes
  nothing under `.claude/`.
- The specs, `docs/development.md` and tests that say and check the above.

## Non-goals

- A change of harness, or a clone with no recorded harness (`attach` stays for that).
- A new command, a new key, or any level other than `block` for `wb rerender`; no agent-run refresh.
- Any change to what `wb upgrade` writes, beyond the one printed line.
- `wb check` reporting staleness. It needs a manifest format change (spec, "Open questions" 1).
- Deleting an orphaned rendered file, or a command that does.
- A force option to overwrite an edited file.
- Rollback of a partly written refresh. A second run finishes it.
- Any change to the permissions file's rules (`harness-rerender`): they are kept as built.

## Assumptions and constraints

- The owner approved the design in `docs/specs/harness-refresh.md` on 2026-10-28, the calls in it included. It was reviewed in three
  rounds, which stopped at the bound; the fixes of the last round were not reviewed again. Where this plan and the spec differ,
  the spec wins and the plan is corrected. The approval of the spec is not the approval of this plan.
- Read in the code at `df82594`, not run: `rerender.build` calls `attach.stage`, which already stages every harness file
  (`Staged.files`, each a `harnessplan.Planned` with `path`, `data`, `sha256`) and the document for the local manifest, and then
  keeps only the permissions file. `localmanifest.replace(writer, expected_hash, document)` and `Writer.replace_file` exist;
  `Writer.create_file` makes missing parent directories and refuses an existing path, and does not set a mode other than 0644 or
  0755 (so a newly created file gets 0644, as attach gives it). `Writer.replace_file` keeps the original's mode without execute,
  group-write or other-write bits.
- `wb check` reads from the local manifest the `files` list: a listed file that is gone or whose hash differs is a problem
  (`check._drift`), and a file below a generated directory that is not listed is a problem (`check._strays`). So every file the
  refresh creates must be in the manifest before the command ends, and a manifest hash must be current once its file is replaced.
- **(call) The manifest's other fields stay as attach wrote them** (`tree`, `module_version`, `source`, `workbench`), as `rerender`
  keeps them today; only the `files` entries change. A refresh from a harness module that differs from the recorded one still prints
  the note, reworded because the other harness files are now replaced (the note says "only the permissions file is replaced" today).
  An orphaned file keeps its manifest entry.
- **(call) Where the new code lives.** The states are built in a new `workbench/refresh.py`, called by `rerender.build`; `rerender.py`
  keeps the permissions file, the digest, the prompt and the exit codes. Tests are in a new `tests/test_refresh.py` and, where they
  touch the command, `tests/test_rerender.py`.
- The exclude lines (`.git/info/exclude`) that attach added come from the layout. A created file must fall under them; if a
  created path would not, the run refuses and names it (Increment A checks this with the writer's exclude check).
- The installer source and its tests may not name a module, a helper, a harness or a path (`tests/test_boundary.py`,
  `tests/test_run.py`); tests use stand-ins.
- Code is the Python standard library only; checks run with `python3 -B -W error tests/run_all.py`. The code in `workbench/` is in
  the agent's write scope in this repository.
- Discovery tooling: skipped. No discovery module is installed and the files the plan touches are named below.
- The change decides which instructions the agent loads and writes into the filesystem, so it touches a permission boundary and the
  filesystem; see "Risks and sensitive actions" for the checkpoint before Increment B.

## Completion criteria

1. After a package skill changed and `wb upgrade` ran, `wb preview rerender` lists the rendered skill as stale, and after
   `wb rerender` it lists it as current (spec criterion 1).
2. The preview shows every stale, applied, new, recreated and orphaned file with its old and new hash (`none` for one that does
   not exist), the changed lines of a stale file and one digest, and writes nothing; a run with nothing to change says so
   (criterion 2).
3. `wb rerender` at a terminal, with the digest, replaces each stale file, creates each new file, writes the manifest and then the
   rendering record, and leaves an orphaned file alone (criterion 3).
4. An edited file, an unrecorded file at a staged path, or a link at any staged or listed path refuses the whole run with nothing
   written and names the file; a missing file is recreated (criteria 4 and 5).
5. A file that changes after the plan, found by the re-read before the first write, refuses with nothing written; one that changes
   after the first replacement stops the run with exit 3 and the written and not-written lists (criterion 5).
6. A run without a terminal is refused at every level and no level is offered (criterion 6).
7. After a failure partway, every relaxed key reads `block`, and a second run reads each replaced or created file as applied and
   finishes the job (criterion 7).
8. `wb upgrade` writes nothing under `.claude/` and prints one line that names `wb preview rerender` after it wrote a harness item
   (criterion 8).
9. The comparison uses the real renderer, so a quoting or `tools:` translation is not stale (criterion 9).
10. The specs, `docs/development.md` and `wb settings` describe the built behavior, and `wb check` reports no problems.
11. The full suite passes with warnings as errors.

## Increments

### Increment A — The states of the rendered files, in the preview

**Outcome:** `wb preview rerender` lists, besides the permissions file, the manifest and the record, every other staged file with
its state (current, applied, stale, edited, missing, new, unrecorded) and every orphaned manifest path, each with old and new hash
(`none` where a hash does not exist), the changed lines of a stale file, a note for a refused state, and a digest that covers all
of it. A link at any staged or listed path, an edited file or an unrecorded one makes the preview refuse and name the file.
Nothing is written by anything in this increment.
**Dependencies:** none (this plan is approved).
**Affected areas:** a new `workbench/refresh.py`; `workbench/rerender.py` (`build`, `Plan`, `render`, the digest body, the note
about a differing harness module); `tests/test_refresh.py` (new); `tests/test_rerender.py` (the existing plan tests keep passing).
**Steps:**
1. Write the tests first, on the synthetic harness of the test fixtures: one test for each state in the table, built by attaching
   at one set of sources and previewing at another (stale), by deleting a rendered file (missing), by editing one (edited), by
   writing a file at a staged path that the manifest does not list (unrecorded), by adding a source file (new), by removing a
   source file (orphaned, present on disk and already gone), and by leaving a file equal to the staged bytes while the manifest
   records another hash (applied). The order of the table holds: an orphan is orphaned whether or not its file is on disk; a link
   is refused even when its content equals the staged and recorded hash and even when nothing else would change; the link check
   covers every staged path and every path the manifest lists. The changed lines of a stale file are shown and a line that is not
   plain printable ASCII is shown as its JSON string (`rerender._whole`). The comparison goes through the renderer: a file whose
   only difference from its source is the translation (quoted names, `tools:`) is current. The digest changes when any state, any
   hash or any listed line changes, and covers the manifest that would be written. A refused state names the path and writes
   nothing. The permissions file is outside the table: a live `allow` rule is never an edit, and a refresh with no change to it
   leaves it as it is. A created path outside the exclude lines refuses and is named. The existing tests of `rerender` still pass.
2. Add `refresh.py`: `classify(writer, recorded, staged_files, settings_path)` reads every staged and listed path without following
   a link (`Writer.read_file`), tries the states in the spec's order, and returns the rows and the refusals. Orphans are decided
   first; the permissions file is skipped.
3. In `rerender.build` call it, add the rows to the plan, build the manifest that would be written (the old one with the `files`
   entries of stale, applied, missing, new and the permissions file changed, entries sorted as `localmanifest` requires, the
   orphaned entries kept, every other field kept), and put the rows and that manifest in the digest body.
4. Print each row in `render` in the same style as the existing lines ("left as it is" for current, hashes for the rest, the
   changed lines under a stale file, `no longer shipped` with the on-disk state for an orphan). Reword the harness-module note.
5. Check the created paths against the exclude lines through the writer's exclude check and refuse a path that falls outside.
6. Read the layout for any rendered file marked as the owner's to edit (spec, "Open questions" 3) and record the answer in the
   Result. The root file is covered by the table; an edited one refuses.
**Verification:** `python3 -B -W error -m unittest tests.test_refresh tests.test_rerender tests.test_attach tests.test_check
tests.test_rendering`, then the full suite. Break `refresh.py` on purpose in each of the ways the tests claim to catch (the order
of the states, the link check, the orphan rule, a hash left out of the digest, the renderer bypassed) and show each caught.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-refresh-rendered-harness#A`.

### Increment B — `wb rerender` writes the files

**Outcome:** `wb rerender` at a terminal, with the digest typed, replaces each stale file, creates each new and each missing file,
writes the manifest (which also takes an applied file's hash), then the rendering record, and leaves current, applied and orphaned
files as they are. Immediately before the first write it re-reads every
file it will replace or create and rebuilds the plan, and refuses with nothing written on any difference. A failure after one
replacement exits 3 with the written and not-written lists; a second run reads each replaced or created file as applied and
finishes the job. It writes nothing when the plan has no change, and offers no level.
**Dependencies:** A, and the owner's answer on a security review (the checkpoint below): this increment stops before it starts until
the owner has said whether to run one.
**Affected areas:** `workbench/rerender.py` (`_write`, `_reconcile`, `_failed`, `run`); `workbench/refresh.py` (the write order and
the re-read); `workbench/localmanifest.py` only if the replacing write needs more than it has; `tests/test_refresh.py`,
`tests/test_rerender.py`.
**Steps:**
1. Write the tests first: the digest typed lets it write; a wrong digest and no terminal write nothing; after a stale file is
   replaced the preview reports it current; a new file is created with its parent directories; a missing file is recreated; an
   orphan is left; a file changed (content, deleted, or swapped for a link) between the plan and the first write refuses with
   nothing written; a file changed after the first replacement fails that replacement, exits 3 and lists written and not written;
   a forced failure after a file, after the manifest and before the record each leaves every relaxed key reading `block` through
   `rendering.effective_level`; a second run after each such failure finishes the job and reports the replaced and created files as
   applied; the permissions file and its kept `allow` rules behave as in `harness-rerender`; a re-run with no change writes
   nothing; the target rules and exit codes of `rerender` hold; no level-log entry is written.
2. Write in this order: the files (each stale file with `Writer.replace_file` and the hash the plan read, each new or missing file
   with `Writer.create_file`; a current or applied file is not touched, and an applied file's hash goes only into the
   manifest), the permissions file as today, the manifest with `localmanifest.replace`, then
   the record last. Keep `_reconcile` correct for the new files, so that the report of a stop says what is on disk.
3. Before the first write re-read every file the plan replaces or creates and compare its hash with the one the plan read, then
   rebuild the plan and compare the digest with the one typed, as `run` does now.
4. Make the report list the files written by state (replaced, created, recreated) and the one stale count that remains.
**Verification:** `python3 -B -W error -m unittest tests.test_refresh tests.test_rerender tests.test_levels tests.test_settings
tests.test_cli tests.test_rendering tests.test_check`, then the full suite. Run it once in a scratch clone attached to a copy of this
repository's harness: change a source skill, run `wb upgrade` or its equivalent on the copy, preview, refresh, preview again, and read
`wb check`; record the output. Deliberate breaks as in Increment A (the record written before the files; the re-read left out; the
digest comparison left out; a file written before the confirmation), each shown caught.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-refresh-rendered-harness#B`.

### Increment C — `wb upgrade` points at the preview

**Outcome:** after an upgrade that wrote a path under a module's `harness/` folder (a neutral skill, agent or command), `wb upgrade`
prints one line saying the rendered copies may be behind and naming `wb preview rerender`. An upgrade that wrote no harness item
prints no such line. It stages nothing, compares nothing and writes nothing under `.claude/`.
**Dependencies:** B.
**Affected areas:** `workbench/upgrade.py` (`_finish`); `tests/test_upgrade.py` (or the file that holds the upgrade report tests).
**Steps:**
1. Write the tests first: an upgrade that writes a harness item prints the line once; one that writes only other paths does not;
   the line does not appear in `wb preview upgrade`; an upgrade writes no path under the harness's own folders (the tree is
   compared before and after); the exit codes and the other lines are unchanged.
2. Decide from the written paths (`progress.writer.written`) whether one lies under `.workbench/<package>/<module>/harness/`, and
   print the line after the "wrote N paths" line.
**Verification:** `python3 -B -W error -m unittest tests.test_upgrade tests.test_install_attach tests.test_cli`, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-refresh-rendered-harness#C`.

### Increment D — The specs, the guide and the plan's acceptance

**Outcome:** the specs, `docs/development.md` and the spec index say what is built; `harness-refresh.md` says "As built" and lists
its remaining limits; `harness-rerender.md` keeps its scope and has no statement left that the build made false.
**Dependencies:** C.
**Affected areas:** `docs/specs/harness-refresh.md`, `docs/specs/harness-rerender.md`, `docs/specs/installer-interface.md`,
`docs/specs/command-permissions.md`, `docs/specs/README.md`, `docs/development.md`.
**Steps:**
1. In `installer-interface.md`, under `rerender`, describe the states, the extra files written, the order of the writes, the exit
   codes and the `upgrade` line; correct the table row that names only the permissions file.
2. `harness-rerender.md` keeps its scope (the permissions file and the table; the owner chose a spec of its own for this design).
   Only the statements that have become false are corrected, for example that the other harness files stay as attach wrote them,
   with a pointer to `harness-refresh.md`; a change beyond that stops for the owner. In `command-permissions.md` correct the
   sentences about what a re-render writes.
3. In `harness-refresh.md` add "As built" (the calls settled during the build, the manifest fields kept, the owner-editable
   question answered) and set what remains open.
4. In `docs/development.md` add the sequence "upgrade, preview rerender, rerender".
5. Run the plan check, `wb check`, `doccheck` and `refcheck`.
**Verification:** `git diff --check`, `wb check`, `wb run code-work check`, `doccheck` and `refcheck`, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-refresh-rendered-harness#D`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` passes in a scratch copy.
- `wb check`, `wb run code-work check`, `doccheck` and `refcheck` report no problems.
- The scratch-clone run of Increment B is repeated on the final tree: change a source skill, upgrade, preview (stale), refresh,
  preview (current), then edit a rendered file and see the preview refuse.
- The owner runs `wb preview rerender --package packages/workbench` and `wb rerender --package packages/workbench` in a terminal on
  this clone, whose rendered `draft-decision`, `draft-plan` and `draft-roadmap` are behind their sources, and reads `wb check`.

## Risks and sensitive actions

- **A permission boundary and the filesystem.** The command rewrites the instructions the agent loads (skills, agents, the root
  file). A defect could replace an owner's edited file, write outside the clone through a link, or leave the clone looser than the
  table says. Mitigations: terminal only with a typed digest and no level; a link at any staged or listed path is refused; an edited
  or unrecorded file refuses the whole run; the plan is re-read and rebuilt before the first write; the record is written last.
  A module providing `security-review` is installed, and the spec says a review is asked for when this is built and only if the
  owner asks. The run therefore stops after Increment A and asks whether to run a security review on Increment B before B starts.
  The owner's answer goes in the Result.
- **A partly written refresh.** There is no rollback. Mitigation: the order of writes keeps relaxed keys at `block`, and a second
  run finishes the job; both are tested.
- **Window after `replace_file`'s comparison.** A write that lands between the comparison and the rename is overwritten without
  notice, as for the permissions file. Accepted and listed in the spec's limits.
- **A newly created file's mode.** `Writer.create_file` gives 0644. This is what attach gives; no execute bit is needed for a
  skill or an agent. Confirmed in Increment A's tests against attach's own output.
- **Not reviewed.** The fixes of the spec's third review round were not reviewed again. The plan's review record should say so.
- No secret, host name or token is written anywhere in this plan. The code in `workbench/` is in the agent's write scope, and the
  owner runs `release-approvals` if the edit gate asks.

## Review record

An independent review with the project's review bridge (model `gpt-5.6-terra`), asked for by the owner on 2026-10-28; two rounds
of a bound of three, converged.

- Round 1: two major findings, both applied. R1-F1: Increment D revised `harness-rerender.md` although the refresh spec records the
  owner's choice to leave its scope alone; D now corrects only statements the build made false and stops for the owner beyond that.
  R1-F2: Increment B named an undefined "applied-pending" replacement; the write set is now stale replaced, new and missing
  created, current and applied untouched, and an applied file's hash goes only into the manifest.
- Round 2: no meaningful finding.

The review is advice and not an approval. The fixes of the spec's own third round were not reviewed again (the spec's header says
so); this review read the plan against the spec as it stands.

## Deferred work

- `wb check` reporting a stale rendered file, which needs the manifest to record a hash of each file's source (spec, "Open
  questions" 1).
- Removing the rendered copy of a skill or agent whose source is gone (spec, "Open questions" 2).
- A `--force` or an adopt path for an edited rendered file; the owner moves the file aside today.
- Closing the window between `replace_file`'s comparison and its rename.

## Result

### Increment A — The states of the rendered files, in the preview (committed `8c8320a`)

**Done.**
- `workbench/refresh.py` (new): `classify(writer, listed, files, settings, exclude)` reads every staged path and every manifest
  path with `Writer.read_file` (no link followed, at any component) and returns the rows and the refusals. Order: orphaned (a
  listed path no longer staged, present or already gone); equal to the staged bytes (current, or applied when the manifest records
  another hash or none); gone (missing when listed, new when not); equal to the recorded hash (stale, with the changed lines,
  40 at most); anything else (edited when listed, unrecorded when not). The permissions file is left out. A created path
  (missing or new) that the layout's exclude entries do not cover is refused.
- `workbench/rerender.py`: `build` calls it and raises `Refused` on any refusal; the manifest of the plan takes the new hash of
  every stale, applied, missing and new file, gets the new entries in `localmanifest`'s order and keeps the orphans' entries; the
  digest body and the `Plan` carry the rows; `render` prints each row (`left as it is`, `(applied)`, `old -> new (stale)` with
  `-`/`+` lines, `none -> new (new)`, `none -> new (missing; recreated)`, `old -> none (orphaned; no longer shipped, present |
  already gone)`); an orphan alone is no change; the harness-differs note is reworded.
- **Interim guard, removed by Increment B (not in the plan):** `run` refuses a plan with rows to write ("not built yet") before
  the prompt. Without it `wb rerender` would have written a manifest naming hashes of files it did not write, and `wb check` would
  have reported them. The cost: until B, `wb rerender` also refuses on a clone with any file behind its source, this one included.
  `tests/test_refresh.py` has a test for it (`Interim`), which B deletes.
- Calls of mine: a staged file equal to the disk and not in the manifest is `applied` (the spec's table is silent; spec lines on
  a created file reading as applied need it), which also adopts an owner-placed file with identical bytes; Increment D adds one
  sentence to the spec's table. The exclude check is my own `covered()` against the layout's entries, not `check_exclude`, which
  only checks that the exclude file can be written. The live `.git/info/exclude` is not read.
- Step 6, the owner-editable question: no layout field and no sentence in `harness-modules.md` marks a rendered file as the
  owner's to edit (searched the `claude` package and the spec). The root file is a row like the rest; an edited one refuses.

**Verification as run** (Python 3.15.0, warnings as errors).
- Tests first: with `refresh.py` absent 27 of the new tests failed and 1 errored (after the fixture was given a module with
  neutral items); they then passed. `tests.test_refresh tests.test_rerender tests.test_attach tests.test_check
  tests.test_rendering tests.test_levels`: 348 tests OK, and `tests.test_refresh` 33 OK after the review edits.
- Ten deliberate breaks, in a scratch copy, each caught by a failing test: links ignored; orphan only when absent from disk;
  orphan decided after the edit test; current judged by the recorded hash only; stale and edited swapped; exclude check removed;
  rows left out of the digest; manifest ignoring the rows; unrecorded treated as new; missing treated as new. **Not run:** the
  plan's "renderer bypassed" break. Criterion 9 rests on the all-current test, where the staged file is the renderer's output
  and the disk is not the neutral source (asserted for the agent's `tools` line).
- Full suite in a scratch copy of the tree: 5874 tests in 12 roots; one error, `test_actionreview_bridge.Setting.
  test_the_real_projects_file_is_read`, which opens the project's own `.workbench/review.json`, a file my scratch copy lacks.
  Not rerun in the real tree. A first full run failed in 1682 tests because the copy lacked `base/`; it was a fault of the copy.
- `git diff --check`, `wb check` and `wb run code-work check` (60 plans) report no problems. `doccheck` and `refcheck` were not
  run; no document but this plan changed.

**Review.** The `reviewer` agent, one exchange (cap 6): no blocking findings. Applied: a vacuous assertion (a line compared with a
whole file) replaced by assertions on the neutral and the rendered agent; a self-comparison replaced by bytes captured before the
build. Noted, not changed: the link tests look for "link" in a message `classify` adds itself, so they do not prove which error
`read_file` raised; no test for a link at a new file's path or a non-regular file (`read_file` covers both); the plan's Risks say a
created file's mode is confirmed against attach's output in A, and no test does it, so it moves to Increment B (the Risks text is
not edited); behavior on a case-insensitive filesystem was not examined. Not done by the reviewer: it ran nothing.

**Checkpoint before B.** The owner accepted the interim guard (2026-10-28) and answered "run a security review of B": after B is
built, the `security-reviewer` agent reviews it, besides the mandatory `reviewer` pass.

**Not done (Increment A).** Increments B to D. The mode of a created file (done in B). The plan's step 5 names "the writer's
exclude check", which does not test coverage; the deviation is above.

### Increment B — `wb rerender` writes the files (committed `f0cc042`)

**Done.**
- `workbench/refresh.py`: `recheck` reads every stale, created and applied row again without following a link and raises
  `Changed` on any difference; `write` replaces a stale file with `Writer.replace_file` and the hash the plan read, creates a
  new or missing file with `Writer.create_file`, and touches no current, applied or orphaned file. A create that failed after
  the file was made raises `Partial` (the path is listed as written and named as possibly partly written).
- `workbench/rerender.py`: `_write` re-reads, writes the files, the permissions file, the manifest and the record, in that
  order; an applied file is read again just before the manifest write (a `reviewer` finding, applied, test first). `_steps`
  gives the write order, which `_reconcile` (the next step only) and `_failed` (the not-written list) use. A failure of the
  re-read refuses with "nothing was written". The success report has one `files:` line (replaced, created, recreated, recorded
  as applied). The interim guard and the `Interim` test class are gone.
- My reading of "the one stale count that remains" (plan step 4): the `files:` line; nothing is stale after a complete run.
- After a stop past the manifest the files read `current`, not `applied`, because the manifest already holds their hashes
  (criterion 7 says `applied`; it holds for a stop before the manifest).

**Verification as run** (Python 3.15.0, warnings as errors). `tests.test_refresh` 61 OK; with `test_rerender`, `test_attach`,
`test_check`, `test_rendering`, `test_levels`: 376 OK; `tests/test_cli.py` 33 OK and `tests/test_settings.py` 82 OK (as scripts,
`PYTHONPATH` set). Written first: the new tests failed (23 of 28) with the guard in place. Twelve deliberate breaks in a scratch
copy, each caught: record before files; re-read left out; digest comparison left out; files before the confirmation; applied
written like stale; stale replaced with the wrong expected hash; created file not read as absent; applied file not read; partial
create not reported; interrupted rename not reconciled; lists without the files; summary left out. Full suite
`python3 -B -W error tests/run_all.py` in the real tree (before the applied-file hardening): 5901 tests in 12 roots OK, which
also clears A's `review.json` error (a fault of the scratch copy). `git diff --check`, `wb check` and `wb run code-work check`
(60 plans) report no problems. Not run: the plan's scratch-clone run (upgrade, preview, refresh, preview, `wb check`), and the
full suite after the last hardening (the 376-test group above was).

**Reviews.** `reviewer` agent, one exchange: no blocking findings. Applied: finding 5 (re-read applied files before the
manifest). Not applied, not blocking: a failed create that made only parent directories reports "nothing was written" with exit
1 (finding 1); an interrupt between `O_EXCL` open and the writer's record of it, and the record step, are reported as not
written (2); `_reconcile` infers from content (3); an interrupt inside the re-read exits 3 where 130 would fit (4); a `Partial`
path is listed under "written" (6).
`security-reviewer` agent, one exchange, experiments on a scratch copy, tree unchanged. No critical or high finding. Sound by
test: links, hard links, FIFOs, directories, hostile staged paths, a parent swapped for a link before create and before replace,
modes (umask 077, 022; a stale 0755 file comes back 0644), output escaping, the three stops leaving relaxed keys at `block`.
Open for the owner:
- **Medium 1.** The edited-file test trusts the local manifest. Anyone who can write `.workbench/local/harness.json` can record
  an owner's edit as the file's hash; the row then reads `stale` and the file is replaced (tested). Bytes written are always the
  staged ones, the preview shows the diff and the owner types the digest. The fixture harness does not deny agent writes to that
  file; the real harness was not checked. Corrections offered: corroborate the hash in the guarded store, or deny agent writes to
  `.workbench/local/**`.
- **Low 2.** A created file is not atomic; a crash leaves a short file the next run refuses and names (an agent file without its
  `tools:` line may load with every tool). Offered: write a private sibling and `link()` it into place.
- **Low 3.** Created files are checked against the layout's exclude entries, not the clone's `.git/info/exclude` (tested: with
  the lines removed a created file is not excluded). Offered: require the line on disk, or add it as attach does.
- **Low 4.** `_changed` splits on any line separator, so a change in CR/VT/U+2028 shows `(stale)` with no changed lines; cut at 40.
- Informational: `Planned.sha256` is trusted (the three real constructors hash their own data); a rendered file is written
  before the permissions file by design, so a stop between leaves new instructions under the old permissions, never a looser key.

**Not done.** Increments C and D. The findings above, apart from 5, are not applied; none was asked for.

### Increment C — `wb upgrade` points at the preview (committed `0bf7d46`)

**Done.**
- `workbench/upgrade.py`: `_finish` prints one line after "wrote N paths" when a written path lies under
  `.workbench/<package>/<module>/harness/` (`_is_harness_item`): "the rendered skills, agents or commands may be behind;
  `wb preview rerender` shows which". It reads `progress.writer.written` only; it stages, compares and writes nothing, and a
  failed upgrade never reaches it.
- `tests/test_upgrade.py`, class `Pointer` (6 tests): a replaced item prints the line once, right after the count; a created
  item prints it; an upgrade that wrote no harness item prints none; `wb preview upgrade` prints none; a failed upgrade prints
  none; every changed path stays within `.workbench` and `.git`.

**Verification as run.**
- The positive test was red before the change. Two deliberate breaks were each caught: the line always printed; the line for
  any `.workbench` path.
- `tests.test_upgrade`, `tests.test_install_attach`, `tests.test_upgrade_preview`: 87 OK. `tests/test_cli.py` as a script: 33 OK.
  `git diff --check` clean.
- First full suite run: one failure, `test_boundary` (a test of mine named a harness folder, which the installer tests may not).
  I removed that redundant assertion; `test_boundary` and `test_upgrade` then ran 65 OK. The full suite rerun: 5908 tests in
  12 roots, OK.

**Review.** One `reviewer` exchange, no blocking findings. Applied: a create-only test; `SKILL_HEAD` defined before use. Not applied:
- `wb add` shares `_finish`, so adding a module that ships harness items also prints the line. That is arguably right (the
  rendered copies lack the new items), but the spec says "after an upgrade". For Increment D or the owner to settle; no test
  pins it.
- A later-stage failure (the store stage) is not tested; by code it also skips `_finish`.

### Increment D — The specs, the guide and the plan's acceptance (committed `bc56873`)

**Done.** Documents only; no code or test changed.
- `harness-refresh.md`: header says it is built; one sentence that an unlisted file of equal content is `applied`; a note under
  criterion 7 (a stop past the manifest leaves the files `current`); new "As built" (write order, report line, failures, the
  upgrade line, the root file answer, `wb check`) and "Limits as built" (the four security findings of B, left for the owner).
- `harness-rerender.md`: pointers only (the table-only statement, the source, the write order, the manifest sentence, the limits);
  its scope is unchanged.
- `installer-interface.md`: the `rerender` table row, the `rerender` section (states, write order, `files:` line), the upgrade line.
- `command-permissions.md`: what the plan lists, the write order, the "Not built" bullet. `specs/README.md` row; `docs/development.md`:
  two table rows and the sequence upgrade, preview rerender, rerender.
- Headings of A, B and C in this Result now name their commits.

**Verification as run.** `git diff --check` clean; `wb check` and `wb run code-work check` (60 plans) report no problems. `wb check`
runs the installed modules' own checks; `wb run doccheck` and `refcheck` are not declared commands here, so they were not run
separately. Full suite (`python3 -B -W error tests/run_all.py`, run while the review was open and before its small wording fixes,
which touched documents only): 5908 tests in 12 roots, OK.

**Review.** One `reviewer` exchange. One blocking finding, applied: `harness-rerender.md` still said the command writes the
permissions file, the manifest hash and the record only. Applied also: the manifest sentence of its "As built", two wordings in
`harness-refresh.md`. The reviewer could not run commands or read the tests.

**For the plan's acceptance (the owner).**
- The Risks text says a created file's mode is "confirmed in A's tests"; it is confirmed in Increment B's tests. The approved text is
  not edited here.
- The scratch-clone run of Increment B was not run on the final tree, and the owner's runs of `wb preview rerender` and `wb rerender`
  on this clone are not done (see the plan's Verification).
- Open: the four security findings of B; whether `wb add` should print the upgrade line.

**Not done.** The items above.
