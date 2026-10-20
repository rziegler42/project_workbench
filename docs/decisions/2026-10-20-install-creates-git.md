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

- Where the target has no `.git`, `install` creates an empty one itself. It is an action of the
  preview and is covered by the digest.
- Git is not run. `install` makes `.git` with `mkdir`, which refuses any existing path including
  a link, and writes a fixed skeleton (`HEAD` on `main`, a four-key `config`, `objects/`,
  `refs/`) through descriptors it holds. *(Changed during the build: the first build ran
  `git init` with a scrubbed environment and an empty template, as the download does. A
  security review showed that git resolves the path itself, so a link planted at `.git` after
  the check made it write the repository into another directory. No program now touches a path
  in the target.)*
- Where the target already holds a `.git`, `install` never runs git there and never reads its
  configuration. A lone `.git` is used as it is.
- The marker `.workbench/local/incomplete` is created before the `.git`, so a failure in it is
  found.

## Alternatives considered

- **Ask the owner to run `git init` first.** Rejected: a missing directory could never be a new
  project, and the owner would do by hand what the installer can do under a fixed arrangement.
- **Run git in an existing `.git` with a scrubbed environment.** Rejected: repository
  configuration still runs code.
- **Run `git init` in the new directory.** Built first and withdrawn: it is path-based, so a
  `.git` link planted after the check redirected it (15 of 15 trials in the review). Running it
  from a held `.git` descriptor with `--git-dir=.` would work but was not tested, and it adds a
  subprocess that the skeleton does not need.

## Consequences

- A fresh install is an existing project straight away and is not committed.
- A lone `.git` target records no remote and warns.

## Verification

Built and tested (`tests/test_install.py`, `tests/test_projectfs.py`): the three starting
states; a hostile lone `.git/config` that is never opened and no program run; a symbolic link
or directory planted at `.git` after the marker (nothing is written outside, exit 3); a failure
during the `.git` leaves the marker; and real git accepts the result (`status`, `fsck`,
`symbolic-ref`). The `config` omits `ignorecase` and `precomposeunicode`, which git sets from
the filesystem; paths that differ only by case are refused by the plan already.

## Related files and decisions

- `docs/specs/installer-interface.md`, `docs/specs/repository-boundary.md`
- `docs/plans/2026-10-20-base-and-manifests.md`
- [2026-10-20-target-decided-by-state](2026-10-20-target-decided-by-state.md)
- [2026-10-20-preview-then-owner-run-write](2026-10-20-preview-then-owner-run-write.md)
