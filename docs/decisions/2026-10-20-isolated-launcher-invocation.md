# The workbench is run through the isolated launcher from project directories

Status: Accepted
Date: 2026-10-20

## Context

`python3 -m workbench` puts the current directory first on Python's module search path. A shell
that is inside a project it does not trust therefore runs that project's own `workbench/` package,
or a `json.py`, `hashlib.py` or `sitecustomize.py` it ships, instead of this code, with the owner's
privileges and before any check of ours. That applies to every command, including `approve` and the
launcher that is meant to protect the owner from a hostile edit. It was found in review of the
launcher: a repository could shadow the workbench under the very command the owner allow-listed. The
weakness is in how Python starts, so no code inside the workbench can close it.

## Decision

From any project directory the workbench is run through the `wb` launcher in the guarded store's
`bin/`. The launcher runs `python3 -I` (isolated mode), which keeps the current directory and
`PYTHONPATH` off the module search path, and adds the workbench directory by hand. The
`python3 -m workbench` form is for a trusted directory only, such as the workbench checkout during
development. Every harness module that gives the agent a way to run the workbench, and every
permission rule it renders for it, names the launcher and not the `-m` form.

## Alternatives considered

- **Keep `python3 -m workbench` everywhere.** Rejected: it lets a hostile project run its own code
  in place of the workbench.
- **`python3 -P -m workbench`.** Rejected for now: `-P` needs Python 3.11, and the isolated mode
  works on every supported version.
- **Check the working directory inside the workbench.** Rejected: the code that would check has
  already been imported from the working directory.
- **Install the workbench as a package on the interpreter's path.** Not decided: how the workbench
  is distributed and installed is not specified yet.

## Consequences

- A harness that exposes the workbench to an agent must call `bin/wb`; `claude-harness` is the first
  place this applies.
- The owner puts `~/.config/project-workbench/bin` on `PATH` to use `wb`; the workbench never does.
- `wb` assumes the workbench is a directory on this machine, until packaging is decided.
- Isolated mode also ignores `PYTHON*` environment variables and the user's site packages. The
  workbench uses only the standard library, so nothing is lost.

## Verification

`tests/test_launch.py`: running `bin/wb` from a directory full of hostile `workbench`, `json`,
`hashlib` and `sitecustomize` files, and with a hostile `PYTHONPATH`, runs none of them; putting the
wrapper back to the `-m` form fails those tests. Specified in `docs/specs/trust-and-approval.md`,
"Invoking the workbench", and described in `docs/development.md`.

## Related files and decisions

- `docs/specs/trust-and-approval.md`, `docs/development.md`
- [2026-10-19-guarded-store](2026-10-19-guarded-store.md)
- [2026-10-19-implementation-language](2026-10-19-implementation-language.md)
- `docs/plans/2026-10-19-module-approvals.md`
