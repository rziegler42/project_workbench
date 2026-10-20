# Implementation plans

A plan describes one bounded piece of work as ordered increments. The rules are in
[`code-work.md`](../specs/code-work.md); this file is the short form for this
repository.

## Names and location

- A plan is one file, `docs/plans/YYYY-MM-DD-<topic>.md`. The date is the creation
  date and the topic is lowercase kebab-case. The file is never renamed or moved;
  archiving changes its status only.
- Several plans may be active at once. There is no fixed single-plan file and no
  hand-maintained index. Active plans are found by listing plans by `Status:`.
- Planning tools and skills may supply a method or content structure, but they do
  not override this location. Do not create tool-owned planning or specification
  directories. Durable requirements belong in `docs/specs/`.

## Content

A plan has, in order:

1. A title, a `Status:` line and a `Created:` date.
2. `Candidate: <roadmap>#<id>`, or `Candidate: none` with a one-line reason.
   Exactly one.
3. `Specs:` naming zero or more specs the plan implements or changes.
4. Goal, scope, non-goals, and assumptions and constraints.
5. Completion criteria for the whole plan.
6. Increments.
7. Verification for the plan as a whole.
8. Risks and sensitive actions, or "None identified".
9. Review record (earlier plans call it Second opinion).
10. Deferred work.
11. Result.

Status is `Proposed`, `Approved`, `In Progress`, `Completed` or `Superseded`.

## Increments

- An increment is the smallest unit that can be verified and reviewed on its own,
  and it produces exactly one local commit.
- Labels run `A` to `Z`, then `AA`, `AB` and so on, in execution order. Labels are
  unique within a plan. More than 15 increments suggests two plans.
- After approval, labels are not renumbered. An increment needed between `B` and
  `C` is `B-A`, then `B-B`, and nests the same way (`B-A-A`).
- The heading is `### Increment <label> — <title>`. Each increment states its
  outcome, dependencies, affected areas, numbered steps, verification, and the
  evidence that completes it.
- An increment is cited as `<plan stem>#<label>`.

## Approval and revision

Write a complete plan with `Status: Proposed`, then obtain the owner's explicit
approval before changing it to `Approved` or beginning implementation. Use
`In Progress` while implementation is underway. Editing anything other than the
status line, the review record and the result after approval needs a new approval.

Classify new findings before editing the plan: add a step when the outcome is
unchanged; add an increment for a separately reviewable outcome or prerequisite;
update assumptions or risks when no work is added; record out-of-scope work as
deferred or in a roadmap.

## Completion

A plan is `Completed` only when its completion criteria are met with recorded
evidence. A superseded plan may be closed without that evidence. A plan that
changes what a spec should say, or makes a durable choice, is not complete until the
spec edit and the decision record exist. A plan whose `Candidate:` names a roadmap
candidate and whose status is `Completed` is what makes that candidate complete.

Archived plans record intended work, verification, and results. They are historical
evidence, not durable architectural authority. Record lasting design constraints as
decisions under `docs/decisions/`.

Do not collect unapproved plan fragments in ad hoc files under `docs/plans/`. Keep
multi-plan direction in `docs/roadmaps/`.

Checks on this format are enforced by the installer once built; until then by the
owner in session.
