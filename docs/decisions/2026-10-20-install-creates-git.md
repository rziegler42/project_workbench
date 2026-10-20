# Install creates the `.git` directory itself, and only when there is none

Status: Proposed
Date: 2026-10-20

## Context

A target is new when it is missing, empty, or holds only a real `.git` directory, and existing
when it has its own real `.git` and a regular-file manifest
([2026-10-20-target-decided-by-state](2026-10-20-target-decided-by-state.md)). No document said
what makes the `.git`. Without it, an install into a missing or empty directory would leave a
directory that every later project command refuses. Running git in a directory that already has
a `.git` can run code named by its configuration.

## Decision

- Where the target has no `.git`, `install` runs `git init --initial-branch=main` itself. It is
  an action of the preview and is covered by the digest.
- Git runs with a scrubbed `GIT_*` environment, global and system configuration ignored and an
  empty template directory, as the download does.
- Where the target already holds a `.git`, `install` never runs git there and never reads its
  configuration. A lone `.git` is used as it is.
- The marker `.workbench/local/incomplete` is created before `git init`, so a failure in it is
  found.

## Alternatives considered

- **Ask the owner to run `git init` first.** Rejected: a missing directory could never be a new
  project, and the owner would do by hand what the installer can do under a fixed arrangement.
- **Run git in an existing `.git` with a scrubbed environment.** Rejected: repository
  configuration still runs code.

## Consequences

- A fresh install is an existing project straight away and is not committed.
- A lone `.git` target records no remote and warns.

## Verification

Not built. The build will test the three starting states and a hostile `.git/config` that
`preview` and `install` must never read or run.

## Related files and decisions

- `docs/specs/installer-interface.md`, `docs/specs/repository-boundary.md`
- `docs/plans/2026-10-20-base-and-manifests.md`
- [2026-10-20-target-decided-by-state](2026-10-20-target-decided-by-state.md)
- [2026-10-20-preview-then-owner-run-write](2026-10-20-preview-then-owner-run-write.md)
