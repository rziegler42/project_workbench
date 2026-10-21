# Claude harness, attach and check

Status: Approved
Created: 2026-10-20
Candidate: workbench-v1#claude-harness
Specs: harness-modules, installer-interface, trust-and-approval, repository-boundary, module-contract

## Goal

Make the workbench hand an AI agent its working files, and fence it in, without a human editing
anything by hand. Today `install` ends with `harness not attached: attach is not built yet`, no
agent receives a skill, an agent definition or a permission rule, and the owner-run commands
(`install`, `upgrade`, `add`, `attach`, `acknowledge`, `recover`, `approve`, `pin`,
`release-approvals`) are protected only by their terminal check, which the specs call friction and
not authentication. The real barrier is a harness `deny` rule, and nothing renders one.

When this plan is done:

- a first-party **Claude harness module** exists whose declaration carries a `layout`;
- the installer **translates** neutral skills, agents and commands into Claude's files from that
  layout, failing closed for a restriction Claude cannot express;
- it **renders** the neutral rule list (the hard-stop floor, the guarded-store write deny and a
  deny for every owner-run command) into Claude's per-clone local settings;
- `wb attach` writes those per-clone files, the `.git/info/exclude` entries and the local manifest
  `.workbench/local/harness.json`, and `wb install` ends by attaching;
- `wb check` reports drift, strays, tracked harness output and tracked-pointer problems.

## Scope

- **Verification of the Claude formats** against the installed Claude Code (2.1.305 on this
  machine) before any is built: the local settings file and its permission-rule syntax, the skill,
  agent and command front matter and paths, and the `@` import in the root file. The specs mark
  all of these "to verify". The findings are recorded in `harness-modules.md`.
- **Neutral items and the neutral rule list** (`harness/neutral/`): a strict reader for skill,
  agent and command files, and the rule list with `ask` and `deny` only (an `allow` is rejected).
- **The `layout` field** of a harness declaration: its values are checked by a new validator, as
  `module-contract.md` leaves to the harness specification.
- **A layout-driven translation and rendering engine.** The installer applies the layout; the
  Claude module is data, not code. Nothing a harness module ships runs at attach.
- **The first-party package** `packages/workbench/` with the module `claude`, shipped with its
  approval record (`release-approvals`).
- **`wb attach`**, the attach step of `wb install`, and **`wb check`**, as specified in
  `installer-interface.md` ("`attach` (proposed)", "`check` (proposed)").
- **Spec and guide updates** for what was built and verified.

## Non-goals

- opencode (`verify-opencode`, `opencode-harness`) and Codex. The engine is layout-driven so they
  can follow, but nothing here builds them.
- The content of any skill, agent or command. Tests use fixtures; the first real items arrive
  with `groundwork-module` and `code-work-module`.
- Hooks (a hook is code, ships only under `harness/claude/` and is registered in the local
  settings) and module-provided tools. Neither has a user yet; both stay in `harness-modules.md`
  as specified and unbuilt. `code-work-module` and `researcher-fetch-tool` bring them.
- Generating the "Compact Instructions" section of `CLAUDE.md`. No module supplies the neutral
  preservation guidance yet (see Decision 3).
- Writing a harness's global configuration, or the owner's own `allow` rules. The workbench never
  writes them (`harness-modules.md`, "Permissions").
- Changing what `install`, `upgrade`, `add`, `acknowledge` or `recover` write or their digests,
  other than `install`'s preview and final step.

## Assumptions and constraints

- Python standard library only; tests with `unittest`; full suite
  `python3 -B -W error -m unittest discover -s tests` (1279 tests today).
- Everything attach writes is per-clone and untracked, is created through the no-follow writer
  (`projectfs`), and is regenerated rather than merged. A committed file never names a harness
  (`repository-boundary.md`).
- A harness module declares no `writes` and no `fills` (`2026-10-20-harness-module-writes-nothing-committed`).
- The local manifest is scratch and grants no authority. `check` says the files match the scratch
  record, not that they are safe.
- A deny rule in Claude is a best-effort barrier: it matches the command text an agent submits and
  not what a wrapper script runs. The specs already say the strength depends on the harness
  (`trust-and-approval.md`); the plan does not claim more, and records the limit.
- The harness calls `wb` and not `python3 -m workbench`
  (`2026-10-20-isolated-launcher-invocation`). The deny rules cover both spellings.
- **Decided by me, for the owner to confirm or change before approval:**
  1. **An existing local settings file.** Attach creates `.claude/settings.local.json` exclusively,
     as the spec says. If it already exists, attach refuses with that path as a conflict and prints
     the exact `permissions` entries to add by hand. It does not merge into the owner's file.
     *Alternative:* merge only `deny` and `ask` entries into the existing JSON, shown in the
     digest-bound preview, never touching `allow`. That is more useful, since many owners already
     have the file, and it is new write surface on a file the owner controls.
  2. **Attach and the unfinished-write marker.** `install` runs attach after its own marker is
     removed, so the install is complete before any per-clone file exists. A failure in attach
     prints `failed:`, says the install is complete, names `wb attach`, and exits 3. Attach is
     idempotent: a path that already holds exactly the planned bytes is left as it is and reported;
     a different one is a conflict. The local manifest is written last, so a part-written attach has
     none and can be rerun. No new marker or recovery command is built.
  3. **The Compact Instructions section** waits for `code-work-module`. The root file this plan
     generates is the `@AGENTS.md` pointer line only. `harness-modules.md` and its acceptance
     criterion are corrected in increment L to say the section appears when a module supplies the
     guidance.
- Discovery: graphify — skipped, this project has no discovery tooling. The files involved
  (`declarations.py`, `modulefiles.py`, `verify.py`, `install.py`, `installplan.py`, `projectfs.py`,
  `floor.py`, `firstparty.py`, `cli.py`) and the five specs above were read for this plan.

## Completion criteria

1. The Claude formats the plan depends on are recorded with the version and the evidence in
   `harness-modules.md`, and each "to verify" for Claude is closed or restated.
2. A neutral skill, agent and command fixture installed for Claude appear at Claude's paths
   under the project, none appears in `git ls-files`, and each is listed in
   `.git/info/exclude`. Two clones with different harnesses (the Claude module and a fixture
   harness) get a byte-identical committed tree.
3. An agent item with a restriction Claude cannot express is not installed and the installer says
   why; an item whose `needs` Claude lacks is skipped with a warning; a rule list containing
   `allow` is rejected; a bad front matter, name or bundled-file path is refused with nothing
   written.
4. After attach, the local settings deny writes to the guarded store and deny `wb install`,
   `upgrade`, `add`, `attach`, `acknowledge`, `recover`, `approve`, `pin` and `release-approvals`
   in the `wb` and the `python3 -m workbench` spellings, and render the floor. `wb preview` is not
   denied. The owner's `allow` rules are never written.
5. `wb attach` writes only per-clone files, refuses a conflict, an unapproved module and a clone
   that already records a harness, is idempotent on a rerun after a failure, and writes the local
   manifest last. `wb install` attaches as its last step and its preview lists the harness files,
   the exclude lines and the local manifest.
6. `wb check` is read-only, leaves `.git/index` byte-identical, reports each condition in
   `installer-interface.md`, reports "none attached" as valid, and exits 1 only when it reports a
   problem.
7. Every hostile case in Review focus has a test that fails without its guard. An adversarial
   `security-reviewer` pass over attach, the rendering, the exclude primitive, the install
   integration and `check` finds nothing Medium or higher unresolved.
8. `harness-modules.md`, `installer-interface.md`, `trust-and-approval.md`,
   `repository-boundary.md` and `docs/development.md` describe what was built, the roadmap's
   Current state is updated, and the full suite passes with `-W error`.

## Review focus

Inputs and conditions the specs imply that the tests must pin, most likely to bite first:

1. **Settings file already exists, or is a link.** Attach must not follow a link at `.claude`,
   `.claude/settings.local.json` or `.git/info/exclude`, and must not overwrite a file it did not
   create (Decision 1).
2. **A neutral item name or bundled file that escapes.** `../`, an absolute path, a name that
   collides after case folding with another item, `.git`, a file at the same path as a generated
   settings file, or a symlink in a skill directory.
3. **Front matter that is not what it looks like.** Duplicate keys, a multi-line value, a `tools`
   entry outside `read search edit shell web agents`, an `allow` smuggled in as a rule, control
   characters and lookalike letters in a name or description.
4. **A deny that does not match.** The command written with a path (`~/.config/project-workbench/bin/wb
   install`), with extra spaces, with `python3 -m workbench`, or under `env`. The plan lists what
   is matched and what is not, rather than claiming it is airtight.
5. **`.git` that is not a directory** (a worktree or submodule gitfile) or has no `info/`:
   refuse the first with a clear message, create `info/` for the second.
6. **Attach after a half-finished attach**, a clone that already has a different harness, and a
   harness module edited between approval and attach (hash mismatch).
7. **A very large neutral tree.** Counts and bytes are bounded like the manifest's.

## Increments

### Increment A — Verify the Claude formats

**Outcome:** the "to verify" statements for Claude are checked against the installed version and
recorded; later increments build on evidence, not on the documentation read on 2026-10-19.
**Dependencies:** none.
**Affected areas:** `docs/specs/harness-modules.md` (the Claude section and Open issues). No code.
**Steps:**
1. Record `claude --version`. Check, from the installed version's own behaviour and its official
   documentation, and note the source and date of each: the project-local settings file name and
   whether Claude ignores it in git by default; the `permissions` `deny` and `ask` rule syntax for
   `Bash(...)` (prefix and wildcard forms, how `&&`, a leading `cd` or `env` are treated) and for
   `Write(...)`/`Edit(...)`/`Read(...)` on a path outside the project; the skill, agent and command
   file paths and front-matter fields; the `@AGENTS.md` import in `CLAUDE.md`; and whether an
   agent's `tools` field restricts it.
2. Run each rule form in a scratch project with a recording stand-in for `wb`, to see whether the
   rule blocks it, and record what is and is not matched.
3. Rewrite the Claude section of `harness-modules.md` with the verified layout and a short
   "Evidence" note (version, date, how checked). Anything not verified stays marked.
**Verification:** `git diff --check`; every changed statement cites its evidence in the note.
**Evidence:** commit with trailer `Plan: 2026-10-20-claude-harness#A`.

### Increment B — Neutral items and the neutral rule list

**Outcome:** the installer reads `harness/neutral/` items and a rule list strictly, and nothing
else yet.
**Dependencies:** A.
**Affected areas:** new `workbench/neutral.py`, its tests; `modulefiles.py` only if its provisional
item-name reading (`<kind>/<name>` or `<kind>/<name>.md`) needs to be shared.
**Steps:**
1. Failing tests for the cases in Review focus 2 and 3, a valid skill (with bundled files), agent
   and command, and a rule list with `allow`.
2. Implement `read_items(tree)` returning typed items (kind, name, description, tools, needs,
   model, body, bundled files with their hashes), and `read_rules(data)` returning `ask`/`deny`
   rules with a tool class and a glob pattern. A strict, single-line front matter reader; bounds on
   count, bytes and name length; paths through `safefs.validate_relpath`; links refused.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-20-claude-harness#B`.

### Increment C — The layout field

**Outcome:** a harness declaration's `layout` is validated, so a bad layout is refused when the
module is verified and before it is approved.
**Dependencies:** A.
**Affected areas:** new `workbench/layout.py`, `declarations.py` or `verify.py` (call it for a
`harness` module), `request.py` (the approval request already prints the layout; it must print the
validated form), tests including the existing `sample-harness` fixture (`root: none`, ...).
**Steps:**
1. Failing tests: every key of `root`, `kinds`, `local_settings`, `hooks`, `exclude`, `notes`
   with good and bad values; an exclude path that is absolute, contains `..`, is `.git`, is under
   `.workbench`, or points at the guarded store; a `kinds` directory shared by two kinds; a rule
   syntax template that is not one of the allowed forms.
2. Implement the validator from what increment A verified. The layout is data: directories,
   file-name patterns, a front-matter field mapping for each kind, the local settings path, a rule
   syntax table and the exclude paths. Nothing in it is executed.
**Verification:** new tests, then the full suite; the approval request test for a harness module.
**Evidence:** commit with trailer `Plan: 2026-10-20-claude-harness#C`.

### Increment D — Translation

**Outcome:** a pure function turns neutral items and a layout into the exact files to write, with
warnings, and fails closed.
**Dependencies:** B, C.
**Affected areas:** new `workbench/harnessplan.py` (translation part), tests.
**Steps:**
1. Failing tests: skill, agent and command to Claude paths; field mapping; a dropped field warns;
   an agent whose restriction is inexpressible is skipped, never installed unrestricted; `needs`
   unmet is skipped with a warning; an override in `harness/claude/` replaces one item; an
   `exclude` entry is reported; an item both overridden and excluded is an error; two items that
   map to one path are an error; output is byte-identical across runs.
2. Implement `translate(items, layout, overrides, excludes)` returning planned files (path, bytes,
   mode, hash) and a list of reports.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-20-claude-harness#D`.

### Increment E — Permission rendering

**Outcome:** the neutral rule list, the floor and the owner-run command denies become the content
of the local settings file.
**Dependencies:** B, C.
**Affected areas:** `harnessplan.py` (rendering part), a single list of owner-run commands next to
`floor.py` or in `cli.py` that `usage` and the rendering share, tests.
**Steps:**
1. Failing tests: the rendered file denies writes to the guarded store and each owner-run command
   in each spelling, renders the floor, leaves `wb preview` alone, never contains `allow`, is
   byte-identical across runs, and a test that fails when a new owner-run command is routed in
   `cli.py` without a deny (so the list cannot drift again; `acknowledge` and `recover` were
   missing from the roadmap's list).
2. Implement `render_permissions(rules, layout)`; the command list is one constant that the CLI's
   owner-run routing is tested against.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-20-claude-harness#E`.

### Increment F — The exclude file and the local manifest

**Outcome:** two new write primitives, bounded and no-follow: add anchored literal lines to
`.git/info/exclude`, and write `.workbench/local/harness.json`.
**Dependencies:** none technical.
**Affected areas:** `projectfs.py` (the exclude primitive, since `safefs` refuses `.git` paths),
`workbench/localmanifest.py` (the record: harness source, version, tree hash, each generated file's
path and hash), tests.
**Steps:**
1. Failing tests: lines added once and never twice; created `info/` and file; `.git` that is a
   file, a link, or `info/exclude` that is a link or a directory refused; an entry beginning `!`
   or `#`, with a glob character, a newline or a backslash refused; existing owner lines kept
   byte for byte; the primitive cannot write any other path under `.git`.
2. Implement both. The local manifest is canonical JSON with a bound, read back strictly.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-20-claude-harness#F`.

### Increment G — The first-party Claude module

**Outcome:** `packages/workbench/` with the module `claude` verifies as first-party and has a
shipped approval.
**Dependencies:** C.
**Affected areas:** `packages/workbench/package.json`, `packages/workbench/claude/module.json`
(type `harness`, the verified layout, `provides` the six harness capabilities that Claude
really supports per A), `workbench/shipped_approvals/` by `release-approvals`, tests.
**Steps:**
1. Failing tests: `verify packages/workbench --select claude` passes; the record matches; a
   change to the declaration is third-party again; the approval request shows the layout in plain
   terms.
2. Create the package and run `release-approvals`; review the diff of the shipped records.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-20-claude-harness#G`.

### Increment H — `wb attach`

**Outcome:** an existing project gets its per-clone harness files, exclude lines and local
manifest from one command.
**Dependencies:** D, E, F, G.
**Affected areas:** new `workbench/attach.py`, `cli.py` (route and usage), tests including the
install fixtures.
**Steps:**
1. Failing tests for each Refuses item of `installer-interface.md` ("`attach`"), a `.git` that is
   a file refused with a message that names it, the idempotent
   rerun (Decision 2), the existing settings file (Decision 1), approval of every module used,
   a content-hash mismatch against the lock, a lock version difference (warns), and the written
   tree against `git ls-files` (nothing tracked).
2. Implement: build the plan from the committed manifest and lock and the harness module (nothing
   is fetched that the owner has not approved), write through `projectfs` in the order directories,
   files, exclude lines, local manifest; print the files, the warnings and the post-install notes,
   and warn that it changed the agent's permissions.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-20-claude-harness#H`.

### Increment I — `wb install` attaches

**Outcome:** a new project is attached as `install`'s last step.
**Dependencies:** H.
**Affected areas:** `install.py`, `installplan.py` or `preview.py` (the preview lists the harness
files, exclude lines and local manifest; the digest covers them), `cli.py` text, tests.
**Steps:**
1. Failing tests: the preview lists them and `install` writes them after its own marker is gone;
   an attach failure prints `failed:`, says the install is complete, names `wb attach`, exits 3
   and a rerun of `wb attach` finishes; the existing install, upgrade, add, acknowledge and
   recover tests are unchanged; `harness not attached` is gone.
2. Implement; the unfinished-write record is not extended (Decision 2).
**Verification:** new tests, then the full suite, then a recorded hand run of an install into an
empty directory and a `claude` start in it, if the owner allows a Claude session for it.
**Evidence:** commit with trailer `Plan: 2026-10-20-claude-harness#I`.

### Increment J — `wb check`: harness files

**Outcome:** the read-only report for the harness: files of another harness, drifted generated
files, strays, and "none attached".
**Dependencies:** H.
**Affected areas:** new `workbench/check.py`, `cli.py`, tests.
**Steps:**
1. Failing tests: each condition; a clean clone exits 0; a clone with none attached exits 0 and
   says so; an edited generated file, a missing one and an extra one under the harness
   directories are reported; nothing is written; the local manifest is not treated as evidence.
2. Implement through the no-follow reader.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-20-claude-harness#J`.

### Increment K — `wb check`: what git tracks

**Outcome:** `check` also reports tracked files that look like harness output or scratch, tracked
files that link or import into untracked content, and committed files that differ from the manifest
beyond their owner class.
**Dependencies:** J.
**Affected areas:** `check.py`, a small bounded git reader that follows the git rule of
`installer-interface.md` (scrubbed environment, no repository configuration, no hooks, no
program from the target), tests with real `git` in a scratch repository and with a hostile
`.git/config`.
**Steps:**
1. Failing tests: the three reports; `.git/index` byte-identical before and after; a hostile
   `core.fsmonitor`, `core.sshCommand` or `include.path` in the repository's config does not run;
   the tracked-pointer rule flags links and imports and ignores prose and source code.
2. Implement. If listing tracked files cannot be done without running git safely, read the index
   format directly instead and record why.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-20-claude-harness#K`.

### Increment L — Documentation

**Outcome:** the specs, the guide and the roadmap match what was built and verified.
**Dependencies:** A to K and the security pass.
**Affected areas:** `docs/specs/harness-modules.md`, `installer-interface.md` (`attach` and `check`
built, `install`'s final step), `trust-and-approval.md` (the rendering note: rendered now, the full
command list), `repository-boundary.md` if it changed, `docs/development.md`, `docs/roadmaps/workbench-v1.md`
(Current state and the `claude-harness` boundary list, which omits `acknowledge` and `recover`),
decision records only if the owner asks.
**Steps:** edit the documents; correct the Compact Instructions criterion (Decision 3); record
every limit found.
**Verification:** `git diff --check`; every claim matched to a test or a run.
**Evidence:** commit with trailer `Plan: 2026-10-20-claude-harness#L`.

## Verification for the plan as a whole

- Full suite with `-W error` after every increment, recorded in the Result.
- A read-only `workflow-reviewer` review per increment, when the owner asks.
- An adversarial `security-reviewer` pass over attach, the rendering, the exclude primitive, the
  install integration and `check` before increment L, since they write the files that set an
  agent's permissions and read a repository an attacker may control. A fix is new attack surface,
  so the reviewer tries to bypass each fix.
- A recorded hand run of the whole path: `install` into an empty directory with the Claude module
  and a fixture module, `claude` started in it, a denied `wb install` attempt, `wb check`.

## Risks and sensitive actions

- **This plan writes the files that set an agent's own permissions.** A bug here can widen what an
  agent may do. Nothing is ever allowed, only denied or asked, and rendering is tested
  byte-for-byte; the security pass is mandatory.
- **A deny rule is not a sandbox.** It stops the obvious command forms and not a wrapper. The
  plan states this in the docs and does not weaken the terminal check or the typed digest.
- **Claude's formats change between versions.** Increment A pins the version and date; `check`
  reports a drift in generated files, not in Claude. A format change later is a new plan.
- **Editing the owner's `.claude/settings.local.json`** is not done (Decision 1).
- **Writing `.git/info/exclude`** is the first write the installer makes under `.git` after
  `install`'s own skeleton. It uses its own primitive and cannot name any other `.git` path.
- Actions that need the owner: running `release-approvals` (shipped records are trusted), any
  `approve`, and the hand run in a live Claude session.

## Review record

Round 1 of 3, 2026-10-20, requested by the owner: Codex (`gpt-5.6-luna`, medium effort,
read-only). Outcome `changes_needed`, one major finding.

- R1-F1 (major): Review focus 5 requires refusing a `.git` file while Deferred work listed
  support for it as deferred, which read as a contradiction. Applied: Deferred work now says
  attach refuses a `.git` file in this plan and only supporting it is deferred; increment H's
  steps name the refusal and its test.

The owner approved the plan on 2026-10-20, including the three decisions under Assumptions and
constraints as written. Findings are untrusted input and were evaluated as review comments.

## Deferred work

- Hooks and module-provided tools for Claude (`code-work-module`, `researcher-fetch-tool`).
- The Compact Instructions section of the root file (`code-work-module`).
- Merging into an existing `.claude/settings.local.json` (Decision 1, alternative).
- Supporting a `.git` that is a file (worktree, submodule). Attach refuses it in this plan:
  increment F's exclude primitive refuses it and increment H tests the refusal and its message.
- opencode and Codex; harness swap; Windows.

## Result

- **A** (not yet committed): the Claude formats were checked against 2.1.305 from the official
  documentation and a scratch project. Findings that change later increments: a `Write(path)` rule
  is never consulted, so E renders `Edit(...)`; an absolute path needs `//` (a single `/` is
  project-relative and silently matches nothing), so E renders `Edit(//…)` or `~/…`; a Bash deny
  matched every tested form except a path-qualified `wb` and `bash -c`, as the documentation says.
  The recorded evidence is in `harness-modules.md`.
