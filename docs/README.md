# Documentation guide

This directory contains the project’s technical references, decisions, plans,
and supporting evidence.

## Index

- `architecture.md` — Current system architecture; points to the specs
- `development.md` — Development, build, test, and verification guidance
- `decisions/` — Durable decision records (ADRs)
- `plans/` — Implementation plans, active and completed
- `roadmaps/` — Multi-plan direction, candidates, and dependencies
- `specs/` — Durable requirements and behavioral specifications

## Authority and lifecycle

- Accepted decisions and current specs are the durable design authority.
- A plan requires the owner's explicit approval before implementation. Several
  plans may be active; active plans are found by listing plans by `Status:`.
- Roadmaps guide sequencing and dependencies. They do not authorize work or
  alter an active plan.
- Completed plans, experiments, investigations, and logs are historical
  evidence, not current authority.
- Record durable architectural choices in decisions rather than relying only on
  plans, roadmaps, tickets, or agent memory.

## Documentation conventions

- Prefer one concise current reference over duplicated rules.
- Link to the governing document or decision rather than restating it.
- Preserve historical records; mark them completed or superseded rather than
  rewriting their conclusions.
- Keep generated artifacts and raw experimental data in their designated
  directories.
- Nothing tracked depends on untracked content: cite an untracked reference by
  source URL, retrieval date and content hash, never by path.
- Use stable, descriptive lowercase kebab-case filenames. Plans and decisions are
  named `YYYY-MM-DD-<topic>.md` and never renamed.

## Checks

The specs define these checks. Each is enforced by the installer once built;
until then by the owner in session:

- the plan check: exactly one `Candidate:` line, increment headings of the form
  `### Increment <label> — <title>`, and no repeated labels;
- duplicate candidate slugs within a roadmap;
- the tracked-pointer rule;
- the tracked reference index, which lists only tracked files;
- acknowledgement of changes made by others to instruction-bearing files.

Until the workbench exists, approval is the owner's explicit statement in
session and a `Status:` line is informational.
<!-- BEGIN workbench/code-work slot:docs-index -->
- [Plans](plans/README.md): the work in hand, as increments
<!-- END workbench/code-work slot:docs-index -->
<!-- BEGIN workbench/groundwork slot:docs-index -->
- [Specs](specs/README.md): what is true now
- [Roadmaps](roadmaps/README.md): where the work is heading
- [Decisions](decisions/README.md): why choices were made
- [References](references/README.md): the outside material the work rests on
<!-- END workbench/groundwork slot:docs-index -->
<!-- @slot: docs-index -->
