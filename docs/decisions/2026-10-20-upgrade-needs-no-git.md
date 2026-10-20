# An upgrade asks no git question; cleanliness is decided by file hashes

Status: Accepted
Date: 2026-10-20

## Context

The interface specification asked an upgrade to require a clean working tree for the affected
paths and to refuse straight after an uncommitted install. Only git can say what is committed,
and asking git safely needs a private git directory tested against a hostile configuration,
because a repository's configuration and attributes can name programs git runs.

## Decision

- `upgrade` and `add` run no git command. A path is replaced only when its current hash equals
  the installed hash, which is the classification itself.
- The upgrade leaves its changes uncommitted and ends by saying nothing was committed and that
  committing the result as one change makes it revertable. The sentence that an upgrade is
  refused until the install is committed is dropped.

## Alternatives considered

- **Build the private git directory now.** Rejected for this plan: a security build as large as
  the upgrade itself; `check` or a later plan can add it.
- **Read `.git` objects directly.** Rejected: parsing a hostile repository.

## Consequences

- An upgrade on an install that was never committed cannot be reverted by git.

## Verification

Tests of the plan `2026-10-20-ownership-and-upgrade`: no git command is run, and an upgrade
straight after an uncommitted install works.

## Related files and decisions

- `docs/specs/installer-interface.md`
- [2026-10-20-target-decided-by-state](2026-10-20-target-decided-by-state.md)
- [2026-10-19-non-destructive-upgrades](2026-10-19-non-destructive-upgrades.md)
