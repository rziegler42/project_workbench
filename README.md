# project-workbench

A vendor-neutral workbench that creates and maintains projects from packages of
modules. It serves software, electronics, HDL, research, CAD, 3D printing and reverse
engineering, with two supported AI harnesses described in the
[harness modules specification](docs/specs/harness-modules.md).

> Status: early implementation. The installer, the verifier, owner approvals, the
> base project, ownership and upgrade, recovery of unfinished writes, and the Claude
> harness are built and tested. The first content module, `groundwork`, is planned.
> Nothing here is released yet.

## What is built

The code is Python 3 using only the standard library, in `workbench/`, with tests in
`tests/`. The commands are listed in [Development](docs/development.md).

- **Verify and approve.** `verify` checks a package without writing into it. `approve`,
  `pin` and `release-approvals` are the owner's acts and run only from a terminal.
- **Install, upgrade and add.** `install` creates a project from a package, `upgrade`
  and `add` change one, and `preview` shows each change first. `acknowledge` accepts
  changes made by others, and `recover` clears the marker of an unfinished write.
- **Claude harness.** The first-party module `claude` in `packages/workbench/` places
  the instructions, skills, agents, commands and permissions that other modules ship.
  `attach` renders them per clone, and `install` runs it as its last step.
- **Memory.** The first-party module `mempalace` lets an agent search the owner's MemPalace (`wb run mempalace search`)
  and gives the owner terminal-only commands to build it. It is tooling over a pinned helper, not an MCP server, and an
  agent cannot write to the memory. See the [mempalace specification](docs/specs/mempalace.md) for what it guarantees and
  what no test covers.
- **Check.** `check` is read-only. It reads the git index itself and never runs git,
  and it reports tracked files that point at untracked content.

The next plan, `groundwork-module`, adds a module for specs, roadmaps, decisions and
references, with three neutral skills and document checks in `check`.

## Install

There is nothing to install. The code is Python 3 using only the standard library, and
it runs from a checkout of this repository. Nothing is released as a package yet.

Run the commands from a directory you trust, such as this repository's root. A
`workbench/` directory or a `json.py` in the current directory of an untrusted project
would run instead of this code. [Development](docs/development.md) explains this and
the `wb` launcher that avoids it.

## Usage

The documented flow, in order. It has not been run end to end by hand yet, so treat the
exact arguments as the command table in [Development](docs/development.md) states them.

1. `python3 -m workbench verify <package>` checks a package and writes nothing into it.
2. `python3 -m workbench approve <package>` records your approval. It is owner-run and
   works only from a terminal.
3. `python3 -m workbench preview install <target> --package <source> --select <module> ...`
   shows what an install would write.
4. `python3 -m workbench install <target> --package <source> --select <module> ...`
   creates the project and attaches the harness as its last step. It is owner-run.
5. `python3 -m workbench check <target>` reports drift and tracked files that depend on
   untracked content. It is read-only.

`upgrade`, `add`, `acknowledge`, `recover` and `attach` are described in
[Development](docs/development.md). The owner-run commands refuse to run from an agent
session. Run the tests with `python3 -B -W error tests/run_all.py`.

## Documentation

- [Specifications](docs/specs/README.md) — the approved design
- [Decisions](docs/decisions/README.md) — why the design is the way it is
- [Roadmap](docs/roadmaps/workbench-v1.md) — the first version, as candidates
- [Plans](docs/plans/README.md) — the work, one file per plan
- [Architecture](docs/architecture.md)
- [Development](docs/development.md) — commands and checks
- [Documentation guide](docs/README.md)

## Project status

The `workbench-v1` roadmap lists the work, and completion is derived from the plans
that name each candidate. Known limits and open items are recorded in each
specification, notably the "As built, and its limits" section of the harness modules
specification.

## License

MIT. See [LICENSE](LICENSE).
