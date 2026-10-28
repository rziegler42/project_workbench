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
| `root` | The root instruction file: its name and how it is built, or `none`. The file and the file it imports are each a plain Markdown name (letters, digits, `-` and `_`, ending `.md`), so the file the installer writes is an instruction file and not a script or configuration file of some other tool. |
| `kinds` | For each of `skill`, `agent`, `command`: the directory, the file layout, and the field mapping from the neutral front matter. A kind the harness lacks is absent. |
| `local_settings` | The per-clone file that receives rendered permission rules and hooks, or `none`. Its `path` is a safe path of exactly two segments (not git metadata, not under `.workbench`, not the guarded store): a dot-directory, then a non-blank name ending `.json`; the layout's `exclude` must cover it. The installer cannot know that the harness reads the file, so the owner's approval of the layout is what stops a settings file the tool ignores. |
| `hooks` | Where hooks are declared, or `none`. With `event`, `timeout` and `block_code` and a `targets` table it describes the edit gate's hook; it may also carry `command_gate`, `{tool, field, timeout}`, the Bash hook that the installer renders when a command is set to `ask` or `none` (`command-permissions.md`, "The command gate"); the timeout must exceed the gate's own 10-second deadline. `local_settings` may carry `shared`, the harness's shared project settings file, which the layout does not write; the installer hashes it and denies edits to it while the command gate is rendered. |
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
| agent | `name`, `description`, `tools`, optional `model`, `writes`, `run` | the body is the agent's instructions |

An agent's `tools` is an abstract, restrictive set drawn from `read`, `search`,
`edit`, `shell`, `web` and `agents`. It limits what the agent has; it grants no
permission. An item may also declare `needs`, a list of capabilities it cannot work
without.

**A confined agent.** An agent may declare two more fields that narrow `edit` and `shell` to a scratch area and to pinned
commands. They are data; the installer enforces them ("The agent gate", below), and no module supplies the enforcement.
Each is one `key: value` line, like every field here, and a list is comma-separated like `tools`:

```
tools: read, search, edit, shell
writes: scratch
run: python3 {scratch}/check.py, python3 {scratch}/check.py --fast
```

- `writes` lists the named roots the agent may write under. Only `scratch` is defined: the session's scratch directory,
  whole, with no sub-pattern. An agent with `writes` may write nowhere else.
- `run` lists pinned command patterns, at most 4, each at most 200 characters; the whole line is at most 600. A pattern is
  space-separated tokens. A token is a literal, or `{scratch}/<name>` where `<name>` is one plain file name (letters, digits,
  `.`, `-`, `_`; not starting with `.` or `-`). No pattern holds a comma, a quote, `;`, `&`, `|`, `$`, a backtick, a
  parenthesis, `<`, `>`, a backslash, a newline or a tab; a literal token uses letters, digits and `. / _ - : = + @ %`
  only. An agent with `run` may run those commands and no others.
- Refused when the item is read, as `tools` is today: a repeated field, an empty or duplicate entry, an unknown root, a
  pattern outside this grammar, a line over its limit, `writes` without `edit` in `tools`, `run` without `shell`, and either
  field together with the `agents` tool. The last holds because an agent it started would not be covered by this agent's
  hook. A confined agent also holds no tool beyond `read`, `search`, `edit`, `shell` and `web`.
- An agent with either field is installed only where the harness's layout describes a per-agent hook and a scratch directory
  ("The agent gate") and the harness provides `permissions`, which carry the deny for the agent's file. On any other harness it
  is skipped with a warning and never installed unconfined, which is the fail-closed rule under "Translation". It is also
  skipped where a module gives its own file for the agent in `harness/<harness>/agents/` (the file would replace the one that
  carries the hook), and where the harness name or the agent name is not one the guard's command takes.

## Translation

The installer translates each neutral item into the attached harness's format using
the harness module's layout.

- An item whose `needs` the harness does not provide is skipped with a warning.
- A field the harness cannot express is dropped with a warning when dropping it only
  loses convenience.
- **An item that declares a restriction the harness cannot express is skipped with a
  warning and never installed unrestricted.** A read-only reviewer that cannot be made
  read-only on a harness is not installed there. This fails closed. A confined agent
  (`writes` or `run`) is such an item on a harness without a per-agent hook.
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

The hooks the installer itself renders are the edit gate, for a harness whose layout carries a `hooks` key
("The edit gate hook", built), and the agent gate, one per confined agent, for a harness whose layout describes a per-agent
hook ("The agent gate", built). Neither is a module's file or listed
under `ships`.

## Root files and instructions

- Every harness reads `AGENTS.md` for project policy, directly or through its root
  file.
- Root files are per-clone, uncommitted and regenerated at attach.
- A root file never carries project guidance of its own beyond what is generated from
  neutral policy. Claude-specific guidance goes in a module's `harness/claude/`
  override.

## The Claude harness module

Built as the first-party module `claude` in `packages/workbench/`, declared as data (`layout`
in `module.json`) and rendered by the installer. It provides six capabilities:
`instructions`, `skills`, `agents`, `commands`, `hooks` and `permissions`. Its layout describes the installer's own
gate hook ("The edit gate hook") and no module's hook. Layout, verified against
Claude Code 2.1.305 (see "Evidence" below):

| kind or file | path |
|---|---|
| root file | `CLAUDE.md`: an `@AGENTS.md` pointer only. The preservation guidance for a compaction is a bullet of the `code-work` policy block, which Claude loads through the pointer; Claude's documentation names no "Compact Instructions" section, so none is generated (`code-work.md`, "Context across increments") |
| skill | `.claude/skills/<name>/SKILL.md`; bundled files beside it |
| agent | `.claude/agents/<name>.md` (`name`, `description`, `tools` as an allowlist, optional `model`) |
| command | `.claude/commands/<name>.md` (`description`, `argument-hint`; `$ARGUMENTS`) |
| local permissions and hooks | `.claude/settings.local.json`, which Claude merges over the committed settings and which holds `permissions` and `hooks` |

- For a confined agent ("The agent gate"), the `agent` kind also carries `hook` and `scratch` entries: the key in the
  agent's front matter that holds hooks, the event, the timeout, the block code, and the template of the session's scratch
  directory. The Claude module declares `hooks` (`PreToolUse`, timeout 20, block code 2), the matcher `Bash|Edit|Write` taken
  from the tool names its layout gives `shell` and `edit`, and the scratch template
  `/private/tmp/claude-{uid}/{cwd_key}/{session_id}/scratchpad`, where `{cwd_key}` is the working directory with every `/` and
  `.` replaced by `-`. The template is observed in one version on one machine ("Hooks in an agent's frontmatter") and is
  checked by the guard against the hook input; where a part is missing the guard refuses.
- A hook that re-injects text after a compaction (a `SessionStart` hook with the `compact` matcher) ships only as
  a `harness/claude/` override. None is built.
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

Hook facts, read from `code.claude.com/docs/en/hooks`, `hooks-guide`, `tools-reference` and `permissions` on
2026-10-22 (the pages show no version; the installed version is 2.1.305 as above, and the hook behaviour is
not yet tested on it). The use built on them is in "The edit gate hook". The owner's live check of the hook (criterion
9 of plan `2026-10-22-checkpoint-settings-and-caps`) was made on 2026-10-22 on Claude Code 2.1.307: exit 2 from the hook
blocked `Write`, `Edit` and `NotebookEdit`; `notebook_path` is the key `NotebookEdit` receives; a hook started from a
subdirectory ran and found the project; and a `Write` was allowed once the plan was approved. Still not verified:
`MultiEdit`, `CLAUDE_PROJECT_DIR`, the hook's `PATH` when Claude is not started from a shell that has the launcher on
it, and project against local settings precedence.

- **Input.** A `PreToolUse` hook gets one JSON object on standard input with `session_id`, `transcript_path`,
  `cwd`, `permission_mode`, `hook_event_name`, `tool_name`, `tool_input` and `tool_use_id`. For the file tools
  "`tool_input.file_path` is always absolute" and `~` and relative paths are expanded before the hook runs.
- **Editing tools.** `Edit` and `Write` take `file_path`; neither targets several files. `NotebookEdit` exists;
  the permissions page names `notebook_path` as its path field and the hooks page gives no schema for it.
  `MultiEdit` is not in the current tools reference. An `Edit(...)` permission rule covers `Edit`, `Write` and
  `NotebookEdit`.
- **Exit codes.** 0 is success (stdout JSON is parsed); 2 is a blocking error and "your stderr is the reason";
  any other non-zero code is a non-blocking error and "the action goes ahead". Exit 2 overrides a JSON `allow`.
  A JSON `permissionDecision` of `deny` on exit 0 also denies; the gate uses exit 2 only.
- **Matcher.** A value of letters, digits, `_`, `-`, spaces, `,` and `|` is an exact name or a list of exact names
  (`Edit|Write`); anything else is an unanchored JavaScript regular expression; matching is case-sensitive.
- **Registration.** `{"hooks": {"PreToolUse": [{"matcher": ..., "hooks": [{"type": "command", "command": ...,
  "timeout": <seconds>}]}]}}` in a settings file; user, project, local and managed files are read and "hook
  entries merge across settings levels". Precedence between project and local files is not verified.
- **Timeout.** `timeout` is in seconds, default 600 for a command hook; on expiry the hook is cancelled, its output
  is discarded and the call is not blocked, unless `"onFailure": "block"` is set.
- **Execution.** A command string runs through `sh -c` on macOS and Linux, in the session's current directory.
  `${CLAUDE_PROJECT_DIR}` is the project root where the session started.
- **Not verified, and not relied on:** that `notebook_path` is the key a `NotebookEdit` hook receives; that
  `MultiEdit` exists; whether `CLAUDE_PROJECT_DIR` is exported to a plain command hook; the `PATH` the hook's
  shell sees (so whether `wb` is found); and hooks through a symlinked path. The last 73,000 characters of the
  hooks page were searched for terms and not read in full.

### Global against project settings (Claude Code 2.1.310, 2026-10-24)

What happens when the owner's user-level configuration (`~/.claude`) differs from the project's. Method: `claude -p` runs in a
throwaway workbench project (122 `deny` and 58 `ask` rules rendered by this harness module), with the user level replaced by a
throwaway configuration directory chosen with `CLAUDE_CONFIG_DIR` and made deliberately noisy: `allow: Bash(*)`, a `PreToolUse`
hook on Bash that appended a line to a log, a skill and an agent each named like one of the project's with a marker in its text,
and an instruction file saying every push is pre-approved and every reply begins with a marker word. The model chose how to
carry out each request; the permission results are read from the run's `permission_denials`. One or two runs each.

- **A project `deny` held** against the global `allow`, and held with the global default mode `auto`: the command was denied and
  did not run.
- **A project `ask` held** against the global `allow`, with `auto`, and with `bypassPermissions`: the command did not run. In
  `-p` mode an `ask` is denied and not prompted; an interactive session was established later (the next section but one).
- **A global hook ran** for commands the project denied and for commands it asked on, so a project cannot switch one off.
- **A global skill replaced a project skill of the same name** (two runs). The skill that loaded was the global one.
- **A project agent replaced a global agent of the same name** (one run).
- **A hook declared in a project agent's frontmatter ran, and blocked.** A `Read` hook logged a line; a hook that exited 2
  refused the agent's `Read` and the agent reported the hook's message (one run each, the `Read` tool only).
- **Both instruction files were loaded.** Asked whether a push needed approval, the model treated a global "pre-approved"
  grant as satisfying the project's "explicit approval" only when asked to push, and said the files do not say which wins.
  With `CLAUDE_CONFIG_DIR` set, the owner's real user-level instruction file was loaded as well as the throwaway one (cause not
  established); the real user-level settings file was not (a control command that the real settings ask on ran).
- **Not tested:** a project `deny` under global `bypassPermissions` (the harness's classifier refused the call and it was not
  retried), interactive mode against `-p`, the edit-gate hook (the project had no process module), project against local
  settings precedence, and any agent tool other than `Read`.

The decisions `2026-10-24-project-guarantees-a-floor`, `2026-10-24-declared-agent-confinement` and
`2026-10-24-installer-reads-global-settings-on-request` (all `Proposed`) rest on these results.

### Hooks in an agent's frontmatter (Claude Code 2.1.310, 2026-10-24)

Recorded by increment A of plan `2026-10-24-agent-confinement`. Method: `claude -p` with a small model, run with the owner's real
user configuration, in a throwaway folder. One project agent with `tools: Bash, Write, Edit, Read` declared a `PreToolUse` hook
in its frontmatter on those four tools. The hook wrote its whole input to a log and exited 2 when a marker file existed, and 0
otherwise. One run each, so each result is a single observation.

- **The hook ran, and exit 2 blocked, for `Bash`, `Write`, `Edit` and `Read`** when the session itself was the agent
  (`--agent`): the command did not run, the file was not written or changed, and the call appeared in `permission_denials`. For
  an agent the model started as a subagent, the hook ran and blocked `Bash`, `Write` and `Read`; `Edit` was not attempted because
  the `Read` before it was blocked.
- **A folder that is not trusted skips the hooks and runs the agent anyway.** In four runs in a folder outside any trusted
  project, no hook ran and the agent ran its command, write and edit unconfined. The debug log said: "Skipping frontmatter hooks
  for main-thread agent ... the folder its definition file came from is not trusted (source: projectSettings)". Nothing in the
  run's output (`permission_denials` empty, exit 0) showed it. **A confinement built on this hook therefore fails open when the
  folder is untrusted.** A folder below a trusted project was trusted (one run). Whether an interactive session prompts for
  trust, and whether the skipped hook is announced, was not tested.
- **The hook input** held `session_id`, `transcript_path`, `cwd`, `prompt_id`, `permission_mode`, `agent_type` (the agent's
  name), `effort`, `hook_event_name`, `tool_name`, `tool_input` and `tool_use_id`; a subagent's input also held `agent_id`.
  `tool_input` was `command` and `description` for `Bash`, `file_path` and `content` for `Write`, `file_path` for `Read`, and
  `file_path`, `old_string`, `new_string` and `replace_all` for `Edit`.
- **The hook's environment** held `CLAUDE_PROJECT_DIR`, `CLAUDE_CODE_AGENT` (the agent's name) and `CLAUDE_CODE_SESSION_ID`. Its
  `TMPDIR` was a per-user folder under `/var/folders/`, which is not where the session's scratch area is.
- **The session's scratch area is not under `TMPDIR`.** In the folder `/private/tmp/claude-<uid>/`, a session had a directory
  named from its working directory (every `/` and `.` replaced by `-`) and, inside it, a directory named by its session id.
  `claude -p` created that directory with a `tasks` entry and no `scratchpad`; interactive sessions of other projects had a
  `scratchpad` directory in the same place. The form is observed, not documented, and was not tested for other characters in the
  working directory, long names, Linux, or what creates the `scratchpad` directory.
- **Not tested:** interactive mode; a hook timeout; `MultiEdit` and `NotebookEdit` in an agent's hook; an agent's hook against
  a session-level hook of the same tool; and a hook in a project that is trusted by its parent but whose agent file is edited.

### An `ask` prompt answered from the remote channel (Claude Code 2.1.310, 2026-10-26)

Recorded by increment A of plan `2026-10-26-command-permission-levels`. Method, run by the owner and reported by the owner: an
interactive `claude --remote-control ask-trial` session in a throwaway git folder (`/tmp/ask-trial`) whose only project setting
was `permissions.ask: ["Bash(echo ask-trial*)"]`. The harness was not attached by the workbench; the rule was written by hand,
so this shows the harness's behavior and not the workbench's rendering. The prompt text named auto mode. Requests were typed from
the remote connection; the owner reported tapping Yes or No on the remote side only, for every prompt. The
workbench repository head was `1a731fa`. One run of each case, so each result is a single observation.

- **The `ask` rule beat auto mode.** The terminal prompt said "Ask rule Bash(echo ask-trial*) overrides auto mode for this
  command" and offered "1. Yes, 2. No".
- **The prompt reached the remote side** for a request typed there. The terminal showed the same prompt while it was pending.
- **Yes was reported to have run the command** (`echo ask-trial-1` printed). The owner reported tapping on the remote side
  only, so this Yes was given there.
- **A repeated Yes ran the command** (reported by the owner: the prompt appeared, the owner accepted it, and it "ran fine").
  The owner later reported tapping on the remote side only. The command text, its output, and whether the terminal prompt
  closed on its own were not reported. An earlier attempt of this repeat was made from the wrong directory and prompted nothing; it is not an
  observation of this session.
- **No answered on the remote side refused the command.** The session said it did not run the command because it was denied,
  and the terminal prompt closed without a keypress there.
- **No `PermissionRequest` hook was found** by `grep -rn PermissionRequest ~/.claude/settings.json ~/.claude/plugins` (no output),
  so whether the owner's global hook fires on an `ask` prompt was not tested. Hooks elsewhere were not searched.
- **A first rule, `Bash(echo ask-trial:*)`, did not prompt** for `echo ask-trial-1`: the command ran with no prompt noticed. The
  likely cause is that the `:*` form matches whole words; that cause was not confirmed.
- **Not tested:** answering at the terminal first, a
  prompt with the remote channel closed or unattended, a rule rendered by the workbench's attach, and any command other than
  `echo`.

### A Bash hook with an exit code and an `ask` rule (Claude Code 2.1.311, 2026-10-26)

Recorded by increment I of plan `2026-10-26-command-permission-levels`. Method, run by the owner and reported by the owner: a
throwaway git folder (`/tmp/gate-trial`) whose local settings held a `PreToolUse` hook for the `Bash` tool, `python3
/tmp/gate-trial/hook.py || exit 2`, and the rule `ask: ["Bash(echo probeword-ok)"]`. The script appended each command it
received to a log and exited 2 when the command contained the word `probeword`, unless it was exactly `echo probeword-ok`; it
exited 0 otherwise. Repository head `174d62f`. The prompt told the agent that the owner was testing a hook on purpose, so that it
would run the command it was given. One run of each case, so each result is a single observation.

- **A hook that exits 0 leaves the `ask` rule in force.** `echo probeword-ok` was allowed by the hook and still prompted, in auto
  mode ("Ask rule Bash(echo probeword-ok) overrides auto mode for this command") and in default mode ("Permission rule
  Bash(echo probeword-ok) requires confirmation").
- **A hook that exits 2 stopped the command before it ran, with no prompt, in auto mode and in default mode.** In auto mode:
  `sh -c 'echo probeword'`, `bash -c 'echo probeword'` and `env echo probeword`. In default mode: `bash -c 'echo probeword'`. The
  agent saw the hook's own message ("PreToolUse:Bash hook error: [python3 /tmp/gate-trial/hook.py || exit 2]: blocked by the
  trial hook: ..."). The submitted text of the default-mode command held a newline from the terminal's line wrap, and it was
  blocked all the same.
- **A word the hook could not see got through.** `echo probe""word` (the shell joins it to `probeword`) was allowed by the hook,
  ran and printed `probeword`, with no prompt, in auto mode. This is the case a text match cannot stop.
- **A command with no word ran** (`echo hello`, auto mode), with no prompt.
- **The log held eight entries for the eight runs reported**, so every command the agent ran reached the hook; the entries
  were read afterwards by the agent and not compared run by run with the owner's sessions.
- **Earlier runs with a broken script.** A first attempt had a stray leading space in `hook.py`, so the script failed with
  `IndentationError` on every call; with `|| exit 2` every Bash command, `echo hello` included, was blocked. The owner did not
  confirm the mode of those runs, so they are not counted as auto-mode evidence, and the missing-script case of the plan was not
  run (a crash that `|| exit 2` turns into 2 is a nearby observation, not exit 127). The owner then rewrote the script and
  pasted its compile and its two exit codes (0 for `echo hello`, 2 for a command with the word), checked by hand, before the
  runs above.
- **Not tested:** default mode got two of the six cases (`echo probeword-ok` and `bash -c`); `sh -c`, `env echo probeword`,
  `echo probe""word` and `echo hello` were not run in default mode. A hook script that is missing or a `wb` that is not on
  `PATH` (exit 127). A hook that answers with JSON (`permissionDecision`) and not an exit code. The hook rendered by the
  workbench, and `wb gate-command`. A subagent's Bash call. A hook in a project that is not trusted. The rendered wildcard
  rule `Bash(wb approve-plan *)` after a hook allows (the trial's rule was the exact string `Bash(echo probeword-ok)`). Any
  command other than `echo` and the three wrappers; `wb` was not used.

### As built, and its limits

Recorded by `claude-harness` (`docs/plans/2026-10-20-claude-harness.md`), each limit found in
review or in the security pass:

- **An existing `.claude/settings.local.json` is a conflict.** Attach creates the file
  exclusively. If another file is there, attach refuses it and prints the entries to add by
  hand. There is no merge, and the owner's `allow` rules are never read or written.
- **Attach is idempotent.** A path that already holds exactly the planned bytes is kept; a
  different one is a conflict. The local manifest, `.workbench/local/harness.json`, is written
  last, so a part-written attach has none and can be rerun. It is scratch and grants no
  authority, except that `wb rerender` trusts its hashes to tell an edited rendered file from a stale one
  ([`harness-refresh.md`](harness-refresh.md)); the rendered permissions deny the harness's write tool on it and
  nothing stops a write by the shell.
- **`install` attaches as its last step,** after its own unfinished-write marker is removed. If
  attach fails, the install is complete, `install` prints `failed:` and names `wb attach`, and
  exits 3.
- **The deny list** covers the guarded store and every owner-run command (`install`, `adopt`, `upgrade`,
  `add`, `attach`, `acknowledge`, `recover`, `approve`, `pin`, `release-approvals`) in five
  spellings: `wb` and the four interpreter forms of `-m workbench` (`rules.SPELLINGS`). `wb preview` is not denied. A Bash deny is not a security
  boundary; see "Verified rendering rules".
- **The rendered rules deny edits to `.claude/settings.local.json` and `.git/info/exclude` only
  together with the edit gate hook** ("The edit gate hook"). Without a hook, Claude prompts for an
  edit, but an agent that has been allowed edits could change its own deny rules. The deny of the local manifest
  (`.workbench/local/harness.json`) is rendered with or without the hook (plan `2026-10-28-protect-local-manifest`).
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

### The edit gate hook

*(Built by plan `2026-10-22-checkpoint-settings-and-caps`. The decision that the installer owns the gate is
`docs/decisions/2026-10-22-installer-owns-the-edit-gate.md`, accepted.)*

The installer, not a module, renders one hook into the same per-clone file as the permission rules, under the
layout's `hooks` key. The layout's `hooks` object carries `settings_key`, `targets`, `event`, `timeout` and
`block_code`; the last three come together or not at all, and a layout with `hooks: none` or without them describes no
hook. The rendered entry is fixed by the layout and not chosen by any module. The matcher is the tool names of
`targets`, sorted and joined with `|`; it is derived and not stored. For the Claude module:

```json
{"hooks": {"PreToolUse": [{"matcher": "Edit|MultiEdit|NotebookEdit|Write",
  "hooks": [{"type": "command", "command": "wb gate claude || exit 2", "timeout": 20}]}]}}
```

- **When it is rendered.** All three must hold: the harness module provides `hooks`; its layout describes a whole
  hook; and an installed process module declares `approval.active`. Otherwise no hook is rendered. If a process
  module with `approval.active` is installed and no hook can be rendered, attach warns that a plan under way is
  not stopped from edits except by instruction. A module that provides `hooks` with a layout that does not describe
  one is refused at attach; one that provides `hooks` without `permissions` gets a warning, because the hook is
  written into the permissions file. A skill or other item that `needs: hooks` is never installed, because a hook
  has no neutral form.
- **Why `|| exit 2`.** Claude treats exit 2 as the only blocking code, so a `wb` that is missing from `PATH` (exit
  127) or a gate that fails for any reason would let the call through. The shell's `||` turns every non-zero exit
  into 2. The harness name is checked against `[a-z0-9][a-z0-9_-]{0,63}` before it is put in the command. A hook
  whose command cannot start in the shell at all is not covered. The live check started Claude from a shell that had the
  launcher directory on `PATH`; whether a hook finds `wb` otherwise is not verified, and if it does not, every edit is
  blocked.
- **Why `timeout: 20`.** A timed-out command hook does not block the call. The gate stops itself after 10
  seconds and refuses, and the harness's limit is set above that. `onFailure: "block"` exists in the current
  documentation and is not rendered, because it is unverified on the installed version.
- **The target table** lives in the layout, under `hooks.targets`, and the gate reads it and holds no tool name
  (closed; anything else is a refusal). For the Claude module: `Edit` and `Write` read `tool_input.file_path`,
  `MultiEdit` reads `tool_input.file_path` and `NotebookEdit` reads `tool_input.notebook_path`. The first two are
  verified in the documentation; `notebook_path` is documented for permission rules only and `MultiEdit` is not in
  the current documentation (see "Evidence"), so both are unverified and the gate refuses a call whose field is
  missing. No documented tool names several files.
- **The command gate** is a second hook in the same event, for the layout's `command_gate.tool` (for Claude, `Bash`), rendered only
  when a command is set to `ask` or `none` and the harness provides `hooks`: `wb gate-command <harness> || exit <block_code>`
  with the layout's time limit. It is specified in `command-permissions.md`; its trials are "A Bash hook with an exit code and an `ask`
  rule" and the repeated spelling probe in the plan `2026-10-26-command-permission-levels`. With either hook the deny below also
  covers the shared settings file.
- **The deny.** With a hook, the rendered deny list also covers edits to `.claude/settings.local.json` and
  `.git/info/exclude`, each spelled from the project root and with a `**/` prefix (the owner edits both by hand),
  so an agent cannot delete the hook, and also by the real path of the project (`Edit(//<root>/.claude/settings.local.json)`
  and `Edit(//<root>/.git/info/exclude)`), because the relative patterns do not resolve from a subdirectory (see "As
  built, and its limits" below). A project path that is not plain and absolute, or holds a character outside the allowed
  set (a quote, brackets, `*`, a backslash, a colon, non-ASCII), refuses the attach; a space is allowed. It is one
  function in the renderer and rendered only with a hook, so it can be dropped alone.
- **As built, and its limits.** The gate is in `trust-and-approval.md`, "Checkpoint and cap settings, and the edit
  gate". **The relative `Edit(...)` deny did not hold from a subdirectory** (live check, 2026-10-22): the patterns are matched
  from the directory Claude started in, so a session started below the root and aimed at
  `../.claude/settings.local.json` was stopped only by the auto mode classifier. Plan
  `2026-10-22-absolute-settings-deny` adds the absolute patterns. The owner's recheck on 2026-10-23 (Claude Code 2.1.309)
  started Claude in a subdirectory of a new project and aimed an `Edit` at `../.claude/settings.local.json`: it was
  refused with "File is in a directory that is denied by your permission settings", in auto mode and again in manual
  mode. Limits that remain: a project that is
  moved keeps stale absolute rules; a clone that already holds a rendered settings file is not migrated (attach treats a
  different file as a conflict); the hook, and so the gate, runs only while a plan is under way, so nothing but the deny
  guards the file at other times; the deny covers the agent's file tools and not a shell.
  Project and local settings precedence, `PATH` for `wb`, and `CLAUDE_PROJECT_DIR` are as listed under "Evidence".

### The agent gate

*(As built by plan `2026-10-24-agent-confinement`: the guard `wb agent-gate` (increment D), the hook, the deny and the note
rendered by attach (increment E), and the end-to-end test (increment F). The decision is
`docs/decisions/2026-10-24-declared-agent-confinement.md`, accepted. Built against the evidence under "Hooks in an agent's
frontmatter".)*

**What was verified, and what was not.** Verified by test, on a synthetic harness and module and with no installed first-party
module: the reading and validation of the fields; each refusal of the guard; the rendered hook, deny and note; the report of
`check`; and the whole path from the declaration through attach to the command in the agent's own file, run through a shell with
the hook input on standard input and the exit code read back, with `wb` a stub that calls the installer with the test's store
and distribution, a permitted and a hostile input each, and a missing `wb`. Verified once live: the trial under "Hooks in an
agent's frontmatter" (Claude Code 2.1.310, `claude -p`). Not verified: the rendered hook against a live harness (no first-party
module ships a confined agent yet, and the real Claude layout is untested for the matcher); an interactive session in a folder
the harness does not trust, which only the owner can run; the case-insensitive filesystem and a different `wb` on `PATH`
(see the limits below).

For a confined agent ("Neutral items") the installer renders a hook into the agent's own file, under the key the layout names,
and not into the settings file. The hook therefore applies to that agent only. Its command is fixed by the layout and not chosen
by any module:

```
wb agent-gate claude <agent> || exit 2
```

with the matcher the layout derives from the tool names it gives `shell` and `edit` (`Bash|Edit|Write`), the event, the timeout
and the block code of the layout. The harness name and the agent name are each checked against `[a-z0-9][a-z0-9_-]{0,63}`
before they are put in the command. `|| exit 2` has the same reason as for the edit gate: any non-zero exit, including a missing
`wb`, becomes the one blocking code.

**What the guard reads.** `wb agent-gate` is a command that is safe for the agent to run, like `gate`. It reads the declared
limits from the installed module's verified neutral item for `<agent>`, found through the same lookup the edit gate uses for its
process module, and never from the rendered agent file, which the agent's own tools could edit. An agent name that no installed
module declares as confined is refused. It reads the layout's scratch template and fills it from the hook input (`session_id`,
`cwd`) and the process (the user id).

**Input and deadline.** The hook input is JSON on standard input, read up to a fixed size; an input that is too large, not an
object, or missing `tool_name`, `tool_input` or `session_id` is refused. The guard stops itself after 10 seconds and refuses; the
harness timeout is set above that, because a timed-out command hook does not block.

**Order of checks, for every call.** The first refusal ends it; the guard allows only after every check passes, and exits with the
block code on anything else, including any error it did not foresee.
1. The tool name is one the layout gives `edit` or `shell`, and the agent holds that capability by its `writes` or `run`. Any
   other tool name is refused.
2. For an edit tool, the path in `tool_input.file_path` must be a non-empty absolute string without a control character. It is
   resolved part by part with no link followed in a part that exists, and a part that does not exist yet is placed against the
   scratch directory and is not counted as outside it. The result must lie under the scratch directory, compared in the
   filesystem's own case rules; `..`, a link on the way, a different case that names another directory, and any error while
   examining a part are each a refusal and never "outside". A path that is the scratch directory itself is refused.
3. For the shell tool, `tool_input.command` must be a string of at most 1,000 characters. Any character outside a closed safe set
   (letters, digits, `. / _ - : = + @ %` and single spaces) is refused, so no quote, `;`, `&`, `|`, `$`, backtick, parenthesis,
   redirection, newline, tab or backslash reaches a shell. The command is split on single spaces (an empty token is refused) and
   compared token by token with each pinned pattern; the token counts must be equal and every literal token equal. A
   `{scratch}/<name>` token must name `<name>` directly inside the scratch directory, with no `..` and no link, by the path rules
   of step 2. A token that starts with `-` and is not spelled in the pattern is refused, and an argument that is not in the
   pattern is refused; the pattern is the only list of what may follow.
4. A pattern that matches allows the call; nothing else does. The command is not run, expanded or parsed by a shell by the
   guard.

**Layout entries and rendering.** The layout's `agent` kind carries the `hook` and `scratch` entries ("The Claude harness
module"). Attach renders the hook for each confined agent whose harness describes both, and skips the agent with a warning where
it does not. The hook is written after the agent's other front-matter lines, in the shape the trial in "Hooks in an agent's
frontmatter" ran:

```
hooks:
  PreToolUse:
    - matcher: "Bash|Edit|Write"
      hooks:
        - type: command
          command: "wb agent-gate claude <agent> || exit 2"
          timeout: 20
```

The key, the event, the timeout and the block code are the layout's. The matcher is every tool name the layout gives `edit` and
`shell`, the same table that builds the agent's `tools` line, so a tool the agent is granted for either is a tool the hook sees.
A file the module gives for the harness in `harness/<harness>/agents/` does not replace a confined agent's file: the agent is
skipped. The existing edit deny, which already covers `.claude/settings.local.json` and `.git/info/exclude`, also covers each
rendered confined-agent file, from the directory the session starts in, from any directory below it, and by absolute path in
the project, so the agent's file tools cannot remove the hook; it is rendered with or without the edit gate's hook, and as for
the settings file the deny covers file tools and not a shell. `wb check` reports a confined agent's file edited after attach as
it does any generated file. Attach prints a note for each confined agent it renders, stating the trusted-folder limit below.

**Limits, stated.**
- **A script the agent writes and then runs is not confined.** A pinned command such as `python3 {scratch}/check.py` runs a file
  the agent wrote into scratch, and that file can do whatever the user can do. The guard decides which command starts; it
  cannot decide what the started program does. A module that ships a confined agent accepts this and states it at approval. The
  scratch directory is per session and not per agent, so a script written by one confined agent can be started by another
  agent's, or the main session's, pinned command. A pinned command that changes the working directory (`cd`) is also unsafe: the
  guard refuses a project root or working directory inside the part of the scratch template before its first placeholder, but
  cannot judge what a pinned command does.
- **The guard runs only where Claude trusts the folder.** Claude skips an agent's frontmatter hooks in a folder it does not trust
  and runs the agent anyway, with nothing in the run's output ("Hooks in an agent's frontmatter"). In such a folder the agent's
  `edit` and `shell` tools are unconfined, whatever it declares. The owner accepted this on 2026-10-24 as a stated limit. The
  guarantee is: enforced in a trusted folder. Whether an interactive session in an untrusted folder runs the agent at all was
  not tested; if it does, the same limit applies. Reading the folder's trust flag from the owner's global configuration
  (`global-settings-check`) and a dedicated tool that fails closed are not built.
- **Verified once.** Each live result is one run of Claude Code 2.1.310. The scratch template is observed, not documented. A
  later Claude Code version can change either, and a version that no longer matches makes the guard refuse, not allow. The
  scratch name is derived from the working directory by turning every character that is not a letter or a digit into `-` (observed for `/`, `.` and `_`; assumed for the rest), and a
  working directory with a non-ASCII character makes the guard refuse every call.
- **The deny matches the file's name as spelled, and the hook command finds `wb` through `PATH`.** On a case-insensitive
  filesystem a write by another agent or the main session to the same file under another case may not match the deny, and a
  different `wb` earlier on `PATH` would be the one the hook runs. Both hold equally for the edit gate's settings file and hook.
  Neither was tested; the confined agent's own writes are limited by its hook in a trusted folder either way.
- **Claude Code only.** opencode and Codex have no per-agent hook in their layouts; a confined agent is not installed there.

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
   specific agent (`researcher-fetch-tool`). The read-only reviewer of `code-work` needs no tool handed to it,
   only an allowlist, which the Claude layout renders.

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
- The Claude root file contains the pointer only. The opencode harness writes no
  root file.
- A generated file edited after attach is reported by the check.
- An agent with `writes` or `run` is read and validated: an unknown root, a pattern outside the grammar, a duplicate, an
  over-long line, a field without its tool, or the `agents` tool alongside either field is refused at read; on a harness without
  a per-agent hook it is skipped with a warning and never installed.
- `wb agent-gate` allows a write under the scratch directory and a command that matches a pinned pattern, and refuses a write
  elsewhere, through a link, with `..`, or in another case; a command with a metacharacter, an extra token, an unspelled option
  or a placeholder outside scratch; a missing path part counted as outside, and any error while examining a path; an input of
  the wrong shape, too large, or past the deadline; and an agent name the installed module does not declare.
- The rendered file of a confined agent carries the hook, the rendered deny covers that file, `wb check` reports it edited,
  and attach prints the trusted-folder note.
- A test module with a confined agent goes from declaration to a refused call through attach and the guard, with the hook's
  command run as the harness runs it.
