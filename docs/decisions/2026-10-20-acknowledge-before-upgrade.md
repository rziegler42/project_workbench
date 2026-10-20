# Baselines gate every upgrade, and the owner accepts a change with `wb acknowledge`

Status: Accepted
Date: 2026-10-20

## Context

The committed manifest is text anyone with write access to the repository can edit, and an
upgrade reads it to learn what was installed. If an edited manifest could say that the owner's
edited file is "as installed", the upgrade would replace the owner's work. Approving an upgrade
preview also updates the baselines, so an unreviewed edit in a file the upgrade writes into
would be accepted without being seen.

## Decision

- Before `upgrade`, `add` or `acknowledge` acts on a project, the project must have baselines
  and a first-seen record at the resolved path in the guarded store. The command compares the
  manifest, every file under `.workbench/` outside `local/` and every file it would write into
  with the baselines, and refuses on any difference, naming the paths. `wb acknowledge` lists
  every path that has a baseline, so an edited seeded file that an upgrade would write a block
  into can be accepted too and the owner is never left with a refusal no command can clear.
- The owner accepts differences with the owner-run, terminal-only `wb acknowledge`, which lists
  them and replaces the baselines for exactly the listed paths after the typed digest.
- The store keeps hashes and not old bytes, so the listing is a hash list and a parsed manifest
  summary, not a line diff.

## Alternatives considered

- **Trust the manifest after a git check.** Rejected: it needs a git question that the project
  has not built safely, and an edit that is committed is still an edit nobody reviewed.
- **Re-baseline silently at upgrade.** Rejected: it accepts an unreviewed edit.
- **Keep old bytes in the store for a line diff.** Deferred: more storage and a new data
  channel; the hash list is enough to stop the attack.

## Consequences

- A hand-edited `AGENTS.md` blocks an upgrade or add that would write into it until the owner
  acknowledges it.
- A project moved on disk, or cloned a second time, is refused until `attach` settles recording
  a remote or a move.

## Verification

Acceptance criteria in `docs/specs/trust-and-approval.md` and `installer-interface.md`; the
tests of the plan `2026-10-20-ownership-and-upgrade` (hand-edited manifest, added or removed
`.workbench/` file, edited seeded file, missing store entry).

## Related files and decisions

- `docs/specs/trust-and-approval.md`
- `docs/specs/installer-interface.md`
- [2026-10-19-non-destructive-upgrades](2026-10-19-non-destructive-upgrades.md)
- [2026-10-19-guarded-store](2026-10-19-guarded-store.md)
