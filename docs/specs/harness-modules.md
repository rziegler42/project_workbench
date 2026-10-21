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
| `local_settings` | The per-clone file that receives rendered permission rules and hooks, or `none`. Its `path` is a safe path of exactly two segments (not git metadata, not under `.workbench`, not the guarded store): a dot-directory, then a non-blank name ending `.json`; the layout's `exclude` must cover it. The installer cannot know that the harness reads the file, so the owner's approval of the layout is what stops a settings file the tool ignores. |
| `hooks` | Where hooks are declared, or `none`. |
| `exclude` | The paths to add to `.git/info/exclude` at attach. |
| `tolerated` | Literal paths, each inside a directory the layout writes into, that the harness or the owner may keep there; `wb check` does not warn about them. Optional, at most 16. |
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

Built as the first-party module `claude` in `packages/workbench/`, declared as data (`layout`
in `module.json`) and rendered by the installer. It provides five capabilities:
`instructions`, `skills`, `agents`, `commands` and `permissions`. It declares `hooks: none`;
the sixth, `hooks`, is added when `code-work-module` ships a hook. Layout, verified against
Claude Code 2.1.305 (see "Evidence" below):

| kind or file | path |
|---|---|
| root file | `CLAUDE.md`: an `@AGENTS.md` pointer only. The generated "Compact Instructions" section is added once a module supplies the neutral preservation guidance (`code-work-module`) |
| skill | `.claude/skills/<name>/SKILL.md`; bundled files beside it |
| agent | `.claude/agents/<name>.md` (`name`, `description`, `tools` as an allowlist, optional `model`) |
| command | `.claude/commands/<name>.md` (`description`, `argument-hint`; `$ARGUMENTS`) |
| local permissions and hooks | `.claude/settings.local.json`, which Claude merges over the committed settings and which holds `permissions` and `hooks` |

- A hook that re-injects text after a compaction ships only as a `harness/claude/`
  override.
- Excluded from git by `.git/info/exclude`: the root file and everything under
  `.claude/`. Claude does not ignore a settings file that was created by hand; it adds
  its own ignore entry to the user's global git excludes only the first time it writes
  the file itself. The workbench therefore always writes the exclude line.

### Verified rendering rules

- **Path rules use `Edit(...)`, never `Write(...)`.** A `Write(path)` rule is accepted
  and never consulted. An `Edit(path)` deny covers every built-in file-editing tool.
- **An absolute path is written `//absolute/path`, or `~/path` for the home directory.**
  A single leading `/` is relative to the project, so `Edit(/abs/path/**)` matches
  nothing and does not warn. This was checked: a write through the single-slash form
  succeeded, and the `//` form was refused.
- **Bash deny rules** match the command text the agent submits. `Bash(wb install:*)`
  (equivalent to `Bash(wb install *)`) blocked, in a test with a recording stand-in
  for `wb`: the plain command, extra spaces, trailing arguments, a leading `cd x &&`,
  a following `; echo`, a preceding `echo &&`, a leading `VAR=1` assignment, and
  `env wb install`. It did not block, by its own text, `wb` written with a path or
  wrapped in `bash -c`; the session's separate auto-mode classifier refused those two
  in the test, which is not a property of the rule. The documentation states the rule
  is "not a security boundary" and names `/bin/rm`, `bash -c` and `git -C` as forms it
  misses. The workbench renders both the `wb` and the `python3 -m workbench` spellings
  and claims no more than that.
- A `deny` and an `ask` rule are checked before an `allow`, so the owner's `allow`
  rules can never lift a deny.
- Hooks live in the same file under `hooks`. Local settings take effect live.

### Evidence

Claude Code 2.1.305, checked on 2026-10-20. Sources: the official documentation at
`code.claude.com/docs/en/` (settings, permissions, skills, sub-agents, slash-commands,
memory, hooks), fetched that day; and a scratch project with a recording stand-in for
`wb`, driven by `claude -p` with a small model. Not verified, and so not relied on: the
`env` wrapper as a command prefix beyond the single test above, whitespace
normalisation beyond doubled spaces, and loading of an untracked skill, agent or
command (a scratch test showed an untracked skill, agent and command all listed by the
session; the documentation is silent).

### As built, and its limits

Recorded by `claude-harness` (`docs/plans/2026-10-20-claude-harness.md`), each limit found in
review or in the security pass:

- **An existing `.claude/settings.local.json` is a conflict.** Attach creates the file
  exclusively. If another file is there, attach refuses it and prints the entries to add by
  hand. There is no merge, and the owner's `allow` rules are never read or written.
- **Attach is idempotent.** A path that already holds exactly the planned bytes is kept; a
  different one is a conflict. The local manifest, `.workbench/local/harness.json`, is written
  last, so a part-written attach has none and can be rerun. It is scratch and grants no
  authority.
- **`install` attaches as its last step,** after its own unfinished-write marker is removed. If
  attach fails, the install is complete, `install` prints `failed:` and names `wb attach`, and
  exits 3.
- **The deny list** covers the guarded store and every owner-run command (`install`, `upgrade`,
  `add`, `attach`, `acknowledge`, `recover`, `approve`, `pin`, `release-approvals`) in five
  spellings: `wb` and the four interpreter forms of `-m workbench` (`rules.SPELLINGS`). `wb preview` is not denied. A Bash deny is not a security
  boundary; see "Verified rendering rules".
- **The rendered rules do not deny edits to `.claude/settings.local.json` or
  `.git/info/exclude`.** Claude prompts for an edit, but an agent that has been allowed edits
  could change its own deny rules. Adding a rule is a separate decision.
- **`.git/info/exclude` has the lowest precedence of git's ignore sources,** so a committed
  `.gitignore` can re-include a path with `!`. `wb check` reports such a file once it is tracked.
  An exclude file that already holds a later `!` line defeats an exclude line that is present.
- **Files are written in path order,** so agents and commands can exist for a moment before the
  settings file does, until a failed attach is rerun.
- **`wb check` never runs git.** It reads `.git/index` itself (versions 2 to 4, SHA-1 or SHA-256,
  at most 16 MiB and 1,000,000 entries; a split or sparse index is refused), so the repository's
  configuration, hooks and filters cannot run. "Tracked" means in the index, so a staged file
  counts as committed. It scans Markdown only, within 4 MiB, 5,000 documents and 5,000 existing-
  path lookups; passing any of these bounds is itself a problem, so `check` exits 1. The stray
  scan stops at 5,000 entries and depth 8 and reports a problem past that, and it warns about an
  unknown entry directly under a harness directory (not a `tolerated` path, nor a directory that
  holds one).
- **Not detected by `check`:** a link whose case differs from the file on a case-insensitive
  filesystem; a link to a missing ordinary path; a tracked symbolic link's target (a warning
  only). `wb check` knows a harness only from the `layout` of a harness module of a first-party
  package in the running workbench's distribution (`workbench/harnesses.py`); the roots, the
  generated directories and the tolerated paths are derived from that layout. A harness recorded in
  the local manifest that is not known gets one warning and no scan, and a name that two first-party
  packages declare is treated the same way. A harness with no module (opencode, Codex) is not known.
- **Not done by the installer:** it does not inspect skill and command overrides, and attach
  never fetches.
- **Not verified:** case-insensitive filesystem behavior (the development machine cannot create
  the colliding names), and a live `claude` session started in an installed project, which needs
  the owner's allowance.

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
2. **Verifying formats and tool exposure.** The Claude formats were verified on
   2026-10-20 against 2.1.305 (see "Evidence"). Still open: the opencode formats
   (`verify-opencode`), and whether either harness can hand a specific tool to a
   specific agent (`code-work-module`, `researcher-fetch-tool`).

## Deferred

- **If opencode cannot render per-clone permissions,** its module declares
  `permissions` as not provided. The existing warning applies: hard stops and the
  guarded store are then enforced only by instruction. The installer never falls back
  to editing a tracked configuration file. The owner decides at `verify-opencode`
  whether that weaker mode is acceptable.
- **Approving this specification did not verify the formats.** The Claude formats
  are now verified; the opencode paths and fields stay "to verify" against the
  installed version (`verify-opencode`).
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
- The Claude root file contains the pointer, and the generated Compact Instructions
  section once a module supplies the neutral guidance. The opencode harness writes no
  root file.
- A generated file edited after attach is reported by the check.
