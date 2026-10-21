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
- **C** (`68c9f36`): `workbench/layout.py` (`problems(layout)` returns every reason a
  layout is refused), called from `modulefiles.verify_module` for a harness module as rule
  `layout`, and `tests/test_layout.py` (29 tests; suite 1344, 1 skipped, `-W error`). The shape, which D, E and G build on:
  `root` (`none` or `{file, import}`), `kinds.<kind>` (`path` as `<dir>/{name}.md` or, for a skill,
  `<dir>/{name}/SKILL.md`; `fields`; for an agent `tools`, a map from a neutral tool to Claude tool
  names), `local_settings` (`path`, `format: json`, `actions` as dotted `deny`/`ask` keys, `rules`
  as one `Name({pattern})` or `Name({path})` template per tool class, `absolute` as `//` or `~/`),
  `hooks`, `exclude` and `notes`. A layout whose written path (root file, a kind directory, the
  settings file) is not covered by an `exclude` entry is refused, and so is any overlap between
  written paths. The loader still checks only the keys, so tests that load odd layouts keep
  working. `request.py` needed no change: a layout is verified before a request is rendered, and
  the request already shows every leaf. `workflow-reviewer` found two Medium and seven Low; fixed: the deny and ask keys must end in
  `deny` and `ask` and not nest (a deny could otherwise be written as an allow); an exclude entry
  is compared by exact spelling and a `dir/` entry never covers a file of that name; an entry that
  covers no written path is refused; `rules` must give `shell` and `write`, and a template named
  `Write`, `NotebookEdit`, `Glob` or `MultiEdit` is refused as inert; a directory holding the
  guarded store is refused; a root file may not import itself. Not done, on purpose: the layout is
  not required to map agent `tools`, since a harness that cannot restrict an agent is valid and D
  must then never install one. E and F must write each exclude entry anchored (`/<entry>`), since
  git matches a slash-free entry at any depth. Three `test_request.py` tests that put arbitrary layouts through
  full verification now render the loaded declaration instead, since verification refuses them.
- **D** (`6f1fda6`): `workbench/harnessplan.py` and `tests/test_harnessplan.py` (36 tests;
  suite 1380, 1 skipped, `-W error`). `translate(items, layout, overrides, excludes, provides)`
  is pure and returns `Result(files, reports)`: `Planned(path, data, mode, sha256, source)` with
  mode 0644, and `Report(level, item, message)` with level `warning`, `skipped`, `excluded` or
  `overridden`. It re-runs `layout.problems` and raises `PlanError`. Every front-matter value is
  written as a JSON-quoted string (`quote`). An agent is skipped, never written, when the layout
  has no `tools` field or table, or grants none of its tools; a tool the layout cannot grant is
  dropped with a warning (the allowlist only narrows); a `tools` line is always written.
  Unmapped optional fields (`args`, `model`) are dropped with a warning. An item is skipped when
  its kind or capability is not provided or its `needs` are unmet, even if overridden. An override
  is `{relative path: bytes}` (a skill needs `SKILL.md`; an agent or command is the one
  `<name>.md`) and is bounded like a neutral tree. Only an agent override is inspected: the layout
  must be able to restrict and its front matter must carry a non-empty tools line, else it is
  skipped (`workflow-reviewer` found this gap, Medium; fixed with tests, along with `items` as
  any iterable and a text-only exclusion reason; suite then 1385). Other overrides are reported only. An override or exclusion naming no neutral item, or an item both overridden and
  excluded, is an error. Mutation checks: removing the quoting, the `tools` guard, the empty-grant
  guard or the `needs` guard each fails tests. Not yet proved: that Claude's parser reads a
  quoted `tools` or `argument-hint` value as the unquoted one; G's end-to-end check must show it.
  How `harness/<name>/` files are read into the override mapping is H's job.
- **E** (`e6e8cab`): `workbench/rules.py` (new: `OWNER_RUN`, `AGENT_SAFE`, `SPELLINGS`,
  `NOT_YET_ROUTED`, `FLOOR_RULES`, `owner_run_patterns()`), `render_permissions(rules, layout,
  store_root, home)` in `workbench/harnessplan.py`, and `tests/test_permissions.py` (21 tests;
  suite 1406, 1 skipped, `-W error`). The output is sorted JSON with only the layout's `deny` and
  `ask` keys. It always holds: `Edit` denies for the store and `<store>/**` (spelled `//abs` or
  `~/rel` by the layout, refused when the store is outside home for `~/`, or when a path has a
  character outside the pattern set); a deny for each of the nine owner-run commands, bare and
  with ` *`, in the `wb` and `python3 -m workbench` spellings; and ask rules for each floor stop
  from a compiled table, a best-effort match on command text, not a sandbox. A module rule is
  added by action, a leading `/` or `~/` in a path pattern is made absolute, and an ask equal to
  a deny is dropped. A drift test parses `cli.py` and fails when a command is routed that
  `rules.py` has not classified as owner-run or agent-safe (`attach` is allowed unrouted until
  H). Mutation checks: the `//` spelling and an owner-run entry each fail tests. Not covered, as
  the plan said: a path-qualified `wb`, `env`, `bash -c`. The floor table is my choice of
  patterns; the owner may want to review it. The settings file must be created only when it is
  absent (H), and the output has no `allow` key.
  `workflow-reviewer` found two Medium and three Low (no probes could run). Fixed, with tests (suite
  1411): a layout without a `read` or `web` template is a `PlanError`, not a `KeyError`; the owner-run
  spellings now include `python3 -B -m workbench`, `python -m workbench` and `python -B -m workbench`
  (other interpreter forms stay unmatched); module rule patterns are re-checked by
  `neutral.read_rules` inside `render_permissions`; a `..`, `.` or empty segment in `home` or the
  store path is refused; more install and delete forms are in the floor table; the drift test now
  also fails when something in `NOT_YET_ROUTED` has been routed. Not done, on purpose: the drift test
  still reads only `argv[0]` string comparisons and `add_parser` calls, so a differently shaped
  dispatch could evade it; the floor table's over-matches (`git clean -n`, `.env.example`) are
  accepted as asks. `trust-and-approval.md`'s owner-run list omits `recover`; L corrects it.
  `security-reviewer` over D and E (probes in a scratch copy): one Medium, four Low, no bypass of
  `translate`'s own rendering and no non-`PlanError` crash on any accepted layout (a mutation fuzz
  of every layout node). Fixed, with tests (suite 1418): the agent-override check is now a strict
  parse (complete front matter, plain `key: value` lines only, no carriage return, the tools key
  exactly once, a value that is a comma list of tool names the layout defines, quotes balanced), so
  `tools: null`, `~`, `[]`, `*`, a comment, a duplicate, an unclosed fence and a `tools:` line
  inside a quoted value are refused; a layout's permission keys must be `<key>.deny` and
  `<key>.ask` with one `<key>` and none named `allow`, and no two tool classes may share a rule
  name or one named `allow`; a path rule starting with `~` but not `~/` is refused. Not done:
  the drift test still reads the AST (the reviewer's alternative, a single route table in
  `cli.py` that the test reads, is better and is a change to `cli.py` for H); field-name targets
  of a layout are not allowlisted; skill and command overrides are not inspected; the caller must
  pass a resolved `store_root`. G must pin the Claude template names (`Bash`, `Edit`, `Read`) in
  its own test, since the validator now only requires them to be distinct. The fix has not been
  re-reviewed by a second `security-reviewer`.
  Second `security-reviewer` pass, on the fixes only: one High, two Medium. The High: the
  line-by-line `tools` check was fooled by a multi-line quoted or flow value (`description: "x` /
  `tools: Read` / `model: y"`) or a value ending in `---`, which YAML reads as one string with no
  `tools` key (tested against PyYAML, not Claude). Fixed (suite 1423): each value must be a complete
  double-quoted JSON string without `---`, or a plain scalar with no leading indicator and no
  `---`, ` #`, `: ` or trailing colon; every key must be one the layout maps (so `hooks`,
  `allowed-tools`, `mcpServers` are refused); and the validator now allows one rule name per tool
  class (`Bash`, `Read`, `Edit`, `WebFetch`, compared with case) and only the `permissions`
  top-level key. Tests: the three multi-line shapes, 15 swallowing openings, unmapped keys, and the
  rule-name and key tables. Residual: the override check is still an approximation of YAML, not a
  parser; the robust alternative is to stop accepting hand-written agent front matter and render it
  from structured fields. The second round of fixes has not had a third review.
  Third `security-reviewer` pass (PyYAML as the oracle): one High, one Medium, three Low. The High:
  U+2028, U+2029 and U+0085 are line breaks to a YAML 1.1 reader but not to `split("\n")`, so a
  value could smuggle a second `tools:` key that wins. Fixed (suite 1428): every front-matter line
  must be printable ASCII (no tab, no control character); a repeated key is refused; a plain value
  must match a conservative pattern and not read as a number, boolean or null; the tools value must
  match a strict list pattern and each name must be in the layout's table exactly (no `strip`).
  The layout validator now also pins the agent `tools` field to `tools`, restricts each neutral
  tool to its own harness names (`read` cannot grant `Bash`) and pins the settings path to
  `.claude/settings.local.json`. Mutation check: without the ASCII guard the quoted-value test
  fails. The reviewer's verdict: a regex approximation of YAML is not acceptable as the only gate;
  the robust change is to render an override's agent front matter from structured fields. Not
  done; recorded for the owner. Reachability against Claude's own parser was not tested.
- **F** (`cda2248`): `Writer.add_exclude(entries)` and `exclude_line(entry)` in
  `workbench/projectfs.py`, `workbench/localmanifest.py` (new), `tests/test_exclude.py` (29 tests)
  and `tests/test_localmanifest.py` (20); suite 1477, 1 skipped, `-W error`. `add_exclude` writes
  each entry as the anchored literal line `/<entry>` (a trailing `/` marks a directory), refuses an
  entry with a glob character, space, `#`, `!`, backslash, colon, a `.`/`..`/empty segment or any
  `.git` component (so it can only name a path inside the project), and takes no path: it opens
  `.git` (a gitfile, link or missing `.git` is a conflict, with a clear message for the gitfile),
  `info` (made when missing) and `exclude` with no-follow descriptors, requires a regular file
  with one link, reads it bounded, and appends only the lines not already there byte for byte. The
  owner's lines are kept byte for byte and the inode is the same; a missing final newline is
  added; an empty list touches nothing. `localmanifest` is canonical JSON (`files`, `format`,
  `harness`, `module_version`, `source`, `tree`, `workbench`; files sorted by path, 2048 at most,
  1 MiB), read back only if byte-identical to the serializer's output; `write` creates
  `.workbench/local/harness.json` exclusively and `read` refuses a link or a non-canonical file. It
  refuses any key a committed manifest holds that this one does not (no seed) and a file path under
  `.workbench/local`. Sixteen mutation checks (each guard removed in a scratch copy) all fail a
  test. Limits: the append is not atomic against a concurrent writer of the same file; a case
  variant of an entry is a different line (git's `core.ignorecase` is not read); the module
  version and source are shape-checked only.
  `workflow-reviewer`: no Critical or High; its experiments were blocked, so findings are from
  reading. Fixed, with tests (suite 1478): a local-manifest file path equal to `.workbench/local`
  or under it is refused with case folded (a case-insensitive filesystem aliases it); a CRLF
  owner file's lines are compared without the trailing `\r`, so a rerun adds nothing. Recorded as
  limits, not fixed: an entry already present is skipped even if a later owner `!` line re-includes
  the path (the owner's own negation wins); a write that fails part-way (ENOSPC) can leave an
  unterminated fragment, which a rerun separates with a newline.
- **G** (`38deb76`): `packages/workbench/package.json` and `packages/workbench/claude/
  module.json` (type `harness`; the layout of `tests/test_layout.CLAUDE` plus one note), the two
  shipped records written by `release-approvals` under `workbench/shipped_approvals/packages/`
  (package and module; approver `workbench-release`, fixed time), and `tests/test_claude_module.py`
  (15 tests; suite 1493, 1 skipped, `-W error`). `verify packages/workbench --select claude` passes
  and is first-party; before `release-approvals` it is refused for its unprefixed capabilities, as
  designed. **Deviation from the plan's wording:** the module provides five capabilities, not six:
  `instructions`, `skills`, `agents`, `commands`, `permissions`. `hooks` is not provided because
  the layout says `hooks: none` and nothing renders hooks yet (non-goal); providing it would let an
  item that `needs` hooks install without any. `code-work-module` adds it with the rendering.
  Tests: records match the current hashes; a changed description, a changed layout and an added
  file each make the copy third-party again; the layout equals the verified one; the rule
  templates are pinned to `Bash(...)`, `Read(...)`, `Edit(...)` with `//` and never `Write(`; the
  rendered permissions use Claude's syntax; the approval request shows the harness-risk flag, the
  need for its own approval and the layout leaves. **Claude's own parser** (Claude Code, haiku,
  scratch project outside the repo, rendered by `translate` with this layout): the agent written
  with quoted `name`, `description`, `tools: "Glob, Grep, Read"` loaded as `reviewer` and had
  `Read`, `Glob`, `Grep` and no `Bash`; a command with quoted `name`, `description` and
  `argument-hint` loaded and substituted `$ARGUMENTS` (`/echoer zebra42` answered `GOT:zebra42`).
  Not probed: a skill's quoted fields beyond the skill being listed, and an override-supplied
  unquoted form. `docs/development.md` still says "none yet" for first-party packages; L fixes it.
  `workflow-reviewer`: no Critical, High or Medium; the shipped records, the first-party path and
  the layout against the spec were found sound (the records by reading and by test; no mutation run
  by the reviewer). Four Low. Fixed, with tests (18 in the file; suite 1496): the rendering test now
  passes the module's own `provides`; the tools table and the rendered agent and command front
  matter are pinned literally, not only against the shared `CLAUDE` constant; an item that needs
  `hooks` is shown to be skipped. Left for L: `harness-modules.md` still says Claude "provides all
  six capabilities", and `development.md` says "none yet"; both must say five, with `hooks`
  joining when `code-work-module` renders hooks. The owner-run protections come from `rules.py`,
  not from `module.json`, and E's tests cover that list.
- **H** (`837037a`): `workbench/attach.py` (new) and the `attach` route in `cli.py`;
  `Writer.check_exclude(entries)` in `projectfs.py` (a read-only look at `.git`, `.git/info` and
  `.git/info/exclude` with no-follow descriptors, so a fault there is found before any file is
  written); `harnessplan.render_root(layout)` (the `@AGENTS.md` pointer only, Decision 3);
  `rules.NOT_YET_ROUTED` is now empty. Built like `upgrade.py`: `parse`, a read-only `prepare`,
  then `apply`. `prepare` refuses, in this order: not an existing project; a clone that already
  records a harness (any), or a local manifest that is not canonical; a project not as last
  acknowledged on this machine (as `upgrade`); a harness package that is neither recorded nor
  given; a harness module the package does not declare, or one the manifest records as an
  ordinary module; a verification failure; a recorded package or module that is not the lock's
  (tree and declaration hashes; the message names `wb upgrade`); a module not approved on this
  machine, the harness included; neutral trees, overrides or exclusions that two modules both
  supply; a translation or layout failure; a path in `.git` or `.workbench`, a collision, or more
  than 16 MiB; a home or store path a rule cannot name; a local manifest that cannot be written
  (checked before the first write); and every conflict, all listed together: a path that exists
  with other bytes, a link or a non-regular file anywhere on the way, and an exclude file that is a
  link, a directory, a fifo or has two links. A path that already holds exactly the planned bytes
  is left and reported, which is what makes a rerun work (Decision 2). A settings file with other
  bytes is Decision 1: refused, with the entries attach would have written printed below the
  refusal and the instruction to move the file aside. `apply` rechecks the held target, adds the exclude lines, creates the
  files, and writes the local manifest last (see the review below for why the lines come first). A failure part-way exits 3,
  lists what was and was not written, and says the project is complete and `wb attach` finishes it.
  Home for the rendered rules is the account database's, not `$HOME` (`attach.default_home`); only
  tests can override it. **No fetch at all:** the recorded packages come from the cache or
  `--package`, as for `upgrade`, and the harness package from `--package`; a source the owner has
  not approved is never contacted, which is stricter than the spec's "fetched at the recorded
  commit if approved". The harness name for `harness/<name>/` overrides is the harness module's
  name. A module's own rule list has no file location yet (the contract reads only skills, agents
  and commands under `harness/neutral/`), so the module rules passed to `render_permissions` are
  empty: the floor, the guarded store and the owner-run commands are always rendered. The first-party
  `claude` module is attached in the tests with the recorded package given by `--package <dir>`.
  Tests: `tests/test_attach.py` (76), `Check` in `tests/test_exclude.py` (13), `Root` in
  `tests/test_harnessplan.py` (4); suite 1588 passing, 1 skipped. Mutation check: 30 mutants of the
  new guards, all killed after six tests were added for the survivors (a manifest that records a
  harness, packages that changed while read, a package changed outside every recorded module, a
  forged module hash, an item that needs `hooks`, a harness without `permissions`). A test with a
  real `git init` under an isolated `HOME` and `GIT_CONFIG_GLOBAL=/dev/null` shows every written
  path ignored by `.git/info/exclude` and none tracked. `docs/development.md` and the specs are L's.
  `workflow-reviewer` of H (from reading and one test run): no Critical or High. Medium, fixed:
  the plan's step order (files, then exclude lines) left a window in which a failure after the
  files and before the exclude lines exits 3 with files git does not ignore, and a `git add -A`
  before the rerun would commit them; the lines now come first (a departure from the step's
  wording, for the owner to note), with a test that a failing `add_exclude` leaves no harness file.
  Low, fixed: the failure text now says a file being written when the failure came may be
  incomplete and must be removed by hand, since attach does not overwrite a file with other bytes;
  an interrupt while printing the success report no longer prints "cancelled". Low, recorded:
  a path holding exactly the planned bytes counts as kept even if git tracks it, and a path tracked
  but missing from the tree is created and shows as modified (attach runs no git; `check`, J and K,
  reports a recorded file that git tracks); a kept file is not re-read at apply, so the local
  manifest can name a hash that changed in between (scratch, no authority); an interrupt between
  `prepare` and the writer is reported as exit 3. Test gaps noted, not filled: the local manifest
  under a real `git` (it relies on the committed `.workbench/.gitignore`), a hard-linked harness
  path, hostile control characters in a module's report text, and a partial file on rerun.
- **I** (`d66b6d7`): `wb install` attaches as its last step. The code `attach` used to
  build the harness files is now `workbench/harnessstage.py` (`stage` returns the files, the
  exclude lines and the local manifest; `inputs`, `check_paths` and the override and exclusion
  readers moved with it), and `workbench/refusal.py` holds the one `Refused` class (with the
  `after` lines), so `preview`, `attach` and `harnessstage` need no import cycle. `preview.prepare`
  stages the harness with the selection's only harness module and passes it to `installplan.build`;
  the plan's `harness` field is not an action (the marker's record and the write loop are
  untouched) but its files, modes, sizes, hashes, exclude lines and the local manifest's hash are
  in the digest. The preview replaces the "not attached" line with the harness section: each
  file, the exclude lines, the local manifest, the settings warning, the permission-less warning
  and the translation's warnings. The path list checked by `safefs.check_tree_paths` includes the
  harness paths, so a module that writes `CLAUDE.md` is refused at the preview. After the write
  loop has removed the marker, `install._attach` calls `attach.apply` on the same writer and
  prints attach's report; a failure (an error or an interrupt) prints `failed:`, the paths this
  attach wrote and did not write, "the install is complete", and `wb attach --harness
  <package>/<module>` with the `--package` hint, and exits 3. The unfinished-write record is not
  extended. `home` (the directory the rules name) is a test-only parameter through `cli.main`,
  `install.run`, `preview.run` and `preview.prepare`. Existing tests changed: two assertions of
  the removed text (`test_install`, `test_installplan`), the expected tree in
  `test_install_writes_expected_tree_modes_classes_and_manifest` (it now includes the local
  manifest), and the reference trees of `test_marker_record` and `test_recover`, which skip
  `.workbench/local/harness.json` because the marker does not list it and the recovered install
  has not been attached. The permission-less warning is shown in the plan text, not on standard
  error, so the existing install, preview and upgrade tests see no new stderr. New:
  `tests/test_install_attach.py` (16). Mutation check: 16 mutants of the new guards; 15 killed,
  one survivor removed (a guard for more than one harness module that `verify` already refuses).
  Suite 1605 passing, 1 skipped. `docs/development.md` describes the attach step; the specs are
  L's. The recorded hand run of an install into an empty directory and a `claude` start was not
  done (it needs the owner's allowance for a Claude session).
  `workflow-reviewer` of I (from reading and 125 tests): no Critical or High. Medium, fixed: an
  install into a lone `.git` whose `.git/info/exclude` attach cannot use (a link, two links,
  oversized) was found only after the install was written; `preview.prepare` now looks at it with
  `Writer.check_exclude` for a `new-git` target, so the preview and the install refuse before the
  digest is typed (test with a symlinked exclude file). Low, fixed: an interrupt while the install's
  own report is printed no longer ends in "cancelled: nothing was written"; the attach still runs.
  Test added for a case-variant collision (`claude.md` against `CLAUDE.md`). Low, recorded: the
  end-of-run output does not repeat the staged warnings (the owner saw them in the plan); the digest
  test does not change a file's mode or the settings path on their own; the `--package` hint in the
  failure text is generic.
- **J** (`3d7e5eb`): `wb check` for the harness files, `workbench/check.py`, routed in
  `cli.py` and classified agent-safe in `rules.AGENT_SAFE`. It opens the target without following
  links, requires an existing project, and reads only through the no-follow `Writer`
  (`read_file`, `list_dir`); `list_dir` now accepts the empty string for the project directory.
  Reports: "none attached" (valid, exit 0); top-level names of a known harness other than the
  attached one (`problem:`, or `warning:` when none is attached, so an owner's own `.claude` does
  not fail a clone); a recorded file that is missing, differs, or cannot be read (a link, a
  linked directory); files not recorded under the directories attach generates into (a link is
  listed, never followed). The scratch-record statement is printed whenever a harness is attached.
  A damaged local manifest is a `problem:`. Findings go to standard error with `problem:` /
  `warning:`, the summary to standard output, at most 40 findings of each kind are listed; exit 1
  only for a problem. Known limits, recorded: the table of other harnesses' top-level names and the
  stray directories lives in `check.py` (`HARNESSES`) and covers only `claude`, `opencode` and
  `codex`; a harness not in it has no stray scan and its files are not recognised in another clone;
  the committed manifest is not read, so a damaged or uncommitted one is K's report; the stray
  scan stops after 5000 entries or 8 levels and says so. `tests/test_check.py` (22). Mutation
  check: 10 mutants, 10 killed. Suite 1629 passing, 1 skipped.
  `workflow-reviewer` of J (from reading and 17 tests): no Critical or High. Medium, fixed: files
  directly under `.claude/` (a hook, rules) were never looked at; they now give a `warning:` (not a
  problem, since the harness or owner may keep files there; `settings.json` is allowed). Low, fixed:
  the unreadable-directory text is bounded; "1 problems" grammar. Tests added: hostile names,
  entry and depth bounds, a recorded path below a linked directory, an unknown harness name, the
  hooks warning. Low, recorded: a directory is listed in full before the entry budget applies
  (`list_dir` has no limit), so a clone with a huge `.claude/commands` makes `check` slow; a
  hostile local manifest can force up to 2048 bounded reads; the scanned directories are a table,
  not derived from the module's layout; empty stray directories are not reported.
- **K** (`762e660`): `wb check` also reports what git tracks, in `check.py` with two new
  modules. **Git is never run.** Planned alternative considered and not taken: a private git
  directory; reading the index directly needs no program, no configuration and no copy, so the
  hostile-configuration risk does not arise (the plan allowed this: "read the index format directly
  and record why"). `workbench/gitindex.py` parses `.git/index` (versions 2, 3, 4; SHA-1 or SHA-256,
  told apart by the trailing checksum so the configuration is not read; optional extensions
  skipped; a required one such as a split or sparse index is refused; at most 16 MiB, the shared
  reader's limit, and 1,000,000 entries; every length checked against the bytes), read through a new
  no-follow `Writer.git_bytes`. `workbench/pointers.py` finds links, reference definitions,
  `href`/`src` and `@path` imports in Markdown outside code. Reports: tracked files under any known
  harness root, `.debug/` or `.workbench/local/` (compared without case) are problems; tracked
  Markdown that points to a path git does not track, where that path exists or is scratch/harness
  output, or points outside the project, are problems; a tracked symbolic link is a warning (its
  target is not read); a module-owned file edited or missing, or a slot block edited, against the
  committed manifest is a problem, a seeded file may change, and recorded files not yet tracked are
  one warning; the manifest line says tracked, not tracked ("not committed") or none, and an
  uncommitted manifest is not a problem; a damaged or unreadable index is a problem and the other
  checks still run. Limits, recorded: "tracked" means in the index, so a staged file counts as
  committed; only Markdown is scanned (manifests and `.gitignore` carry no links); a link to a
  missing ordinary path is not flagged; document, byte and lookup bounds are 5000, 64 MiB and 5000
  and say so when passed; comparing files with the manifest reads the working tree, not git's
  objects. `tests/test_check.py` now builds a real git repository (22 earlier tests unchanged in
  intent; 20 new), `tests/test_gitindex.py` (11, real git for versions 2 to 4, SHA-256, a split
  index, a submodule entry, truncation at every length, and random corruption with the checksum
  repaired), `tests/test_pointers.py` (9, including hostile text in linear time; a quadratic fence
  pattern was found and fixed). The hostile-configuration test sets `core.fsmonitor`, `hooksPath`,
  `sshCommand`, `editor`, `include.path`, a filter and `diff.external` in `.git/config`, forbids any
  process start, and checks nothing ran and `.git/index` is byte-identical. Mutation check: 25
  mutants, 25 killed (after adding bound tests for the first run's survivors; one mutant of a
  limit parameter was dropped with the parameter). Suite 1671 passing, 1 skipped.
  `workflow-reviewer` of K (from reading and 64 tests): no Critical or High. Medium, fixed, both
  reproduced first: a hostile index with one long path took quadratic time (80,000 path parts: 3
  s and growing) and a version 4 index could grow each path by a byte per entry; paths are now
  limited to 4096 bytes and 64 MiB in all. The `](<` form in the Markdown patterns rescanned its
  line each time (80,000 repeats: 55 s); every bracketed form is now bounded to 2048 characters.
  Tests added for both, with the unterminated forms in the linear-time test. Low, fixed: a tracked
  document that cannot be read (a path the reader refuses, as a hostile index can name) is now
  one `problem:` instead of being skipped silently; the manifest comparison says it reads the
  working tree. Low, recorded: `@/...` and `@~/...` in prose are reported as outside the project;
  a link whose case differs from the file is not flagged on a case-insensitive filesystem; a
  version 4 index out of sorted order and unknown modes are accepted; an intent-to-add entry counts
  as tracked. Suite 1673 passing, 1 skipped, re-run before the commit.
- **Security pass before L** (adversarial `security-reviewer`, 2026-10-21, 40 tool calls, scratch
  copy only; its experiments are in the session scratchpad and not retained): no Critical or High.
  It found no way to widen agent permissions, write outside the project, follow a symlink or run
  code. Verified by experiment: a `.claude` symlink swapped in after preflight and before the first
  write, and a `.git/info` symlink swapped in, both stop with exit 3 and write nothing through the
  link; line injection into the exclude primitive (newline, CR, NUL, U+2028, U+202E, U+0085, `..`,
  `.git` in any case, `GIT~1`) is refused; no input produced an `allow` entry or altered the
  settings JSON; every owner-run command is denied in all five spellings and `wb preview` is not;
  hostile index inputs (bad checksum, an extension length of 0xffffffff, a required extension) are
  refused. Medium, fixed: the `](<` and `[id]: <` forms were linear but slow, about 4 µs per byte,
  so a 16 MiB Markdown file would take about a minute. The angle-bracket target is now bounded to
  256 characters and the total Markdown budget is 4 MiB (was 64 MiB); the worst case of 4 MiB of
  `](<` now takes about 2.6 s, and the budget message is the existing "not all were looked at".
  Low, recorded and not changed: a committed `.gitignore` can re-include a path with `!`, since
  `.git/info/exclude` has the lowest precedence, and `check` flags such a file once tracked; the
  rendered rules do not deny edits to `.claude/settings.local.json` or `.git/info/exclude`
  themselves (a Bash deny is documented as best effort, and an edit is prompted by Claude); an
  exclude file that already holds a later `!` line defeats an exclude line that is present; files
  are written in path order, so agents and commands can exist for a moment before the deny rules
  until a failed attach is rerun; `exclude_line` accepts `-x` and `K` (the Kelvin sign), both
  harmless. Not run, for the owner to decide before release: a fake-`git` recorder against a
  hostile `.git/config` through the CLI (K's own test patches process starts instead), a version 4
  varint fuzz, a symlinked `.workbench/local` and `.git/index` through the CLI, case variants on
  APFS, and the install exit-3 path. `test_a_split_index_is_refused` failed once and passed on
  every rerun; it asserts "split index" in a message that sometimes says "split or sparse index".
