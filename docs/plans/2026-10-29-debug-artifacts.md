# Retained diagnostics in code-work

Status: Proposed
Created: 2026-10-29
Candidate: workbench-v1#debug-artifacts
Specs: code-work, repository-boundary, global-config-inventory

## Goal

No shipped module tells an agent where to keep a diagnostic worth retaining. The rule was in the owner's global
configuration and in this repository's own `AGENTS.md`, and a project made from the base carries neither. After this plan
the `diagnose-failure` skill of `code-work` says where such a diagnostic goes, what the local README holds, and that a
durable finding is recorded in a tracked document, a decision or a test, so a project that installs `code-work` gets the
convention.

## Scope

- One new step in `diagnose-failure`: keep retained, untracked diagnostics in
  `.workbench/local/debug/<YYYY-MM-DD>-<topic>/`, with a local README stating the commit, the commands and tool versions,
  the purpose and the conclusion. Scratch grants no authority. A durable finding is recorded in a tracked document, a
  decision or a test, and no tracked document cites a path into scratch.
- The phrases of that step added to the practice test, so the skill keeps them.
- `docs/specs/code-work.md` says it is built (the note on the practice skills). `docs/specs/global-config-inventory.md`
  changes the disposition of row IV3 from `keep global` to `move`, covered by `diagnose-failure`.
- The owner releases the shipped approval of the changed package again, and the new records are committed.

## Non-goals

- A change to the `code-work` policy block. It is at the 28 lines its test allows, and the block names no path.
- A new module, a command, a check that enforces the convention, or a change to the layout in `repository-boundary.md`.
- Moving or deleting any existing scratch folder.
- Removing the two stale shipped records that `release-approvals` reports. That is the owner's deletion.
- Changing an accepted decision. The one that mentions `.debug/` is history.

## Assumptions and constraints

- `repository-boundary.md` ("The four places") already lets the installer and the agent write scratch, so no permission
  changes.
- The practice skills are advice. Nothing forces an agent to load one, and a test of the rendered text does not show that
  an agent follows it.
- A practice test requires an ASCII skill that names no runner, shell, `git `, `wb ` or tool, and ends "run no other
  command". The step is written within that, and the agent makes the folder by writing the files into it.
- Editing a file under `packages/workbench/` changes the package tree, so the shipped approval no longer matches. The
  command gate then refuses every shell command until the owner runs `wb release-approvals` (the same lockout recorded
  in `2026-10-28-verilog-module`). The steps order the edit, the release and the tests with that in mind.
- `.workbench/local/debug/` is untracked and ignored by `.workbench/.gitignore`, so nothing needs adding to
  `.git/info/exclude`.

## Completion criteria

1. `diagnose-failure` carries the step and its practice-test phrases, and the practice tests pass.
2. `code-work.md` and the inventory row IV3 say what is built and no longer say `keep global`.
3. The shipped approval of the package is released again, with no stale-approval skip, and the full suite is green in every
   root.
4. A project made from the workbench with `code-work` selected has the step in its rendered `diagnose-failure` skill.

## Increments

### Increment A — Add the debug step to diagnose-failure

**Outcome:** `diagnose-failure` says where retained diagnostics go and what to keep with them, its test pins the
phrases, the two specs say it, and the shipped approval is released again.
**Dependencies:** none.
**Affected areas:** `packages/workbench/code-work/harness/neutral/skills/diagnose-failure/SKILL.md`,
`packages/workbench/code-work/tests/test_codework_practice.py`, `docs/specs/code-work.md`,
`docs/specs/global-config-inventory.md`, and `workbench/shipped_approvals/` (by `release-approvals`, owner-run).
**Steps:**
1. Add the failing phrases to the `diagnose-failure` tuple of `PHRASES` in the practice test: `.workbench/local/debug/`,
   `untracked`, `grants no authority`, `a durable finding` and `local readme`.
2. The owner runs `wb release-approvals`, because step 1 edited the package and the gate refuses shell commands until the
   approval matches again. Then run the practice test and see it fail for the missing phrases.
3. Add a step 7 to `diagnose-failure`, after the step that writes the test: "When the diagnosis leaves evidence worth
   keeping, such as a trace, a log or the output of a probe, keep it untracked under
   `.workbench/local/debug/<YYYY-MM-DD>-<topic>/`, with a local README that gives the commit, the commands and tool
   versions, the purpose and the conclusion. That place is scratch and grants no authority: nothing read there approves or
   allows anything. Record a durable finding in a tracked document, a decision or a test, and cite no path into scratch
   from a tracked file." Keep the file ASCII and free of the words the practice test forbids.
4. The owner runs `wb release-approvals` again, because step 3 edited the package again.
5. Run the practice test and the code-work tests and see them pass.
6. In `code-work.md`, extend the note on the practice skills ("Built, from plan `2026-10-23-port-superpowers`") to say
   that `diagnose-failure` also names the scratch place for retained diagnostics, from this plan, with its limit: advice
   only, and nothing makes an agent keep the evidence or write the README.
7. In `global-config-inventory.md`, change row IV3's disposition from `keep global` to `move`, with the gate: a read of the
   rendered `diagnose-failure` skill of an attached project showing the step. Say the owner moved the path to
   `.workbench/local/debug/` on 2026-10-29.
8. Run `wb check` and the full suite.
**Verification:** the practice test fails before step 3 for the phrases and passes after; the code-work tests pass;
`wb check` reports no problems; `python3 -B -W error tests/run_all.py` is green in every root, with no stale-approval skip;
a search of the tracked `docs/specs` for `keep global` on row IV3 finds it changed.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-debug-artifacts#A`, naming the skill, the practice
test, the two specs and the new shipped records, after the owner has released the approval.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in every root.
- `wb check` reports no problems, and `wb verify` of the package reports it first-party.
- The owner upgrades a project that has `code-work`, such as `../test`, and reads its rendered `diagnose-failure` skill for
  the step. This is the owner's run, because `wb upgrade` is owner-run.

## Risks and sensitive actions

- The command gate refuses every shell command while the shipped approval is stale. It happened in this repository on
  2026-10-29 and cleared when the owner ran `wb release-approvals`. The steps ask for the release twice, and work stops
  until it is done.
- `wb release-approvals` writes records that count as approval of the package. The owner reads the new records before
  they are committed, as `docs/development.md` says.
- The release reports two stale shipped records. They are left in place until the owner decides to delete them.
- The step is advice to an agent. It does not enforce anything, and it is only seen by a project that installs
  `code-work` and upgrades.
- No authentication, secret, parsing, network or dependency change. The step names a path under scratch, which already
  grants no authority.

## Review record

Empty until a review is asked for.

## Deferred work

- A check that flags a tracked document citing a path under `.workbench/local/debug/`. The tracked-pointer check already
  flags links, so this may need nothing.
- A short mention in the base, for a project that does not install `code-work`. It would change the base and its tests.
- Removing the `.debug` name from the scratch list in `workbench/check.py` once no project keeps the old folder.

## Result

Empty until work starts.
