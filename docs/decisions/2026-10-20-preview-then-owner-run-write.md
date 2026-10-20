# A project write is previewed read-only and then written by an owner-run command

Status: Proposed
Date: 2026-10-20

## Context

`install`, `upgrade` and adding a module write a project. The roadmap requires a preview the owner
approves first. The first design was one command that previews when it has no terminal and writes
when it has one. Review showed that an agent can open its own pseudo-terminal, pass the terminal
test and type the digest it just printed. The typed digest is friction and not authentication
(`trust-and-approval.md`, "Residual risk"); only the harness's deny rules keep an agent from a
command.

## Decision

- `wb preview install|upgrade|add` is read-only and may be run by an agent. It prints the preview
  and no token to type.
- `wb install`, `wb upgrade` and `wb add` write, are owner-run and terminal-only, and are denied to
  an agent by the harness, as are `attach`, `approve`, `pin` and `release-approvals`.
- A write command computes the preview in its own process, shows it, and asks for the first 12
  characters of its digest. Nothing is stored between steps and no digest is accepted from another
  run.
- The approval binds a SHA-256 digest of an injective encoding of the whole write plan. After the
  approval the command writes from the bytes it already holds and checks the digest again first.
- Nothing is committed, pushed or published. A failure after writing stops, reports what was
  written, and exits 3.

## Alternatives considered

- **One command: preview without a terminal, write with one.** Rejected: an agent with a
  pseudo-terminal completes it.
- **A stored preview and an approval token.** Rejected: something stored can be edited or
  forged between the two steps.
- **A flag such as `--yes`.** Rejected: it removes the owner's approval.

## Consequences

- The harness modules must render a `deny` for the seven owner-run commands. That requirement is
  in `trust-and-approval.md`, "Rendering rules", and no harness renders it yet.
- An agent can still tell the owner what a write would do, by running `preview`.

## Verification

Not built. The specification is `docs/specs/installer-interface.md`, "The preview and approval".
The build will test that a write command refuses without a terminal and that a changed plan fails
the digest check.

## Related files and decisions

- `docs/specs/installer-interface.md`, `docs/specs/trust-and-approval.md`
- `docs/plans/2026-10-20-installer-interface.md`
- [2026-10-19-non-destructive-upgrades](2026-10-19-non-destructive-upgrades.md)
- [2026-10-19-restrictive-only-permissions](2026-10-19-restrictive-only-permissions.md)
