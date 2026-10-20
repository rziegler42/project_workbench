# The guarded store's location is fixed and nothing can move it

Status: Proposed
Date: 2026-10-20

## Context

The guarded store holds approvals, pins and the owner's settings, so whoever controls which
directory the workbench treats as the store controls what it accepts as approved
(`2026-10-19-guarded-store`). That record names the location, `~/.config/project-workbench/`, but
not whether something can change it. A convenient override, an environment variable or an option or
a file that names another store, can be set by an agent in the very command it runs, and the
workbench would then read approvals the agent wrote itself. A command run by an agent can set its
own environment, and an option is part of the command.

## Decision

The location is computed from the account's home directory and is `~/.config/project-workbench/`.
No workbench environment variable, command-line option or configuration file moves it. The code takes
the store's root as an argument, but only so that tests can use a temporary directory: the command
line cannot supply it. `HOME` itself is honoured, as the operating system does for any program run by
the same account; that is the same-account limit the trust specification already states, not a new
one.

## Alternatives considered

- **An environment variable such as `WORKBENCH_HOME` or `XDG_CONFIG_HOME`.** Rejected: an agent sets
  it for one command and points the workbench at a store it controls.
- **A `--store` option on each command.** Rejected for the same reason, and because the deny rules a
  harness renders match a command, not what an option points at.
- **A per-project store location in a committed file.** Rejected: committed text must never choose
  where authority is read from.

## Consequences

- Tests set `HOME` for a child process or pass a temporary root to the code, and a guard in the test
  support fails any test that reaches the real location.
- An owner who wants a separate store uses another account or another `HOME`.
- Protection of the store still depends on the harness's deny rules and on the account boundary, as
  `2026-10-19-guarded-store` says.

## Verification

`tests/test_store.py` (no workbench variable moves the store; a test that asks for the real location
fails), `tests/test_cli.py` (a child process finds its store from `HOME`), and the docs in
`docs/development.md`. Specified in `docs/specs/trust-and-approval.md`, "Concrete formats".

## Related files and decisions

- `docs/specs/trust-and-approval.md`, `docs/specs/repository-boundary.md`
- [2026-10-19-guarded-store](2026-10-19-guarded-store.md)
- `docs/plans/2026-10-19-module-approvals.md`
