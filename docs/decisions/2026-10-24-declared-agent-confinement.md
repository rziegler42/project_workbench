# An agent's limits are declared as data and enforced by the installer

Status: Accepted by the owner on 2026-10-24 (the design only; nothing is built, and the open items below are settled by the plan that builds it)
Date: 2026-10-24

## Context

A neutral agent today restricts itself with a tool allowlist (`tools: read, search`). That is enough for a reviewer that only
reads. Some agents need more: a security reviewer must write and run small scripts, with fake programs and hostile inputs, in a
temporary area, without touching the reviewed tree. A tool list cannot narrow that: a shell cannot be limited to one directory,
and a write tool cannot be limited by name.

The owner's earlier configuration confined four agents with one guard script run as a `PreToolUse` hook on each agent. The
guard is an allowlist over shell command text and says of itself that it is not a sandbox. A committed process cannot depend on
an agent that exists only in the owner's personal configuration: what a committed process references must ship in a module or
be a checked capability. So if the workbench uses a security reviewer, the agent and its confinement must ship.

The installer already owns one hook, the edit gate (`2026-10-22-installer-owns-the-edit-gate`): the module declares data, the
installer's code decides, and the harness layout says where the hook goes.

## Decision

1. **Declared limits.** The neutral agent format gains fields that declare an agent's limits as data: the paths it may write,
   named relative to a root such as the session's temporary directory, and the commands it may run.
2. **No general shell for an elevated agent.** Running a script the agent wrote goes through one command that its module pins,
   matched by a fixed pattern with no shell parsing.
3. **The installer enforces the limits.** A generic guard in the installer reads the declared fields and is rendered into the
   harness as a per-agent hook, as the edit gate is. A module ships no guard code.
4. **The layout names the root.** A harness layout declares where its session temporary directory is.
5. **The skill and the agent ship together.** A module that holds an elevated agent also holds the skill that uses it, is
   optional, and provides a capability of that name. A process names the capability and not the module, so declining the module
   declines both.
6. **A stated limit.** A script the agent writes and runs is not confined by any of this. The specification written for it says so.

## Alternatives considered

- **A guard script shipped by the module, as in the earlier configuration.** Rejected: it parses shell text on every tool call
  and puts module code on the permission path.
- **Keep the agent in the owner's personal configuration.** Rejected: a committed process may not depend on it.
- **No agent with write access; the parent runs the experiments.** Possible, but it moves hostile inputs into the main
  session's context, which the agent exists to avoid. Not chosen; it remains the fallback if this decision is superseded.
- **An operating-system sandbox.** Not portable across the supported systems and outside what the installer controls.

## Consequences

- A specification change (agent fields, the layout's temporary-directory entry, per-agent hook rendering) and an installer
  change come before the first elevated agent ships. Each has its own plan.
- The hard guarantee lives in the workbench's code, which can be tested, and not in a module's.
- Open, to settle in the plan that builds it: how a fixed command pattern is written and matched safely; how the installer
  learns the session's temporary directory from a hook call (the hook input carries a session id and a working directory);
  whether an interactive session asks the owner to trust a project's hooks; and that the rendered agent file is a harness file
  the project's own agent could edit, so the existing deny on the rendered settings file would need to cover it.

## Verification

A trial on 2026-10-24 with Claude Code 2.1.310, run with `claude -p` in a throwaway workbench project. A hook declared in a
project agent's frontmatter on the `Read` tool ran (a log line was written), and a hook that exited 2 on `Read` blocked it (the
refusal appeared in `permission_denials` and the agent replied with the hook's message). One run each. Not tested: interactive
mode, which may ask the owner to trust the project's hooks; and any tool other than `Read`.

## Related files and decisions

- `docs/specs/harness-modules.md`, `docs/specs/module-contract.md`
- `2026-10-22-installer-owns-the-edit-gate`, `2026-10-23-one-owner-per-skill-name`, `2026-10-19-restrictive-only-permissions`
- Roadmap candidates `agent-confinement` and `security-review-module`
