# The base ships in the distribution and is trusted as the workbench is

Status: Accepted
Date: 2026-10-20

## Context

Every project starts with content that no module supplies: `AGENTS.md` with its policy slot,
`docs/README.md` with its index slot, and `.workbench/.gitignore`. The module contract says the
base is not a module and has no type, but nothing says where its files live or how they are
trusted. A module needs an approval record; the base has no author other than the workbench.

## Decision

- The base is the directory `base/` in the workbench distribution, plus the generated
  `.workbench/.gitignore`. It is not a module and has no approval record.
- It is trusted as the workbench code is: the distribution is the trust root
  (`trust-and-approval.md`). A change to it is a change to the workbench and is released with it.
- The committed manifest records the base's tree hash and the workbench version, so a later
  check can tell what a project was installed from.
- The base owns two slots, `policy` and `docs-index`. A module cannot own either.

## Alternatives considered

- **Make the base a first-party module.** Rejected: it would need a type, an approval and a place
  in the order, for content every project must have.
- **Generate every base file in code.** Rejected: policy text is easier to read and review as
  files than as strings in code. Only the one-line ignore file is generated.

## Consequences

- The verifier knows the base slots, so a fill of either needs no selected owner.
- An install reads the base through the safe reader and refuses a link or a special file.

## Verification

Built and tested (`tests/test_base.py`, `tests/test_verify.py`): the base is hashed from the bytes
read, contains no harness file name, holds each slot marker exactly once, refuses links, special
files and executables, and a module that owns a base slot is refused. The specification is
`docs/specs/repository-boundary.md`, "The base".

## Related files and decisions

- `docs/specs/repository-boundary.md`, `docs/specs/module-contract.md`
- `docs/plans/2026-10-20-base-and-manifests.md`
- [2026-10-19-closed-module-types](2026-10-19-closed-module-types.md)
- [2026-10-20-first-party-by-location-and-shipped-record](2026-10-20-first-party-by-location-and-shipped-record.md)
