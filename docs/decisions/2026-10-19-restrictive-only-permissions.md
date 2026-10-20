# Neutral permission rules are restrictive only

Status: Accepted
Date: 2026-10-19

## Context

Permission rules are rendered into each harness's local settings. A neutral rule list
that could say `allow` would let a committed or third-party file widen what an agent may
do, which is the opposite of the trust model.

## Decision

The neutral rule list contains only `ask` and `deny`, each with a tool class and a
pattern, and never `allow`. An `allow` entry is rejected. Rules are rendered into local,
uncommitted harness configuration only. A convenience allowance is the owner's own and
lives in the owner's own configuration; the workbench never writes it. Committed
configuration may add a rule and may not remove one. Allowances for workbench helpers
target the `wb` launcher, not the helper.

## Alternatives considered

- **Neutral `allow` rules with approval.** Rejected: widening is exactly what
  committed content must not do.
- **Per-project allow lists.** Rejected: allowance is personal, not project policy.

## Consequences

- A project cannot ship pre-approved commands. Each owner grants their own allowances.
- Rule patterns use a neutral glob form that each harness module maps; the grammar is
  written with the schema.

## Verification

Acceptance criteria in `docs/specs/trust-and-approval.md` and
`docs/specs/harness-modules.md`: a rule list containing `allow` is rejected, and rendered
settings deny writes to the guarded store.

## Related files and decisions

- `docs/specs/trust-and-approval.md`, `docs/specs/harness-modules.md`
- [2026-10-19-compiled-hard-stop-floor](2026-10-19-compiled-hard-stop-floor.md)
