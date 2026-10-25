# Project scoping in the mempalace skill and policy

Status: In Progress
Created: 2026-10-24
Candidate: workbench-v1#mempalace-scoping
Specs: mempalace

## Goal

The `mempalace` module's `recall-memory` skill and its policy block tell an agent when to search the owner's palace and
that a result is data. They do not say three things the owner's global memory rules say, and the gap matters because one
palace can hold notes from many projects:

- A search returns the nearest notes whatever project they were filed for. Nothing tells the agent that a note from another
  project or wing is background and not a fact about this project.
- Both texts say "a memory" ("an agent cannot file or change a memory", "whether a memory exists at all"), which blurs the
  palace with the harness's own built-in memory, a different store that an agent may still write where the owner allows it.
- When both stores could answer one question, nothing says which is consulted first.

When this plan is done, the skill and the policy block say, and tests pin that they say:

1. **Another project's result is background.** A result counts as about this project only when its wing or its source file
   names this project. Any other result, including one with no wing or an unclear source, is background: it is not a fact
   about this project, and the agent says which wing it came from when it quotes it.
2. **"The palace", not "a memory".** Both texts say "the palace" for the store they search. The sentence about filing says
   an agent cannot add to or change the palace, and adds that writing the harness's built-in memory is a separate act the
   owner may allow, which these texts neither grant nor forbid.
3. **Order of the stores.** For a question both could answer, the harness's built-in memory is read first, because it is
   already scoped to this project and loaded, and the palace is searched only when it does not answer. This is choice 1
   below and is the owner's to confirm.

The texts stay neutral: no harness name, no new command, ASCII, and the block stays within its existing 14-line limit.

## Scope

- `packages/workbench/mempalace/harness/neutral/skills/recall-memory/SKILL.md`,
  `packages/workbench/mempalace/files/blocks/policy.md` and
  `packages/workbench/mempalace/tests/test_mempalace_guidance.py` (increment A).
- The "policy block and the skill" list of `docs/specs/mempalace.md`, the shipped approval, the full suite and this plan's
  record (increment B).

## Non-goals

- A default wing per project, a helper change, a new option or a change to what `search` passes. The roadmap names it as a
  larger change that is not part of this.
- A change to the helper `mempalace`, its tests other than `test_mempalace_guidance.py`, or any other module.
- Anything in `~/.claude` or the owner's global memory rules, which this plan reads but does not edit.
- Deciding how an agent writes the built-in memory; the plan only says the palace is a different store.
- A security review. It runs only if the owner asks.

## Assumptions and constraints

- Python 3.11 minimum, standard library only; the module's tests run with
  `env PYTHONPATH=.:packages/workbench/mempalace/tests python3 -B -W error -m unittest discover -s packages/workbench/mempalace/tests -t packages/workbench/mempalace/tests`;
  the full suite is `python3 -B -W error tests/run_all.py`.
- Existing tests bind both texts: no harness name (`Claude`, `claude`, `opencode`, `Codex`, `CLAUDE.md`, `AGENTS.md`), no
  path, the only commands `wb run mempalace search` (and `status` in the skill), a block of at most 14 lines, front matter
  of a name and a description only, and the routing sentences. The sentences "An agent cannot file or change a memory" and
  "whether a memory exists at all" are asserted by the test file today, so choice 2 changes those tests as well; every other
  existing assertion stays.
- Editing the module's tree stales its shipped approval until the owner runs `release-approvals` in B. I run it only on the
  owner's exact words ("Run it for me"), and delete stale records only after a preview and "remove them".
- `docs/specs/knowledge-tools.md` (Non-goals and the paragraph on the owner's global instruction) records that the harness's
  built-in memory is the default and that installing the `mempalace` module is the owner's request for the palace. It does
  not say which store is read first; that order is choice 1, which is mine and which the owner confirms by approving this
  plan.
- Discovery tooling: graphify: skipped - not installed in this project. The scope was found on 2026-10-24 by searching
  `docs/` and `packages/` for `mempalace-scoping` and for "a memory" (the skill, the block and their test file).

### Choices (made by me; the owner may change any)

1. **The built-in memory answers first.** It is already loaded and scoped to the project, a search costs a command and
   can return another project's notes, and the owner's global rule makes it the default. The alternative, the palace first,
   would search on every overlapping question. I chose built-in first and the palace when that does not answer.
2. **Both texts change wording, the tests follow.** "A memory" becomes "the palace" in the skill, the block and the two
   assertions that carry it, so the tests change with the text and not around it. This is the one place existing assertions
   are edited; each edited assertion is replaced by the new wording, not loosened.
3. **Scoping is by what a result says, not by a filter.** The agent already may pass `--wing`; the texts say to narrow with
   it when the wing for this project is known. A result is about this project only when its wing or source file names this
   project; an unlabeled or ambiguous one is background. The helper has no default wing (that is the larger change), so
   the texts do not name one.
4. **No new file.** The rules fit in the two files that exist.

## Completion criteria

1. The skill states rules 1 to 3 of the Goal and the block states the same three in fewer words, every clause pinned by a
   test that searches for it, and the choices above are honoured.
2. Neither text contains "a memory" for the palace; negative tests show the old phrases are gone and that the texts still
   name no harness and no command beyond `search` and `status`.
3. Each new or edited test was seen to fail on the old text and pass on the new one.
4. `docs/specs/mempalace.md` "The policy block and the skill" lists the three rules.
5. The full suite is green in all roots with no stale-approval skip after the owner's `release-approvals`; `doccheck`,
   `refcheck` and `git diff --check` print nothing.

## Increments

### Increment A - The three rules in the skill and the block

**Outcome:** both texts carry rules 1 to 3, pinned by tests.
**Dependencies:** none.
**Affected areas:** `packages/workbench/mempalace/harness/neutral/skills/recall-memory/SKILL.md`,
`packages/workbench/mempalace/files/blocks/policy.md`, `packages/workbench/mempalace/tests/test_mempalace_guidance.py`.
**Steps:**
1. Test first in `test_mempalace_guidance.py`: one test per rule for the block and one for the skill, each searching the
   whitespace-normalised text for every clause (rule 1: a result from another project or wing is background, not a fact
   about this project, and the wing is named when quoting; rule 2: "the palace" is used, an agent cannot add to or change
   the palace, the built-in memory is a separate store; rule 3: the built-in memory is read first, the palace only when it
   does not answer). Replace the two assertions on "a memory" with the new wording. Add negative tests: neither text says
   "a memory" for the palace, names a harness, adds a command, or exceeds 14 lines in the block. Run them and see them fail.
2. Edit `SKILL.md` and `policy.md` in plain ASCII and the workbench's words. Keep the front matter, the numbered steps, the
   routing sentences and the refusal rules. Run the module's tests.
**Verification:** the module's tests; `git diff --check`; `env PYTHONPATH=workbench python3 -B packages/workbench/groundwork/helper/doccheck`
prints nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-mempalace-scoping#A`.

### Increment B - Spec, approval and record

**Outcome:** the spec lists the three rules, the shipped approval matches the changed module, and the plan records it.
**Dependencies:** A.
**Affected areas:** `docs/specs/mempalace.md` ("The policy block and the skill"), `workbench/shipped_approvals/` (by
`release-approvals`), this plan's Result.
**Steps:**
1. Add the three rules as list items after the existing five in the spec.
2. The owner runs, or asks me to run, `python3 -m workbench release-approvals`. Remove stale records only after a preview and
   the owner's "remove them".
3. Run the full suite, `doccheck`, `refcheck` and `git diff --check`.
4. Fill the Result and set the status to `Completed`.
**Verification:** the full suite passes with no stale-approval skip; the document checks print nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-mempalace-scoping#B`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots; `git diff --check` and the document checks print nothing.
- `grep` of the skill and the block for "a memory" finds none; the existing guard tests pass.
- No live run is planned: whether Claude loads the skill when it should, and whether it follows the order of stores, is
  unverified. Text tests show the texts state the rules, not that an agent obeys them.

## Risks and sensitive actions

- **A rule the owner's global rules would phrase differently.** Choice 1 fixes an order the roadmap leaves open. It is
  stated as mine for the owner to confirm before approval.
- **Tests that bind the old wording.** Two assertions change (choice 2); the rest of the file is untouched.
- **Approvals.** A stales one shipped record. `release-approvals` is owner-run; I run it only on "Run it for me".
- Nothing is pushed by this plan.

## Review record

Round 1 of 3, `ask-codex review-plan`, 2026-10-25 (model `gpt-5.6-luna`, effort medium), outcome changes needed, two findings.

- R1-F1 (major, Assumptions and Choices): the store order was supported by an instruction read from the session, not a
  tracked source. Accepted: the assumption now cites `docs/specs/knowledge-tools.md`, says that spec does not give the order,
  and says the owner confirms choice 1 by approving. The owner decided R1-F1 as applied.
- R1-F2 (minor, Goal and choice 3): no rule said how a result is judged to be about this project. Accepted: rule 1 and
  choice 3 now say a result is about this project only when its wing or source file names it, and an unlabeled or ambiguous
  one is background. Not decided with the tool (the tool lists only R1-F1 as pending).

Both changes are to the plan's wording. The review was not archived. The owner approved the plan on 2026-10-25, after round 1 and without a second round, and so
confirmed choice 1.

## Deferred work

- A default wing per project (a helper and settings change), the roadmap's stated larger change.
- A live check that an agent follows the order of stores.

## Result

- Increment A: `SKILL.md` and `policy.md` carry the three rules. The skill has a paragraph on the order of stores, a
  "Whose note it is" paragraph and a closing sentence that the built-in memory is a separate act it neither grants nor
  forbids; the block has the same three in a clause or a bullet each and stays at 14 lines (its first draft had 15 and the
  existing length test caught it). "a memory" is gone from both texts. The module's tests: 152 pass. Before the edit, 8 tests
  failed on the old text: the 2 existing tests whose assertions I edited (one in the block, one in the skill) and the 6 new
  ones (in each of the block and the skill: the background rule, the order and separate store, and "not a memory").
  I left "Only the owner builds the memory" and "the owner has to build the memory" as they are, since the plan changes only
  "a memory". The module's shipped approval is stale until B. Next: B.
