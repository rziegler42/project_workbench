# A project target is decided by the directory's state, from files and without git

Status: Proposed
Date: 2026-10-20

## Context

The roadmap said that whether a command makes a new project or works on an existing one is
decided from the target's state and not from how the target was spelled, and that a directory with
a committed manifest is existing. Review of the interface specification found two problems. A
fresh install is not committed, so the install would be refused as "anything else" until the owner
committed. And running git to classify an untrusted directory executes its code: a hostile
`.git/config` can run a program through `core.fsmonitor`, and `.gitattributes` can name a filter
driver. The target can also be a symbolic link, so the place the owner typed and the place acted on
can differ.

## Decision

- A project command takes the target as `<target>` or `--dir <path>`, defaults to `.`, and refuses
  when the two spellings name different directories.
- A symbolic link as the typed target is refused. A link in a parent directory is resolved. The
  target is resolved once, opened without following links, and its identity is re-checked before
  any write.
- Root, the home directory, the guarded store, anything inside it and anything containing it are
  refused by file identity.
- New or existing is decided from the target's files and not from its spelling: a missing
  directory with an existing parent, an empty directory, or one holding only a real `.git`
  directory is new; a directory with its own real `.git` directory and a regular-file
  `.workbench/manifest.json` is existing; anything else is refused.
- Git is not run to decide this. An existing project need not have its manifest committed.

## Alternatives considered

- **A committed manifest marks an existing project, as the roadmap said.** Rejected: a fresh
  install is uncommitted, and deciding it needs git.
- **Run git with a scrubbed environment to classify.** Rejected: repository configuration and
  attributes still run code.
- **Follow a symbolic link target.** Rejected: the owner typed one place and the installer would
  act on another.

## Consequences

- `check` reports whether the manifest is committed instead of treating it as a state.
- Git is used only after a private, scrubbed arrangement that the build must test against a hostile
  configuration. The mechanism is a proposal in the specification.
- Ownership and mount-point checks of the target are deferred.

## Verification

Not built. The specification is `docs/specs/installer-interface.md`, "The target" and "States of a
target". The build will carry tests for each state and for a hostile `.git/config`.

## Related files and decisions

- `docs/specs/installer-interface.md`, `docs/specs/repository-boundary.md`
- `docs/plans/2026-10-20-installer-interface.md`
- [2026-10-19-guarded-store](2026-10-19-guarded-store.md)
- [2026-10-20-fixed-store-location](2026-10-20-fixed-store-location.md)
