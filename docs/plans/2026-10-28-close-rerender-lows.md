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
