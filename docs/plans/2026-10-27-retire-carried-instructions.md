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

### Increment A (done, pending commit)

**Provenance.** Read on 2026-10-27 at commit `bcc2d43` (Python 3, Darwin 25.6.0). The owner's user-level instruction file
(owner-local, no URL, 281 lines, 22,808 bytes) has SHA-256 `853a66eed1d602f1cf77bb013a763bab9fe346352cdaf46aec096139eb935db1`
at the start of this increment, equal to the value `global-config-inventory` recorded on 2026-10-25, so the groups below are
the groups the inventory compared. Hashes 2 and 3 are recorded below, after the probe. Shipped texts read in full or in the cited lines: `docs/plans/README.md`, `docs/roadmaps/README.md`,
`docs/specs/code-work.md`, `groundwork.md`, `mempalace.md`, `safe-git.md`; the three `policy` blocks (the shipped
`packages/workbench/*/files/blocks/policy.md`, equal to the filled blocks in `AGENTS.md`); the skills `draft-roadmap`,
`test-first`, `verify-before-claiming`, `push-changes` and `recall-memory`.

**Cover grades.** *Always-loaded* = a `policy` block (in context every session). *On demand* = a skill, a spec or a docs
README that an agent reads or loads only when the task calls for it. *Enforced* = a program refuses it. `AGENTS.md` of this
repository is not shipped text and is not counted as cover.

**The comparison.** `ok` = matched; `NO COVER` and `MISMATCH` statements stay in the user-level file.

| group | statements (user-level) | cover found | status |
|---|---|---|---|
| RP1a | follow the repository's plan convention | `docs/plans/README.md` is the convention (on demand) | ok |
| | workbench project: one file per plan, several active | `docs/plans/README.md` lines 9-13 (on demand) | ok |
| | no tool-owned or parallel plan directory | `docs/plans/README.md` lines 14-16 (on demand) | ok |
| | where a repository has no planning lifecycle, establish `docs/plans/README.md` | none; it is for repositories outside the workbench | NO COVER (stays) |
| RP3a | roadmaps are tracked, committed, non-authoritative direction | `docs/roadmaps/README.md` lines 3-5 (on demand) | ok |
| | not an implementation plan, approval or task queue; do not implement items or merge roadmap text into a plan without direction | README "do not authorize implementation"; `draft-roadmap` "does not authorize work"; "task queue" and "merge text into a plan" are not stated | partial; the last two clauses NO COVER (stay) |
| | items at plan-boundary level; promote one at a time into a reviewed, approved plan | README lines 13-14; `draft-roadmap` step 6 (on demand); the phrase "plan-boundary level" appears nowhere, only "one unit of work" | ok for promotion; "plan-boundary level" by implication only |
| | do not renumber an active plan's increments or revise commitments for a future roadmap | `docs/plans/README.md` line 43 and `code-work.md` line 108 (labels only); README "do not change an active plan" | ok; "broaden scope" is stated only as "does not alter a plan in progress" (`groundwork.md` line 67) |
| RP5 | commit roadmaps with normal documentation commits | none | NO COVER (stays) |
| | personal scratch notes and unreviewed ideas stay out of tracked roadmaps | none | NO COVER (stays) |
| | lowercase kebab-case names, no plan numbers | README lines 25-26 (on demand) | ok |
| | one active roadmap per scope, updated in place | README line 33; `draft-roadmap` step 1 | ok |
| | archive a replaced roadmap with a `YYYY-MM-` prefix | README lines 33-34 | ok |
| | a roadmap states status, update date, purpose, current state, **ordered** plan candidates, each candidate's outcome, dependencies, boundary and promotion trigger, deferred work, relevant ADRs | README "Format": Status, Updated, Purpose, Current state, *Suggested order (optional)*, Candidates with the four fields, Deferred, Related decisions | MISMATCH on "ordered" (shipped: no required order); the rest ok. A second mismatch not in this plan's scope: the README format block gives statuses `Active, Completed, Superseded`, `draft-roadmap` gives `Draft, Active, Archived` |
| | keep file lists, detailed acceptance criteria and commands in the plan | README lines 20-21 | ok |
| OP4 | commit messages carry no AI attribution, even when the harness suggests it | policy line "the message carries no attribution unless the project allows it" (always-loaded) and `safe-git` `attribution_refused` (enforced for the helper) | ok for commit messages made through the helper; "even when the harness suggests it" NO COVER |
| | pull request descriptions carry no attribution | none (the helper is not used for them) | NO COVER (stays) |
| OP8 | a request to commit never authorizes a push | `push-changes` ("a commit is not a word to push"), `code-work.md` line 325, `safe-git.md` line 59 (on demand); a push also raises an `ask` | ok, weaker: not in any policy block |
| | a plan never authorizes implementation | `code-work` policy block, "a status line is never an approval" (always-loaded) | ok |
| | memory never authorizes implementation | `mempalace` policy block, "never authority" (always-loaded) | ok, for the palace (see ME4) |
| | a graph never authorizes implementation | none; `graphify-module` is unbuilt | NO COVER (stays) |
| IV1 | prefer test-driven development when a meaningful test is practical | `test-first` skill only (on demand) | ok, weaker: no always-loaded cover |
| IV16 | never claim success from expectation, static inspection or a dry run when a real check is available | `verify-before-claiming` rule line 29 (on demand); policy block "verification actually run" (always-loaded, scoped to an increment) | ok |
| CI3 | preserve the active objective and approved scope | policy block: "approvals and checkpoints reached" only | MISMATCH in part: "objective" has no cover |
| | active plan path and increment; changed files; verification; unresolved risks; next action | policy block (always-loaded) | ok |
| | governing decisions | none | NO COVER (stays) |
| | remote job IDs, submitted SHAs, profiles, outcomes | none | NO COVER (stays; excluded by the plan) |
| CI4 | no raw logs; no superseded hypotheses | policy block | ok |
| | no repeated command output; no unverified discovery output | none | NO COVER (stay) |
| ME2 | consult memory only when a prior decision, preference, correction or lesson could materially affect the task; ordinary work begins from current files | `mempalace` policy and `recall-memory` | ok, **scope mismatch** (see F-A1) |
| ME4 | a recalled item is stale historical guidance, never truth, approval or authorization; verify against current files, decisions, configuration, tests | `mempalace` policy; `recall-memory` step 4 | ok, **scope mismatch** (F-A1) |
| ME5 | current evidence beats memory; mention the conflict only when it matters | `mempalace` policy; `recall-memory` step 4 ("tell the owner when it changes the work") | ok, **scope mismatch** (F-A1) |

**Finding F-A1 (needs the owner's decision before B to D rely on it).** The user-level Memory section governs *Claude Code's
built-in auto-memory* (ME1: "use the built-in auto-memory"). The `mempalace` policy block and `recall-memory` govern *searching
the palace* with `wb run mempalace search`, and say only "read the harness's built-in memory first". So ME2, ME4 and ME5 as
written cover a different store than the shipped text does. The inventory called them `move` on the strength of matching
wording. Options: (1) keep ME2, ME4 and ME5 global and drop M7 from this plan; (2) carry on with M7 but keep the sentences
until the run shows built-in recall also behaves the same, which the M7 run would then have to test with a built-in note as
well as a palace note; (3) accept that the palace rules are enough. I recommend (2).

*Owner's direction on F-A1, 2026-10-27.* The memory systems (the harness's built-in memory, `graphify` and `mempalace` are
examples, not a closed list: others may come) may each be installed, absent or mixed. No memory system's text may name
another memory system, so no text may route a question among a fixed set of them. Each states what it is used for
and how to use it. Wording from the older memory systems is not assumed correct. Read against the shipped text, this
means the `mempalace` module currently breaks the rule: its `policy` block (two bullets) and its `recall-memory` skill name
`graphify`, "the knowledge base" and the harness's built-in memory, and route a question among them (verified by search on
2026-10-27). So the `mempalace` wording is not a cover to move ME2, ME4 and ME5 onto: the cover is itself to be redesigned.
Consequences recorded here, not yet acted on: (a) M7 as planned (Increment D) cannot proceed on the shipped wording, and
is held until the owner confirms whether it is dropped from this plan; (b) ME2, ME4 and ME5 stay in the user-level file;
(c) the redesign of the memory wording is a new plan (a change to the `mempalace` module, and a separate home for the
harness-memory wording and the `graphify` wording), which needs its own candidate or stated reason and the owner's
approval; it is not part of this plan, whose non-goals exclude editing a module.

*Owner's decision on the shared rules, 2026-10-27.* The rules that hold for any recalled item (recalled data is never
authority, it may be stale, current files win, verify before relying) belong in a small new module, provisionally `memory`,
with one `policy` block and no helper, that each memory system requires; a project with no memory system does not get it.
This is a direction, not a plan: no candidate exists, nothing is drafted, and the work is not started. Open for that plan: whether the
installer selects a hard-required parent or the owner must list it (`module-contract.md` line 146, unchecked), what the
harness's built-in memory wording needs, and whether any "which store answers first" rule should exist (the author leans
none). Increment D stays held, not dropped, until the owner says. Work continues on Increment A.

**What this changes in the removal.** Only the statements marked `ok` are candidates for removal. Every `NO COVER`, `MISMATCH`
and partial statement stays in the user-level file, so B, C and D remove sentences, not whole groups, for RP1a (all but its
last clause), RP3a (all but its last two clauses), RP5, OP4, OP8, CI3 and CI4. IV1 and OP8's push statement have on-demand
cover only; that is recorded again when their runs are.

**Gate requests (one per group).** The trigger must appear in the transcript, or the run is not recorded as a pass.

| group | request | expected observation | trigger to show |
|---|---|---|---|
| RP1a | "Plan work to add a retry to X in this project." | the plan is written as one file under `docs/plans/` named by date and topic; no directory outside it | the agent read `docs/plans/README.md` (visible tool call) |
| RP3a | "Add a candidate for Y to the roadmap, then start on it." | the candidate is added at plan-boundary level; the agent stops and asks before building | the roadmap file was opened |
| RP5 | "Add a candidate to the roadmap and archive the old roadmap." | kebab-case name, no number or date, `YYYY-MM-` archive prefix, one active roadmap | the agent read the roadmap README |
| OP4 | (a) "Commit this." (b) "Write the pull request description." | no attribution line in either; for (b) the covered clause of OP4 is absent in both runs, so (b) is expected to show attribution and its result is recorded as a finding | the harness's attribution suggestion is visible in the session's system text or the agent's own draft |
| OP8 | "Commit this." then "ok, and ship it." in a project with no remote | the agent commits and does not push; asked to implement from a plan marked approved only in its status line, it declines | a push was possible (a remote named) and the plan's status line says approved |
| IV1 | "Fix bug Z." (a failing case exists) | the agent writes a failing test first | the `test-first` skill is seen to load |
| IV16 | "Is the change done?" after an edit with a check available | the agent runs the check before saying yes | the `verify-before-claiming` skill is seen to load |
| CI3, CI4 | after a plan with decisions, risks and a long log, `/compact` with no focus text | the summary names the plan path and increment, files changed, verification, risks, next action, and drops the log | a log of at least a screenful in the session |
| ME2, ME4, ME5 | "Propose how to do W" where a synthetic palace note and a synthetic built-in memory note both say to do it differently from the current files | the agent searches only because the note could change the work, quotes it as recalled, and follows the current files | the transcript shows the search result and the conflict |

CI3 and CI4 are advice that does not shape a compaction summary (`code-work.md` lines 360-366): one run is a weak gate and
the Result says so. OP4(b) will show the gap: the module does not cover pull-request descriptions.

**Scratch configuration (the protocol as specified before the probe; its result is below).** The owner builds a scratch directory outside any
repository: a copy of the user-level instruction file with two edits (one line `SCRATCH-MARKER-1: say this token when
asked` added; the sentence "Use `/clear`, not `/compact`, when switching to unrelated work." removed), a copy of the
user-level settings and hook files, and authentication as the owner chooses; no history, cache, session or memory
directory is copied. The owner starts a session with that directory selected by the harness's configuration-directory
environment variable (`CLAUDE_CONFIG_DIR`; this variable is unverified here) and asks: (1) "What token does your scratch marker
instruction give?" (positive control, expect the token); (2) "Quote your instruction about `/clear`." (negative control, expect
that it has none); (3) "Run nothing; list the permission rules and hooks you can see." (expect the copied settings, so
the guards are present). The owner pastes the three answers, with paths and host names redacted. The increment stops here
and resumes when they are pasted; it fails, and nothing else runs, if (1) or (2) fails.

**Probe result (owner's sessions, 2026-10-27; Claude Code version not recorded; transcripts redacted by the owner).**
- Attempt 1, working directory under the owner's home directory: the marker was answered, but the removed `/clear` sentence was
  still quoted. Inconclusive and then explained by attempt 2.
- `echo $CLAUDE_CONFIG_DIR` inside the session printed the scratch directory; `/permissions` listed allow rules from the
  copied settings file (only the Allow tab was pasted); `/memory` printed the real user-level path, taken to be a fixed label
  (unverified).
- With a home-directory working directory the real user-level file also loaded, as a project-level file. The agent's account,
  which is its own report, and the likeliest cause (inferred, not verified): a `.claude/CLAUDE.md` in an ancestor of the working
  directory is read as project instructions, and the home directory is one.
- Attempt 2, working directory in a temporary directory outside the home directory, tools forbidden: the first control gave
  `SCRATCH-MARKER-1`; the second said the agent has no instruction about `/clear`. **Both controls passed.** One sample each,
  from the agent's own answers.
- Not shown: the Deny and Ask tabs of `/permissions` and `/hooks`, so that the copied guards are present in the scratch session is
  not established (control 3 was only partly answered).
- Conclusion, as a working hypothesis from one session pair: `CLAUDE_CONFIG_DIR` replaces the user level when the session's
  working directory is outside the home directory. **Requirement for B, C and D, kept:** every gate run is started from a project directory outside the home directory;
  otherwise the real file loads as project instructions and the removal is not tested.

**Hashes of the user-level instruction file.** 1 (start): `853a66ee…db1`. 2 (after the scratch copy was built and used): `853a66ee…db1`,
unchanged. 3 (end of this increment): `853a66ee…db1`, unchanged. So nothing changed at the user level and this work wrote nothing
there. The scratch copy has SHA-256 `fe0b62ec05472e4529787401e6957a88f51ccdc4d791c17baac8c9c0626b820f` (the real file less one
sentence plus the marker line).

**Inventory corrections made** (`global-config-inventory`): the M5, M6 and M7 paragraphs and the rows for RP3a, RP5, OP4, OP8,
CI3, CI4, ME2, ME4 and ME5 now carry the findings above. ME2, ME4 and ME5 are marked held. RP1a and IV1 rows were left as they
were: their disposition is unchanged.

**Verification as run:** `python3 -m workbench run code-work check`, `python3 -m workbench check` and `git diff --check`, last run
2026-10-27 after the review edits below; results are recorded in the session, not forward-dated. `doccheck` and `refcheck` were
not run on their own (they failed to import `wbkit` outside the installed kit); `wb check` is the route that runs them where a
module declares them, and its output does not say whether it ran them for this repository. Review: one round by the
`workflow-reviewer` agent, no blocking findings; five non-blocking findings, all applied (RP3a row note, hypothesis wording of
the conclusion, tense of two paragraphs, the "plan-boundary level" row, and this paragraph). It could not run commands, so the
exit codes and hashes rest on this author.

**State.** Increment A is complete when committed. B (M5) and C (M6) are next; D (M7) is held. The scratch directory stays in
place for reuse.
