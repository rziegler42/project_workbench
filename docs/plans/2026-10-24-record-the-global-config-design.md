# Record the global-configuration design in the roadmap, decisions and specs

Status: In Progress
Created: 2026-10-24
Candidate: none (direction-setting documents that precede `global-config-migration` and `self-hosting`; no roadmap candidate names it)
Specs: harness-modules, superpowers-ports

## Goal

The owner's `~/.claude` (agents, skills, hooks, helpers, `settings.json`, `CLAUDE.md`) holds work the design has not accounted
for, and the owner's working vision for the end state is not written anywhere tracked. Two candidates, `global-config-migration`
and `self-hosting`, assume that list is complete and that the old repositories are a source to carry over. The owner has said
both assumptions are wrong: the old system is lessons learned, not authority, and the end design is still being worked out.

When this plan is done:

- the roadmap shows what has been built since 2026-10-22, no longer treats the old repositories as a source to port, and
  names the candidates a bounded first-pass inventory turned up, so `global-config-migration` and `self-hosting` depend on
  a known list and not on none. The inventory is not claimed complete: completing it, by a line-by-line comparison of the
  global files, is the first step of `global-config-migration`;
- three decision records are written as `Proposed` for the owner to accept, reject or defer: what a project guarantees under
  any global setup, how an elevated agent is confined, and whether the installer may read the global configuration;
- two specs state what was found true on 2026-10-24, with the version, the method and the limits;
- nothing else changes: no code, no package, no approval.

## Scope

- The roadmap `docs/roadmaps/workbench-v1.md` (increment A).
- Three decision records in `docs/decisions/`, all `Proposed` (increment B).
- `docs/specs/harness-modules.md` (the evidence section) and `docs/specs/superpowers-ports.md` (increment C).

## Non-goals

- Accepting a decision, or building anything a decision proposes. Accepting is the owner's act; each built candidate has its
  own plan.
- Editing a spec to describe an unbuilt design. A spec says what is true now; a design that is not built lives in the roadmap
  and in a `Proposed` decision, and its spec is written with the plan that builds it.
- Any change to a package, so no shipped approval goes stale and no `release-approvals` is needed.
- The `mempalace` follow-up (project scoping of a search, the wording "a memory", the order against built-in memory). That
  edits a module and stales its approval; it is a candidate, not part of this plan.
- Changes to the owner's `~/.claude`, `claude_global_config` or `claude_project_template`. The superpowers references in
  the owner's `CLAUDE.md` and agent files are the owner's to change; this plan only records them.
- Choosing a name for the knowledge base, or deciding whether `graphify` is built.

## Assumptions and constraints

- The owner's end-state vision is a working position and may change: the owner maintains `~/.claude`, the project maintains
  `<project>/.claude`, the project's settings give a consistent workbench experience whatever the global settings are, and the
  old repositories go away once the workbench can run without them. Wording in the roadmap and the decisions says so.
- Nothing tracked may depend on untracked content. The owner's design notes and the trial's scratch files are untracked, so
  every fact a document relies on is written into that document. The facts to record, from a trial run on 2026-10-24 with
  Claude Code 2.1.310 (`claude -p`, a scratch `CLAUDE_CONFIG_DIR` holding a deliberately noisy global configuration, and the
  a scratch project with 122 `deny` and 58 `ask` rules rendered by the Claude harness), are:
  1. A project `deny` held against a global `allow: Bash(*)`, and held under a global `defaultMode` of `auto`. The command
     was denied and did not run.
  2. A project `ask` held against the same global `allow`, under `auto`, and under `bypassPermissions`: the command did not
     run (`-p` mode denies an `ask` rather than prompting, so interactive behaviour is not shown).
  3. A global `PreToolUse` hook ran for commands the project denied and for commands it asked on.
  4. A global skill with the same name as a project skill was the one loaded (two runs).
  5. A project agent with the same name as a global agent was the one loaded (one run).
  6. A hook declared in a project agent's frontmatter ran, and a hook that exited 2 blocked the agent's `Read` (one run each,
     the `Read` tool only).
  7. The owner's global `CLAUDE.md` and the project's instructions were both loaded, and the model said the files do not
     say which wins. With `CLAUDE_CONFIG_DIR` set, the real `~/.claude/CLAUDE.md` was loaded as well as the scratch one
     (cause not established); the real `settings.json` was not (a control command the real settings ask on ran).
  8. Not tested: a project `deny` under global `bypassPermissions` (not run), interactive mode against `-p`, the edit-gate
     hook (the scratch project had no `code-work`), and any agent tool other than `Read`.
- The inventory behind the roadmap additions was read on 2026-10-24 from the owner's global Claude configuration (agents,
  skills, the headers of hook scripts, `settings.json`, `CLAUDE.md`) and from the owner's two earlier repositories. The hook
  scripts, `settings.json` and `CLAUDE.md` were not compared line by line, and the reference files of `freecad-scripts` and
  `graphify-workflow` were not read. It is a first pass and the plan says so wherever it relies on it.
- Provenance. Those sources and the trial's scratch files are untracked and outside this repository, so no tracked text
  cites one by path or depends on its content (`AGENTS.md`, "Working agreement"; the tracked-pointer rule). The trial facts
  above are first-hand observations, and a record states each with its date, tool version, method, run count and limits; it
  does not point at the scratch files. A statement about what the old configuration contains is written as an observation
  of 2026-10-24 and carries no filesystem path. Where a later plan needs a source, it cites it by URL, retrieval date and
  content hash.
- graphify: skipped, not installed in this repository. The scope was verified by reading `docs/roadmaps/workbench-v1.md`,
  the completed plans' `Candidate:` lines, `packages/workbench/`, `docs/specs/harness-modules.md`,
  `docs/specs/superpowers-ports.md`, `docs/specs/knowledge-tools.md` and `docs/decisions/` on 2026-10-24.
- Roadmap candidates stay at plan-boundary level: each states an outcome, dependencies, a boundary and a promotion trigger,
  with no file lists or commands.

## Choices (made by me, for the owner to accept or overturn)

1. **Specs only for what is true today.** The agent-confinement design and the global-settings check are not built, so they
   go into decisions and candidates and not into `harness-modules.md` or `repository-boundary.md`.
2. **The security reviewer ships with its skill in one optional module** (`security-review-module`), not in `code-work`. The
   agent needs extra power, and a separate module lets the owner decline both at approval. `code-work` names no such
   module; it would use any module that provides the capability.
3. **`graphify-module` loses the words "ported" and "keeps the plan receipt".** The discovery gate and its receipt were
   dropped on 2026-10-19 and `code-work.md` says there is no gate; the candidate keeps `graphify` for structure and impact
   questions, as the `mempalace` policy block routes them. Whether it is built stays open.
4. **Seven new candidates**, listed in increment A. They are the smallest split I could find that keeps each candidate
   buildable by one plan; the owner may merge or drop any.
5. **The global-settings check is a `Proposed` decision, not a candidate yet.** Its premise (a conflict worth reporting) is
   partly shown by the trial (a global skill shadows a project skill) and partly unverified.

## Completion criteria

1. The roadmap's "Current state" describes every completed plan since 2026-10-22, each bullet drawn from that plan's own
   result, and `Updated:` is 2026-10-24.
2. The roadmap names the seven new candidates with outcome, dependencies, boundary and promotion trigger; every candidate in
   "Suggested order" has a section and every section is in the order; no dependency names a slug that does not exist.
3. The wording conflicts are gone: the `claude_global_config` mirror sentence, "ported" in `remaining-modules-rename` and
   `graphify-module`, the plan receipt in `graphify-module`, and the assumption that `knowledge-base-package` and
   `researcher-fetch-tool` inherit the old items.
4. Three decision records exist with `Status: Proposed`, each following `docs/decisions/README.md`, citing no untracked path.
5. `harness-modules.md` states the trial facts of the Assumptions list (items 1 to 8), with the version, the date, the
   method, the run counts and the untested cases. `superpowers-ports.md` records which of the owner's agent definitions and
   routing lines name the plugin, with its own date, the scope of what was compared (agent `skills:` lists and the routing
   text; not a line-by-line audit) and the workbench skill that replaces each.
6. `doccheck`, `refcheck` and `git diff --check` print nothing, and no file outside `docs/` changed.

## Increments

### Increment A — refresh the roadmap

**Outcome:** the roadmap is current, free of the wording conflicts, and lists the candidates that `global-config-migration`
and `self-hosting` depend on.

**Dependencies:** none.

**Affected areas:** `docs/roadmaps/workbench-v1.md`.

**Steps:**

1. Read the `Result` or completion note of each plan that "Current state" does not name, found by searching the roadmap for
   each plan stem on 2026-10-24: `2026-10-23-increment-loop-and-review-skills`, `2026-10-23-push-checkpoint`,
   `2026-10-23-compaction-guidance`, `2026-10-23-review-engine`, `2026-10-23-delegated-approval`,
   `2026-10-23-port-superpowers`, `2026-10-23-gate-input-bound-only-under-way`, `2026-10-24-remote-runner-module`,
   `2026-10-24-owner-run-in-code` and `2026-10-24-mempalace-module`. `2026-10-22-code-work-commit` is not named by its stem
   either; check whether the `safe-git` bullet already covers it before adding one. Add one bullet each, no longer than the
   existing ones, stating only what that plan's result records, including its stated limits.
2. Rewrite the three conflicting passages: the `global-config-migration` boundary, `remaining-modules-rename` and
   `graphify-module` (choice 3), and the dependency wording of `knowledge-base-package` and `researcher-fetch-tool`. The
   `global-config-migration` text reflects the working vision (the owner keeps `~/.claude`; each global item moves only
   after a test or a recorded run shows a project behaves the same without it; no mirror to keep in step; the list of what
   stays global is the owner's), says it may change, and adds the superpowers dependencies as items to settle: the three
   agents' `skills:` lists, the routing in the owner's `CLAUDE.md`, the session-start rule, and the gaps recorded in
   `superpowers-ports.md`. It also makes the candidate's first step a line-by-line comparison of the global agents, skills,
   hooks, `settings.json` and `CLAUDE.md` against the specs and modules, recording what was and was not inspected and a
   disposition (move, redesign, drop, keep global) for every item found; the first-pass inventory of this plan is its
   starting point and not its end.
3. Add the new candidates, each with outcome, dependencies, boundary and promotion trigger:
   - `architecture-decisions-merge`: the rules of the owner's `architecture-decisions` skill that `draft-decision` lacks are
     added to `groundwork`; the workbench's dated names win on conflict. Edits a package.
   - `agent-confinement`: an agent declares its limits as data (write roots, allowed commands) and the installer enforces
     them with a per-agent hook, as it does the edit gate; the Claude layout declares the scratch path. Depends on the
     decision of increment B being accepted. Needs a spec change and an installer change.
   - `security-review-module`: the optional module holding the `security-review` skill and the security-reviewer agent,
     providing a capability of that name. Depends on `agent-confinement`.
   - `verilog-module`: `verilog-verilator-sim` and `verilog-sby-formal` as neutral skills, text only, rewritten in the
     workbench's words after a read of their content for accuracy; split by the rule of
     `2026-10-23-one-owner-per-skill-name`. Both skills are written for plain Verilog-2001 and say not to use
     SystemVerilog, so the module is named for the language. A VHDL or SystemVerilog module, if the owner writes either, is
     a separate candidate with its own tools and skills; this one does not widen to cover them.
   - `cad-modules`: a tool-neutral `cad` module and a FreeCAD module (`freecad-scripts` and its script), after the same
     read. Whether the FreeCAD MCP advice stays is open.
   - `global-settings-check`: an owner-run, read-only command that reports where a global setting may conflict with a
     project's. Depends on its decision being accepted; the roadmap states it may never be built.
   - `mempalace-scoping`: the module's skill and policy say a result from another project is background; "a memory"
     becomes "the palace"; the order against built-in memory is stated. Edits a package.
4. Update "Suggested order" and the dependency lists of `global-config-migration` and `self-hosting` so each global item's
   replacement is a dependency; update `Updated:`.
5. Check: every `###` candidate heading appears once in "Suggested order"; every slug in a `Dependencies:` line has a
   section; the new candidates carry no file lists or commands. Run `doccheck`, `refcheck`, `git diff --check`.

**Verification:** the checks of step 5 print nothing; a read of the diff shows no statement about a plan that its result does
not record.

**Evidence of completion:** the commit, and the slug check's result in the Result.

### Increment B — three decision records, `Proposed`

**Outcome:** the three durable choices are written for the owner to decide.

**Dependencies:** A (the records name the new candidates).

**Affected areas:** `docs/decisions/2026-10-24-project-guarantees-a-floor.md`,
`docs/decisions/2026-10-24-declared-agent-confinement.md`,
`docs/decisions/2026-10-24-installer-reads-global-settings-on-request.md`, and the index in `docs/decisions/README.md`.

**Steps:**

1. Write each with the template of `docs/decisions/README.md` and `Status: Proposed`:
   - **A project guarantees a floor, not identical behaviour.** The project's `deny` and `ask` rules, edit gate, owner-run
     refusals and hard stops are the guarantee; convenience may vary with the owner's global settings; guarantees that matter
     are enforced in the workbench's code and not only by rendered settings, because settings merge across levels; the
     workbench never writes a harness's global configuration. Evidence: items 1 to 7 of the Assumptions list. Consequences
     include that a global skill was observed to shadow a project skill of the same name, which the workbench cannot
     prevent, and that a global hook and the global instructions were observed to apply alongside the project's. The record
     states these as observations of one version and a few runs, and keeps what was not established as limits or open
     questions: why the global instruction file was loaded under a changed configuration directory, whether any setting
     can stop a global hook, interactive behaviour, and the untested cases. Related: `restrictive-only-permissions`,
     `one-owner-per-skill-name`.
   - **An agent's limits are declared and enforced by the installer.** The shape of the notes: no general shell for an
     elevated agent, declared write roots and allowed commands, one pinned execution command, a generic installer guard
     rendered as a per-agent hook, the Claude layout declaring the scratch path, one optional module holding the skill and
     the agent. Alternatives: a module-shipped guard script (rejected: shell-text parsing on every call), keeping the agent
     personal (rejected: a committed process may not depend on a personal agent), no confined agent at all. Consequences
     include the limit that a script the agent writes and runs is not confined, and the open questions (how a fixed-pattern
     command is matched, how the installer learns the scratch path, whether an interactive session asks for hook trust).
     Evidence: item 6.
   - **The installer may read the global configuration, read-only and on the owner's request.** It is a proposal to amend
     `repository-boundary.md`, which says the workbench "never reads, checks or requires" a harness's global configuration.
     It does not reverse the accepted `2026-10-19-guarded-store`, which rejected keeping approvals in a harness's global
     configuration because the workbench must not depend on one; the record says why a read-only report on the owner's
     request creates no such dependency (nothing is stored there, nothing is approved from it, and the workbench works
     with it absent). It lists both authorities in its related section. The installer's own code reads the configuration,
     never a module's; the command is owner-run and terminal-only; it prints names and paths and never values; it decides
     nothing and feeds no approval or `allow` rule; the harness module supplies the location and keys as data.
     Alternatives: no detection (rely on the floor), a module-run check (rejected: project code would read private
     configuration). Acceptance of the record and the amendment of `repository-boundary.md` are prerequisites for any plan
     that builds the command. States that it may be deferred until the trial's untested cases are run.
2. Add one row per record to the index in `docs/decisions/README.md` (stem, title, `Proposed`), after the existing rows.
3. Check that no new text names a path under `.debug/`, a scratch directory or a directory of an earlier repository (search
   the new files for `.debug`, `scratch`, `/tmp` and `claude_`), and that each record says what was run, with the version,
   the date and the run count (the provenance constraint of the Assumptions). `~/.claude` may appear as the name of the
   harness's global configuration directory, as the specs already use it, but no text cites its content as a source.
4. Run `doccheck`, `refcheck`, `git diff --check`.

**Verification:** the checks print nothing; each record has all of the README's sections; the index lists all three records
as `Proposed`; the search of step 3 finds nothing.

**Evidence of completion:** the commit. The owner's acceptance, rejection or deferral of each record is separate and not a
condition of this plan.

### Increment C — specs that state what is true today

**Outcome:** `harness-modules.md` and `superpowers-ports.md` carry the verified facts and no more.

**Dependencies:** none (independent of B).

**Affected areas:** `docs/specs/harness-modules.md` (the evidence section, where "Precedence between project and local files
is not verified" stands), `docs/specs/superpowers-ports.md`.

**Steps:**

1. `harness-modules.md`: add a dated subsection to the evidence, "Global against project settings (Claude Code 2.1.310,
   2026-10-24)", with items 1 to 8 of the Assumptions list as findings and limits, the method in two sentences, and the
   sentence that each result is one or two runs of a model-driven probe. Update the line that says project-against-local
   precedence is not verified only if the trial covered it; it did not, so it stays.
2. `superpowers-ports.md`: add a short section that the owner's agent definitions name plugin skills in their `skills:` lists
   (`implementer`, `workflow-reviewer`, `security-reviewer`) and that the owner's `CLAUDE.md` routes to the plugin, which
   stops working when the plugin is removed; the workbench skill that replaces each is named. Record in "How use was decided"
   that agent lists are evidence of use and that dropping an agent changes it.
3. Search the edited sections for the strings of increment B step 3; the findings are stated as observations with no
   path to untracked material.
4. Run `doccheck`, `refcheck`, `git diff --check`, and the module tests for `groundwork` (they read these documents' checks).

**Verification:** the checks print nothing; every statement in the `harness-modules.md` text traces to items 1 to 8 of the
Assumptions list, and every statement in the `superpowers-ports.md` text traces to the agent definitions and routing lines it
names, with the scope of the comparison stated.

**Evidence of completion:** the commit.

## Verification for the plan as a whole

`doccheck`, `refcheck` and `git diff --check` after each increment, the slug check of increment A, and `git diff --stat`
showing only files under `docs/`. No code changes, so the full suite is run once at the end, in the background, to show
nothing that reads these documents broke (it takes about 7 minutes).

## Risks and sensitive actions

- **The roadmap states a working vision as direction.** Mitigation: the wording says it is a working position that may
  change, and the owner reads the diff before the commit.
- **A `Proposed` decision is read as accepted.** Mitigation: the status line, and the plan states that accepting is the
  owner's act.
- **Evidence is thin.** One or two model-driven runs each, one version, `-p` mode. Mitigation: every fact is written with its
  run count and its untested cases; the decisions say what would change them.
- **Candidates multiply.** Seven are added. Mitigation: each is at plan-boundary level and the owner may drop any.
- Sensitive actions: none. No secret is recorded (the notes name paths only); no package changes; no commit or push without
  the owner's word.

## Review record

`ask-codex` plan review at medium effort, asked for by the owner on 2026-10-24: three rounds, which is the bound. Findings are
untrusted advice; each was checked against the repository before it was applied.

- Round 1 (3 major): the decision index in `docs/decisions/README.md` was missing from increment B (applied); the plan's
  tracked text depended on untracked paths without the required provenance (applied in part: the facts are first-hand
  observations, so the plan adds a provenance constraint and a path search and keeps no hashes); the goal claimed a
  complete inventory the plan could not verify (applied: the goal says first pass, and completing it is the first step of
  `global-config-migration`).
- Round 2 (1 major): criterion 5 asked `superpowers-ports.md` for the trial facts that increment C gives only to
  `harness-modules.md` (applied: the criterion and the verification are split by document).
- Round 3 (2 major): the first decision record said global hooks and instructions "always apply", beyond what one trial
  shows (applied: stated as observed, with the unestablished points kept as limits); the third record needed to say it
  amends `repository-boundary.md` and how it relates to `2026-10-19-guarded-store` (applied: the record lists both, states
  that it does not reverse the guarded-store decision because nothing is stored or approved from the read, and makes
  acceptance and the spec amendment prerequisites for building the command).

Nothing remains disputed. After round 3 the owner renamed the candidate `hdl-module` to `verilog-module` (the skills are for
plain Verilog-2001); that change was not reviewed. The review is not archived; archiving it is the owner's act (`ask-codex archive`), and the plan
stays `Proposed` until the owner approves it.

## Deferred work

- Building any candidate added here, each with its own plan.
- The cases the trial did not cover: a project `deny` under global `bypassPermissions`, interactive mode, the edit-gate hook
  and non-`Read` agent tools.
- `remote-runner.md` names the global `security-review` skill as advice. It is true today and changes when that skill moves.
- A neutral check that two modules' policy text does not contradict a global rule, which the workbench cannot see.
- The `CLAUDE.md` and agent-file edits for the superpowers removal, which are the owner's.

## Result

### Increment A (2026-10-24)

The roadmap `docs/roadmaps/workbench-v1.md` is refreshed.

- "Current state" gained ten bullets, one per plan the roadmap did not name by stem: `increment-loop-and-review-skills`,
  `push-checkpoint`, `compaction-guidance`, `gate-input-bound-only-under-way`, `review-engine`, `delegated-approval`,
  `port-superpowers`, `remote-runner-module`, `owner-run-in-code` and `mempalace-module`, each from that plan's own Result and
  limits, and an eleventh on the global configuration. `2026-10-22-code-work-commit` was not given a bullet: the
  `safe-git` bullet and the `code-work-commit` candidate already say its helper moved. One earlier sentence (`delegate` has no
  effect, nothing reads a cap) is now dated to when that plan closed.
- Wording conflicts removed: the mirror sentence of `global-config-migration` (replaced by "there is no mirror to keep in
  step"); "ported" in `graphify-module` and `remaining-modules-rename`; the plan receipt and the `code-work-plans` evidence
  dependency in `graphify-module`; the inheritance wording of `knowledge-base-package` and `researcher-fetch-tool`.
- Seven candidates added before `global-config-migration`: `architecture-decisions-merge`, `agent-confinement`,
  `security-review-module`, `verilog-module`, `cad-modules`, `global-settings-check` and `mempalace-scoping`.
  `global-config-migration` now states the working vision as provisional, makes the line-by-line comparison its first step,
  lists the superpowers dependencies as items to settle, and depends on the four candidates that supply a global item;
  `self-hosting` depends on the three that change a shipped module. `remaining-modules-rename` shrinks to the rename pass,
  because its other contents have candidates of their own (a consequence of the split, for the owner to accept).
- Verification as run: a script found 40 candidate sections and 40 slugs in "Suggested order", none missing from either and
  none repeated, and every dependency that names a candidate names a section; `doccheck`, `refcheck` and `git diff --check`
  print nothing. The review of the diff for statements a plan's result does not record was made by me and not by a reviewer.
- Limits: the bullets summarize long Results and were drawn from reading each plan's Result section, and the first 30 to 60
  lines of the longer ones; the review-engine increments between C and F, and the middle increments of the remote-runner and
  mempalace plans, were not read in full.

### Increment B (2026-10-24)

Three decision records are written, each `Status: Proposed`, and indexed in `docs/decisions/README.md`.

- `2026-10-24-project-guarantees-a-floor`: the floor (a project's `deny` and `ask` rules, edit gate, owner-run refusals and hard
  stops), no promise of identical behavior, guarantees that matter enforced in the workbench's code, and no writing of a
  harness's global configuration. Alternatives include the owner's first statement of the end state (reset the user level and
  supply everything from the project), rejected in favor of the split. Its Verification section holds the trial's seven
  findings with the version, date, method and run counts, and what was not tested.
- `2026-10-24-declared-agent-confinement`: declared limits as data, no general shell for an elevated agent, a generic installer
  guard rendered as a per-agent hook, the layout naming the temporary directory, and the skill and agent shipped together in
  an optional module. Open items recorded: the fixed command pattern, how the installer learns the session directory, hook
  trust in an interactive session, and that the rendered agent file is a harness file the project's own agent could edit.
- `2026-10-24-installer-reads-global-settings-on-request`: a proposal to amend `repository-boundary.md` and to leave
  `2026-10-19-guarded-store` unchanged, with the reason; owner-run, terminal-only, read-only, names and paths only; acceptance
  and the amendment come before any plan builds it; it may be deferred.
- Verification as run: a search of the three files for `.debug`, `scratch`, `/tmp` and `claude_` finds nothing; `doccheck`,
  `refcheck` and `git diff --check` print nothing; the index lists all three as `Proposed`. Nothing under `packages/`
  changed.
- Not done: the owner has not accepted, rejected or deferred any of the three, and none was reviewed by a second reviewer.
  The trial's untested cases are still untested.
