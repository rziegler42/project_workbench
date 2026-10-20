# Harness files are per-clone output and are never committed

Status: Accepted
Date: 2026-10-19

## Context

Developers on one project may use different AI harnesses, each with its own root file
and skill, agent, command and settings directories. Committing those files ties the
repository to one harness, clutters history, and lets a contributor commit
configuration that another developer's agent then trusts.

## Decision

Harness files are generated per clone by `attach` and are never committed. The
committed repository names no harness: no committed file lists a harness's file names,
root file or directories. Generated paths are kept out of git through
`.git/info/exclude`, not a tracked ignore file. The committed `.workbench/.gitignore`
contains only `/local/`. A clone may have no harness attached. Changing harness means
a new clone, repopulated by `git pull`.

## Alternatives considered

- **Commit harness files.** Rejected: ties the project to one harness and puts
  agent-readable configuration under any contributor's control.
- **Ignore harness paths in a tracked `.gitignore`.** Rejected: that file would name
  the harness in the committed repository.
- **Support swapping harness in place.** Deferred: a new clone is simpler and safe.

## Consequences

- A fresh clone has no harness files until `attach` runs.
- The committed tree is byte-identical across clones that differ only in harness.
- A `check` reports stray, drifted or tracked harness files.

## Verification

Acceptance criteria in `docs/specs/repository-boundary.md` and
`docs/specs/harness-modules.md`: no harness file appears in `git ls-files`, and the
committed manifest never names a harness.

## Related files and decisions

- `docs/specs/repository-boundary.md`, `docs/specs/harness-modules.md`
- [2026-10-19-closed-module-types](2026-10-19-closed-module-types.md)
- [2026-10-19-tracked-pointer-rule](2026-10-19-tracked-pointer-rule.md)
