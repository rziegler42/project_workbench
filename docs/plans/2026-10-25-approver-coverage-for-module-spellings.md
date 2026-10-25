# Approver coverage for the module spellings (move M1, stage 1)

Status: Proposed
Created: 2026-10-25
Candidate: none (this is move M1 of the move list in `global-config-inventory`, a follow-on to `workbench-v1#global-config-migration`; whether the roadmap gains a candidate for it, or this plan names that one, is the owner's call and a roadmap edit stops for the owner)
Specs: global-config-inventory

## Goal

Make the owner's approver review the workbench's commands before any global helper it reviews is replaced. Today the approver
matches the raw text of a command against the spellings of the global helpers (`claude-workflow`, `remote-runner`,
`ask-codex archive`) and plain `git push`; a command written `wb run safe-git commit` or `wb run remote-runner submit` matches
no rule (finding F-A1), and the project renders no `ask` for those commands, so the approver's hook may never see them
(F-B1, F-B2). M9, M14 and M16 of the move list cannot start until this is settled and shown to work.

When the plan is done: the owner has decided what happens to the module commands' prompt (F-B2) and whether the module commit
spelling is delegated; the owner's approver data covers the module spellings; a recorded interactive run shows that a
`wb run safe-git commit` is prompted, that the approver logs a verdict for it, and that a project `ask` reaches a global
`PermissionRequest` hook (the F-B1 test); and the inventory spec records the result and the new hashes. No global entry is
removed.

## Scope

- Draft the F-B2 choice, and the question of delegating the module commit spelling, as a `Proposed` decision. The owner alone
  accepts it.
- Write the owner's runbook for the approver's data edits and the tests, in the inventory spec: for each affected rule and
  rubric section, the spelling to add and what must not change.
- After the owner makes the edits and runs the tests in a terminal, record the run and update the inventory spec.

## Non-goals

- Stage 2 of M1 (the redesign into `action-review-engine`, which has no plan), the approver program itself, its
  configuration file, and the `git-push` rule.
- Removing any global `ask`, `allow` or `deny` entry, hook, helper or agent, or changing one the runbook does not name. The
  agent changes no user-level entry at all. Under option 2 of Increment A, the owner adds the global `ask` entries the
  runbook names; that is an addition by the owner, never a removal. M9, M14 and M16 are their own plans.
- Rendering an `ask` for the module commands, if the owner chooses that: it changes the `safe-git` and `remote-runner`
  modules and is a separate plan (see the stop under Increment A).
- Editing the user level. The agent does not write it (`2026-10-24-project-guarantees-a-floor`); every edit there is the
  owner's, in a terminal.
- The `cancel` and `prune` rules: the module wraps neither, and its `fetch-overwrite` and the review-engine `archive` are
  owner-run and denied, so they raise no prompt for the approver to review (inventory, M1).

## Assumptions and constraints

- The approver's hook sees only a prompt that an `ask` rule raised (inventory, F-B1). Covering a spelling in the approver
  helps only where something prompts for it; that is why F-B2 comes first.
- Reading the approver's rules, rubric and log at the user level is allowed; the inventory did so. A tracked document names a
  global file by role, item name, retrieval date and SHA-256 and never by path
  (`AGENTS.md`: nothing tracked points to untracked content).
- The approver sends a command's text to a model to be judged, so a test command goes out of the machine. Use only commands
  whose text is harmless: no secret, no real host name, no token.
- A recorded run needs the interactive session the owner runs; a `-p` run denies an `ask` and so cannot show the F-B1 result
  (inventory, F-B1).
- Discovery: skipped, no discovery tooling is installed; the scope is the approver's data and the move list, read directly.
- Caps from `wb settings`: three review rounds, one retry of the same failure, six reviewer exchanges. Checkpoints that stop
  for the owner here: accept-decision, and approve-plan before any work.
- Delegation lets the approver allow a command by itself (it delegates `claude-workflow-commit` and `ask-codex-archive`
  today). Extending that to a new spelling is a widening of what runs unprompted, so it is the owner's choice and nothing in
  this plan assumes it.

## Completion criteria

1. A `Proposed` decision record sets out the options for F-B2 and for delegating the module commit spelling, and the owner
   has accepted a choice. The plan is complete as written only if that choice is option 2; under option 1 or 3 it ends
   after Increment A, is closed by the owner (`Superseded`, or `Completed` for A alone as the owner decides), and criteria
   2 to 4 do not apply.
2. The inventory spec holds a runbook that names, for each of the rules `claude-workflow-commit`, `claude-workflow-remove`,
   `remote-runner-submit` and `remote-runner-fetch` and for the rubric, the spelling added and the content left unchanged.
3. A recorded run, written into the spec and this plan's Result with the command, the tool versions, the commit and the
   conclusion, shows: a `wb run safe-git commit` raises a prompt; the approver logs a verdict for it; the same for
   `wb run safe-git remove`, `wb run remote-runner submit` and `fetch`, each prompted by the owner's added global `ask` entries; and a project
   `ask` reaches the global `PermissionRequest` hook (the F-B1 test).
4. The spec records the new hashes of the changed approver items and the unchanged hashes of everything else the plan was
   told not to touch, taken before and after; the agent wrote nothing at the user level.
5. `doccheck`, `refcheck`, `git diff --check` and `wb check` pass.

## Increments

### Increment A — Draft the F-B2 decision

**Outcome:** a `Proposed` decision record, `docs/decisions/2026-10-25-module-commands-and-the-approver.md`, that states the
choices and their cost and stops for the owner. Nothing is accepted by the agent.
**Dependencies:** none.
**Affected areas:** the new decision file; the inventory spec's M1 paragraph and F-B2. The spec now offers two alternatives
for F-B2 (the workbench renders an `ask`, or the owner accepts the loss). Option 2 below, the owner's own global `ask`
entries, is a third that this plan adds, so A edits both places to list it as a proposed alternative, say it came from this
plan, and cite the record as `Proposed`. The spec is edited in place; the owner's approval of this plan covers that edit.
**Steps:**
1. Read the `draft-decision` skill and its template, the accepted decisions the choice touches
   (`2026-10-19-restrictive-only-permissions`, `2026-10-22-model-calls-go-through-vendor-bridges`,
   `2026-10-24-project-guarantees-a-floor`), `safe-git.md` and `remote-runner.md`.
2. Write the options for the module commands' prompt: (1) the workbench renders an `ask` for `wb run safe-git commit` and
   `remove` and for the module's `remote-runner submit` and `fetch` (a change to those modules, permitted by restrictive-only
   permissions, which allow `ask`); (2) the owner adds global `ask` entries for the module spellings (an owner step at the user
   level, nothing in the project); (3) the owner accepts that the module commands prompt only by the owner's `allow` rules
   and `auto` mode, and so that the approver may not see them. For each, say what the approver sees, what a project without
   the owner's global settings gets, and what it costs.
3. Edit F-B2 and the M1 paragraph in the inventory spec so they list option 2 beside the two they name, as a proposal that
   neither the spec nor the plan prefers.
4. State the second question: whether the module commit spelling is delegated as `claude-workflow-commit` is, with the
   reason either way (a commit that is not delegated prompts the owner every time).
5. Write it `Proposed`, run the checks, and stop. Report it to the owner and wait.
**Stop:** only option 2 lets B and C proceed, because only there does a prompt for the module commands exist for the approver
to review. If the owner accepts option 1, this plan stops after A: the `ask` is rendered by a change to the `safe-git` and
`remote-runner` modules, which is a new plan, and B and C are replaced by a fresh plan after it. If the owner accepts option 3,
this plan stops after A: the approver will not review the module commands, so M1 stage 1 cannot be met; M9, M14 and M16 stay
blocked until the owner decides again, and the Result records that. In both cases the Result records which option was
accepted and that B and C were not done.
**Verification:** `doccheck`, `refcheck`, `git diff --check` and `wb check` exit clean; the decision's status line reads
`Proposed`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-approver-coverage-for-module-spellings#A`.

### Increment B — The owner's runbook

**Outcome:** the inventory spec holds a runbook the owner can follow in a terminal and a list of tests, so that no edit is
made on a guess.
**Dependencies:** A, and the owner's acceptance of the decision with option 2.
**Affected areas:** `docs/specs/global-config-inventory.md` (a new subsection under M1; no global path in it).
**Steps:**
1. Read the approver's rules, rubric and verdict schema, and the part of the program that matches a command, at the user
   level, read only. Record in the runbook which spellings each rule matches and how (whole text, a prefix, a pattern), so
   the added spelling is written the same way. If the program shows a way to see a match without a model call, say so; do not
   assume one.
2. For each of the four rules and the rubric sections, write the spelling to add (`wb run safe-git commit`,
   `wb run safe-git remove`, `wb run remote-runner submit`, `wb run remote-runner fetch`) and the lines that must not change.
   Write what to do about delegation as the accepted decision says; if it does not say, leave the module commit spelling
   undelegated.
3. List the tests the owner runs: each module command that should prompt; the commands that must not match (`wb run safe-git
   push-check`, a compound line, a command that merely contains the text); and the F-B1 test with the exact steps in an
   interactive session. Give each a command whose text is harmless, the verdict expected, and the log line to read.
4. Name the files that must have the same hash before and after, and the ones that change, by role and item name, and record
   the current hashes taken at the start of this increment.
5. Run the checks. Do not write under the user level.
**Verification:** `doccheck`, `refcheck`, `git diff --check` and `wb check` pass; a search finds no global path and no
credential in the runbook; the hashes of the global files read are the same at the start and the end of the increment.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-approver-coverage-for-module-spellings#B`.

### Increment C — Record the edits and the run

**Outcome:** the spec and this plan's Result record the gate for stage 1 as a run, with its provenance.
**Dependencies:** B, and the owner has made the edits and run the tests of the runbook in a terminal and said so.
**Affected areas:** `docs/specs/global-config-inventory.md` (the M1 and F-A1, F-B1, F-B2 text, and the hashes of the changed
approver items); this plan's Result.
**Steps:**
1. Read the approver's log for the owner's test commands (read only). Record the command text, the verdict and the time; leave
   out anything else in the log.
2. Take the hashes of the global files again. Check that only the items the runbook names changed and record the new hashes.
3. Write the result of each test as run, including a test that failed or did not prompt, with the tool versions and the
   commit. A test that did not run is reported as not run.
4. Update M1 to say stage 1 is done and what it showed, update F-A1, F-B1 and F-B2 with the measured result, and note the
   blocker is cleared for M9, M14 and M16 only if the tests passed.
5. If a test failed, stop and report: do not edit the approver, and do not widen the plan.
**Verification:** `doccheck`, `refcheck`, `git diff --check` and `wb check` pass; the recorded hashes match the files; the
agent's own action wrote nothing at the user level (hashes of the files other than the owner's edits are unchanged).
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-approver-coverage-for-module-spellings#C`.

## Verification for the plan as a whole

`doccheck` and `refcheck` over the plan, the decision and the spec; `git diff --check`; `wb check`; the hash comparison of
Increment C; and the recorded interactive run of criterion 3. Independent review of each increment follows `run-increment`.

## Risks and sensitive actions

- **A control is changed.** The approver is part of the owner's hard-stop set. Stage 1 only adds coverage; it removes no
  rule, no spelling and no hook. The owner makes the edits and keeps the old file to put back.
- **Delegation widens what runs unprompted.** Left undelegated by default; the owner decides in A.
- **A test command leaves the machine.** The approver sends the command text to a model. Use only harmless text.
- **A false pass.** A prompt that the owner's `allow` rules or `auto` mode suppresses would hide a gap. Each test states the
  settings it ran under, and the F-B1 test is interactive.
- **A rule that matches too much.** A spelling written as a prefix could match `safe-git push-check` or a compound line; the
  tests of B include those.
- **Security review.** The change touches an authorization control. Ask the owner whether to run a security review with the
  installed `security-review` module; none runs unless asked.
- **Nothing is pushed or published** by this plan.

## Review record

Round 1 (review engine, bridge `ask-codex`, model `gpt-5.6-terra`, effort medium; the owner asked for it). Verdict: changes
needed; two major findings, both applied.

- R1-F1 (applied): the non-goals forbade changing any global `ask` entry while option 2 has the owner add some. They now say
  the agent changes no user-level entry and the owner may add the named entries; removals stay out.
- R1-F2 (applied): option 3 cannot meet the stage-1 gate. Only option 2 now proceeds to B and C; options 1 and 3 end the plan
  after A, and the completion criteria say so.

Round 2 (same settings; the owner asked for it). Verdict: changes needed; one major finding, applied.

- R2-F1 (applied): option 2 (the owner's global `ask` entries) is not an F-B2 alternative in the spec, which names only
  rendering an `ask` or accepting the loss. Increment A now edits F-B2 and M1 to list it as a proposed third alternative,
  said to come from this plan.

Round 3 (same settings; the owner asked for it). Verdict: no meaningful changes; no findings. The reviewer found the third
F-B2 alternative scoped to Increment A's spec update and the option-dependent stops aligned with the inventory's M1 gate. All
three rounds are used. A review with no findings is not an approval; the plan stays `Proposed` until the owner approves it.

## Deferred work

- Stage 2: the redesign of the rules and rubric into `action-review-engine`, when it exists.
- The stale pointers and missing outcome hooks (F-A2, F-A3, F-B4): stage 2.
- M9, M14, M16 and the other moves: their own plans, after stage 1 is recorded.
- A roadmap candidate for the moves, and any decision about F-B3 and F-B5: the owner's.

## Result

Empty until work starts.
