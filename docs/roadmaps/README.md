# Roadmaps

Roadmaps are tracked, committed, non-authoritative documents for multi-plan
direction. They preserve dependencies, boundaries, and rationale. They do not
authorize implementation or change an active plan. The rules are in
[`groundwork.md`](../specs/groundwork.md).

## Lifecycle

- A roadmap is a list of candidates with no required order. Order and dependencies
  are hints, and what is learned may reshuffle, add or drop candidates. A roadmap may
  keep an optional suggested order as a list.
- Promote one selected candidate into a complete, reviewed, explicitly approved plan
  in `docs/plans/`. Several plans may be active; one candidate has one plan.
- A candidate's completion is derived. It is complete when a plan whose `Candidate:`
  line names it has `Status: Completed`. Completion is never written into the roadmap,
  so the roadmap file changes only when direction changes.
- Record durable architectural choices in `docs/decisions/`; roadmaps explain
  direction and dependencies but do not replace decisions.
- Keep implementation-ready file lists, detailed acceptance criteria, and executable
  verification commands in the promoted plan.

## Naming and candidates

- Use stable, lowercase, kebab-case scope names such as `workbench-v1.md`. Do not use
  numbers or dates in roadmap filenames.
- A candidate's ID is a short topic slug in lowercase kebab-case, unique within its
  roadmap, fixed when created, never reused or renumbered, and unchanged if the title
  is reworded. A candidate is cited as `<roadmap>#<id>`, for example
  `workbench-v1#approve-specs`.
- An abandoned candidate is marked dropped with a reason and stays in the file,
  because completed work may refer to it.
- Keep one roadmap per scope that is not archived and update it in place. A replacement
  takes a new name, and the old roadmap is retired by setting `Status: Archived`. The
  file is never moved or renamed, so `<roadmap>#<id>` stays valid. Retiring or replacing
  a roadmap changes direction, so it needs the owner.

## Index (current)

List roadmaps that are not archived; an archived roadmap stays in place and keeps its
history.

| Roadmap | Status | Scope |
|---|---|---|
| `workbench-v1.md` | Active | First version of the installer, harnesses, `groundwork` and `code-work` |

## Format

```markdown
# Roadmap: <scope>

Status: Draft | Active | Archived
Updated: YYYY-MM-DD

## Purpose

## Current state

## Suggested order (optional)

## Candidates

### <id> — <title>

**Outcome:** ...
**Dependencies:** ...
**Boundary:** ...
**Promotion trigger:** ...

## Deferred

## Related decisions
```
