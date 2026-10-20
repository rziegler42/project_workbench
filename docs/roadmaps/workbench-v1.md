# Roadmap: workbench-v1

Status: Active
Updated: 2026-10-19

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
  built with `code-work-module`, because the plan format names the sections they
  depend on.
- **The installer is not run on its own repository** until `self-hosting` has shown,
  by a test, that its output agrees with the hand-maintained files.
- **The commit helper does not exist while it is being built.** Until `code-work-module`
  ships it, commits are made with the owner's own tooling.

## Current state

- The old template created this repository. `adopt-conventions` is done (2026-10-19):
  the repository's own documents follow the new conventions, and harness files and the
  old template manifest are excluded from git. The old template is retired at
  `self-hosting`.
- Seven specifications are approved by the owner (2026-10-19) and read `Current`:
  `terms`, `module-contract`, `repository-boundary`, `trust-and-approval`,
  `groundwork`, `code-work` and `harness-modules`. Implementation has not started.
- Twelve decision records are accepted (2026-10-19), listed under Related decisions.
- `installer-core-verifier` is built and its language decision is accepted
  (`2026-10-19-implementation-language`, 2026-10-19): a Python 3
  package `workbench/` with the safe filesystem layer, hashing, declaration and module
  verification, set verification and `python3 -m workbench verify`. It writes nothing
  into a project. `module-contract` records the concrete schema it accepts.
- Out of the first version: Codex as a harness, a way of working for CAD and EDA,
  harness swap, three-way merge on upgrade, and migration of the old projects.

## Suggested order

`approve-specs`, `adopt-conventions`, `installer-core-verifier`, `module-approvals`,
`installer-interface`, `base-and-manifests`,
`ownership-and-upgrade`, `claude-harness`, `verify-opencode`, `opencode-harness`,
`groundwork-module`, `researcher-fetch-tool`, `code-work-module`,
`remote-runner-module`, `peer-review-provider`, `knowledge-base-package`,
`self-hosting`, `remaining-modules-rename`.

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
  `--dir <path>`, accepted by every command. If neither is given the target is `.`.
  If both are given and resolve to the same directory that is accepted; if they
  differ the command refuses and writes nothing.
- The target is resolved to an absolute path once, and everything after that works
  from the resolved path.
- Whether a command creates a new project or works on an existing one is decided from
  the target's state, not from the spelling: an empty or missing directory (a lone
  `.git` is allowed) is new; a directory with a committed manifest is existing;
  anything else is refused with nothing written.
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
fail-closed handling of restrictions the harness cannot express.
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

### code-work-module — The `code-work` module

**Outcome:** the programming way of working: the plan format and its checks, plan
approval and the delegation helper, the increment loop, review, checkpoints and loop
caps, the commit helper behind `wb` (including the first commit in a repository with no
commits, which the current helper cannot make), the shared-branch configuration, and
the policy block.
**Dependencies:** `module-approvals`, `claude-harness`, `groundwork-module`.
**Boundary:** programming only. Remote jobs and the peer-review provider are separate.
**Promotion trigger:** `groundwork-module` complete.

### remote-runner-module — `remote-runner` as a generic module

**Outcome:** the remote-runner configuration moves under `.workbench/`, and fetching
remote job output follows the checkpoint and hard-stop rules.
**Dependencies:** `claude-harness`, `code-work-module`.
**Boundary:** the module and its configuration. The `remote-runner` tool itself must
learn the new path, which is a change outside this repository.
**Promotion trigger:** `code-work-module` complete.

### peer-review-provider — The peer-review provider module

**Outcome:** the reviewer module, which takes a harness and a model setting and
supplies the `peer-review` capability, replacing the old Codex tool module.
**Dependencies:** `module-approvals`, `code-work-module`.
**Boundary:** one provider. Others can be added as separate modules.
**Promotion trigger:** `code-work-module` complete.

### knowledge-base-package — The knowledge base as a package

**Outcome:** the knowledge base adopts the workbench's package declaration, gets its
generic name, provides its own capability, and is read through a read-only skill.
**Dependencies:** `claude-harness`, `groundwork-module`.
**Boundary:** the knowledge base's own repository changes. Its name is still open.
**Promotion trigger:** `groundwork-module` complete and the name chosen.

### self-hosting — Self-hosting

**Outcome:** this repository's own files are checked against what the installer would
generate, and the old template is retired. The document conventions were already
adopted by `adopt-conventions`, so this candidate is only the proof of agreement and the
retirement.
**Dependencies:** `ownership-and-upgrade`, `claude-harness`, `groundwork-module`,
`code-work-module`.
**Boundary:** agreement between hand-maintained files and generated output, and the
retirement of the old template. The installer does not rewrite its own repository until
that agreement is tested.
**Promotion trigger:** `code-work-module` complete.

### remaining-modules-rename — Remaining modules and the rename pass

**Outcome:** the optional `graphify` module, the `formal` module and the CAD domain
modules are ported, and the module list is renamed consistently.
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
