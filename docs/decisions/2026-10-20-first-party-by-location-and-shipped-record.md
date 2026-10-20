# A package is first-party by its place in the distribution and a matching shipped record

Status: Accepted
Date: 2026-10-20

## Context

Only the first-party package may provide unprefixed capability names, and first-party modules are
approved at release time, with the records shipping with the workbench
(`2026-10-19-uniform-package-trust`). The specifications did not say how the installer decides that a
package is first-party. A flag or a name in `package.json` is written by the package's author and
proves nothing, and a package that has been edited since its release must not keep rights it was
granted for different content.

## Decision

A package is first-party only when all of these hold:

1. its directory is directly inside the workbench distribution's `packages/` directory and is not a
   symbolic link;
2. its declared name equals its directory name; and
3. a shipped package record for that name matches the package's current declaration hash and
   whole-package tree hash.

The shipped records are in `workbench/shipped_approvals/`, in the same layout as the guarded store.
They are read in place and never copied into the store. They are made by a release-time command that
verifies every package under `packages/` as first-party, writes nothing if any module fails, and uses
a fixed approver and time so that a second run changes nothing. Anything else is third-party. A
first-party package changed after its release is third-party until it is released again.

## Alternatives considered

- **A name list or a flag in the package or in a file.** Rejected: whoever writes it can claim it.
- **Location alone.** Rejected: an edit to a released package would keep the right to unprefixed
  names for content nobody approved.
- **Signatures.** Rejected for now: a signing key needs managing and a place to keep it, and the
  distribution already is the trust root.
- **Recording first-party approvals in the guarded store.** Rejected: the specification says the
  records are read from the installed workbench and are not copied into the store.

## Consequences

- The distribution directory is the trust root, and it shares the owner's account. Anything that can
  write the repository can add a package and run the release command, so what a release changes in
  `workbench/shipped_approvals/` must be reviewed in its git diff before it is accepted. The command
  needs no terminal, because releases may run unattended.
- There are no first-party packages yet, so the rule is tested against a fixture distribution.
- An edit to a first-party package loses its rights until the next release.

## Verification

`tests/test_firstparty.py` (location, symbolic links, name mismatch, a changed package, a damaged or
misplaced shipped record, reproducible generation) and `tests/test_gate.py` (mixed first-party and
third-party selections). Specified in `docs/specs/trust-and-approval.md`, "First-party packages", and
`docs/specs/module-contract.md`, "Capabilities".

## Related files and decisions

- `docs/specs/trust-and-approval.md`, `docs/specs/module-contract.md`
- [2026-10-19-uniform-package-trust](2026-10-19-uniform-package-trust.md)
- `docs/plans/2026-10-19-module-approvals.md`
