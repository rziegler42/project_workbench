# Re-render an attached harness after a settings change

Status: Proposed
Created: 2026-10-27
Candidate: none (an owner request, found while building the per-command levels; no roadmap candidate names it)
Specs: harness-rerender, command-permissions, installer-interface
Decisions: 2026-10-27-rerender-is-terminal-only (Proposed; the owner accepts it)

## Goal

An owner who changes a level in `~/.config/project-workbench/settings` can make an attached clone pick it up with one owner-run
command, `wb rerender`, and no new clone. A read-only `wb preview rerender` shows what would change. When the plan is done the
design in `docs/specs/harness-rerender.md` is built, its acceptance criteria 1 to 8 pass, and the specs say it as built.

## Scope

- `wb preview rerender`: the plan of a re-render, read only, as its own agent-safe key defaulting to `none`.
- `wb rerender`: terminal only, the preview digest typed, the plan rebuilt just before the first write, the permissions file
  replaced with `Writer.replace_file`, the local manifest's hash for it replaced, and the rendering record written last. Its key
  offers `block` only.
- The live permissions file's `allow` rules kept, and every rule or entry the new file will not have listed in the preview.
- `wb check` naming the command when the rendering is out of date, and no longer telling the owner to attach in a new clone for
  that case.
- The specs, `docs/development.md` and tests that say and check the above.

## Non-goals

- A change of harness, or a clone with no recorded harness (`attach` stays for that).
- A re-render for a module or package change. That is `upgrade`'s work (`harness-rerender`, "Limits").
- `none` for `wb rerender`. It would read the level through `rendering.effective_level`, which is `block` exactly when a
  re-render is needed (`harness-rerender`, "Terminal only").
- A hook or watcher that re-renders by itself.
- Closing the window between `replace_file`'s hash comparison and its rename.
- Re-rendering any file other than the permissions file. The table changes no other staged file.

## Assumptions and constraints

- The owner approved the design in `docs/specs/harness-rerender.md` on 2026-10-27, the calls in it included (the spec's header says
  so). It was reviewed in four rounds with the project's review bridge; the last edit, making the command terminal-only, was not
  reviewed. The spec stays `Draft` until Increment D. Where this plan and the spec differ, the spec wins and the plan is corrected.
- Both commands are project commands under `installer-interface.md`, "The target": `[<target> | --dir <path>]`, defaulting to
  `.`, resolved once, opened without following links and held, with the refusals and the printed resolved target that section
  defines, and the exit codes `attach` uses (0 done, 1 refused, 3 stopped after writing, 130 interrupted before writing).
  `target.open_target` and `target.write_refusal` carry those rules for `attach` and are reused.
- The table is rendered into one file, the harness's permissions file, through `harnessstage.stage` and
  `harnessplan.render_permissions`; the gate reads only the record, the local manifest's harness name, that file and the shared
  settings file (`rendering.effective_level`). Both were read in the code, not run.
- `Writer.replace_file` exists and is used by `upgrade` (`upgrade.py`). `localmanifest.write` uses `create_file`, which does not
  overwrite, so a replacing write is new.
- `wb check` already reports a permissions file that differs from the record (`check._rendering_drift`).
- Staging needs the harness package. For a local source it is given with `--package`, as for `upgrade` and `attach`.
- A new owner-run key follows `docs/decisions/2026-10-26-a-level-for-every-command`. Offering `block` only is an exception to its
  decision 3, which the accepted decision does not allow. The exception is proposed in `2026-10-27-rerender-is-terminal-only`
  (`Proposed`). That record must be accepted by the owner before this plan is approved; if it is not accepted, this plan is
  wrong and is redrafted. The exception is then listed with the other (`command-permissions`, "Not built").
- Code is the Python standard library only; checks run with `python3 -B -W error tests/run_all.py`. The code in `workbench/` is
  in the agent's write scope in this repository.
- Discovery tooling: skipped. No discovery module is installed and the files the plan touches are named below.
- The change touches authorization, a permission boundary and the filesystem, so an increment that touches them stops for the
  owner before the next (see "Risks and sensitive actions").

## Completion criteria

1. With the table changed from `block` to `none` for a key, `wb preview rerender` shows the key moving and writes nothing, and
   `wb rerender` at a terminal with the digest makes the key read `none` (spec criterion 1).
2. With no change to the table it writes nothing, and every `allow` rule in the live file is listed and survives (criterion 2).
3. A permissions file that is a link, is not valid, or changes between the plan and the replacement is refused with nothing
   written; anything the live file has that the new one will not is listed (criterion 3).
4. A failure after the permissions file is replaced and before the record is written leaves every relaxed key reading `block`
   (criterion 4).
5. A clone with no recorded harness is refused and pointed at `attach` (criterion 5).
6. A run without a terminal is refused at every level and the key offers `block` only (criterion 6).
7. If anything the plan reads changes between the preview and the write, the command refuses and writes nothing (criterion 7).
8. `wb check` reports an out-of-date rendering and stops reporting it after a re-render (criterion 8).
9. The specs, `docs/development.md` and `wb settings` describe the built behavior, and `wb check` reports no problems.
10. The full suite passes with warnings as errors.

## Increments

### Increment A — The plan of a re-render and `wb preview rerender`

**Outcome:** `wb preview rerender [<target> | --dir <path>] [--package <source> [--ref <ref>] ...]` prints the resolved target,
then the whole plan and its digest, from the clone's recorded harness and the table now, and writes nothing; a re-render that
changes nothing says so; the key `wb preview rerender` exists, agent-safe, default `none`. It exits 0 when it printed a plan and
1 when it refused.
**Dependencies:** none (this plan is approved).
**Affected areas:** a new `workbench/rerender.py`; `workbench/attach.py` (the resolution and staging in `prepare`, shared rather
than copied); `workbench/cli.py`; `workbench/levels.py` and `workbench/rules.py` (the key); `tests/test_rerender.py`,
`tests/test_levels.py`, `tests/test_cli.py`.
**Steps:**
1. Write the tests first: a clone attached at one table and re-planned at another lists each key's old and new rule (`deny`,
   `ask`, `none`, `unruled`); an unchanged table says nothing changes and yields an empty write list; a live file with an extra
   `allow` rule lists it as kept; a live entry the new file will not have is listed as a removal; the digest changes when any of
   these changes; a change to a staged input that leaves the rendered permissions file the same still changes the digest; the
   preview lists the permissions file, the local manifest and the rendering record with their old and new hashes, and a file
   that a run would leave as it is is marked as such; a clone with no recorded harness, a harness that is not one the project records, and unacknowledged
   differences are refused; nothing is written in any case; the registry has the key and a drift test still passes. The target
   rules hold: the default is `.`, `<target>` and `--dir` are one value: both naming the same directory is accepted and two that differ are refused with nothing
   written (`installer-interface.md`, "The target", rules 3 to 5, as the shared parser has them), a target that is not an
   existing project or whose state `installer-interface.md` refuses is refused before anything is read, the resolved target is
   printed first and sanitized, and the exit codes are as above.
2. Share the part of `attach.prepare` that resolves the packages and stages the harness; keep `attach`'s behavior and tests
   unchanged.
3. Build the plan in `rerender.py` from `harnessstage.stage`'s permissions file and the record `rendering.record_of` would give,
   read the live permissions file through the project writer, carry its `allow` rules over, compute the removals, and digest the
   whole plan: the table, both files' hashes, the kept and removed entries, the record body, and the identity of every input the
   staging read (the tree hash of the harness module and of each module snapshot, the harness module's version, and the local
   manifest's `tree` and `module_version`), so an input that changes without changing the rendered file still changes the digest.
   The preview names the files a re-render replaces: the permissions file, the local manifest, and the rendering record (by its
   name in the guarded store, not its path), each with its old and new hash, and says which of them a run would leave as it is.
4. Route `wb preview rerender` in `cli.py` and print the plan.
5. Add the key `wb preview rerender` to the registry as agent-safe with the default `none`.
**Verification:** `python3 -B -W error -m unittest tests.test_rerender tests.test_levels tests.test_cli tests.test_attach`, then
the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-rerender-attached-harness#A`.

### Increment B — `wb rerender`: the terminal-only write

**Outcome:** `wb rerender [<target> | --dir <path>] [--package <source> [--ref <ref>] ...]` at a terminal, with the digest typed,
replaces the permissions file, the local manifest's hash for it, and then the record, and refuses without a terminal; the key
offers `block` only. It prints the resolved target before the plan, and exits 0 done, 1 refused, 3 stopped after writing and 130
interrupted before writing.
**Dependencies:** A, and the owner's answer on a security review (the checkpoint below): this increment stops before it starts
until the owner has said whether to run one.
**Affected areas:** `workbench/rerender.py`; `workbench/localmanifest.py` (a replacing write); `workbench/rendering.py` (writing
the record last); `workbench/cli.py`; `workbench/levels.py` and `workbench/rules.py`; `workbench/settings.py` (a level the key
does not offer reads `block` with a note); `tests/test_rerender.py`, `tests/test_levels.py`, `tests/test_settings.py`,
`tests/test_cli.py`.
**Steps:**
1. Write the tests first: the digest typed (`confirm.token_of`, `confirm.typed_matches`) lets it write; a wrong digest and no
   terminal write nothing; the plan is rebuilt before the first write and a difference in the table, either file, the manifest or a staged input (a changed package or module tree that leaves the rendered
   file the same)
   refuses with nothing written; a live file replaced between the plan and the write is a `WriteConflict` and nothing is
   written; a link, an invalid file or an unreadable file refuses; a forced failure after the permissions file is replaced, and
   again after the manifest, leaves every relaxed key reading `block` through `rendering.effective_level`; after a full run a key
   moved from `block` to `none` reads `none`; the `allow` rules survive; a re-run with no change writes nothing; `wb settings`
   shows the key with only `block` and a settings entry of `none` for it reads `block` with a note; the target rules and exit
   codes of Increment A hold for the write, a target whose identity changes between the plan and the write refuses with nothing
   written, and a failure after writing began reports what was and was not written and exits 3.
2. Add the key `wb rerender`, owner-run, default `block`, offering `block` only.
3. Replace the permissions file with `Writer.replace_file`, expecting the hash of the file as the plan read it.
4. Add a replacing write to `localmanifest` and update the entry for the permissions file; confirm in the code what `wb check`
   reads from the manifest before relying on the order and record the answer in the plan's Result.
5. Write the record last, with the shared settings file's hash as `rendering.with_shared_hash` gives it.
6. Route `wb rerender` in `cli.py` with the terminal test and the typed digest, as `upgrade` has them, and no level-log entry.
**Verification:** `python3 -B -W error -m unittest tests.test_rerender tests.test_levels tests.test_settings tests.test_cli
tests.test_rendering tests.test_check`, then the full suite. Run it once in a scratch clone attached to a copy of this
repository's harness, change a level, preview, re-render, and read `wb settings` and `wb check`; record the output.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-rerender-attached-harness#B`.

### Increment C — `wb check` names the command

**Outcome:** when the rendering is out of date, `wb check` says so and names `wb rerender`; the text that tells the owner to
attach again in a new clone is gone for this case; a re-render makes the report go away.
**Dependencies:** B.
**Affected areas:** `workbench/check.py`, `tests/test_check.py`.
**Steps:**
1. Write the tests first: a record whose digest differs from the table now gives one line naming `wb rerender`; the same clone
   after a re-render gives none; a stale state is informational and does not change the exit code (the stale state already reads
   `block`); the existing lines for a changed permissions file and a shared settings file are kept.
2. Add the table-digest comparison to `_rendering_drift` and reword the lines that point at a new clone.
**Verification:** `python3 -B -W error -m unittest tests.test_check tests.test_rerender`, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-rerender-attached-harness#C`.

### Increment D — The specs, the guide and the plan's acceptance

**Outcome:** the specs, `docs/development.md` and the spec index say what is built; the "Not built" item that this plan closes is
gone; the spec's status is `Current`.
**Dependencies:** C.
**Affected areas:** `docs/specs/harness-rerender.md`, `docs/specs/command-permissions.md`, `docs/specs/installer-interface.md`,
`docs/specs/README.md`, `docs/development.md`.
**Steps:**
1. In `command-permissions.md` replace the "Not built" item on re-rendering with the built behavior, and list `wb rerender` with
   the keys that offer `block` only.
2. In `installer-interface.md` add the two commands, their arguments, their exit codes and what they print.
3. In `docs/development.md` add the commands and the sequence "edit the settings, preview, re-render".
4. Add the row to `docs/specs/README.md` and set the spec's status to `Current` with its built-by note and its remaining limits.
5. Run the plan check, `wb check` and `refcheck`.
**Verification:** `git diff --check`, `wb check`, `wb run code-work check`, `doccheck` and `refcheck`, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-rerender-attached-harness#D`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` passes.
- `wb check`, `wb run code-work check`, `doccheck` and `refcheck` report no problems.
- The scratch-clone run of Increment B is repeated on the final tree: change a level to `none`, preview, re-render, and read that
  the key reads `none`; change it back, re-render, and read that it reads `block`.

## Risks and sensitive actions

- **Authorization and a permission boundary.** The command decides which commands the harness lets an agent run. A defect could
  leave a key reading looser than the table says. Mitigations: the record is written last, so any earlier failure reads `block`;
  the command is terminal-only; the plan is rebuilt before the first write and its digest compared with the one typed; the
  forced-failure tests of Increment B. A module providing `security-review` is installed in this project. A security review runs
  only when the owner asks, so the run stops after Increment A and asks whether to run one on Increment B before B starts. The
  owner's answer goes in the Result.
- **Kept `allow` rules.** The command keeps rules it did not render. Mitigation: the preview lists them and the typed digest covers
  them. The owner sees them only if they read the preview; no code makes them.
- **The window after `replace_file`'s comparison.** A write that lands between the comparison and the rename is overwritten
  without notice. Accepted and listed in the spec's limits.
- **A `localmanifest` change.** A replacing write is new code on the file that records the harness. Mitigation: it uses
  `replace_file` with the expected hash and a test for each failure.
- **Not reviewed.** The last edit to the spec (terminal-only) had no review round. The plan's review record should say so.
- No secret, host name or token is written anywhere in this plan. The code in `workbench/` is in the agent's write scope, and the
  owner runs `release-approvals` when the edit gate asks.

## Review record

Empty until a review is asked for.

## Deferred work

- `none` for `wb rerender`, if a way to authorize a stale rendering without a terminal is ever wanted. It needs its own decision.
- Picking up a module or package change in an attached clone, which `upgrade` covers today.
- Closing the window between `replace_file`'s comparison and its rename.

## Result

### Increment A — The plan of a re-render and `wb preview rerender` (committed as `85a4bcc`)

**Done.**
- `workbench/rerender.py` (new): `build` makes the plan from the clone's recorded harness and the table now; `render` and
  `run_preview` print it; nothing is written by them. The plan lists the project, the harness, each key whose rule moves (old to
  new), the three files (the permissions file, the local manifest, the rendering record by name) with old and new hash or "left
  as it is", the live `allow` rules it keeps (`kept:`), every other live entry the new file will not have (`removed:`), notes,
  a summary of the inputs, and a 64-character digest. A re-render that changes nothing says `nothing to change`.
- `workbench/attach.py`: `prepare` is split into `stage` (the shared read, check, verify, gate and translate; returns a
  `Staging` that also carries the identity of every package and module read) and `prepare`; `parse` takes `harness_required`.
  `wb attach` is meant to behave as before.
- `workbench/cli.py` routes `wb preview rerender [<target> | --dir <path>] [--package <source> [--ref <ref>]] ...`;
  `workbench/rules.py` adds `rerender` to `PREVIEW_ACTIONS`, which gives the agent-safe key `wb preview rerender`
  (default `none`). Exit codes: 0 plan printed, 1 refused, 2 usage.
- The digest covers the project, the harness, the table digest, the three files' old and new hashes, the kept and removed entries,
  the whole new record and manifest, and the inputs (package tree hashes, each module's declaration and tree hash, the harness
  token and version).
- Two calls of mine, not in the plan: the new local manifest keeps every field of the old one and changes only the permissions
  file's hash, so a note (`harness module differs...`) is printed when the staged harness is not the recorded one; the live file's
  `allow` list is found as the sibling of the rendered `deny` list, because the layout names no `allow`.

**Verification as run** (Python 3.15.0, warnings as errors).
- Tests first: `tests/test_rerender.py` failed on import with the module absent, then passed.
- `python3 -B -W error -m unittest tests.test_rerender`: 36 tests OK.
- Seven distinct deliberate breaks of `rerender.py` were each caught by a failing test (inputs left out of the digest; allow
  rules dropped; removals not listed; the record's old hash replaced; kept and removed cut at 200 characters; non-string `allow`
  items kept; a clone with no recorded harness not refused). One was not caught at first (non-string `allow` items kept) and the
  test was strengthened. The file was restored and compared after each run.
- `tests.test_levels tests.test_attach tests.test_install_attach tests.test_settingscmd tests.test_rendering tests.test_check
  tests.test_command_gate tests.test_adopt_rules tests.test_rerender`: 385 tests OK (before the review edits); `test_cli.py` (31)
  and `test_settings.py` (81) OK through discovery. `tests/test_levels.py` lists the new key.
- Full suite on the final tree, in a scratch copy: `python3 -B -W error tests/run_all.py`, 5627 tests in 11 roots. One failure:
  `packages/workbench/claude/tests`, `test_claude_module.Shipped.test_the_package_verifies_as_first_party_and_installs_claude`.
  It expects the module list `[ask-codex, claude, code-work, groundwork, safe-git, review-engine, mempalace, remote-runner,
  security-review]`, which has no `action-review`. It fails the same way on a clean copy of `HEAD` (`d9ef76d`), so it is not
  caused by this increment. It is skipped unless the shipped approvals are current (`support.require_release`), and they became
  current today after `release-approvals`, so it ran for the first time. Not fixed: it is in a first-party package, and a change
  there needs `release-approvals`. An earlier full run of a copy made before the review edits failed in that test and in
  `test_levellog.test_parallel_appends_keep_every_line` (the known intermittent failure), which did not recur.
- `git diff --check`, `wb check` and `wb run code-work check` report no problems. `doccheck` and `refcheck` printed nothing.
- A sample preview was run with a changed table, two added `allow` rules and one extra entry; it printed what the plan describes.

**Review.** The `reviewer` agent, one exchange (cap 6): no blocking findings, recommendation "no blocking findings". Applied:
missing tests from step 1 added (the harness the project does not record, unacknowledged differences, the default target,
an empty target and `--dir`, a link target, a non-object file, a deeply nested file, a non-list and a non-string `allow`, an
`ask` rule); a test that could not fail removed; kept and removed entries shown whole instead of cut at 200 characters; the
lambda replaced by a `def`; a comment pinning the case of no `deny` list. Noted, not changed: a preview opens the guarded store
and writes the launcher wrapper if it is missing, as every preview does (`cli._open_store`, `launch.install_wrapper`), and the
tests cannot see it because `bin/wb` already exists; the reviewer could not diff `attach.py` against git, so the behavior-preserving
claim rests on the 95 attach tests and the full suite; the output is unbounded in count for a very large live file. Not
done by the reviewer: it ran nothing.

**Not done.** Sanitized output of a control character in the project line has no test of its own (`ascii_text` is used). A preview
into a fresh store is untested. Increments B to D. The plan said `levels.py` and `tests/test_cli.py` would change; neither did,
because the registry derives the key from `rules.PREVIEW_ACTIONS`.

**Checkpoint before B.** The plan asked whether the owner wants a security review of Increment B, and B waited for the owner's
acceptance of `2026-10-27-rerender-is-terminal-only`. The owner accepted it (committed as `6f14476`) and answered "Yes, run one".

### Increment B — `wb rerender`, the terminal-only write (committed as `1989c73`)

**Done.**
- `workbench/rules.py`: `rerender` is in `OWNER_RUN`, which gives the key `wb rerender` (owner-run, default `block`, offers
  `block` only: it is in no `_OFFERS` entry) and the deny patterns of every spelling. A settings entry of `none`, `ask` or
  `delegated` for it reads `block` with a note, through the existing rule for a level a key does not offer.
- `workbench/localmanifest.py`: `replace(writer, expected_hash, document)`, a replacing write through `Writer.replace_file`.
- `workbench/rerender.py`: `run` refuses unless standard input and output are both terminals (at no level), prints the plan,
  asks for the first 12 characters of the digest, calls `held.recheck()`, rebuilds the plan and refuses unless its digest equals
  the confirmed one, then `_write`s the files whose old and new hash differ, in this order: the permissions file
  (`replace_file` with the hash the plan read), the local manifest (`localmanifest.replace` with the hash the plan read), the
  rendering record last. Exit codes: 0 done or nothing to change, 1 refused or cancelled, 2 usage, 3 stopped after writing began,
  130 interrupted before it. A stop after writing began lists what was written and what was not. No level-log entry is written.
- `workbench/cli.py` routes `wb rerender`; without a terminal it refuses before the store or the target is opened.
- Step 4, answered from the code: `wb check` reads from the local manifest only `harness` and the `files` list (`check._drift`
  compares each file's hash, `_strays` and `_shallow` use the paths); `_rendering_drift` reads the record and the live file. So
  the manifest's hash for the permissions file must be current, and it is written before the record.
- Hand-kept key lists in `tests/test_levels.py`, `test_rendering.py`, `test_permissions.py` and `test_owner_run_arguments.py` now
  include `rerender`. The key changes the table, so a clone attached before this commit (this one included) reads every relaxed
  key as `block`, and has no deny for `wb rerender`, until it is re-rendered.

**Verification as run** (Python 3.15.0, warnings as errors).
- Tests first: with the command absent, 30 of the new tests failed and 2 errored; they then passed.
- `python3 -B -W error -m unittest tests.test_rerender`: 78 tests OK (classes `Write`, `Relaxed`, `Pty`, `Keys` are B's; `Pty`
  runs the command on real pseudo-terminals with `approve.is_terminal` as it ships). `test_settings.py` (82) and `test_cli.py`
  (33) OK through discovery; `tests.test_levels tests.test_rendering tests.test_check tests.test_owner_run_arguments
  tests.test_attach tests.test_command_gate tests.test_adopt_rules tests.test_permissions` OK.
- Deliberate breaks of `rerender.py`, each caught by a failing test: the record written first, no digest comparison, no
  `held.recheck()`, writing before the confirmation, exit 1 for a stop after writing, no shared-file note, plain display of kept
  rules, no reconcile after an interrupt. One was not caught at first (the terminal check in `run`, since `cli` checks it
  too); a test that calls `run` directly and one that stops `cli` before the store were added. The file was restored and compared.
- Full suite on the final tree, in a scratch copy: 5672 tests in 11 roots. Two failures, neither from this increment:
  `test_claude_module.Shipped.test_the_package_verifies_as_first_party_and_installs_claude` (recorded under A, also fails on a clean
  `HEAD`) and `test_levellog.ConcurrencyTest.test_parallel_appends_keep_every_line` (the known intermittent failure: it failed
  in one of two reruns on its own and passed in the other). An earlier full run, before the review edits, also found
  `test_permissions.OwnerRun.test_the_constant_is_the_documented_list`, which was a hand-kept list and is fixed.
- `git diff --check`, `wb check` and `wb run code-work check` report no problems.

**Reviews.**
- The `reviewer` agent, one exchange (cap 6): no blocking findings. Applied: a conflict on the first file now exits 1 with
  "nothing was written" (the plan and criterion 3 say refused with nothing written; it had exited 3); a test with the table
  unchanged and a stop after the file is replaced (`Relaxed`). Not applied: an interrupt landing between `replace_file`'s return
  and the report, which the security review's second finding covers and `_reconcile` now handles. The reviewer's note that these
  Result items were missing is this entry. The `block` assertions in the forced-failure tests hold for any write order, because
  the table is changed first; the ordering is proved by the written and not-written lists, which the record-first break fails.
- The `security-reviewer` agent, on the owner's answer: no Critical or High findings. Medium: a re-render re-baselined the shared
  settings file silently, so a change to it after attach, which the record watches, became accepted when the owner re-rendered for
  another reason, with only a record hash in the plan. Fixed: the plan now carries a note naming the shared file, its old and new
  hash, and that the re-render records it as it is and does not write it. Low: two different kept rules could print alike; fixed
  (a rule that is not plain printable ASCII, or has a leading or trailing space or a backslash, is shown as its JSON string).
  Low: after an interrupt right after the rename the report called the replaced file "not written"; fixed (`_reconcile` checks the
  live files). A regression test for each, each shown to fail without its fix. Tested by the reviewer: typed-ahead input does not
  answer the prompt; link, hard link and swapped-directory attacks; forced failures at each step; hostile and oversized content; an
  edited shared file reads `block`. Not tested by it: a real harness, the harness's handling of `disableAllHooks`, an older
  attach, and a real race of the rename.

**Limits.** A process that owns a pseudo-terminal can type the digest; that is the limit `approve` shares, and the barrier against
an agent is the deny rule. The shared-file note shows hashes, not content. The plan was not run against this clone's own harness:
`wb preview rerender` refuses here until the owner runs `wb acknowledge` for the review-engine files, and `wb attach` for a
scratch clone is the owner's. The owner can run the plan's scratch-clone check with `python3 -m workbench preview rerender
--package packages/workbench` and `python3 -m workbench rerender --package packages/workbench` in a terminal. The window
between `replace_file`'s comparison and its rename stays (spec, "Limits"). A preview and a re-render both open the guarded store
and write the launcher wrapper if it is missing. The output is unbounded in count for a very large live file.

**Real-harness run (the owner's, after B was committed).** The owner ran `wb acknowledge`, then `python3 -m workbench preview
rerender --package packages/workbench` and `python3 -m workbench rerender --package packages/workbench` in a terminal on this
clone. The plan listed every key moving from `unrecorded` (this clone predates records), the two old `approve-plan` denies as
`removed`, the harness-module note and one digest; the typed digest wrote three paths and exit was 0. Afterwards `wb check`
reported no problems, the rendered file held the deny rules for `wb rerender` in all five spellings, and the command gate was
live (a command of mine that named the approval command was refused). The paste's second listing lacked the `wb rerender` line
that the first had, while both digests were equal; I took it for a trimmed paste, and the deny rules confirm the rule was rendered.

**Not done.** `wb check` does not yet name the command (Increment C); the specs, `docs/development.md` and the spec index
(Increment D).

### Increment C — `wb check` names the command (committed as `5d193e2`)

**Done.**
- `workbench/check.py`: `_stale_table` compares the record's `table_digest` with `rendering.digest` of
  `rendering.current_table(...)` and returns the warning `rendering: out of date; the settings table differs from the rendered
  one (wb rerender)`, the spec's wording; `_rendering_drift` now returns `(problems, warnings)` and `run` passes the warning on, so
  the stale state is informational and cannot change the exit code or hide a problem. A table that cannot be built
  (`ApprovalError`, `levels.RegistryError`) gives no line. The line for a relaxed key with no recorded command gate now says
  "remove the obstacle and run `wb rerender`" instead of "attach again in a new clone"; a test shows a re-render clears that state
  once the obstacle is gone. The other drift lines are as they were.
- Tests are in `tests/test_rendering.py` (`DriftTest`), not `tests/test_check.py` as the plan's affected areas say, because the
  fixtures with an attached synthetic harness and a settable table are there. The plan is not edited for this.

**Verification as run** (Python 3.15.0, warnings as errors).
- Tests first: five of the new tests failed with the check unchanged (the others passed for want of a line to find).
- `tests.test_rendering tests.test_check tests.test_rerender tests.test_levels tests.test_attach`: 315 tests OK.
- Two deliberate breaks of `check.py` were caught (the digest comparison removed; the warning made a problem). The second was
  first reported as not caught: `warnings` and `problems` have the same length, so a stale bytecode cache of the edited file was
  used; with a fresh `PYTHONPYCACHEPREFIX` it was caught.
- Full suite on the tree, in a scratch copy: 5679 tests in 11 roots. One failure: the Claude module test recorded under A, which
  also fails on a clean `HEAD`. The intermittent levellog test did not fail this time.
- `git diff --check`, `wb check` and `wb run code-work check` report no problems; `wb check` on this clone after the re-render
  shows no stale line.

**Review.** The `reviewer` agent, one exchange (cap 6): no blocking findings. Applied: a vacuous exit-code assertion replaced by a
check of the problem line; `ApprovalError` added to the table-cannot-be-built test; a test that an agent-safe key at its default
`none` is not a stale table; a test that a re-render clears the no-gate problem. Noted, not changed: the warnings list is cut at
40 lines (`LISTED`), so the stale line, which comes last, could be cut on a clone with more than 40 warnings; a record from before
records had a table digest is not valid and gives no line (nothing is printed for it, and no test covers it).

**Not done.** The specs, `docs/development.md` and the spec index (Increment D).

### Increment D — The specs, the guide and the plan's acceptance (not committed)

**Done.**
- `docs/specs/harness-rerender.md`: status `Current`; the header says what built it; "Not decided" is replaced by "As built" (how the
  manifest's hash is replaced, how the preview shows the change, the level wiring, the shared settings file, a failed write, `wb check`)
  and "Limits as built"; the early sections are marked as the state before a re-render; one sentence about what `wb check` reads is
  settled.
- `docs/specs/command-permissions.md`: a section "Re-rendering an attached clone" (the key and why it offers `block` only, the
  preview key, terminal-only, what the plan lists, the write order and exit codes); `wb rerender` named in the header, in "Levels
  offered", in the none-list sentence and in P4 and P5; the "Not built" item on re-rendering is gone, replaced by two deferred items
  (a `none` for the key; a module or package change); the two sentences that said a clone must be attached again now say attached
  again or re-rendered.
- `docs/specs/installer-interface.md`: the `rerender` row of the command table, a `### rerender` section (needs, reads, the preview's
  lines, the write, exit codes, who may run it), the stale-rendering warning under `check`, `rerender` in the preview verbs, in the
  section "The preview and approval" and in the list of commands the harness denies.
- `docs/specs/README.md`: a row for the spec. `docs/development.md`: two command rows, the sequence "edit the settings, preview,
  re-render", the key in the list of those that offer `block` only, and the text on "Yes, and don't ask again", which no longer
  needs a new clone.

**Verification as run.**
- `git diff --check`, `wb check`, `wb run code-work check`, `doccheck` and `refcheck`: no output or no problems, run after the last
  edit. `tests.test_docset_fixture`: 15 OK.
- Full suite on the tree, in a scratch copy: 5681 tests in 11 roots, two failures, both recorded under B: the Claude module test (also
  fails on a clean `HEAD`) and the intermittent `test_levellog` parallel append test. Four small document edits made after that run
  changed no code; `tests.test_docset_fixture` was run again after them.

**Review.** The `reviewer` agent, one exchange (cap 6): no blocking findings, and every claim it was asked to check against the code
matched (exit codes, write order, what the preview prints, what `wb check` reads, the key's offers, the deny in five spellings, the
terminal refusal before the store). Applied: the exit codes now say an interrupt once the writes begin is 3 even if nothing was
renamed; the early sections of the spec are marked as history and its "Not built" sentence corrected; P4 and P5 name `wb rerender`; the
"Not built" wording about the key is one sentence; the section "The preview and approval" names `rerender`. Not checked by it: it ran
nothing, and it did not read `attach.stage`.

**Completion criteria of the plan.** 1 to 7: the tests of B, on a synthetic harness and on real pseudo-terminals, and the owner's
run on this clone's real harness. 8: the tests of C and `wb check` on this clone. 9: Increment D. 10: the full suite passes except
two failures that are not from this plan: the Claude module test, which expects a module list without `action-review` and needs a
change in a first-party package (so the owner's `release-approvals`), and the intermittent levellog test.

**Not done.** The Claude module test is not fixed. Nothing is pushed. The plan's `Decisions:` line still says the decision is
`Proposed`; it was accepted on 2026-10-27 (`6f14476`), and the line is in the approved part of the plan. The plan's status is left for
the owner.
