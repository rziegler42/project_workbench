# Development

## Setup

There is nothing to set up and no dependency is installed. The code is Python 3 using
only the standard library, and the repository assumes git, a POSIX shell and `python3`,
as `docs/specs/repository-boundary.md` states.

Minimum Python version: 3.6, the lowest minor version that has every language feature
written so far (f-strings are the newest). The checks have been run only on 3.14; the
minimum is derived from the features used, not from running older interpreters. Raise
it here whenever a later increment uses a newer feature.

## Commands

Keep this table accurate. Use `not applicable` rather than leaving an
ambiguous blank.

| Purpose | Command |
|---|---|
| Setup | not applicable (standard library only; nothing to install) |
| Run locally | `python3 -m workbench verify [<package> \| --dir <path>] [--select <module> ...] [--no-harness-required]` |
| Verify the sample package | `python3 -m workbench verify tests/fixtures/sample-package --select sample-harness sample-notes` |
| One focused test | `python3 -m unittest tests.test_package` |
| Full tests | `python3 -m unittest discover -s tests` |
| Format | not applicable (no code yet) |
| Lint or static analysis | not applicable (no code yet) |
| Type check | not applicable (no code yet) |
| Build | not applicable (no code yet) |
| All required checks | `python3 -m unittest discover -s tests`; document checks are run by the owner in session, as `docs/README.md` states |

## The verify command

`verify` reads a package and writes nothing into it or anywhere else except the guarded
store (see below). The package is the positional argument or
`--dir`, defaulting to `.`; the same path given both ways is accepted, two different
paths are a usage error. Without `--select` it checks every module on its own; with it,
it also checks the named modules as one install (`<module>` or `<package>/<module>`),
and prints the install order. A harness module is required in a selection unless
`--no-harness-required` is given.

| Exit code | Meaning |
|---|---|
| 0 | accepted; one line per module with its version and the first twelve characters of the declaration and tree hashes, then warnings |
| 1 | refused; one `refused:` line per problem on stderr, naming the package or module and the rule |
| 2 | usage error |

## The guarded store

Every command first makes sure the guarded store, `~/.config/project-workbench/`, exists.
It creates the directory and `packages/`, `cache/`, `projects/` and `bin/` with mode
`0700` when they are missing, and does nothing when they are there. The command line then
seeds the personal settings if they are missing (`Store.ensure` itself only makes the
directories, so settings depend on the store and not the reverse). A failure to seed ends
the command with exit code 1. Notes about the settings are printed with the verify
warnings and start with `settings:`. A store or one of
those directories that is a symbolic link, is owned by another user, or has any mode
other than `0700` (group or other access, setgid, sticky) is refused with exit code 1, and nothing is repaired. A usage error or
`-h` does not create it.

- The personal settings are the file `settings` in the store: strict JSON with a
  `version`, a `checkpoints` object (`stop` or `delegate` per checkpoint name) and a
  copy of the hard-stop floor's ids. A missing file is created. With no settings, or with
  any entry that is missing or not exactly `delegate`, a checkpoint stops. A damaged file
  is never overwritten: the command prints a `settings:` warning and everything stops
  until the owner repairs it.
- The hard-stop floor is compiled into `workbench/floor.py`. The copy in `settings` is for
  reading and rendering only; editing or deleting it changes nothing. `effective_stops`
  can combine added stops with the floor and refuses any removal; no module declares an
  added stop yet.
- The location is fixed. No workbench environment variable moves it; `HOME` decides it,
  as for any program run by the same account.
- The store is a mechanical barrier, not an operating-system one, and it shares the
  owner's account. Until `claude-harness` renders a deny rule on writes to it, it is
  protected by instruction only.
- Tests never touch the real store. They pass a temporary root, or set `HOME` for a child
  process, and `tests/support.py` fails a test that asks for the real location. After a
  full test run, `~/.config/project-workbench` should not have been created by the suite.

## Verification workflow

1. Run the narrowest check covering the change.
2. Inspect the complete useful failure output and correct the root cause.
3. Rerun the failed check.
4. Run the broader required check when practical.

Document checks that intentionally update snapshots, fixtures, generated code,
or tracked artifacts.

## Local debug artifacts

Keep retained, untracked diagnostics in
`/.debug/<YYYY-MM-DD>-<topic>/`. Opt in locally; do not add this directory to
the tracked `.gitignore`:

```sh
printf '/.debug/\n' >> .git/info/exclude
mkdir -p .debug
```

Include a local README with the source commit, command and tool versions,
purpose, and conclusion. These artifacts are not portable to fresh clones or
worktrees. Record durable findings in tracked documentation, decisions, or
tests instead.

## Debugging

Run `python3 -m unittest discover -s tests -v` for per-test output. Run all
commands from the repository root.

## Tool-specific guidance

Use the repository's documented command interface. Add guidance for a build
system, language server, generated files, or other tool only when the project
uses it. Keep project-wide tool configuration committed and distinguish each
tool's exclusions from other tools' input filters.
