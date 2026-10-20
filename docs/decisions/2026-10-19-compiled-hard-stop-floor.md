# The hard-stop floor is compiled in; committed policy may only tighten

Status: Accepted
Date: 2026-10-19

## Context

Some actions are irreversible or externally effecting. If the list of them lived in a
file, a damaged settings file or a hostile commit could shorten it. A reviewing AI
reads the same text as the agent and can be steered the same way.

## Decision

The floor of hard stops is compiled into the installer, and also seeded additively into
the owner's personal settings. The compiled floor always applies, so deleting or
damaging the settings cannot remove it. The floor is: force operations and rewriting
pushed history; deleting uncommitted project files or overwriting an existing or tracked
file with fetched content; publishing or deploying; anything touching secrets; and
installing dependencies. Modules may add hard stops; nothing, including committed
project policy, may remove one. Committed policy may tighten and never loosen or grant.
Each harness that provides `permissions` receives the floor as local deny and ask rules.
Deleting in scratch or the temporary directory is a personal permission, not a hard stop.

## Alternatives considered

- **Floor in settings only.** Rejected: removable by damaging one file.
- **Committed, project-editable floor.** Rejected: a contributor could loosen it.
- **Rely on a reviewing AI to enforce it.** Rejected: it can be steered by the same text.

## Consequences

- Changing the floor needs a new workbench version.
- Enforcement is mechanical only where a harness provides `permissions`; elsewhere it is
  by instruction, with a warning.

## Verification

Acceptance criteria in `docs/specs/trust-and-approval.md`: a module that tries to remove a
floor entry is refused, and a plan that omits its risks section still cannot cause a hard
stop to be skipped.

## Related files and decisions

- `docs/specs/trust-and-approval.md`
- [2026-10-19-guarded-store](2026-10-19-guarded-store.md)
- [2026-10-19-restrictive-only-permissions](2026-10-19-restrictive-only-permissions.md)
