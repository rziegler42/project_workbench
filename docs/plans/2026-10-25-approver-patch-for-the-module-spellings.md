# Prepare and test the approver patch for the module spellings (move M1, stage 1, option 1a)

Status: Completed
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

### Increment A (done, reviewed, committed as `ee81294`)

Ran 2026-10-25 at commit `3457d02`, Python 3.15.0, Darwin 25.6.0.

Baseline: the approver program's SHA-256 is `94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b`, and the
configuration, rubric, schema and eight rule files hashed the same as in the baseline plan; they were the same again at the end
of the increment. A fresh scratch copy hashed identical to the originals.

Spec: the required behavior is written in the inventory spec, after the M1 paragraph (a table of the four spellings with tool,
rule, subcommand, flags, positionals and required flags, then what must stay unmatched and unchanged). Findings made while
reading, now in that text:
- The flags of the module's `commit` and `remove` equal those of the global rules (`safe-git.md`); no difference was found. The
  module's `submit` requires exactly one of `--remote` and `--best`, which a rule cannot say; it does not need to.
- The fetch collector reads `args["--force"]`, so the module's fetch rule must declare `--force` although the module's `fetch`
  never passes it. A command carrying it matches and then fails the existing check `no_fetch_force`. A rule that omitted the flag
  would make the collector fail with a missing key.
- By reading, `split_command` should need no change, because a multi-word spelling is a raw-text prefix like the others; the
  plan's Increment B step 1 lists it, and B confirms or corrects this and leaves it alone if it holds. The unpatched run cannot
  show it either way.
- `wb` is a shell-script launcher outside the repository. The installed-helper check treats it like plain `git` (no installed copy
  to compare with) plus the shebang and interpreter test that the global helpers get.
- By reading (grep of the program), tool names are used only by the matching and by `resolve_invocation`, so the new names
  `safe-git` and `wb-remote-runner` should need entries in the spelling map and the supported-tools list and, if the new branch
  precedes the lookup, not in `INSTALLED_TOOLS`; B confirms this, and the plan's list stands until then.

Tests (scratch, untracked; script SHA-256 `8e2303be46941047377edbf016843ff1796c6b8b34b242e0fb445f88f521ee20`): 83 tests run
with `python3 -I -B` against the unpatched copy, calling `split_command`, `match_event`, `load_rules`, `CHECKS` and
`resolve_invocation` only (no model call, no `process`, `evaluate`, `main` or `load_helper`). The script refuses a copy root
that is, or contains, the user level (this replaces the tautological guard of the earlier experiment). Result: 59 passed and 24
failed, and each failure has the stated reason: 12 because `split_command` returns no spelling for a `wb run ...` line (so no
rule is read), 1 because the rules directory holds 8 rules and not the expected 12 ids, and 11 because `resolve_invocation`
raises `KeyError` for a spelling it does not know. The 8 controls pass (five existing spellings, the `python3 -B` spelling,
`DELEGABLE` and plain `git`). The 51 "must stay unmatched" tests also pass, but they pass vacuously before the patch (no spelling
matches at all), so they have value only as regression tests after it; they are not evidence that the patch is safe.
Not run: anything that reaches a model or the hook's entry point, the collectors, and the interactive session.

Verification as run: `doccheck`, `refcheck`, `git diff --check`, `wb run code-work check` and `wb check` (see the report).
Review: the `reviewer` agent (one exchange): no blocking finding. Applied: the reading-only claims (`split_command`, the constants,
the `--force` inference, the tokenizer) are marked as by reading and to be confirmed in B; the missing sentence that only a
prompted command is reviewed; the module's own bounds on `submit` and `fetch`, and the paths after `--`. Noted: 11 of the 24
failures are `KeyError` from an unknown spelling, not "no spelling matches", a deviation from the wording of step 5 that this
Result already states. A review with no blocking finding is not an approval.

Committed as `ee81294`. Not done in A: Increments B and C.

### Increment B (done, reviewed, committed as `6720b44`)

Ran 2026-10-25 at commit `ee81294`, Python 3.15.0, Darwin 25.6.0, on a scratch copy of the approver in the layout it expects
(the program under `hooks/` and its data under `codex-approver/`). The user-level files were read only: the hashes of the program
and of the configuration, rubric, schema and eight rule files matched the baseline at the start, after the patch and after the
fixes below.

**What the patch changes** (one program file edited, four rule files added; base hash
`94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b`):
- a map `WB_SPELLING_TOOL` of the two new spellings to the tool names `safe-git` and `wb-remote-runner`, added to
  `SPELLING_TOOL`, and the two names added to `SUPPORTED_TOOLS`;
- a new function `resolve_launcher` and one branch at the top of `resolve_invocation` that sends the two new spellings to it.
  The launcher `wb` must resolve outside the repository (the same walk of `PATH` as for the helpers and plain `git`), and so
  must the file it resolves to (a link into the repository is refused). Its shebang must be one word, or exactly
  `#!/usr/bin/env python3`, and gets the interpreter test the helpers get. The real launcher runs `python3` through `PATH`, so
  `python3` must also resolve outside the repository;
- four rule files, each a copy of the global rule for the same command with only `id` and `tool` changed (`safe-git-commit`,
  `safe-git-remove`, `wb-remote-runner-submit`, `wb-remote-runner-fetch`). They reuse the collectors, checks and rubrics.

Not touched: `split_command`, `tokenize`, `match_rule`, `parse_arguments`, `INSTALLED_TOOLS`, the collectors, `DELEGABLE`, the existing
spellings, the configuration, the rubric and the schema. `match_event` already passes only the rules of the spelling's own tool
to `match_rule`, and the module rules carry tool names no global spelling maps to, so a module rule cannot match a global
spelling and a global rule cannot match a module spelling (the cross-tool tests show it).

**Read in A and now confirmed by test:** `split_command` needs no change (a multi-word spelling is a raw-text prefix; the
tests pass without touching it); `INSTALLED_TOOLS` needs no entry (the new branch returns before the lookup); the module
fetch rule must declare `--force` (a test shows the flag reaches the collector's arguments and `no_fetch_force` refuses it).
The real `wb` launcher, read once, begins `#!/bin/sh`, which the check accepts; the check was not run against the real launcher
or the owner's `PATH`.

**Tests** (scratch, untracked; script SHA-256 `9486745ed8d28d9ecbb56b9f47060405aba27487113b56b5410d72c1aa041bbd`, the script
of A plus 8 launcher tests added after the security review): against the unpatched copy the 83 tests of A gave 59 passed and
24 failed (recorded in A); against the patched copy **91 passed, 0 failed**. They call `split_command`, `match_event`,
`load_rules`, `CHECKS` and `resolve_invocation` only. The controls (five existing spellings, the `python3 -B` spelling,
`DELEGABLE`, plain `git`) pass unchanged. The 51 "must stay unmatched" tests, vacuous before the patch, pass with the
spellings listed; most of them (operators, substitution) pass because the tokenizer refuses them, which was also so before
the patch, so they are regression tests and not evidence that the patch itself refuses them.

**Hostile strings** (scratch script SHA-256 `4e9e90336fa05920430d93c632bcb916c983073975f870d73db74cea493973a1`): 37 command
strings and 5 malformed events, all as predicted, none matching a module rule when it should not. They include an equals-form
flag, a short flag, a duplicate flag, a flag whose value is a flag, an empty value, CR and CRLF, a NUL byte, a full-width `w`,
a no-break space after `run` and after the spelling, upper case `WB` and `Remove`, `$HOME`, a tilde, a brace expansion, a
comment, a subshell, a heredoc, a 20,000-character argument (over the cap) and a 16,000-character one (under it, matched),
a global spelling with a module subcommand, and a module spelling with a flag only the module lacks. Matching is routing, not
approval: a line that matches (for example a fetch with an absolute path, or `--force`) is still refused later by the rule's
checks. Those checks were not run here (they sit behind the collectors).

**The typo hazard, measured:** with the patched program, a rules directory in which one new rule names an unknown collector,
holds invalid JSON, or names a tool the program does not support makes the matching raise for every command that begins with a
listed spelling, including the existing global ones, as measured on the baseline. Removing the four new files while keeping the
patched program loads (8 rules) and the new lines simply stay unmatched.

**The self-check** (SHA-256 `b5899c2ad0fefb9cf1c4a902b56b1281d512cbc3bc9254f9175153e3fe4e6642`): it imports the program without running the hook's entry point, calls the matching
functions and the launcher check with harmless text, and writes nothing but a temporary directory it removes. With an optional
second argument it also compares the program's SHA-256. It checks that the rules directory loads with exactly the 12 expected
ids and that `DELEGABLE` is unchanged; that each new rule equals its global source except `id` and `tool`; that every flag a
collector reads is declared by each rule and every rubric section exists; that the seven existing lines and the four new lines
match their rules and eight lines stay unmatched; and, for both spellings, the launcher cases (accepted outside the repository;
refused inside it, with no launcher, with no `python3`, with `python3` only inside the repository, as a link into the
repository, and with a shebang that has an argument, a tab, a NUL or no shebang; the `env python3` shebang accepted). Results, run on
scratch copies: the fixed patched copy passes (72 checks); the base copy fails (28); a copy with a mistyped collector fails (28);
a copy missing the four rule files fails (16); a copy with invalid JSON in one new rule fails (27); a copy with the new rules but
the unpatched program fails (34); and the patched program before the security fixes fails (10). A mutation run changed the new
rule files in 14 ways (dropping a flag a collector reads, a mistyped or wrong rubric, removing a check, emptying the checks,
loosening `required` or `positionals`, reducing `review_checks`, changing a flag kind): all 14 were caught. It exits non-zero on
any failure. It does not run a collector, and it does not judge the owner's real `PATH`.

**The patch** (`git diff --no-index --no-prefix`, applied with `-p1` from the root that holds `hooks/` and `codex-approver/`).
Its two whitespace-only context lines are written empty, which `git apply` and `patch` both accept; the SHA-256 of the text
below, as a file ending in one newline, is `ff3d5ece0142bd22779e831a19b0984509dfc23756b62ce015abb93758ed1a16`. It applies to the program with SHA-256
`94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b`; the patched program's SHA-256 is
`d8b3facdee46432d27547a07865abf024741929ae2d9191e1015ee8280bcd613`. On a fresh copy of the base, `git apply --check -p1`
succeeded, and the real apply with `git apply` and, separately, with the system `patch` (Apple 2.0-12u11) each gave 16 files
whose hashes are identical to the patched copy's, on which the tests and the self-check pass. The security reviewer also found
the patch has no `..`, absolute path, link, non-ASCII byte or tab, and that `git apply` refuses it on an already patched tree.

```diff
diff --git b/codex-approver/rules/safe-git-commit.json b/codex-approver/rules/safe-git-commit.json
new file mode 100644
index 0000000..656b7cd
--- /dev/null
+++ b/codex-approver/rules/safe-git-commit.json
@@ -0,0 +1,36 @@
+{
+  "id": "safe-git-commit",
+  "tool": "safe-git",
+  "subcommand": "commit",
+  "collector": "commit",
+  "checks": [
+    "head_matches",
+    "repo_config_safe",
+    "staging_state_ok",
+    "paths_valid",
+    "message_valid",
+    "paths_not_credentials",
+    "paths_regular",
+    "facts_complete",
+    "no_secret_lines"
+  ],
+  "rubric": "commit",
+  "required": [
+    "--expected-head",
+    "--subject"
+  ],
+  "flags": {
+    "--expected-head": "value",
+    "--subject": "value",
+    "--body": "value",
+    "--trailer": "multi",
+    "--leave-other-staged": "bool"
+  },
+  "positionals": "paths",
+  "review_checks": [
+    "message_matches_change",
+    "scope_is_coherent",
+    "change_is_safe_in_itself",
+    "no_reviewer_directed_text"
+  ]
+}
diff --git b/codex-approver/rules/safe-git-remove.json b/codex-approver/rules/safe-git-remove.json
new file mode 100644
index 0000000..64dafda
--- /dev/null
+++ b/codex-approver/rules/safe-git-remove.json
@@ -0,0 +1,27 @@
+{
+  "id": "safe-git-remove",
+  "tool": "safe-git",
+  "subcommand": "remove",
+  "collector": "remove",
+  "checks": [
+    "confirm_present",
+    "removal_valid",
+    "ignore_status_known",
+    "preview_matches_arguments",
+    "no_git_metadata"
+  ],
+  "rubric": "remove",
+  "required": [
+    "--confirm"
+  ],
+  "flags": {
+    "--confirm": "bool",
+    "--recursive": "bool"
+  },
+  "positionals": "paths",
+  "review_checks": [
+    "targets_look_disposable",
+    "scope_is_narrow",
+    "no_reviewer_directed_text"
+  ]
+}
diff --git b/codex-approver/rules/wb-remote-runner-fetch.json b/codex-approver/rules/wb-remote-runner-fetch.json
new file mode 100644
index 0000000..c24d242
--- /dev/null
+++ b/codex-approver/rules/wb-remote-runner-fetch.json
@@ -0,0 +1,27 @@
+{
+  "id": "wb-remote-runner-fetch",
+  "tool": "wb-remote-runner",
+  "subcommand": "fetch",
+  "collector": "fetch",
+  "checks": [
+    "job_id_valid",
+    "job_remote_configured",
+    "fetch_paths_valid",
+    "no_fetch_force",
+    "fetch_targets_safe",
+    "no_secret_lines"
+  ],
+  "rubric": "remote-runner-fetch",
+  "required": [],
+  "flags": {
+    "--dest": "value",
+    "--as": "value",
+    "--force": "bool"
+  },
+  "positionals": "two-or-more",
+  "review_checks": [
+    "files_are_plausible_job_output",
+    "destination_is_appropriate",
+    "no_reviewer_directed_text"
+  ]
+}
diff --git b/codex-approver/rules/wb-remote-runner-submit.json b/codex-approver/rules/wb-remote-runner-submit.json
new file mode 100644
index 0000000..91d1215
--- /dev/null
+++ b/codex-approver/rules/wb-remote-runner-submit.json
@@ -0,0 +1,33 @@
+{
+  "id": "wb-remote-runner-submit",
+  "tool": "wb-remote-runner",
+  "subcommand": "submit",
+  "collector": "submit",
+  "checks": [
+    "repo_config_safe",
+    "remote_selection_valid",
+    "submit_source_valid",
+    "profile_defined",
+    "revision_pushed",
+    "origin_url_usable",
+    "no_secret_lines"
+  ],
+  "rubric": "remote-runner-submit",
+  "required": [
+    "--profile"
+  ],
+  "flags": {
+    "--remote": "value",
+    "--best": "bool",
+    "--profile": "value",
+    "--ref": "value",
+    "--snapshot": "bool"
+  },
+  "positionals": "none",
+  "review_checks": [
+    "profile_command_is_expected",
+    "revision_is_the_intended_work",
+    "host_selection_is_appropriate",
+    "no_reviewer_directed_text"
+  ]
+}
diff --git a/hooks/codex_approver.py b/hooks/codex_approver.py
index 8937c92..221d626 100644
--- a/hooks/codex_approver.py
+++ b/hooks/codex_approver.py
@@ -52,12 +52,16 @@ SPELLINGS = (
 REMOTE_RUNNER_SPELLINGS = tuple(spelling.replace("claude-workflow", "remote-runner") for spelling in SPELLINGS)
 ASK_CODEX_SPELLINGS = tuple(spelling.replace("claude-workflow", "ask-codex") for spelling in SPELLINGS)
 GIT_SPELLINGS = ("git",)
+# The workbench's own commit and remote-job commands, run through its launcher. Their tool names differ from the
+# global helpers' so a rule for one can never match the other's spelling.
+WB_SPELLING_TOOL = {"wb run safe-git": "safe-git", "wb run remote-runner": "wb-remote-runner"}
 SPELLING_TOOL = dict(
     [(spelling, "claude-workflow") for spelling in SPELLINGS]
     + [(spelling, "remote-runner") for spelling in REMOTE_RUNNER_SPELLINGS]
     + [(spelling, "ask-codex") for spelling in ASK_CODEX_SPELLINGS]
-    + [(spelling, "git") for spelling in GIT_SPELLINGS])
-SUPPORTED_TOOLS = ("claude-workflow", "remote-runner", "ask-codex", "git")
+    + [(spelling, "git") for spelling in GIT_SPELLINGS]
+    + list(WB_SPELLING_TOOL.items()))
+SUPPORTED_TOOLS = ("claude-workflow", "remote-runner", "ask-codex", "git", "safe-git", "wb-remote-runner")
 # How many positional words a rule accepts: (minimum, maximum or None).
 POSITIONAL_COUNTS = {"paths": (1, None), "none": (0, 0), "one": (1, 1), "up-to-two": (0, 2), "two-or-more": (2, None)}
 VERDICT_WORDS = ("approve", "decline", "no_verdict")
@@ -446,9 +450,42 @@ def find_on_path(name, path_value, cwd):
     return None, "not_found:" + name


+def resolve_launcher(name, path_value, cwd):
+    """Decide whether `name` would run a launcher script from outside the repository under a trusted interpreter.
+
+    The workbench launcher has no installed copy to compare with. As for plain git it has to resolve outside the
+    repository, and so does the file it resolves to. Its shebang then gets the interpreter test the helpers get,
+    and because the launcher runs `python3` through PATH, that must resolve outside the repository too.
+    """
+    launcher, why = find_on_path(name, path_value, cwd)
+    if launcher is None:
+        return False, why
+    boundary = repo_boundary(cwd)
+    if is_inside(launcher, boundary):
+        return False, "launcher_inside_repository"
+    try:
+        with open(launcher, "rb") as handle:
+            shebang = handle.readline(200).decode("utf-8", "replace").strip()
+    except OSError:
+        return False, "launcher_unreadable"
+    if shebang != "#!/usr/bin/env python3":
+        if "\0" in shebang or len(shebang.split()) != 1 or not shebang.startswith("#!/"):
+            return False, "unrecognised_shebang"
+        if is_inside(os.path.realpath(shebang[2:]), boundary):
+            return False, "interpreter_inside_repository"
+    python, why = find_on_path("python3", path_value, cwd)
+    if python is None:
+        return False, why
+    if is_inside(python, boundary):
+        return False, "interpreter_inside_repository"
+    return True, None
+
+
 def resolve_invocation(spelling, path_value, home, cwd, installed=None):
     """Decide whether the command would execute the installed helper under a trusted interpreter."""
     tool = SPELLING_TOOL[spelling]
+    if spelling in WB_SPELLING_TOOL:
+        return resolve_launcher("wb", path_value, cwd)
     if tool == "git":
         # Plain git has no installed copy to compare with; it only has to resolve outside the repository.
         git, why = find_on_path("git", path_value, cwd)
```

**The self-check script:**

```python
"""Pre-apply self-check for the patched approver. Reads only: it imports the program (no hook entry point runs),
calls the matching functions and the launcher check with harmless text, and writes nothing but a temporary
directory it removes. Run: python3 -I -B selfcheck.py <root-holding-hooks-and-codex-approver> [expected-program-sha256]
Exit status 0 only if every check passes."""
import ast
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

root = Path(sys.argv[1]).resolve()
program = root / "hooks" / "codex_approver.py"
if not program.is_file() or not (root / "codex-approver" / "rules").is_dir():
    sys.exit("FAIL: %s does not hold hooks/codex_approver.py and codex-approver/rules" % root)
sys.dont_write_bytecode = True
digest = hashlib.sha256(program.read_bytes()).hexdigest()
print("program sha256", digest)
spec = importlib.util.spec_from_file_location("approver_selfcheck", program)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

failures = []


def check(name, ok, detail=""):
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  [%s]" % detail))
    if not ok:
        failures.append(name)


def rule_for(command):
    try:
        got = m.match_event({"tool_name": "Bash", "tool_input": {"command": command}})
    except Exception as exc:  # noqa: BLE001 - a refused rule or configuration file lands here
        return "raised %s: %s" % (exc.__class__.__name__, exc)
    return got[3]["id"] if got else None


if len(sys.argv) > 2:
    check("the program hash is the expected one", digest == sys.argv[2], digest)
check("TOOL_HOME is the rules directory under the root", m.TOOL_HOME == root / "codex-approver", str(m.TOOL_HOME))
expected = ["ask-codex-archive", "claude-workflow-commit", "claude-workflow-remove", "git-push", "remote-runner-cancel",
            "remote-runner-fetch", "remote-runner-prune", "remote-runner-submit", "safe-git-commit", "safe-git-remove",
            "wb-remote-runner-fetch", "wb-remote-runner-submit"]
try:
    ids = sorted(r["id"] for r in m.load_rules(m.TOOL_HOME / "rules", known_collectors=m.COLLECTORS, known_checks=m.CHECKS))
except Exception as exc:  # noqa: BLE001
    ids = "raised %s: %s" % (exc.__class__.__name__, exc)
check("the rules directory loads with exactly the 12 expected ids", ids == expected, str(ids))
check("DELEGABLE is unchanged", m.DELEGABLE == frozenset({"claude-workflow-commit", "ask-codex-archive"}), str(sorted(m.DELEGABLE)))

# Each new rule is its global source with only `id` and `tool` changed; every flag a collector reads is declared; every
# rubric section exists. A rule that loads can still lose its review at run time (a missing key, a missing section).
try:
    by_id = {path.stem: json.loads(path.read_text()) for path in sorted((m.TOOL_HOME / "rules").glob("*.json"))}
    for new, old in (("safe-git-commit", "claude-workflow-commit"), ("safe-git-remove", "claude-workflow-remove"),
                     ("wb-remote-runner-submit", "remote-runner-submit"), ("wb-remote-runner-fetch", "remote-runner-fetch")):
        differing = sorted(key for key in set(by_id[new]) | set(by_id[old]) if by_id[new].get(key) != by_id[old].get(key))
        check("%s equals %s except id and tool" % (new, old), differing == ["id", "tool"], str(differing))
    functions = {node.name: node for node in ast.walk(ast.parse(program.read_text())) if isinstance(node, ast.FunctionDef)}
    for rule_id, rule in sorted(by_id.items()):
        function = functions[m.COLLECTORS[rule["collector"]].__name__]
        needed = {node.slice.value for node in ast.walk(function) if isinstance(node, ast.Subscript)
                  and isinstance(node.value, ast.Name) and node.value.id == "args" and isinstance(node.slice, ast.Constant)}
        missing = sorted(needed - set(rule["flags"]) - {"paths"})
        check("%s declares every flag its collector reads" % rule_id, not missing, str(missing))
        try:
            m.load_rubric(rule)
            rubric_ok, why = True, ""
        except Exception as exc:  # noqa: BLE001
            rubric_ok, why = False, str(exc)
        check("%s names an existing rubric section" % rule_id, rubric_ok, why)
except Exception as exc:  # noqa: BLE001
    check("rule files can be compared with their sources", False, "%s: %s" % (exc.__class__.__name__, exc))

H, S = "--expected-head abc123 --subject 'x'", "--profile p"
for command, want in [
    ("claude-workflow commit %s -- a.txt" % H, "claude-workflow-commit"),
    ("claude-workflow remove --confirm a.txt", "claude-workflow-remove"),
    ("remote-runner submit %s" % S, "remote-runner-submit"),
    ("remote-runner fetch job1 out/a.txt", "remote-runner-fetch"),
    ("remote-runner cancel job1", "remote-runner-cancel"),
    ("git push origin main", "git-push"),
    ("ask-codex archive --plan docs/plans/x.md", "ask-codex-archive"),
    ("wb run safe-git commit %s -- a.txt" % H, "safe-git-commit"),
    ("wb run safe-git remove --confirm a.txt", "safe-git-remove"),
    ("wb run remote-runner submit %s" % S, "wb-remote-runner-submit"),
    ("wb run remote-runner fetch job1 out/a.txt", "wb-remote-runner-fetch"),
    ("wb run safe-git push-check", None),
    ("wb run remote-runner cancel job1", None),
    ("wb run remote-runner prune --remote r", None),
    ("wb run safe-git commit %s --force -- a.txt" % H, None),
    (" wb run safe-git remove --confirm a.txt", None),
    ("env wb run safe-git remove --confirm a.txt", None),
    ("wb run safe-git remove --confirm a.txt; ls", None),
    ("wb run code-work check", None),
]:
    got = rule_for(command)
    check("%-60s -> %r" % (command[:60], want), got == want, "got %r" % (got,))

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp).resolve()
    (base / "repo" / ".git").mkdir(parents=True)
    out, inside = base / "out", base / "repo" / "bin"
    out.mkdir()
    inside.mkdir()
    SH = "#!/bin/sh\nexit 0\n"

    def put(directory, name, body):
        path = directory / name
        if path.is_symlink() or path.exists():
            path.unlink()
        path.write_bytes(body if isinstance(body, bytes) else body.encode())
        path.chmod(0o755)

    def invoke(spelling, *directories):
        try:
            return m.resolve_invocation(spelling, os.pathsep.join(str(d) for d in directories), str(base), str(base / "repo"))
        except Exception as exc:  # noqa: BLE001 - an unpatched program lands here
            return "raised %s: %s" % (exc.__class__.__name__, exc)

    for spelling in ("wb run safe-git", "wb run remote-runner"):
        put(out, "wb", SH)
        put(out, "python3", SH)
        put(inside, "wb", SH)
        for name, directories, want in [
            ("a launcher and python3 outside the repository are accepted", (out,), (True, None)),
            ("a launcher inside the repository is refused", (inside,), (False, "path_entry_inside_repository")),
            ("no launcher on PATH is refused", (base / "empty",), (False, "not_found:wb")),
        ]:
            got = invoke(spelling, *directories)
            check("%s [%s]" % (name, spelling), got == want, str(got))
        (out / "python3").unlink()
        got = invoke(spelling, out)
        check("no python3 on PATH is refused [%s]" % spelling, got == (False, "not_found:python3"), str(got))
        put(inside, "python3", SH)
        (inside / "wb").unlink()
        got = invoke(spelling, out, inside)
        check("python3 only inside the repository is refused [%s]" % spelling, got == (False, "path_entry_inside_repository"), str(got))
        (inside / "python3").unlink()
        put(out, "python3", SH)
        put(inside, "evil.sh", SH)
        (out / "wb").unlink()
        (out / "wb").symlink_to(inside / "evil.sh")
        got = invoke(spelling, out)
        check("a launcher that is a link into the repository is refused [%s]" % spelling,
              got == (False, "launcher_inside_repository"), str(got))
        for name, body, want in (("a shebang with an argument", "#!/bin/sh -e\n", (False, "unrecognised_shebang")),
                                 ("a shebang with a tab", "#!/bin/sh\t-e\n", (False, "unrecognised_shebang")),
                                 ("a shebang with a NUL", b"#!/bin/sh\0x\n", (False, "unrecognised_shebang")),
                                 ("no shebang", "echo hi\n", (False, "unrecognised_shebang")),
                                 ("the env python3 shebang", "#!/usr/bin/env python3\n", (True, None))):
            put(out, "wb", body)
            got = invoke(spelling, out)
            check("%s [%s]" % (name, spelling), got == want, str(got))

print("\n%s" % ("ALL CHECKS PASSED" if not failures else "%d CHECK(S) FAILED: do not use this configuration" % len(failures)))
sys.exit(1 if failures else 0)
```

**Reviews.** The `reviewer` (one exchange) and the `security-reviewer` (one exchange; its probes ran on scratch copies and no
collector, `process`, `evaluate`, `main` or `load_helper` was run). Neither is an approval.
- Reviewer finding 1 (the increment has no steps, no Increment C, no owner steps, no review record): the cause was the author's
  own error. The script that wrote this Result had cut the plan at its first `### Increment B` heading, so the reviewer saw a
  plan without B's steps and without C. The plan check then reported the damage, and the plan was rebuilt from the committed
  text with only the Result changed (checked: everything before `## Result` is identical to the commit). The owner steps are
  Increment C's by design, and the review record is this paragraph. Applied from findings 2, 6 and 7: the first line of the real launcher is recorded; the self-check now covers the
  launcher's shebang forms and a missing launcher and can compare the program hash; the limit that the collectors judge facts
  from the global program is in the spec's measured bullet. Finding 5 (the unmatched tests are weaker evidence than they sound):
  applied, in the Tests paragraph. Findings 3, 4, 8 and 9 raised nothing to change (4: the `wb-remote-runner-submit`
  bounds the rules cannot say are stated in the spec).
- Security finding Medium 1 (the launcher's `python3` was not judged): applied. Regression tests failed first (6 launcher
  tests against the patched program, for the stated reasons) and pass after the fix. Low 2 (a link from `PATH` into the repository
  was not refused) and Low 3 (a tab or NUL in the shebang; a NUL raised `ValueError`): applied the same way. Low 5 (the
  self-check missed a dropped flag, a wrong rubric, a removed check and a loosened rule): applied, and the mutation run above
  shows it now catches them. Low 4 (a `PATH` entry spelled in another case than the repository passes on a case-insensitive
  file system): not applied, because `is_inside` is the program's existing function and the behavior is not new; recorded as a
  limit. The security reviewer's candidate correction was read but not copied: the author's fix differs in the shebang handling.
  Nothing it found could turn a module rule into an allow: the module rule ids are not in `DELEGABLE`, `load_config` rejects a
  delegate id outside it, and `delegated_decision` returns no decision for them (tested and read by the reviewer).
- Not re-reviewed: the fixes after the security review were tested by the author's regression tests and the mutation run, not by a
  second adversarial pass. Say so to the owner; a further pass is the owner's call.

**Limits.** Nothing here ran the hook's entry point, a model call, a collector, or an interactive session; the checks behind
the collectors were not run. The launcher check judges the launcher, its shebang interpreter and `python3` on `PATH`, but not the
workbench checkout the launcher records and runs (the real launcher sets a directory variable to a checkout, which may be the
repository being worked on), and not a `PATH` entry spelled in another case on a case-insensitive file system (an existing
limit of `is_inside`). The approver reviews facts computed by the global `claude-workflow` program (option 1a), which may differ
from what the module's `safe-git` does with the same arguments. A match is only a routing decision; a wrong review would still
be advice, since no module rule can be allowed without the owner.

### Increment C (done, reviewed, committed as `7972b2a`; owner steps carried out 2026-10-25, see "Owner steps as carried out")

Increment C's own step 1 says to run the self-check before anything else; steps 3 and 4 below do so, on a scratch copy before the
live apply.

Written 2026-10-25 at commit `6720b44`. Nothing was applied and no user-level file was written; the hashes below are the ones recorded
in Increment B. Files are named by role and SHA-256, never by path.

**Owner steps, in order.** Each is the owner's, in a terminal. Stop at the first step that fails.
1. **Back up** the approver program, the folder of its data (configuration, rubric, schema and the eight rule files) and the
   settings file that holds the hook entries, in both the owner's configuration and its mirror. The program must hash to
   `94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b` before the patch; if it does not, stop, because the patch
   was written against that program only.
2. **Save the two texts from Increment B's Result as files, each ending in one newline, and check their hashes** (for example with
   `shasum -a 256 <file>`): the patch must hash to `ff3d5ece0142bd22779e831a19b0984509dfc23756b62ce015abb93758ed1a16` and the
   self-check script (saved as `selfcheck.py`) to `b5899c2ad0fefb9cf1c4a902b56b1281d512cbc3bc9254f9175153e3fe4e6642`. If either
   differs, the copy altered it (the patch has two whitespace-only context lines written empty): save it again from the text
   and stop if it still differs. In these steps the **root** is a directory that holds the program's folder `hooks/` and the data
   folder `codex-approver/` side by side, and the patch applies with `-p1` from it.
3. **Try the patch on a scratch copy first, before touching the live files.** Copy the backed-up program and data folder into a new
   scratch root in that layout, apply the patch there with `git apply -p1` (or `patch -p1`), and check that the program hashes to
   `d8b3facdee46432d27547a07865abf024741929ae2d9191e1015ee8280bcd613`. Run the self-check on the scratch root:
   `python3 -I -B selfcheck.py <scratch root> d8b3facdee46432d27547a07865abf024741929ae2d9191e1015ee8280bcd613`. It must print
   `ALL CHECKS PASSED` and exit 0 (72 checks). If it does not, stop; nothing live has changed. The self-check reads and writes
   nothing but a temporary directory and does not run the hook's entry point. The patch also adds the four rule files
   (`safe-git-commit`, `safe-git-remove`, `wb-remote-runner-submit`, `wb-remote-runner-fetch`).
4. **Apply the patch live** in the same way to the owner's configuration, check the same program hash, and run the same self-check
   against the live root. It must pass again. If any part of step 4 fails, restore the backup of the affected files and stop.
5. **Repeat step 4 in the mirror**, so the two copies hash alike. On any failure restore that copy from its backup.
6. **Add one hook entry per new spelling** in the settings file, with the same events and timeouts as the existing entries for
   the approver (the spellings are `wb run safe-git` and `wb run remote-runner`). Match how the existing entries are written; if the
   file lists spellings individually, add the two module spellings the same way.
7. **Add the four global `ask` entries** the accepted decision `2026-10-25-module-commands-and-the-approver` chose, one per command
   (`wb run safe-git commit`, `wb run safe-git remove`, `wb run remote-runner submit`, `wb run remote-runner fetch`), written in
   the form of the existing `ask` entries for the global commands.
   If an edit to the settings file fails or the file no longer parses, restore it from its backup (step 1) and stop.
8. **Start a new session** so the settings and the program are read again.
9. **Run the interactive gate of M1 stage 1** and record it. The gate, as the inventory spec words it: a `wb run safe-git commit`
   raises a prompt, the approver logs a verdict for it, and (the F-B1 test) a project `ask` reaches a global `PermissionRequest`
   hook. Use harmless command text. Write down the command, whether a prompt appeared, and the new row in the approver's own
   log (its time and the rule id, which should be one of the four new ids). Where the log lives and the shape of the entries in
   the settings file are in the owner's configuration, which this plan did not read; read the existing entries and copy their
   shape. Say so in the record if anything differed from these steps.
10. **Keep the backup** until the gate has passed; delete it only then.

**If the patch is wrong.** The failure is quiet: the approver stops reviewing and stops delegating the commit for the listed
spellings, and the prompt falls back to the ordinary permission rules. The sign is that the approver's log gets no new row for a
reviewed command (the new commands and the existing ones alike) after a prompt that should have been reviewed. The self-check in
step 3 (on a scratch copy) and step 4 are the guard; if a log row is missing after both passed, restore the backup and report it. No module rule can be allowed
without the owner, so a wrong patch cannot approve a command by itself.

**Spec.** In `global-config-inventory`, the M1 paragraph now says the patch is prepared and tested on a scratch copy and not
applied, and that the recorded interactive run is the gate. This plan is named as the carrying plan of stage 1; the earlier plan is
named only as the source of the baseline and the decision. Owner step text in the spec was changed from "adds and removes
nothing" to what step 3 to 7 add.

**Checks, as run:** `doccheck`, `refcheck`, `git diff --check`, `wb run code-work check` (45 plans) and `wb check` were clean
before the review; they are rerun after the edits it caused (see the end of this subsection).

**Review.** One `reviewer` exchange (not an approval); no blocking finding. Finding 1 (the self-check ran only after the live
apply): applied; steps 3 and 4 now try the patch on a scratch copy first. Finding 2 (a restore instruction only at one step):
applied, in steps 4, 5 and 7. Finding 3 (the owner could not act from the text alone): applied for the self-check script's hash,
the definition of the root, the hashing command, the scratch-copy command line and what to record at the gate; not applied for
the settings file's entry shape and the log's place, which this plan did not read and cannot name without reading the user
level, so the step tells the owner to copy the shape of the existing entries. Finding 4 (the subsection was unfinished): applied
by this paragraph. Not checked by the reviewer: that the quoted texts reproduce the hashes (checked in Increment B), the owner's real
settings, and the real `PATH`.

**Owner steps as carried out (2026-10-25, by the owner in a terminal; the agent read the user level, wrote nothing there, and
read the results back).** Files are named by role and SHA-256, never by path.
- Step 1: the approver program hashed to the base hash (`94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b`) in
  both the owner's configuration and its mirror. Both trees' program, data folder (eight rule files) and settings file were
  backed up to a folder outside both; the program and settings hashes of each backup matched the original.
- Step 2: the patch and the self-check script were extracted from Increment B's Result by a small script and hashed to the
  recorded values (`ff3d5ece…1ed16`, `b5899c2a…42`).
- Step 3: on a scratch copy, the patch applied with `patch -p1`, the program hashed to
  `d8b3facdee46432d27547a07865abf024741929ae2d9191e1015ee8280bcd613`, and the self-check printed `ALL CHECKS PASSED`.
- Steps 4 and 5: a dry run and then the real apply, in the live configuration and in the mirror. Each program hashed to the
  patched value, the rule folders of the two were identical, and the self-check passed in each (72 checks).
- Step 6: **not needed.** The settings file has one `PermissionRequest` hook with the matcher `Bash` that runs the approver for
  every Bash command, so there is no list of spellings to extend. The step applied only if the file listed spellings
  individually.
- Step 7: four `ask` entries (`wb run safe-git commit`, `wb run safe-git remove`, `wb run remote-runner submit`,
  `wb run remote-runner fetch`, each with `:*`) were added after the existing `remote-runner fetch` group in both settings
  files, by a script that refused to run if the file did not round-trip as 2-space JSON. A diff of each file against its backup
  showed exactly those four added lines.
- Steps 8 and 9, the gate, in a new session: the owner asked for `wb run safe-git commit --expected-head
  0000000000000000000000000000000000000000 --subject 'gate test' -- docs/plans/README.md`. A permission prompt appeared and named
  the new `ask` rule. The approver's verdict log went from 994 to 995 rows; the new row (2026-10-25T20:53:10Z) has the rule
  `safe-git-commit`, decision `none`, verdict `decline` and the failed check `head_matches`, as expected for an all-zero head. The
  launcher check therefore passed on the owner's real `PATH`. **The gate passed for `safe-git commit`.**
- Step 10: the backups are kept until the owner decides to delete them.

**What the gate did not show.** Only `safe-git-commit` went through a live prompt. `safe-git-remove`, `wb-remote-runner-submit`
and `wb-remote-runner-fetch` rest on the scratch tests and the self-check; the two remote commands were deliberately not run
(they reach a remote). The review is still advice: no module rule can be allowed without the owner. The mirror's changes (the
patched program, four rule files, four `ask` entries) were committed by the owner in the mirror repository as `6ae0566` (local,
not pushed at the time of writing).
