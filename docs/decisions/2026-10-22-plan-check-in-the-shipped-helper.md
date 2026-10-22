# The plan check lives in the helper the `code-work` module ships

Status: Proposed
Date: 2026-10-22

## Context

The `code-work` module needs a plan check: one `Candidate:` line, the sections of the hashed region,
required fields, the labels of the increments. The groundwork document checks run in code that
`groundwork` ships as helpers (`2026-10-21-module-code-lives-in-modules` supersedes
`2026-10-21-installer-runs-document-checks`, which had put them in the installer because a module with no
code needed it). `code-work` already ships code, a single-file helper that the launcher runs from a private
copy. The check reads plans, which anyone who can commit may write, so the reader must be bounded and must
not follow links.

## Decision

The plan check is a subcommand of the helper `code-work` ships, `wb run code-work check`, beside `plans`
and `report`. The helper is one file that imports nothing from `workbench/`. It repeats the fence and
quotation handling of the groundwork `doccheck` helper, and a parity test on a hostile corpus keeps the two
in step. The installer knows nothing of plans.

## Alternatives considered

- **A `wb check` addition that reuses the groundwork reader.** One tested reader and no separate pin step,
  but the installer would know the plan format, which the module-boundary rule forbids, and the helper
  would have nothing to prove about shipping, pinning and launching untrusted input.
- **Install-time checking.** Rejected: the installer never runs a module's code at install, and a plan is
  written after the install.

## Consequences

- The plan format can change with the module, in one place, without an installer release.
- Two readers of the same fenced-text rules exist and could drift; the parity test is the guard.
- The helper is a pinned helper like any other: edited bytes are refused until acknowledged
  (`2026-10-22-installer-pins-declared-helpers`).

## Verification

- `packages/workbench/code-work/tests/` (the helper, the reports, the module and the end-to-end path); the
  parity of the fence and quotation handling with `doccheck` is `test_codework_helper.py`, class `Agreement`.
- Plan `2026-10-21-code-work-plans`, increments B, C, D, E and G.

## Related files and decisions

- `docs/specs/code-work.md`, `docs/specs/module-boundary.md`
- [2026-10-21-module-code-lives-in-modules](2026-10-21-module-code-lives-in-modules.md)
- [2026-10-21-installer-runs-document-checks](2026-10-21-installer-runs-document-checks.md)
