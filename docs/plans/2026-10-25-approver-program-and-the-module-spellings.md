# The approver program and the module spellings (move M1, stage 1, second attempt)

Status: Proposed
Created: 2026-10-25
Candidate: none (this is move M1 of the move list in `global-config-inventory`, a follow-on to `workbench-v1#global-config-migration`; whether the roadmap gains a candidate for it is the owner's call and a roadmap edit stops for the owner)
Specs: global-config-inventory

## Goal

Find out what it takes to make the owner's approver review the workbench's commands, and put the choice in front of the owner
with measured evidence. Plan `2026-10-25-approver-coverage-for-module-spellings` ended after its Increment A (`Superseded`)
because the approver's spellings are constants in its program, not data: a rule file cannot add `wb run safe-git commit`,
which the plan had assumed. M1 stage 1, and with it the blockers on M9, M14 and M16, stay open.

When this plan is done: the inventory spec says correctly that the approver's spellings, supported tools, installed-helper
check and delegable rules are program code; a read-only experiment on a scratch copy has measured what the approver does with a
module spelling and with a rejected rule file; and a `Proposed` decision sets out the owner's choices with that evidence. No
approver file, setting or helper is changed, and nothing is removed.

## Scope

- Correct the M1, F-A1 and "Rules of the order" text of the inventory spec, which still describes the approver's change as a
  data edit.
- Run a read-only experiment on a scratch copy of the approver program, with a copy of its configuration, rules and rubric, and
  record what it shows.
- Draft a `Proposed` decision on how the approver comes to review the module commands. The owner alone accepts it.

## Non-goals

- Changing the approver program, its configuration, rules, rubric or log, or any other user-level file. The agent does not
  write the user level (`2026-10-24-project-guarantees-a-floor`); the experiment reads it and writes only in the scratch
  directory.
- Running the approver for real, calling a model, or testing a prompt: the experiment calls the matching functions only.
- Stage 2 of M1 (the redesign into `action-review-engine`, which has no plan), M9, M14, M16, and any removal of a global entry.
- Rendering an `ask` for the module commands, delegating the module commit spelling, and the global `ask` entries the accepted
  decision `2026-10-25-module-commands-and-the-approver` describes. They stay as that decision left them; this plan changes none.
- Editing the roadmap.

## Assumptions and constraints

- The approver's program matches a command against a fixed list of spellings in code and accepts a rule only for a tool in a
  fixed list (read 2026-10-25 in the superseded plan's Result). That was read, not run; the experiment tests it.
- The approver program is imported as a module from a scratch copy so that its log and configuration paths, which are relative to
  the file, point into the scratch directory. If importing it would run its main routine, a call to a model or a write outside
  scratch, the experiment stops and is reported; no workaround is tried.
- A tracked document names a global file by role, item name, retrieval date and SHA-256, never by path (`AGENTS.md`).
- Test command text is harmless: no secret, no real host name, no token.
- The owner's `security-review` question: the approver is an authorization control, and the experiment runs code on a copy of it.
  The owner decides whether to run a security review with the `security-reviewer` agent, which runs experiments on a copy; none
  runs unless asked.
- Discovery: skipped, no discovery tooling is installed; the scope is one program and the move list, read directly.
- Caps from `wb settings`: three review rounds, one retry of the same failure, six reviewer exchanges. Checkpoints that stop for
  the owner here: approve-plan before any work, and accept-decision.

## Completion criteria

1. The inventory spec's M1, F-A1 and "Rules of the order" no longer call the approver's change a data edit, and name what is
   code and what is data, with the date and hashes of what was read.
2. The experiment's results are recorded with the command, the tool versions, the commit and the conclusion: whether
   `wb run safe-git commit` and `wb run remote-runner submit` lines match any rule; whether a rule file naming an unsupported
   tool is refused and what that does to the other rules; which constants and functions a patch would have to touch. Any
   experiment not run is reported as not run.
3. A `Proposed` decision sets out the choices (patch the approver program; wait and fold the coverage into
   `action-review-engine`; keep the global helpers and accept that M9, M14 and M16 stay blocked) with their costs, and the owner
   has accepted a choice or deferred it. This plan makes no choice for the owner.
4. The hashes of the global files read in Increments A and B are the same at the start and the end of each of those increments.
5. `doccheck`, `refcheck`, `git diff --check`, `wb run code-work check` and `wb check` pass.

## Increments

### Increment A — Correct the spec

**Outcome:** the inventory spec says what the approver's change really is, so that nothing built or planned later relies on a data
edit.
**Dependencies:** none.
**Affected areas:** `docs/specs/global-config-inventory.md` (the M1 paragraph, F-A1, F-B1 and rule 1 of "Rules of the order");
nothing else. The spec is edited in place.
**Steps:**
1. Read the approver program's spelling lists, tool list, installed-helper check and delegable-rule constant at the user level,
   read only. Take the SHA-256 of the program and of the data files read, and compare them with the spec's inventory.
2. In M1, replace the stage 1 text that has the owner add spellings to the existing rules and rubric with the truth: the
   spellings are constants in the program, a rule for an unsupported tool is refused, and so stage 1 needs a change to the program
   (or its redesign into the engine). Say that the plan `2026-10-25-approver-coverage-for-module-spellings` ended after its
   Increment A for that reason, and that the carrying plan of stage 1 is this one. Keep the F-B2 text and the gate as they are.
3. In F-A1 say that the list of spellings is code. In rule 1 of "Rules of the order" change "its data" to what is true. In F-B1
   leave the claim about prompts untouched.
4. State the one untested claim as untested: that a rejected rule file silences the other rules (Increment B tests it).
5. Run the checks. Do not write under the user level.
**Verification:** `doccheck`, `refcheck`, `git diff --check` and `wb check` pass; a search finds no global path and no credential in
the edited text; the global hashes are the same at the start and the end.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-approver-program-and-the-module-spellings#A`.

### Increment B — The experiment on a scratch copy

**Outcome:** the spec and this plan's Result hold what the approver's matching code does with the module spellings and with a
rejected rule file, as run.
**Dependencies:** A.
**Affected areas:** the scratch directory only; then `docs/specs/global-config-inventory.md` (the measured results in M1 and F-A1).
**Steps:**
1. Copy the approver program, its configuration, rules and rubric into a new, empty directory in the session's scratchpad, in the
   layout the program expects (`hooks/` beside `codex-approver/`). Keep the experiment scripts in a different directory and run
   Python with `-I`. Hash the originals before and after.
2. Before importing, read the program's top level for anything it runs on import; stop and report if it would call a model, write
   outside the copy or run a command.
3. Test, calling the matching functions only: (a) the match of `claude-workflow commit ...`, `wb run safe-git commit ...`,
   `wb run remote-runner submit ...` and `safe-git push-check` lines, harmless text, against the copied rules; (b) a copy of a rule
   file naming the tool `wb` or another unsupported tool, and what loading the rules does, including whether the other rules still
   load; (c) the same with a rule file that is malformed.
4. List the constants, functions and rule keys a patch would have to change for the four module spellings and the outcome hooks,
   by name and line, without making the patch.
5. Record each result with the command, tool versions, the commit and the conclusion. An experiment that did not run is reported
   as not run. Write the measured results into M1 and F-A1 of the spec.
6. Run the checks. Do not write under the user level.
**Verification:** each experiment's output was read, not assumed; the hashes of the originals are unchanged; `doccheck`,
`refcheck`, `git diff --check` and `wb check` pass; the scratch directory holds nothing that was not created for the experiment.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-approver-program-and-the-module-spellings#B`.

### Increment C — Draft the decision

**Outcome:** a `Proposed` decision that sets out how the approver may come to review the module commands, with the evidence of B,
and that stops for the owner.
**Dependencies:** B.
**Affected areas:** a new file `docs/decisions/2026-10-25-approver-coverage-for-the-module-commands.md` (the date is that of the
day it is written) and its row in `docs/decisions/README.md`.
**Steps:**
1. Read the `draft-decision` skill and its template, and the accepted decisions the choice touches
   (`2026-10-22-model-calls-go-through-vendor-bridges`, `2026-10-24-project-guarantees-a-floor`,
   `2026-10-25-module-commands-and-the-approver`).
2. Write the choices: (1) the owner patches the approver program to recognise the module spellings, with B's list of what changes;
   (2) the owner waits and the coverage is built into `action-review-engine`; (3) the owner keeps the global helpers and M9, M14
   and M16 stay blocked, with that loss named. For each say what the approver sees, what a project without the owner's settings
   gets, who makes the change, and what it costs. Say that the global `ask` entries of the accepted decision are needed under (1)
   and (2) in any case.
3. Write it `Proposed`, cite B's measured results and the commit, run the checks, and stop. Report it and wait.
**Verification:** `doccheck`, `refcheck`, `git diff --check` and `wb check` pass; the status line reads `Proposed`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-approver-program-and-the-module-spellings#C`.

## Verification for the plan as a whole

`doccheck` and `refcheck` over the plan, the decision and the spec; `git diff --check`; `wb run code-work check`; `wb check`; the
hash comparison of the global files at the start and end of each increment. Independent review of each increment follows
`run-increment`.

## Risks and sensitive actions

- **A control is examined.** The approver is part of the owner's hard-stop set. This plan only reads it and runs copies of its
  matching code in scratch; it changes nothing.
- **Running a copy of a security program.** Importing the program could run something unintended. Step 2 of B reads its top level
  first, and a surprise stops the increment.
- **A test command leaves the machine.** None should: no model call is made. If one would be, stop.
- **A false pass.** A match function that returns nothing for a reason other than the one under test would look like a result;
  each test states what it called and the reason it returned.
- **Security review.** The change touches an authorization control. Ask the owner whether to run a security review with the
  installed `security-review` skill; none runs unless asked.
- **Nothing is pushed or published** by this plan.

## Review record

Round 1 (review engine, bridge `ask-codex`, model `gpt-5.6-terra`, effort medium; the owner asked for it). Verdict: no
meaningful changes; no findings. The reviewer found the plan coherent with the named spec and the parent roadmap context, its
`Candidate: none` reason valid, and the program-spelling issue treated as an investigation and an owner decision, not a data
edit. One round used of three. Before the round the author narrowed Completion criterion 4 to the increments that read global
files (A and B). A review with no findings is not an approval; the plan stays `Proposed` until the owner approves it.

## Deferred work

- The patch to the approver program, or the redesign into `action-review-engine` (M1 stage 1 and stage 2): the owner's choice
  after the decision of Increment C, in their own plan.
- M9, M14, M16 and the other moves: their own plans, after stage 1 is recorded.
- The remaining findings (F-A2, F-A3, F-A4, F-B3, F-B4) and a roadmap candidate for the moves: the owner's.

## Result

### Increment A (done, not yet committed)

Edited `docs/specs/global-config-inventory.md` in place: rule 1 of "Rules of the order", the M1 paragraph (stage 1, the
superseded plan, the carrying plan, the F-B2 decision accepted on 2026-10-25) and F-A1. F-B1 was left untouched, as step 3 says.
The spellings, supported tools, installed-helper check and delegable rules are stated as program code. "A rejected rule file
silences the other rules" is stated as untested in F-A1 and pointed to from M1.

Provenance: read 2026-10-25 at `045438d`. The approver program's SHA-256 is
`94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b`, equal to the spec's inventory row, and the same at the start
and the end of the increment. Only the program was read in this increment; no data file was read.

Verification as run, after the review fixes and the Result edit: `doccheck`, `refcheck`, `git diff --check`,
`wb run code-work check` (44 plans) and `wb check` exit clean. The edited text holds no global path or credential.

Review: the `reviewer` agent, one exchange of six. No blocking finding. Applied: the full plan stem in the M1 carrying-plan line
(finding 1), and a pointer to F-A1 for the untested claim in M1 (finding 2). Not applied: re-wrapping of two long lines
(finding 3, cosmetic). The reviewer could not read the user level or run the checks. Its recommendation is not a verdict.

Not done: Increments B and C.
