# The installer's commands and options

Status: Approved
Created: 2026-10-20
Candidate: workbench-v1#installer-interface
Specs: repository-boundary, trust-and-approval, module-contract

## Goal

Write one specification, `docs/specs/installer-interface.md`, of the installer's command line,
so `base-and-manifests` and the candidates after it are built against a settled interface and
not one invented while coding. It covers the commands (install, attach, check, upgrade, add a
module, and the five that exist: verify, approve, pin, launch, release-approvals), their
options, how the target is chosen, the preview and approval flow, the output, and the exit
codes.

When this plan is done the owner has approved a spec that says, for every command, what it
reads, what it may write, what it refuses, who may run it, and what it prints and returns.
The five commands that exist are described as they are, and any change to them is named for
a later plan to make. No code changes.

## Scope

- The requirements the roadmap already settles, written as rules: the two spellings of the
  target (`<target>` and `--dir <path>`), the default `.`, the same-directory test, the
  one-time resolution to an absolute path, new versus existing decided from the target's
  state, the resolved target printed before a preview, and the refused targets (the home
  directory, the filesystem root and the guarded store).
- Which commands take a project target and which take a package, a project id or nothing.
  The plan reads the roadmap's "every command" as every command that acts on a project
  (install, attach, check, upgrade, add a module), and the target rules govern those
  without exception. The existing `verify` and `approve` take a package directory, and
  `pin` and `launch` take `--root`; they act on a package or a helper and not on a
  project's state. The one question left for the owner (Increment A) is whether those
  four also accept the two spellings, and under what meaning.
- Each command: purpose, arguments, options, what it reads and writes, what it refuses
  with nothing written, and whether it is owner-run (terminal only) or may be run by an
  agent.
- The preview and approval flow for install, upgrade and add-a-module: what a preview
  shows, how it is approved, and how the approval binds to what is then written.
- The output contract and the exit codes, including how a refusal is told from a helper's
  own exit code, and how a warning is told from an error.
- How the commands are invoked: the `wb` launcher is the form the harness uses
  (decision `2026-10-20-isolated-launcher-invocation`), and the usage text says so.
- Edits to other documents that follow: `repository-boundary` points to the new spec
  for operation options, the specs README lists it, and the roadmap's current state is
  updated.

## Non-goals

- Any code or test, including changing the existing parser or usage text.
- The contents of a base, a manifest or a harness, and the translation of neutral items.
  Those belong to `base-and-manifests`, `claude-harness` and later candidates.
- Settling option names for a command whose behavior is not yet specified in detail
  elsewhere (migration, module removal, three-way merge). The spec says they do not exist.
- The plan-approval and delegation commands, which `code-work-module` defines.
- Shell completion, a configuration file for options, and environment-variable overrides.
  The store location in particular stays fixed (decision `2026-10-20-fixed-store-location`).
- Committing, pushing or publishing anything beyond what the owner approves in session.

## Assumptions and constraints

- Discovery tooling: skipped. This project provides none. The scope was checked directly
  against `workbench/cli.py`, the plan and spec text, and the roadmap candidate.
- The roadmap says option names and formats stay proposals until the code that uses them
  exists. The spec therefore separates **rules** (the target rules, who may run what, what
  is refused, the exit codes) from **proposals** (option and command spellings), and marks
  each. Approving the spec approves the rules.
- The target rules above are settled by the owner in the roadmap and are written as given,
  not reopened. Changing one needs the owner's say.
- A command that writes a project must not run before the installer can show the owner what
  it will write and the owner has approved it; the spec must not describe a flow that skips
  the preview.
- Approval stays the owner's act. The spec must keep `approve` and `pin` terminal-only
  and must not give an agent-run command a way to record an owner approval in the guarded
  store. `release-approvals` is different and stays as built: a maintainer's release-time
  command that needs no terminal and writes only the shipped first-party records in the
  workbench distribution, never the guarded store. The spec distinguishes the two.
- The installer never commits, pushes or publishes (`repository-boundary`). The spec
  states that for every command, including upgrade, which leaves its changes uncommitted.
- Anything in this plan that is inferred from the current code and not from a spec is marked
  as such in the spec, so a reader can tell a rule from a description.

## Completion criteria

- `docs/specs/installer-interface.md` exists and contains: the target rules; the
  state-based new-or-existing rule with a table of target states and outcomes; a command
  table; one section per command; the preview and approval flow; the output and exit-code
  contract; a list of rules separated from proposals; deferred items; and acceptance
  criteria.
- Every command in the roadmap outcome (install, attach, upgrade preview, add module,
  verify, check) has a section, and each existing command is described and consistent with
  `workbench/cli.py` as it is.
- For each command the spec states whether an agent may run it. Every command that
  records an owner approval or pin in the guarded store is terminal-only, and
  `release-approvals` is described as the release-time command that writes only shipped
  records.
- Each target state (missing, empty, a lone `.git`, a committed manifest, anything else,
  the home directory, the root, the guarded store, two spellings that differ) has a stated
  outcome, and none writes before the refusal.
- Every open question the spec raises is answered by the owner and recorded, or listed under
  Deferred with a reason.
- `repository-boundary`, `trust-and-approval` and `module-contract` contain no statement
  that contradicts the new spec, and the specs README and the roadmap list it.
- The owner has approved the spec and its status reads `Current`, with a line saying that
  only the commands marked built exist.
- No file outside `docs/` changes, and the existing test suite still passes unchanged.

## Increments

### Increment A — Target rules and the command inventory

Dependencies: None
Affected areas: `docs/specs/installer-interface.md` (new)

Outcome: the spec exists with its purpose, the target rules and the inventory of commands,
and the open questions about the target are put to the owner.

1. Create the spec with a `Status: Draft` line, a purpose and scope, and the terms it uses
   (target, project target, package, project id) taken from `terms.md` and not redefined.
2. Write the target rules exactly as the roadmap settles them: two spellings, default `.`,
   agree-or-refuse, resolve once, state decides new or existing, print before a preview,
   refuse the home directory, the root and the guarded store.
3. Define "the same directory" as the existing `verify` does (symbolic links and `..`
   resolved), and state that a target is checked after resolution, so a link to the home
   directory or the store is also refused.
4. Write a table of target states and outcomes: missing, empty, empty with a lone `.git`,
   holding a committed manifest, a file and not a directory, a symbolic link, a directory
   with other content, and each refused place.
5. Write the command inventory as a table: name, what it takes (project target, package,
   project id, none), whether it writes a project, whether it writes only the guarded
   store, and whether it is terminal-only.
6. List the questions only the owner can answer, each with a recommended answer, and
   present them: whether `verify` and `approve` share the two spellings for their package
   argument; whether `pin` and `launch` keep `--root` or also accept `--dir`; and whether a
   symbolic link as a target is refused or resolved. Which project commands take the
   target is not a question: all of them do. Record the answers in the spec.

Verification: each rule in the roadmap candidate appears once in the spec; every state in
the table has an outcome; the open questions are answered or deferred; the spec cites no
path under `.debug/`.

Evidence: the spec's target section and tables match the roadmap candidate, and the owner's
answers are in the text.

### Increment B — The commands and their options

Dependencies: Increment A
Affected areas: `docs/specs/installer-interface.md`

Outcome: every command has a section the next candidate can build from.

1. For `install`: arguments, the module selection and how a harness is chosen (a harness is
   mandatory), what it verifies and requires approved before writing, the write order from
   `module-contract`, what is written, and the point after which nothing is written
   without the preview approved.
2. For `attach`: runs inside an existing clone, writes only per-clone harness files,
   refuses when a local manifest already records a harness, and what it prints for steps it
   cannot perform.
3. For `check`: read-only, what it reports, and that a clone with no harness attached is
   valid and printed as "none attached".
4. For `upgrade` and for adding a module: the preview, its classes (replace, skip,
   conflict, append), the clean-tree requirement for the affected paths, the refusal of an
   older workbench than the manifest records, and that changes are left uncommitted.
5. For the five existing commands: describe them as `workbench/cli.py` has them, marking
   each as built, and name any difference from the rules above (for example `verify`'s
   package argument, and `--root` on `pin` and `launch`) as a change for a later plan.
6. Mark every option and command spelling as a proposal, and every rule as a rule.
7. State, for each command, that it never commits, pushes or publishes.

Verification: each command in the roadmap outcome has a section; each section says what the
command reads, writes and refuses; each states whether an agent may run it; every existing
command's section agrees with `workbench/cli.py`, checked by reading it and by running
`python3 -m workbench` with no arguments to compare the usage text.

Evidence: the command sections, with the built and proposed marks, and the recorded check
of the existing commands against the code.

### Increment C — The preview, the approval flow, the output and the exit codes

Dependencies: Increment B
Affected areas: `docs/specs/installer-interface.md`

Outcome: how a write is previewed and approved, and what every command prints and returns,
are settled.

1. Specify the preview: it is produced by a read-only step, lists every file or block by
   path and owner class and whether it is created, replaced, skipped, a conflict or an
   append, shows the resolved target first, and shows the package and module hashes the
   writing will rely on. Nothing in a preview is truncated, and package text is shown as
   ASCII, as `request.py` already does for an approval request.
2. Specify how a preview is approved and how the approval binds to what is written: the
   write re-verifies and writes exactly what was previewed, and refuses if anything it
   depends on changed since. State whether approval is a terminal step run by the owner,
   and which command gives it, consistent with the rule that an agent cannot approve. This
   is a decision for the owner and is recorded as one (see Increment D).
3. Specify the output contract: what goes to standard output and to standard error, the
   `refused:` and `warning:` prefixes the code already uses, that text from a package is
   cleaned before printing, and whether a machine-readable form exists. Recommend none in
   this version, with a reason, unless the owner wants one.
4. Specify the exit codes: 0 done, 1 refused with nothing written, 2 usage error, and
   whether a further code is needed to tell "a preview was produced and needs approval"
   from a refusal. Note that a launched helper's own exit code is returned as it is.
5. Specify the failure rule: a command that fails midway reports what was written, and
   states whether it is safe to run again.

Verification: the preview, approval, output and exit-code sections agree with each other
and with `trust-and-approval`; no flow lets an agent-run command write a project without a
preview the owner approved; the exit codes agree with `cli.py` for the existing commands.

Evidence: the completed sections and the owner's recorded answers on approval and exit
codes.

### Increment D — Align the other documents and record the decisions

Dependencies: Increment C
Affected areas: `docs/specs/README.md`, `docs/specs/repository-boundary.md`,
`docs/specs/trust-and-approval.md`, `docs/specs/module-contract.md`,
`docs/roadmaps/workbench-v1.md`, `docs/decisions/` and its index

Outcome: no document contradicts the new spec, and each durable choice has a record.

1. Add the spec to the specs README table.
2. In `repository-boundary`, keep the operation rules and point to the new spec for
   options, arguments and exit codes, without repeating them.
3. Search the three existing specs for wording about commands, targets, previews or exit
   codes, and reconcile each.
4. Update the roadmap's current state and the candidate's outcome, without recording
   completion (completion is derived from this plan).
5. Draft a decision record, as `Proposed`, for each durable choice the owner made in
   Increments A to C that outlasts this spec. Candidates, to be confirmed when the choices
   are made: the target is decided by the state of the directory and not by the spelling;
   a project write is previewed and approved before it happens. Add each to the decisions
   index. The owner accepts a record; this plan never does.

Verification: `grep` for the old wording turns up no contradiction; the index lists every
new record; each new record has `Status: Proposed` until the owner changes it.

Evidence: the changed documents, the new records, and the grep output.

### Increment E — The owner approves the spec

Dependencies: Increment D
Affected areas: `docs/specs/installer-interface.md`, this plan's Result section

Outcome: the spec reads `Current`.

1. Ask the owner to read the spec and approve it, or list corrections.
2. Apply the corrections and ask again, until the owner approves or stops.
3. On approval, change the spec's status line to `Status: Current` with the date and a
   line saying that only the commands marked built exist and the rest are proposals until
   their candidates are built.
4. Do not change the status of any decision record unless the owner accepts it.

Verification: the spec's status line was changed only after the owner's explicit approval
in session; no spec is marked `Current` without it.

Evidence: the status line and the owner's statement, recorded in the Result section.

## Verification

- `python3 -B -W error -m unittest discover -s tests` passes unchanged. No code or test
  file changes, so a change in the count would show an accident.
- `git status --short` shows only files under `docs/` before each commit, and nothing under
  `.debug/`, `.claude/` or `CLAUDE.md`.
- The spec cites no path under `.debug/`, and no tracked document depends on untracked
  content.
- Each command in the spec is checked against `workbench/cli.py` where it already exists.
- Each increment's commit names only changes present in its diff and carries
  `Plan: 2026-10-20-installer-interface#<label>`.
- `git diff --check` is clean.

## Risks and sensitive actions

- **A flow that lets an agent-run command write a project.** The main risk in an interface
  spec is a convenience that quietly removes the owner's approval, for example a `--yes`
  flag or a non-terminal approval. The spec must not add one, and Increment C is checked
  against this.
- **Designing ahead of the code.** Options settled now may not survive `base-and-manifests`.
  The proposals are marked, only the rules are approved, and a later plan may revise the
  spec in place.
- **Overlap with the existing commands.** Renaming `--root` or the package argument would
  change commands that have users. The spec only names such a change; it makes none.
- **The target refusals depend on resolution.** Resolving a path follows symbolic links,
  so the spec states that a refused place is judged after resolution and that the check and
  the write use the same resolved value.
- **Independent review.** If the owner asks for one, the spec is sent to an external
  service. It describes the threat model and residual risks, so the checks in `AGENTS.md`
  apply first.
- No commit, push, deployment, dependency installation, secret use or deletion is part of
  this plan beyond the commits the owner asks for.

## Review record

Requested by the owner. Reviewer: Codex through `ask-codex`, model `gpt-5.6-luna`, medium
effort, bound of 3 rounds. The review is open; one round has been used.

**Round 1** (2026-10-20): outcome `changes_needed`, two major findings, both applied.

- R1-F1 (applied): the plan said every command that records an approval is terminal-only,
  but `release-approvals` records shipped approvals without a terminal. The assumptions
  and completion criteria now separate `approve` and `pin` (terminal-only, guarded store)
  from `release-approvals` (release time, shipped records only).
- R1-F2 (applied): the plan treated the target rules' reach as an open question while the
  roadmap says "every command". The scope now reads "every command" as every command that
  acts on a project, which the rules govern without exception. The remaining question is
  narrowed to whether the four package and helper commands also accept the two spellings.

## Deferred work

- The parser, usage text and any renamed options: `base-and-manifests` and later candidates.
- A machine-readable output format, unless the owner asks for one in Increment C.
- Module removal, format migration and three-way merge, which the specs already defer.
- Plan-approval and delegation commands: `code-work-module`.
- Cleaning up cache copies, old shipped records and leftover `bin/run/` directories, which
  `trust-and-approval` already lists as deferred.

## Result

Not started.
