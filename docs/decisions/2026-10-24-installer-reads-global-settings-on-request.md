# The installer may read a harness's global configuration, read-only, on the owner's request

Status: Accepted by the owner on 2026-10-24 (the design only; `repository-boundary.md` is amended and the command built by a later plan, which may wait until the cases the trial did not cover are run)
Date: 2026-10-24

## Context

A harness's global configuration can add to or replace what a project provides. A trial on 2026-10-24 (below) found a global
skill silently replacing a project skill of the same name, and a global hook running beside the project's. The owner would
like to know when a global setting may conflict with a project's, and wants that to be something only the workbench can do,
read-only against the user-level configuration, and not something a project's own code can do.

Two written authorities stand against it. `repository-boundary.md` says the workbench "never reads, checks or requires" a
harness's global configuration. The accepted decision `2026-10-19-guarded-store` rejected keeping approvals in a harness's
global configuration, because the workbench must not depend on one.

This record decides to amend the first, in the plan that builds the command, and to leave the second unchanged: a read-only report on the owner's request stores
nothing there, approves nothing from it, and the workbench works with the configuration absent, so it creates none of the
dependence the second rejects.

## Decision

Accepted as the design; a plan builds it only after `repository-boundary.md` is amended:

1. The installer's own code may read a harness's global configuration, read-only. A module's helper or check never does.
2. It does so only through an owner-run command that requires a terminal on both ends, with the test already used for the
   owner-run arguments, and not through `wb check` or any command an agent can run.
3. It prints names and paths and never values, because a global file can hold tokens and the output reaches whoever reads
   the terminal.
4. It decides nothing. Its report feeds no approval, no `allow` rule and no setting.
5. The harness module supplies, as data in its layout, where the configuration is and which keys matter. The installer parses
   the file itself with a bounded reader that does not follow links.
6. Each line of the report says "possible conflict" or "confirmed conflict" according to what has been verified. A rule whose
   precedence is not verified is reported only as possible.
7. It begins with the Claude harness. Another harness is added when its global file format is verified.

The rule in `repository-boundary.md` is amended in the plan that builds the command. Until then the spec still says the
workbench never reads a harness's global configuration, and nothing reads it. Building the command may be deferred until the
cases the trial did not cover are run.

## Alternatives considered

- **No detection; rely on the floor and on code enforcement** (`2026-10-24-project-guarantees-a-floor`). Viable, and the fallback
  while the command is not built.
- **A check run by a module.** Rejected: project-controlled code would read the owner's private configuration.
- **Add it to `wb check`.** Rejected: an agent can run it, and its output enters the model's context.
- **Copy the global configuration into the guarded store.** Rejected: it would copy secrets into a second place.

## Consequences

- The boundary rule gets an exception, which is a larger trust surface than a rule with none. It is narrow: owner-run,
  terminal-only, read-only, names and paths only.
- What counts as a conflict depends on precedence rules that are only partly verified, so the first version reports little.
- Each harness adds a global-file format to maintain.
- A global instruction file's contents cannot be compared line by line without reading values, so conflicting text between the
  global and project instruction files stays outside what this reports.

## Verification

The relevant results of the trial of 2026-10-24 (Claude Code 2.1.310, `claude -p`, a throwaway configuration directory with a
noisy user level, one or two runs each): a global skill replaced a project skill of the same name (two runs); a global hook ran
beside the project's; a project `deny` and `ask` held against a global `allow`. Not tested: a project `deny` under global
`bypassPermissions`, interactive mode, and agent tools other than `Read`. The full list is in
`2026-10-24-project-guarantees-a-floor`.

## Related files and decisions

- `docs/specs/repository-boundary.md`, `docs/specs/trust-and-approval.md`
- `2026-10-19-guarded-store`, `2026-10-19-restrictive-only-permissions`, `2026-10-24-project-guarantees-a-floor`
- Roadmap candidate `global-settings-check`
