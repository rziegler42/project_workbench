# Module-specific code, tests and tooling live in the module, behind a shared kit

Status: Accepted
Date: 2026-10-21

## Context

The installer (`workbench/`) and its tests (`tests/`) were meant to hold only what is specific to the
workbench. Module-specific code has collected in them: the document checks of `groundwork`
(`doccheck`, `refcheck`, `refindex`), the `wb code-work` dispatch, the paths and settings file of the
`claude` harness, and about four thousand lines of tests for those modules. Two causes: a module had no
place for its tests or tooling, and the accepted decision
`2026-10-21-installer-runs-document-checks` put the groundwork checks in the installer because a
module's helper is a single file and could not reuse the installer's careful file reading. The
result is an installer that cannot be understood, changed or tested without the modules it ships.

## Decision

The rule in `docs/specs/module-boundary.md` is adopted: the installer's code and tests contain mechanism
only, and anything specific to a module lives in that module's directory. To make that possible:

- The workbench provides a **kit**, a small standard-library library with its own API version, that the
  installer and module helpers share. A Python helper reaches it through a fixed runner that enforces the
  version the module declares.
- A module has two maintainer directories, `tests/` and `tools/`, that are hashed and approved, never
  installed and never run by the installer. One test command runs the installer's tests and every
  module's.
- A module offers commands (`commands`, run with `wb run`) and contributes to `wb check` (`checks`)
  through pinned helpers, declared in its `module.json`. The installer knows no command or check by name.
- A harness's paths come from its module's `layout`, not from tables in the installer.
- The installer's tests use synthetic modules.

This record supersedes `2026-10-21-installer-runs-document-checks`, which is marked accordingly. The
earlier record's rules for what a check reports are unchanged; where the checks run, and in what code, changes. This record also adopts what
that record rejected for now, a `checks` field in the declaration, in the form the specification
defines, and answers its rejected "check shipped as module code" by running the checks as pinned helpers
over the kit.

## Alternatives considered

- **Leave the code in the installer and only move the tests.** Rejected: it keeps the installer
  entangled, and a check's tests would live far from the check.
- **Copy the careful reading code into each helper.** Rejected: security-sensitive code duplicated in
  every module drifts and is reviewed once per copy. The kit has one implementation that the installer
  uses too.
- **Let a helper import the installer.** Rejected: it ties every helper to the installer's internals and
  puts the whole installer on the helper's attack surface.
- **A plugin interface that runs module code in the installer's process.** Rejected: the installer
  never runs what a module ships (`module-contract.md`); a pinned helper in its own process, started by
  the launcher, keeps that.
- **An MCP server as the module interface.** Deferred in the specification: the command line is already
  the neutral interface.

## Consequences

- Module checks and commands run approved code against hostile repository content, where the installer's
  own checks did not. The kit makes the reading safe; it cannot make a helper write nothing. A check that
  is unpinned or edited is a problem, never a silent skip.
- A change that raises the kit API needs every helper's declaration, and so its approval, updated with
  it. This is deliberate while the modules are first-party.
- The package tree hash changes for every module that gains code or tests, so the shipped approvals are
  released again at each step (`release-approvals`, run by the owner).
- Moving the code is several plans, in the order the specification gives. The open plan
  `code-work-plans` is reconsidered after `wb run` exists. Until each move lands, the code stays where
  it is: the document checks keep running in the installer until the plan that moves them to `groundwork`
  lands, though the older record no longer governs where they belong.
- `module-contract.md`, `terms.md` and `installer-interface.md` change with the first plan that builds
  each part.

## Verification

Each plan that moves code records its own evidence. The boundary test in the specification (no
first-party module, helper, harness name or harness path in `workbench/` or `tests/` outside the release
mechanism) fails while any module-specific code is left in the installer, and passes when the last move
is done.

## Related files and decisions

- `docs/specs/module-boundary.md`
- [2026-10-21-installer-runs-document-checks](2026-10-21-installer-runs-document-checks.md) (superseded by this record)
- [2026-10-20-isolated-launcher-invocation](2026-10-20-isolated-launcher-invocation.md)
- [2026-10-20-first-party-by-location-and-shipped-record](2026-10-20-first-party-by-location-and-shipped-record.md)
- [2026-10-19-uniform-package-trust](2026-10-19-uniform-package-trust.md)
