# A project guarantees a floor under any global setup, not identical behavior

Status: Accepted by the owner on 2026-10-24 (a working position; a change is made by a superseding record)
Date: 2026-10-24

## Context

A harness reads settings from more than one level. For Claude, the owner's user-level configuration (`~/.claude`), the
project's committed files and the project's per-clone files are all read and combined. The owner maintains the user level; the
workbench's Claude harness module writes only the per-clone project files. The owner wants a consistent workbench experience
in a project whatever the user level holds.

Three things were already known. `harness-modules.md` records that hook entries merge across settings levels and that
precedence between project and local files is not verified. `restrictive-only-permissions` keeps every convenience allowance
in the owner's own configuration, and `guarded-store` and `repository-boundary.md` keep the workbench out of a harness's global
configuration. And the plan `2026-10-24-owner-run-in-code` showed that a guarantee which depends on matching command text
leaks on routes the text does not match, so a rule that matters had to move into the workbench's own code.

The owner has said this is a working position, not a settled design, and that it may change as the end design is worked out.

## Decision

1. **The floor.** Under any global configuration, a project that has the workbench keeps its own `deny` and `ask` rules, its
   edit gate, its owner-run refusals and its hard stops. These are what the workbench guarantees.
2. **No promise of identical behavior.** Convenience, prompts, and the effect of a global skill, hook or instruction file
   may differ with the owner's global configuration. The workbench does not claim to override them.
3. **A guarantee that matters is enforced in the workbench's own code.** Settings merge across levels, so a rendered setting
   is a first line and not the guarantee. The owner-run refusal in `wb run` and `wb launch` is the pattern.
4. **The workbench never writes a harness's global configuration.** The owner maintains it.

## Alternatives considered

- **Identical behavior whatever the global setup.** Rejected: the trial below shows a global hook and a global skill and
  instruction file taking effect beside or over the project's, and a project cannot remove a global `allow`.
- **Reset the owner's user level to a fresh install and supply everything from the project.** This was the owner's first
  statement of the end state. Rejected in favor of the split above: the owner's allowances and approver hook live at the user
  level by `restrictive-only-permissions`, and the project cannot write there.
- **Write into the user level.** Rejected by `guarded-store` and `repository-boundary.md`.
- **Say nothing.** Rejected: without a stated floor, each later plan guesses what a project can promise.

## Consequences

- A global skill was observed to replace a project skill of the same name, and the workbench cannot prevent it. A module
  skill name the owner's own configuration might also use is at risk; a project agent was observed to win over a global one.
- A global hook and the global instruction file were observed to apply beside the project's. The workbench can avoid depending
  on them and cannot switch them off.
- New guarantees are written as code in the installer or the launcher, with a test, and not as text a harness may merge.
- A check that reports where a global setting may conflict is a separate decision (`2026-10-24-installer-reads-global-settings-on-request`).

## Verification

A trial on 2026-10-24 with Claude Code 2.1.310, run with `claude -p`. A throwaway configuration directory, chosen with
`CLAUDE_CONFIG_DIR`, held a deliberately noisy user level: `allow: Bash(*)`, a `PreToolUse` hook on Bash that wrote a line to a
log, a skill and an agent each named like a project one with a marker in their text, and an instruction file saying every push
is pre-approved and every reply begins with a marker word. The project was a throwaway workbench project with 122 `deny` and 58
`ask` rules rendered by the Claude harness. Each result was read from the run's `permission_denials` and reply. One or two runs
each; the model chose how to carry out each request.

1. A project `deny` held against the global `allow`, and held with the global default mode `auto`: the command was denied and
   did not run.
2. A project `ask` held against the global `allow`, with `auto`, and with `bypassPermissions`: the command did not run. In
   `-p` mode an `ask` is denied and not prompted, so interactive behavior is not shown.
3. The global hook ran for commands the project denied and for commands it asked on.
4. A global skill with the same name as a project skill was the one loaded (two runs).
5. A project agent with the same name as a global agent was the one loaded (one run).
6. Both the global instruction file and the project's instructions were loaded; asked whether a push needed approval, the
   model treated the global grant as satisfying the project's "explicit approval" only when asked to push, and said the files
   do not say which wins.
7. With `CLAUDE_CONFIG_DIR` set, the owner's real user-level instruction file was loaded as well as the throwaway one (cause not
   established); the real user-level settings file was not (a control command that the real settings ask on ran).

Not tested: a project `deny` under global `bypassPermissions` (the harness's classifier refused that call and it was not
retried), interactive mode against `-p`, the edit-gate hook (the trial project had no process module), and any agent tool other
than `Read`. The decision can change if those results differ.

## Related files and decisions

- `docs/specs/harness-modules.md`, `docs/specs/repository-boundary.md`, `docs/specs/trust-and-approval.md`
- `2026-10-19-restrictive-only-permissions`, `2026-10-19-guarded-store`, `2026-10-23-one-owner-per-skill-name`
- Roadmap candidates `global-config-migration` and `global-settings-check`
