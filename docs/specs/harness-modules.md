# Harness modules

Status: Current. Approved by the owner on 2026-10-19; implementation has not started. Paths, field names and
formats are proposals. Every statement about what a particular harness reads is taken
from its official documentation as read on 2026-10-19 and must be re-checked against
the installed version before implementation; the places where it is unverified are
marked.

Terms are defined in `terms.md`. A harness module is a module (`module-contract.md`)
of type `harness`. Where its files go and what is never committed is defined in
`repository-boundary.md`. The rules for permissions and hooks are in
`trust-and-approval.md`.

## Purpose and scope

This specification defines how a harness module describes one AI agent runtime, how
neutral items from other modules are translated into that runtime's files, how rules
are rendered into its local configuration, and what the first two harnesses, Claude
and opencode, do. It lets a module author write an item once and have every attached
harness receive it.

Non-goals:

- Codex as a harness. It is out of the first version. This specification records its
  shape only so that nothing here rules it out.
- The content of any skill, agent or command.
- How a harness is chosen. A project has exactly one harness module, and a clone may
  have none attached.

## What a harness module declares

A harness module's declaration (see `module-contract.md`) has type `harness` and
provides some or all of the six harness capabilities: `instructions`, `skills`,
`agents`, `commands`, `hooks` and `permissions`. In addition it carries a layout
description in a `layout` field of `module.json`, which the installer reads as data.
The layout is therefore part of the declaration: it is covered by the declaration
hash, shown in plain terms at approval and verified like any other field. A harness
module needs no extra file for it. Field names are proposals.

| field | meaning |
|---|---|
| `root` | The root instruction file: its name and how it is built, or `none`. |
| `kinds` | For each of `skill`, `agent`, `command`: the directory, the file layout, and the field mapping from the neutral front matter. A kind the harness lacks is absent. |
| `local_settings` | The per-clone file that receives rendered permission rules and hooks, or `none`. |
| `hooks` | Where hooks are declared, or `none`. |
| `exclude` | The paths to add to `.git/info/exclude` at attach. |
| `notes` | Post-install notes for steps the installer cannot perform. |

The installer applies the layout. A harness module contains no code that runs at
attach, and the installer never executes anything it ships.

## Neutral items

A module supplies an item once, under `harness/neutral/`, as a Markdown file with
simple front matter and a body. A skill may be a directory with bundled resource
files. Field names are proposals.

| kind | front matter | notes |
|---|---|---|
| skill | `name`, `description` | the body is the skill; bundled files are copied as plain files |
| command | `name`, `description`, `args` | the body is the prompt |
| agent | `name`, `description`, `tools`, optional `model` | the body is the agent's instructions |

An agent's `tools` is an abstract, restrictive set drawn from `read`, `search`,
`edit`, `shell`, `web` and `agents`. It limits what the agent has; it grants no
permission. An item may also declare `needs`, a list of capabilities it cannot work
without.

## Translation

The installer translates each neutral item into the attached harness's format using
the harness module's layout.

- An item whose `needs` the harness does not provide is skipped with a warning.
- A field the harness cannot express is dropped with a warning when dropping it only
  loses convenience.
- **An item that declares a restriction the harness cannot express is skipped with a
  warning and never installed unrestricted.** A read-only reviewer that cannot be made
  read-only on a harness is not installed there. This fails closed.
- A kind the harness lacks (for example project-level commands in Codex) may be
  translated into another kind only where the harness module says so. Otherwise the
  item is skipped with a warning.
- An override under `harness/<name>/` replaces the translation of the one item it
  matches, by kind and name. An `exclude` entry in the optional manifest in that
  directory stops one neutral item being installed for that harness, with a reason.
  Both are defined in `module-contract.md`, and every exclusion is reported.
- Every generated file's hash is recorded in the local manifest, so a later check can
  report a file that has been edited.

## Permissions

The neutral rule list is restrictive only. Each rule has an action, `ask` or `deny`,
a tool class (`shell`, `read`, `write`, `web`), and a pattern. An `allow` rule is
rejected. Patterns use a small neutral glob form that each harness module's layout
maps to its own rule syntax; the exact grammar is written with the schema.

- Rules come from the floor in `trust-and-approval.md`, from hard stops that modules
  add, and from a module's declared restrictions. Committed configuration may add a
  rule and may not remove one.
- Each harness that provides `permissions` receives the rules in its per-clone local
  settings, which are uncommitted. The rendering is regenerated at attach and
  reported if it drifts.
- Rendered rules include a deny on writes to the guarded store and a deny on the
  command that records an approval, so the agent cannot approve its own work.
- A harness that provides no `permissions` yields a warning at attach that hard stops
  and the guarded store are enforced only by instruction.
- The owner's own `allow` rules remain in the owner's configuration. The workbench
  never writes them.

## Hooks

Hooks have no neutral form. They are code that runs, so they ship only as files under
`harness/<name>/`, are listed under `ships` in the declaration, and are shown in
plain terms when the module is approved. A harness that declares `hooks: none` simply
does not receive them.

## Root files and instructions

- Every harness reads `AGENTS.md` for project policy, directly or through its root
  file.
- Root files are per-clone, uncommitted and regenerated at attach.
- A root file never carries project guidance of its own beyond what is generated from
  neutral policy. Claude-specific guidance goes in a module's `harness/claude/`
  override.

## The Claude harness module

Provides all six capabilities. Proposed layout, to be verified against the installed
version:

| kind or file | path |
|---|---|
| root file | `CLAUDE.md`: an `@AGENTS.md` pointer followed by a generated "Compact Instructions" section built from the neutral preservation guidance |
| skill | `.claude/skills/<name>/SKILL.md` |
| agent | `.claude/agents/<name>.md` (tool restriction through its `tools` field) |
| command | `.claude/commands/<name>.md` |
| local permissions and hooks | a per-clone settings file under `.claude/`, uncommitted (to verify: the local, gitignored variant) |

- A hook that re-injects text after a compaction ships only as a `harness/claude/`
  override.
- Excluded from git by `.git/info/exclude`: the root file and everything under
  `.claude/`.

## The opencode harness module

Provides all six capabilities, with hooks as code. Proposed layout, to be verified
against the installed version, whose documentation was inconsistent between two
generations:

| kind or file | path |
|---|---|
| root file | none: opencode reads `AGENTS.md` directly |
| skill | `.opencode/skills/<name>/SKILL.md` |
| agent | `.opencode/agents/<name>.md` (restriction through its `permission` and `mode` fields) |
| command | `.opencode/commands/<name>.md` |
| permissions | the `permission` key of project configuration (to verify: how a per-clone, uncommitted rendering is possible) |
| hooks | JavaScript plugins under `.opencode/plugins/`, which are code and shown at approval |

- Excluded from git by `.git/info/exclude`: everything under `.opencode/`, and any
  project configuration file the installer generated.
- If the project already tracks its own opencode configuration, the installer does
  not overwrite it.

## Codex (not built in the first version)

Recorded so the schema does not rule it out. Codex reads `AGENTS.md` natively with no
import and a combined size cap of 32 KiB, so project policy must stay small. Its
agents are one TOML file each with no tool list. It has no project-level commands, so
a command would be translated into a skill. Its project hooks, rules and
configuration take effect only after the user trusts the project in their own
configuration, so the installer can write them but cannot activate them and must print
a post-install note. Its rules feature is marked experimental.

## Module-provided tools

Neither harness is documented to scope one agent's shell commands or write paths:
tool restriction is by tool name, and permission rules apply to the whole session. An
agent that must do one narrow thing, such as saving a fetched file into the references
area, therefore does not get a shell. It is given a **dedicated tool**.

- A module may ship a small tool, exposed to the harness through the harness's
  tool-server mechanism (to verify for each harness), and declare it as an item the
  harness module wires into the local settings.
- A tool is named `<package>:<module>:<tool>` in a neutral agent's `tools` set. Only
  agents that list it receive it. No other agent is given it, and it is not added to
  the session-wide tools.
- A tool is code that runs, so it is listed under `ships` and shown at approval. It
  is subject to the same hash and content verification as any shipped file, and it
  never runs at install.
- A harness that cannot give a tool to one agent only, or cannot expose a tool at all,
  does not install the agent that needs it. The agent is skipped with a warning, per
  the fail-closed translation rule.

## Open issues

1. **opencode per-clone configuration.** The documentation names no uncommitted
   local-override file. Rendering permissions without editing a tracked file needs an
   answer.
2. **Verifying formats and tool exposure.** The field mappings above, and whether each
   harness can hand a specific tool to a specific agent, come from documentation read
   on one day, and must be checked against the versions actually installed.

## Deferred

- **If opencode cannot render per-clone permissions,** its module declares
  `permissions` as not provided. The existing warning applies: hard stops and the
  guarded store are then enforced only by instruction. The installer never falls back
  to editing a tracked configuration file. The owner decides at `verify-opencode`
  whether that weaker mode is acceptable.
- **Approving this specification does not verify the formats.** The Claude and
  opencode paths and fields stay "to verify" against the installed versions;
  `claude-harness` and `verify-opencode` check them.
- Field names and formats remain proposals.

## Acceptance criteria

- A neutral skill, agent and command installed for Claude and for opencode each appear
  at the harness's own path, and none appears in `git ls-files`.
- Attaching the same module set to two clones with different harnesses yields a
  byte-identical committed tree.
- An agent item that declares a restriction a harness cannot express is not installed
  there, and the installer says why.
- An item that needs a capability the harness lacks is skipped with a warning.
- A neutral rule list that contains an `allow` entry is rejected.
- After attach, the rendered local settings deny writes to the guarded store and deny
  the command that records an approval, for a harness that provides `permissions`.
- A hook appears only if the module ships it under `harness/<name>/`, and it is listed
  at approval.
- The Claude root file contains the pointer and the generated Compact Instructions
  section, and the opencode harness writes none.
- A generated file edited after attach is reported by the check.
