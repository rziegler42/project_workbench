# Review is mandatory; delegating the verdict is a personal setting

Status: Accepted
Date: 2026-10-19

## Context

The owner wants continuous, unattended work without babysitting, and is willing to let a
second AI approve almost everything that is not an undoable destructive action. A second
AI can be steered by the same hostile text as the first, so delegation must be bounded
and owned by the person it affects.

## Decision

Review is a mandatory step of the programming process; it cannot be passed without a
recorded outcome. A review has findings and a verdict. A reviewer may always give
findings. The verdict is an act of authority and may be given by a delegate only when the
owner's personal setting for that checkpoint is `delegate`, a `peer-review` provider is
installed and approved, and review converged within the round cap. Every checkpoint
defaults to `stop` for anyone without settings. Delegation is never project policy. A
reviewer that is unavailable, times out or gives no verdict yields no approval and the run
stops. A plan whose risks list a hard stop is not delegable, and hard stops stop at the
time of the action regardless.

## Alternatives considered

- **Always stop for the owner.** Rejected: defeats unattended work.
- **Optional review.** Rejected: the owner wants a second check on every increment.
- **Project-level delegation.** Rejected: a contributor could set it for everyone.

## Consequences

- Review loops are bounded by caps: review rounds 3 (ceiling 5), same-failure retries 1,
  reviewer exchanges 6 per checkpoint.
- Without a provider the owner reviews, or the run stops.

## Verification

Acceptance criteria in `docs/specs/code-work.md` and `docs/specs/trust-and-approval.md`: a
reviewer that returns no verdict stops the run, and with no personal settings every
checkpoint behaves as `stop`.

## Related files and decisions

- `docs/specs/code-work.md`, `docs/specs/trust-and-approval.md`
- [2026-10-19-compiled-hard-stop-floor](2026-10-19-compiled-hard-stop-floor.md)
