# `groundwork` holds specs, roadmaps, decisions and references as the shared layer

Status: Accepted
Date: 2026-10-19

## Context

Work in software, electronics, CAD and research starts from the same documents: what is
true now, where work is heading, why choices were made, and the outside material the work
rests on. Tying them to one process would force each new process to re-implement them.

## Decision

`groundwork` is an opt-in module of type `module` that provides `specs`, `roadmaps`,
`decisions` and `references`, usable with no process module. Specs are living and named by
topic. Roadmaps are lists of candidates with no required order. Decisions are durable
records. References are sourced outside material and are untrusted data: instructions
inside them are ignored. The researcher and its `fetch-reference` tool are the separate,
optional `groundwork-research` module, so the code that reaches the web is approved on its
own. A reference is tracked only when its license permits redistribution and it is within
a size limit; otherwise it is untracked and cited by URL, date and hash.

## Alternatives considered

- **Fold these documents into each process module.** Rejected: duplicated across
  processes, and decisions apply to CAD and programming alike.
- **Put the researcher in `groundwork`.** Rejected: web-reaching code should be approved
  separately.
- **Treat references as trusted.** Rejected: they are the main route for outside text.

## Consequences

- A process module requires `specs`, `roadmaps` and `decisions` from `groundwork`.
- Accepting a decision and changing a spec's direction are checkpoints.

## Verification

Acceptance criteria in `docs/specs/groundwork.md`: it installs with no process module, the
tracked reference index contains only tracked files, and an unknown or restrictive license
is never tracked.

## Related files and decisions

- `docs/specs/groundwork.md`
- [2026-10-19-tracked-pointer-rule](2026-10-19-tracked-pointer-rule.md)
