# Close the three Low findings of the refresh security review

Status: Proposed
Created: 2026-10-28
Candidate: none — the deferred Lows 2 to 4 of the security review of Increment B of `2026-10-28-refresh-rendered-harness`, not a roadmap candidate
Specs: harness-refresh, harness-rerender

## Goal

`wb rerender` creates a rendered file that is missing, shows what changed in a stale one, and checks that git would not see a
file it creates. Three small defects remain in that path (recorded under "Open for the owner" in the Result of
`2026-10-28-refresh-rendered-harness`, Increment B):

- **Low 4.** `_changed` splits on any line separator, so a stale file whose only change is a CR, VT or U+2028 shows `(stale)` with
  no changed lines. After this plan the preview shows that a line separator changed.
- **Low 3.** A file the run would create is checked against the layout's exclude entries, not the clone's `.git/info/exclude`,
  so with those lines removed a created file is not excluded. After this plan the run refuses unless the exclude lines are on disk.
- **Low 2.** A created file is written in place, so a crash leaves a short file that the next run refuses and names; an agent file
  without its `tools:` line may load with every tool. After this plan a created file appears whole or not at all.

## Scope

- `workbench/refresh.py` (`_changed`, `classify`) and the tests in `tests/test_refresh.py` and `tests/test_rerender.py` (Increments A and B).
- `workbench/projectfs.py` (`Writer.create_file`) and its tests (Increment C).
- `docs/specs/harness-refresh.md` ("Limits as built") for each Low closed.

## Non-goals

- Corroborating the manifest's hashes in the guarded store (still not planned).
- Any change to what `wb rerender` writes, to its states or to its digest.
- A change to the write order. A rendered file is still written before the permissions file.

## Assumptions and constraints

- **My call (marked):** Low 3 is closed by requiring the line on disk and refusing otherwise, not by writing it, because a preview
  must write nothing and a rerender should not edit `.git`. The owner may prefer the other offered form (add it, as attach does).
- **My call (marked):** Low 2 is closed in `Writer.create_file`, which is shared by install, adopt, add and rerender, so every
  caller gets it. The cost is a wider blast radius, so Increment C tests the callers' existing behaviour first. If the owner would
  rather limit it to rerender, Increment C is dropped and the Low stays recorded.
- Whether `Writer` may read `.git/info/exclude` (`safefs.validate_relpath` may refuse a `.git` component) is not known. Increment B
  step 1 finds out; if it is refused, B stops and reports rather than widen the reader.
- `workbench/` and `tests/` may not name a module, helper, harness or path other than the installer's own
  (`tests/test_boundary.py`); `.git/info/exclude` is the installer's own.
- Nothing is run for security: no new dependency, no secret, no network.

## Completion criteria

1. A stale file whose only change is a line separator shows at least one changed line in `wb preview rerender`, and the digest still binds it.
2. A run that would create a file refuses, naming the problem, when the clone's `.git/info/exclude` does not hold the layout's lines for it, and creates it when it does. The preview and the run agree.
3. A created file is never visible in a partial state: a write that fails part way leaves no file at the path, and an existing file or link at the path still refuses.
4. The existing behaviour of install, adopt, add, upgrade and rerender is unchanged where nothing failed; the full suite and `wb check` pass.

## Increments

### Increment A — Show a changed line separator (Low 4)

**Outcome:** the preview's changed lines come from text split on `\n` only, so a CR, VT or U+2028 change shows.
**Dependencies:** none.
**Affected areas:** `workbench/refresh.py`; `tests/test_refresh.py`; `docs/specs/harness-refresh.md`.
**Steps:**
1. Write the test first: two byte strings that differ only by one separator character give at least one changed line; see it fail.
2. In `_changed`, split on `\n` (keeping other separators inside the shown line, cleaned by the existing display step) and make the test pass.
3. Check that the shown text is still cleaned for the terminal (`display.clean`) so the separator cannot move the cursor.
4. Mark the Low closed in "Limits as built".
**Verification:** the new test red then green; `tests.test_refresh` and `tests.test_rerender`; `git diff --check`; `wb check`; a `reviewer` pass.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-close-rerender-lows#A`.

### Increment B — Require the exclude lines on disk (Low 3)

**Outcome:** `classify` refuses to create a file unless the clone's own `.git/info/exclude` holds the layout's lines that cover it.
**Dependencies:** A.
**Affected areas:** `workbench/refresh.py`, `workbench/rerender.py`; their tests; `docs/specs/harness-refresh.md`.
**Steps:**
1. Find out how the project's exclude file can be read without following a link, and whether `Writer.read_file` allows it. Stop and report if not.
2. Write the test first: a clone whose exclude file lacks the lines gets a refusal for a created file, and one that holds them does not; see it fail.
3. Read the file once in `classify`, treat a missing file as no lines, and test coverage against the lines read.
4. Keep the preview and the run in step: both call `classify`.
5. Update "Limits as built".
**Verification:** the new tests red then green; `tests.test_refresh`, `tests.test_rerender`, `tests.test_attach`; `git diff --check`; `wb check`; a `reviewer` pass.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-close-rerender-lows#B`.

### Increment C — Create a file whole or not at all (Low 2)

**Outcome:** `Writer.create_file` writes a private sibling, syncs it and links it into place, so a crash leaves no short file at the path.
**Dependencies:** none (independent of A and B; ordered last because it is the widest).
**Affected areas:** `workbench/projectfs.py`; its tests; the tests of install, adopt, add and rerender that read a created file; `docs/specs/harness-refresh.md`.
**Steps:**
1. Write the test first: a write that fails part way (a fault injected through `safefs._fire`) leaves nothing at the path and no sibling; see it fail.
2. Keep the exclusive, no-follow semantics: an existing file, a link or a non-directory in the way still raises `WriteConflict`.
3. Write the sibling with a private name in the same directory, fsync, `link()` it to the final name, remove the sibling, and clean up on every failure path.
4. Run the full suite, since every installer write path uses this method.
5. Update "Limits as built".
**Verification:** the new test red then green; `tests.test_projectfs` and every test that writes a file; the full suite `python3 -B -W error tests/run_all.py`; `git diff --check`; `wb check`; a `reviewer` pass.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-close-rerender-lows#C`.

## Verification for the plan as a whole

The full suite, `wb check`, `wb run code-work check`. An owner-run `wb preview rerender` on this clone afterwards to see that it still lists nothing.

## Risks and sensitive actions

- Increment C changes the primitive every installer write uses; a mistake there could break install or leave a stray sibling file. Mitigation: tests first, fault injection, the full suite, and a reviewer.
- Increment C creates a hard link, so a filesystem without link support would fail. The refresh plan already proposed this form; tests show the failure leaves nothing behind.
- Increment B reads a file inside `.git`; it must not follow a link, and must not write there.
- Whether to run a security review is the owner's to ask.

## Review record

Empty until a review is asked for.

## Deferred work

- Corroborating the recorded hashes in the guarded store.
- The scratch-clone trial of the manifest deny against the harness's other write tools.

## Result

### Increment A — Show a changed line separator (Low 4)

**Done.** `refresh._changed` splits on `\n` only (it used `splitlines`, which also splits on CR, VT, FF and U+2028, so two texts that
differed only in which separator they held compared equal and a stale file showed no changed line). Two tests in
`tests/test_refresh.py` (`Stale`) were written first and failed for that reason: three separator swaps (VT/FF, CR/U+2028, CRLF/LF)
each give the exact changed lines, and a change of only the final newline gives one added empty line. The preview still prints a
changed line through `_whole`, so a line that is not plain ASCII is shown as its JSON string. `harness-refresh.md` ("Limits as
built") now says the limit is closed. A file changed only by its final newline now shows one added or removed empty line, where it
showed none before; the spec says so.

**Verification as run.** `tests.test_refresh` and `tests.test_rerender` 143 OK (after the last edit); the full suite
`python3 -B -W error tests/run_all.py` 5914 tests in 12 roots OK (started before the U+2028 literal in a test was replaced by its
escape, which does not change the string); `git diff --check` clean; `wb check` no problems. `wb run code-work check` ran when the
plan was written (62 plans) and not again.

**Review.** One `reviewer` exchange, no blocking findings. It found one caller of `_changed` and one reader of `Row.lines`, and the
digest holds no lines, so it cannot change. Applied: the literal U+2028 character in the test source became the ` ` escape. Not
applied: an end-to-end test through `render` for a CR change (the existing `\x01` test covers the same display path).

**Not done.** Increments B and C. The plan's `Status:` line still says `Proposed`.

### Increment B — Require the exclude lines on disk (Low 3)

**Done.** Step 1 found that `Writer.git_bytes("info/exclude", limit)` already reads the file read-only, without following a link, with
a size limit, so nothing was widened. `refresh.classify` reads `.git/info/exclude` once, only when some row would be created, and
refuses a created file unless the layout entry that covers it has its own line there (`projectfs.exclude_line`, the line
`add_exclude` writes; a CR at the end of a line is ignored, a missing file has no lines), or when the file cannot be read as a plain
regular file. `covered` gained an optional `lines` argument and an entry that cannot be written as a line (`SafeFsError`,
`UnicodeEncodeError`) covers nothing. The preview and the run agree because both call `classify` (`rerender.py:148`, the only caller),
and the run rebuilds the plan after the typed digest. Nothing is written to `.git`. Tests first, in `tests/test_refresh.py` (`New`):
a file missing the lines, a missing exclude file and an exclude file that is a link were red (nothing refused) and are green; CRLF
endings with other lines, a clone with nothing to create and no exclude file, a `.git` that is a file (refused earlier, by the existing
check) and an entry that cannot be a line guard the other side. `harness-refresh.md` ("Limits as built") says what is checked.

**Verification as run.** `tests.test_refresh`, `tests.test_rerender`, `tests.test_boundary` and `tests.test_attach` 245 OK after the last
edit; the full suite `python3 -B -W error tests/run_all.py` 5919 tests in 12 roots OK (started before the last two tests, the `.git` file
and the unwritable entry, were added; those ran in the 245); `git diff --check` clean; `wb check` no problems.

**Review.** One `reviewer` exchange, no blocking findings. Applied: `UnicodeEncodeError` is caught when an entry is turned into a line
(fail-closed), and a test for a `.git` that is a file (the reviewer assumed this run's message would be the one shown; an earlier check
refuses it, so the test asserts that refusal). Not applied: naming "invalid entry" in the message, since the layout's entries are
validated at attach.

**Not done.** Increment C. Not exercised on a real worktree or submodule clone. The plan's `Status:` line still says `Proposed`.

### Increment C — Create a file whole or not at all (Low 2)

**Done.** `Writer.create_file` now checks the final name is free (lstat), fills and fsyncs a sibling `.workbench-<pid>-<hex>.tmp`
in the same directory (mode 0644 under the umask, 0755 when executable, as before), fires a new hook stage `projectfs_filled`, and
`link()`s the sibling to the final name (exclusive; `dir_fd`, no follow). The sibling is unlinked on every path out, and the path
is added to `written` only after the link. Tests first in `tests/test_projectfs.py`: a fault at `projectfs_filled` leaves nothing
and lists nothing, and a file appearing during the write is a `WriteConflict` and is kept; both were red and are green. Two more
guard the one-link result and the umask. One existing assertion in `tests/test_adopt.py` looked for created files under their
final names in an `os.open` watch; it now looks for the sibling name (the check that no existing file is opened for writing is
unchanged). `refresh.Partial`'s docstring and one comment, and two paragraphs of `harness-refresh.md`, describe the new behaviour.
A conflict at the final name now says "the path already exists" for a link or directory there, where it said "a link or a file is
in the way"; no test or doc asserted the old text.

**Verification as run.** The 14 write-path test modules 586 OK; the full suite `python3 -B -W error tests/run_all.py` 5925 tests in
12 roots OK (started before the `refresh.py` comment edits made after review); `git diff --check` clean; `wb check` no problems.

**Review.** One `reviewer` exchange, no blocking findings. Applied: the `Partial` docstring and comment no longer overstate the
guarantee (an interruption between the link and the listing leaves a whole, unlisted file, which the next run reads safely).
Answered: `executable` still ends in `fchmod(0o755)` as before, so the mode is unchanged. Not applied: a test for `wb recover`
on a marker with two links; surfacing a failed sibling unlink; checking the linked inode is the one written (`replace_file` has
the same gap); the descriptor leak on an interrupt between `os.open` and the next line (same shape as `replace_file`);
`test_refresh`'s `Partial` test still simulates the old in-place write with a mock.

**Not done.** Not run on Linux or a filesystem without hard links. `tests/test_projectfs.py` still lacks an `import unittest.mock`
(one test errors when the file runs alone; unrelated). The `Partial` message still says "may be partly written". The plan's
`Status:` line still says `Proposed`.
