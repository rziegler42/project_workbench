# A harness module writes nothing committed

Status: Proposed
Date: 2026-10-20

## Context

The committed repository names no harness
([2026-10-19-harness-files-per-clone](2026-10-19-harness-files-per-clone.md)). A harness module
is mandatory at install, but attach is not built. The roadmap said install had no harness step
yet; the interface specification said it ends with attach. A module may also declare `writes` and
`fills`, which land in committed files.

## Decision

- `install` requires, verifies and approves exactly one harness module, as for any module, and
  writes nothing for it. The committed manifest and the module namespaces do not name it.
- Until attach is built, `install` prints `harness not attached: attach is not built yet`.
- A harness module that declares `writes` or `fills` is refused at install, because a committed
  file it wrote would name the harness.

## Alternatives considered

- **Skip the harness requirement until attach exists.** Rejected: it would change the contract
  twice and let a project be installed that cannot later be attached.
- **Let a harness module write committed files.** Rejected: it would name the harness in the
  committed repository.

## Consequences

- `claude-harness` adds the attach step to `install`.
- A package that holds only a harness is omitted from the manifest.

## Verification

Not built. The build will test that a harness module's files are absent from the written tree
and the manifest, and that a harness module declaring `writes` or `fills` is refused.

## Related files and decisions

- `docs/specs/module-contract.md`, `docs/specs/installer-interface.md`
- `docs/plans/2026-10-20-base-and-manifests.md`
- [2026-10-19-harness-files-per-clone](2026-10-19-harness-files-per-clone.md)
- [2026-10-19-closed-module-types](2026-10-19-closed-module-types.md)
