# Retire the global install and push prompts (moves M8 and M9)

Status: Completed
Created: 2026-10-25
Candidate: none (these are moves M8 and M9 of the move list in `global-config-inventory`, a follow-on to `workbench-v1#global-config-migration`; whether the roadmap gains a candidate for them is the owner's call and a roadmap edit stops for the owner)
Specs: global-config-inventory

## Goal

Let the project's own rendered rules supply the prompts that the owner's user-level settings also carry, and record tha
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
- Changing what the installer or the harness module renders. If the pinning test fails, that is a finding to stop on, no
  a rule change to make inside this plan.
- M1 stage 2, M14, M16 and the other moves.

## Assumptions and constraints

- **Moves M8 and M9 are independent.** The owner may carry out one and not the other; each has its own increment and its own
  gate.
- **A project without the workbench loses these prompts.** The floor covers only attached projects
  (`2026-10-24-project-guarantees-a-floor`; rule 4 of the order). The owner decides in this plan whether that is wanted. By
  approving this plan the owner states that it is; if it is not, the move is dropped from the plan before approval.
- **The prompt, not the entry, reaches the approver.** The approver is a `PermissionRequest` hook with matcher `Bash`
  (inventory, M1 stage 1). It runs whenever a prompt appears, whichever rule caused it. M9's gate checks this and does no
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
2. For M8: a recorded interactive run in an attached project with the thirteen user-level entries removed shows a promp
   for at least one install form, declined, with nothing installed; the Result gives the command, the tool versions, the
   commit and the conclusion. (Increment B)
3. For M9: a recorded interactive run in an attached project with the user-level `git push` entry removed shows a promp
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
- **The push gate must not push.** The owner declines the prompt, and the test runs in a throwaway project. If the promp
  does not appear, the owner stops and nothing proceeds, because a missing prompt would be a finding about the floor.
- **The approver may not log a verdict for a prompt that a project rule caused.** That is what M9's gate measures. If i
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

The reviewer found nothing else and said the plan matches the gates of M8 and M9 in the inventory. A second round was no
asked for; whether to have one is the owner's call.

## Deferred work

- M14 (the `claude-workflow` removal), M16 (the remote job paragraphs) and the other moves stay unplanned.
- The question of an `ask` for `go install` in the project's install list is the owner's, for a separate change to the
  floor.

## Result

### Increment A (done, reviewed, committed as `a333708`)

Run 2026-10-25 at commit `68a09a1`, Python 3.15.0, Darwin 25.6.0. The plan's approval was recorded by the owner (`wb plan-status`
printed `approved`). One path changed: `tests/test_permissions.py`. One test was added to class `Floor`, after
`test_the_floor_is_rendered_as_ask_rules`: `test_the_floor_asks_for_the_install_and_push_forms_the_user_level_also_asks_for`.
The plan said "beside `test_the_install_forms_are_asked_for`", which sits in class `Hostile`; `Floor` is the better home and the
deviation is only of place. `workbench/rules.py` is untouched.

- **What the test does:** it renders the floor with `lists()` and asserts that some rendered `Bash(...)` ask pattern matches each of
  fifteen command lines: the thirteen install forms of M8 (`pip`, `pip3`, `python3 -m pip`, `npm install`, `npm ci`,
  `cargo install`, `cargo add`, `brew install`, `apt install`, `apt-get install`, `uv pip install`, `uv add`, `pipx install`),
  `git push` and `git push origin main`. The matcher is `fnmatch.fnmatchcase` over the pattern with `[` and `?` escaped, so
  `*` is the only wildcard. It also asserts that a command with no rule is not matched (`pip uninstall`, `npm run build`,
  `uv run pytest`, `git pull`, and `go install`, which the plan leaves global), and that `npm ci` is not matched by a lis
  holding only `npm install*`.
- **Fails first, shown without editing `rules.py`:** a scratch script (not tracked) removed one floor entry in memory and ran
  the test. Without `uv add*` it failed at `uv add requests`; without `git push` it failed at `git push`; a removal of an entry
  that does not exist passed. The first draft of the matcher wrongly failed bare `git push` (a pattern with no `*` must match
  exactly); that was the test's own bug and was fixed before the runs above.
- **Verification as run:** `python3 -B -m unittest discover -s tests -p 'test_permissions.py'`, 29 tests OK;
  `python3 -B -W error tests/run_all.py`, 4225 tests in 10 roots, OK (run before and after the review fixes);
  `git diff --check`, `wb check` and `wb run code-work check` (46 plans), clean.
- **Review:** the `reviewer` agent, one exchange (of a cap of 6), no blocking finding. Finding 1 (the "not vacuous" loop was true
  by construction, and so did not meet step 3): applied; the loop is replaced by fixed strings that must not match. Finding 2
  (the matcher checked only the first and last pieces of a pattern): applied; `fnmatch` replaces it. Findings 3 (all thirteen
  forms covered) and 5 (scope) raised nothing. Finding 4 (the test is in `Floor`, not beside the Hostile test): recorded above.
  The review is not an approval.
- **Not run, and limits:** the test pins the repository's rendering of the floor. It does not show how Claude Code matches a
  pattern in a live session, which is what the gates of Increments B and C measure. The reviewer could run nothing and read
  only. The fixes after the review were checked by rerunning the test, the scratch removals and the full suite, not by a second
  review.
- **Next:** Increments B and C stop for the owner's removals.

### Increment B (done, reviewed, committed as `f4b3816`)

Started 2026-10-25 at commit `a333708`. The plan's approval is the owner's record (`wb plan-status` printed `approved`).
At the start nothing was removed and no gate had run; the owner then made the removals and the gate run, recorded below. The agent read the user-level settings file once, read-only, and found it holds all
thirteen M8 entries in `permissions.ask` (88 entries in all), each in the form `Bash(<form>:*)`, and `Bash(go install:*)`
beside them.

**Owner steps.** Every step is the owner's, in a terminal. Tracked text names no path to the user level, so `USER` below is
the user-level settings file and `MIRROR` is its copy in the mirror repository; the owner supplies both paths. The mirror half
ends when that repository is archived (Assumptions and constraints).

1. Back up both files, each next to itself, and keep the backups out of any repository: copy `USER` to `USER.bak-m8` and
   `MIRROR` to `MIRROR.bak-m8`.
2. Save the script below as `remove_m8.py` in your own work folder, which this repository does not track. It removes exactly
   the thirteen entries, refuses unless the file reads back byte for byte as the JSON it parses to, and does nothing unless
   given `--apply`.

   ```python
   import json, os, sys, tempfile

   FORMS = ("pip install", "pip3 install", "python3 -m pip install", "npm install", "npm ci", "cargo install",
            "cargo add", "brew install", "apt install", "apt-get install", "uv pip install", "uv add", "pipx install")
   ENTRIES = ["Bash(%s:*)" % form for form in FORMS]
   KEPT = "Bash(go install:*)"

   path = sys.argv[1]
   apply = "--apply" in sys.argv[2:]
   with open(path, encoding="utf-8") as handle:
       text = handle.read()
   data = json.loads(text)
   for indent in (2, 4, 1, 3, 8):
       for tail in ("\n", ""):
           if json.dumps(data, indent=indent, ensure_ascii=False) + tail == text:
               break
       else:
           continue
       break
   else:
       sys.exit("refused: the file does not round-trip, so a rewrite would change more than the entries")
   ask = data["permissions"]["ask"]
   removed = [entry for entry in ask if entry in ENTRIES]
   print("removed (%d):" % len(removed))
   for entry in removed:
       print("  " + entry)
   print("not present:", [entry for entry in ENTRIES if entry not in ask] or "none")
   data["permissions"]["ask"] = [entry for entry in ask if entry not in ENTRIES]
   print("ask entries remaining: %d (was %d); go install kept: %s"
         % (len(data["permissions"]["ask"]), len(ask), KEPT in data["permissions"]["ask"]))
   if not apply:
       sys.exit("dry run: nothing written; rerun with --apply")
   out = json.dumps(data, indent=indent, ensure_ascii=False) + tail
   descriptor, name = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)))
   with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
       handle.write(out)
   os.chmod(name, os.stat(path).st_mode & 0o7777)
   os.replace(name, path)
   print("written")
   ```
3. Dry run on `USER`: `python3 -I -B remove_m8.py USER`. Read the list. Then `python3 -I -B remove_m8.py USER --apply`.
4. Diff: `diff USER.bak-m8 USER`. Only thirteen lines should be gone, each an `ask` entry.
5. Repeat steps 3 and 4 on `MIRROR` with `MIRROR.bak-m8`.
6. Paste the script's output and each diff here. The agent then reads `USER` read-only to confirm the thirteen are gone and
   `Bash(go install:*)` and the other entries remain, and stops if they are not.

**Gate run, after step 6.** In a new Claude Code session in an attached project (`wb check` reports no drift there), ask the
agent to run `pip install --dry-run requests`. A prompt should appear. Decline it. Paste the prompt text, say whether i
names a rule, and say whether the command ran (it must not have). Give `claude --version` and the project's `git rev-parse
HEAD`. If no prompt appears, restore `USER` from `USER.bak-m8` and stop; that is a finding about the floor, and the plan does
not change it.

**Script check, run by the agent on a scratch copy of the user-level file** (the real file was only read): the dry run listed
all thirteen and left the file alone; `--apply` on the copy removed thirteen lines and added none (`diff`), left 75 of 88
entries with `Bash(go install:*)` kept, and a second run found none to remove. The copy was not the mirror, whose formatting
the script's round-trip check will judge.

**Removals, made by the owner 2026-10-25.** On both files the dry run listed the thirteen entries with `go install kept: True`,
`--apply` wrote, and `diff` against the backup showed exactly thirteen `ask` lines gone and nothing added (75 entries left of
88). The agent then read the user-level file read-only: 75 `ask` entries, and among the install and push forms only
`Bash(git push:*)` and `Bash(go install:*)` remain. The agent wrote nothing at the user level or the mirror.

**Gate run, made by the owner.** Commit `a333708`, Claude Code 2.1.310, in this repository (attached). Asked to run
`pip install --dry-run requests`, the session showed a permission prompt reading "Ask rule Bash(pip install*) overrides auto
mode for this command". That is the pattern the floor renders (Increment A); the prompt names the pattern and not its
source, and the user-level entry, which had the form `pip install:*`, was gone. The owner chose No, and the command did not run. Conclusion: with
the user-level `pip install` entry gone, the project's own rule still prompts. Only the `pip install` form was run live; the
other twelve rest on the Increment A test, which pins the rendering and not Claude Code's live matching. Backups of both files
(`.bak-m8`) remain with the owner.

**Verification as run:** `git diff --check`, `wb check`, `doccheck`, `refcheck`, `wb run code-work check` (46 plans), all clean.
**Not done:** a push, and Increment C.
**Review:** the `reviewer` agent, one exchange (of a cap of 6), no blocking finding, four not blocking, all applied. (1) The
Result heading and opening paragraph still said nothing was done: corrected. (2) A placeholder sentence about the review:
replaced by this paragraph. (3) The twelve non-pip inventory rows could be read as live evidence: they now say "not run live"
and cite Increments A and B. (4) Attributing the prompt to the floor was an inference: softened above. The reviewer read only
the two changed regions and could not run commands or read the user level. The review is not an approval.

### Increment C (done, reviewed, not yet committed)

Started 2026-10-25 at commit `f4b3816`. `wb plan-status` printed `approved` (re-approved by the owner after the Result heading was
corrected from a misspelling). The removal and the gate run were made by the owner, recorded below the steps.

**Owner steps.** Every step is the owner's, in a terminal. `USER` and `MIRROR` are the roles named under Increment B; the
owner supplies the paths. Backups from Increment B (`.bak-m8`) predate the M8 removals, so they are not current: make new ones.

1. Back up both files, each next to itself: copy `USER` to `USER.bak-m9` and `MIRROR` to `MIRROR.bak-m9`.
2. Save the script below as `remove_m9.py` in your own work folder (untracked). It removes exactly `Bash(git push:*)`, refuses
   unless the file reads back byte for byte as the JSON it parses to, and does nothing unless given `--apply`.

   ```python
   import json, os, sys, tempfile

   ENTRY = "Bash(git push:*)"

   path = sys.argv[1]
   apply = "--apply" in sys.argv[2:]
   with open(path, encoding="utf-8") as handle:
       text = handle.read()
   data = json.loads(text)
   for indent in (2, 4, 1, 3, 8):
       for tail in ("\n", ""):
           if json.dumps(data, indent=indent, ensure_ascii=False) + tail == text:
               break
       else:
           continue
       break
   else:
       sys.exit("refused: the file does not round-trip, so a rewrite would change more than the entry")
   ask = data["permissions"]["ask"]
   print("present:", ENTRY in ask)
   data["permissions"]["ask"] = [entry for entry in ask if entry != ENTRY]
   print("ask entries remaining: %d (was %d); go install kept: %s"
         % (len(data["permissions"]["ask"]), len(ask), "Bash(go install:*)" in data["permissions"]["ask"]))
   if not apply:
       sys.exit("dry run: nothing written; rerun with --apply")
   out = json.dumps(data, indent=indent, ensure_ascii=False) + tail
   descriptor, name = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)))
   with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
       handle.write(out)
   os.chmod(name, os.stat(path).st_mode & 0o7777)
   os.replace(name, path)
   print("written")
   ```
3. Dry run on `USER`: `python3 -I -B remove_m9.py USER`; then `python3 -I -B remove_m9.py USER --apply`.
4. Diff: `diff USER.bak-m9 USER`. Exactly one line should be gone, the `git push` entry.
5. Repeat steps 3 and 4 on `MIRROR` with `MIRROR.bak-m9`.
6. Paste the output and each diff here. The agent then reads `USER` read-only to confirm only that entry is gone, and stops
   if not.

**Gate run, after step 6.** Use a throwaway attached project with no remote, or one whose remote you name, never this
repository. (a) Count the rows of the approver's verdict log and note the number. (b) In a new Claude Code session in that
project, ask the agent to run `git push`. A prompt should appear. Decline it. (c) Count the rows again. Paste the prompt text,
both counts, and the new row's rule, decision and verdict (rows hold command hashes, not command text), and say that nothing was
pushed. Give `claude --version` and the project's `git rev-parse HEAD`. If no prompt appears, restore `USER` and `MIRROR` from
the `.bak-m9` files and stop; that is a finding about the floor. If the prompt appears but the log gains no row, restore the
entry and stop; that is a finding about the approver. This plan changes neither.

**Removals, made by the owner 2026-10-25.** On both files the dry run printed `present: True`, `74 (was 75)` and `go install kept:
True`; `--apply` wrote; `diff` against the `.bak-m9` backup showed exactly one `ask` line gone (`Bash(git push:*)`) and nothing added.
The agent then read the user-level file read-only: 74 `ask` entries, and among the push and install forms only
`Bash(go install:*)` remains. The agent wrote nothing at the user level or the mirror. As a deviation from step 2, the agent saved
the script in its scratch folder, transcribed from the block above, and the owner ran it from there; it touched only the two named
files.

**Gate run, made by the owner.** Throwaway attached project with no remote and no commits, Claude Code 2.1.310 (so there is no
project commit to give). The approver's verdict log went from 1006 to 1007 rows. In a new session the agent was asked to run
`git push`; the session showed a permission prompt reading "Ask rule Bash(git push) overrides auto mode for this command". The
owner chose No, and the command did not run (the project has no remote, so nothing could have been pushed). The one new row
has rule `git-push`, decision `none`, verdict `decline`, mode `delegate`, reason `failed_checks`, with the failed checks
`remote_is_configured`, `remote_transport_safe`, `push_target_known`, `outgoing_known` and `outgoing_trusted`; it holds a command
hash and no command text. Conclusion: with the user-level `git push` entry gone, the project's own rule still prompts, and the
global approver still fires on that prompt and logs a verdict, so the F-B1 inference holds for this case. The prompt names the
pattern `git push`, not its source. Only the bare `git push` form was run; `git push origin main` and the force forms rest on the
Increment A test, which pins the rendering and not Claude Code's live matching. The backups (`.bak-m9`) remain with the owner.

All the gate-run details above (prompt text, counts, the row's fields) are from the owner's pasted terminal output, and the
owner confirmed choosing No. The decline came from failed remote checks, so it is no evidence about a push with a remote
configured.

**Verification as run:** `git diff --check`, `wb check`, `doccheck`, `refcheck`, `wb run code-work check` (46 plans), all clean.
The full test suite was not rerun: no code changed since Increment A.
**Not done:** a push.
**Review:** the `reviewer` agent, one exchange (of a cap of 6), no blocking finding, five not blocking. (1) The "pending"
verification line: replaced by this paragraph. (2) Provenance of the gate-run details: stated above. (3) The inventory's F-B1
text still called the case untested: a clause now points at this run and limits it to one case. (4) The script's location was
a deviation from step 2: named above. (5) The re-approval wording was unverifiable by the reviewer and is left as the plan
status reported it. The reviewer read only the two changed regions and ran nothing. The review is not an approval.
