# Closed set of module types with count rules

Status: Accepted
Date: 2026-10-19

## Context

A project is built from modules of very different roles. Some roles must occur
exactly once (the AI runtime a clone uses), some at most once (the way of working),
and most any number of times. A flat capability list can say "provides" and
"requires" but not "exactly one", and a project with two harnesses or two competing
processes has no coherent behavior.

## Decision

The set of module types is closed and owned by the installer: `harness` (exactly one
per project), `process` (at most one) and `module` (any number, the default). A module
has exactly one type. The installer stops when a project would have two harness or two
process modules. Only a `harness` module may provide the six harness capabilities. A
module's `blocks` list expresses further conflicts, a conflict is a hard stop, and a
module never conflicts with its own `provides`.

## Alternatives considered

- **Capabilities only, with a `blocks` entry for every exclusive role.** Rejected:
  "exactly one harness" cannot be stated, and every harness would need to block every
  other.
- **Open, package-defined types.** Rejected: the installer could not enforce counts it
  does not know, and a third party could define a type that bypasses a rule.
- **Several harnesses per project.** Rejected: the harness is a property of a clone.
  Switching harness means a new clone.

## Consequences

- The installer owns a small table and every module declares one type.
- Adding a type is a change to the contract and to `module-contract.md`.
- "At most one provider" beyond the table is expressed by providing and blocking the
  same capability.

## Verification

Acceptance criteria in `docs/specs/module-contract.md`: two harness or two process
modules are refused; a module that provides and blocks one capability installs alone
and is refused beside a second provider.

## Related files and decisions

- `docs/specs/module-contract.md`, `docs/specs/terms.md`
- [2026-10-19-harness-files-per-clone](2026-10-19-harness-files-per-clone.md)
