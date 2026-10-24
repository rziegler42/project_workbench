# Roadmap: workbench-v1

Status: Active
Updated: 2026-10-24

This roadmap is direction only. It does not authorize implementation and does not
change any plan. A candidate is referred to as `workbench-v1#<id>`. Candidates are
identified by a topic slug and carry no required order; the suggested order below and
the dependencies are hints, and what is learned along the way may reshuffle, add or
drop candidates.

## Purpose

Build the first version of the project-workbench installer and its first modules, as
specified in `docs/specs/`: a neutral installer that creates and maintains projects
from packages of modules, with Claude and opencode as the supported harnesses and a
programming way of working (`code-work`) on top of a shared `groundwork` module.

## Bootstrap

This repository is built while the new system does not yet exist, so two sets of rules
meet here and the order matters.

- **The old conventions governed only until `adopt-conventions`, which is done.** Until
  then this repository followed the rules in its own `AGENTS.md` and
  `docs/plans/README.md`: one active plan in `docs/plans/next.md`, explicit owner
  approval of a plan before implementation, numbered archives, and numbered decision
  records. `adopt-conventions` rewrote those documents by hand to the new document
  conventions (dated plan and decision names, the `Candidate:` and `Specs:` lines, no
  fixed `next.md`). The repository had no commits, so nothing needed migrating.
- **Mechanical enforcement waits for the code.** Hash-bound approval, the guarded store,
  the derived active-plan listing, the checks and the commit helper arrive with their
  candidates. The repository has one developer, so none of them is needed early. Until
  they exist, approval is the owner's explicit statement in session, a `Status:` line is
  informational, and active plans are found by searching for it. The repository's own
  documents say that these checks are "enforced by the installer once built; until then
  by the owner in session".
- **The first commit already respects the new boundary.** Harness files (`CLAUDE.md`,
  `.claude/`) and the old `.template-manifest` are not committed; `adopt-conventions`
  excluded them before any commit existed.
- **Plans are approved by the owner in session** until the approval mechanism that the
  later candidates build exists.
- **No project file is written before module approval exists.** `installer-core-verifier`
  writes nothing into a project; it verifies declarations. `module-approvals` comes
  before `base-and-manifests`, so the first time the installer writes a project, the
  approval check is already in place. Plan approval and the delegation helper are
  built with `code-work-plans` and plan `2026-10-22-plan-approval-records`, because the plan format names the
  sections they depend on.
- **The installer is not run on its own repository** until `self-hosting` has shown,
  by a test, that its output agrees with the hand-maintained files.
- **The commit helper does not exist while it is being built.** Until `code-work-commit`
  ships it, commits are made with the owner's own tooling.

## Current state

- The old template created this repository. `adopt-conventions` is done (2026-10-19):
  the repository's own documents follow the new conventions, and harness files and the
  old template manifest are excluded from git. The old template is retired at
  `self-hosting`.
- Seven specifications are approved by the owner (2026-10-19) and read `Current`:
  `terms`, `module-contract`, `repository-boundary`, `trust-and-approval`,
  `groundwork`, `code-work` and `harness-modules`.
- Twelve decision records were accepted on 2026-10-19 and five more on 2026-10-20, listed under
  Related decisions.
- `installer-core-verifier` is built and its language decision is accepted
  (`2026-10-19-implementation-language`, 2026-10-19): a Python 3
  package `workbench/` with the safe filesystem layer, hashing, declaration and module
  verification, set verification and `python3 -m workbench verify`. It writes nothing
  into a project. `module-contract` records the concrete schema it accepts.
- `module-approvals` is built (plan `2026-10-19-module-approvals`, increments A to K): the guarded
  store at a fixed location and its personal settings; the compiled hard-stop floor; approval
  records for modules and packages; first-party approvals shipped with the workbench; the approval
  request and gate; the owner-run `approve` command, from a directory or from a source downloaded
  inertly into the store's cache with its commit recorded; helper pins, the `launch` command and the
  `wb` launcher. It writes nothing into a project. `trust-and-approval`, `repository-boundary` and
  `module-contract` record the formats and rules it built. The two decisions it proposed were
  accepted on 2026-10-20.
- Found while building it, for later candidates: `python3 -m workbench` run from inside an
  untrusted project lets that project's code run first, so the harness must call the `wb` launcher
  and not the `-m` form (decision `2026-10-20-isolated-launcher-invocation`, accepted); a module has no field to declare an added hard stop; and nothing removes
  cache copies, shipped records of earlier releases or leftover `bin/run/` directories.
- `installer-interface` is being written (plan `2026-10-20-installer-interface`): the draft spec
  `docs/specs/installer-interface.md` covers the target rules, the commands, the preview and
  approval, the output and the exit codes, and awaits the owner's approval. It changes no code. It
  departs from the wording of the candidate below in three places, listed in the spec under
  "Departures from the roadmap's wording".
- `base-and-manifests` is implemented (plan `2026-10-20-base-and-manifests`, increments A to I; its
  completion is derived from that plan): the `base/` content and its loader, the canonical
  committed manifest with the project seed and ID, the write plan with its digest, `wb preview
  install` (read-only) and the owner-run `wb install` into a missing, empty or lone-`.git` target,
  with the acknowledgement baselines and the first-seen record written to the guarded store.
  It ended with `harness not attached` until `claude-harness`. Its three decisions were
  accepted on 2026-10-20. It writes the empty `.git` itself and runs no program in the target, after a
  security review found that `git init` followed a link planted at `.git`.
- `ownership-and-upgrade` is implemented (plan `2026-10-20-ownership-and-upgrade`, increments A to M;
  its completion is derived from that plan): strict slot blocks, the hash-checked file replace, the
  readers for the acknowledgement baselines and the existing project, the owner-run `wb acknowledge`,
  `wb preview upgrade` and `wb preview add` (read-only), and the owner-run `wb upgrade` and `wb add`,
  with classification of every path, a marker and read-back on the write, and no git and no
  deletion. Its two decisions (`2026-10-20-acknowledge-before-upgrade`,
  `2026-10-20-upgrade-needs-no-git`) were accepted on 2026-10-20. The owner-class declaration field is
  deferred; a rerun after a part-way failure is not repaired (the plan's Result lists the limits).
- `claude-harness` is implemented (plan `2026-10-20-claude-harness`, increments A to L; its completion
  is derived from that plan): the Claude formats verified against Claude Code 2.1.305, the neutral
  skill, agent and command reader, the layout field, translation and rendering (the `deny` rules for
  every owner-run command), the first-party module `claude` in `packages/workbench/` with its
  shipped approval, the owner-run `wb attach`, `wb install` attaching as its last step, and the
  read-only `wb check` (harness drift, strays, other harnesses' files, tracked output and pointers,
  the manifest), which reads `.git/index` itself and runs no git. An adversarial security pass found
  nothing above Low unresolved. The hand run in a live `claude` session was not done. The plan's Result
  and `harness-modules.md` ("As built, and its limits") list the limits. The compaction guidance is
  a policy bullet from `compaction-guidance`; no Compact Instructions section is rendered.
- `groundwork-module` is implemented (plan `2026-10-21-groundwork-module`, increments A to I; its
  completion is derived from that plan): the first-party module `groundwork` in
  `packages/workbench/` with the four READMEs, the `docs-index` and policy blocks and three skills
  (`draft-spec`, `draft-roadmap`, `draft-decision`), shipping no code; the reference index format
  (`docs/references/index.json`, canonical JSON); and the document and reference checks, which the
  installer runs in `wb check` for a project that has the module. Two adversarial security passes
  found nothing above Medium unresolved. The package was released again with its approvals. The two
  decisions it proposed (`2026-10-21-reference-index-format`,
  `2026-10-21-installer-runs-document-checks`) were accepted on 2026-10-21. The hand run in a live `claude`
  session was not done. `groundwork.md` ("As built, and its limits") lists the limits.
- Git work lives in its own module (plan `2026-10-22-safe-git-module`, increments A to E; it carries out
  `2026-10-22-git-work-in-its-own-module` and has no roadmap candidate, so its completion is not derived).
  The first-party module `safe-git` provides the capability `commit` and ships `wb run safe-git commit` and
  `remove` and the neutral skill `commit-changes`. `code-work` keeps `check`, `plans` and `report` and
  requires `commit`. The code moved unchanged; the attribution setting is `.workbench/safe-git.json`.
  `docs/specs/safe-git.md` records it. The hand run of install and commit in a project is still to do.
- Model calls go through thin vendor bridges (plan `2026-10-22-ask-codex-bridge`, increments A to E; it carries
  out the first part of `2026-10-22-model-calls-go-through-vendor-bridges` and has no roadmap candidate, so its
  completion is not derived). `docs/specs/model-bridge.md` is the contract (version 1). A helper may run another
  installed module's pinned command through the kit's `wbkit/call.py` and `wb run --provides <capability>`
  (`module-boundary.md`). The first-party module `ask-codex` provides the capability `model-bridge` and the
  command `ask-codex ask`; it passes the conformance checklist against a fake `codex` program, and no test starts a
  real one. Security and workflow reviews found no Critical or High finding. The review engine and the
  action-review engine (candidates below), a second vendor and the hand run against a real Codex are still to do.
- Plan approval is a recorded approval (plan `2026-10-22-plan-approval-records`, increments A to F; it had
  `Candidate: none`, so its completion is not derived). The installer records an owner-made approval per project
  (`wb approve-plan`, `wb plan-status`); the process module declares an `approval` command and the `code-work` helper's
  `region` subcommand computes the plan's hashed region. The decision
  `2026-10-22-installer-records-plan-approval-module-computes-region` was accepted on 2026-10-22. The candidate
  `code-work-approval` was too large for one plan and is split into `checkpoint-settings-and-caps`,
  `increment-loop-and-review-skills`, `push-checkpoint`, `compaction-guidance` and `delegated-approval`; the older
  plans, specs and decisions that name `code-work-approval` mean this group. Security and workflow reviews found
  nothing above Medium unresolved; the hand run in a live project is still to do.
- The checkpoint settings, the loop caps and the edit gate are implemented (plan
  `2026-10-22-checkpoint-settings-and-caps`, increments A to H; its completion is derived from that plan once it is
  completed). A process module declares `checkpoints`, `caps` and `approval.active`; `code-work` declares its eight
  checkpoints and three caps and ships the `active` subcommand; the personal settings gain `caps`; the read-only
  `wb settings` prints the effective values; and the installer's `wb gate <harness>` refuses a file edit while a plan
  under way is not approved, rendered into the Claude harness as a `PreToolUse` hook (the Claude module now provides
  `hooks`) together with a deny on edits to the rendered settings file. The tool-to-field table is the harness
  layout's, not the installer's, which departs from the wording of the plan. `delegate` still has no effect, nothing
  reads a cap yet, a project cannot lower one, and the hook was seen working in a live Claude session on 2026-10-22 (Claude Code 2.1.307; the owner's check,
  criterion 9 of the plan), which also found that the deny on the rendered settings file does not hold from a
  subdirectory (corrected by plan `2026-10-22-absolute-settings-deny`, which renders the absolute patterns; the owner's
  recheck on 2026-10-23 confirmed it). The decision `2026-10-22-installer-owns-the-edit-gate` is Accepted. A
  project-level setting that the installer can read without naming a module, so that a project may lower a cap, is
  not a candidate yet; add one if the owner wants it. A security review found one Medium finding, fixed; the fixes had
  no second reviewer.
- Out of the first version: Codex as a harness, a way of working for CAD and EDA,
  harness swap, three-way merge on upgrade, and migration of the old projects.

## Suggested order

`approve-specs`, `adopt-conventions`, `installer-core-verifier`, `module-approvals`,
`installer-interface`, `base-and-manifests`,
`ownership-and-upgrade`, `claude-harness`, `verify-opencode`, `opencode-harness`,
`groundwork-module`, `researcher-fetch-tool`, `code-work-plans`, `module-boundary-kit`,
`module-commands`, `module-checks`, `module-harness-paths`, `code-work-commit`,
`checkpoint-settings-and-caps`, `increment-loop-and-review-skills`, `push-checkpoint`, `compaction-guidance`,
`remote-runner-module`, `review-engine`, `delegated-approval`, `action-review-engine`,
`mempalace-module`, `graphify-module`, `knowledge-base-package`, `port-superpowers`, `global-config-migration`, `self-hosting`, `remaining-modules-rename`.

## Candidates

### approve-specs — Approve the specifications and record the decisions

**Outcome:** the specifications are reviewed and approved by the owner, and the
durable choices are written as decision records, so later work is built against a
settled design.
**Dependencies:** none.
**Boundary:** documents only. Possibly an independent review of the specs, at the
owner's request. No code.
**Promotion trigger:** the owner judges the design closed enough to build against.

### adopt-conventions — Adopt the new document conventions in this repository

**Outcome:** this repository's own documents follow the new conventions, so the work
that follows is planned, recorded and archived the way the specs say. The plans,
decisions and roadmaps READMEs and `AGENTS.md` describe dated plan and decision names,
the `Candidate:` and `Specs:` lines, and no fixed `next.md`; the placeholder `next.md`
is replaced by that convention; harness files and the old `.template-manifest` are
excluded before the first commit; and the documents state which checks are enforced by
the installer once built and until then by the owner in session.
**Dependencies:** `approve-specs`.
**Boundary:** documents and exclude entries only. No code. No mechanical enforcement.
Removing a stage-0 file uses the approved removal helper, with the owner's approval.
**Promotion trigger:** `approve-specs` complete.

### installer-core-verifier — Installer core and the declaration verifier

**Outcome:** a small installer core that writes only inside a target through a safe
layer, and a verifier that reads a package and its modules and accepts or refuses
them exactly as `module-contract` states, writing nothing when any module fails.
**Dependencies:** `adopt-conventions`.
**Boundary:** declarations, types, capabilities, requirements, conflicts and
verification. It writes nothing into a project. No approvals, manifests, harness or
upgrade. The safe-write rules are ported deliberately, with tests, from the old
template.
**Promotion trigger:** `adopt-conventions` complete.

### module-approvals — The guarded store and module approvals

**Outcome:** every command ensures the user-level guarded store exists and is seeded;
the hard-stop floor is compiled into the installer and also seeded into personal
settings; a package is downloaded inertly into the store's cache; module and package
approvals are recorded and verified against declaration and content hashes;
first-party approvals can be generated at release time and are read from the workbench
distribution; and the `wb` launcher and its pins exist.
**Dependencies:** `installer-core-verifier`.
**Boundary:** the store, module and package approvals, the verifier, and the launcher.
No project is written, and there is no plan approval or delegation helper yet.
**Promotion trigger:** `installer-core-verifier` complete.

### installer-interface — The installer's commands and options

**Outcome:** a specification of the installer's command line: the commands (install,
attach, upgrade preview, add module, verify, check), their options, exit codes, and the
preview and output contract. Requirements settled so far:

- The target directory is one value with two spellings, a positional `<target>` or
  `--dir <path>`, accepted by every project command. If neither is given the target is `.`.
  If both are given and resolve to the same directory that is accepted; if they
  differ the command refuses and writes nothing.
- The target is resolved to an absolute path once, and everything after that works
  from the resolved path.
- Whether a command creates a new project or works on an existing one is decided from
  the target's state, not from the spelling: an empty or missing directory (a lone
  `.git` is allowed) is new; a directory with its own `.git` and a manifest file is existing,
  decided from files without running git; anything else is refused with nothing written.
- Commands that write print the resolved absolute target before the preview.
- The home directory, the filesystem root and the guarded store are refused as targets.

**Dependencies:** `module-approvals`, because the approval and store behavior decides
which options are needed.
**Boundary:** a specification only, approved by the owner. Option names and formats stay
proposals until the code that uses them exists. `installer-core-verifier` defines only
its own verify command.
**Promotion trigger:** `module-approvals` complete.

### base-and-manifests — Base, manifests and installing into an empty target

**Outcome:** install creates the base content, the project seed and ID, the committed
manifest and the tracked `.workbench/.gitignore` in a new target, from a chosen set of
modules, without a harness step yet.
**Dependencies:** `module-approvals`, `installer-interface`.
**Boundary:** the base and the committed manifest only. Attach, upgrade and the local
manifest are later candidates. The mandatory-harness rule is enforced when attach
exists.
**Promotion trigger:** `module-approvals` and `installer-interface` complete.

### ownership-and-upgrade — Ownership, slots and non-destructive upgrade

**Outcome:** owner classes are recorded, slots and blocks work, and an upgrade shows a
full preview and changes nothing until approved, leaving conflicts alone and offering
an append on approval where a seeded file lacks a needed slot.
**Dependencies:** `base-and-manifests`.
**Boundary:** the upgrade and its preview only. Format migrations are not included.
**Promotion trigger:** `base-and-manifests` complete.

### claude-harness — Claude harness module, attach and check

**Outcome:** a Claude harness module, an attach operation that writes only per-clone
harness files, rendering of the neutral permission rules, the root file, and a check
that reports drift, stray files and tracked-pointer problems.
**Dependencies:** `ownership-and-upgrade`, `module-approvals`.
**Boundary:** Claude only. Translating neutral skills, agents and commands, with
fail-closed handling of restrictions the harness cannot express. It must render a `deny`
for the owner-run commands `wb install`, `upgrade`, `add`, `attach`, `acknowledge`, `recover`,
`approve`, `pin` and `release-approvals` (`trust-and-approval.md`, "Rendering rules"), and call `wb` and not the
`-m` form. `opencode-harness` carries the same duty.
**Promotion trigger:** `ownership-and-upgrade` and `module-approvals` complete.

### verify-opencode — Verify the installed opencode against the specification

**Outcome:** a written, evidence-based answer to the open questions about opencode:
the formats of its installed version, how a per-clone permission rendering can be done
without editing a tracked file, whether a specific tool can be given to one agent, and
how compaction guidance is delivered.
**Dependencies:** none technical; best after `claude-harness` so the comparison is
concrete.
**Boundary:** investigation and a recorded conclusion. No harness module is built.
**Promotion trigger:** the owner chooses to proceed with opencode.

### opencode-harness — opencode harness module

**Outcome:** an opencode harness module that attaches and checks as `claude-harness`
does, with whatever `verify-opencode` showed to be possible.
**Dependencies:** `claude-harness`, `verify-opencode`.
**Boundary:** opencode only.
**Promotion trigger:** `verify-opencode` concluded.

### groundwork-module — The `groundwork` module

**Outcome:** the module that provides specs, roadmaps, decisions and references, with
its templates, skills, indexes and checks. It ships no code.
**Dependencies:** `ownership-and-upgrade`, `claude-harness`.
**Boundary:** the four document areas and their checks. The researcher and the
`fetch-reference` tool are the separate `groundwork-research` module.
**Promotion trigger:** `claude-harness` complete.

### researcher-fetch-tool — The `groundwork-research` module

**Outcome:** the optional `groundwork-research` module: a least-privilege researcher
agent and a dedicated `fetch-reference` tool that only it holds, with the size, type
and provenance limits the specification states.
**Dependencies:** `groundwork-module`, and a verified way for each harness to give one
tool to one agent (`claude-harness` for Claude, `verify-opencode` for opencode).
**Boundary:** web references only. Remote job output and the knowledge base are other
channels.
**Promotion trigger:** `groundwork-module` complete and tool exposure verified.

The `code-work` module (`docs/specs/code-work.md`) is too large for one plan, so it is
three candidates built in this order, each leaving a working module. The first plan
creates the module; the next two add to it and release the package again.

### code-work-plans — The `code-work` module: plans and its read-only helper

**Outcome:** the process module `code-work` exists in `packages/workbench/`: the plan
format, the `docs/plans/` README, a `docs-index` entry, a policy block, a skill for
drafting a plan, and one shipped, self-contained helper whose read-only subcommands
`check`, `plans` and `report` are run as `wb run code-work <subcommand>`, a command the module
declares, through the launcher; the installer pins the helper when the owner confirms the install. It
proves the path every later helper subcommand uses: shipping, pinning, launching and reading untrusted
plans.
**Dependencies:** `module-approvals`, `claude-harness`, `groundwork-module`.
**Boundary:** reading only. No commit or remove, no approval record, no review loop,
caps, checkpoint or push rule. Until plan `2026-10-22-plan-approval-records`, approval was the owner's
explicit statement in session and the policy block says so.
**Promotion trigger:** `groundwork-module` complete.

The next four candidates carry out `docs/specs/module-boundary.md` and the decision
`2026-10-21-module-code-lives-in-modules`: module-specific code, tests and tooling leave the
installer for the modules. The open `code-work-plans` plan was reconsidered after
`module-commands` and its increments F to H were amended for the installer pinning declared helpers
(`2026-10-22-installer-pins-declared-helpers`).

### module-boundary-kit — The kit and the maintainer directories

**Outcome:** the installer's reading code (`safefs`, `display`, project finding and the
project ID) lives in a standard-library kit, `wbkit`, with an API version; the launcher can
start a Python helper through a runner that enforces the version the module declared; a
module may hold `tests/` and `tools/`, which are hashed and approved and never installed;
one command runs the installer's tests and every module's.
**Dependencies:** `code-work-plans` (increments A to E).
**Boundary:** no new user-visible command and no module code moves except one module's
tests, as proof. `commands`, `checks` and `wb run` are later candidates.
**Promotion trigger:** the specification `module-boundary` is Current.

### module-commands — Module commands and `wb run`

**Outcome:** a module declares `commands`, the verifier checks them, and `wb run` runs the
pinned helper by the rules of the specification, including the pin-path check; `dispatch.py`
and the `code-work` entries in the installer are gone, and the `code-work` tests move into
the module.
**Dependencies:** `module-boundary-kit`.
**Boundary:** commands only. Checks and harness paths are separate.
**Promotion trigger:** `module-boundary-kit` complete.

### module-checks — Module checks and the groundwork move

**Outcome:** a module declares `checks`; `wb check` runs them and prints their bounded
lines; the document checks (`doccheck`, `refcheck`, `refindex`) and their tests move into
`groundwork` as check helpers over the kit.
**Dependencies:** `module-commands`.
**Boundary:** the rules a check reports do not change. A security pass is part of it,
because the helpers read hostile repository content.
**Promotion trigger:** `module-commands` complete.

### module-harness-paths — Harness paths from the harness module

**Outcome:** the harness table in `check.py` and the settings path in `layout.py` are read
from the harness module's `layout`; a
boundary test fails if the installer or its tests name a first-party module, helper,
harness name or harness path.
**Dependencies:** `module-checks`.
**Boundary:** no new harness. `opencode` and `codex` entries with no module are removed.
**Promotion trigger:** `module-checks` complete.

### code-work-commit — The commit helper

**Outcome:** the helper gains `commit` and `remove`, so a commit is local, lists exact
paths, carries no tool attribution unless a project says otherwise, and can be the first
commit in a repository with no commits; it leaves the acknowledgement baselines to the
owner, so a change made through it is listed by the next `wb acknowledge`. The helper was built in
`code-work` and then moved to the `safe-git` module (`2026-10-22-safe-git-module`).
**Dependencies:** `code-work-plans`.
**Boundary:** local commits and approved deletions only. It never pushes. The helper
reads a repository the project controls, so a security pass is part of it.
**Promotion trigger:** `code-work-plans` complete.

### checkpoint-settings-and-caps — The checkpoint settings, the loop caps and the gate

**Outcome:** the checkpoint settings (which actions stop for the owner), the loop caps (review rounds and
increment attempts), and an enforcement point that refuses work on a plan whose record does not read `approved`
(a hook or a deny rule the module renders; the record and the `plan-status` command exist already).
**Dependencies:** `code-work-commit`; plan `2026-10-22-plan-approval-records` (built).
**Boundary:** programming only. Settings and the enforcement point; no skills, no reviewer agent, no push rule.
The enforcement point is the installer's `wb gate`, rendered as a Claude hook (built).
**Promotion trigger:** the owner chooses to begin it.

### increment-loop-and-review-skills — The increment loop, the review skills and the reviewer agent

**Outcome:** the neutral skills for one increment (implement, verify, record, stop for the owner), the review
skills (what to ask a reviewer, how to evaluate findings, the review record), and the reviewer agent.
**Dependencies:** `checkpoint-settings-and-caps`.
**Boundary:** skills and one agent definition, in the owner's words and the project's own locations. No review
engine and no vendor.
**Promotion trigger:** `checkpoint-settings-and-caps` complete.

### push-checkpoint — The shared-branch push checkpoint

**Outcome:** a push to a shared branch is a checkpoint the owner decides, with the credential scan before it,
rendered as a rule the harness enforces.
**Dependencies:** `checkpoint-settings-and-caps`.
**Boundary:** the checkpoint and its rule. The commit helper and `remove` stay in `safe-git`.
**Promotion trigger:** `checkpoint-settings-and-caps` complete.

### compaction-guidance — The compaction guidance

**Outcome:** the preservation guidance for compaction, as a bullet of the `code-work` policy block.
**Dependencies:** `claude-harness`.
**Boundary:** the guidance text in the policy block. No rendered "Compact Instructions" section (Claude's
documentation names none), no hook and no wrapper that triggers compaction from outside a session.
**Promotion trigger:** the owner chooses to begin it.

### remote-runner-module — `remote-runner` as a generic module

**Outcome:** the remote-runner configuration moves under `.workbench/`, and fetching
remote job output follows the checkpoint and hard-stop rules.
**Dependencies:** `claude-harness`, `checkpoint-settings-and-caps`.
**Boundary:** the module and its configuration. The `remote-runner` tool itself must
learn the new path, which is a change outside this repository.
**Promotion trigger:** `checkpoint-settings-and-caps` complete.

### review-engine — The review engine

**Outcome:** the review module, which provides the `peer-review` capability and requires `model-bridge`. It holds
the rounds, the sealed review state, the findings schema (blocker, major, minor, nit), `decide`, and the
owner-only `extend`, `reset`, `archive` and `prune`; it reads its bridge, model and effort from its own project
setting `.workbench/<module>.json` and runs a bridge only through `wb run --provides model-bridge`. It replaces the
owner's personal review tool for a project.
**Dependencies:** `checkpoint-settings-and-caps` (the loop caps); the `ask-codex` bridge (plan
`2026-10-22-ask-codex-bridge`).
**Boundary:** one engine that knows no vendor. Where the sealed state lives is decided in its plan (the owner's
tool keeps it in untracked scratch, which a module must not depend on). The bridges are separate modules, one
per vendor.
**Promotion trigger:** `checkpoint-settings-and-caps` complete.

### delegated-approval — Delegated plan approval

**Outcome:** a plan approval made by a delegate under the owner's standing authorization, as the delegation
helper and a record that names its delegate and its review, bound to the same hashed region.
**Dependencies:** `review-engine` (it needs the `peer-review` capability); plan
`2026-10-22-plan-approval-records` (built).
**Boundary:** the delegation helper, its record fields and its verdict rule
(`trust-and-approval.md`, "Plan approval"). The owner's own approval stays as built.
**Promotion trigger:** `review-engine` complete.

### action-review-engine — The action-review engine

**Outcome:** the action-review module (the capability name `action-review` is a proposal), which requires
`model-bridge`, takes facts about an action and returns a verdict with reasons as data, from a rubric and rules.
It writes no `allow` rule and no setting, and its verdict authorizes nothing by itself
(`2026-10-22-model-calls-go-through-vendor-bridges`, decisions 6 and 7).
**Dependencies:** `checkpoint-settings-and-caps`; the `ask-codex` bridge; a way for the module that owns an action to give
the facts before the action is made (open in the accepted record).
**Boundary:** a rubric and rules engine, not a reviewer of documents; the enforcement point that uses its verdict
stays in the owner's own configuration. It is separate from `review-engine`, and a project may install either.
**Promotion trigger:** `checkpoint-settings-and-caps` complete and the facts interface decided.

The next three candidates are the knowledge modules, each solving a different problem and none replacing
another (`docs/specs/knowledge-tools.md`): `mempalace` recalls earlier sessions and decisions, `graphify` shows
structure and impact, and the knowledge base keeps classified online research. They are built in this order,
because the first is the smallest and the least entangled; a shared convention is written down only from what
the first two show.

### mempalace-module — The `mempalace` module

**Outcome:** the first-party module `mempalace`, which provides `memory-recall`: the agent-safe commands
`status` and `search` over the owner's installed MemPalace, the owner-run `init` and `mine`, a policy block and a
neutral skill that route questions and treat answers as data. It is tooling and not an MCP server.
**Dependencies:** `module-commands`, `claude-harness`. The first plan must settle the open
questions in `docs/specs/mempalace.md` ("Evidence and open questions") by running the real program in a
scratch palace under `/.debug/`.
**Boundary:** the module and its tests, with a fake `mempalace` in the tests. No write an agent can make, no
MCP rendering, and no installation or configuration of the program. Writes to the palace are owner-run only.
**Promotion trigger:** the owner approves `docs/specs/mempalace.md` and `docs/specs/knowledge-tools.md`.

### graphify-module — The `graphify` module

**Outcome:** the optional module `graphify`, which provides `code-graph`, ported from the owner's
`claude_global_config` (the `graphify-workflow` skill and its helper) and `claude_project_template` (the guidance,
`.graphifyignore` and ignore entries). It keeps the freshness status, the rule that an old graph is orientation
only, and the plan receipt, written as neutral skills and a pinned helper.
**Dependencies:** `mempalace-module` (for the shared conventions it shows), `code-work-plans` (the plan
evidence section).
**Boundary:** the module and a spec of its own. It does not ingest conversation history or the knowledge base.
The graph output is untracked. This candidate takes `graphify` out of `remaining-modules-rename`.
**Promotion trigger:** `mempalace-module` complete and the owner chooses to begin it.

### knowledge-base-package — The knowledge base as a package

**Outcome:** the knowledge base adopts the workbench's package declaration, gets its
generic name, provides its own capability (`knowledge-base`), and is read through a read-only skill. It holds,
retains and classifies the owner's online research per domain, each item with its provenance.
**Dependencies:** `claude-harness`, `groundwork-module`; the conventions of `mempalace-module` and
`graphify-module`.
**Boundary:** the knowledge base's own repository changes. Its name is still open. It does not hold decisions
or conversation, and nothing tracked cites a path into it.
**Promotion trigger:** `groundwork-module` complete and the name chosen.

### port-superpowers — Port the superpowers skills the owner uses into neutral skills

**Outcome:** an inventory of the superpowers skills the owner's global configuration and agents
rely on (brainstorming, planning, plan execution, code review, test-driven development, systematic
debugging, verification before completion, worktrees and branch finishing), each recorded as used
or not, already covered by a workbench rule or skill, or a gap; the module each ported skill belongs
to; and the first ports as neutral skills, written in the workbench's own words, in the project's
own locations (`docs/specs/`, `docs/plans/`), with no harness named. Brainstorming is expected to
go to `groundwork` as a step before `draft-spec`; the rest to `code-work` or `safe-git`, unless
the inventory shows a practice that every process shares, which would argue for a module of its own.
**Dependencies:** `claude-harness`, `groundwork-module`, `increment-loop-and-review-skills` (which owns the
increment loop, review and reviewer-agent skills).
**Boundary:** the inventory, the placement decisions, and the skills the inventory selects first. The
git-specific slice was taken by `2026-10-22-safe-git-module`: the `commit-changes` skill is written, and
`using-git-worktrees` and `finishing-a-development-branch` are recorded as not ported, with the reasons, in
`docs/specs/safe-git.md`; this candidate starts from that and does not revisit git.
Each further port is its own candidate. Whether the superpowers wording may be reused is checked
against its licence before any text is copied, and the default is to write new text. Removing
superpowers from the owner's `~/.claude` belongs to `global-config-migration`.
**Promotion trigger:** `increment-loop-and-review-skills` complete.

### global-config-migration — Move the owner's global Claude configuration into modules

**Outcome:** the owner's `~/.claude` returns to a mostly default state because what it
carried for project work is now supplied by installed modules: agents, skills, commands,
the policy text, the commit helper, the review wiring and the compaction guidance.
What stays global, and why, is a written list: the owner's own `allow` rules (the
workbench never writes `allow`), machine-level settings such as authentication, model
choice and remote hosts, and anything the owner wants in a project that has no workbench.
**Dependencies:** `checkpoint-settings-and-caps`, `increment-loop-and-review-skills`, `push-checkpoint`,
`compaction-guidance`, `remote-runner-module`, `review-engine`, `action-review-engine`, and
`groundwork-module`; hooks rendering for Claude (built by `checkpoint-settings-and-caps`).
**Boundary:** one global item at a time, each moved only after a test or a recorded run
shows a project behaves the same without the global copy, so no hard stop, deny rule or
approver is ever absent in between. The `claude_global_config` mirror is kept in step
(`~/.claude` and the mirror are updated together). It also settles the open question
whether the settings file's own path is denied for edits (`harness-modules.md`, "As built,
and its limits"). It does not move the owner's `allow` rules and does not change what
the installer writes.
**Promotion trigger:** `checkpoint-settings-and-caps`, `increment-loop-and-review-skills`, `push-checkpoint`,
`compaction-guidance`, `remote-runner-module`, `review-engine` and
`action-review-engine` complete, and the owner chooses to begin removing items from `~/.claude`. Each of those
earlier plans lists the global items it replaces, so this candidate starts from that list.

### self-hosting — Self-hosting

**Outcome:** this repository's own files are checked against what the installer would
generate, and the old template is retired. The document conventions were already
adopted by `adopt-conventions`, so this candidate is only the proof of agreement and the
retirement.
**Dependencies:** `ownership-and-upgrade`, `claude-harness`, `groundwork-module`,
`checkpoint-settings-and-caps`, `increment-loop-and-review-skills`, `push-checkpoint`, `compaction-guidance`.
**Boundary:** agreement between hand-maintained files and generated output, and the
retirement of the old template, and approving this repository's own plans with `wb approve-plan`. The installer
does not rewrite its own repository until that agreement is tested.
**Promotion trigger:** `checkpoint-settings-and-caps`, `increment-loop-and-review-skills`, `push-checkpoint` and
`compaction-guidance` complete.

### remaining-modules-rename — Remaining modules and the rename pass

**Outcome:** the `formal` module and the CAD domain
modules are ported, and the module list is renamed consistently. (`graphify` moved to `graphify-module`.)
**Dependencies:** `claude-harness`.
**Boundary:** porting and renaming. Each ported module is checked against the
specification. Nothing here is required by `code-work`.
**Promotion trigger:** the owner chooses a module to port.

## Deferred

- A way of working for CAD and EDA (`cad-work`), until a project shows it is needed.
- Codex as a harness.
- Changing harness as an installer feature; the supported route is a new clone.
- Three-way merge on upgrade.
- Migration of projects made from the old template.
- A local pre-push git hook that runs the check.
- A wrapper that triggers compaction from outside a session.

## Related decisions

Accepted 2026-10-19, in `docs/decisions/`:

- `2026-10-19-closed-module-types`
- `2026-10-19-harness-files-per-clone`
- `2026-10-19-uniform-package-trust`
- `2026-10-19-guarded-store`
- `2026-10-19-compiled-hard-stop-floor`
- `2026-10-19-restrictive-only-permissions`
- `2026-10-19-mandatory-review-personal-delegation`
- `2026-10-19-groundwork-shared-layer`
- `2026-10-19-derived-completion-slugs-dated-names`
- `2026-10-19-non-destructive-upgrades`
- `2026-10-19-tracked-pointer-rule`
- `2026-10-19-implementation-language`

Accepted 2026-10-20:

- `2026-10-20-fixed-store-location`
- `2026-10-20-first-party-by-location-and-shipped-record`
- `2026-10-20-isolated-launcher-invocation`
- `2026-10-20-target-decided-by-state`
- `2026-10-20-preview-then-owner-run-write`

Accepted 2026-10-21:

- `2026-10-21-reference-index-format`
- `2026-10-21-installer-runs-document-checks`

Accepted 2026-10-22:

- `2026-10-22-git-work-in-its-own-module`
- `2026-10-22-model-calls-go-through-vendor-bridges`
