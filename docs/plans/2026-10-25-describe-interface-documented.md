# Document the describe interface and complete the action-review contract

Status: Completed
Created: 2026-10-25
Candidate: none (plan 1 of the five in the split of `docs/specs/action-review.md` for `workbench-v1#action-review-engine`; it builds nothing, and the candidate is complete only when the engine is built, so the plan that builds it names the candidate)
Specs: action-review, module-contract, module-boundary, safe-git

## Goal

Settle on paper everything the accepted decision `2026-10-25-describe-interface-for-action-review` left open, and
count where the owner's approver goes wrong, so that the next plans (`safe-git describe`, then the engine) have
nothing to guess. This is plan 1 of the five in the split of `docs/specs/action-review.md`. It changes documents only.

When the plan is done:

- the specs say how a module declares that it provides `describe` for an action;
- `safe-git.md` names the facts of `describe commit` and `describe remove`, their types, and their numeric caps with
  the source of each number, and maps every check of the approver for a commit, a removal and a push to a fact or
  records why it has none;
- `action-review.md` states the verdict object, the output and exit contract of `review`, the log, and how the
  engine learns that a command is pinned and declared;
- the spec records a count of the approver's declines by failed check, taken before the engine's rubric is written.

## Scope

- Four documentation commits, one per increment, in `docs/specs/` (and one dated note after the unchanged body of
  the accepted decision, see Increment D).
- Reading the owner's approver program, its rule files, rubric and verdict log, read-only (role USER). The agent
  does not run the approver and writes nothing at the user level.
- Reading the real `commit` and `remove` code of `safe-git` to list what each validates.

## Non-goals

- Building anything: no `describe` command, no engine, no hook, no verifier change, no test. Those are plans 2 to 5.
- The JSON schema of a rule file. The engine's plan writes it first (spec, "The engine").
- Labelling commands, the shadow period, the test set of dangerous cases, or any change to the 10% bound. The count
  in Increment A informs the owner's decision on the bound and does not make it.
- Facts for the remote actions (`remote-runner describe`); they wait for M16.
- Changing the design the owner approved on 2026-10-25, or any accepted decision other than the dated note below.

## Assumptions and constraints

- **The design stands.** The owner approved `docs/specs/action-review.md` as a design and accepted the decision
  record on 2026-10-25. This plan fills what they left open and proposes nothing that contradicts them. The spec stays
  `Draft` because nothing is built.
- **A call this plan makes is the author's until the owner approves the plan.** The declaration form (Increment B)
  changes what `module-contract.md` says about direction. By approving this plan the owner approves that form; if the
  owner prefers another, they say so before approval and Increment B changes.
- **The user level is read only.** The agent reads the approver, its rules, its rubric and its log, as it did
  for the earlier plans, and never writes there (`2026-10-24-project-guarantees-a-floor`). The log holds command
  digests, not command text; no digest is copied into a tracked file. Tracked text names a global file by role
  (USER), item name, retrieval date and SHA-256, and writes no path to it (`AGENTS.md`, the tracked-pointer rule).
- **Scratch work stays out of the tree.** Any script that reads the log is written in the session scratchpad, run with
  `python3 -I -B`, reads in binary mode, and prints counts only.
- **The caps must fit the bridge.** The model bridge accepts a prompt of at most 262,144 bytes
  (`model-bridge.md`). The facts, the rubric and the review questions travel in one prompt, so the facts cap is chosen
  with that figure in view.
- **Each increment is one reviewed local commit** made with `wb run safe-git commit`, with no attribution. Review is the
  `reviewer` agent, as `run-increment` says. A review by a second model happens only if the owner asks.
- Discovery: graphify: skipped, no discovery tooling installed. The scope is four named specs and two read-only
  inputs, all enumerated above.

## Completion criteria

1. `action-review.md` holds a count of the approver's declines by failed check, with the log's role, item, retrieval
   date, byte size and SHA-256 at the time it was read, and states what the count does and does not show. If the log
   cannot give it, the spec says so and why.
2. `module-contract.md` and `module-boundary.md` state the declaration form, marked as specified and not built, with
   its field type, bounds, refusals and the rule the engine applies; the two specs agree.
3. `safe-git.md` has a "Describe" section with, for `commit` and `remove`: each fact's name, type and meaning; each
   refusal of the real command as an error code; the numeric caps with their source and the rule that truncation keeps only whole values; and a table that maps every
   approver check for a commit, a removal and a push to a fact or to a recorded reason. The gap between the approver's
   push checks and `push-check` is listed.
4. `action-review.md` states the verdict object, the output and exit contract of `review`, the log content and
   location, and how the engine learns that a command is pinned and declared, or lists that last as a named open
   question for the owner.
5. The dated note on the decision record exists after its unchanged body.
6. `git diff --check`, `wb check`, `doccheck`, `refcheck` and `wb run code-work check` are clean at the last commit.

## Increments

### Increment A — Count the approver's declines by failed check

**Outcome:** the spec records where the approver's declines come from, so the engine's rubric and checks are written
knowing which checks cause them. The count is evidence, not a bound.
**Dependencies:** none.
**Affected areas:** `docs/specs/action-review.md` (the Evidence section and the sentence in "Accuracy and cutover"
that says plan 1 does this first). Reads, not changes: the approver's verdict log and program (role USER).
**Steps:**
1. Locate the verdict log by reading the approver program (read-only). Record its role, item name, byte size,
   retrieval date and SHA-256 before it is read.
2. Write a read-only script in the session scratchpad that opens the log in binary mode and prints only counts: rows
   in total; rows by rule; rows by verdict; and, for declines, rows by failed check, with the first and last row date.
   Run it with `python3 -I -B`. It prints no command digest and no free text from a row.
3. If the log lacks the failed checks, is unreadable, or has a shape the script does not know, stop. Record what
   was found in the spec's Evidence section and report to the owner. Do not widen the plan to get past it.
4. Add a subsection to Evidence: the counts, the provenance line (role, item, date, size, SHA-256, script run with
   which Python), and the limits. The limits are: a decline in the log is not a false decline, because no label exists;
   the count says which checks cause declines and not which were wrong; the log grows, so the figures are as of the
   retrieval date; and a command whose rule does not load is not reviewed at all, so the log cannot show it
   (spec, "Anti-goals").
5. Say in one sentence whether the counts bear on the provisional 10% bound. Do not change the bound: it is the
   owner's.
**Verification:** `git diff --check`; `doccheck`; `refcheck`; `wb check`; `wb run code-work check`. The script's output
is read and pasted as counts only; the log's SHA-256 is recomputed after the read and equals the recorded one, or the
difference is explained as growth. No tracked file holds a digest or a path to a global file.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-describe-interface-documented#A`.

### Increment B — The declaration form for a module that provides `describe`

**Outcome:** the contract says how a module declares that it provides `describe` for an action, so the engine can
refuse a module that does not, and Increment D can state the engine's admission rule in full.
**Dependencies:** none.
**Affected areas:** `docs/specs/module-contract.md` ("Module declaration" table, "Concrete schema", acceptance
criteria) and `docs/specs/module-boundary.md` ("Declaration schema").
**Steps:**
1. Specify an optional field `describes` on a `commands` entry: a list of at most 16 distinct strings, each
   `^[a-z][a-z0-9-]*$` and at most 32 characters, the actions the command's `describe` verb answers. It is allowed only
   when `describe` is one of the command's `arguments`, and `describe` may not be listed in `owner`.
2. State the engine's admission rule in the spec text: it accepts a (module, action) only when the command is pinned for
   an installed module, `describe` is among its `arguments`, and the action is in `describes`. This is the
   "provides `describe` for that action" test of the decision, record 5.
3. State the refusals the verifier gives, each naming the module and the field: an entry that is not a string, a duplicate action,
   an action that fails the form, `describes` without `describe` in `arguments`, and `describe` in `owner`. Mark the field
   *(specified, not built; the verifier support and its tests are the first increment of the plan for `safe-git describe`)*,
   as the contract marks other fields that are not built.
4. Record the alternatives and why they lose: a capability per action (capabilities are one project-wide namespace of
   names with no action argument), and a module-level list (it would not say which command's `describe` answers, and the
   pin is per command).
5. State that the field is additive and part of the declaration hash as written, like the other optional fields, so
   no contract version bump is needed.
**Verification:** the two specs agree on the field and its refusals (read side by side); `git diff --check`; `doccheck`;
`refcheck`; `wb check`; `wb run code-work check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-describe-interface-documented#B`.

### Increment C — Facts, caps and the approver's checks for `safe-git`

**Outcome:** `safe-git.md` fixes what `describe commit` and `describe remove` report, in numbers, and shows that no
check the approver makes today is lost for a commit, a removal or a push.
**Dependencies:** none (Increment A informs it and is done first).
**Affected areas:** `docs/specs/safe-git.md` (a new "Describe" section; the "Declaration (summary)" table).
Reads, not changes: the `safe-git` helper's validation code and tests; the approver's program, rules and rubric
(role USER).
**Steps:**
1. Read the real `commit` and `remove` validation in the helper and list every refusal it can give, with the reason.
   Each becomes an error code in the `errors` list of the decision (`a-z0-9_`, at most 64 characters).
2. Read the approver's rule for the `commit`, `remove` and `git push` spellings, and its collectors and rubric
   (read-only). List each check, the fact it needs, and where the fact comes from today.
3. Define the facts of each action as a flat set of named values, with type and meaning (string, whole number, boolean,
   null, or array of strings), covering step 1 and step 2. Write a table that maps each approver check to a fact name, or
   to a recorded reason it has none (for example, a check that the engine makes elsewhere).
4. Choose the numeric caps and state the source of each: the serialized object in bytes, each string value in
   bytes, the length of each array and of each string in an array. The object cap is set so that the largest object, the
   rubric and the review questions fit in the bridge's 262,144-byte prompt with a stated margin; show the
   arithmetic. State what a diff fact is (which lines, which paths) and what happens when it does not fit: `truncated`
   is true, `facts` keeps only whole values that fit and never a cut value (decision 3), and the verdict is a decline. Say in plain words that this makes a very large commit always decline and the
   owner then sees the normal prompt.
5. List the checks of the approver for a push that `push-check` does not yet give (for instance, facts about the
   outgoing commits), as a gap. Design nothing for them. Say that a later plan covers the gap, and that the split in
   `action-review.md` needs a step for it, which Increment D records.
6. Add the acceptance criteria this section needs for plan 2: facts equal what the real command acts on, a repository
   byte for byte the same after the call, one error code per real refusal, and the cap behaviour.
**Verification:** every refusal listed in the "Commit" and "Remove" paragraphs of `safe-git.md` appears as an error
code; every approver check for the three actions appears in the table; the arithmetic of the cap is shown and
reproduces; the section says that truncation keeps only whole values and never cuts one; `git diff --check`; `doccheck`; `refcheck`; `wb check`; `wb run code-work check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-describe-interface-documented#C`.

### Increment D — The engine's contract, completed in the spec

**Outcome:** `action-review.md` holds the contract of the engine that its plan builds from, apart from the rule
schema, which is that plan's first deliverable. The decision record carries a dated note that its open point is settled.
**Dependencies:** Increments B and C.
**Affected areas:** `docs/specs/action-review.md`; the end of
`docs/decisions/2026-10-25-describe-interface-for-action-review.md` (a dated note, body unchanged).
**Steps:**
1. State the verdict object of `review`: `verdict` (`approve` or `decline`), `failed_checks` (an array of check names
   from the fixed set), `reason` (a string with a stated maximum), with the types and bounds, in the style of the decision.
2. State the output and exit contract: one JSON object on standard output and an exit status for each of an approve, a
   decline, a refusal (a rule that does not load, an unpinned module or bridge, an unreviewable command) and an engine
   failure. A refusal and a failure approve nothing and say why in a message the hook can show.
3. State the log: the fields it holds (hashes, never command text), what each hash covers, and where it lives, which is
   outside every project (spec, "Accuracy and cutover").
4. State how the engine learns that a command is pinned and declared. Read how the launcher records pins today
   (`module-boundary.md`) and write the rule if the answer is already there. If it is not, record it as a named open
   question for the owner and do not guess.
5. Record the timeout as it stands: open (spec, "Constraints and assumptions"). Add the figure the owner chooses if they
   state one when approving this plan. Do not choose one.
6. Update the split in the spec: plan 1 as done, a step for the `push-check` gap of Increment C, and the first
   increment of plan 2 as the verifier support for `describes`.
7. Add the dated note after the unchanged body of the decision record: "2026-10-25 (clarification): the form of the
   declaration is settled in `module-contract.md`, by plan `2026-10-25-describe-interface-documented`." This is a narrow
   clarification and needs the owner's approval; approving this plan with this text in it is that approval, and the owner may strike the step before approving, since the
   decision already says the form is settled in `module-contract.md`. The decision's
   body and status are not touched.
**Verification:** the verdict object and the decision's field rules do not contradict each other (read side by side);
the decision's body is byte for byte unchanged (a diff shows only the added note); `git diff --check`; `doccheck`;
`refcheck`; `wb check`; `wb run code-work check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-describe-interface-documented#D`.

## Verification for the plan as a whole

After Increment D, on the last commit: `git diff --check`; `wb check`; `wb run code-work check`; `doccheck`; `refcheck`.
Read the four specs and the note together for contradiction. No code changed, so the test suite is not rerun; its last
result (4225 tests OK, 2026-10-25) is not evidence for this plan.

## Risks and sensitive actions

- **Reading the user level.** The approver, its rules, rubric and verdict log are read-only inputs. The log is runtime state
  and holds digests, not command text. Nothing is written there and no digest or path is copied into a tracked file. The
  reviewer agent reads only the changed tracked files.
- **A count misread as an error rate.** The count of declines is not a rate of false declines. Increment A says so in the
  spec. Only the owner's labels measure false declines.
- **A cap that makes the review useless.** A tight cap would send many commits to the owner's prompt. Increment C shows the
  arithmetic and the consequence so the owner can judge the figure before approving the plan.
- **Direction change in a contract spec.** The `describes` field changes `module-contract.md`. The owner's approval of this
  plan is that stop; no verifier change is made.
- **The note on an accepted decision.** One dated sentence, text fixed above, with the body untouched.
- Externally visible actions: none. Nothing is pushed.

## Review record

Reviewed by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-25, at the
owner's request: three rounds, bound 3, converged in round 3 with no meaningful finding.

- R1-F1 (major, applied): the plan builds nothing, so naming the candidate would mark it complete. The `Candidate:` line is
  now `none` with the reason.
- R1-F2 (blocker, rejected): the reviewer said the dated note edits an accepted decision. The `draft-decision` skill allows a
  narrow dated note after the unchanged body with the owner's approval, and the accepted record leaves the form and the
  caps to the specs. Not applied; the owner may strike the step (Increment D, step 7) before approving.
- R2-F1 (major, applied): Increment C now requires that truncation keeps only whole values and never cuts one.

Round 3 was run after these edits, so the final text was reviewed. A review is not an approval: the plan stays `Proposed`.

## Deferred work

- Plans 2 to 5 of the split: `safe-git describe` (with the verifier support for `describes`), the engine, the shadow hook
  with the labelled set and the test set, and the cutover with M14. Each needs its own plan and the owner's approval.
- The extension of `push-check` for the outgoing commits, named as a gap in Increment C.
- The JSON schema of a rule file: the first deliverable of the engine's plan.
- Whether the 10% bound stays: the owner's call, after Increment A.
- Facts for the remote actions: after M16.

## Result

### Increment A — done, committed as `1f009c7`

Read the approver's program to find its verdict log, recorded its size and SHA-256, and ran a scratchpad script
(`python3 -I -B`, binary read, counts only). The log has the failed checks, so the plan did not stop. The spec's
Evidence section now holds "The approver's declines by failed check": 1,019 rows, 662 approve, 336 decline, 21 no
verdict; declines by rule and by failed check, for commit, remove and push; provenance and limits. The log's SHA-256
was equal after the read. One sentence in "Accuracy and cutover" now points to the count. The 10% bound is unchanged.
Changed path: `docs/specs/action-review.md`.

Verification as run: `git diff --check`, `wb check`, `wb run code-work check` (47 plans), `doccheck` and `refcheck`
were all clean before the review fixes; they are rerun before the commit. Not run: the test suite (no code changed).

Review: the `reviewer` agent, one round, no blocking finding. Three non-blocking: the summary sentence overstated
`no_reviewer_directed_text` for push (applied: the sentence now gives the per-action leaders); the log's last date
is a day after the retrieval date (applied: the spec says the timezone was not checked); the Python version
(checked: it is the printed output of `python3 -I -B -V`, 3.15.0). Nothing remains open.

### Increment B — done, committed as `d3c94e4`

Specified the optional `describes` field on a `commands` entry in `docs/specs/module-boundary.md` ("Declaration
schema": the field, its refusals, the engine's admission rule, the alternatives that lose, and the note on the
declaration hash and the contract version) and in `docs/specs/module-contract.md` (the field-table row, a bullet in
the concrete schema, an acceptance bullet). Marked specified, not built, in each place. No code changed.

Verification as run: `git diff --check`, `wb check`, `wb run code-work check` (47 plans), `doccheck` and `refcheck`
were clean before the review fixes; they are rerun before the commit. The two specs were read side by side.

Review: the `reviewer` agent, one round, no blocking finding. Applied: the hash claim now holds only for a pin the
installer made (a hand pin records no hash, so `describes` is a filter there, like `arguments`); an empty list is
stated to be allowed. Not applied: a blank line before the `approval` bullet, which was already there. Nothing
remains open.

### Increment C — done, committed as `7f2400a`

Added a "Describe" section to `docs/specs/safe-git.md`, marked specified, not built, and a note in the Declaration
table and in "Non-goals". It holds: the error codes for the refusals of the real `commit` and `remove` (read from the
helper and the shared path check); the facts of `describe commit` and `describe remove` with their types; the caps with
their sources and the arithmetic (196,608 + 28,332 + 8,192 = 233,132 of 262,144, 29,012 spare); the rule that a value is
omitted whole and never cut; a table that maps each approver check for commit and remove to a fact or an engine or
rubric check; the push gap as a list; and the acceptance criteria for the plan that builds `describe`. The approver's
rules, rubric and program were read read-only; their SHA-256 and sizes are in the section. No code changed.

Calls made by the author, for the owner to judge: the `diff` cap of 96 KiB (narrower than the approver's 256 KiB, so a
commit with a diff between the two declines under `describe`; stated in the section); the object cap of 196,608 bytes;
the array cap of 200 elements; one error code per refusal class rather than per message; and the new git shapes
(`cat-file`, `check-ignore`, `ls-files`) that `describe` needs, left to the security pass of plan 2.

Verification as run: `git diff --check`, `wb check`, `wb run code-work check` (47 plans), `doccheck` and `refcheck`
were clean before the last review fixes; they are rerun before the commit. Not run: the test suite (no code changed).

Review: the `reviewer` agent, two rounds (cap 3). Round 1 found two blocking findings (two `remove` refusals with no
code; an exit-status contradiction) and nine non-blocking; all were applied. Round 2 found no blocking finding and five
non-blocking points, all applied (the `no_git_metadata` row, the non-goals line, facts on a refusal, the file system
monitor in the program-selection test, a criterion for `entry_total`). Nothing remains open.

### Increment D — done, committed as `da44f74`

Added to `docs/specs/action-review.md`: the section "The verdict, the output and the log" (the verdict object with
types and bounds, the output and exit table with 0, 1 and 2, the log fields and their residual exposure, and how the
engine learns that a command is pinned and declared); the split updated (plan 1 done, the plan 2 first increment, the
push gap); three open questions for the owner; and two acceptance bullets. Added the dated note, with the text fixed in
the plan, after the unchanged body of `docs/decisions/2026-10-25-describe-interface-for-action-review.md`; `git diff`
shows only that appended note. No code changed.

Not decided by the author, and left to the owner: how the engine knows a command is declared for an action (the
launcher enforces the pin but not `describes`; option (a) a launcher rule, option (b) a read-only listing, with the
author's lean to (a) and the cost of it stated); who writes the log, and whether a failed write may withhold an approve;
and the timeout (no figure was stated). The step-4 answer for "pinned" was found in `module-boundary.md`; the answer for
"declared" was not, so it is a named open question.

Verification as run: `git diff --check`, `wb check`, `wb run code-work check` (47 plans), `doccheck` and `refcheck`
were clean before the review fixes; they are rerun before the commit. Not run: the test suite (no code changed). For
the plan as a whole, the four specs and the note were read together by the reviewer for contradiction.

Review: the `reviewer` agent, one round, no blocking finding and eight non-blocking. Applied: the refusal row no longer
covers a `truncated` object; the hook validates the object and a decline's exit 0 is addressed; the sibling bridge
contract difference is noted; the log's residual exposures and the acceptance bullet are corrected; the pin claim is
qualified for a hand pin and the command-name mapping is noted; the cost of option (a) is recorded; the split's counts
and cross-reference are corrected; C's line above is corrected. Nothing remains open in this increment.

### Plan closed

All four increments are committed (A `1f009c7`, B `d3c94e4`, C `7f2400a`, D `da44f74`) and pushed to `origin/main`.
Completion criteria, checked against the last increment's commit: 1 the count and its provenance are in
`action-review.md` (Evidence); 2 the declaration form is in `module-contract.md` and `module-boundary.md`, marked
specified, not built; 3 the "Describe" section is in `safe-git.md`; 4 the verdict object, the exit contract, the log
and the pinned-and-declared question are in `action-review.md`, the last as a named open question; 5 the dated note
follows the unchanged body of the decision; 6 `git diff --check`, `wb check`, `wb run code-work check` (47 plans),
`doccheck` and `refcheck` were run clean on a clean tree at `da44f74`.

Open, for the owner and for the plans that follow: how the engine knows a command is declared for an action (a launcher
rule or a read-only listing), who writes the engine's log, the timeout, and the rubric size estimate, which the engine's
plan measures. The `Candidate:` is `none`: the candidate `action-review-engine` is complete only when the engine is
built. Plans 2 to 5 of the split still need their own drafts and the owner's approval.
