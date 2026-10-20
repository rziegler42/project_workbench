# Packages are treated uniformly; trust is by approval after an inert download

Status: Accepted
Date: 2026-10-19

## Context

Modules ship hooks, helpers and instructions that an agent will act on. The workbench's
own first-party package and anyone's third-party package carry the same risk once
installed. A package ref can move, so approving a name is not approving content.

## Decision

Every package is treated the same way. A package is first downloaded inertly into a
cache in the guarded store, as data only, so its declaration can be shown. The owner
approves the declaration and the content tree hash. The first approval pins the
resolved commit and tree hash, and later attaches and teammates verify against it. A
changed declaration or changed content is a new subject and needs a new approval. A
package added to the committed manifest by someone else is never activated until the
owner approves it on this machine. First-party modules differ only in coming from the
workbench distribution and carrying approvals generated at release time, read from the
installed workbench. The installer never executes anything a package ships at install.

## Alternatives considered

- **Trust first-party code implicitly.** Rejected: a different route to the same
  verification is a second path to defend.
- **Approve by package name or ref.** Rejected: a mutable ref can change what is
  received.
- **Approve after writing the files.** Rejected: the owner would approve what is
  already installed.

## Consequences

- Install and attach do nothing until approval exists.
- Third-party names are prefixed `<package>:<name>`, and only the first-party package
  may use unprefixed core names.

## Verification

Acceptance criteria in `docs/specs/trust-and-approval.md` and
`docs/specs/repository-boundary.md`: a module whose declaration or content differs from
its approval is not installed, and a newly listed package is not written or activated
before approval.

## Related files and decisions

- `docs/specs/trust-and-approval.md`, `docs/specs/module-contract.md`
- [2026-10-19-guarded-store](2026-10-19-guarded-store.md)
