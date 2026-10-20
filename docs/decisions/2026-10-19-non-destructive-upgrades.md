# Upgrades are non-destructive, by file ownership class, with no three-way merge

Status: Accepted
Date: 2026-10-19

## Context

A project in motion has edited files and a history. An upgrade that overwrites them loses
work and can hide a hostile change. The owner has been hurt by upgrades that did exactly
that.

## Decision

Every file the installer writes into the committed tree has an owner class: module-owned,
seeded, slot block, or living or historical. Module-owned files and slot blocks are
replaced only when their hash equals the installed hash, otherwise they are left and
reported. Seeded files are never touched. Living or historical content (plans, specs,
decisions, roadmaps, references) is never touched. An upgrade shows a complete preview
classified as replace, skip, conflict or append, and writes nothing until the owner
approves. It leaves its changes uncommitted so they form one revertable change. Where a
seeded file lacks a slot a module needs, it offers to append a block on approval. A
newer module version needs its declaration approved first. An upgrade by an older
workbench is refused. Three-way merge is not performed.

## Alternatives considered

- **Three-way merge.** Deferred: complex, and a wrong merge is a silent loss.
- **Overwrite with a backup.** Rejected: still destroys work in place.
- **Never upgrade, only reinstall.** Rejected: loses edits and history.

## Consequences

- An edited module-owned file is a conflict for the owner to resolve by hand.
- Format changes are never applied in place; tools read both formats and migration is a
  separate opt-in command.

## Verification

Acceptance criteria in `docs/specs/repository-boundary.md`: the tree is unchanged if the
preview is not approved, and a seeded file or living document is never modified.

## Related files and decisions

- `docs/specs/repository-boundary.md`
- [2026-10-19-uniform-package-trust](2026-10-19-uniform-package-trust.md)
