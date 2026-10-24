# Agents with declared limits, enforced by the installer

Status: In Progress
Created: 2026-10-24
Candidate: workbench-v1#agent-confinement
Specs: harness-modules

## Goal

Build what the accepted decision `2026-10-24-declared-agent-confinement` describes, so that a module can ship an agent that
writes and runs small scripts in a scratch area and nowhere else, and the installer, not the module, enforces that.

When this plan is done:

- a neutral agent can declare the paths it may write and the commands it may run, as data;
- the Claude harness layout declares where a session's scratch directory is;
- the installer renders a per-agent hook for such an agent, and a generic guard in the installer decides each call from
  the declared limits, refusing on anything it does not understand;
- an agent whose limits a harness cannot enforce is not installed there;
- the specification says what is enforced and states the limit: a script the agent writes and runs is not confined;
- no module ships an elevated agent yet. A test module proves the path from declaration to refusal.

## Scope

- The neutral agent fields, their reader and their validation (`workbench/neutral.py`, `workbench/layout.py`).
- The layout's scratch-directory entry and its per-agent hook entry, for the Claude module.
- The guard command and its tests, in the style of the edit gate (`workbench/gate_hook.py`).
- Rendering the hook into the agent file, and the deny on the rendered agent file (`workbench/harnessplan.py`,
  `workbench/attach.py`, `workbench/check.py`).
- The specification change in `docs/specs/harness-modules.md`, including the evidence of a live trial.

## Non-goals

- Shipping an agent, the `security-review` skill or the `security-review-module` candidate. That is the next candidate and
  waits for this one.
- Confining what a script the agent wrote does when it runs. The decision states this limit; this plan states it in the
  spec.
- opencode and Codex. A harness whose layout has no per-agent hook does not install a confined agent, which is the
  existing rule that a restriction a harness cannot express is never installed unrestricted.
- Any change to the edit gate, the floor, or the owner-run list.
- Any use of a model other than the live trial in increment A.

## Assumptions and constraints

- Python standard library only; tests with `unittest`; the project minimum is 3.11.
- The decision's trial (2026-10-24, Claude Code 2.1.310, `claude -p`) showed that a hook in a project agent's frontmatter on
  `Read` runs and that exit 2 blocks. It did not test any other tool, interactive mode, or what the hook input carries for
  `Bash`, `Write` and `Edit`. Increment A tests those; the later increments are built against what A records.
- The hook input carries a session id and a working directory (the decision's statement). Increment A (`2c922a8`) recorded the
  form of the scratch directory as observed, not documented: `/private/tmp/claude-<uid>/<working directory with / and . replaced
  by ->/<session id>/scratchpad`, not under `TMPDIR`. If the layout's template cannot name it for a given session, the layout
  declares no scratch and the agent is not installed (fail closed).
- **Found by A, and accepted by the owner on 2026-10-24:** Claude skips an agent's frontmatter hooks in a folder it does not
  trust and runs the agent anyway, so the guard is not run there. The owner accepted this as a stated limit and not a gap to
  close in this plan (choice 8). The permission layer's deny rules still applied in an untrusted folder (one run).
- The rendered agent file is a harness file the project's own agent could edit. The guard therefore reads the limits from the
  installed module's verified neutral item, not from the rendered file.
- The edit gate runs only while a plan is under way; this guard runs on every call of its agent.
- Editing files under `packages/workbench/claude/` or any module's tree stales its shipped approval. `release-approvals` is the
  owner's; I run it only on "Run it for me", and delete stale records only after a preview and "remove them".
- Discovery tooling: graphify: skipped — not installed in this project; the scope was found by reading the decision,
  `harness-modules.md`, `gate_hook.py`, `layout.py`, `neutral.py` and the Claude module's layout.

### Choices (made by me; the owner may change any)

1. **Two fields, kept small.** An agent declares `writes`, a list of named roots it may write under (only `scratch` is defined),
   and `run`, a list of pinned command patterns. Whole-root write access only; no sub-patterns inside a root. Cost: an agent
   cannot be limited to a sub-folder of the scratch area. It does not need to be.
   **Encoding.** Neutral front matter is one `key: value` line of printable ASCII per field (`neutral._front_matter`), so both
   fields are one line, and a list is comma-separated like `tools`. This works because no pattern may hold a comma:
   ```
   tools: read, search, edit, shell
   writes: scratch
   run: python3 {scratch}/check.py, python3 {scratch}/check.py --fast
   ```
   Limits: `writes` takes the one word `scratch`; `run` takes at most 4 patterns of at most 200 characters each, and the line
   is at most 600 characters. A duplicate, an empty entry, an unknown root, a pattern outside the grammar, or a repeated
   field is refused at read, as `tools` is today. `writes` needs `edit` in `tools`, and `run` needs `shell`; a field without its
   tool is refused. `module-contract.md` does not define agent front matter (checked), so only `harness-modules.md` changes.
2. **A pinned command is matched token by token, with no shell parsing.** The pattern is a sequence of space-separated tokens,
   each a literal or the placeholder `{scratch}/<name>`, where the part after the slash is one plain file name. The guard
   first refuses any command containing a character outside a closed safe set (no quote, `;`, `&`, `|`, `$`, backtick,
   parentheses, redirection, newline or backslash), then splits on single spaces and compares token by token. A placeholder
   token must name a file directly inside the scratch directory, with no link in the path and no `..`. A token starting with
   `-` that the pattern does not spell is refused. Cost: a pinned command cannot take a quoted argument. Alternative
   rejected: a regular expression written by the module, which puts module-chosen matching on the permission path.
3. **The agent file carries the hook; the settings file does not.** The trial put the hook in the agent's own frontmatter, so
   it applies to that agent only and not to the session. The rendered hook is `wb agent-gate <harness> <agent> || exit 2`,
   with the same `|| exit` reasoning as the edit gate. The matcher covers the tools the agent holds that can write or run:
   the layout's edit and shell tool names.
4. **The scratch directory is a template in the layout,** for example a path built from the temporary directory, the user id,
   the project's directory name and the session id. The guard fills it from the hook input and the environment and refuses if
   any part is missing. The exact template is whatever A verifies; this plan does not guess it.
5. **A confined agent's rendered file is denied for edits,** by extending the existing edit deny (the same function that
   covers `.claude/settings.local.json`) to the rendered agent paths, in both the relative and the absolute spelling. The
   deny covers file tools and not a shell, as the spec already says of the settings file.
6. **The guard command is `wb agent-gate`,** a new `AGENT_SAFE` command beside `gate`. It reads the declared limits from the
   installed, pinned module through the same lookup the edit gate uses for its process module, never from the rendered file.
7. **A confined agent may not delegate.** An agent that declares `writes` or `run` and also lists the `agents` tool is refused
   at read, because the agent it started would not be covered by this agent's hook. A confined agent also gets no tool
   beyond `read`, `search`, `edit`, `shell` and `web`; the guard covers `edit` and `shell` only, and `web` writes nothing
   to disk. Alternative rejected: recursive inheritance, which needs a second hook model and has no trial behind it.
8. **The guarantee holds in a trusted folder only, and the spec and attach say so.** Because Claude skips the hook in a
   folder it does not trust, the spec states the confinement as enforced where the folder is trusted, and that a headless
   run (`claude -p`, the SDK, a script) in an untrusted folder skips the guard and leaves the agent's `edit` and `shell`
   tools unconfined. Attach prints a note whenever it renders a confined agent. Whether an interactive session in an untrusted
   folder runs the agent at all was not tested; if it does, the same limit applies there, and the spec says it was untested.
   Not done here: reading the folder's trust flag from the owner's global configuration (that is the unbuilt
   `global-settings-check`), and a dedicated tool that fails closed, which is Deferred work. Alternative rejected for now:
   a tool in the workbench's own code instead of `edit` and `shell`, which would fail closed but needs a tool server that
   is unbuilt and untried.

## Completion criteria

1. Increment A's trial results are in the spec's Evidence: for `Bash`, `Write` and `Edit` in an agent's frontmatter, whether
   the hook ran and blocked, the fields the hook input carries, and whether the scratch directory is computable.
2. A neutral agent with `writes` or `run` is read and validated against the encoding in choice 1; an unknown root, a pattern
   outside the grammar, a duplicate, an over-long line, a field without its tool, or the `agents` tool alongside either
   field is refused at read; an agent with these fields on a harness whose layout has no per-agent hook is skipped with a
   warning and never installed.
3. `wb agent-gate` allows a write under the scratch directory and a command that matches a pinned pattern, and refuses: a
   write elsewhere, through a link, with `..`, in another case, or by a missing field; a command with a metacharacter, an
   extra token, an option the pattern does not spell, or a placeholder outside scratch; a part of a path that does not exist
   yet (it is placed against the scratch directory and does not count as outside it) and any error while examining a path
   (it counts as a refusal, never as outside); an input of the wrong shape, too
   large, or past the deadline; and an agent name the installed module does not declare. Each is a test.
4. The rendered agent file for a confined agent carries the hook, the rendered deny covers that file, and `wb check` reports
   an edited agent file.
5. A test module with a confined agent goes from declaration to a refused call through attach and the guard, with the
   hook's command run as the harness runs it.
6. The spec states the enforcement, the grammar, the stated limit, the trusted-folder limit of choice 8, and what was and was
   not verified. No spec or decision text claims the live behaviour beyond A's evidence. Attach prints the note of choice 8
   for a confined agent, and a test shows it. The decision `2026-10-24-declared-agent-confinement` carries a dated note of the
   trusted-folder limit; its body is not edited.
7. `python3 -B -W error tests/run_all.py` is green on this machine; `release-approvals` reports nothing stale;
   `doccheck`, `refcheck` and `git diff --check` print nothing.

## Increments

### Increment A — A live trial of the open facts

**Outcome:** the facts the later increments depend on are recorded as evidence, or the plan is stopped for the owner.
**Dependencies:** none. Needs the owner's allowance to run `claude -p` in a throwaway project.
**Affected areas:** `docs/specs/harness-modules.md` ("Evidence" only). No code.
**Steps:**
1. In a throwaway workbench project outside this repository, install a trial agent whose frontmatter declares a hook on
   `Bash`, `Write` and `Edit`, each hook writing the whole hook input to a log and exiting 0, then 2.
2. Run `claude -p` with the agent: ask it to run a command, write a file and edit a file. Record for each tool whether the
   hook ran, whether exit 2 blocked it, and the fields of the hook input (session id, working directory, tool input).
3. From a session's real scratch directory, record how it relates to the temporary directory, the user id, the project
   directory and the session id, and whether the hook can compute it.
4. Record that the interactive trust question was not tested, unless the owner runs it.
5. Write the results into the spec's Evidence section with the Claude Code version and the date.
**Stop rule:** if a tool's hook does not block, or the scratch directory cannot be computed, stop and report to the owner
before B; the plan's later increments change or end.
**Verification:** `doccheck`, `refcheck` and `git diff --check` print nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-agent-confinement#A`.

### Increment B — The specification

**Outcome:** the spec describes the agent fields, the pinned-command grammar, the layout entries, the guard, the rendering and
the stated limit, built against A's evidence.
**Dependencies:** A.
**Affected areas:** `docs/specs/harness-modules.md` (neutral items, translation, a new section beside "The edit gate hook",
acceptance criteria). `module-contract.md` is not changed: it does not define agent front matter.
**Steps:**
1. Add the fields to the neutral agent table with the encoding, example and limits of choice 1, the grammar and the character
   set, the refusal of `agents` beside either field (choice 7), and the fail-closed rule for a harness with no per-agent hook.
2. Add the section for the guard: input, the order of checks, the refusals, the deadline, where the limits are read from.
3. Add the layout entries to the Claude layout table and the rendering rule.
4. State the limits: a script the agent writes and runs is not confined, and the guard runs only in a folder Claude trusts
   (choice 8), with A's observations.
5. Add acceptance criteria matching completion criteria 2 to 5.
**Verification:** `doccheck`, `refcheck`, `git diff --check`; the owner reads the spec.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-agent-confinement#B`.

### Increment C — Read and validate the fields, and skip what cannot be enforced

**Outcome:** a neutral agent with `writes` and `run` is read and checked; the layout validator accepts the scratch and
per-agent hook entries; translation skips a confined agent on a harness that has no such hook.
**Dependencies:** B.
**Affected areas:** `workbench/neutral.py`, `workbench/layout.py`, `workbench/harnessplan.py` (translation only), their tests,
and the Claude module's layout in `packages/workbench/claude/module.json` (and its tests).
**Steps:**
1. Tests first: each refusal in completion criterion 2 (including the `agents` combination and each limit at, and one past,
   its bound), the accepted example of choice 1 read back field by field, and the layout validator's refusals for a
   malformed entry.
2. Implement the reader, the grammar check and the layout validation, then the skip with a warning.
3. Add the layout entries to the Claude module.
**Verification:** the new tests fail before and pass after; the root suite and the `claude` module suite pass;
`release-approvals` (the owner's) for the edited `claude` module.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-agent-confinement#C`.

### Increment D — The guard

**Outcome:** `wb agent-gate <harness> <agent>` decides one call from the declared limits.
**Dependencies:** C.
**Affected areas:** a new `workbench/agent_gate.py`, `workbench/cli.py`, `workbench/rules.py` (the command's safe-list entry),
tests. The edit gate's path helpers are reused, not copied: moved to a shared place only if reuse needs it.
**Steps:**
1. Tests first for completion criterion 3, each as a case with the hostile input, using a fake scratch directory and a fake
   installed module; links, `..`, case variants, a metacharacter set, option-like tokens, NUL, oversize input and the deadline.
2. Implement the guard: shape, then agent lookup from the installed pinned module, then tool dispatch, then the path or command
   check; every other outcome is a refusal.
3. Add the command to the safe-list and the CLI.
**Verification:** the new tests; the root suite; `git diff --check`. Security review by an independent reviewer only if the owner
asks (this increment touches untrusted input, paths and command text).
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-agent-confinement#D`.

### Increment E — Render the hook and protect the rendered file

**Outcome:** attach writes the hook into a confined agent's file, the deny covers that file, and `check` reports an edit to it.
**Dependencies:** D.
**Affected areas:** `workbench/harnessplan.py`, `workbench/attach.py`, `workbench/check.py`, `workbench/rules.py` if the deny
function lives there, tests.
**Steps:**
1. Tests first: the rendered frontmatter bytes for a confined and an ordinary agent; the deny patterns in both spellings;
   the drift report; an unconfined agent's file is byte-identical to before.
2. Implement the rendering and the extension of the deny. The harness name and agent name are checked against the same
   pattern as the gate's before they enter the command.
3. Attach prints the note of choice 8 once for each confined agent it renders, and a test shows it, and that an
   unconfined agent produces no note.
**Verification:** the new tests; the root suite; a re-attach is idempotent.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-agent-confinement#E`.

### Increment F — End to end, and the records

**Outcome:** a test module's confined agent is refused outside its limits through the real attach and the hook's own command; the
decision and the spec say what is built.
**Dependencies:** E.
**Affected areas:** `tests/` (a test module and an end-to-end test), `docs/specs/harness-modules.md` ("As built"),
`docs/development.md` if a command is added, the plan's Result.
**Steps:**
1. Install a test module with a confined agent into a fixture project, attach, and run the rendered hook command as the harness
   would, with a hostile and a permitted input.
2. Update the spec from "proposed" to "as built", with what was and was not verified; add `wb agent-gate` to the development
   documentation.
3. Add a dated note to `docs/decisions/2026-10-24-declared-agent-confinement.md` recording the trusted-folder limit, leaving
   its body unchanged, and update `docs/decisions/README.md` only if its status text needs it.
4. Run the full suite once with nothing edited meanwhile; record the totals in the Result.
**Verification:** the end-to-end test; `python3 -B -W error tests/run_all.py`; `doccheck`, `refcheck`, `git diff --check`.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-agent-confinement#F`.

## Verification for the plan as a whole

- The full suite is green once after F, with nothing edited while it runs.
- `release-approvals` reports nothing stale after C; deleting stale records is on "remove them".
- No agent ships and no live session other than A's trial was run. The owner may run an interactive check of the hook trust
  question; the spec records whether they did.

## Risks and sensitive actions

- **Hooks that do not run.** A hook that times out or fails to start lets the call through. `|| exit 2` covers a failed start;
  the guard's own deadline sits below the harness timeout. A's trial showed the hook blocks for `Bash`, `Write`, `Edit` and
  `Read`. It also showed Claude skips the hook silently in a folder it does not trust, which this plan accepts as a stated
  limit (choice 8); the residual is a headless run in an untrusted folder, and an interactive one if Claude allows it.
- **A pinned command is still a program.** The pattern pins the command line, not what the named program does. The stated
  limit is in the spec.
- **A weak grammar is a bypass.** The grammar refuses before it parses, and each refusal has a test; an independent security
  review is available at the owner's request.
- **The scratch directory may not be computable.** Then the plan stops at A, which is a cheap place to find out.
- **Rendered file edited by the agent.** The deny covers file tools only. A shell can still edit it, and the guard reads its
  limits from the installed module, so an edited file does not widen the limits.
- Sensitive actions: running `claude -p` in A (a model call, in a throwaway directory outside this repository, with the owner's
  allowance); `release-approvals` and stale-record removal (the owner's). Nothing is committed or pushed without the
  owner's word. Reviews run only when the owner asks.

## Review record

Rounds 1 and 2 of 3, 2026-10-24, `ask-codex review-plan`, model `gpt-5.6-luna`, effort medium (asked for by the owner).
Outcome: converged. Two findings, both major, both applied:

- R1-F1: the neutral format for `writes` and `run` was not defined against the one-line front matter. Choice 1 now gives the
  encoding, an example, the limits and the refusals, and increment C tests them. `module-contract.md` was checked and does not
  define agent front matter.
- R1-F2: a confined agent that held the `agents` tool could start an agent outside its hook. Choice 7 refuses that
  combination at read; completion criterion 2 and increments B and C carry it.

Round 2 found nothing. Closed with `ask-codex archive` at 2026-10-24T17:02:09Z after 2 of 3 rounds, 2 decisions applied and
0 rejected, on the owner's word.

## Deferred work

- `security-review-module`: the module with the skill and its agent, the first user of this plan.
- A dedicated tool, in the workbench's own code, given to a confined agent in place of `edit` and `shell`. It would fail
  closed in an untrusted folder, because without it the agent can do nothing. It needs a tool server (unbuilt), a trial that
  the harness hands a tool to one agent only and what an unapproved server does, and a plan of its own.
- Reading the folder's trust flag from the owner's global configuration so `wb check` can warn, which waits on
  `global-settings-check`.
- The S7 fix, a separate plan to draft after this one: `is_inside` treats a missing path as outside the repository in
  `workbench/wbkit/call.py`, `ask-codex`, `safe-git` and `remote-runner` (fixed in `mempalace`; `remote-runner`'s
  `trusted_entries` has half of it). Found on 2026-10-24; the shared kit was shown to return "not inside" for a missing
  directory in a repository.
- opencode and Codex support for per-agent hooks, with `verify-opencode`.
- Sub-paths inside a root, and a second root (for example the session's temporary directory beside a project scratch), if an
  agent needs them.

## Result

**Increment A (`2c922a8`):** the trial ran on Claude Code 2.1.310 and is recorded in `harness-modules.md`, "Hooks in an agent's
frontmatter". The hook blocked `Bash`, `Write`, `Edit` and `Read` for the session agent, and `Bash`, `Write` and `Read` for a
subagent. The stop rule applied: in a folder Claude does not trust, the hooks are skipped and the agent runs unconfined, with
nothing in the output. The owner accepted that as a stated limit on 2026-10-24 (choice 8), with the dedicated tool and the
trust-flag read as Deferred work, and the amendments of that day to choice 8, the D and E steps, the risks and the deferred
items. The first four runs were in a folder outside any trusted project; the later runs were below this project, whose
trust was inherited. The interactive check was not run. A hook input dump briefly held a local messaging token in
untracked scratch; the hook no longer logs it.

**Increment B:** `harness-modules.md` now specifies the fields (`writes`, `run`, their encoding and refusals), the translation
rule, the layout's `hook` and `scratch` entries, the new section "The agent gate" (input, deadline, order of checks, rendering,
deny, check, attach note), the three stated limits (an unconfined written script, trusted folder only, verified once) and the
acceptance criteria. Choices of mine in the text: the safe character set is letters, digits, `. / _ - : = + @ %` and single
spaces; a command is at most 1,000 characters; the scratch directory itself is not a writable path; the Claude scratch template
is `/private/tmp/claude-{uid}/{cwd_key}/{session_id}/scratchpad`, taken from A's observation. `doccheck`, `refcheck` and
`git diff --check` print nothing. The owner reads the spec; no code changed.

**Increment C:** `neutral.read_items` reads `writes` and `run` (`Item.writes`, `Item.run`) under the grammar and limits of
choice 1, and refuses the `agents` tool beside either. `layout.problems` accepts the agent kind's `hook`
(`key`, `event`, `timeout`, `block_code`) and `scratch` together, and refuses one without the other, a hook without a tools
table that grants `edit` and `shell`, and a scratch template that is not absolute, has fewer than two plain segments, has a
placeholder first segment or lacks `{session_id}` exactly once. `harnessplan` skips a confined agent, overrides included: with the
reason "no per-agent hook" where the layout lacks the entries, and "does not yet render the hook" where it has them. That second
skip is deliberate and increment E replaces it, so no confined agent is ever written without its hook. The `claude` module
declares `hook` (`hooks`, `PreToolUse`, 20, 2) and `scratch` (`/private/tmp/claude-{uid}/{cwd_key}/{session_id}/scratchpad`),
pinned by its module test. Two existing tests changed: the layout constants test no longer expects `writes` and `run` as harness
fields, and a `code-work` test that removes an agent's tools table now removes the hook and scratch with it. `release-approvals`
was run on the owner's word, and three stale shipped records were removed after a preview and "remove them". The full suite is
green: 3,991 tests in 9 roots. One earlier full run stopped making progress in the first root (no CPU for 21 minutes, a
leftover child process, a wait on a condition variable); it was stopped, and the verbose run of that root and the next full run
passed. The cause was not found and the hang was not reproduced.

**Increment D:** `wb agent-gate <harness> <agent>` is built in `workbench/agent_gate.py`, routed in `cli.py` and listed in
`rules.AGENT_SAFE`. It reads the agent's limits from the installed module's neutral agent file after its hash equals the
manifest's, never from a rendered file; checks the shape of `cwd` and `session_id` before the lookup; allows a write only
strictly below the scratch directory (no `..`, `.` or empty part, no link in a part that exists, the scratch directory spelled
exactly as filled, an unexaminable part a refusal); and allows a command only after the closed character set and a token-by-token
match. Beyond D's listed areas: `gate_hook.py` gained the shared `guard` and `document`, and `fold` and `check_cwd` became public
(the plan's "moved only if reuse needs it" applied); `layout.facts` gained `agent_gate`; `docs/development.md` and
`installer-interface.md` list the command; two spec sentences no longer say "not built". Existing tests changed: the layout facts
tests and the `claude` module's harness-facts test (which staled its shipped record; `release-approvals` was run on the owner's
word and two stale records were removed after a preview). The guard's 53 tests were written after the code, not before; a
mutation check (no link check, `..` normalised away) was caught by them, and the character set alone is not caught by any
command test because token equality refuses the same commands, so one test calls it directly. The full suite is green: 4,044 tests
in 9 roots. A project path with a space, or a character outside letters, digits, `. _ -` and `/`, makes every call refuse, since
the scratch name cannot be derived; only `/` and `.` becoming `-` was observed. No independent security review has been run.
**For E:** `harnessstage._override` lets a module ship `harness/<harness>/agents/<name>.md`, which replaces the rendered file;
E must refuse an override of a confined agent or render the hook into it.

**Increment D, security review:** an independent adversarial review (a `security-reviewer` agent, on the owner's word) found no
direct bypass of the path or command checks and five points, each judged here. (1) Fixed: the guard took the project from the
hook's `cwd`, so an agent could build a project with a matching manifest and agent file inside its scratch area and move the
working directory there; the guard now refuses a working directory or project root (also through a link) at or below the
template's literal leading part, with three regression tests that fail without it. (3) Fixed: Claude's directory names turn
`_` into `-` (seen for `claude_global_config`), so the key is now every non-alphanumeric ASCII character turned into `-`, a
non-ASCII working directory is refused, and the spec's limit says the rule was observed for `/`, `.` and `_` and assumed for the
rest. (4) Fixed: a Bash call with a field outside `command`, `description`, `timeout` and `run_in_background` (for example
`dangerouslyDisableSandbox`) is refused. (5) Recorded in the spec: the scratch directory is per session, so one agent can plant
a script for another's pinned command, and a pinned `cd` is unsafe. (2) Not a bypass today and carried to E: the matcher is
`Bash|Edit|Write`, which equals the tools an agent holding `edit` and `shell` is rendered with, because the layout lists only
`Edit` and `Write` for `edit`; E must derive the matcher from that same list and test that they agree. Not changed:
`guard` does not catch `BaseException`, which no code on its path raises, and a non-zero exit is a block under `|| exit 2`.
