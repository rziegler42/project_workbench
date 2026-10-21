# Harness paths from the harness module

Status: Approved
Created: 2026-10-21

Candidate: workbench-v1#module-harness-paths
Specs: docs/specs/module-boundary.md, docs/specs/module-contract.md, docs/specs/harness-modules.md

## Goal

The installer reads a harness's paths from that harness module's `layout` and from nowhere else. The table of
harness names and paths in `workbench/check.py` and the settings path in `workbench/layout.py` leave the
code, and a boundary test fails if any file of `workbench/` or `tests/` (outside `tests/fixtures`) names a
first-party module, one of its helpers, a harness name or a harness path. The installer's tests then prove
mechanism on a synthetic harness module and do not depend on the `claude` module being in the distribution
(`module-boundary.md`, "Harness paths come from the harness module" and "What the installer's own tests may
use").

## Scope

- Facts `wb check` needs about a harness (the top-level names it owns, the directories attach generates into,
  the entries it tolerates beside them), derived from a layout by one function in `layout.py`.
- One new optional layout key, `tolerated`, because one of those facts (the shared `settings.json` that
  Claude itself keeps in its directory) cannot be derived (see Choices).
- Replacing the one literal settings path in `layout.py` with rules that hold for any harness.
- A small reader that returns the layouts of the harness modules of the first-party packages in the running
  workbench's distribution, and `wb check` using it in place of `HARNESSES`.
- Removing the `opencode` and `codex` entries, which no module describes.
- Rewriting the installer's tests that name `claude`, `groundwork`, `code-work`, their helpers or their paths so
  they use synthetic modules, and moving what is specific to the shipped `claude` module into
  `packages/workbench/claude/tests/`.
- The boundary test, and rewording the comments in `workbench/` that name a harness or module.
- Updating the three specs to say what is built.

## Non-goals

- A new harness. `opencode` and `codex` are removed from the table and nothing replaces them.
- Moving the harness **tool-name** guards (`RULE_NAMES`, `TOOL_NAMES`, `INERT_TEMPLATE_NAMES` in `layout.py`).
  They stay, as the Choices explain.
- Any change to what attach writes, to what `wb check` reports for a project with the `claude` module, or to
  the neutral formats.
- Reading harness layouts from a third-party package, or from a project (see Choices, 4).
- The `code-work-*` plans.

## Assumptions and constraints

- Python 3.14, standard library only; `python3 -B -W error tests/run_all.py` is the full test command (2269
  tests in 4 roots at the start).
- **Impact, from a repository search at `054868e` on 2026-10-21** (`graphify: skipped — the repository has no
  graph tooling`). In `workbench/` the harness knowledge is two tables: `HARNESSES` in `check.py` (used by
  `_strays`, `_shallow`, `_generated`, `_scratch_path` and `_others`) and `SETTINGS_PATHS` in `layout.py` (used by
  `_settings`). `RULE_NAMES`, `TOOL_NAMES` and `INERT_TEMPLATE_NAMES` in `layout.py` name Claude's tools. Six
  `workbench/` files also name a harness or module in a comment (about 14 lines). The larger cost is in
  `tests/`: about 390 lines in 23 files name `claude`, `groundwork`, `code-work` or a helper, mostly
  `test_attach.py` (100), `test_check.py` (53), `test_layout.py` (47), `test_harnessplan.py` (42),
  `test_install_attach.py` (38) and `test_groundwork_fixture.py` (37). `tests/test_attach.py`,
  `test_install_attach.py` and `support_install.py` attach the real shipped `claude` module.
- A harness's `layout` already names every path attach writes, and the layout validator already requires an
  `exclude` entry to cover each of them (`layout.py`, module docstring). The facts `check` needs are therefore
  derivable except the tolerated file.
- "Known harness" means a harness module of a package that `firstparty.is_first_party` accepts in the
  workbench's own distribution. The distribution is the trust root for the layout, as for shipped approvals.
- A change to any file of a first-party module, including its `tests/`, changes its tree hash, so the owner
  runs `python3 -m workbench release-approvals` and approves removing stale records. Only increment C changes
  the `claude` module, so that happens once. I do not run it. While records are stale about 104 tests skip.
- `docs/specs/module-boundary.md` is Current. The edits to it here mark done what the plan builds and record
  the departures below, which the owner approves with this plan.

### Departures from the specification

- **Tool names stay in the installer** (Choice 1). The specification's table puts "tool names" in module
  content; this plan keeps the three tool-name guards in `layout.py` until a second harness exists.
- **A new layout key, `tolerated`** (Choice 2), which the specification does not mention.
- **A weaker settings-path guard** (Choice 3), if the owner takes the recommended option.

### Choices for the owner

The plan assumes these. Each is the owner's to change at approval, and none is binding before then.

1. **Tool-name guards stay in the installer for now.** The spec lists "tool names" among what a harness owns,
   but its inventory names only `HARNESSES` and `SETTINGS_PATHS`. The three tables are fail-closed guards that
   the installer applies to a layout it cannot verify (a deny under a name the harness never consults, a read-only
   agent given a shell). Their contents are Claude's. Moving them to the module would make the guard
   circular, because the layout would then say which of its own names are acceptable. A generic form needs a
   second harness to design against, so it waits for `opencode-harness`. The boundary test looks for module,
   helper, harness and harness-path words, not tool names, so it passes with them in place.
2. **A layout key `tolerated`** (a list of literal paths) names files that the harness itself, or the owner, may
   keep inside the harness's directory, so `wb check` does not warn about them. `claude` declares
   `.claude/settings.json`. The alternative is to drop the allowance, which would make `wb check` warn about
   that file for every Claude user.
3. **The settings path rule.** The specification lists `SETTINGS_PATHS` among the tables to remove. It is the
   same kind of guard as the tool-name tables: it makes sure the `deny` rules land in a file the harness
   reads. Options:
   - *(recommended, and what the specification says)* Replace the literal with: a safe, unreserved path of
     exactly two segments, the first a dot-directory other than `.git` and `.workbench`, the name ending
     `.json`, and covered by the layout's `exclude` (already required). Increment B settles the exact wording
     by tests. **After this, nothing but the owner's approval of the module's layout stops a harness from
     declaring a settings file its tool never reads** (for Claude, `.claude/rules.json`), which would leave
     the `deny` list silently inert. Exclusive create and `exclude` coverage do not address that.
   - Keep the literal beside the tool-name guards as a recorded residual, and move it with them when a second
     harness exists. The boundary test then needs the settings path on its exception list.
4. **Where harnesses come from.** Only first-party harness modules of the running workbench's distribution are
   known to `wb check`. A harness recorded in the local manifest but not known gets one warning ("not a harness
   this workbench knows, so its files were not scanned"); today it would be silently unscanned. A third-party
   harness is recognised by `check` only after a later decision.
5. **The boundary test derives its words** from the `module.json` files under `packages/` (module names, the
   file names under `ships` and the last segment of each helper path, which is its pin name, each layout's
   root file, kind directories, settings path, `exclude` entries and `tolerated` paths), plus a short list in
   `tests/fixtures/` of harness names that have no module yet (`opencode`, `codex`), so the test names none
   itself. Names are matched case-folded (so `Claude` in a docstring and `code-work-module` in a comment are
   caught); a path is matched as a unit, so `SKILL.md` (the neutral format's name) is not flagged.

## Completion criteria

- `HARNESSES` and `SETTINGS_PATHS` are gone. `wb check` takes the roots, generated directories and tolerated
  entries of the attached harness, and the roots of the other known harnesses, from their layouts, and reports
  for a project with the `claude` module what it reported before.
- A layout may declare `tolerated`; the verifier checks it. The settings path rule holds for any harness
  and is refused with a test for each rule broken.
- The installer's tests build and attach synthetic harness modules with made-up names and paths. The shipped
  `claude` module is tested in `packages/workbench/claude/tests/`: its layout verifies, attach writes the
  expected files and rules, and `wb check` on the result is clean and finds a stray.
- The boundary test passes, and fails when a first-party module name, a helper name, a harness name or a harness
  path is added to a file of `workbench/` or `tests/` (shown by a mutation check).
- With `packages/` emptied in a scratch copy of the tree, the installer's own tests pass with no skip caused
  by a missing package (a recorded run, J).
- The security pass is recorded with what was accepted and not fixed; the specs describe what is built; the
  full suite passes.

## Increments

### Increment A — Facts derived from a layout, and the `tolerated` key

Outcome: `layout.facts(layout)` returns what `check` needs, and a layout may declare `tolerated`. Nothing
calls the function yet and no module changes.
Dependencies: none.
Affected areas: `workbench/layout.py`, `workbench/declarations.py` (`LAYOUT_KEYS`),
`tests/test_layout.py`, `docs/specs/module-contract.md`.

1. Tests first, on a synthetic layout with made-up names: `roots` are the top-level names of the root file,
   every kind directory and the settings path; `generated` are the kind directories (the path up to `/{name}`);
   `directories` are the top-level directories among the roots; `tolerated` is the declared list. A layout
   with no root, no settings or no kinds gives the corresponding empty result. `tolerated` is refused when it is
   not a list of at most 16 safe paths, when a path is not inside a directory the layout writes into, when it
   is listed twice, or when it equals a path the layout writes.
2. Add `tolerated` to the layout keys and validator, and `facts`.
3. Add `tolerated` to the module contract's layout table.

Verification: the new tests, `test_layout.py`, `test_declarations.py`, the full suite. Evidence: each refusal
has a test; the shipped `claude` module still verifies unchanged.

### Increment B — The settings path rule

Outcome: the settings path is checked by rules that hold for any harness, and no harness path is in `layout.py`.
Dependencies: none (independent of A).
Affected areas: `workbench/layout.py`, `tests/test_layout.py`, `docs/specs/module-contract.md`.

1. Tests first: a path of two segments with a dot-directory first and a `.json` name is accepted; each of these
   is refused naming `layout.local_settings.path`: one segment, three segments, a first segment that is not a
   dot-directory, `.git`, `.workbench`, `.config/project-workbench`, a name not ending `.json`, an unsafe path
   (`..`, absolute, a NUL, a backslash), a case or Unicode fold of a reserved name, and a path the `exclude` list
   does not cover. The existing test that the claude path is accepted keeps passing on the claude layout.
2. Replace the `SETTINGS_PATHS` test with these rules.
3. Update the contract's wording for `local_settings.path`.

Verification: the new tests, the full suite. Evidence: a mutation check (each rule removed fails a test). This
increment changes a path attach writes, so the security pass covers it (increment J).

### Increment C — The `claude` module declares what it tolerates, and tests itself

Outcome: the shipped `claude` module declares `tolerated` and carries the tests of what is specific to it.
Dependencies: A.
Affected areas: `packages/workbench/claude/module.json`, `packages/workbench/claude/tests/`,
`workbench/shipped_approvals/` (owner-run), `docs/specs/harness-modules.md`.

1. Add `"tolerated": [".claude/settings.json"]` to the layout.
2. Add tests to the module, written against the real module: its layout verifies and its facts are the roots
   `CLAUDE.md` and `.claude`, the three generated directories and the one tolerated file; attach into a
   synthetic project writes exactly the expected files, the exclude lines and the settings file with a `deny`
   for every owner-run command; `wb check` on the result is clean, reports a file under `.claude/skills` that
   attach did not write, warns about an unknown entry beside the tolerated file and not about it, and reports
   a tracked `.claude/` path. These are the claude-specific assertions that increments F and G take out of the
   installer's tests.
3. **Owner step:** run `release-approvals` and approve removing the stale records. I preview the removal and
   run it with `claude-workflow remove --recursive` only after the owner says so.

Verification: the module's tests, the full suite after the release step. Evidence: the module's tests run in
the `packages/workbench/claude/tests` root; the package verifies; no `__pycache__` in the package.

### Increment D — Known harnesses, and `wb check` from layouts

Outcome: `wb check` takes its harness facts from layouts, and `HARNESSES` is gone.
Dependencies: A, and C including the owner's `release-approvals` step, because until then `harnesses.known`
treats `claude` as not first-party and the unchanged `test_check.py` cannot pass against the real distribution.
Affected areas: new `workbench/harnesses.py`, `workbench/check.py`, `workbench/cli.py` only if the distribution
is passed down, `tests/test_harnesses.py`, `tests/test_check.py`, `docs/specs/harness-modules.md`.

1. Tests first, on a synthetic distribution (a temporary `packages/` with a package, a harness module and its
   shipped record, built with the existing release mechanism): `harnesses.known(distribution)` returns the
   facts of each first-party harness module; a module of type `module` is ignored; a package that is not
   first-party (record missing or stale, a link, a name that differs from its directory) is not known; a
   layout that does not verify is not known; an empty or missing `packages/` gives none; a harness listed in
   two packages is a refusal of that name, not a pick.
2. Implement `harnesses.known`, reading with the declaration loader and `firstparty.is_first_party`.
3. In `check.py`, replace each use of `HARNESSES` by the facts of the attached harness (strays, shallow,
   tolerated) and by the roots of all known harnesses (tracked output, other harness's files, scratch
   paths). `run` and `examine` take an optional `distribution`, defaulting to the running one. An attached
   harness that is not known gives the one warning of Choice 4.
4. Remove the `opencode` and `codex` entries. The existing `test_check.py` stays as it is and must pass with
   the real distribution; new tests use the synthetic one: a project attached to a synthetic harness gets
   strays and other-harness files reported from its layout; a harness unknown to the workbench gets the
   warning; a tracked path under another known harness's root is a problem.

Verification: `test_check.py`, `test_harnesses.py`, the full suite. Evidence: the unchanged `test_check.py`
passes against the real distribution, so what `wb check` reports for the `claude` module did not change.

### Increment E — A synthetic harness for the layout and translation tests

Outcome: the tests of the layout validator, the translation and the permission rendering use a synthetic
harness, and do not name `claude`.
Dependencies: C (the claude-specific assertions have moved).
Affected areas: `tests/support_harness.py`, `tests/test_layout.py`, `tests/test_harnessplan.py`,
`tests/test_permissions.py`, `tests/test_neutral.py`, `tests/test_module_test_imports.py`.

1. Replace `CLAUDE` in `support_harness.py` by a layout with made-up names (root file `FIXTURE.md`, directory
   `.fixture/`, settings `.fixture/settings.local.json`), keeping the tool names the guards in `layout.py`
   require (Choice 1). Keep an alias only if a module's tests import the old name; none should.
2. Update the four test files and their expected paths. An assertion that proved something about the real
   Claude rendering and is not already in the module's tests is added there in C's file, not dropped; if that
   needs a second change to the module, it is made here and the release step repeated.
3. `test_module_test_imports.py` names `CLAUDE` only as a string in its fixtures; change it to the new name.

Verification: the four files, then the full suite. Evidence: the test count is unchanged or higher than before
(2269 plus the tests of A to D), and the number of `claude` hits in these files is zero.

### Increment F — Attach tests on a synthetic harness

Outcome: `test_attach.py`, `test_install_attach.py`, `test_exclude.py` and `test_localmanifest.py` attach a
synthetic harness module built in a temporary package, not the shipped `claude` module.
Dependencies: E.
Affected areas: those four files, `tests/support_install.py`, `tests/support.py`.

1. Add a builder to the shared test support that writes a synthetic harness module (declaration with the
   synthetic layout, neutral skill, agent and command) into a package directory. It is the fixture builder
   `module-boundary.md` Choice 3 calls for, and a module's tests may reuse it.
2. Switch the four files to it and update the paths, names and the `harness` argument (`workbench/claude`
   becomes the synthetic package and module). `support.require_release` is called only where a real package is
   still attached, which after this increment is none of these files.
3. Where a test of these files asserted something only the real module can show, it is already covered by C.

Verification: the four files, then the full suite. Evidence: no `packages/workbench` path in the four files;
the full suite passes with the tests that attached the real module now independent of its approval records.

### Increment G — Check tests on a synthetic harness

Outcome: `test_check.py` runs on the synthetic harness and on a synthetic distribution.
Dependencies: D, F.
Affected areas: `tests/test_check.py`.

1. Switch `Clone`/`Base` use to the builder of F and the synthetic distribution of D; update paths and the
   expected "harness: <name> attached" lines.
2. Remove the assertions about `.opencode`, `opencode.json` and `.codex` (those harnesses are gone) and cover
   "files of another known harness" with a second synthetic harness.

Verification: `test_check.py`, the full suite. Evidence: no `claude`, `opencode` or `codex` in the file.

### Increment H — The remaining fixtures and names

Outcome: no other file of `tests/` names a first-party module, helper, harness or harness path.
Dependencies: F.
Affected areas: `tests/test_groundwork_fixture.py` (renamed to a neutral fixture file by the owner's hand
commit if the helper cannot commit a rename), `tests/support_install.py`, `tests/support_doccheck.py`,
`tests/support_docs.py`, `tests/test_modulefiles.py`, `tests/test_verify.py`, `tests/test_run.py`,
`tests/test_declarations.py`, `tests/test_request.py`, `tests/test_manifest.py`, `tests/test_kit.py`,
`tests/test_base.py`, `tests/support.py`, and the groundwork module's tests if a support file moves into them.

1. The fixture "shaped like `groundwork`" gets a made-up module name; its docstring says what it models without
   naming the module.
2. `support_doccheck.py` and `support_docs.py` serve only the groundwork helpers' tests. Move them into
   `packages/workbench/groundwork/tests/` if that is where all their callers are, otherwise make them take
   the helper path as an argument and name no module. This changes the `groundwork` module, so the release
   step is repeated for it.
3. Fix each remaining hit one by one, leaving the release-mechanism exception (`test_firstparty.py` and the
   `support.py` code that uses the distribution) naming only the package directory.

Verification: the full suite; a repository search for the derived words in `tests/` returns only the
exception. Evidence: the search output, recorded in the plan's Result.

### Increment I — The boundary test and the comments

Outcome: a test enforces the rule, and the comments in `workbench/` name no harness or module.
Dependencies: A to H.
Affected areas: new `tests/test_boundary.py`, `tests/fixtures/boundary-words.json`, `workbench/check.py`,
`workbench/layout.py`, `workbench/pointers.py`, `workbench/neutral.py`, `workbench/modulefiles.py`,
`workbench/harnessplan.py`.

1. Tests first: the word list is derived as in Choice 5 from a synthetic distribution (a module name, a helper,
   a layout path), and a file of a synthetic installer tree that names each kind of word fails with the file
   and line; a tree that names none passes; the derivation ignores a word of two characters or fewer and
   matches a path as a unit; an unreadable or oversized file is a failure, not a skip.
2. Run it against the real tree (`workbench/`, `workbench/wbkit/`, `tests/` without `tests/fixtures`) and the
   real `packages/`. Reword each hit in `workbench/` (the layout docstring example, `check.py` prose, the
   comments in `pointers`, `neutral`, `modulefiles` and `harnessplan`).
3. Mutation check: add `claude`, `doccheck`, `.claude/skills` and `opencode` to a scratch copy of a
   `workbench/` file in turn; each fails the test.

Verification: the test and the full suite. Evidence: the mutation results.

### Increment J — Without the first-party modules, the security pass, and the documents

Outcome: the installer's tests pass with no first-party module in the distribution; the plan's security pass is
recorded; the specs describe what is built.
Dependencies: I.
Affected areas: `tests/test_boundary.py` (or a sibling test), `docs/specs/module-boundary.md`,
`docs/specs/harness-modules.md`, `docs/specs/module-contract.md`, `docs/development.md` if a command changed,
this plan.

1. Run once, not as a test (a test that ran the installer's test root inside itself would recurse and take
   twice as long): copy the tree to a scratch directory with `packages/` empty, run
   `python3 -B -W error tests/run_all.py` there, and record the result in the Result. The evidence is the skip
   count: any skip that a missing package causes (`support.require_release` skips when there is no release) is
   a test still tied to a shipped module and is fixed, so the run must show no such skip. A pass with those
   skips does not count.
2. Security pass by a `security-reviewer`, then a second to try to bypass its fixes (the process of
   `module-checks`): the settings path rule (B), `harnesses.known` (a link or a changed package presented as
   first-party, a layout with hostile paths, a project that records a harness name chosen to collide), and
   `check`'s use of the derived roots (a layout whose roots make `check` read or flag more than it should),
   and the settings rule with a path the harness never reads.
   Record findings, fixes with tests, and what was accepted and not fixed.
3. Specs: in `module-boundary.md` mark the inventory rows done and record the tool-name residual and where it
   goes next; in `harness-modules.md` replace "Only Claude, opencode and Codex roots are scanned" and the
   stray-scan limits with what is built; in `module-contract.md` confirm `tolerated` and the settings rule.
4. Write the Result and propose the decision `2026-10-21-harness-facts-from-layouts` (Proposed; accepting it is
   the owner's act) covering Choices 1 to 4 and pointing at the departures listed above.

Verification: the full suite; `git diff --check`; no `__pycache__` under `packages/`. Evidence: the recorded
security pass and the count of tests.

## Verification

- After each increment: its own tests, then `python3 -B -W error tests/run_all.py`.
- `wb check` on a project that has the `claude` module and is attached gives the same lines before and after
  (shown by `test_check.py` against the real distribution in D, and by the module's tests after).
- The word search of the boundary test returns no hit outside the exception, and the run with `packages/`
  emptied (J) shows no skip caused by a missing package.
- Linux and a virtualenv interpreter remain untested, as in the earlier plans.

## Risks and sensitive actions

- **Weakening a guard.** B removes a literal allowlist for the path that carries the `deny` rules. The
  replacement is structural; the layout must still be covered by `exclude`, and attach still creates the
  file exclusively and never overwrites. It does not ensure the harness reads that file (Choice 3). The
  security pass tries to bypass the rule, including with a settings path the harness never reads, and a
  reviewer who finds the rule too loose sends the plan back to the owner.
- **A wider trust input for `wb check`.** `check` reads module declarations from the distribution. The
  distribution is the trust root and the module must match its shipped record; a module changed since release
  is not known, and `check` warns. Covered by the security pass.
- **Stale approvals.** C and H change first-party modules. Between the edit and the owner's `release-approvals`
  about 104 tests skip, so I run the full suite again after the release step, not before.
- **Two-sided test churn.** Increments E to H rewrite many assertions. The count of tests must not fall and the
  claude-specific assertions are moved, not dropped (C). A reviewer compares the assertions removed with the
  ones added.
- **Rename and delete in one commit.** The commit helper refuses a commit that mixes a rename or deletion with
  additions, so H may need the owner's hand commit.
- Sensitive actions: `release-approvals` and removing stale records (owner), and the commits, which the owner
  asks for.

## Review record

Independent review by Codex (`ask-codex review-plan`, medium effort, 2026-10-21): round 1 of a bound of 3,
outcome converged, no findings and no pending decisions. The reviewer called the plan complete and consistent
with the specifications, decisions and implementation evidence. Before the review, an advisor pass changed the
plan in five places: the run with `packages/` emptied is a recorded one-off and not a recursive test; Choice 3
says what the settings-path guard stops guaranteeing and offers keeping the literal; a "Departures from the
specification" list was added; the boundary-word derivation covers pin names and is case-folded; D waits for
C's owner step. The review does not approve the plan; it stays `Proposed` until the owner approves it.
The owner answered "Go with your recommendations" on 2026-10-21, which settles Choices 1 to 5 as written,
including the recommended option of Choice 3. The owner then approved the plan
("Approve, commit") on 2026-10-21.

## Deferred work

- Moving the tool-name guards out of the installer, with the second harness (`opencode-harness`).
- Recognising a third-party harness module in `wb check`.
- Case-insensitive filesystems and a live `claude` session, untested as before.

## Result

Not started.
