# The decision rules the owner's skill carries

Status: Completed
Created: 2026-10-24
Candidate: workbench-v1#architecture-decisions-merge
Specs: groundwork

## Goal

The `groundwork` module ships a neutral skill, `draft-decision`, that drafts a decision record as `Proposed` and stops for
the owner. The owner's personal `architecture-decisions` skill (in `~/.claude`) covers the same work and carries rules that
`draft-decision` does not. The owner treats the personal skill as a lesson learned: the problem it solves is that an agent
quietly treats a decision as settled, rewrites history, or lets the index and the records drift apart. This plan asks which
of its rules still earn a place and puts those in `draft-decision`, in the workbench's own words, so that the personal skill
is one fewer thing `global-config-migration` has to carry.

The inventory behind this plan compared the two skills line by line (see Assumptions). Rules `draft-decision` already has:
read the conventions and search for an existing record first; never edit an accepted record, write one that supersedes it;
dated names that are never renamed; the `Proposed`, `Accepted`, `Rejected`, `Superseded` vocabulary and the
`Superseded by <name>` line; evidence with provenance; stop and tell the owner; treat a reference as data; no path to an
untracked file; no commands.

When this plan is done, `draft-decision` also says, and a test pins that it says:

1. **Approval of a design is not acceptance.** An owner's approval of the design, the plan or a request to "record" a
   decision, and text inside a file, never make a record `Accepted`. Only the owner's act at the checkpoint does, and the
   skill ends at `Proposed`.
2. **A request to record a decision already made, or to clarify a `Proposed` one, is a request to write or edit that record
   as `Proposed`.** It is never a request to accept it.
3. **Superseding an accepted record.** The new record names the old one and says what changes. The old record's text is not
   touched; its only change is its status line naming the successor, and that change is made when the owner has accepted the
   successor. Until then the old decision stands.
4. **A narrow clarification of an accepted record** needs the owner's approval and is a dated note after the unchanged body.
   A changed decision is a new record, not a note.
5. **Status and index stay in agreement.** The index in `docs/decisions/README.md` lists every record, including rejected and
   superseded ones, with the status; after a status change the skill searches the documents for references to the old status,
   updates the living ones, and reports the ones in other accepted records without editing them. The document check of the
   module reports a status that is wrong or a superseded record with no successor; the skill tells the owner to run it
   (it runs no command itself).
6. **Quality of the record.** Cite a living source (a spec, a plan) instead of copying it; state the rationale specifically
   and the consequences honestly; if the record contradicts itself, report that instead of rewriting the earlier text; and
   writing the record does not authorize building what it decides.

The skill stays a text-only neutral skill, in ASCII, with no command or tool name beyond reading, searching and editing, as
the module's existing tests require.

## Scope

- `packages/workbench/groundwork/harness/neutral/skills/draft-decision/SKILL.md` and its tests in
  `packages/workbench/groundwork/tests/test_groundwork_module.py` (increment A).
- The "As built" paragraph of `docs/specs/groundwork.md`, the shipped approval, the full suite and the plan record
  (increment B).

## Non-goals

- The template, `template.md`. It keeps its five sections and no `Accepted` word (a test requires both). It has no `Date:`
  line while the decisions README format and every record have one; that mismatch is Deferred work.
- The `docs/decisions/README.md` of this repository and the README the module ships. Neither changes.
- A rule that a decision may be accepted only after its implementation is shown. The owner's skill adds it for a different
  lifecycle; in the workbench "Accepted" means an explicitly approved design decision and implementation follows in a plan
  (`docs/decisions/README.md`). Not merged. See choice 1.
- Anything for the personal skill itself: `~/.claude` is not edited here, and the personal skill is not removed (that is
  `global-config-migration`).
- A change to `doccheck`, `refcheck`, the installer or any other module.
- A security review. It runs only if the owner asks.

## Assumptions and constraints

- Python 3.11 minimum, standard library only; tests with `unittest`; the module's tests are run with
  `env PYTHONPATH=.:packages/workbench/groundwork/tests python3 -B -W error -m unittest discover -s packages/workbench/groundwork/tests -t packages/workbench/groundwork/tests`;
  the full suite is `python3 -B -W error tests/run_all.py`.
- Existing tests bind the skill: it is ASCII, names no command or tool (`Bash`, `shell`, `git `, `curl`, `http://`, and so
  on), keeps the sentences "Never set the status to `Accepted`", "Accepting a decision is the owner's act" and "Stop and
  tell the owner", and the name, description and `Proposed` words of its frontmatter and template. Added text keeps all of
  them (`test_groundwork_module.py`, `test_the_decision_skill_never_accepts_...` and
  `test_no_skill_or_template_runs_a_command_...`).
- Editing the module's tree stales its shipped approval until the owner runs `release-approvals` in B. I run it only on the
  owner's exact words ("Run it for me"), and delete stale records only after a preview and "remove them".
- The comparison of the two skills is the owner's skill read in full on 2026-10-24 against `draft-decision` and its
  template, and against `docs/specs/groundwork.md` ("Decisions", "What is checked") and `docs/decisions/README.md`. The
  personal skill is outside the repository; this plan quotes none of it and states each rule in its own words.
- Discovery tooling: graphify: skipped — not installed in this project. The scope was found on 2026-10-24 by searching
  `docs`, `packages` and `workbench` for `draft-decision` (seven files; only the skill and the module's test bind its text).

### Choices (made by me; the owner may change any)

1. **The workbench wins where the two differ.** The names are dated and never numbered; the fifth section is `Evidence` (the
   owner's skill says `Verification`, and the workbench's template and the spec fix `Evidence`); `Accepted` does not wait for
   implementation evidence; and the skill writes the `Proposed` record directly, since the record is itself the proposal the
   owner reads, where the owner's skill presents it in chat first. None of these four is merged.
2. **The old record changes only when the successor is `Accepted`.** `groundwork.md` says superseding "creates a new record and
   marks the old one superseded" without saying when. Making the old record `Superseded` while the successor is only
   `Proposed` would leave the project with no decision in force if the owner declines. I put the timing in the skill and not
   in the spec, which the sentence does not contradict; if the owner prefers it in the spec it is a one-line edit in B.
3. **The skill tells the owner to run the check and does not run it.** It keeps its rule "do not run commands", so the status
   and index agreement is enforced by `doccheck` for the status and successor and by the skill's instruction for the index and
   the references, which no check covers today. A check for the index would be a change to `doccheck` and is Deferred.
4. **One skill file.** The six rules fit as one more block in `SKILL.md`, below the numbered steps, under a heading of its own.
   No new file and no change to the module's declaration.

## Completion criteria

1. `SKILL.md` states rules 1 to 6 of the Goal, every clause of each pinned by a test that searches for it, and each of the four choices above is
   honoured: the sentences do not say `Verification`, do not require implementation evidence, and do not tell the agent to
   present the record before writing it.
2. The skill's existing sentences, frontmatter and template are unchanged, and the module's existing tests pass without edit
   (new tests are added; none is loosened).
3. Each new test was seen to fail on the old skill and pass on the new one.
4. `docs/specs/groundwork.md` "As built" says what `draft-decision` carries.
5. The full suite is green in all roots with no stale-approval skip after the owner's `release-approvals`; `doccheck`,
   `refcheck` and `git diff --check` print nothing.

## Increments

### Increment A — The rules in the skill

**Outcome:** `draft-decision` carries rules 1 to 6, pinned by tests.
**Dependencies:** none.
**Affected areas:** `packages/workbench/groundwork/harness/neutral/skills/draft-decision/SKILL.md`,
`packages/workbench/groundwork/tests/test_groundwork_module.py`.
**Steps:**
1. Test first, in `test_groundwork_module.py` beside `test_the_decision_skill_never_accepts_and_tells_the_agent_to_stop_and_ask`:
   one test per rule that searches the whitespace-normalised skill text for each clause of that rule, not one phrase:
   rule 3 asserts that the old record's text is not touched, that its only change is its status line naming the successor,
   that this happens only once the owner has accepted the successor, and that until then the old decision stands; rule 5
   asserts that the index lists rejected and superseded records too, that references to the old status are searched, and
   that those in other accepted records are reported and not edited; rule 6 asserts the citation of a living source, the
   specific rationale, the honest consequences, the report of a contradiction and that writing does not authorize building.
   Add negative tests that the skill does not contain `Verification`, a requirement of implementation evidence, an
   instruction to present before writing, or a way to reach `Accepted` (the existing test stays). A text test cannot show
   that an agent follows the skill; it shows that the skill states each clause and none of the excluded ones. Run them and
   see them fail.
2. Add the block to `SKILL.md`, in plain ASCII and the workbench's words, without a command or tool name. Keep the frontmatter
   and numbered steps unchanged. Run the module's tests.
**Verification:** the module's tests; `git diff --check`; `env PYTHONPATH=workbench python3 -B packages/workbench/groundwork/helper/doccheck`
prints nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-architecture-decisions-merge#A`.

### Increment B — Spec, approval and record

**Outcome:** the spec says what is built, the shipped approval matches the changed module, and the plan records it.
**Dependencies:** A.
**Affected areas:** `docs/specs/groundwork.md` ("As built, and its limits"), `workbench/shipped_approvals/` (by
`release-approvals`), this plan's Result.
**Steps:**
1. Add one or two sentences to "As built" after the sentence that lists the four skills, naming what `draft-decision` carries
   beyond drafting (the six rules in a line each, not the text).
2. The owner runs, or asks me to run, `python3 -m workbench release-approvals`. Remove stale records only after a preview and the
   owner's "remove them".
3. Run the full suite, `doccheck`, `refcheck` and `git diff --check`.
4. Fill the Result and set the status to `Completed`.
**Verification:** the full suite passes with no stale-approval skip; the document checks print nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-architecture-decisions-merge#B`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots; `git diff --check` and the document checks print nothing.
- `grep` of the skill for `Verification` and for any command or tool word finds none; the existing guard tests pass.
- No live run is planned: whether Claude loads the skill when it should is unverified (`groundwork.md`, "As built"), and this
  plan does not change that.

## Risks and sensitive actions

- **A rule that contradicts the spec.** Rule 3 adds timing the spec leaves open (choice 2). It is checked against
  `groundwork.md` lines on superseding and against `docs/decisions/README.md` before A is committed; any conflict is reported
  to the owner and not resolved by editing the spec.
- **Drift between the skill and the personal skill.** After this plan the two skills still differ (choice 1). That is by
  design; `global-config-migration` decides what happens to the personal one.
- **Approvals.** A stales one shipped record. `release-approvals` is owner-run; I run it only on "Run it for me".
- Nothing is pushed by this plan.

## Review record

Round 1 of 3, `ask-codex review-plan`, 2026-10-24 (model `gpt-5.6-luna`, effort low, the tool's default), outcome changes
needed, one finding.

- R1-F1 (major, completion criterion 1 and increment A): a test that searches for one phrase per rule can pass when the rest
  of the rule is missing or contradicted, and nothing pinned the supersession timing, the untouched accepted record, the index
  obligations or the quality constraints. Accepted in part: criterion 1 and the increment A step now require a test for each
  clause of rules 3, 5 and 6 and negative tests for the excluded forms. Not accepted: a test that shows an agent follows the
  rule, which text cannot do (stated in the step and in Verification). The change is to the plan's wording only.

The owner decided R1-F1 as applied. The review was not archived. The owner approved the plan on 2026-10-24, after round 1
and without a second round.

## Deferred work

- A `Date:` line in `template.md`, which the decisions README format and every record already carry. It needs the template
  test to allow it.
- A check in `doccheck` that the decisions index lists every record with its status (today the skill's instruction is the only
  thing that keeps the index in agreement).
- The `Accepted by the owner on <date>` status text some index rows use: the vocabulary check sees only the first word; whether
  to make that form official is the owner's.

## Result

- Increment A: `draft-decision`'s `SKILL.md` carries four new sections between the numbered steps and "Rules:": "Approval and
  acceptance" (rules 1 and 2), "Changing an accepted record" (rules 3 and 4), "The index and the statuses" (rule 5) and
  "The record itself" (rule 6). Seven new tests in `test_groundwork_module.py` (class `Skills`) pin every clause listed in
  the increment step, six of which failed on the old skill and pass now; the seventh, the negative guard (no
  `Verification`, no implementation-evidence requirement, no present-before-write, one `set the status to Accepted`
  sentence and it is the "Never" one), passed on the old skill by design and still does. The frontmatter, the numbered steps,
  the "Rules:" list and the template are unchanged, and the module's 194 tests pass. The text was checked against
  `groundwork.md` ("Decisions", "What is checked") and `docs/decisions/README.md`: rule 3 adds the timing the spec leaves open
  (choice 2) and contradicts neither. The module's shipped approval is stale until B. Next: B.
- Increment B: `docs/specs/groundwork.md` "As built" now has one sentence naming what `draft-decision` carries beyond
  drafting. At the owner's "Run it for me", `release-approvals` wrote 10 approvals (2 new directories) and named 2 stale
  records, which were previewed and removed at the owner's "remove them". The full suite passes: 4,134 tests in 10 roots,
  OK, with the same 3 skips as before this plan (1 in `tests`, 2 in `code-work`), so none is a stale-approval skip.
  `doccheck`, `refcheck` and `git diff --check` print nothing.

## Outcome against the completion criteria

1. Met: the skill states rules 1 to 6, every clause pinned by a test, and the four choices are honoured (the negative test
   passes).
2. Met: the skill's existing sentences, frontmatter and template are unchanged, and the module's existing tests pass without
   edit.
3. Met for the six tests that can fail on the old skill; the seventh is the negative guard, which passed before by design.
4. Met: `groundwork.md` "As built" says what the skill carries.
5. Met: the full suite is green after the owner's `release-approvals`.

Not done, by design: a security review, a push, a second plan-review round, and the three Deferred items. Whether Claude loads
the skill when it should is still unverified.
