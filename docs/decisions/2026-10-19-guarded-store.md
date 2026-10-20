# Approvals and personal settings live in a guarded store outside the project

Status: Accepted
Date: 2026-10-19

## Context

An approval kept inside the repository can be forged by anyone who can commit, and
scratch under the project can be written by the agent. Authority has to come from a
place the agent and contributors cannot write.

## Decision

Approvals, acknowledgement baselines, pinned hashes and the owner's personal settings
live in a guarded store at `~/.config/project-workbench/`, outside any project. The
agent must not write it: each harness that provides `permissions` receives a local
deny rule on writes to it. The owner records an approval by running a command
themselves from a prompt the agent does not control, and the agent's command
permissions deny that command. Every command first ensures the store exists and is
seeded, idempotently. A project's entry is keyed by its project ID and also records
where the project was first seen. A `Status:` line in a committed file is never an
approval.

## Alternatives considered

- **Approvals in the repository.** Rejected: forgeable by any contributor.
- **Approvals in scratch under `.workbench/local/`.** Rejected: writable by the agent.
- **A harness's global configuration.** Rejected: tied to one harness, and the
  workbench must not depend on one.

## Consequences

- The store is a mechanical barrier, not an operating-system one. It runs under the
  owner's account, so its strength depends on the harness's deny rules.
- A harness without `permissions` yields a warning that the store is protected only by
  instruction.

## Verification

Acceptance criteria in `docs/specs/trust-and-approval.md`: a committed approved status
with no matching record is not an approval, and a write to the store is denied after
attach.

## Related files and decisions

- `docs/specs/trust-and-approval.md`, `docs/specs/repository-boundary.md`
- [2026-10-19-uniform-package-trust](2026-10-19-uniform-package-trust.md)
- [2026-10-19-compiled-hard-stop-floor](2026-10-19-compiled-hard-stop-floor.md)
