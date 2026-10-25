# Prepare and test the approver patch for the module spellings (move M1, stage 1, option 1a)

Status: Proposed
Created: 2026-10-25
Candidate: none (this is move M1 stage 1 of the move list in `global-config-inventory`, a follow-on to `workbench-v1#global-config-migration`; whether the roadmap gains a candidate for it is the owner's call and a roadmap edit stops for the owner)
Specs: global-config-inventory

## Goal

Carry out the owner's accepted choice. Two accepted decisions govern. `2026-10-25-approver-coverage-for-the-module-commands`
(a decision record, `Accepted by the owner on 2026-10-25 (option 1a)`) chose its option 1a: a narrow change to the
owner's approver program so that it reviews `wb run safe-git commit`, `wb run safe-git remove`, `wb run remote-runner submit` and
`wb run remote-runner fetch`, with the collectors unchanged. `2026-10-25-module-commands-and-the-approver` (also accepted) chose
that the owner adds global `ask` entries for the four spellings (its Question 1, option 2) and that the module commit is not
delegated (its Question 2, option 1); the patch keeps it undelegated. The agent cannot write the user level, so this plan prepares the patch and its tests on a scratch
copy, has them reviewed, and hands the owner a patch, a self-check and the exact steps. The owner applies it.

When this plan is done: the required behavior is written in the inventory spec; a patch exists, with tests that failed before it
and pass with it, on a scratch copy of the approver at a named hash; an independent review and a security review of the patch
have been run and their findings judged; and the owner holds the patch, a pre-apply self-check, and a list of the other user-level
edits (the global `ask` entries the accepted decision `2026-10-25-module-commands-and-the-approver` chose, and the hook entries per
spelling). Nothing is applied, and no user-level file is written by the agent.

## Scope

- State in the inventory spec what the patched approver must do with each of the four spellings, and what it must still refuse.
- On a scratch copy of the approver (program, configuration, rules, rubric), write tests of that behavior first, see them fail,
  then write the narrow patch and see them pass. The collectors keep calling the global `claude-workflow` program (1a).
- Run the patch against the controls (the existing spellings and rules still match) and against hostile input.
- Request the independent reviews and judge the findings.
- Hand over: the patch, its SHA-256, the self-check, and the owner steps.

## Non-goals

- Writing any user-level file or the owner's global-configuration mirror, applying the patch, or running the approver for real.
- A model call, or running the hook's entry point. The tests call the matching functions and the installed-helper check only,
  with harmless text.
- Option 1b (rewriting the collectors to take facts from the module), delegating the module commit, widening `DELEGABLE`, and
  moves M9, M14 and M16.
- The recorded interactive run that is the gate of M1 stage 1 (a prompt for `wb run safe-git commit`, a logged verdict, and the
  F-B1 test). It needs the patch applied and an interactive session, and is the owner's.
- Editing the roadmap.

## Assumptions and constraints

- The approver program at the hash `94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b` (read and measured in the
  plan `2026-10-25-approver-program-and-the-module-spellings`). If the hash differs when this plan starts, stop and tell the owner.
- What B of that plan measured holds as the baseline: no `wb run` spelling matches; a refused rule file makes the matching
  functions raise for every command that begins with a listed spelling and tokenizes; the collectors call the global
  `claude-workflow` program; `process_outcome` follows the matching.
- A typo in a new rule file silences the review and the commit delegation for every listed spelling. The self-check exists
  to catch that before the patch is applied.
- Which program the spelling `wb` resolves to is checked like plain `git` (it must resolve outside the repository, and there is no
  installed copy to compare with); the plan's first increment fixes this by reading the program and the module specs, and
  stops if the module specs say otherwise.
- The agent writes the user level nowhere (`2026-10-24-project-guarantees-a-floor`). Tracked text names a global file by role and
  SHA-256, never by path. Scratch work lives in the session's scratchpad and is untracked; tracked text cites it by hash.
- Test command text is harmless: no secret, no real host name, no token.
- Discovery: skipped, no discovery tooling is installed; the scope is one program and four spellings, read directly.
- Caps from `wb settings`: three review rounds, one retry of the same failure, six reviewer exchanges. Checkpoints that stop for the
  owner here: approve-plan before any work; the owner applies the patch.
- The owner asked for a `security-reviewer` pass on the patch; it runs in Increment B.

## Completion criteria

1. The inventory spec states the required behavior for the four spellings and what must still be refused, with the evidence of the
   baseline measurements.
2. The tests of that behavior failed against the unpatched scratch copy and pass against the patched one, each result recorded with
   the command, the tool versions, the commit and the conclusion; any test not run is reported as not run.
3. Controls: the existing controls (`claude-workflow commit` and `remove`, `remote-runner submit` and `fetch`, `git push`,
   `ask-codex archive`) match the same rules as before the patch; the rules directory loads; `DELEGABLE` is unchanged.
4. The patch is stored in the plan's Result with its SHA-256, the base hash it applies to and the patched program's hash; the
   self-check and the owner steps are recorded.
5. A `reviewer` pass on each increment and a `security-reviewer` pass on the patch have been run, and every finding is judged.
6. The hashes of the user-level files read are the same at the start and the end of each increment.
7. `doccheck`, `refcheck`, `git diff --check`, `wb run code-work check` and `wb check` pass.

## Increments

### Increment A — The required behavior and the failing tests

**Outcome:** the inventory spec says exactly what the patched approver must match and refuse, and a test script on a scratch copy
fails for the right reason before any patch.
**Dependencies:** none.
**Affected areas:** `docs/specs/global-config-inventory.md` (a short subsection under M1); the scratch directory.
**Steps:**
1. Confirm the approver program's hash is the one named above, and hash the data files read. Stop if it differs.
2. Read `docs/specs/safe-git.md` and `docs/specs/remote-runner.md` for the flags and positional shapes of `commit`, `remove`,
   `submit` and `fetch`, and the approver's four existing rules for the same commands. Write down any difference in flags
   between the module command and the global one; do not assume they are equal.
3. Write the required behavior: for each of the four spellings, the tool name it maps to, the rule it uses, the flags and
   positionals it accepts, and that it stays reviewed only when the global `ask` entries prompt for it. Write what must stay
   refused or unmatched: `wb run safe-git push-check`, `wb run remote-runner cancel` and `prune` (the module wraps neither),
   a flag the module does not have, `wb` alone, a leading space, an environment prefix, and operators after the spelling.
   Say how the installed-helper check treats `wb` (like `git`: it resolves outside the repository), and that
   `DELEGABLE` and the existing spellings are unchanged.
4. Copy the approver into a new, empty scratch directory in the layout the program expects, and hash the copy against the
   originals. Write the tests in a different scratch directory, run with `python3 -I -B`, calling the matching functions and the
   installed-helper check with a fake `wb` on a scratch PATH. Include the controls and the refused-file hazard.
5. Run the tests against the unpatched copy. Read the output; each new-spelling test must fail because no spelling matches, not
   for another reason. Record the controls as passing.
6. Run the checks. Do not write under the user level.
**Verification:** the new-spelling tests fail for the stated reason and the controls pass, with the output read; the originals'
hashes are unchanged; `doccheck`, `refcheck`, `git diff --check` and `wb check` pass.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-approver-patch-for-the-module-spellings#A`.

### Increment B — The patch, its tests and its reviews

**Outcome:** a patch to the scratch copy makes the tests pass, leaves the controls and `DELEGABLE` untouched, and has been reviewed
by the `reviewer` and by the `security-reviewer`.
**Dependencies:** A.
**Affected areas:** the scratch directory; the plan's Result (the patch and its hashes); `docs/specs/global-config-inventory.md`
(the measured results).
**Steps:**
1. Write the smallest patch that makes the tests pass: the spelling lists and the map from spelling to tool, the table of
   installed tools, the supported-tools list, `split_command` for the multi-word prefix, the installed-helper check for the
   `wb` spellings, and the four rule files. Do not touch the collectors, `DELEGABLE` or the existing spellings.
2. Run the tests; read the output. Run the controls and a set of hostile strings (a leading space, a tab, an environment prefix,
   operators, a quoted word, a path-qualified `wb`, `wb run` alone, a flag the module lacks, a very long text) and record
   what matches. A hostile string that matches a module rule when it should not stops the increment.
3. Write the pre-apply self-check: a script that loads the patched rules directory and the five controls and the four new lines,
   and exits non-zero if any fails. It guards the typo hazard.
4. Produce the unified diff against the base hash, and take its SHA-256 and the patched program's. Check that the diff applies
   to a fresh copy of the base and yields the patched hash.
5. Ask the `reviewer` for a pass on the patch, the tests and the spec text, then judge the findings with `evaluate-findings`.
   Ask the `security-reviewer` for an adversarial pass on a copy of the patch (it runs its own probes, writes nothing under the
   user level and never runs the hook's entry point), and judge its findings. A finding that is applied gets a regression test
   that fails before the fix.
6. Write the measured results into the inventory spec (M1) and the patch with its hashes into the Result. Run the checks.
**Verification:** the tests pass and each result was read; the controls match as before; the diff applies to a fresh base copy;
the originals' hashes are unchanged; `doccheck`, `refcheck`, `git diff --check`, `wb run code-work check` and `wb check` pass.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-approver-patch-for-the-module-spellings#B`.

### Increment C — The owner steps

**Outcome:** the owner holds an ordered list of what to do at the user level, and the inventory spec says that the patch is
prepared and not applied.
**Dependencies:** B.
**Affected areas:** the plan's Result; `docs/specs/global-config-inventory.md` (the M1 paragraph, its carrying plan and the
mentions that agree with it).
**Steps:**
1. Write the owner steps in the Result: back up the program and the rules; apply the patch to the program and add the four rule
   files, in the owner's configuration and in its mirror; run the self-check before anything else and stop if it fails; add the
   hook entries per spelling in the settings file (the same events and timeouts as the existing entries); add the four global
   `ask` entries of the accepted decision; start a new session; run the interactive gate of M1 stage 1; keep the backup until
   the gate has passed. Name each file by role and hash, not by path.
2. State what the owner should expect when the patch is wrong (the review and the commit delegation silently stop), and how to
   see it (the log shows no new rows).
3. In the inventory spec, change the M1 paragraph to say the patch is prepared and tested on a scratch copy and not applied,
   and that the recorded interactive run remains the gate.
4. In the inventory spec, replace the carrying plan named for M1 stage 1 (now
   `2026-10-25-approver-program-and-the-module-spellings`) by this plan, and keep the earlier plan named only as the source of the
   measured baseline and of the decision record. Search the spec for any other mention of the carrying plan and make it agree.
5. Run the checks, and ask for a `reviewer` pass on the steps and the spec text.
**Verification:** `doccheck`, `refcheck`, `git diff --check`, `wb run code-work check` and `wb check` pass; the steps contain no path
under the user level and no credential.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-approver-patch-for-the-module-spellings#C`.

## Verification for the plan as a whole

`doccheck` and `refcheck` over the plan and the spec; `git diff --check`; `wb run code-work check`; `wb check`; the hash comparison of
the user-level files read, at the start and the end of each increment; the tests, the controls and the diff-applies check of B,
rerun once at the end of C. Independent review of each increment follows `run-increment`.

## Risks and sensitive actions

- **An authorization control is patched.** The patch is to the approver, which is part of the owner's hard-stop set. This plan only
  prepares it on a copy. The owner applies it, after the self-check.
- **A typo disables the review and the commit delegation** for every listed spelling (measured). The self-check and the backup
  steps answer it.
- **A new spelling that runs a repository-supplied program.** `wb` is resolved by the installed-helper check like `git`; the
  security review probes it with a fake `wb` inside and outside the repository.
- **A false pass.** A test that passes for the wrong reason would look like a result; each test states what it called and why it
  returned, and the new-spelling tests are seen to fail first.
- **Reviewer divergence.** The approver reviews facts that the global `claude-workflow` program computes, which may differ from
  what the module's `safe-git` does with the same arguments. 1a accepts this; the plan records any difference it finds in A.
- **Security review.** The change touches an authorization control, and the owner asked for it: it runs in Increment B.
- **Nothing is pushed or published** by this plan.

## Review record

Round 1 (review engine, bridge `ask-codex`, model `gpt-5.6-terra`, effort medium; the owner asked for it). Verdict: changes
needed, two major findings, both decided as applied. R1-F1 (the governing choice looked ambiguous): the reviewer wrote that the
cited plan did not exist, which misread a decision record that exists and is accepted; the useful part was applied, so the
plan now names both accepted decisions and the option each chose, and says the commit stays undelegated. R1-F2 (the spec's
carrying-plan reference would be left pointing at the earlier plan): applied, as an explicit step in Increment C. One round
used of three. The author did not run a second round; the edits are small. A review is not an approval; the plan stays
`Proposed` until the owner approves it.

## Deferred work

- Applying the patch, the interactive gate run, and the F-B1 test: the owner's.
- Option 1b (the collectors take facts from the module), so that M14 can follow, and the engine redesign (M1 stage 2): their own plans.
- M9, M14, M16 and the other moves: their own plans, after stage 1 is recorded.

## Result

Empty until work starts.
