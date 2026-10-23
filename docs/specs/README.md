# Specifications

This directory holds durable, repository-owned requirements and behavioral
specifications. A spec states what is true now. It is a living document, edited in
place, and not a work log. Implementation sequencing belongs in `../plans/`, and
durable design choices belong in `../decisions/`. The rules are in
[`groundwork.md`](groundwork.md).

## Names and status

- One spec per topic, named by topic in lowercase kebab-case with no date, for
  example `module-contract.md` or `trust-and-approval.md`.
- Every spec has a `Status:` line: `Draft`, `Current` or `Superseded`. A superseded
  spec names its successor.
- Changing what a spec says about direction stops for the owner. Correcting a typo or
  recording evidence does not.

## Content

Each spec identifies its scope, non-goals, assumptions, relevant constraints or
interfaces, acceptance criteria, and links to the decisions and external material
that govern it. Numbers and tolerances carry their source: a decision, a reference,
or an evidence note.

## Index

| Spec | Subject |
|---|---|
| [`terms.md`](terms.md) | Vocabulary used by every other spec |
| [`module-contract.md`](module-contract.md) | Package and module declarations, types, capabilities, conflicts |
| [`module-boundary.md`](module-boundary.md) | What is installer mechanism and what is module content; the kit, module commands and checks |
| [`repository-boundary.md`](repository-boundary.md) | Places, manifests, ownership classes, install, attach, check, upgrade |
| [`trust-and-approval.md`](trust-and-approval.md) | Authority, approvals, hard stops, untrusted content |
| [`installer-interface.md`](installer-interface.md) | The installer's commands: the target, options, preview and approval, output and exit codes |
| [`groundwork.md`](groundwork.md) | Specs, roadmaps, decisions and references |
| [`code-work.md`](code-work.md) | The programming way of working |
| [`safe-git.md`](safe-git.md) | Local commits of exact paths and approved deletions, as a module of their own |
| [`model-bridge.md`](model-bridge.md) | The contract of a thin vendor module that lets an engine ask a model one read-only question |
| [`review-engine.md`](review-engine.md) | The review module that provides `peer-review`: rounds, findings, sealed state, the project setting |
| [`harness-modules.md`](harness-modules.md) | How a harness module describes one AI runtime |
