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

Committed as `a31c426`.

### Increment B (done, not yet committed)

Ran at commit `a31c426`, 2026-10-25, Python 3.15.0, Darwin 25.6.0. The approver program, its configuration, rubric, schema and
eight rule files were copied into a new scratch directory in the layout the program expects (no log); the copy hashed
identical to the originals. The experiment script lives in a separate scratch directory and ran with `python3 -I -B`. The
program's top level was read first: stdlib imports, constants and definitions, with `main()` behind an `__main__` guard, so
importing it runs nothing. The script asserted that the program's home directory was inside the scratch copy. Only `split_command`,
`tokenize`, `load_rules` and `match_event` were called; no model call, no `process`, `evaluate` or `main`.

Results (run, output read):
- Controls: `claude-workflow commit`, `claude-workflow remove`, `remote-runner submit`, `remote-runner fetch` and `git push` lines
  each matched their rule. This shows the harness can match.
- `wb run safe-git commit`, `wb run safe-git remove`, `wb run remote-runner submit`, `wb run remote-runner fetch` and
  `wb run safe-git push-check` matched nothing. Reason, from the printed intermediate values: `split_command` returned `None`
  (no listed spelling is a prefix of the text), so no rule was read.
- Rule directories with one extra file: tool `wb`, `safe-git` and `wb run safe-git` each raised "rule tool is not supported";
  malformed JSON, a missing `tool` key and an unknown collector each raised their own `ConfigError`. In all six, `load_rules`
  raised for the whole directory and each of the five control lines then raised the same error instead of matching (this is the
  behaviour of `load_rules` and `match_event`; that the real hook calls them on every covered event is by reading). A valid
  extra rule (control) loaded, nine rules, and all five controls matched. A first run of that control failed because of my own
  input (a subcommand with a digit); it was corrected and rerun.
- By reading only: `main()` wraps `process()` in a handler that swallows any exception, so, by reading, no verdict is recorded and
  no decision is made, and the normal prompt is expected. Not run, because it would reach a model.
- Patch list, by reading: spelling lists and the spelling-to-tool map (lines 43 to 59), `SUPPORTED_TOOLS` (60),
  `INSTALLED_TOOLS` (38 to 39), `split_command` (100; it must consume a multi-word prefix such as `wb run safe-git` and map it to a
  tool), `resolve_invocation` (from 449; it reads a spelling's last word as a path under the home directory), the collectors that call
  the global `claude-workflow` program as a library (`load_helper` 387, `collect_commit` 867, `collect_remove` 947), new rule files,
  and per-spelling hook entries in the settings file. The outcome hooks follow the matching, because `process_outcome` (2225) calls
`match_event`; this was read, not run. `DELEGABLE` (77) stays if commit is not delegated. Finding: the approver's
  review of a commit or removal depends on the global `claude-workflow` program, so M14 would break it even with spellings added.

Verification as run: the originals' hashes (program, configuration, rubric, schema, eight rules) were identical before and after
(`diff` of the two lists, clean); the program's hash is `94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b`,
the same as in Increment A, so the line numbers below are those of that file. The scratch copy holds only copied files (no
bytecode). Spec edits are in M1 and F-A1. `doccheck`, `refcheck`, `git diff --check`, `wb run code-work check` (44 plans) and
`wb check` exit clean. The script is untracked scratch; its inputs were the five control lines above, the five module lines
above, and six one-file variants of the rules directory (three unsupported tool names, malformed JSON, a missing key, an unknown
collector) plus the valid-extra-rule control.

Reviews of B: the `reviewer` agent (one exchange): no blocking finding; applied the checks line, `process_outcome` in the patch
list, the run/read split in M1 and the swallow wording, the program hash, and a description of the inputs. Not applied: the
re-wrapping of long lines (cosmetic). The `security-reviewer` agent (the owner asked for it): no Critical or High finding; it
reproduced the match results with 15 variants of its own. Medium, applied: the refused-file effect reaches every command that
begins with a listed spelling and tokenizes, covered or not (`git status` included), and a bad or missing `config.json` or rules
directory has the same effect; the owner's mode is `delegate`, so such an error removes the commit and archive auto-allow and
the log, and falls back to a prompt. My Result had measured only the five controls. Low, applied: the patch list gained
`INSTALLED_TOOLS` and `split_command`. Low, noted: the experiment script's check that the program's home is inside the scratch
copy is a tautology, since the home derives from the argument; the safety came from passing the scratch path, not from the check.
Also found by that review and read only: a leading space, an environment prefix, `;`, `&&`, `|` or a redirect after the
spelling make a line unreviewed, and `git -C x push`, `--force-with-lease` and similar forms tokenize but match no rule; these are
properties of the existing approver, recorded for the owner's decision and not a request to patch it.

Not done: Increment C and the commit.
