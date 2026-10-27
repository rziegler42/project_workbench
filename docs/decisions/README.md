# Architecture decisions

Record durable design choices here as decision records (ADRs). A decision explains
why a choice was made and what was rejected; specs and architecture documents
describe the resulting system. The rules are in [`groundwork.md`](../specs/groundwork.md).

## Status and lifecycle

- **Proposed** — under review; not yet a project decision.
- **Accepted** — explicitly approved design decision. Implementation may follow in a
  separate plan.
- **Rejected** — considered but explicitly not adopted.
- **Superseded** — replaced by a newer record, which names it.

Accepting a record is the owner's act and stops for the owner by default. Do not
rewrite an accepted record to change a decision. Create a new record that supersedes
it. Record implementation evidence in the record's verification section and in the
associated plan.

## Naming and format

- One record per decision, named `YYYY-MM-DD-<topic>.md`: the creation date and a
  lowercase kebab-case topic. The filename stem is the record's stable ID. A record
  is never renamed. There is no sequential number.
- Keep each record concise: context, decision, alternatives considered, consequences,
  verification, and related files and decisions.

```markdown
# Decision title

Status: Proposed | Accepted | Rejected | Superseded by <stem>
Date: YYYY-MM-DD

## Context
## Decision
## Alternatives considered
## Consequences
## Verification
## Related files and decisions
```

## Index

List every record, including rejected and superseded ones.

| Decision | Title | Status |
|---|---|---|
| [2026-10-19-closed-module-types](2026-10-19-closed-module-types.md) | Closed set of module types with count rules | Accepted |
| [2026-10-19-harness-files-per-clone](2026-10-19-harness-files-per-clone.md) | Harness files are per-clone output and are never committed | Accepted |
| [2026-10-19-uniform-package-trust](2026-10-19-uniform-package-trust.md) | Packages are treated uniformly; trust is by approval after an inert download | Accepted |
| [2026-10-19-guarded-store](2026-10-19-guarded-store.md) | Approvals and personal settings live in a guarded store outside the project | Accepted |
| [2026-10-19-compiled-hard-stop-floor](2026-10-19-compiled-hard-stop-floor.md) | The hard-stop floor is compiled in; committed policy may only tighten | Accepted |
| [2026-10-19-restrictive-only-permissions](2026-10-19-restrictive-only-permissions.md) | Neutral permission rules are restrictive only | Accepted |
| [2026-10-19-mandatory-review-personal-delegation](2026-10-19-mandatory-review-personal-delegation.md) | Review is mandatory; delegating the verdict is a personal setting | Accepted |
| [2026-10-19-groundwork-shared-layer](2026-10-19-groundwork-shared-layer.md) | `groundwork` holds specs, roadmaps, decisions and references as the shared layer | Accepted |
| [2026-10-19-derived-completion-slugs-dated-names](2026-10-19-derived-completion-slugs-dated-names.md) | Candidate completion is derived; candidate IDs are slugs; plans and decisions are dated | Accepted |
| [2026-10-19-non-destructive-upgrades](2026-10-19-non-destructive-upgrades.md) | Upgrades are non-destructive, by file ownership class, with no three-way merge | Accepted |
| [2026-10-19-tracked-pointer-rule](2026-10-19-tracked-pointer-rule.md) | Nothing tracked in a document or workbench-managed file depends on untracked content | Accepted |
| [2026-10-19-implementation-language](2026-10-19-implementation-language.md) | Python with the standard library only for the installer | Accepted |
| [2026-10-20-fixed-store-location](2026-10-20-fixed-store-location.md) | The guarded store's location is fixed and nothing can move it | Accepted |
| [2026-10-20-first-party-by-location-and-shipped-record](2026-10-20-first-party-by-location-and-shipped-record.md) | A package is first-party by its place in the distribution and a matching shipped record | Accepted |
| [2026-10-20-isolated-launcher-invocation](2026-10-20-isolated-launcher-invocation.md) | The workbench is run through the isolated launcher from project directories | Accepted |
| [2026-10-20-target-decided-by-state](2026-10-20-target-decided-by-state.md) | A project target is decided by the directory's state, from files and without git | Accepted |
| [2026-10-20-preview-then-owner-run-write](2026-10-20-preview-then-owner-run-write.md) | A project write is previewed read-only and then written by an owner-run command | Accepted |
| [2026-10-20-base-ships-in-distribution](2026-10-20-base-ships-in-distribution.md) | The base ships in the distribution and is trusted as the workbench is | Accepted |
| [2026-10-20-install-creates-git](2026-10-20-install-creates-git.md) | Install creates the `.git` directory itself, and only when there is none | Accepted |
| [2026-10-20-harness-module-writes-nothing-committed](2026-10-20-harness-module-writes-nothing-committed.md) | A harness module writes nothing committed | Accepted |
| [2026-10-20-acknowledge-before-upgrade](2026-10-20-acknowledge-before-upgrade.md) | Baselines gate every upgrade, and the owner accepts a change with `wb acknowledge` | Accepted |
| [2026-10-20-upgrade-needs-no-git](2026-10-20-upgrade-needs-no-git.md) | An upgrade asks no git question; cleanliness is decided by file hashes | Accepted |
| [2026-10-21-module-code-lives-in-modules](2026-10-21-module-code-lives-in-modules.md) | Module-specific code, tests and tooling live in the module, behind a shared kit | Accepted |
| [2026-10-21-installer-runs-document-checks](2026-10-21-installer-runs-document-checks.md) | The installer runs the document checks, for a project that has the module | Superseded by 2026-10-21-module-code-lives-in-modules |
| [2026-10-21-reference-index-format](2026-10-21-reference-index-format.md) | The reference index is canonical JSON, and the index and README are not references | Accepted |
| [2026-10-21-harness-facts-from-layouts](2026-10-21-harness-facts-from-layouts.md) | The installer reads a harness's paths from that harness module's layout | Proposed |
| [2026-10-22-plan-check-in-the-shipped-helper](2026-10-22-plan-check-in-the-shipped-helper.md) | The plan check lives in the helper the `code-work` module ships | Accepted |
| [2026-10-22-installer-pins-declared-helpers](2026-10-22-installer-pins-declared-helpers.md) | The installer pins the helpers a confirmed plan declares | Accepted |
| [2026-10-22-commit-helper-leaves-baselines-to-the-owner](2026-10-22-commit-helper-leaves-baselines-to-the-owner.md) | The commit helper leaves the acknowledgement baselines to the owner | Accepted |
| [2026-10-22-git-work-in-its-own-module](2026-10-22-git-work-in-its-own-module.md) | Git work (`commit`, `remove`) lives in its own module, not in `code-work` or `groundwork` | Accepted |
| [2026-10-22-model-calls-go-through-vendor-bridges](2026-10-22-model-calls-go-through-vendor-bridges.md) | Model calls go through thin vendor bridges; review and action review are separate engines | Accepted; the file name for the action-review engine refined by 2026-10-26-action-review-reads-the-review-setting |
| [2026-10-22-installer-records-plan-approval-module-computes-region](2026-10-22-installer-records-plan-approval-module-computes-region.md) | The installer records and gates plan approval; the process module's pinned helper computes the hashed region | Accepted |
| [2026-10-22-installer-owns-the-edit-gate](2026-10-22-installer-owns-the-edit-gate.md) | The installer owns the edit gate and its hook; the process module names what is under way | Accepted by the owner on 2026-10-23 |
| [2026-10-23-delegated-plan-approval](2026-10-23-delegated-plan-approval.md) | Delegated plan approval is written by the installer, from a sealed review of the same bytes | Accepted by the owner on 2026-10-23; decision 6 superseded by 2026-10-26-per-command-permission-levels |
| [2026-10-23-one-owner-per-skill-name](2026-10-23-one-owner-per-skill-name.md) | A skill name has one owner module; a practice that spans modules is split into skills | Accepted |
| [2026-10-24-project-guarantees-a-floor](2026-10-24-project-guarantees-a-floor.md) | A project guarantees a floor under any global setup, not identical behavior | Accepted |
| [2026-10-24-declared-agent-confinement](2026-10-24-declared-agent-confinement.md) | An agent's limits are declared as data and enforced by the installer | Accepted |
| [2026-10-24-installer-reads-global-settings-on-request](2026-10-24-installer-reads-global-settings-on-request.md) | The installer may read a harness's global configuration, read-only, on the owner's request | Accepted |
| [2026-10-25-adopt-an-existing-repository-without-editing-it](2026-10-25-adopt-an-existing-repository-without-editing-it.md) | Adopt an existing repository without editing it | Accepted by the owner on 2026-10-25 |
| [2026-10-25-module-commands-and-the-approver](2026-10-25-module-commands-and-the-approver.md) | What prompts for the module commands, so the owner's approver can review them | Accepted by the owner on 2026-10-25 |
| [2026-10-25-approver-coverage-for-the-module-commands](2026-10-25-approver-coverage-for-the-module-commands.md) | How the approver comes to review the module commands | Accepted by the owner on 2026-10-25 (option 1a) |
| [2026-10-25-describe-interface-for-action-review](2026-10-25-describe-interface-for-action-review.md) | A module that owns an action reports what it would do through a read-only `describe` command | Accepted by the owner on 2026-10-25 |
| [2026-10-26-per-command-permission-levels](2026-10-26-per-command-permission-levels.md) | Each owner-run and checkpointed command gets one permission level in the owner's personal settings | Accepted by the owner on 2026-10-26; decisions 2 and 6 and Question 2 refined by 2026-10-26-permission-levels-as-built and 2026-10-26-a-level-for-every-command |
| [2026-10-26-describe-push-takes-the-push-arguments](2026-10-26-describe-push-takes-the-push-arguments.md) | A push is described by `safe-git describe push`, which takes the arguments of `git push` and validates them itself | Accepted |
| [2026-10-26-ask-level-spelling-limit](2026-10-26-ask-level-spelling-limit.md) | At the ask and none levels the harness's rule is the only barrier, and its limit is accepted | Accepted by the owner on 2026-10-26 |
| [2026-10-26-ask-level-command-gate](2026-10-26-ask-level-command-gate.md) | A command gate stops Bash commands that name a relaxed command unless the ask rule can fire on them | Accepted by the owner on 2026-10-26 |
| [2026-10-26-permission-levels-as-built](2026-10-26-permission-levels-as-built.md) | The permission levels as built: what stands, what changed and what was not built | Accepted by the owner on 2026-10-26 |
| [2026-10-26-a-level-for-every-command](2026-10-26-a-level-for-every-command.md) | Every command has a permission level, and no level is limited to block | Accepted by the owner on 2026-10-26 |
| [2026-10-26-action-review-reads-the-review-setting](2026-10-26-action-review-reads-the-review-setting.md) | The action-review engine reads `.workbench/review.json`, the review engine's file, where decision 5 names a file per engine | Accepted by the owner on 2026-10-26 |
| [2026-10-27-command-gate-command-position](2026-10-27-command-gate-command-position.md) | The command gate reads a single-word command in command position, not the word alone | Accepted by the owner on 2026-10-27 |
| [2026-10-27-command-gate-literal-arguments](2026-10-27-command-gate-literal-arguments.md) | The command gate leaves a literal `wb run` command and a sibling command name alone | Accepted by the owner on 2026-10-27 |
| [2026-10-27-rerender-is-terminal-only](2026-10-27-rerender-is-terminal-only.md) | `wb rerender` offers `block` only and always needs a terminal | Accepted by the owner on 2026-10-27 |
