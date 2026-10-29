# project-workbench

A vendor-neutral workbench that creates and maintains projects from packages of modules,
for people who want reviewed, owner-approved work with a coding agent. It serves software,
electronics, HDL, research, CAD, 3D printing and reverse engineering, with two supported AI
harnesses described in the [harness modules specification](docs/specs/harness-modules.md).

> **Status:** early implementation. The installer, verifier, owner approvals, base project,
> ownership and upgrade, unfinished-write recovery, the Claude harness and the first
> content modules are built and tested. Nothing is released yet.

## Quick start

Requirements: Python 3.11 or later (standard library only), git and a POSIX shell. There
is nothing to install; the code runs from a checkout of this repository.

Run the commands from a directory you trust, such as this repository's root. A `workbench/`
directory or a `json.py` in the current directory of an untrusted project would run instead
of this code. [docs/development.md](docs/development.md) explains this and the `wb` launcher
that avoids it.

```sh
python3 -m workbench verify <package>
python3 -m workbench preview install <target> --package <source> --select <module>
```

Expected result: `verify` reports on the package and writes nothing into it, and `preview`
shows what an install would write without writing it.

## Usage

The documented flow, in order. It has not been run end to end by hand yet, so treat the
exact arguments as the command table in [docs/development.md](docs/development.md) states
them.

1. `python3 -m workbench verify <package>` checks a package and writes nothing into it.
2. `python3 -m workbench approve <package>` records your approval. It is owner-run and works
   only from a terminal.
3. `python3 -m workbench preview install <target> --package <source> --select <module> ...`
   shows what an install would write.
4. `python3 -m workbench install <target> --package <source> --select <module> ...` creates
   the project and attaches the harness as its last step. It is owner-run.
5. `python3 -m workbench check <target>` reports drift and tracked files that depend on
   untracked content. It is read-only.

A repository that already has content is adopted instead, with `preview adopt` and `adopt`
(same arguments as `preview install` and `install`). `adopt` creates only what is missing and
changes no file that exists; it attaches nothing, so run `attach` and then `upgrade` to add
the blocks it could not fill. `upgrade`, `add`, `acknowledge`, `recover` and `attach` are
described in [docs/development.md](docs/development.md). The owner-run commands refuse to run
from an agent session.

The first-party modules are in `packages/workbench/`. Among them, `claude` places the harness
files, `groundwork` adds specs, roadmaps, decisions and references, `code-work` adds plans and
the increment loop, and `mempalace` lets an agent search the owner's memory but never write to
it.

## Development

```sh
python3 -B -W error tests/run_all.py
```

Run this before asking for a review or a commit. Project conventions for people and coding
agents are in [AGENTS.md](AGENTS.md).

| Path | Contents |
|---|---|
| `workbench/` | The installer and its commands, in Python 3 |
| `tests/` | The repository's own tests; each module keeps its own under its `tests/` |
| `base/` | The files every new project starts with |
| `packages/workbench/` | The first-party modules |
| `docs/` | Project documents, indexed in [docs/README.md](docs/README.md) |

## Documentation

All project documents are indexed in [docs/README.md](docs/README.md). The commands, checks and
workflows are in [docs/development.md](docs/development.md). The `workbench-v1`
[roadmap](docs/roadmaps/workbench-v1.md) lists the work, and completion is derived from the
plans that name each candidate. Known limits are recorded in each specification, notably the
"As built, and its limits" section of the harness modules specification.

## Contributing

Changes follow [AGENTS.md](AGENTS.md). A change starts as a roadmap candidate, becomes a plan
the owner approves, and lands as reviewed local commits.

## Security

No private reporting channel is defined yet.

## License

MIT. See [LICENSE](LICENSE).
