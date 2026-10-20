# Development

## Setup

There is no code yet, so there is nothing to set up. The repository assumes git, a
POSIX shell and `python3`, as `docs/specs/repository-boundary.md` states.

## Commands

Keep this table accurate. Use `not applicable` rather than leaving an
ambiguous blank.

| Purpose | Command |
|---|---|
| Setup | not applicable (no code yet) |
| Run locally | not applicable (no code yet) |
| One focused test | not applicable (no code yet) |
| Full tests | not applicable (no code yet) |
| Format | not applicable (no code yet) |
| Lint or static analysis | not applicable (no code yet) |
| Type check | not applicable (no code yet) |
| Build | not applicable (no code yet) |
| All required checks | not applicable (no code yet); document checks are run by the owner in session, as `docs/README.md` states |

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

Not applicable until code exists.

## Tool-specific guidance

Use the repository's documented command interface. Add guidance for a build
system, language server, generated files, or other tool only when the project
uses it. Keep project-wide tool configuration committed and distinguish each
tool's exclusions from other tools' input filters.
