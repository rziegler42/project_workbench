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
