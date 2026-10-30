# Close the superpowers retirement

Status: Completed
Created: 2026-10-30
Candidate: none — these are moves M10, M11 and M12 of the move list in `global-config-inventory`, a follow-on to `workbench-v1#global-config-migration`, which the plan `2026-10-27-retire-carried-instructions` also followed; whether the roadmap gains a candidate for them is the owner's call and a roadmap edit stops for the owner
Specs: global-config-inventory, superpowers-ports

## Goal

The superpowers plugin stopped working on 2026-10-29 when the owner's user-level configuration was reset, and the plan the inventory
named for retiring it, `retire-superpowers-plugin`, was never written. This plan closes that out. When it is done, the specs say that
moves M10 to M12 were overtaken by the reset and name no plan that does not exist; the one test the specs left open (does a request for
new behaviour load `brainstorm` with no plugin?) has been run once and its result is recorded; and the owner has a decision record in
front of them on what, if anything, should route work in a repository that has no workbench skills.

## Scope

- Marking M10, M11 and M12 in `docs/specs/global-config-inventory.md` as overtaken, and removing the pointers to a carrying plan that
  does not exist.
- A recorded run of the session-start test, which is the owner's run, with its result written into `docs/specs/superpowers-ports.md`.
- One decision record, `Proposed`, on routing for repositories outside the workbench, with the options and what each costs.

## Non-goals

- Any change under `packages/`, so no release and no shipped text. The gaps in `evaluate-findings` and `verify-before-claiming` stay
  deferred (below).
- Any edit of the owner's user-level configuration. Whatever the decision says about it is the owner's to do, and is not done here.
- Porting `dispatching-parallel-agents`, `writing-skills`, `using-git-worktrees` or a fresh implementer per increment.
- Editing the roadmap. The wording of `global-config-migration` that lists the superpowers dependencies as items to settle is left for
  the owner, who may ask for it separately.
- Opening or citing the owner's backup of the former configuration. The specs already record what it held, by role and date.

## Assumptions and constraints

- The plugin is not enabled: the live user settings file names no plugin, and this repository's agents (`reviewer`,
  `security-reviewer`) have no `skills:` lists. This was read on 2026-10-30.
- The inventory is the record of a state that ended on 2026-10-29. Its rows are edited only to say what became of a move; no row is
  rewritten as if it described a live configuration.
- The session-start test needs a new session in a project with the workbench's skills installed, and its outcome depends on the
  harness version, so the record names the version the owner reports. It can fail; a failure is recorded as a gap, not fixed here.
- Nothing tracked points to anything untracked: the decision record and the specs name no path in the owner's home directory.
- A decision record is written `Proposed`. The owner's level for `accept-decision` is read with `wb settings`; the plan does not accept
  the record on the owner's behalf.

## Completion criteria

1. In `global-config-inventory.md`, M10, M11 and M12 each say that the reset overtook them and that no carrying plan will be written,
   and `retire-superpowers-plugin` appears in the specs only in those notes, as history.
2. `superpowers-ports.md` records one run of the session-start test with its date, the harness version the owner reports, what was
   asked, and whether `brainstorm` loaded, and it no longer says only that the test "has not been run".
3. A decision record on routing outside the workbench exists as `Proposed` in `docs/decisions/` and in the index, with at least these
   options: none; the workbench adopted into the repository; a short user-level instruction file; the two guards alone (no automatic
   worktree, no merge or cleanup without approval). It states what each costs and names the owner's choice as open.
4. `wb check` and `wb run code-work check` report no problems, no file under `packages/` changed, and every change is committed
   locally with the trailer of its increment.

## Increments

### Increment A — Close M10 to M12 in the specs

**Outcome:** the specs say that the reset overtook the plugin's retirement, and none points to a plan that will not exist.
**Dependencies:** none.
**Affected areas:** `docs/specs/global-config-inventory.md` (the entries M10, M11 and M12 and the "Superpowers dependencies:
proposals" section's closing line, if it still says the owner can disable the plugin only after proposals 1 to 3);
`docs/specs/superpowers-ports.md` (the sentence that names the owner step, if any, and the status note).
**Steps:**
1. Search the specs for `retire-superpowers-plugin` and for "disable the plugin", and list every hit with its line.
2. For each of M10, M11 and M12, add one sentence after its text: overtaken on 2026-10-29 by the reset, which removed the plugin, the
   agent definitions and the routing text; no carrying plan will be written; the owner step is no longer outstanding. Keep the move's
   own text unchanged, as the inventory is a record.
3. Change the other hits so that none names `retire-superpowers-plugin` as a plan to come. Where a hit is the move's own "Carrying
   plan:" line, the note in step 2 is the change.
4. Run the search of step 1 again and check that each remaining hit is a note that says "overtaken".
**Verification:** the search of step 4; `wb check`; `wb run code-work check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-30-close-the-superpowers-retirement#A`.

### Increment B — Run the session-start test once

**Outcome:** the specs record what happens when a request for new behaviour arrives in a workbench project with no plugin.
**Dependencies:** A.
**Affected areas:** `docs/specs/superpowers-ports.md` (a short section, "The session-start test", and the row for
`using-superpowers`).
**Steps:**
1. Write the procedure into the spec: start a new session in a project that has `groundwork` and `code-work` installed and attached
   (this repository qualifies), with no plugin enabled; ask for a new behaviour in plain words, with no mention of a skill; note
   whether `brainstorm` is invoked before any code is written. Also run it once in a project with no workbench skills and note that
   nothing loads, which is the expected result and the cost of gap 1 of the decision in Increment C.
2. Stop and ask the owner to run both sessions and report: the harness version, the request they typed, and what loaded.
3. Record the owner's report, with the date, under the spec's new section. Do not edit the report into a pass: write what was said.
4. If `brainstorm` did not load in the workbench project, record that as a gap in the spec's inventory and list the follow-up in
   Deferred work; do not change a skill or a policy block here.
**Verification:** the new section holds the date, the version, the request and the result, each as the owner reported it; `wb check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-30-close-the-superpowers-retirement#B`.

### Increment C — Draft the decision on routing outside the workbench

**Outcome:** the owner has one `Proposed` record that lays out the choices for a repository with none of the workbench's skills.
**Dependencies:** B (its result says whether the policy block and the skill listing do the work inside a workbench project).
**Affected areas:** `docs/decisions/2026-10-30-routing-outside-the-workbench.md` (new) and its row in `docs/decisions/README.md`.
**Steps:**
1. Use the `draft-decision` skill. Read `docs/decisions/README.md` and search the decisions for a record on the same choice first; if
   one exists, stop and tell the owner.
2. Write the context: the old routing text and its two guards went with the reset (the specs record them by role and date), the
   workbench skills exist only in an attached project, and Increment B's result.
3. Write the options named in completion criterion 3, with what each costs: what an agent would do in a repository with no workbench,
   who maintains the text, whether it reaches the three harnesses or one, and what it leaves unguarded.
4. State the decision as open, with no recommendation hidden in the text; give the plan's own recommendation in a separate line if
   the owner asks for one.
5. Set the status to `Proposed`, add the index row, and stop for the owner. Do not accept it, and do not edit any user-level file.
**Verification:** `wb check` (it reports a wrong status and a missing index row); the record has every section of the template;
`wb run code-work check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-30-close-the-superpowers-retirement#C`.

## Verification for the plan as a whole

`wb check`; `wb run code-work check`; a search of the specs for `retire-superpowers-plugin` showing only notes that say "overtaken";
`git diff --stat` against the head before the plan showing no path under `packages/`; and `python3 -B -W error tests/run_all.py`, once,
because the specs are read by tests.

## Risks and sensitive actions

- The session-start test is run by the owner and its result is theirs; the plan records it and does not infer it. A failure is a real
  gap and the plan then ends with it listed, not fixed.
- The decision touches what an agent may do in repositories outside the workbench. Nothing in it is built here, and the owner's
  user-level files stay untouched.
- The inventory is a record of an ended state. An edit that rewrote a row as current would mislead; each change is a dated note.
- None of the increments changes a package, deletes a file or publishes anything.

## Review record

Empty until a review is asked for.

## Deferred work

- **`evaluate-findings` against the plugin's receiving-code-review:** ask before acting on a list with an unclear item, apply one item
  at a time and test each, check that a suggested feature is needed, no praise before verifying. A package edit, so a release.
- **`git diff --check`** in `verify-before-claiming`, as the old completion rule had it. A package edit, so a release.
- **A fresh implementer per increment** (`subagent-driven-development`), deferred by `2026-10-23-increment-loop-and-review-skills`.
- **`writing-skills`**, which matters when the `knowledge-base` module ships its own skills; **`dispatching-parallel-agents`**; and
  **`using-git-worktrees`**, left out on purpose by `safe-git.md`.
- **The wording of `workbench-v1#global-config-migration`**, which still lists the superpowers dependencies as items to settle, is the
  owner's roadmap edit.
- **The domain forms** of `test-first`, `diagnose-failure` and `verify-before-claiming`, which wait for a module with a domain.

## Result

### Increment A — M10 to M12 closed in the specs (committed as `7553b64`)

Changed: `docs/specs/global-config-inventory.md` only. M10, M11 and M12 each gain a dated note, "Overtaken, 2026-10-29": the reset
removed what the move would have edited, no carrying plan will be written, and the owner step is no longer outstanding. M11's note
says where the two guards and `git diff --check` are carried (the decision drafted in Increment C and this plan's deferred work), and
M12's says that its gate, the session-start test, is run by Increment B. The sentence in "Superpowers dependencies: proposals" that said
the owner can disable the plugin only after proposals 1 to 3 gains a history note. The moves' own text is unchanged.

Search as run: `retire-superpowers-plugin` appears three times in `docs/specs`, all in the moves' own "Carrying plan:" lines, each now
followed by an "Overtaken" note; no other spec names it. "Disable the plugin" appears in M12 (noted) and in the proposals section
(noted) and in the "After the reset" paragraph, which already says the proposals are history. `docs/specs/superpowers-ports.md` named
no owner step, so it was not changed; its sentence that the session-start reliance "has not been tested" is for Increment B.

Verification as run: `wb check` and `wb run code-work check` (74 plans): no problems. The whole `tests` root is for the plan as a
whole, after Increment C. No file under `packages/` changed.

Review: the `reviewer` agent, one exchange, no blocking finding. Applied: M11's and M12's notes no longer speak in the present tense of
work that is not done (M11 says the plan "picks up" the guards in the options of its decision and `git diff --check` in its deferred
work; M12 says "a corresponding test, in a real session with no plugin enabled" is Increment B's work and its result goes to
`superpowers-ports.md` once run) (1, 2). Recorded: the notes' claims about the reset are supported by `superpowers-ports.md` and the
inventory (3); the history note on proposal 5 reads correctly (4). The roadmap's wording about the superpowers dependencies is left
for the owner, as the plan's non-goals say. The reviewer could not run the checks or read a diff.

### Increment B — the session-start test (committed as `e6fb410`)

Changed: `docs/specs/superpowers-ports.md`: a new section "The session-start test" with the procedure, the four runs recorded in
the owner's words, the harness version, and a reading; the sentence in "What stops working" that said the reliance "has not been
tested" now points to the section; the reasoning for `using-superpowers` gains the finding. Also, outside the plan's listed areas,
one sentence of `docs/specs/global-config-inventory.md` ("After the reset") that said the reliance "is untested" now says it was
untested on 2026-10-29 and points to the runs. The owner ran the sessions, and nothing was changed to make a result pass.

Results as the owner reported them, 2026-10-30, with the harness version the owner reported once after all four runs, Claude Code
v2.1.314 (the owner did not say which run it belongs to, so it is not recorded per run): (1) a first run, "I did not see the brainstorm load, but it might have been my prompt", with the
project and request not reported: inconclusive; (2) in the owner's test project with the workbench's skills attached, "I want to add a
new command to this project that lists every plan with its status. Let's build it." did NOT invoke `brainstorm`: the agent read the
docs, then asked how to proceed with "Draft a plan (Recommended)" and "Brainstorm first" among the options (the pasted transcript
ends at the question and shows no file write); (3) in the same project, "I want to design a new feature" DID load `brainstorm`; (4) in
a non-project folder the same prompt: "the brainstorm skill did not load", which matches the expectation.

Reading, recorded in the spec: against the expectation (a request for new behaviour in a workbench project invokes `brainstorm`
before any file is written) the result is a gap. It is consistent with the wording of the request mattering, but the runs do not
isolate it (the requests differ in more than the verb, the second ended in a question to the owner, and each was run once), and they
do not show what the plugin did. It is recorded and not closed here, as the plan says. The spec's path for the owner's test project is
elided in the quote of the third run, so that no tracked text points to an untracked path. Because the plan's Deferred work is part of the approved text, the follow-up is
not added there: the owner can ask for a deferred-work entry, which needs a new approval, or take it into the decision of Increment C.

Verification as run: `wb check` and `wb run code-work check` (74 plans): no problems. No file under `packages/` changed.

Review: the `reviewer` agent, one exchange, no blocking finding. Applied: the owner's path to the test project is elided from the
quote of the third run (1); "nothing loaded, as expected" narrowed to what was reported, and the inference about the folder marked as
one (2); the reading no longer says the wording is the cause, no longer asserts what the plugin did, and says "not invoked when the
agent asked" and "no file write is shown" for the second run (3); the version is stated as reported once after all four runs (5);
the stale "is untested" sentence of the inventory (7). Checked against the owner's own messages: the quoted words and the transcript
details of the second run are verbatim (1, 4). Recorded: step 4 of the increment, to list the follow-up in Deferred work, is not done
because the plan is approved; the owner decides how it is carried (6).

### Increment C — the decision on routing outside the workbench (not yet committed)

Changed: `docs/decisions/2026-10-30-routing-outside-the-workbench.md` (new, `Proposed`). Nothing else: the decisions README has no
index table (it lists no record), so there was no row to add, which the plan's step 5 assumed. No file under `packages/` changed.

The record states the context (what the former user-level instruction file carried, by role and date; what a workbench project has and
another repository lacks; the floor decision `2026-10-24-project-guarantees-a-floor`; the owner's runs of 2026-10-30 and their limits),
four options each with what it costs (nothing at the user level; attach the workbench per repository; a short user-level instruction
file; only the two guards, as instruction or as permission rules), the consequences, and the evidence with its provenance. The
decision itself is stated as open: the owner has not chosen, and no recommendation is written into the record. Whether `brainstorm`
should be forced for new behaviour inside a workbench project is named as a separate question and is not decided there.

The record is `Proposed` and was not accepted. The owner's level for `accept-decision` is `ask`, so accepting it is the owner's
confirmation of the `groundwork accept` command with its digest, which has not been asked for.

Verification as run: `wb check` and `wb run code-work check` (74 plans): no problems; the record has the template's sections.

Review: the `reviewer` agent, one exchange, no blocking finding. Applied: option 1 no longer says the guards are held by the harness's
prompts (the specs do not say so) and says that no compiled floor applies outside the workbench; an invented preference ("what the
owner liked") and unsourced costs ("heavy for a throwaway repository") are gone; option 2 states the `brainstorm` gap observed inside
an attached project and no longer says "the tests cover" it; the advantage argued only for option 4 is removed and its cost says how a
harness treats such a rule is not tested; each option says which harnesses it reaches; the consequences and the evidence conclusion
are narrowed to the one plain-folder run; the version is stated as reported once after all the runs; and the record notes that the
floor decision rejected resetting the user level, which the owner has since done (1 to 7). The reviewer could not run the checks or
read the owner's messages.

Verification for the plan as a whole, as run: `wb check` and `wb run code-work check` (74 plans): no problems;
`python3 -B -W error tests/run_all.py`: 6251 tests in 13 roots, all OK; no file under `packages/` changed by this plan.

Completion criteria: (1) met: M10, M11 and M12 carry an "Overtaken, 2026-10-29" note and `retire-superpowers-plugin` appears only in
those moves' own lines, each followed by the note (Increment A); (2) met: `superpowers-ports.md` records the runs with date, the
harness version as reported once, the requests and what loaded (Increment B); (3) met: the record exists as `Proposed`, with the four
options and their costs and the choice open, and no row in the decisions index because the README has none (Increment C); (4) met:
the checks report no problems, no file under `packages/` changed, and each increment is committed with its trailer (C's commit is
the last).

After the commit of C, on 2026-10-30 the owner chose options 2 and 4 (attach the workbench per repository where the process is
wanted, and keep only the two guards at the user level) on the author's recommendation; the Decision section, the alternatives and the
consequences were written to say so while the record was still `Proposed`, and the owner accepted it through `groundwork accept` at
the level `ask`, with the previewed digest and the harness prompt: the status line reads "Accepted by" the owner's git identity on
2026-10-30, the level log has the pair `accept-decision ask` and `done accepted ... via ask`, and the decisions README has no index
row to update. That change is committed after C, not inside it.

Open for the owner: the wording or rules of the two user-level guards, which are the owner's to write; which repositories get the
workbench; whether the `brainstorm` gap needs a deferred-work entry, which needs a new approval of this plan; the roadmap
wording of `global-config-migration` about the superpowers dependencies; and the other deferred gaps (`evaluate-findings`,
`git diff --check`, a fresh implementer, `writing-skills`).
