# The safe-git module: git work moves out of code-work

Status: Approved
Created: 2026-10-22
Candidate: none — carries out the accepted decision `2026-10-22-git-work-in-its-own-module`; the roadmap has no candidate for it
Specs: code-work, safe-git, module-boundary, module-contract, trust-and-approval

## Goal

Move `commit` and `remove` out of the `code-work` helper into a first-party module, `safe-git`, so a project
with no process module (a CAD or EDA project) can have safe commits and approved deletions, and so
`code-work-approval` builds its gate and deny rules against the final command name. Add the one piece of
git-specific guidance the `port-superpowers` candidate would otherwise have to supply: a neutral skill that
teaches an agent to commit through the helper.

When this plan is done:

- `wb run safe-git commit` and `wb run safe-git remove` behave exactly as `wb run code-work commit` and
  `remove` do today, with the attribution setting at `.workbench/safe-git.json`;
- the `code-work` helper has only `check`, `plans` and `report`, and `code-work` hard-requires the capability
  `commit`;
- the moved git code is the same code: the security pass of `2026-10-22-code-work-commit` still stands for it;
- a neutral skill `commit-changes` ships in `safe-git`;
- the shipped approvals are made again, and the specs, guide, roadmap and decision text say where git work lives.

## Scope

- **The module** `packages/workbench/safe-git/`: `module.json` (type `module`, provides `commit`, command
  `safe-git` with the arguments `commit` and `remove`, kit 1), the helper `helper/safe-git`, its tests, and the
  skill.
- **The helper**: lines 676 to 1720 of `packages/workbench/code-work/helper/code-work` (the git runner,
  `commit`, `remove`), plus the few shared definitions they use (`Refused`, `shown`, `find_root`).
- **`code-work`**: the helper loses those lines and the two commands; the declaration loses two arguments and
  gains `requires: commit`; the policy block and the plans README say the commit goes through the git helper.
- **Tests**: the git, commit and remove tests and `support_git.py` move; `test_codework_module.py` is split.
- **The skill** `commit-changes` (see Choice 5).
- **The release** of the shipped approvals (`release-approvals`, run by the owner), and a review of the move.
- **Docs**: a spec `docs/specs/safe-git.md` taking over the Commit section of `code-work.md`, edits to the
  specs and guide that name the old command, the roadmap, and the decision records.

## Non-goals

- Any change to what `commit` or `remove` do, other than the command name and the setting path. No new git
  subcommand, no push, branch, worktree or merge.
- Plan approval, review, caps and the push checkpoint (`code-work-approval`).
- The deny rules and the approver in the owner's `~/.claude` (`global-config-migration`).
- Porting any other superpowers skill (`port-superpowers`). Only the git-specific slice is taken here.
- Moving the three read-only subcommands, or any change to `groundwork`.

## Assumptions and constraints

- Python standard library only; tests with `unittest`; full suite `python3 -B -W error tests/run_all.py`
  (2638 tests in 4 roots today, and it gains a fifth root). Real git is used; a test that needs it skips with a
  reason when `git` is not found.
- The installer and its tests must not name `safe-git`, its helper or its paths (`tests/test_boundary.py`).
- The code moves unchanged. The only edits to it are listed in increment A; any other edit stops the plan.
- Nothing is installed in a real project yet, so no pin or setting file needs migrating.
- The helper refuses a commit that mixes deletions with additions, so a move commit made with it fails for the
  increments that delete files. For those, the owner's permission to run plain `git add -A -- <paths>` and
  `git commit -m` as separate calls applies, and the result is checked with `git status`.

### Choices (made by me; the owner may change any)

1. **Candidate: none.** Adding a roadmap candidate would be a direction change; the decision record is the
   authority. Completion is therefore not derived.
2. **Add, then remove.** Increment A adds the module as a copy, so each increment is verified on its own;
   increment B deletes the original and rewires `code-work`.
3. **The setting is renamed with no compatibility.** `.workbench/code-work.json` becomes
   `.workbench/safe-git.json`, with the same format and rules. Nothing is installed, so nothing reads the old name.
4. **A hard requirement.** `code-work` requires `commit` (the record says so).
5. **One new skill, `commit-changes`.** The superpowers skills specific to git are `using-git-worktrees` and
   `finishing-a-development-branch`. Neither is ported here: worktrees and branch finishing need git
   subcommands the helper deliberately does not run, merging into a shared branch is outside the agent
   (`code-work.md`), and the push is a checkpoint that `code-work-approval` builds. The reasons are recorded in
   the new spec, so `port-superpowers` starts from them. The skill is written new, from the owner's own commit
   rules, and copies no superpowers text.

## Completion criteria

1. `packages/workbench/safe-git/` exists, verifies as a first-party `module`, provides `commit`, ships only its
   helper, and `package.json` lists it after `groundwork`.
2. Through the launcher, in an installed project, `commit` makes a first and a next commit, refuses an
   unborn-branch claim and an attribution message, and `remove` previews then removes, all as the tests of
   `2026-10-22-code-work-commit` show; an edited helper is refused.
3. The attribution setting is read from `.workbench/safe-git.json`, absent means refuse, and
   `.workbench/code-work.json` is read by nothing.
4. The `code-work` helper contains no git code: it never starts a program, and `commit` and `remove` are not
   among its arguments.
5. Installing `code-work` without `safe-git` stops with the hard-requirement message; installing both works.
6. A diff of the moved region against the original shows only the edits listed in increment A.
7. Every test of the moved code passes in the new root; the full suite passes; the boundary test passes.
8. The shipped approvals match the packages and the stale records are gone.
9. The skill is accepted by the neutral reader, names no tool but the two commands, and tells the agent to
   stop for the owner before a deletion and never to push.
10. The specs, guide, roadmap and Proposed decision records name `safe-git` where they named the old command;
    accepted records other than the one this plan carries out are not edited; and `docs/specs/safe-git.md`
    records the git slice of `port-superpowers`.

## Increments

### Increment A — The safe-git module, added as a copy

**Outcome:** `wb run safe-git commit|remove` work and are tested; `code-work` is untouched.
**Dependencies:** none.
**Affected areas:** `packages/workbench/safe-git/` (new), `packages/workbench/package.json`.

1. Create `module.json`: name `safe-git`, version `0.1.0`, type `module`, provides `["commit"]`, ships
   `["helper/safe-git"]`, `commands.safe-git` with `helper`, `runtime: python`, `kit: 1`, `arguments:
   ["commit", "remove"]`. No `fills` and no `writes`.
2. Create `helper/safe-git`: the module docstring and the shared definitions it needs, then the region from
   "running git" to the end of `command_remove`, then a `main` with its own usage text. The only edits to the
   moved lines: `SETTING` becomes `.workbench/safe-git.json`, strings that say `code-work` say `safe-git`, and
   `main` offers only the two commands. Mode `0755`.
3. Copy `test_codework_git.py`, `test_codework_commit.py`, `test_codework_remove.py` and `support_git.py` as
   `test_safegit_*.py` and `support_git.py`; change what the edits in step 2 require.
4. Add `test_safegit_module.py`: the declaration, the file list, the package order, and the launcher tests
   (first and next commit, unborn-branch refusal, attribution refusal, remove preview and confirm, edited helper
   refused, another argument refused), taken from `test_codework_module.py`.
5. Add `safe-git` to `package.json`.

**Verification:** the new root passes (`PYTHONPATH=.:packages/workbench/safe-git/tests python3 -B -W error -m
unittest discover -s packages/workbench/safe-git/tests`); `code-work`'s tests still pass; `diff` of the moved
region against the original lists only the step 2 edits.
**Evidence:** the diff output and the test counts, in the Result.

### Increment B — Remove git work from code-work

**Outcome:** `code-work` has only the three read commands and requires `commit`.
**Dependencies:** A.
**Affected areas:** `packages/workbench/code-work/` (helper, `module.json`, `files/blocks/policy.md`,
`files/docs/plans/README.md`, tests).

1. Delete lines 676 to the end of `command_remove` from the helper, the `CHANGING` table and the usage text for
   them; update the docstring.
2. In `module.json`: `arguments` becomes `["check", "plans", "report"]`; add `"requires": [..., "commit"]`.
3. Policy block and plans README: the commit goes through the git helper (name no command in the block, which
   names no tool today); the README's "Committing an increment" says `wb run safe-git commit` and the
   setting file `.workbench/safe-git.json`.
4. Delete the three git test files and `support_git.py`; remove the commit and remove tests from
   `test_codework_module.py` and update its declaration, policy and install expectations; the install
   tests select `safe-git` too. Add a test that installing `code-work` without `safe-git` stops on the
   hard requirement.
5. Add a test that the `code-work` helper imports no `subprocess` and names no `git` program.

**Verification:** the `code-work` root and the full suite pass, except the shipped-approval tests that need the
release in D. The commit of this increment mixes deletions with modifications; see Assumptions.
**Evidence:** test counts before and after; the grep showing no git code remains.

### Increment C — The `commit-changes` skill

**Outcome:** an agent given only this skill commits correctly.
**Dependencies:** A.
**Affected areas:** `packages/workbench/safe-git/harness/neutral/skills/commit-changes/SKILL.md`, tests.

1. Write the skill in the style of `draft-plan`: when the owner has asked for a commit; run the verification the
   work names first; read the diff of exactly the paths to commit; name the paths and the full HEAD hash;
   use `--trailer` when the project's process asks for one; describe only the change, with no tool
   attribution unless the project allows it; one commit, never a push; deletion by the `remove` preview first
   and `--confirm` only after the owner approves; stop and report a refusal rather than work around it.
2. Tests: the reader accepts it; front matter is a name and description only; Claude receives it; it names no
   harness or tool beyond the two commands; it contains the rules above; the module's file list now includes it.

**Verification:** the new tests and the module root pass.
**Evidence:** the rendered skill path for the Claude harness in an install test.

### Increment D — Review and release

**Outcome:** the move is reviewed and the approvals match.
**Dependencies:** A, B, C.
**Affected areas:** `workbench/shipped_approvals/packages/`.

1. An independent read-only review (`workflow-reviewer`) of the whole move, given the diff of the moved region
   and the Review focus below. A security pass by `security-reviewer` only if that diff shows anything beyond
   the listed edits or the review finds one; the code itself keeps the pass of increment F of
   `2026-10-22-code-work-commit`.
2. Fix findings with regression tests; record them in the Result.
3. After the owner says "Run it for me": `python3 -m workbench release-approvals`; preview and, after the owner
   says "remove them", delete the stale records with `claude-workflow remove --recursive --confirm`.
4. Run the full suite.

**Verification:** `python3 -B -W error tests/run_all.py` is green; the shipped-approval tests pass.
**Evidence:** the review outcome, the record hashes added and removed, the suite counts.

### Increment E — Specs, guide, roadmap and decisions

**Outcome:** the documents describe the system as it is.
**Dependencies:** D.
**Affected areas:** `docs/specs/safe-git.md` (new), `docs/specs/code-work.md`, `docs/specs/README.md`,
`docs/specs/module-boundary.md`, `docs/specs/trust-and-approval.md`, `docs/development.md`,
`docs/roadmaps/workbench-v1.md`, `docs/decisions/`.

1. `safe-git.md`: purpose, declaration, the Commit section moved from `code-work.md`, the attribution setting,
   limits as built, the superpowers git slice (what was and was not ported and why), acceptance criteria.
   Index it in `docs/specs/README.md`.
2. `code-work.md`: the Commit section points to `safe-git`; the declaration table lists `requires commit` and the
   three read subcommands; correct the stale "implementation has not started" status and add an "As built"
   section listing what exists. Edit the other specs and `development.md` wherever `wb run code-work commit`,
   `remove` or `.workbench/code-work.json` appear (found by search).
3. Roadmap: add this plan's outcome to the Current state; narrow the `port-superpowers` boundary to say the
   git-specific skills were taken here. This is a direction edit and needs the owner's approval of this plan.
4. Decisions: fill the Verification section of `2026-10-22-git-work-in-its-own-module` (the decisions guide asks
   for implementation evidence there); update the Proposed `commit-helper-leaves-baselines-to-the-owner` and
   `plan-check-in-the-shipped-helper` where they name the helper or the setting path. Every other accepted
   record is left unchanged; where one names the old command, the plan leaves it as history.

**Verification:** the document checks (`doccheck`) and the full suite pass; a search finds no live document naming
`wb run code-work commit` or `.workbench/code-work.json`.
**Evidence:** the search output.

## Review focus

- **A pinned command that changed owner.** A project pin recorded for `code-work` must not let `safe-git` run
  unpinned, and an upgrade must ask for the new pin.
- **The setting under its new name.** A file left at the old name must not be read; a link or malformed file at
  the new name must stop the commit as before.
- **The hard requirement.** `code-work` without `safe-git` stops, and so does selecting only `code-work`.
- **No git left behind.** The `code-work` helper starts no program, so its "runs no program" claim is true again.
- **A shipped approval for a changed tree.** Stale records must fail the gate, not pass it.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all five roots.
- The diff-of-region check of completion criterion 6.
- `git diff --check` is clean and `git status` is clean after the last commit.
- A hand run in a scratch project of install, one commit and one removal is **not** part of this plan; it is
  the dogfood step discussed with the owner.

## Risks and sensitive actions

- `release-approvals` rewrites the shipped approvals; it runs only on the owner's exact words, and the stale
  records are deleted only after the owner's "remove them" and a preview.
- The moved helper changes a repository. No behaviour changes, so no new attack surface is expected, but the
  review in D checks that claim and does not assume it.
- Nothing is pushed by this plan.

## Review record

Reviewed by Codex (`gpt-5.6-luna`, effort medium) on 2026-10-22, at the owner's request. Round 1 of a bound of 3;
outcome: converged, with two minor findings, both applied.

- R1-F1 (applied): criterion 10 asked for accepted decision records to name `safe-git` while step 4 left them
  unchanged. Criterion 10 now covers Proposed records and the record this plan carries out, and step 4 says
  every other accepted record stays as history.
- R1-F2 (applied): the `Specs:` line omitted `safe-git`, `trust-and-approval` and the other specs this plan
  creates or edits. It now names them.

Nothing is left for the owner. The review is not an approval; the plan stays `Proposed`.

## Deferred work

- The hand run of install and commit in a real project (the dogfood step).
- `using-git-worktrees` and `finishing-a-development-branch`: not ported; revisit with `code-work-approval`
  (push checkpoint) and `port-superpowers`.
- Rewiring the owner's permission rules and approver from `claude-workflow` to `wb run safe-git`
  (`global-config-migration`).

## Result

### Increment A — done

- `packages/workbench/safe-git/` added: `module.json`, `helper/safe-git`, `tests/` (the git, commit and remove
  tests as `test_safegit_*.py`, `support_git.py`, and a new `test_safegit_module.py` of 16 tests), and the
  package lists it after `groundwork`. `code-work` is untouched.
- A diff of the moved region (lines 676 to 1720 of the original) shows only four edits: `SETTING` and three
  usage or docstring strings that said `code-work`.
- Verification: the new root runs 222 tests, OK; the full suite runs 2860 tests in 5 roots, OK.
- Differences from the plan, all small:
  - The helper is mode 0644, like the other helpers, not 0755.
  - `find_root` is not copied, because the git code never calls it; the copy needs `Refused`, `shown` and `_DIR`.
  - Three tests in other modules listed the package's modules and now include `safe-git`
    (`test_claude_module.py`, `test_codework_module.py`, `test_groundwork_module.py`).
- The shipped-approval tests passed, so the release in increment D is still needed for the real shipped
  records but nothing fails before it.
- Next: increment B.

### Increment B — done

- The `code-work` helper lost the git region and the `CHANGING` table: 1,745 lines became 680. It has the
  three read commands, imports only the standard library, and starts no program. Its docstring and usage text
  no longer mention `commit` or `remove`.
- `module.json`: arguments are `check`, `plans`, `report`; `requires` gains `commit`. The policy block says
  "the git helper"; the plans README says `wb run safe-git commit` and `.workbench/safe-git.json`.
- Tests: deleted `support_git.py`, `test_codework_git.py`, `test_codework_commit.py` and
  `test_codework_remove.py`. Updated the declaration, policy and install expectations (the installs select
  `safe-git` too). Added a test that the helper holds no git code, a test that installing `code-work` without
  `safe-git` stops on the `commit` requirement, and a check that `commit` and `remove` are refused arguments.
- Differences from the plan, both small: the helper's unused imports (`json`, `unicodedata`, `wbkit`) went
  with the git code, so the import test now expects the standard library only; the old "only import of
  subprocess is below the read-only part" test became a test that no git code is present.
- Verification: the full suite runs 2650 tests in 5 roots, OK (2860 before; the difference is the deleted
  copies of the moved tests).
- Next: increment C.

### Increment C — done

- `packages/workbench/safe-git/harness/neutral/skills/commit-changes/SKILL.md` added, written new from the
  owner's commit rules. It names no tool but `wb run safe-git commit` and `wb run safe-git remove`, tells the
  agent to stop for the owner before a deletion (preview, then `--confirm` only after approval), never to
  push, and to stop and report a refusal.
- Tests in `test_safegit_module.py`: a `Skill` class of 6 tests (the reader accepts it, front matter, Claude
  receives it, names no tool and runs only the two commands, states the commit rules, makes the owner approve
  a deletion), one install test showing `.claude/skills/commit-changes/SKILL.md`, and the module's file-list
  test now includes the skill.
- Differences from the plan: the Claude harness rewrites the skill's front matter (it quotes the name), so the
  Claude test compares the body only.
- Verification: the full suite runs 2657 tests in 5 roots, OK (the new root has 229).
- Next: increment D.

### Increment D — done

- Review: a read-only `workflow-reviewer` read the whole move with the diff of the moved region. The diff
  shows only the four listed edits, so no security pass was run. The reviewer found no defect in the moved
  code (names and imports resolve in both helpers, no git left in `code-work`, the setting is read only at
  `.workbench/safe-git.json`, the hard requirement and the declarations hold, the skill matches the helper).
  It ran nothing, so those checks are by reading. Two findings:
  - `docs/development.md` lines 46, 47 and 67 still name `run code-work commit`, `run code-work remove` and
    `.workbench/code-work.json`. Left for increment E, whose step 2 covers that file.
  - No test showed that a `safe-git` pin lets no other command run. Added
    `test_the_pin_of_safe_git_lets_no_other_command_run`. A real upgrade from a project that holds only a
    `code-work` pin is not tested; nothing is installed yet, so none exists.
- Release: on the owner's "Run it for me", `release-approvals` wrote 5 approvals for the one first-party
  package (record directories `26b17c7ce070`, `5399615cb502`, `7d863844209e`, `976d923470fb`,
  `cbcc75d58a13`). On the owner's "remove them", after a preview, the 4 stale records (`45b866c8efb9`,
  `78582b5e6f5d`, `7e2cbd8c1bdd`, `c8d8649a3323`) were deleted.
- With the approvals matching, the shipped-approval test in `test_claude_module.py`, which had been skipped
  while they were stale, ran and still listed three modules. It now lists `safe-git` too.
- Verification: the full suite runs 2658 tests in 5 roots, OK.
- Next: increment E.

### Increment E — done

- `docs/specs/safe-git.md` added (purpose, declaration, the Commit and Remove rules moved from
  `code-work.md`, the attribution setting, how it runs git, the skill, the superpowers git slice with the
  reasons `using-git-worktrees` and `finishing-a-development-branch` were not ported, as built and limits,
  acceptance criteria) and indexed in `docs/specs/README.md`.
- `docs/specs/code-work.md`: the status line no longer says implementation has not started; the declaration
  table lists `requires commit` and the three read subcommands; the Commit section points to `safe-git`;
  acceptance and decided points name the new command; a new "As built, and its limits" section lists what
  exists and what is `code-work-approval`. `module-boundary.md` names `safe-git` among the modules that keep
  specs. `docs/development.md` names `wb run safe-git commit` and `remove`, the section "The safe-git
  helper" and `.workbench/safe-git.json` (the three lines the review flagged).
- Roadmap: a Current-state entry for this plan; a note on `code-work-commit` that the helper moved; the
  `port-superpowers` boundary now says the git slice was taken; the accepted decision is listed.
- Decisions: the Verification of `2026-10-22-git-work-in-its-own-module` is filled with this plan's
  evidence. The Proposed `commit-helper-leaves-baselines-to-the-owner` is refined for the new names and
  stays Proposed. `plan-check-in-the-shipped-helper` names only `check`, which stays in `code-work`, so it
  is unchanged. `trust-and-approval.md` says "the commit helper" without a command, so it is unchanged.
  No other accepted record was edited.
- Search: no live document outside `docs/plans/` and the accepted decision this plan carries out names
  `wb run code-work commit`, `code-work remove`, `the code-work helper` as the commit helper, or
  `.workbench/code-work.json`.
- Not done, not in this plan: the two missing rows in the decisions index, and accepting the Proposed
  records.
- Verification: `doccheck` and `refcheck` print no problems, `git diff --check` is clean, and the full suite
  runs 2658 tests in 5 roots, OK.
- The plan is complete: all five increments are done. Its status stays `Approved` until the owner archives it.
