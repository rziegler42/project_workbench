# superpowers-ports

Status: Draft. Written by plan `2026-10-23-port-superpowers`, increments A and B. The placement rule awaits the owner's
acceptance of its decision record, and the status column is final at increment G.

Terms are defined in `terms.md`. The neutral item format and its translation are in `harness-modules.md`; the modules
that receive the ports are `code-work.md`, `groundwork.md` and `safe-git.md`.

## Purpose and scope

The owner's global configuration (`~/.claude`) routes project work to skills of the superpowers plugin. This spec records,
for each skill of the plugin, whether the owner uses it and what became of it in the workbench, so that
`global-config-migration` can remove the plugin knowing nothing was dropped by accident. It also records where each ported
skill lives, because one superpowers skill can belong in more than one module.

Non-goals:

- The text of any skill. A port is written in the workbench's own words and lives in its module's neutral tree.
- Changes to `~/.claude`, which belong to `global-config-migration`.
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

A skill is **used** when the owner's own files name it: `~/.claude/CLAUDE.md` ("Skill and agent routing" and "Implementation
and verification") or the `skills:` list of one of the owner's agents (`implementer`, `workflow-reviewer`,
`security-reviewer`). A skill the plugin installs but no file of the owner's names is **not used**. The plugin entry in
`~/.claude/settings.json` shows it is enabled; it does not show use.

## The inventory

Dispositions: **covered** (a workbench item already does the job), **ported** (a new skill is written), **split** (the
practice has a general part and domain parts that belong to different modules), **not ported** (with the reason), **gap**
(not done and not planned; a later candidate if the owner wants it). Status is `built` or `planned`.

| Superpowers skill | Used (shown by) | Disposition | Workbench skill | Owner module | Status |
|---|---|---|---|---|---|
| brainstorming | yes (`CLAUDE.md`, "Starting repository work") | ported | `brainstorm` | `groundwork` | planned |
| writing-plans | yes (`CLAUDE.md`, "Skill and agent routing") | covered | `draft-plan` | `code-work` | built |
| executing-plans | yes (`CLAUDE.md`, "Skill and agent routing") | covered | `run-increment` | `code-work` | built |
| subagent-driven-development | yes (`CLAUDE.md`, "Skill and agent routing") | covered in part; gap for a fresh implementer per increment | `run-increment` | `code-work` | built |
| requesting-code-review | yes (`CLAUDE.md`; `workflow-reviewer`) | covered | `request-review` and the `reviewer` agent | `code-work` | built |
| receiving-code-review | yes (`CLAUDE.md`, "Skill and agent routing") | covered, with differences | `evaluate-findings` | `code-work` | built |
| test-driven-development | yes (`CLAUDE.md`; `implementer`) | split: general part ported | `test-first` | `code-work` | planned |
| systematic-debugging | yes (`CLAUDE.md`; `implementer`) | split: general part ported | `diagnose-failure` | `code-work` | planned |
| verification-before-completion | yes (`CLAUDE.md`; `implementer`, `workflow-reviewer`, `security-reviewer`) | split: general part ported | `verify-before-claiming` | `code-work` | planned |
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
  listing do this work. `global-config-migration` decides what replaces the routing in `CLAUDE.md`.
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

## Where a skill goes when it belongs in more than one module

A skill name is one path in a harness, so two modules that ship a skill of the same name make the attach fail (the
installer refuses a neutral path two modules both supply). The rule, proposed in
`docs/decisions/2026-10-23-one-owner-per-skill-name.md` (Proposed until the owner accepts it):

1. A skill, agent or command name has exactly one owner module, and no two first-party packages ship the same name.
2. A practice that spans modules is **split** into separate skills with separate names. The general part goes to the module
   every process shares (`code-work` for the first ports). A domain form is a different skill in the domain's module. It
   names the general skill it extends and says its own rules take precedence in its domain; it does not copy the text.
3. A module whose skill extends another module's skill `requires`, as hard, a capability the owner module provides: an
   existing core name where one fits, otherwise a new core name that the first such domain module's plan adds to a
   specification. Nothing is added until a domain module exists.
4. The owner of each ported skill is the Owner column of the inventory; a test checks every row marked built.

Two worked examples, both planned:

- **Test first.** `test-first` is general and owned by `code-work`; its text names no language or runner and says the
  plan's verification line gives the command. A hardware-description module would later ship a differently named skill, for
  example one about writing the testbench first, that extends `test-first` and requires the capability `code-work`
  provides.
- **Verification.** `verify-before-claiming` is general and owned by `code-work`: run the command that shows the claim and
  report what was run and not run. A domain module that has its own checks (a simulation, a proof, a model check) ships a
  skill that says which runs count as evidence in that domain, and extends the general one.

## Acceptance criteria

1. The table lists all 15 skills of the plugin version 7.0.0 and the provenance table has a hash for each.
2. Every row marked built names a skill that the owner module ships; every row marked planned is built by the plan
   `2026-10-23-port-superpowers` or is marked not ported or gap.
3. Nothing in the spec points at the plugin's path or at `~/.claude` as a source for a requirement.
4. No two first-party packages ship a skill, agent or command of the same name (`tests/test_skill_names.py`).

## Related

- Plan `2026-10-23-port-superpowers`; roadmap candidate `workbench-v1#port-superpowers`.
- `safe-git.md` ("What was and was not taken from the superpowers skills"), `code-work.md`, `groundwork.md`,
  `harness-modules.md`.
