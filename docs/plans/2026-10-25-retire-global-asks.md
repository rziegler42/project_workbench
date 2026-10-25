# Retire the global install and push prompts (moves M8 and M9)

Status: Proposed
Created: 2026-10-25
Candidate: none (these are moves M8 and M9 of the move list in `global-config-inventory`, a follow-on to `workbench-v1#global-config-migration`; whether the roadmap gains a candidate for them is the owner's call and a roadmap edit stops for the owner)
Specs: global-config-inventory

## Goal

Let the project's own rendered rules supply the prompts that the owner's user-level settings also carry, and record that
they do. Two moves in the move list name this plan as their carrier (`retire-global-asks`):

- **M8:** the thirteen user-level `ask` entries for package installs (`pip install`, `pip3 install`, `python3 -m pip install`,
  `npm install`, `npm ci`, `cargo install`, `cargo add`, `brew install`, `apt install`, `apt-get install`, `uv pip install`,
  `uv add`, `pipx install`). The inventory marks each `move`: the floor renders an `ask` for the same install form.
- **M9:** the one user-level `ask` entry for `git push`. Its blocker, M1 stage 1, is done (plan
  `2026-10-25-approver-patch-for-the-module-spellings`, `Completed`), and the F-B1 test of M1 passed.

When the plan is done, a test pins that the project's floor renders all fourteen forms as `ask`, and the Result holds a
recorded interactive run for each move that shows the prompt appearing with the user-level entries removed. The removals
themselves are the owner's, in a terminal; the agent does not write the user level
(`2026-10-24-project-guarantees-a-floor`).

## Scope

- A test in this repository that pins the claim "the floor renders an `ask` for each of the fourteen forms".
- The written owner steps for removing the entries, from the user-level settings file and from its mirror, and for the
  gate run of each move.
- Recording each gate run in this plan's Result, and updating the M8 and M9 paragraphs and the `move` rows of
  `global-config-inventory` to say what was run.

## Non-goals

- Removing anything. Every removal is the owner's, in a terminal, after the gate for its move is recorded.
- Any `deny` entry, hook, the approver program, its `git-push` rule, its outcome hooks, or any `allow` rule. All stay
  (rule 1 of the order, and the M9 paragraph).
- `Bash(go install:*)`, which the inventory marks `keep global` because the project's install list has no `go install`.
- Changing what the installer or the harness module renders. If the pinning test fails, that is a finding to stop on, not
  a rule change to make inside this plan.
- M1 stage 2, M14, M16 and the other moves.

## Assumptions and constraints

- **Moves M8 and M9 are independent.** The owner may carry out one and not the other; each has its own increment and its own
  gate.
- **A project without the workbench loses these prompts.** The floor covers only attached projects
  (`2026-10-24-project-guarantees-a-floor`; rule 4 of the order). The owner decides in this plan whether that is wanted. By
  approving this plan the owner states that it is; if it is not, the move is dropped from the plan before approval.
- **The prompt, not the entry, reaches the approver.** The approver is a `PermissionRequest` hook with matcher `Bash`
  (inventory, M1 stage 1). It runs whenever a prompt appears, whichever rule caused it. M9's gate checks this and does not
  assume it.
- **The agent only reads the user level.** The owner makes every change there, and to its mirror, and pastes the output.
- **A gate test must be harmless.** The commands used to trigger a prompt are declined at the prompt, so nothing installs
  and nothing is pushed. The push test is run in a throwaway attached project with no remote, or with a remote the owner
  names, and never pushes this repository. No secret, host name or token is written into any tracked file.
- **The mirror is a transitional step, not the roadmap's direction.** The roadmap says the earlier repositories go away
  and there is no mirror to keep in step, but the owner's global instruction to update the mirror and the user level
  together stays in force until that repository is archived (`global-config-inventory`, CS1b and F-C5). So each owner
  removal is made in both for now. When the mirror is archived, the mirror half of each step is dropped, and nothing
  else in this plan changes.
- Tracked text names a global file by its role, never by a path.

## Completion criteria

1. A test in `tests/` fails if any of the thirteen install forms or `git push` stops being rendered as an `ask` by the
   floor, and it passes at the committed head. (Increment A)
2. For M8: a recorded interactive run in an attached project with the thirteen user-level entries removed shows a prompt
   for at least one install form, declined, with nothing installed; the Result gives the command, the tool versions, the
   commit and the conclusion. (Increment B)
3. For M9: a recorded interactive run in an attached project with the user-level `git push` entry removed shows a prompt
   for a push, declined, and one new approver verdict row for it (rule `git-push`); the Result gives the same provenance.
   (Increment C)
4. The M8 and M9 paragraphs and `move` rows of `global-config-inventory` say what was run, and `wb check`, `doccheck`,
   `refcheck` and `wb run code-work check` are clean.
5. No removal was made by the agent, and no file under the user level or its mirror was written by the agent.

## Increments

### Increment A — Pin the floor's coverage of the install and push forms

**Outcome:** a test states, for each of the thirteen install forms and for `git push`, that the floor renders an `ask`
entry that matches it, so the inventory's `move` claim is checked by a test and not only by a read.
**Dependencies:** none.
**Affected areas:** `tests/test_permissions.py` (one test, beside `test_the_install_forms_are_asked_for`). No other file.
**Steps:**
1. Read `workbench/rules.py` (`FLOOR_RULES`, the `install-dependencies` and `publish-or-deploy` groups) and the existing
   tests `test_the_floor_is_rendered_as_ask_rules` and `test_the_install_forms_are_asked_for`.
2. Write the test first. For each of the thirteen user-level install forms and for `git push`, take the form as a command
   line (for example `pip install requests`, `npm ci`, `uv pip install x`, `git push origin main`) and assert that some
   rendered `Bash(...)` `ask` pattern matches it, using the same prefix-and-wildcard reading the rendered patterns have. The
   test names the thirteen forms explicitly, so a removal of any one from the floor fails it.
3. Show that it fails for the right reason by removing one form from a copy of the rule group in the test itself (a
   negative case that asserts the matcher rejects a form with no rule), not by editing `rules.py`.
4. Run the test and the full suite.
**Verification:** `python3 -m unittest discover -s tests -p 'test_permissions.py'`, then the full tests,
`python3 -B -W error tests/run_all.py`, then `git diff --check`, `wb check` and `wb run code-work check`. All pass.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-retire-global-asks#A`. The reviewer pass this
repository's increment loop requires happens before the commit.

### Increment B — M8: write the owner steps, record the install-prompt run

**Outcome:** the owner has exact commands for removing the thirteen entries and for the gate run, and the recorded run is
in this plan's Result and in the inventory.
**Dependencies:** A committed.
**Affected areas:** this plan (Result), `docs/specs/global-config-inventory.md` (the M8 paragraph and the thirteen rows).
**Steps:**
1. Write the owner steps in the Result: a backup of the user-level settings file and of its mirror; a small script, kept in
   the owner's own work folder and not tracked, that removes exactly the thirteen named entries, refuses unless the file
   round-trips as it was written, prints the entries it removed and the count remaining, and leaves `Bash(go install:*)`
   and every other entry; the same script on the mirror; a diff of each file against its backup.
2. Stop. The owner makes the removals and pastes the output. The agent reads the user-level file read-only to confirm the
   thirteen entries are gone and the rest unchanged (a count and a list of removed names, no values beyond the entry text).
3. Give the owner the gate run: in a new session in an attached project, ask the agent to run one harmless install
   command (for example `pip install --dry-run requests`); the owner declines the prompt. Record the prompt text, that nothing ran, and which rule
   caused it if the prompt names one.
4. Record the run in the Result with the command, the Claude Code version, the commit and the conclusion. Update the M8
   paragraph and rows of the inventory to say what was run and that the removal was the owner's.
**Verification:** `git diff --check`, `wb check`, `doccheck` and `refcheck` (the commands of
`docs/development.md`), `wb run code-work check`. The gate run is the owner's and is read from the pasted transcript.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-retire-global-asks#B`. If the owner declines M8, the
increment is dropped by the owner's word and its label is not reused.

### Increment C — M9: record the push-prompt run

**Outcome:** the recorded run shows that, with the user-level `git push` entry removed, a push still prompts in an attached
project and the approver still logs a verdict for it.
**Dependencies:** A committed. B is not required.
**Affected areas:** this plan (Result), `docs/specs/global-config-inventory.md` (the M9 paragraph and its row).
**Steps:**
1. Write the owner steps in the Result: a backup of the user-level settings file and its mirror (reuse B's if still
   current), removal of the one entry `Bash(git push:*)` by the same kind of script, and a diff.
2. Stop for the owner's removal. Read the user level read-only to confirm only that entry is gone.
3. Give the owner the gate run: count the rows of the approver's verdict log before; in a new session in a throwaway
   attached project, ask the agent to push; the owner declines the prompt; count the rows after. Record that exactly one
   new row appeared, its rule (`git-push`), its decision and its verdict, and that nothing was pushed. Rows hold command
   hashes, not command text.
4. Record the run in the Result with provenance and update the M9 paragraph and row of the inventory.
**Verification:** as for B.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-retire-global-asks#C`.

## Verification for the plan as a whole

`python3 -B -W error tests/run_all.py`, `git diff --check`, `wb check`, `doccheck`, `refcheck` and
`wb run code-work check`, then a read-only comparison of the owner's user-level `ask` list against the inventory's rows
showing the fourteen entries are gone and the others, `go install` included, are present.

## Risks and sensitive actions

- **Every removal changes the owner's real configuration** and is the owner's act, after a backup and with a diff. A bad
  edit to the user-level settings file could break the owner's sessions; the removal script refuses unless the file
  round-trips and the diff is read before the next step.
- **A project without the workbench loses the prompts** (Assumptions). Approving this plan records the owner's choice.
- **The push gate must not push.** The owner declines the prompt, and the test runs in a throwaway project. If the prompt
  does not appear, the owner stops and nothing proceeds, because a missing prompt would be a finding about the floor.
- **The approver may not log a verdict for a prompt that a project rule caused.** That is what M9's gate measures. If it
  does not, the entry is restored by the owner and the finding is reported; this plan does not change the approver.
- **Reviewers read files.** None of the text above or of the gate output contains a secret, host name or token.

## Review record

One round of the review engine on 2026-10-25, asked for by the owner (round 1 of a bound of 3). The reviewer's reading was
`changes_needed`, with two findings. Neither is an approval.

- **R1-F1 (major), the mirror requirement against the roadmap's no-mirror direction:** applied. The roadmap and the
  inventory (CS1b, F-C5) agree that the instruction to update both stays in force until the mirror repository is archived,
  so the plan now says the mirror step is transitional and what ends it (Assumptions and constraints).
- **R1-F2 (minor), the whole-suite command:** applied. The plan now uses `python3 -B -W error tests/run_all.py`, the
  full-test command in `docs/development.md`.

The reviewer found nothing else and said the plan matches the gates of M8 and M9 in the inventory. A second round was not
asked for; whether to have one is the owner's call.

## Deferred work

- M14 (the `claude-workflow` removal), M16 (the remote job paragraphs) and the other moves stay unplanned.
- The question of an `ask` for `go install` in the project's install list is the owner's, for a separate change to the
  floor.

## Result

Empty until work starts.
