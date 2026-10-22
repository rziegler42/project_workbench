# Git work lives in its own module

Status: Accepted by the owner on 2026-10-22
Date: 2026-10-22

## Context

The `code-work` helper (`packages/workbench/code-work/helper/code-work`) holds two kinds of work. The
subcommands `check`, `plans` and `report` read a project's plans and are the programming process. The
subcommands `commit` and `remove`, with the git runner, the attribution guard and the expected-HEAD check,
are safe git and safe deletion. They have nothing to do with plans: the code is in the second half of the
file, below a banner, and its tests (`test_codework_git.py`, `test_codework_commit.py`,
`test_codework_remove.py`, `support_git.py`) are separate from the plan tests.

The design notes of 2026-10-19 say a CAD or EDA project uses `groundwork` plus domain modules with no
process module (`cad-work` is skipped until a project proves it is needed), and that its commits are
restore points at milestones, not review-gated units. Such a project has no safe commit. A module's helper
is a self-contained, separately pinned script and cannot import another module's, and the kit holds no git
code, so a second module that wants safe commits would copy about a thousand lines of security-sensitive
code, or install `code-work` for the helper alone.

`groundwork` is not the place: its spec lists commits and "anything else about carrying work out" as
non-goals, it ships read-only checks and writes only documents, and its approval would then cover the most
dangerous code in the packages.

Nothing yet depends on the command name. `code-work-approval`, the next candidate, adds deny rules, a gate
and policy text that name `wb run code-work commit`, so moving is cheapest now.

## Decision

- A new first-party module of type `module`, `safe-git`, ships the `commit` and `remove` commands and
  provides the capability `commit`. The owner chose the name `safe-git`; the capability name is a proposal.
- `code-work` keeps `check`, `plans` and `report` and requires `commit` (hard), because its plans README
  tells the agent to commit through the helper.
- The code moves unchanged, with its tests. Only what the move forces changes: the command name
  (`wb run safe-git commit`), and the attribution setting path, which becomes `.workbench/safe-git.json`
  with the same format.
- A project with no process module may install `safe-git` alone. `groundwork` does not require it.
- The decision `2026-10-22-commit-helper-leaves-baselines-to-the-owner` is unaffected: the helper still
  never reads or writes the guarded store.

## Alternatives considered

- **Put it in `groundwork`.** Rejected for the reasons in Context: it contradicts that spec's non-goals,
  makes a mutating tool part of the read-only document layer, and ties git fixes to the approval of the
  document layer. The one argument for it, that every project already has `groundwork`, saves a project one
  install line.
- **Leave it in `code-work`.** Rejected: a project with no process, which the notes expect for CAD, either
  goes without or installs the programming process for one helper. `cad-work` would also face a rename later,
  after `code-work-approval` has named the command in more places.
- **Move the git runner into the kit.** Rejected: the kit is mechanism every helper needs, and `commit` is
  policy (what a commit may carry, when it is refused). It would also make the installer the owner of
  git-running code, against `2026-10-21-module-code-lives-in-modules`.
- **Each domain module writes its own.** Rejected: a copy per module, each needing its own security pass and
  pin.

## Consequences

- One copy of the git code, one security pass, one pin, usable with or without a process module.
- One more module to install, approve and release. `code-work` declares a hard requirement, so installing it
  without `safe-git` stops with the requirement message.
- Moving needs a plan: a new module and its declaration, the helper split, the tests split (the mixed
  `test_codework_module.py` by hand), the policy block and README text, specs (`code-work.md`,
  `module-boundary.md`, `trust-and-approval.md`), `development.md`, the roadmap, and a re-release of the
  shipped approvals, which is owner-run. A pin recorded for `code-work` does not carry over; nothing is
  installed yet.
- The completed plan `2026-10-22-code-work-commit` stays as history and keeps the old names.
- The owner accepted the record as drafted, so the capability is named `commit` and `code-work` requires it hard.

## Verification

None yet. The plan that carries out the move would show the moved tests passing in the new module, the
`code-work` tests passing without the git code, the boundary test passing, and the released approvals
matching.

## Related files and decisions

- `packages/workbench/code-work/helper/code-work`, `packages/workbench/code-work/tests/`
- `docs/specs/code-work.md`, `docs/specs/groundwork.md`, `docs/specs/module-boundary.md`
- [2026-10-19-groundwork-shared-layer](2026-10-19-groundwork-shared-layer.md)
- [2026-10-21-module-code-lives-in-modules](2026-10-21-module-code-lives-in-modules.md)
- [2026-10-22-commit-helper-leaves-baselines-to-the-owner](2026-10-22-commit-helper-leaves-baselines-to-the-owner.md)
- [2026-10-22-plan-check-in-the-shipped-helper](2026-10-22-plan-check-in-the-shipped-helper.md)
