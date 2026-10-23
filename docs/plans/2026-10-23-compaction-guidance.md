# The compaction guidance

Status: Approved
Created: 2026-10-23
Candidate: workbench-v1#compaction-guidance
Specs: code-work, harness-modules

## Goal

`code-work.md` says the module ships neutral guidance on what a compaction must preserve, and that the Claude root file
carries a generated "Compact Instructions" section built from it. Neither exists: the policy block placed in
`AGENTS.md` says nothing about compaction, and the Claude root file is the one `@AGENTS.md` line.

The roadmap candidate assumed the section would steer Claude's summary. A check of the current Claude Code
documentation (below, "Evidence") found no such section: the documented ways to steer a compaction are the text the owner
gives `/compact` and a `SessionStart` hook with the `compact` matcher, and the documented behaviour of the root file is
that it is read again from disk and put back after every compaction. The owner therefore chose the smaller scope: put
the preservation rules in the policy text that every harness reads, and correct the specs that promised a section.

When this plan is done:

- the `code-work` policy block in `AGENTS.md` states, in tool-neutral words, what a compaction must preserve and that the
  plan, not the conversation, is the state;
- the specs and the roadmap candidate say what is built and no longer promise a rendered "Compact Instructions"
  section, and say what the documentation does and does not confirm;
- the changed package approval is released by the owner and the full suite passes.

## Scope

- One bullet in `packages/workbench/code-work/files/blocks/policy.md`, and the tests that pin it (increment A).
- Corrections to `code-work.md`, `harness-modules.md` and the roadmap candidate `compaction-guidance`; the approval
  release; the plan's Result (increment B).

## Non-goals

- A rendered "Compact Instructions" section, a neutral `guidance` kind, or any change to `workbench/` or the root-file
  rendering. No documentation confirms the section; building the mechanism for it is deferred until one does.
- A `SessionStart` hook that re-injects text after a compaction. It is code that runs, has no neutral form and needs
  its own approval display. It is deferred.
- A command or wrapper that triggers a compaction. No tool lets an agent do it, and the roadmap excludes a wrapper
  outside the session.
- opencode. How it receives guidance waits for `verify-opencode`.
- Any change to when the agent recommends `/compact`. The owner's own global instruction stays where it is.

## Assumptions and constraints

- The policy block is installed into `AGENTS.md` as a fill and replaced on upgrade only while unedited
  (`code-work.md`, "Policy placed in `AGENTS.md`"). Editing `files/blocks/policy.md` changes the `code-work` tree hash,
  so its shipped approval goes stale; the release is the owner's (`release-approvals`, run only on "Run it for me";
  stale records removed only after a preview and "remove them").
- `workbench/` and `tests/` hold only mechanism and `tests/test_boundary.py` must stay green. Nothing changes there.
- The policy block names no harness and no tool beyond `wb approve-plan`, `wb plan-status` and `wb settings`, and a test
  now limits it to 18 lines. The new bullet needs about four more lines.
- Evidence about Claude Code, read from the official documentation on 2026-10-23 by a subagent and then checked by me
  against the fetched text (the pages carry no version, and the text can change, so re-read them before relying on
  it): the memory page says the project
  root `CLAUDE.md` "survives compaction: after `/compact`, Claude re-reads it from disk and re-injects it" and that
  `@path` imports are expanded and loaded alongside it; the context-window page says `/compact` takes focus
  instructions; the hooks pages list `compact` among the `SessionStart` matchers. The pages name no "Compact
  Instructions" section (the phrase appears in none of the four pages), and the documentation does not say whether an
  agent can trigger a compaction. Sources, retrieved 2026-10-23 with `curl` and hashed as fetched (SHA-256):

  | page | hash |
  |---|---|
  | `https://code.claude.com/docs/en/memory.md` | `82d60341354924ee8658de0fcde297c2ac37b237dcc931aa4a83329b2c7bb6e7` |
  | `https://code.claude.com/docs/en/context-window.md` | `f2cf7463cb14b4dc9607ee235b26267ed5cc6ca17ad7abd45fe83924130cdbd9` |
  | `https://code.claude.com/docs/en/hooks.md` | `c6ef9d211e8c4dc870add6302c47971f5fec316888993143011716f78b9862d8` |
  | `https://code.claude.com/docs/en/hooks-guide.md` | `004ded2fd87af2deee93d4ce7f47216a82b5e22fc76f345ea654eeb51b2bee3c` |

  The fetched files are scratch and are not tracked; the specs cite these URLs, date and hashes and nothing depends on a
  path.
- Discovery: graphify: skipped, not installed here; the scope was enumerated by reading the policy block, its tests, the
  specs' mentions of compaction and the root-file rendering.

### Choices (made by me; the owner chose choice 1)

1. **Policy text only.** The owner picked this over a re-injection hook and over building the section anyway. It
   relies on the documented re-reading of `CLAUDE.md` and its imports after a compaction, so the rules reach the
   summary's reader again; it does not steer the summary itself, which only `/compact` text or a hook can do.
2. **The wording is behaviour, in one bullet.** Draft: "When context is compacted, what must survive is the active
   plan's path and increment, the approvals and checkpoints reached, the files changed, the verification actually run
   and its result, unresolved risks and the next action. The plan, not the conversation, is the state: record an
   increment's outcome in the plan before the session is compacted or ends. Raw logs and superseded hypotheses need not
   survive." It names no harness. The final wording is set in increment A and shown to the owner at the commit.
3. **The line limit rises from 18 to 24.** The limit is a guard against a block that grows without notice; the bullet
   is the only addition.
4. **The old statement that `push` and `compact` are absent from the block changes.** The test
   `test_the_policy_block_names_no_rule_the_module_cannot_yet_enforce` forbids both words. Compaction guidance is advice
   the module now states, so `compact` is allowed; `push` stays forbidden, because the block still states no push rule.
5. **The roadmap candidate is edited here.** Its "Outcome" and "Boundary" lines and one sentence in "Current state"
   promise the rendered section. Changing them is a change of direction, so the owner's approval of this plan is the
   approval of exactly those three edits and no others.

## Completion criteria

1. The policy block carries the bullet of choice 2 (final wording per increment A), names no harness, stays within 24
   lines and keeps every rule it had; the rendered `AGENTS.md` fill carries it.
2. A test pins the preserved items, the plan-as-state sentence and the absence of any harness word.
3. `code-work.md` and `harness-modules.md` no longer say the root file carries a generated "Compact Instructions"
   section; they say the policy text is built, what the documentation confirms and what it does not, and that the hook
   and the rendered section are deferred. The roadmap candidate says the same in its three places.
4. The full suite, `doccheck`, `refcheck` and `git diff --check` pass; the `code-work` approval is released by the owner
   and the suite runs with no Claude skip.

## Increments

### Increment A — The policy bullet

**Outcome:** the policy block tells every attached harness's agent what a compaction must preserve.
**Dependencies:** none.
**Affected areas:** `packages/workbench/code-work/files/blocks/policy.md`;
`packages/workbench/code-work/tests/test_codework_module.py` (the policy tests and the 18-line limit).
**Steps:**
1. Tests first: a policy test that the text carries "the active plan's path and increment", "the approvals and
   checkpoints reached", "the files changed", "the verification actually run", "unresolved risks", "the next action",
   "the plan, not the conversation, is the state" and "before the session is compacted or ends"; the line limit is 24;
   the `compact` word is allowed and `push` is not; the words `Claude`, `opencode`, `Codex` and `CLAUDE.md` still do not
   appear; the only `wb` commands are the three it names. See the new tests fail.
2. Write the bullet, after the plan-drafting and commit rules and before the verification rule, in the block's own
   style (a hyphen bullet, plain sentences). Keep the other rules unchanged.
3. Run the new tests, the `code-work` suite and the boundary test.
**Verification:** the module tests; `tests.test_boundary`; `doccheck`, `refcheck` and `git diff --check` print nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-compaction-guidance#A`.

### Increment B — Spec, roadmap and record

**Outcome:** the specs and the roadmap say what is built, the approval is released, and the plan records it.
**Dependencies:** A.
**Affected areas:** `docs/specs/code-work.md` ("Context across increments", "Decided points that were open", "As built",
"Open items"); `docs/specs/harness-modules.md` (the Claude layout table, "Hooks" and the acceptance line about the
root file); `docs/roadmaps/workbench-v1.md` (the candidate's Outcome and Boundary and the sentence in Current state,
choice 5); the package approval (owner-run); this plan's Result.
**Steps:**
1. Edit the specs: the preservation guidance is the policy bullet; Claude reads the root file again after a compaction
   as the documentation says, citing the four pages with their retrieval date and hashes from the plan's evidence; the
   "Compact Instructions" section is unconfirmed and not built; a `SessionStart`
   `compact` hook is documented and deferred; the guidance steers nothing by itself and is advice. Leave the opencode
   open item.
2. Edit the three roadmap places named in choice 5 and nothing else in the roadmap.
3. Run the full suite. If it reports the approval stale, stop and ask the owner to run `release-approvals`; preview any
   stale record and delete it only after "remove them". Run the suite again.
4. Run `doccheck`, `refcheck` and `git diff --check`; search the docs for a remaining promise of the rendered section.
5. Fill the Result, including that no live session was used. Set `Status: Completed` only after every criterion has its
   evidence.
**Verification:** the full suite with no Claude skip; the document checks print nothing.
**Evidence:** the one local commit (specs, roadmap, plan, refreshed approval record), trailer
`Plan: 2026-10-23-compaction-guidance#B`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots with no Claude skip; `git diff --check`, `doccheck` and
  `refcheck` print nothing.
- Global items this plan will let `global-config-migration` retire, none yet: the "Compact instructions" section of
  `~/.claude/CLAUDE.md` stays until a recorded run shows a project behaves the same without it.
- A live check is possible and not planned: attach `code-work` in a scratch project, compact, and see whether the agent
  still names the active plan and next action. Until the owner runs it, the effect is unverified.

## Risks and sensitive actions

- **The guidance is advice.** It does not steer the summary and nothing checks that an agent follows it. It relies on
  documented re-reading of the root file, not on a live run.
- **The documentation can change or be wrong.** The evidence has no version; the hashes identify the text read on
  2026-10-23 and a later fetch may differ. The specs say what was read, when, and its hash.
- **Text in the instruction file is trusted by the agent.** The bullet is first-party and shown at approval; it asks the
  agent only to keep and record state.
- **The package tree changes.** The approval goes stale; the release is the owner's and stale records are deleted only
  after a preview and "remove them".
- **A roadmap edit is a change of direction.** It is limited to the three places in choice 5, covered by the owner's
  approval of this plan.
- No push, no install into a project, no secret and no deletion beyond the stale approval record.

## Review record

Round 1 of 3, 2026-10-23, `ask-codex review-plan`, model `gpt-5.6-luna`, effort medium (asked for by the owner).
Outcome: changes needed; two major findings.

- R1-F1 applied. The evidence had no content hash, which the repository's reference rule requires. I fetched the four
  documentation pages with `curl` on 2026-10-23, hashed them as fetched, checked the quoted sentences against the
  text myself, and put the URLs, date and hashes in the evidence; increment B carries them into the spec text. The
  fetched files stay scratch and untracked.
- R1-F2 rejected, with a reason. A decision record is for a durable architectural constraint. Here the plan builds
  less than the roadmap candidate promised, and the specs (living documents, edited in place) and the roadmap carry
  the result together with the evidence and its limits; an ADR would restate them and could not say more. Nothing
  here constrains later architecture: the rendered section and the hook stay open under Deferred work. The reviewer
  holds that the plan format requires a record; the owner decides, and can ask for an ADR, which would add a step to
  increment B.

Left for the owner: whether R1-F2 stands as rejected, whether to approve, and whether to ask for a further round.

## Deferred work

- A rendered root-file section and a neutral `guidance` kind, if the documentation or a live check ever confirms that a
  named section steers a compaction.
- A Claude-only `SessionStart` hook with the `compact` matcher that re-injects the guidance, with its approval display.
- Delivery to opencode (`verify-opencode`).
- A live check in a scratch project.

## Result

Not started.
