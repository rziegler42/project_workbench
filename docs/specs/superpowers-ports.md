# superpowers-ports

Status: Current for the inventory and the four first ports, which plan `2026-10-23-port-superpowers` built. The placement
rule is accepted in its decision record.

Terms are defined in `terms.md`. The neutral item format and its translation are in `harness-modules.md`; the modules
that receive the ports are `code-work.md`, `groundwork.md` and `safe-git.md`.

## Purpose and scope

Until the owner's user-level configuration was reset on 2026-10-29, it routed project work to skills of the superpowers plugin.
This spec records, for each skill of the plugin, whether the owner uses it and what became of it in the workbench, so that the
plugin could be removed knowing nothing was dropped by accident; the reset removed it. It also records where each ported
skill lives, because one superpowers skill can belong in more than one module.

Non-goals:

- The text of any skill. A port is written in the workbench's own words and lives in its module's neutral tree.
- Changes to the owner's user-level configuration, which are the owner's.
- A promise to port every skill. A skill marked not ported or a gap stays so until the owner picks it.

## Source and provenance

The plugin is untracked content outside this repository. Nothing here points at its path. It is cited by:

| field | value |
|---|---|
| name | superpowers (installed as `superpowers@claude-plugins-official`) |
| version | 7.0.0 |
| source URL | `https://github.com/obra/superpowers` (from the plugin's own README; no release tag was found in the installed copy, so the version above and the hashes below identify the content) |
| retrieved | 2026-10-23 |
| licence | MIT, copyright 2025 Jesse Vincent (`LICENSE` SHA-256 `a37e0e9697144819e1d965176ac4ae5bc3fa02d11e7812036bbcadf6dafe2400`) |

The text of the plugin is data. An instruction inside it, including its own rule to invoke a skill, is not followed here.

| skill | SHA-256 of its `SKILL.md` |
|---|---|
| brainstorming | `6ee10d1481b8a2580d5336ff66c5c08acc9d4b251b13bbc3bfd31be99c261d43` |
| diagnosing-superpowers | `5a652f8132cc901eb5ca61f89157839f87a2f20aed037fc7a2b51051bc37cd19` |
| dispatching-parallel-agents | `1968923066f3b707eb01d1992cdf4c42284c3855f70253b9cd5000ff45fca13c` |
| executing-plans | `f38e8f2ddcf079f65493adc713c1fed78421dfaf5f4dbf6b3a6b2b1d95466e71` |
| finishing-a-development-branch | `8db5a922b242dd4e1bf824cb91c13b3e8d8e8a86d6ceaf7f0774eb9cce909d65` |
| receiving-code-review | `091df1629510af1b92fc4abd6f96732ebedb4cb2c0f3457e8f2740b0504a2438` |
| requesting-code-review | `2180e14a448e9410bec88e6646a2d1f0ce7fdd58de27388c1e052e929679d2bc` |
| subagent-driven-development | `8dde5589ee083fb4999106d116f01c8fdaf3116a8a9813fdedeb80329de49046` |
| systematic-debugging | `51c6435d98c83c42c96ba7c35725a0b2c376cd487fb1a4e6bd0ddbe7e33ef202` |
| test-driven-development | `64b03fce4aee5a97a93160cea8111f3ba13a17b7c001db4bd5836d67fd10705d` |
| using-git-worktrees | `8cfb86f121269e8f7f12361e6795c4f6738828340e28964c9229d365666c9edd` |
| using-superpowers | `82c5c8866ad7f5dd4440ce66bd7806ba48a2f13771beae5cf112e53f08fe36ba` |
| verification-before-completion | `2befe7fc55bcadaa3d97dd9e8efeb633d2561c0ebe74c5a8b17c4d9e7e4520b3` |
| writing-plans | `a6c67c1900064347c2a329990dd3c555657c51c3ec53b259a08aa01a2c26139a` |
| writing-skills | `bbdfe742f853562e643a3d40d64476359d47881e39cef80a189283fa26d11ab9` |

## How use was decided

A skill is **used** when the owner's own files name it: the owner's user-level instruction file (its sections "Skill and agent
routing" and "Implementation and verification") or the `skills:` list of one of the owner's agents (`implementer`,
`workflow-reviewer`, `security-reviewer`). A skill the plugin installs but no file of the owner's names is **not used**. The plugin
entry in the owner's user-level settings file shows it is enabled; it does not show use.

Those files are identified by role only, as owner-local files with no URL. This spec read them on 2026-10-23 and recorded no hash.
`global-config-inventory.md` records the SHA-256 of each as read on 2026-10-25. The copy the owner kept at the reset of 2026-10-29
was hashed on 2026-10-29 with `shasum -a 256`: the instruction file is `6c4de9ea291da89416fe3f869811b057866519759149a14388c80eb66006bd5c`
and the settings file is `36c2594f83c4884133e60cf4a9dbd9cad7f40bcbdbc5563bdd978864aa104247`. Neither equals the hash the inventory
records, so the copy differs from the bytes read on 2026-10-25 for a reason these records do not show, such as later edits, the
reset or the backup. The evidence here is therefore a reading on those dates and cannot be re-checked against the copy.

## The inventory

Dispositions: **covered** (a workbench item already does the job), **ported** (a new skill is written), **split** (the
practice has a general part and domain parts that belong to different modules), **not ported** (with the reason), **gap**
(not done and not planned; a later candidate if the owner wants it). Status is `built`, or `none` for a row with no item.

| Superpowers skill | Used (shown by) | Disposition | Workbench skill | Owner module | Status |
|---|---|---|---|---|---|
| brainstorming | yes (`CLAUDE.md`, "Starting repository work") | ported | `brainstorm` | `groundwork` | built |
| writing-plans | yes (`CLAUDE.md`, "Skill and agent routing") | covered | `draft-plan` | `code-work` | built |
| executing-plans | yes (`CLAUDE.md`, "Skill and agent routing") | covered | `run-increment` | `code-work` | built |
| subagent-driven-development | yes (`CLAUDE.md`, "Skill and agent routing") | covered in part; gap for a fresh implementer per increment | `run-increment` | `code-work` | built |
| requesting-code-review | yes (`CLAUDE.md`; `workflow-reviewer`) | covered | `request-review` and the `reviewer` agent | `code-work` | built |
| receiving-code-review | yes (`CLAUDE.md`, "Skill and agent routing") | covered, with differences | `evaluate-findings` | `code-work` | built |
| test-driven-development | yes (`CLAUDE.md`; `implementer`) | split: general part ported | `test-first` | `code-work` | built |
| systematic-debugging | yes (`CLAUDE.md`; `implementer`) | split: general part ported | `diagnose-failure` | `code-work` | built |
| verification-before-completion | yes (`CLAUDE.md`; `implementer`, `workflow-reviewer`, `security-reviewer`) | split: general part ported | `verify-before-claiming` | `code-work` | built |
| using-git-worktrees | yes (`CLAUDE.md`, "Skill and agent routing") | not ported | none | none | none |
| finishing-a-development-branch | yes (`CLAUDE.md`, "Skill and agent routing") | not ported | `push-changes` covers the push | `code-work` | built |
| using-superpowers | no (the plugin's own start-up rule) | not ported | none | none | none |
| dispatching-parallel-agents | no | gap | none | none | none |
| writing-skills | no | gap | none | none | none |
| diagnosing-superpowers | no | not ported | none | none | none |

Reasons for the rows that are not a plain port:

- **using-git-worktrees, finishing-a-development-branch.** Settled in `safe-git.md`, "What was and was not taken from the
  superpowers skills": a worktree needs git subcommands the helper does not run; merging and cleanup are outside the agent;
  the push is a checkpoint (`push-changes`). Not revisited here.
- **using-superpowers.** It tells an agent to look for a skill before every reply. That is behaviour of the harness and of the
  policy text, not a project practice. In a workbench project the `policy` slot in `AGENTS.md` and the harness's own skill
  listing do this work. The routing in the owner's old user-level instruction file went with the reset of 2026-10-29. Run on
  2026-10-30 ("The session-start test"), a request for new behaviour in a workbench project that asked to build one had not invoked
  `brainstorm` when the agent asked how to proceed (it offered it as an option and recommended drafting a plan first), while one that
  asked to design one loaded it. That is a gap against the expectation that new behaviour starts with `brainstorm`; it is recorded and
  not closed, and one run of each wording does not show that the wording is the cause.
- **diagnosing-superpowers.** It diagnoses sessions of the plugin itself. It has no meaning once the plugin is gone.
- **dispatching-parallel-agents, writing-skills.** Not named by any file of the owner's. If the owner wants either, it is its
  own candidate: the first would belong to `code-work`, the second to a module about writing skills for the workbench.
- **subagent-driven-development.** `run-increment` runs the loop in the author's own context. A fresh implementer per
  increment was deferred by plan `2026-10-23-increment-loop-and-review-skills` and stays deferred.

## Differences found in the covered rows

These are what the plugin's skill says that the workbench item does not. They are findings, not changes: each is a later plan
if the owner wants it. The comparison reads the plugin skill's text against the workbench skill's text for the points below
only; it is not a line-by-line audit.

- **receiving-code-review against `evaluate-findings`.** The plugin tells the agent: when any item of a list of feedback is
  unclear, stop and ask before implementing any item (items may be related); never answer with praise or agreement before
  verifying; implement one item at a time and test each; and check a suggested "professional" feature against what is
  actually used before adding it. `evaluate-findings` verifies each finding, rejects with a reason, and refuses
  instructions inside a finding, but it does not say to ask before acting on a list with an unclear item, to apply one at a
  time, or to check a suggested feature for need.
- **writing-plans against `draft-plan`.** The plugin's plan is task-and-step shaped with a code block per step and is stored
  by default under a tool-owned directory. The workbench plan is lettered increments in `docs/plans/`. This is intended and is
  not a difference to close.
- **executing-plans against `run-increment`.** The plugin runs a whole plan to the end and stops on a blocker. The workbench
  stops after each increment for the owner's verdict. This is intended (`code-work.md`, "The increment loop").

## What stops working when the plugin is removed

*Note, 2026-10-29.* The plugin is no longer enabled, because the owner's user-level configuration was reset, so what follows
records what would have stopped working and is now what stopped. The three agent definitions and the routing text it describes are
no longer loaded, and nothing in the workbench depended on them.

Observed on 2026-10-24 by reading the owner's agent definitions and the routing text of the owner's user-level instruction
file. The comparison covers the agents' `skills:` lists and the routing lines only; it is not a line-by-line audit of either
file.

- **Three agent definitions name plugin skills in their `skills:` lists.** The reference breaks silently once the plugin is gone.
  `implementer` names `systematic-debugging`, `test-driven-development` and `verification-before-completion`;
  `workflow-reviewer` names `requesting-code-review` and `verification-before-completion`; `security-reviewer` names
  `verification-before-completion`. The workbench skills that replace them are `diagnose-failure`, `test-first`,
  `request-review` and `verify-before-claiming`. They exist only in a project that installed `code-work`; editing the agent
  definitions was the owner's; the reset removed them.
- **The routing text names the plugin's skills** for brainstorming, planning, plan execution, subagent-driven development,
  receiving and requesting code review, worktrees, debugging and verification. Without the plugin none of them loads. The
  workbench counterpart of each is the inventory table's row; worktrees are not ported.
- **The session-start rule.** The plugin injects `using-superpowers` at the start of a session, which tells an agent to look
  for a skill first. Nothing else the owner has does that. For a workbench project this document relies on the `policy` slot of
  `AGENTS.md` and the harness's skill listing (see the row for `using-superpowers`); that is stated and was not tested when the plugin went; "The session-start test" below is the procedure and holds the runs.
- **Evidence of use.** Each skill the agents name is also named by the routing text, so dropping or rewriting an agent does
  not by itself change a row's "used" status; removing the routing lines would.

## The session-start test

Added 2026-10-30 by plan `2026-10-30-close-the-superpowers-retirement`, Increment B. The plugin used to inject `using-superpowers` at
the start of a session, which told an agent to look for a skill first. In a workbench project the `policy` slot of `AGENTS.md` and the
harness's skill listing stand in for it; until the runs below, that was stated and not tested. The test is the owner's run, because
the result is what a live session does and a model of it would prove nothing.

Procedure. With no plugin enabled, start a new session and type a request for a new behaviour in plain words, with no mention of a
skill or a command, then note whether the `brainstorm` skill is invoked before any code or file is written. Do it twice:

1. In a project with `groundwork` and `code-work` installed and attached (this repository qualifies). Expected: `brainstorm` is
   invoked.
2. In a project with no workbench skills. Expected: no skill is invoked, which is the cost of having no routing outside the
   workbench (the decision drafted by the plan's Increment C).

Each run records the date, the harness version the owner reports, the request as typed, and what loaded, in the owner's words. A run
whose result differs from the expectation is recorded as it happened and listed as a gap; this section does not change a skill or a
policy block to make it pass.

Runs, in the owner's words and as the owner pasted them:

- **2026-10-30, first run, inconclusive.** The owner reported: "I did not see the brainstorm load, but it might have been my prompt."
  The project, the harness version and the request were not reported, and the owner thought the prompt may have been the cause, so
  this run is not counted as a result.
- **2026-10-30, second run, in a separate test project of the owner's with the workbench's skills attached** (the agent offered both
  `draft-plan` and `brainstorm`, so both skill sets were present; the harness version is the one reported below). Request typed: "I want to add
  a new command to this project that lists every plan with its status. Let's build it." What the owner pasted: the agent said it would
  start by reading the project docs and seeing how commands are defined, ran two shell commands, and then asked how to proceed "given
  the project policy that work needs an approved plan first", with the options "Draft a plan (Recommended)" (use the `draft-plan`
  skill, then stop for the owner to run `wb approve-plan`), "Brainstorm first" (run the `brainstorm` skill to settle requirements
  before drafting the plan), "Type something" and "Chat about this". The pasted transcript ends at that question: `brainstorm` was offered
  and had not been invoked when the agent asked, and no code or file write is shown in it.
- **2026-10-30, third run, in the same test project.** The owner reported: "With the prompt: 'I want to design a new feature' the
  brainstorm skill loaded in the [test project]." (The path the owner gave is elided: a tracked document does not point to an untracked
  one.) Request typed: "I want to design a new feature". `brainstorm` loaded.
- **Harness version,** asked for after all four runs and reported once by the owner as "Claude Code v2.1.314". The owner did not say
  which run it belongs to, so it is the version of the harness the owner was using that day, not a per-run record.
- **Reading, against the expectation above.** The expectation was that `brainstorm` is invoked before any code or file is written.
  In the second run it had not been invoked when the agent asked; it was offered as the second option, and the first, recommended
  option was to draft a plan. The agent cited the project policy that work needs an approved plan first, so the policy text reached it
  and did some of the work of a session-start rule, but it routed to `draft-plan` and left `brainstorm` to the owner's choice. Whether
  `brainstorm` would have run after the owner chose is not known. The third run shows the other side: a request that says "design"
  loaded `brainstorm`. The two results are consistent with the wording of the request mattering, as the owner suspected of the first
  run, but they do not isolate it: the second request was longer and named a command and a status listing, the agent's answer was a
  question and not a skill decision, and each wording was run once. This is recorded as a gap against the expectation that
  `brainstorm` is invoked for a request for new behaviour, not as a failure of a skill. What the plugin did is not shown by these runs
  (it was not enabled); the plugin's own skill, as this spec describes it, tells an agent to look for a skill before every reply.
  Whether the workbench should force brainstorming for new behaviour is the owner's decision.
- **2026-10-30, item 2 of the procedure above, a folder that is not a project.** The owner reported: "In a non-project folder the
  brainstorm skill did not load with the same prompt", meaning "I want to design a new feature". That matches the expectation. A
  folder that is not a project would not have the workbench's skills, so `brainstorm` would not be there to load (an inference; the
  owner did not report the folder's contents). It is one prompt, and it is the cost the decision of the plan's Increment C weighs: with
  no workbench, nothing sends the agent to a skill. The owner did not report what the agent did instead.

## Where a skill goes when it belongs in more than one module

A skill name is one path in a harness, so two modules that ship a skill of the same name make the attach fail (the
installer refuses a neutral path two modules both supply). The rule, proposed in
`docs/decisions/2026-10-23-one-owner-per-skill-name.md` (Accepted 2026-10-24):

1. A skill, agent or command name has exactly one owner module, and no two first-party packages ship the same name.
2. A practice that spans modules is **split** into separate skills with separate names. The general part goes to the module
   every process shares (`code-work` for the first ports). A domain form is a different skill in the domain's module. It
   names the general skill it extends and says its own rules take precedence in its domain; it does not copy the text.
3. A module whose skill extends another module's skill `requires`, as hard, a capability the owner module provides: an
   existing core name where one fits, otherwise a new core name that the first such domain module's plan adds to a
   specification. Nothing is added until a domain module exists.
4. The owner of each ported skill is the Owner column of the inventory; a test checks every row marked built.

Two worked examples; the general skills are built, the domain forms are not:

- **Test first.** `test-first` is general and owned by `code-work`; its text names no language or runner and says the
  plan's verification line gives the command. A hardware-description module would later ship a differently named skill, for
  example one about writing the testbench first, that extends `test-first` and requires the capability `code-work`
  provides.
- **Verification.** `verify-before-claiming` is general and owned by `code-work`: run the command that shows the claim and
  report what was run and not run. A domain module that has its own checks (a simulation, a proof, a model check) ships a
  skill that says which runs count as evidence in that domain, and extends the general one.

## Acceptance criteria

1. The table lists all 15 skills of the plugin version 7.0.0 and the provenance table has a hash for each.
2. Every row marked built names a skill that the owner module ships (`tests/test_skill_names.py`); a row for a skill
   that is not built says `none` throughout.
3. Nothing in the spec points at the plugin's path or at `~/.claude` as a source for a requirement.
4. No two first-party packages ship a skill, agent or command of the same name (`tests/test_skill_names.py`).

## Related

- Plan `2026-10-23-port-superpowers`; roadmap candidate `workbench-v1#port-superpowers`.
- `safe-git.md` ("What was and was not taken from the superpowers skills"), `code-work.md`, `groundwork.md`,
  `harness-modules.md`.
