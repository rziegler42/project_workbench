# Raise the byte limit of the document check

Status: Completed
Created: 2026-10-29
Candidate: none — a limit in an existing repository check was crossed by the combined content of two branches, and no roadmap candidate names it.
Specs: repository-boundary

## Goal

`wb check` reads every tracked Markdown document for a pointer to untracked content, up to a total of 4 MiB (`MAX_DOCUMENT_BYTES`
in `workbench/check.py`). The tracked documents on `origin/main` total 3,860,052 bytes. The merge of the branch `freecad-module`
(3,897,962 bytes alone) into it totals 4,207,568 bytes, 13,264 over the limit, so the check stops reading and reports "more
documents or references than are looked at; not all were looked at" as a problem. Done means the limit leaves room for the
tracked documents to grow, `wb check` reports no problem on the merged tree, and the check still stops at the limit.

## Scope

- The value of `MAX_DOCUMENT_BYTES` in `workbench/check.py`, and one test that the default limit lets a document set over the old
  limit be read in full.
- Any text in `docs/development.md` or a spec that states the old figure, if one is found.

## Non-goals

- `MAX_DOCUMENTS` (5000) and `MAX_LOOKUPS` (5000), which are not close to being reached (279 tracked Markdown files).
- Any change to what the check looks for, how it reads a file, or which files it reads.
- Trimming documents to fit under the old limit.
- Merging, pushing, or any change to the `freecad` module.

## Assumptions and constraints

- The limit is a safety bound on the work of one check, not a rule from a spec: a search of `docs/specs/` and `docs/decisions/`
  found no statement of 4 MiB. `tests/test_check.py` patches `MAX_DOCUMENT_BYTES` to test the stop, so the existing test does not
  depend on the value.
- The merge of `origin/main` into `freecad-module` is staged and uncommitted when this plan is written. It is committed first,
  on the owner's word, with `wb check` failing only on this limit; nothing is pushed. If the commit helper refuses to commit a
  merge, the owner commits it, or aborts it, and this plan is reconsidered.
- Increment A edits `workbench/check.py`, which is workbench code and not part of `packages/workbench/`, so no shipped approval is
  released for it. If the edit gate or the package-tree hash says otherwise, stop and tell the owner.
- The owner chose 8 MiB (2026-10-29): about 4 MiB of headroom over the merged tree, and still a small read.

## Completion criteria

1. `MAX_DOCUMENT_BYTES` is 8 MiB (8 * 1024 * 1024).
2. A test shows that a tracked document set over 4 MiB and under the new limit is read in full with no "not all were looked at"
   problem, and the existing tests of the stop at the limit still pass.
3. `wb check` reports no problem on the tree with the merge committed.
4. The full suite, `wb run code-work check` and `git diff --check` pass.

## Increments

### Increment A — Raise the limit

**Outcome:** the document check reads up to the new limit and `wb check` is clean on the merged tree.
**Dependencies:** the merge of `origin/main` into `freecad-module` is committed.
**Affected areas:** `workbench/check.py`, `tests/test_check.py`, and any document that states the old figure.
**Steps:**
1. Search `docs/` and `tests/` for the figure 4 MiB or 4194304 and list every place; stop and tell the owner if a spec states it as a
   rule.
2. Test first: add a test in `tests/test_check.py` that builds a project whose tracked Markdown totals just over 4 MiB in a few
   files and expects no "not all were looked at" problem; see it fail with the old limit.
3. Change `MAX_DOCUMENT_BYTES` to the new value.
4. Run `tests/test_check.py`, the full suite, `wb check`, `wb run code-work check` and `git diff --check`.
5. Record the increment in the Result and stop for the owner.
6. On the owner's word, make the one local commit with `wb run safe-git commit`, the exact paths and the trailer below.
**Verification:** the new test fails before the change and passes after; the existing stop-at-the-limit tests pass; `wb check`
prints no problem on the merged tree; the full suite is green.
**Evidence:** the one local commit, trailer `Plan: 2026-10-29-raise-check-document-cap#A`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` green in all roots; `wb check` and `wb run code-work check` report no problems;
  `git diff --check` prints nothing.

## Risks and sensitive actions

- The change widens a bound on a filesystem read in a repository check. The check reads each file once through the safe reader, so
  the extra work is at most the new limit in bytes. The owner was asked and declined a security review (2026-10-29).
- A larger limit lets the documents grow further before the check complains. The warning at the limit remains a problem, not a
  warning.
- Nothing is committed or pushed without the owner's explicit word.

## Review record

Empty until a review is asked for.

## Deferred work

- A check that reports how close the documents are to the limit before they cross it.

## Result

### Increment A

- **Found at step 1:** the plan's assumption that no spec states the figure was wrong. `docs/specs/harness-modules.md` (the
  `wb check` paragraph) and `docs/development.md` (the `wb check` bounds) both state 4 MiB. The plan's `Specs:` line names only
  `repository-boundary`, so `harness-modules` is also changed. I stopped and told the owner; the owner chose to go ahead under
  the existing Scope ("any text in `docs/development.md` or a spec that states the old figure") without a new approval, and to
  record the understatement here. The other 4 MiB figures found (the level log, the review-engine state, `doccheck`'s own bound
  in the groundwork module, and old plans as history) are different bounds and were not changed.
- **Test first:** `test_documents_over_four_mebibytes_in_all_are_looked_at_in_full` in `tests/test_check.py` tracks three Markdown
  files of 1.5 MiB each and expects no "not all were looked at" problem and exit code 0. It failed with the old limit
  ("problem: more documents or references than are looked at; not all were looked at") and passes with the new one.
- **Written:** `MAX_DOCUMENT_BYTES` in `workbench/check.py` is `8 * 1024 * 1024`; the figure is updated to 8 MiB in
  `docs/specs/harness-modules.md` and `docs/development.md`.
- **Verification as run:** `tests/test_check.py`, 45 tests, OK (44 before the new one); the full suite, 6077 tests in 13 roots,
  OK; `wb check` found no problems on the merged tree (it reported the size problem before); `wb run code-work check` (72 plans)
  found no problems; `git diff --check` printed nothing.
- **Gate:** no shipped approval was released: the change is outside `packages/workbench/`.
- **Not done:** no security review (the owner declined it); no independent review (only when the owner asks). The deferred
  check that reports how close the documents are to the limit was not built.
