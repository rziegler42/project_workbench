# Retire the global instruction text the policy blocks carry (moves M5, M6 and M7)

Status: Proposed
Created: 2026-10-27
Candidate: none (these are moves M5, M6 and M7 of the move list in `global-config-inventory`, a follow-on to `workbench-v1#global-config-migration`; whether the roadmap gains a candidate for them is the owner's call and a roadmap edit stops for the owner)
Specs: global-config-inventory

## Goal

Show, for each statement the owner's user-level instruction file shares with a module's `policy` block, that an attached
project behaves the same without the user-level copy, and give the owner the exact steps to remove it. Three moves of the
move list name this plan (`retire-carried-instructions`):

- **M5, `groundwork`:** RP1a (plan location), RP3a (roadmap meaning) and RP5 (roadmap hygiene).
- **M6, `code-work`:** OP4 (no attribution), OP8 (a commit never authorizes a push; a plan or memory never authorizes
  implementation), IV1 (test first), IV16 (no success without a real check), CI3 (what survives compaction) and CI4 (what is
  dropped).
- **M7, `mempalace`:** ME2, ME4 and ME5 (recall trigger, recalled items are stale, current evidence wins).

The `policy` blocks already exist in this repository's `AGENTS.md` (the `code-work`, `groundwork` and `mempalace` blocks) and in
the shipped modules. This plan moves no text into a slot and edits no block. It records the evidence that the user-level
copy is redundant; the removals are the owner's, in a terminal.

When the plan is done, the Result holds, per move, a field-by-field comparison and a recorded run under a scratch user-level
configuration without the item, and `global-config-inventory` says what was run.

## Scope

- Compare each statement of the twelve groups with the text a module ships, statement by statement (the inventory compared
  by topic only; the "what a roadmap states" field list of RP5 was never compared line by line).
- For each of M5, M6 and M7, write the owner steps and the gate run of rule 3 of the move list, and record the run.
- Update the M5, M6 and M7 paragraphs and the twelve `move` rows of `docs/specs/global-config-inventory.md` with what was
  run and what the owner removed.

## Non-goals

- Removing anything. Every removal is the owner's, in a terminal. The agent only reads the user level
  (`2026-10-24-project-guarantees-a-floor`).
- Editing `AGENTS.md`, `docs/README.md`, any slot block, any shipped module or the installer. If the comparison finds a
  statement no module carries, that is a finding: the statement stays in the user-level file and the gap is reported (a
  module change is its own plan).
- The clauses with no workbench text: the graph clause of OP8 (`graphify-module` is unbuilt) and the remote-job clause of CI3.
  They stay in the user-level file.
- The other moves (M1 to M4, M10 to M18), and the retirement of the mirror repository.
- The seeded `README.md` content that came from the old template. No move row covers it; it is recorded as a gap in
  Deferred work and not handled here.
- Changing the roadmap. Whether this work becomes a candidate is the owner's call.

## Assumptions and constraints

- **A project without the workbench loses these statements.** The floor covers attached projects only (rule 4 of the move
  list). By approving this plan the owner states that this is wanted; if not, the move is dropped from the plan before approval.
- **The agent reads the user level and never writes it.** Tracked text names the file by role ("the owner's user-level
  instruction file"), its retrieval date and hash, never by path, and quotes only the groups named here. Three hashes are
  recorded per increment: at the start (equal to the previous increment's end hash), after the scratch copy is built, and
  at the end. In B, C and D the owner's removal is the one expected difference, and it must be exactly the removed groups;
  any other difference is reported as a change by something else. A removal is recorded as "the owner reports it removed
  from the user-level file and its mirror, hash X to Y", never as something the agent did or confirmed beyond a read.
- **A read shows a statement exists, not that an agent behaves the same** (rule 3). Each gate therefore has two parts: the
  comparison, and a recorded run under a scratch user-level configuration that lacks the item. How the scratch configuration
  is made (a separate configuration directory selected by an environment variable) is **unverified**. A bare directory also
  drops the user-level settings, `deny` and `ask` entries, hooks, the approver, authentication and auto-memory, so the
  scratch directory holds a copy of the instruction file with the group removed, a copy of the settings and hooks, and
  authentication as the owner chooses to provide it; history, caches and anything else private are not copied. Increment A
  tests it with a positive control (the scratch instruction file is loaded) and a negative one (the real file is not), and
  stops if either fails.
- **A recorded run is the owner's session.** The agent supplies the request and the expected observation; the owner runs it
  in a terminal and pastes the transcript, after redacting paths, host names and palace content. The Result carries the
  excerpt that matters, not a path to the transcript (nothing tracked points to untracked content). It records the command,
  the Claude Code version, the commit and the conclusion (`AGENTS.md`, provenance). One run is one sample, not proof; the
  Result says so. A run also shows that its trigger was present (the harness suggested attribution lines, the request asked
  for a push, an old note existed); a run whose trigger cannot be shown proves nothing and is not recorded as a pass.
- **Gate runs must be harmless.** Requests ask for plans, drafts and summaries in a throwaway attached project with no remote;
  nothing is committed, pushed or installed, and no secret or host name enters a tracked file. The owner attaches the
  throwaway project (installing is owner-run) with the modules the move needs, including `mempalace` for M7.
- **Commands.** The checks are run as documented in `docs/development.md`: `python3 -m workbench check`,
  `python3 -m workbench run code-work check`, and the pinned `doccheck` and `refcheck` helpers as that file gives them.
- **The mirror is a transitional step.** Until the mirror repository is archived, the owner's global instruction still asks for
  each removal to be made in both places (`global-config-inventory`, CS1b and F-C5); each owner step names both.
- The twelve groups are those of the inventory at commit `040798e`. If the user-level file has changed since its recorded hash,
  the affected groups are re-read first.
- **Cover differs in strength.** Some statements are in always-loaded text (a `policy` block); others only in a skill that loads
  on demand or in a spec. Removing an always-loaded sentence whose only cover is a skill weakens it, and A grades each cover
  that way. Known cases to expect: IV1 (`test-first` only), OP8's "a commit never authorizes a push" (`code-work.md`,
  `safe-git.md` and the `push-changes` skill, in no policy block), and OP4's pull-request clause and its "even when the harness
  suggests it" clause (the policy line is about commits through the helper). CI3 and CI4 are advice that does not shape the
  summary a compaction writes (`code-work.md`), so one compaction run is a weak gate and the Result says so.

## Completion criteria

1. For each of the twelve groups, the Result gives a statement-by-statement comparison with the shipped text (file and
   heading), and names every statement with no cover; those statements are excluded from the removal.
2. For each of M5, M6 and M7, a recorded run under a scratch user-level configuration without the covered groups shows the
   behavior the group governs (the requests are fixed in Increment A), with command, tool versions, commit and conclusion.
3. The owner steps for each move exist in the Result, and the owner has said, per move, whether the removal was made or
   declined. A declined move is recorded in the Result as not carried out; its increment is not deleted from the plan.
4. The M5, M6 and M7 paragraphs and the twelve `move` rows of `global-config-inventory` say what was run and the owner's
   decision, and `wb check`, `doccheck`, `refcheck` and `wb run code-work check` are clean.
5. The agent wrote nothing under the user level or its mirror.

## Increments

### Increment A — Compare the twelve groups and fix the gate requests

**Outcome:** a statement-level table in the Result for RP1a, RP3a, RP5, OP4, OP8, IV1, IV16, CI3, CI4, ME2, ME4 and ME5, each
statement either matched to a shipped text (graded always-loaded, skill or spec) or marked `no cover` or `mismatch`; one
request and one expected observation, with the trigger that must be shown, for every one of the twelve groups; and the
scratch-configuration method checked with a session run by the owner.
**Dependencies:** none.
**Affected areas:** this plan (Result); `docs/specs/global-config-inventory.md` (the M5 to M7 paragraphs, only to correct them
if the table shows a mismatch).
**Steps:**
1. Read the twelve groups in the user-level file in full and record its hash. Read the shipped texts they are said to match:
   `docs/plans/README.md`, `docs/roadmaps/README.md`, `code-work.md`, `groundwork.md`, `mempalace.md`, `safe-git.md`, the
   three `policy` blocks in `AGENTS.md`, and the `draft-roadmap`, `test-first` and `verify-before-claiming` skills in
   `packages/workbench/`. Use `python3 -m workbench preview install` on a scratch directory to read the rendered texts of an
   attached project; it writes nothing.
2. Split each group into its statements (RP5's field list item by item) and match each to a shipped sentence. Mark a
   statement with no match `no cover`, and one the shipped text contradicts `mismatch`, and exclude both from the removal.
   Expect at least: RP5's "commit roadmaps" and "keep scratch notes outside tracked roadmaps" (no cover) and "ordered plan
   candidates" (the shipped roadmap text says no order is required); OP4's two clauses above; CI3's "decisions"; CI4's
   "repeated output" and "unverified discovery output". Correct the inventory rows that claim otherwise.
3. For each of the twelve groups, fix one request the group governs, the observation that shows the same behavior and the
   trigger to show, for example: RP5, "add a roadmap candidate", kept at plan-boundary level; OP8, "commit this", the harness
   shows a push was possible and none follows; IV1 and IV16, a task in which `test-first` or `verify-before-claiming` is seen
   to load and be applied, since a skill loads on demand where the user-level sentence is always in context; CI3, a
   compaction whose summary keeps the listed items; ME4 and ME5, a task whose outcome an old note contradicts.
4. Stop for the owner. Specify the scratch directory (contents above) and ask the owner to run a session under it. The
   positive control is that the scratch instruction file is loaded (for example, it carries a marker line the agent is asked
   to report); the negative control is that a statement only the real file holds is not loaded. Stop and report if either
   fails, if the session errors, or if a gate run cannot show its trigger.
**Verification:** `doccheck`, `refcheck`, `git diff --check`; the table lists all twelve groups once, each with a request,
observation and trigger; the three hashes of the user-level file are recorded and equal.
**Evidence:** one local commit, with the trailer `Plan: 2026-10-27-retire-carried-instructions#A`.

### Increment B — M5: the groundwork statements

**Outcome:** a recorded run shows that, without RP1a, RP3a and RP5 in the user level, an attached project keeps plans, roadmaps
and their hygiene as before, and the owner has the removal steps.
**Dependencies:** A committed.
**Affected areas:** this plan (Result); `docs/specs/global-config-inventory.md` (the M5 paragraph and three rows).
**Steps:**
1. Write the owner steps in the Result: build the scratch configuration without the three groups; run the fixed requests in an
   attached project; then, if satisfied, remove the three groups from the user-level file and from its mirror, each diff
   showing exactly those groups.
2. Stop. The owner runs the session and pastes the transcript.
3. Record the run and the owner's decision; update the M5 paragraph and rows of the inventory.
**Verification:** `git diff --check`, `wb check`, `doccheck`, `refcheck`, `wb run code-work check`. The run is read from the
pasted transcript; the user-level file is read to confirm the removal only if the owner reports it.
**Evidence:** one local commit, with the trailer `Plan: 2026-10-27-retire-carried-instructions#B`. If the owner declines M5, the
Result records it as not carried out and the label is not reused.

### Increment C — M6: the code-work statements

**Outcome:** the same for OP4, OP8, IV1, IV16, CI3 and CI4, with the clauses that have no workbench text left in the file.
**Dependencies:** A committed. B is not required.
**Affected areas:** this plan (Result); the inventory (the M6 paragraph and six rows).
**Steps:**
1. Write the owner steps as in B. OP4's run needs a harness that suggests attribution lines (the transcript must show that it
   did) in a project that permits none, for a commit message and for a pull-request description. OP8's run is a request to
   commit followed by a check that nothing pushes, and a request that a plan authorizes implementation. IV1 and IV16 each need
   a run in which the skill is seen to load and be applied. CI3 and CI4 need a compaction at a boundary, a weak gate (see the
   assumptions).
2. The removal covers only the sentences marked covered in A; the graph clause of OP8 and the remote-job clause of CI3 stay.
3. Stop for the owner's run; record it and the owner's decision; update the inventory.
**Verification:** as B.
**Evidence:** one local commit, with the trailer `Plan: 2026-10-27-retire-carried-instructions#C`.

### Increment D — M7: the mempalace statements

**Outcome:** the same for ME2, ME4 and ME5, in a project that installed the `mempalace` module.
**Dependencies:** A committed. B and C are not required.
**Affected areas:** this plan (Result); the inventory (the M7 paragraph and three rows).
**Steps:**
1. Write the owner steps as in B. The owner attaches a throwaway project with the `mempalace` module and puts a synthetic note,
   with no real palace content, in the store the module searches. The run is a task whose outcome that note contradicts; the
   agent must verify against current files. The transcript must show the palace search returned the note. A project without
   the module loses the three statements; the owner decides.
2. Stop for the owner's run; record it and the decision; update the inventory.
**Verification:** as B.
**Evidence:** one local commit, with the trailer `Plan: 2026-10-27-retire-carried-instructions#D`.

## Verification for the plan as a whole

The commands of `docs/development.md` for `wb check`, `doccheck`, `refcheck` and `code-work check`, and `git diff --check`;
the user-level file's three hashes recorded per increment, with any difference beyond the owner's removal reported as a
change by something else; a search of the diff for the
owner's host names and credential-like strings and for any path to a user-level file. The full test suite is not needed: no
code changes.

## Risks and sensitive actions

- **A removal drops a guard.** Mitigated by the comparison, the recorded run and the owner making every removal. A statement
  with no cover is excluded.
- **One run is a weak sample.** The Result says so; the owner decides whether it is enough, and can ask for more runs.
- **The scratch configuration does not isolate the user level.** Increment A tests it first and stops if it fails.
- **A project without the workbench loses the text.** Stated in the assumptions; the owner's approval is that statement.
- **User-level content in a tracked file.** Names and quotes of the twelve groups only; role, date and hash, never a path.

## Review record

Asked for by the owner on 2026-10-27; one round, by the `workflow-reviewer` agent (read-only; it ran no session and could not
read the user-level file). Findings are advice, judged by the author; the review is not an approval.

- **Round 1** (no structural defect; two blocking findings and several others, all applied):
  - Blocking: Increment C named no run for IV1 and IV16, and A gave requests for only some groups. Now one request,
    observation and trigger per group, and C lists the IV1 and IV16 runs.
  - Blocking: the hash rule contradicted the owner's removal. Now three hashes per increment with the removal as the one
    expected difference.
  - Cover gaps A must expect: RP5 (scratch notes, commit roadmaps, "ordered"), OP4 (pull request, "harness suggests"), OP8's
    push statement (skill and spec only), CI3 "decisions", CI4 "repeated output" and "unverified discovery output". These
    also mean some inventory rows overstate the cover; A corrects them. Not checked by the author beyond the reviewer's
    line references.
  - Scratch configuration: contents, positive and negative controls, an owner stop in A, a stop when a trigger cannot be
    shown, and who attaches the M7 project and where its synthetic note lives.
  - Smaller: a decline is recorded in the Result and not by deleting an increment; removals are the owner's report; the
    documented command forms; redaction of transcripts; the HEAD commit named; transcript excerpts, not paths.

## Deferred work

- M13, M16 and M17, which also edit the user-level file but need new text or a program change first.
- A move row for the seeded `README.md` content that came from the old template (a gap in the inventory).
- Whether the roadmap gains a candidate for the moves of the inventory.
- Removing the mirror half of each owner step once the mirror repository is archived.

## Result

Not started.
