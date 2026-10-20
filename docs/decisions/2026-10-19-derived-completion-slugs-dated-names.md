# Candidate completion is derived; candidate IDs are slugs; plans and decisions are dated

Status: Accepted
Date: 2026-10-19

## Context

Several people may add plans, decisions and roadmap candidates at once. A shared counter
collides, a hand-maintained index drifts, and a roadmap that records completion changes
every time work finishes.

## Decision

A candidate is complete when a work record (a plan whose `Candidate:` line names it and
whose status is `Completed`) refers to it. Completion is derived and never written into
the roadmap, so the roadmap file changes only when direction changes. Candidate IDs are
topic slugs in lowercase kebab-case, unique within a roadmap, never reused or renumbered,
and written `<roadmap>#<id>`. Plans are `docs/plans/YYYY-MM-DD-<topic>.md` and decisions
are `docs/decisions/YYYY-MM-DD-<topic>.md`: the date is the creation date, the file is
never renamed, and its stem is its stable ID. Several plans may be active, and which are
active is derived by listing plans by status. There is no shared counter anywhere.

## Alternatives considered

- **Sequential numbers.** Rejected: collide across collaborators.
- **Completion marked in the roadmap.** Rejected: churns a file meant to stay stable.
- **A fixed single active plan file.** Rejected: collaborators on different areas collide.
- **Date of archival in the name.** Rejected: a plan is named by its start date.

## Consequences

- Two records created on one day collide only if they share a topic.
- A check reports a duplicate candidate slug.
- This repository adopts the convention at `adopt-conventions`; until then its own
  decisions README says numbered. This record and its siblings are the one approved
  exception.

## Verification

Acceptance criteria in `docs/specs/groundwork.md` and `docs/specs/code-work.md`: a roadmap
file is unchanged when a work record completes, and a duplicate slug is reported.

## Related files and decisions

- `docs/specs/groundwork.md`, `docs/specs/code-work.md`
- [2026-10-19-groundwork-shared-layer](2026-10-19-groundwork-shared-layer.md)
