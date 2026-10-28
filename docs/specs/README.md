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
| [`action-review.md`](action-review.md) | Draft design of the action-review engine: the `describe` interface of the module that owns an action, the verdict, the thin hook |
| [`knowledge-tools.md`](knowledge-tools.md) | The three knowledge modules (`mempalace`, `graphify`, the knowledge base): which problem each owns, routing, shared conventions |
| [`mempalace.md`](mempalace.md) | The module that lets an agent search the owner's MemPalace; owner-run commands build it |
| [`command-permissions.md`](command-permissions.md) | The per-command permission levels (`block`, `delegated`, `ask`, `none`) in the owner's personal settings: the table, the log, the rendering record, the command gate and `approve-plan` at `ask` and `none` |
| [`harness-rerender.md`](harness-rerender.md) | `wb rerender`: rendering an attached clone's permissions again after the owner's table changes, terminal-only, with a preview and a digest |
| [`harness-refresh.md`](harness-refresh.md) | Draft: refreshing the rendered skills and agents of an attached clone from their sources, by `wb rerender`, and reporting the ones that are behind |
| [`remote-runner.md`](remote-runner.md) | The module that gives a project its remote job profiles and a guarded way to submit, inspect and fetch |
| [`security-review.md`](security-review.md) | The module that gives a project a security review: one skill and one confined agent, provided as the capability `security-review` |
| [`harness-modules.md`](harness-modules.md) | How a harness module describes one AI runtime |
| [`superpowers-ports.md`](superpowers-ports.md) | The superpowers skills the owner uses, and what became of each |
| [`global-config-inventory.md`](global-config-inventory.md) | A disposition for each item of the owner's global Claude configuration, with what was and was not inspected |
