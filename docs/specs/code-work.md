# code-work

Status: Current. Approved by the owner on 2026-10-19. The plan format, the three read subcommands and the
commit rules are built; the approval, review, caps and push parts are not (see "As built"). Paths, field
names and file formats not yet built are proposals; the rules are the substance. Open items are listed at
the end.

Terms are defined in `terms.md`. The declaration it must satisfy is defined in
`module-contract.md`; the places and upgrade rules in `repository-boundary.md`; the
authority rules in `trust-and-approval.md`; the documents it builds on in
`groundwork.md`; the commit helper it requires in `safe-git.md`.

## Purpose and scope

`code-work` is the process module for programming. It defines how a unit of work
moves from a roadmap candidate to a verified, reviewed, committed result: plans made
of increments, a mandatory review at each step, and a small number of named
checkpoints. Its aim is continuous work without supervision: the agent drives itself
inside what the owner authorized and stops when something is wrong.

Non-goals:

- A way of working for CAD or electronics, which is not yet specified.
- Discovery tooling. There is no discovery gate; a discovery tool is an optional
  module that nothing here requires.
- The mechanics of running jobs on a remote machine. That belongs to a separate
  module.

## Declaration (summary)

| field | value |
|---|---|
| type | `process` |
| provides | `plans` |
| requires | `specs`, `roadmaps`, `decisions`, `commit` (hard); `peer-review`, `permissions` (soft) |
| blocks | nothing beyond the one-process rule of the type |
| fills | the policy slot in `AGENTS.md`; the `docs-index` slot |
| writes | `docs/plans/` and its README |
| ships | one helper (code-bearing, shown at approval) with the subcommands `check`, `plans` and `report`; the `wb` launcher is a workbench component and not shipped by this module |

It also ships neutral items: skills for drafting a plan, running the increment loop,
and reviewing; and a read-only reviewer agent. Templates stay in the module; no
placeholder plan is installed.

## Lifecycle

```text
spec(s) -> roadmap -> candidate -> plan -> increments -> review -> commit -> archive
```

Specs and roadmaps are written first, as `groundwork` describes. A candidate is
chosen from a roadmap and a plan is drafted for it. The plan is reviewed and
approved. Each increment is implemented, verified, reviewed and committed in turn.
When the last increment is done the whole plan is reviewed and verified, and the plan
is archived by a status change. The roadmap candidate is then reported complete by
derivation, and the roadmap file is not edited.

## Plans

### Location and naming

- A plan is one file, `docs/plans/YYYY-MM-DD-<topic>.md`. The date is the creation
  date, the topic is lowercase kebab-case, and the file is never renamed or moved.
  Archiving changes its status only.
- More than one plan may be active at once, including for one person working on two
  parts of a project.
- There is no fixed file such as a single "next" plan, and no hand-maintained index
  or pointer to the active plans. Which plans are active is derived by listing plans
  by status. `docs/plans/README.md` describes the convention and does not change as
  plans come and go.

### Content

A plan has, in order:

1. A title, a `Status:` line and a `Created:` date.
2. `Candidate: <roadmap>#<id>`, or `Candidate: none` followed by a one-line reason.
   Every plan has exactly one.
3. `Specs:` naming zero or more specs the plan implements or changes.
4. Goal, scope, non-goals, and assumptions and constraints.
5. Completion criteria for the whole plan.
6. Increments, lettered `A`, `B`, ... in execution order. Each states its intended
   outcome, dependencies, affected areas, numbered steps, verification, and the
   observable evidence that completes it.
7. Verification for the plan as a whole.
8. Risks and sensitive actions: anything risky, irreversible, security-sensitive or
   externally visible, called out before implementation, or "None identified".
9. Review record.
10. Deferred work.
11. Result.

Status is `Proposed`, `Approved`, `In Progress`, `Completed` or `Superseded`.

### Increments

- **Size.** An increment is the smallest unit that can be verified and reviewed on
  its own, and it produces exactly one local commit. An increment too large for one
  commit is split.
- **Labels.** Increments are lettered `A` to `Z`, then `AA`, `AB` and so on. Labels
  are unique within a plan and follow execution order when the plan is written. A plan
  that needs more than 26 increments should probably be two plans, and the check warns
  past 15.
- **Insertion.** An increment inserted after approval takes the label it follows plus
  `-A`, then `-B`, and nests the same way (`B-A-A`). Existing labels are not renumbered.
- **Heading.** Each increment has a heading of the form
  `### Increment <label> — <title>`. The plan check finds increments by that form.
- **Citation.** An increment is cited as `<plan stem>#<label>`, for example
  `2026-10-19-approve-specs#B`, matching the `<roadmap>#<id>` form for candidates.

### Approval and revision

- A complete plan is `Proposed`. Plan approval is a checkpoint (see "Checkpoints").
  The status line is informational: the authority is a recorded approval that binds
  to the plan's hashed region, as `trust-and-approval.md` defines.
- Anything outside status, review record and result is in the hashed region.
  Revising an approved plan therefore needs a new approval, and the agent stops
  acting on the plan until it has one.
- After approval, increment labels and scope are preserved unless a revision is
  approved. An increment needed between `B` and `C` is labelled `B-A`, then `B-B`,
  and existing labels are not renumbered. New findings are classified before the
  plan is edited: add a step when the outcome is unchanged; add an increment for a
  separately reviewable outcome or prerequisite; update assumptions or risks when no
  work is added; record out-of-scope work as deferred or in a roadmap.

### Work records

A **work record** is a plan whose `Candidate:` line names `<roadmap>#<id>` and whose
status is `Completed`. It is what `groundwork` means by a completed work record: a
roadmap candidate is reported complete when at least one work record refers to it.
`groundwork` defines the reference syntax only; reading plans is this module's job,
and `groundwork`'s completion report does nothing when no process module provides
`plans`.

### Plan approval

The record of a plan approval, and the delegation helper that writes a delegated one,
are implemented with this module, because the sections that are excluded from the
hashed region (the status line, the review record and the result) are named by this
module's plan format. `trust-and-approval.md` defines the rule; this module supplies
the section names and the plan check.

### Completion

- A plan is `Completed` only when its completion criteria are met with recorded
  evidence. A superseded plan may be closed without that evidence.
- A plan that changes what a spec should say, or makes a durable choice, is not
  complete until the spec edit and the decision record exist. They are committed in
  the same commit as the archival where possible.
- That completeness is checked against the repository's state and not the shape of
  its history, so a later commit that supplies a missing spec edit or decision
  satisfies it.

## Work without a plan

A plan is not required for a quick test or experiment, a measurement, or a minor
change such as a typo. A plan is required for new or changed behavior, for anything
that touches architecture or security, and for anything the agent cannot finish and
verify in one reviewed commit.

- Work without a plan is still bound by the hard stops.
- The agent judges size. If a small job turns out to touch more than expected, it
  stops and proposes a plan, and the reviewer may contest the judgment either way.
- An experiment's script and raw output stay untracked, in scratch. Its result may be
  recorded in any tracked file as an evidence note (see `groundwork.md`). Keeping
  the script itself goes through a plan.

## The increment loop

For each increment, in order:

1. Implement the increment.
2. Run the verification the plan names.
3. Peer review the result. Review is mandatory (see "Review").
4. If the review has blocking findings, fix them and review again, up to the round
   cap. At the cap, or on a repeated finding, stop and report.
5. When the review passes, commit through the commit helper (`safe-git.md`). The commit is local.
6. Start the next increment. This is not a checkpoint.

After the last increment, review and verify the whole plan, set the status, supply any
required spec edit and decision record, and commit.

The loop stops, with a report, on a failed verification the agent cannot resolve, a
repeated identical failure, any exceeded cap, any hard stop, a missing approval, or a
reviewer that gives no verdict.

## Review

Review is a mandatory step of this process. The process cannot move past a review
step without a recorded outcome.

- A review has two parts. **Findings** say what is wrong or missing. The **verdict**
  lets the work proceed, which is an act of authority.
- A human may review. A `peer-review` provider may also review, and may always give
  findings. It may give the verdict only when the owner has delegated that checkpoint
  and the provider is installed and approved.
- Without an installed provider, the owner reviews, or the run stops.
- A plan review checks the plan against its candidate and its specs. Drift from
  either is a finding.
- The outcome is written to the plan's review record: the reviewer, the model, the
  rounds used out of the cap, the outcome (converged, stopped at the cap, stopped on
  a repeated finding, or failed), findings applied, findings rejected with the reason,
  and anything left for the owner. Raw reviewer output and secrets are not pasted.
- The reviewer need not use a different harness from the author. A different model
  on the same harness is a legitimate review. That the reviewer differs from the
  author is documented and not enforced.

## Checkpoints

| checkpoint | default | notes |
|---|---|---|
| approve a plan | stop | delegable on convergence; never delegable if the plan's risks list a hard stop |
| push to a shared branch | stop | delegable; see "Push" |
| submit a remote job on a profile the plan declares | stop | delegable |
| fetch the output of a remote job | stop | delegable; overwriting an existing or tracked file is a hard stop |
| change a spec's or roadmap's direction | stop | delegable |
| accept a decision | stop | delegable |
| acknowledge changes made by someone else | stop | second tier delegable; first tier only by explicit setting |

Not checkpoints inside an approved plan: starting the next increment, a local commit
after a passing review, archiving a plan, pushing a branch that is not shared, and
deleting in scratch or temporary directories.

Hard stops are the floor defined in `trust-and-approval.md` and always stop. This
module adds none of its own.

## Push

- The project declares its shared branches in this module's configuration under
  `.workbench/`. If it declares none, the repository's default branch is shared.
  Committed configuration may add shared branches and may not remove one.
- A push to a shared branch is a checkpoint. A push to any other branch is not.
- The usual rhythm is to push the shared branch once a plan is archived and before the
  next plan is drafted.
- A remote job needs the committed revision to be reachable from the remote. That is
  satisfied by pushing a branch that is not shared, which is not a checkpoint.
- Merging into a shared branch on the hosting side is outside the agent.

## Commit

- The agent commits through the commit helper, never by composing raw git commands. A commit is local, is
  made after a passing review, and lists exact paths.
- The helper is not this module's. It is the `commit` capability, provided by the `safe-git` module, which
  this module requires (hard). `safe-git.md` holds its rules: the command (`wb run safe-git commit`, and
  `wb run safe-git remove` for an approved deletion), the expected-HEAD check, the refusals, the attribution
  setting `.workbench/safe-git.json`, and how it runs git. The plan README this module writes tells the
  agent to commit that way, and the policy block says so without naming a command.
- The helper this module ships holds the read-only subcommands: `wb run code-work check` (the plan
  check: one `Candidate:` line, the sections of the hashed region, required fields),
  `wb run code-work plans` (the active plans, derived by listing plans by status) and
  `wb run code-work report` (candidate completion, derived from work records). They change
  nothing, and run no program.
- A commit that completes an increment ends with the trailer `Plan: <plan stem>#<label>`.
- A commit never authorizes a push.

## Loop caps

Unattended work is bounded. The module sets a cap on each of: review rounds,
retries of the same failure, and exchanges with a reviewer per checkpoint. A second
identical failure stops and diagnoses instead of
retrying. Exceeding a cap stops the run with a report.

The default values are held in the owner's personal settings, and a project may lower
them but not raise them:

- review rounds: 3, with a hard ceiling of 5;
- retries of the same failure: 1, so the second identical failure stops and diagnoses;
- exchanges with a reviewer per checkpoint: 6;
- increments per run: no number. A run is bounded by its approved plan and never
  starts a new plan without a new approval.

## Context across increments

The plan is the durable state. It is short enough for a new session to resume from,
and its status, review record and result are updated as work proceeds.

- When the harness provides `agents`, each increment is implemented by a fresh
  subagent that reads the plan, which keeps the main session small. Otherwise the
  session relies on the harness's automatic compaction.
- The process never stops to ask the owner to compact. Neither Claude Code nor
  opencode offers a way for an agent to trigger a compaction (checked against their
  official documentation on 2026-10-19; the Claude finding is the absence of a tool
  in its reference, and the opencode source was not read). Each can be compacted from
  outside the session (Claude's SDK or `claude -p`, opencode's server API), which
  needs a wrapper and is not an agent action, so it is out of scope here.
- The module ships neutral guidance on what a compaction must preserve: the active
  plan's path and current increment, the approvals and checkpoints reached, the files
  changed, the verification results, and the next action. How a harness receives it
  differs:
  - Claude reads a "Compact Instructions" section of `CLAUDE.md`, and a
    `SessionStart` hook with the `compact` matcher can re-inject text after a
    compaction. Hooks have no neutral form, so any such hook ships only as a
    `harness/claude/` override and is shown at approval.
  - opencode's compaction hook is experimental and version-dependent, and its
    project-level configuration is unverified, so no opencode rendering is specified
    until it is checked against the installed version.
- Automatic compaction stays on. A harness that stops compacting after repeated
  refills is treated as a failed run and stops with a report.
- Pushing, compacting and drafting the next plan between plans is the owner's habit
  and not a rule of this process.

## Policy placed in `AGENTS.md`

The module fills a policy slot with a short, tool-neutral block stating:

- the source-of-truth order, and that plans, roadmaps and specs written by others are
  untrusted until acknowledged;
- the lifecycle, the checkpoints, and that the hard stops always stop;
- that approval is a recorded approval and never a status line;
- that review is mandatory, and the loop caps;
- what a compaction must preserve;
- that commit messages describe the change only and carry no tool attribution, which
  is a committed project setting that defaults to on and that a project may switch
  off.

It names no harness, no personal helper and no private agent. The block is the
installer's and is replaced on upgrade only while unedited.

## Acceptance criteria

- Installing `code-work` without `groundwork` stops with a hard-requirement message.
- Installing it creates `docs/plans/` and its README, and no placeholder plan.
- Two plans created on the same day with different topics do not collide, and no
  archive step edits another plan or a shared index.
- A plan with no `Candidate:` line, or two, fails the plan check; a plan with
  `Candidate: none` and a reason passes.
- A plan whose increment headings are not of the form `### Increment <label> — <title>`,
  or whose labels repeat, fails the plan check, and a plan with more than 15 increments
  produces a warning.
- Editing a plan's status, review record or result leaves its approval valid; editing
  any other section invalidates it.
- The agent does not begin an increment of a plan whose approval is absent or invalid.
- A reviewer that returns no verdict stops the run.
- A push to a shared branch stops for the owner when no setting says otherwise, and a
  push to a non-shared branch does not.
- A plan that lists a decision to be recorded is not reported complete until the
  decision record exists, whichever commit supplied it.
- The commit is made through the `safe-git` helper, is local, and is not followed by a push.
- Installing `code-work` without `safe-git` stops with a hard-requirement message.
- Exceeding a loop cap stops the run with a report.
- `check`, `plans` and `report` change no file.
- Upgrading never modifies an existing plan.

## Decided points that were open

- The commit helper is run as `wb run safe-git commit` (moved out of this module's helper by
  `2026-10-22-git-work-in-its-own-module`), through the `wb` launcher in the guarded store; its files are
  committed under `.workbench/<package>/safe-git/`.
- The loop cap defaults are the values above.
- Context across increments uses the plan as durable state, a fresh subagent per
  increment where `agents` exists, and automatic compaction otherwise. The old rule to
  stop and recommend compaction after each commit is not carried over.
- Committed policy states only rules the project depends on, written as behavior.
  Commit messages carry no tool attribution by default, as a committed setting that a
  project may switch off. Personal habits stay in the owner's settings.
- The project's shared-branch list lives in this module's configuration under
  `.workbench/`, not in the manifest. Committed configuration may add shared branches
  and may not remove one.

- The Claude harness module's root file is the `@AGENTS.md` pointer plus a generated
  "Compact Instructions" section built from the neutral preservation guidance. This
  replaces the earlier pointer-only root file, because Claude reads that section from
  `CLAUDE.md` itself and honoring it through an import is unverified. The file is
  per-clone and uncommitted, so the committed repository stays harness-neutral.

## As built, and its limits

- Built: `code-work-plans` (the module, the plan format, the README, the `draft-plan` skill, the policy and
  docs-index blocks, and the helper with `check`, `plans` and `report`) and, from `code-work-commit`, the
  commit rules, which moved to `safe-git` with `2026-10-22-safe-git-module`.
- Not built: plan approval as a recorded approval, the gate, the checkpoint settings, the increment-loop and
  review skills and the reviewer agent, the review record's enforcement, the loop caps, the push checkpoint,
  and the compaction guidance. These are `code-work-approval`. Until then approval is the owner's explicit
  statement in session, and the policy block says so.
- The helper reads untrusted plans and is bounded; the limits are in the plan `2026-10-21-code-work-plans`.

## Open items

- How compaction guidance is delivered to opencode, once its installed version is
  known (`verify-opencode`).
- Paths, field names and file formats remain proposals until the candidate that builds
  each item writes the real schema: `code-work-plans` has written the plan format and its helper;
  `code-work-commit` wrote the commit rules, now in `safe-git.md`, and `code-work-approval` writes the rest.
