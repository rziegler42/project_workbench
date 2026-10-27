# A permission level for every command

Status: Proposed
Created: 2026-10-27
Candidate: none (an owner request that implements the accepted decision `2026-10-26-a-level-for-every-command`; no roadmap candidate names it)
Specs: command-permissions, trust-and-approval, installer-interface, harness-modules, code-work, module-boundary

## Goal

Every `wb` command and subcommand the owner can reasonably want to govern has a key in the personal settings, with a default that
matches what the command does today, and no key is limited to `block`. When the plan is done the owner can tighten any agent-safe
command, can let an agent run any installer command at `none` without a terminal, and sets every level in one table. The
specification `docs/specs/command-permissions.md` ("Planned: a level for every command") says so as built and its planned
acceptance criteria P1 to P6 pass, except where "Deferred work" says otherwise.

## Scope

- Keys for the agent-safe commands and subcommands, the one-action-one-key rule, and the drift test that fails when a routed
  command has no key (decision 1).
- Defaults from what a command does today: `none` for agent-safe commands, `block` for the rest (decision 2).
- The table as the single source of a level, and one vocabulary: `stop` and `delegate` as read-only aliases (decisions 5 and 6).
- Rendering a `deny` for an agent-safe key set to `block`.
- A shared way for an owner-run installer command to run at `none` without a terminal, with its log entry, and then each command
  that uses it: `install`, `adopt`, `upgrade`, `add`, `approve`, `pin`, `acknowledge`, `recover`, `release-approvals`, `attach`.
- `accept-decision` at `none`.
- The specs, `docs/development.md` and tests that say and check the above.

## Non-goals

- The compiled hard-stop floor (`floor.py`) and the hook entry points `gate`, `agent-gate` and `gate-command`: not keys.
- `ask` for any key other than `approve-plan`. Each needs its own preview digest; that is a second plan.
- `none` for an owner-run argument of a module command (`wb run mempalace init`, `review-engine reset` and the others). It needs the
  module's helper to skip its own terminal test, which is a change to the module contract and needs its own decision
  ("Deferred work").
- A master switch or profile that turns every protection off.
- Converging `AGENTS.md` with the base and the module blocks: a separate plan.
- Changing the neutral rule list, which still holds only `ask` and `deny` (`2026-10-19-restrictive-only-permissions`).

## Assumptions and constraints

- Increment I builds the decision `2026-10-27-command-gate-literal-arguments`, which is `Proposed` until the owner accepts it. It was
  found after F to H were built: relaxing a common-word key blocks every `wb run safe-git commit` whose subject or paths hold the word
  (`2026-10-27-command-gate-literal-arguments`, "Context").
- The decision `2026-10-26-a-level-for-every-command` and the spec are accepted and approved by the owner. Where this plan and
  either differs, they win.
- Increment E builds the decision `2026-10-27-command-gate-command-position`, which is `Proposed` until the owner accepts it. F to K
  need it, because the gate as it stands blocks every command that holds a common word such as `install` once its key is relaxed.
- Only `approve-plan` runs without a terminal today (`planapprovals.py`). Every other owner-run command refuses unless standard
  input and output are terminals, each with its own check (`install.py`, `upgrade.py`, `acknowledge.py`, `recover.py`,
  `approve.py`, `pins.py`), and several also read a typed confirmation. Running at `none` therefore changes each command, and the
  change is a decision about what replaces the typed confirmation: nothing, because `none` means no confirmation and no gate.
- `attach` is not terminal-gated; the harness denies it to the agent (`attach.py`). At `none` its change is only the removal of the
  `deny`.
- Code is the Python standard library only; checks are run with `python3 -B -W error tests/run_all.py`.
- A level of `ask` or `none` takes effect only through the rendering record, the live hashes of the harness settings files and the
  command gate (`command-permissions.md`, "Rendering"). A new `none` command path reads the same record.
- The code in `workbench/` is in the agent's write scope in this self-hosted repository (`command-permissions.md`, "Limits").
- Authorization, the guarded store and a permission boundary change here, so an increment that touches them stops for the owner
  before the next (see "Risks and sensitive actions").

## Completion criteria

1. Every command and subcommand `cli.py` routes has a key, except `gate`, `agent-gate` and `gate-command`, and a test fails when
   one has none (spec P1).
2. With no settings, every agent-safe key reads `none` and every other key reads `block` (P2).
3. A table entry sets a key's level in either direction whatever its checkpoint says, and a version 1 `stop` or `delegate` for a key
   the table does not mention reads as `block` or `delegated` with a note (P3).
4. Every key built by this plan accepts `block` and `none`; a level a key does not offer reads as `block` with a note (P4).
5. With every key built by this plan set to `none`, none of those commands refuses for want of a terminal or a harness `deny`, the
   floor still applies, and each run that changes something is logged (P5).
6. `accept-decision` set to `none` lets an agent accept a decision and at `block` it does not (P6).
7. The specs, `docs/development.md` and `wb settings` describe the built behavior, and `wb check` reports no problems.
8. The full suite passes with warnings as errors.

## Increments

### Increment A — Keys for the agent-safe commands and the drift test

**Outcome:** the registry has a key for every routed action except the three hook entry points; each action reaches one key;
agent-safe keys default to `none`; the settings reader and `wb settings` carry them; nothing is enforced yet.
**Dependencies:** none (this plan is approved).
**Affected areas:** `workbench/levels.py`, `workbench/rules.py`, `workbench/settings.py`, `workbench/settingscmd.py`,
`workbench/cli.py` (read only, for the routing list), `tests/test_levels.py`, `tests/test_settings.py`, `tests/test_settingscmd.py`,
`tests/test_cli.py`.
**Steps:**
1. Write the tests first: the keys `wb verify`, `wb preview install`, `wb preview adopt`, `wb preview upgrade`, `wb preview add`,
   `wb launch`, `wb check`, `wb plan-status` and `wb settings` exist; `wb run` and `wb preview` do not; `delegate-approve-plan` has
   no key; `wb run <command> <argument>` has a key for each declared argument, `block` if the argument is owner-run and `none`
   otherwise; an agent-safe key defaults to `none`; each owner-run key still defaults to `block`; no action reaches two keys; and a
   test fails when `cli.py` routes a command that is in neither the registry nor the three exceptions.
2. Add the agent-safe keys to the registry from `rules.AGENT_SAFE` minus the three exceptions and `delegate-approve-plan`, and the
   non-owner-run module arguments from the declarations; add the default `none` for them (`levels._DEFAULTS` or a successor).
   Subcommand keys follow the spelling in the spec.
3. Confirm the settings reader accepts, reports and defaults the new keys; `wb settings` prints them grouped by command.
4. Add `none` to what every new key offers; keep `block` for the rest until their increment.
**Verification:** `python3 -m unittest discover -s tests -p 'test_levels*.py'`, `-p 'test_settings*.py'` and `-p 'test_cli.py'`, then
`python3 -B -W error tests/run_all.py`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#A`.

### Increment B — The table is the single source of a level

**Outcome:** a table entry wins in either direction; `stop` and `delegate` are read-only aliases from a version 1 file; `wb settings`
prints only the four level names and notes a translated word.
**Dependencies:** A.
**Affected areas:** `workbench/settings.py`, `workbench/settingscmd.py`, `tests/test_settings.py`, `tests/test_settingscmd.py`,
`docs/specs/command-permissions.md`, `docs/specs/trust-and-approval.md`.
**Steps:**
1. Write the tests first: a checkpoint `stop` and a table entry `none` read `none`; a checkpoint `delegate` and a table entry `block`
   read `block`; with no table entry, `stop` reads `block` and `delegate` reads `delegated` with a note; the old rule "stricter of
   the two" no longer applies; a version 1 file is unchanged in effect; a damaged table still reads `block` for the whole table.
2. Replace the stricter-of rule in `effective` with table-wins and the fallback.
3. Print the translated-alias note in `wb settings`.
4. Correct the spec's "The levels", "The table" and "Reading rules" to the built behavior.
**Verification:** the settings tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#B`.

### Increment C — A `deny` for an agent-safe key set to `block`

**Outcome:** an owner who sets an agent-safe key to `block` has the harness deny that command to the agent; at `none` nothing is
rendered; the recording and the command gate treat the key like any other.
**Dependencies:** A, B.
**Affected areas:** `workbench/rules.py`, `workbench/rendering.py`, `workbench/harnessplan.py` if it names the rules,
`tests/test_rendering.py`, `tests/test_command_gate.py`, `docs/specs/command-permissions.md`, `docs/specs/harness-modules.md`.
**Steps:**
1. Write the tests first: an agent-safe key at `block` renders a `deny` in each `wb` spelling and the interpreter spellings; at
   `none` it renders none; the record lists the key as `deny` or `none`; a table changed after attach makes the key read `block`
   (the existing record rule); `wb check` still passes on a clone with the default table.
2. Render `deny` for the agent-safe keys read as `block`. Owner-run rendering is unchanged.
3. Check by test that a default table renders exactly what it rendered before this increment.
**Verification:** the rendering and gate tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#C`.

### Increment D — One way for an installer command to run at `none`

**Outcome:** a shared function lets an owner-run installer command decide, from the level it reads now, whether it may run
without a terminal, and writes its log attempt before the change and its outcome after; no command uses it yet. The part that needs
no knowledge of the rest of the workbench, "given a level and the terminals, may this run, and the log append", lives in the kit,
so that a module helper can use it later; the checks that need the rendering record stay in the installer.
**Dependencies:** B.
**Affected areas:** a new `workbench/wbkit/levels.py` (the pure part), a new `workbench/levelrun.py` (the installer part; names
for the builder to settle), `workbench/levels.py`, `workbench/levellog.py`, `workbench/planapprovals.py` (to reuse, not to change in
behavior), `tests/test_wbkit_levels.py`, `tests/test_levelrun.py`, `docs/specs/command-permissions.md`,
`docs/specs/module-boundary.md`.
**Steps:**
1. Write the tests first. For the kit part: given the level `block` it allows only when standard input and output are terminals;
   given `none` it allows; given an unknown, missing or unreadable level it falls back to the terminal test; it writes the attempt
   and outcome lines with the log's format and limits (one line, append, no read, refuses a link, a non-regular file and a second
   hard link); it imports only the standard library and the kit. For the installer part: at `block` the function refuses and the
   command's terminal test applies as now; at `none` it allows only while the rendering record, the live hashes and the gate hold
   (the same conditions `approve-plan` checks); an unreadable log or record refuses; a level the key does not offer reads `block`;
   an equal repeat that changes nothing writes no entry.
2. Build the kit part as an addition only: it changes no existing kit function and so does not raise `wbkit.API`; a test checks
   that the existing helpers still load against the kit.
3. Factor what `planapprovals.py` already does for `none` into the installer part, calling the kit part, with no change to
   `approve-plan`'s behavior; its existing tests must pass unchanged. Move the log's append call to the kit part only if its tests
   pass unchanged, and otherwise leave it in `levellog.py` and call the one from the other.
4. Document both parts in the spec's "Planned" section as built, and the new kit module in `module-boundary.md`'s list of what the
   kit holds.
**Verification:** `python3 -m unittest discover -s tests -p 'test_wbkit_levels.py'`, `-p 'test_levelrun.py'` and
`-p 'test_approve_levels.py'`, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#D`.
**Checkpoint (owner):** this increment changes authorization and the log. At its end the agent asks whether to run a security review
with an installed module that provides `security-review`, and does not begin E until the owner answers.

### Increment E — The command gate reads a single-word command in command position

**Outcome:** with a key of the form `wb <word>` relaxed, the command gate blocks a Bash command that names a launcher spelling and
then the word (`wb install`, `python3 -m workbench install`, the store's `bin/wb install`, and every spliced or expanded form of the
pair), and no longer blocks a command that holds the word alone (`npm install`, `git commit -m 'install deps'`, `ls docs/install.md`);
`wb preview <action>` is allowed. `approve-plan` and `wb run <command> <argument>` are read as now. This is the decision
`2026-10-27-command-gate-command-position` and builds only that.
**Dependencies:** D, and the owner's acceptance of that decision. If the owner does not accept it, this increment and F to I are
dropped by a new amendment of the plan, and the keys they cover offer `block` only.
**Affected areas:** `workbench/command_gate.py`, `tests/test_command_gate.py`, `docs/specs/command-permissions.md` ("The command gate"),
`docs/development.md`.
**Steps:**
1. Write the tests first. For a gate with `wb install` relaxed: allowed are `wb install --dir x`, the same through the store's
   `bin/wb`, `wb preview install --dir x`, `npm install`, `git commit -m 'install deps'`, `ls docs/install.md` and a command that
   names neither; blocked are `python3 -m workbench install`, `bash -c 'wb install'`, `env wb install`, `sh -c "wb  install"`,
   `w""b install`, `wb inst""all`, `wb $'\x69nstall'`, `${X}wb install` and a command with more than 64 `$'` strings; the keys
   `approve-plan` and `wb run <command> <argument>` give the results they give now (the existing tests pass unchanged). A test pins
   that the launcher spellings and the preview actions the gate reads are those of `rules`.
2. Change `words` and `judge` so that a key `wb <word>` is read as the launcher alternatives followed by the word, with the same
   folding, skeleton, `$'` decoding and in-order rules applied to the pair, and remove the exact token pair `preview <action>` for the
   actions of `rules.PREVIEW_ACTIONS` before the search, as `delegate-approve-plan` is removed.
3. Update the spec's "The command gate" and `docs/development.md`.
**Verification:** `python3 -B -W error -m unittest discover -s tests -p 'test_command_gate.py'`, the tests of the rendering and the
gate hook, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#E`.
**Checkpoint (owner):** this increment changes a permission boundary and a parser of untrusted text. At its end the agent asks whether
to run a security review with an installed module that provides `security-review`, and does not begin F until the owner answers.

### Increment F — `install` and `adopt` at `none`

**Outcome:** with `wb install` or `wb adopt` set to `none` and rendered, an agent can install or adopt without a terminal and
without a typed confirmation; at `block` they refuse without a terminal as now.
**Dependencies:** D and E.
**Affected areas:** `workbench/install.py`, `workbench/adoptplan.py` and the adopt code, `workbench/cli.py`, `tests/test_install.py`
and the adopt tests, `docs/development.md`, `docs/specs/installer-interface.md`.
**Steps:**
1. Write the tests first, for each command: refused with no terminal at `block`; at `none` the same arguments run with the
   preview computed, the plan applied as the typed confirmation would have applied it, and the attempt and outcome logged; at `none`
   with an unapproved module or a changed package it refuses before any write; the exit codes are the existing ones.
2. Replace each terminal test with the function from D.
3. Decide the form: the same arguments, no flag. A flag such as `--yes` was rejected in `2026-10-20-preview-then-owner-run-write`.
4. Update the command table in `docs/development.md` and the spec.
**Verification:** the install and adopt tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#F`.

### Increment G — `upgrade` and `add` at `none`

**Outcome:** the same for `wb upgrade` and `wb add`, which also refuse until the owner has acknowledged a changed manifest; the
acknowledgement check is not bypassed.
**Dependencies:** D and E (F is not required).
**Affected areas:** `workbench/upgrade.py`, `workbench/upgradeplan.py`, `workbench/cli.py`, the upgrade tests,
`docs/development.md`, `docs/specs/installer-interface.md`.
**Steps:**
1. Write the tests first: at `none` the commands run only when the acknowledgement baselines hold and refuse, writing nothing,
   when they do not; the log has the attempt and the outcome; at `block` the terminal rules apply as now.
2. Replace the terminal test with the function from D, and keep the acknowledgement check where it is.
3. Update the development table and the spec.
**Verification:** the upgrade tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#G`.

### Increment H — `approve` and `pin` at `none`

**Outcome:** the same for `wb approve` and `wb pin`, the commands that make a package or a helper trusted.
**Dependencies:** D and E.
**Affected areas:** `workbench/approve.py`, `workbench/pins.py`, `workbench/cli.py`, their tests, `docs/development.md`,
`docs/specs/trust-and-approval.md`.
**Steps:**
1. Write the tests first: at `none` an approval or a pin is recorded for exactly the declaration and tree hashes it computes now,
   and the record equals the one the terminal command writes; the first-party shipped approvals are untouched; an unreadable
   package refuses with nothing written; the log has both lines.
2. Replace the terminal test with the function from D.
3. State in the spec, in the consequences, that `none` here lets an agent make a package trusted, as the decision records.
**Verification:** the approve and pin tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#H`.
**Checkpoint (owner):** this increment lets an agent make code trusted. At its end the agent asks whether to run a security review,
and does not begin I until the owner answers.

### Increment I — The command gate leaves a literal `wb run` command and a sibling command name alone

**Outcome:** with single-word keys relaxed (`wb add`, `wb install`, `wb upgrade`, `wb pin`, `wb approve`), the command gate no longer
blocks `wb run safe-git commit ... --subject 'Add tests' -- tests/test_add.py` or any `wb run <name> <literal arguments>`, no longer
blocks `wb approve-plan` because `wb approve` is relaxed; the obfuscated and compound forms
stay blocked as now, and the block message for a key at `none` says what it read. This is the decision
`2026-10-27-command-gate-literal-arguments` and builds only that.
**Dependencies:** E, and the owner's acceptance of that decision. If the owner does not accept it, this increment is dropped by a new
amendment, the keys of F to H stay as built, and the spec and the plan say that relaxing a common-word key blocks commits.
**Affected areas:** `workbench/command_gate.py`, `tests/test_command_gate.py`, `docs/specs/command-permissions.md` ("The command
gate"), `docs/development.md`.
**Steps:**
1. Write the tests first. For a gate with `wb add`, `wb install` and `wb pin` relaxed: allowed are `wb run safe-git commit
   --expected-head <40 hex> --subject 'Add tests' -- tests/test_add.py`, the same with `'Fix padding'`, `-- workbench/install.py`,
   `'pin, mapping, shipping'`, a single-quoted subject that holds a newline, and the same through the store's `bin/wb`; with
   `wb approve` relaxed, `wb approve-plan docs/plans/a.md`. Blocked are every form the existing tests block, and in addition
   `wb run x --subject "$(wb install)"`, `wb run x 'a' ; wb install`, `wb run x 'a' | xargs wb`, `wb run x "install"`,
   `wb run x install; wb install`, a command with a newline outside quotes, `wb run x 'a'<newline>wb install`, `w""b install`,
   `w\b install`, `w\<newline>b install`, `wb inst\<newline>all`, `wb run wb install`, `wb run workbench install`,
   `wb run x 'a'x`, `wb run x 'a''b'`, a lookalike launcher, `wb inst""all`, `wb approve${X}`, `wb approve"-plan"`, and
   `wb run mempalace init` with that key relaxed whatever its arguments. A test pins that the sibling names are those of `rules`.
2. Change `judge` so that a single-word launcher key skips a command that fully matches the literal `wb run` form on the raw text;
   remove the exact sibling tokens before the search; and word the message for a `none` key, which needs the level of each
   relaxed key passed to `judge`.
3. Update the spec's "The command gate" and `docs/development.md`, and the Result of this plan.
**Verification:** `python3 -B -W error -m unittest discover -s tests -p 'test_command_gate.py'`, the tests of the rendering and the gate
hook, a differential run of the old and the new `judge` over a set of spellings that finds none that the old blocked and the new allows,
except the forms the decision exempts, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#I`.
**Checkpoint (owner):** this increment changes a permission boundary and a parser of untrusted text. At its end the agent asks whether
to run a security review with an installed module that provides `security-review`, and does not begin J until the owner answers.

### Increment J — `acknowledge`, `recover`, `release-approvals` and `attach` at `none`

**Outcome:** the same for the remaining installer commands. `acknowledge` is set by the checkpoints `acknowledge-first-tier` and
`acknowledge-second-tier`; `attach` only loses its `deny`; `release-approvals` loses its `deny` (it never had a terminal test).
**Dependencies:** D and E (I, the gate change, is not required but is better built first).
**Affected areas:** `workbench/acknowledge.py`, `workbench/recover.py`, `workbench/attach.py`, `workbench/cli.py`,
`workbench/rules.py`, their tests, `docs/development.md`, `docs/specs/trust-and-approval.md`.
**Steps:**
1. Write the tests first: `acknowledge` at the tier's `none` records the baselines exactly as the terminal command does; `recover`
   clears only the marker and the empty directories it clears now; `attach` and `release-approvals` render no `deny` at `none`; the
   log is written for each that changes something.
2. Replace the terminal tests with the function from D where one exists.
3. Update the development table and the specs.
**Verification:** the affected tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#J`.

### Increment K — `accept-decision` at `none`, and the documents

**Outcome:** the checkpoint `accept-decision` offers `block` and `none`; the decision-drafting guidance reads it; `wb settings`
prints it; the specs and `docs/development.md` describe everything built and the spec's status reads as current.
**Dependencies:** B (it reads the table); the other increments are not required.
**Affected areas:** the process module's checkpoint declaration and the `draft-decision` skill text in the package under
`packages/workbench/`, `workbench/levels.py`, `tests/test_levels.py`, `docs/specs/command-permissions.md`,
`docs/specs/code-work.md`, `docs/development.md`.
**Steps:**
1. Write the tests first: the key offers `block` and `none`; it reads `block` by default; a table entry sets it; `wb settings`
   prints it.
2. Change the skill text so that an agent accepts a decision only while `wb settings` prints `level accept-decision: none`, and
   otherwise stops at `Proposed`. Keep the wording out of the managed `AGENTS.md` blocks.
3. Correct `code-work.md`, whose checkpoint table lists `accept-decision` as delegable, to the built behavior.
4. Move the "Planned" section of the spec into the built sections, leave what is deferred under "Not built", and update the
   acceptance criteria and the review record.
**Verification:** the levels tests, `wb check`, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#K`.

## Verification for the plan as a whole

1. `python3 -B -W error tests/run_all.py` passes.
2. `wb check` reports no problems, and `wb run code-work check` reports none.
3. `wb settings` with the default personal settings prints every agent-safe key as `none` and every other key as `block`.
4. A trial in a throwaway project, run by the owner: set `wb install` to `none`, attach, and have the agent run an install with no
   terminal; then set it back to `block` and confirm it refuses. The agent describes the steps and runs none of them.
5. A security review of the permission boundary, run only if the owner asks at the checkpoints in D, E, H and I.

## Risks and sensitive actions

- **Authorization and the guarded store change.** Letting an agent run `install`, `upgrade`, `approve` and `pin` at `none` removes
  the only barrier the harness `deny` and the terminal test gave. The owner chooses that, the default is unchanged, and every run
  is logged. The log can be written from a shell (`2026-10-26-ask-level-command-gate`), so it is a record and not a control.
- **A typed confirmation disappears at `none`.** For each command the plan replaces a terminal test and sometimes a typed digest
  with no confirmation. The risk is a path that runs without the checks the terminal path made. Each increment states the checks
  that remain and tests them.
- **`accept-decision` at `none`** weakens the rule that an accepted decision outranks the code.
- **Self-hosted code.** The code the commands run is in the agent's write scope here, so a `none` level here is weaker than in a
  project that only uses the workbench.
- **A rendering that denies too much.** Increment C could deny an agent-safe command the agent needs (for example `wb settings`)
  if an owner sets it to `block`. That is the owner's choice and the default is `none`; a test pins the default rendering.
- Four increments, D, E, H and I, are checkpoints for a security review; a review runs only when the owner asks.
- Nothing is pushed, published or installed from outside, and no secret is used.

## Review record

Reviewed by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-27, at the owner's
request: two rounds of the bound of 3, converged. Round 1 returned one major finding: the plan left the owner-run arguments of
module commands at `block` only, against the accepted decision and the spec's P4 and P5. The owner chose to defer them; the spec's
"Levels offered", P4, P5 and "Not built" were narrowed, a clarification note was proposed on the decision, and the finding was
applied. Round 2 returned no meaningful findings and one minor one (the `Specs:` line omitted `module-boundary`), which was applied.
The review is not an approval; the plan stays `Proposed` until the owner approves it.

**Amendments after approval.** The plan was approved by the owner with `wb approve-plan` and changed twice afterwards, each time with
a new approval. (1) On 2026-10-27, after Increment D was committed, a command-gate problem stopped the work: a relaxed key such as `wb
install` blocked `wb preview install`, `npm install` and commit messages that hold the word. The owner chose to fix the gate first;
the decision `2026-10-27-command-gate-command-position` was proposed, the plan gained a new Increment E for it, the old E to I became F
to J, and the owner accepted the decision and approved the plan again. (2) On 2026-10-27, after Increment H was committed, a second
problem (the gate blocked every `wb run safe-git commit` whose subject or paths held a relaxed word, and `wb approve-plan` when `wb
approve` was relaxed) was found by running the gate on those commands; the owner chose to build H as planned and fix the gate
separately, the decision `2026-10-27-command-gate-literal-arguments` was proposed and reviewed (its first draft was changed after the
review), the plan gained Increment I, the old I and J became J and K, and the owner accepted the decision and approved the plan
again. The label changes touched increments that had no commit under the old labels, so no commit trailer is wrong. Both decisions
carry the owner's acceptance in their status lines.

**Review of the whole plan, 2026-10-27, at the owner's request.** One round by the `reviewer` agent after Increment K, reading the plan,
the three decisions, the spec and the code; it ran nothing. Verdict on the code: no blocking finding. Blocking findings, all applied:
three stale sentences in the specs (`command-permissions.md` "a key is never limited to `block`", `installer-interface.md` "no command
an agent is meant to run records an approval or a pin", `code-work.md` "only `approve-plan` offers a level beyond `block`") and this
record of the amendments. Also applied: the command table of `installer-interface.md`, the log section of the spec, and the settings
description of `docs/development.md`. Left as they are, because the plan body cannot change without a new approval: the plan's
Assumptions still call the decisions of Increments E and I `Proposed` (both are Accepted), the headings of the Result entries still
say "built, not committed" (every increment is committed; the commits are listed in the plan's history by the `Plan:` trailer), and
the Goal and Completion criterion 4 are worded without the exceptions that the K Result lists. The review's ranked risks are in the
chat record: an agent can make code trusted at `none`; the command gate is a text matcher; real-harness coverage covers `install`,
`add` and the gate only; `attach` and `release-approvals` are tested with the command mocked; `accept-decision` is guidance only.
Security reviews were asked and run at the checkpoints D, E, H and I and at J; F, G and K had no security review: F's was offered as optional and not asked for, and the owner was not asked at the end of G or K (the plan lists no checkpoint there; F and G touch authorization and the filesystem, which AGENTS.md says to ask about).


## Deferred work

- **`none` for an owner-run argument of a module command** (`wb run mempalace init`, `mine`, `remote-runner fetch-overwrite`, and the
  review engine's `reset`, `archive`, `prune`, `amend`, `extend`). The helper of each checks its own terminal, and the contract has
  no field through which the installer can tell it to skip that. It needs a decision on the module contract and then a plan. Until
  then these keys offer `block` only, which the accepted decision says no key should; the plan states that gap and the owner's
  decision is what closes it. The shape to propose, which the decision may change:
  1. the declaration of an owner-run argument gains an optional field for the levels it offers;
  2. the launcher computes the level of the key `wb run <command> <argument>` (the rendering record, the live hashes, the gate) and
     passes it to the helper, which cannot derive it itself;
  3. the helper calls the kit's level function from Increment D in place of its own terminal test, and writes its own log attempt
     after its own checks and its outcome after the change;
  4. a helper run directly, without the launcher, receives no level and falls back to the terminal test, so it fails closed. An
     agent that runs a helper directly can supply whatever the launcher would, so this is no stronger than the terminal test, which
     is a mistake guard; the barrier remains the harness rules and the command gate.
  A change to an existing kit function would raise `wbkit.API`, and the runner matches it exactly, so every first-party helper's
  declaration would be updated in the same plan; Increment D's addition does not.
- **`ask` for every other key.** One preview digest per command, starting with `install` and `adopt`.
- **`wb run review-engine extend`** (Increment G of the earlier plan) belongs to the same work.
- **Converging `AGENTS.md`** with the base and the module blocks: the generic rules (source of truth, diagnostics, review, testing)
  move into modules and the file keeps only what is specific to this repository. A separate plan.
- **A command that re-renders an attached clone**, so a table change takes effect without a new attach.
- The rule that a command reaching more than one key takes the strictest of them stays unbuilt, because no command reaches two keys.

## Result

### Increment A — built, not committed (2026-10-27)

**Done.** `workbench/levels.py` has `agent_keys()` and a `registry(checkpoints, commands, agent=True)` that adds a key for each
agent-safe action (`wb verify`, `wb preview install|adopt|upgrade|add`, `wb launch`, `wb check`, `wb plan-status`, `wb settings`) and for
each declared module argument; an owner-run argument defaults to `block`, any other to `none`, and an agent-safe key offers `block`
and `none` and defaults to `none`. `workbench/rules.py` names the words that are not keys (`HOOK_ENTRY_POINTS`, `DISPATCHERS`,
`REACHES_ANOTHER_KEY`, `PREVIEW_ACTIONS`). `settings.effective` takes `agent`; `wb settings` passes each command's arguments and prints
the new `level` lines; `rendering.table_of` passes `agent=False`, so the table that is digested into a rendering record is the one it
was before and an attached clone keeps its record. The spec's built sections ("Which levels a key offers", "Shipped defaults",
acceptance criterion 1, "`wb settings`"), `docs/development.md` and two docstrings say so.

**Verification as run.** The tests were written first and failed for the right reasons (missing attributes and keys). Then
`python3 -B -W error tests/run_all.py`: `Ran 4883 tests in 10 roots`, `OK`; `wb check`: no problems; `wb settings` printed the new keys
(agent-safe and non-owner-run module arguments `none`, owner-run `block`). Existing tests changed where they assumed the old key list:
`tests/test_settingscmd.py` (the `level_lines` helper, and a count of `settings:` lines that the key `level wb settings: none` had
made wrong), `tests/test_settings.py`, `tests/test_rendering.py` (the record lists the keys it rendered) and `tests/test_approve_levels.py`.

**Review.** One round by the `reviewer` agent (1 of 6 exchanges, cap 3 rounds): no blocking findings, five not blocking. Applied:
(1) the built sections of the spec and two docstrings said every default is `block`: corrected; (2) nothing tied `rules.PREVIEW_ACTIONS` to
the tuple `cli._preview` accepts: a test parses `cli.py` and compares; (3) the digest test built its "before" table from the code under
test, and `agent=False` left the non-owner module arguments in when a 3-tuple was given: the test now writes the old keys out, and
`agent=False` leaves those arguments out too, with a test; (4) `docs/development.md` did not say a `block` on an agent-safe key is not
yet enforced: added. No finding rejected. The reviewer could not run anything and did not read the diffs or the decision.

**Not done, carried forward.**
- A `block` set on an agent-safe key is read and printed and not enforced until Increment C.
- A damaged or unreadable settings file reads the whole table as `block` (spec "Reading rules"), the agent-safe keys included.
  When C renders a `deny` for them, such a file would deny `wb settings` and `wb check`, the commands that report it. C must decide
  whether agent-safe keys are exempt from the whole-table block. **Owner decision needed before C.**
- `effective_level` requires a rendering-record entry for a key at `none`. That suits a key that opens a `deny`; an agent-safe key at its
  default `none` opens nothing and needs no record. C and D must say so.
- The agent-safe keys are absent from the record, so C changes the record's digest for every attached clone with a relaxed key.
  C must keep such a clone readable or say how it is re-attached.

**Review of the whole plan:** not yet asked.

### Increment B — built, not committed (2026-10-27)

**Done.** `settings._level` returns a key's table entry, else its checkpoint reading (`stop` as block, `delegate` as delegated), else
its default; the stricter-of rule is gone. A table entry a key does not offer reads as block with a note; a damaged table reads every
key as block and still overrides a checkpoint of `delegate`; a key in both with different readings gets one note that the level
applies; `delegate` still takes effect for `approve-plan` only. `Effective` gains `translated` (a defaulted field), and `wb settings`
prints `translated <key>: <word> read as <level>` after the `level` lines. The spec's built sections (`The levels`, `The table`,
`Reading rules`, `wb settings`), `trust-and-approval.md`'s Settings paragraph, `docs/development.md` and two docstrings say so.

**A departure from the plan's wording.** Step 1 says a translated word is read "with a note". The translation is returned in
`Effective.translated` and printed as its own `translated` line, not added to `notes` and not printed as a `settings:` line, because
`tests/test_delegation.py` (`test_delegate_for_the_one_name_has_no_note`) pins that a legitimate `delegate` shows no `settings:`
line and a translation is not a problem. The Outcome ("notes a translated word") still holds. The owner may prefer a `settings:` line.

**Verification as run.** Tests first; the old stricter-of tests and the new table-wins tests failed for the right reason. Then
`python3 -B -W error tests/run_all.py`: `Ran 4893 tests in 10 roots`, `OK`; `wb check`: no problems. Tests changed: the stricter-of
cases in `tests/test_settings.py` and `tests/test_settingscmd.py` now assert table-wins; new tests cover each checkpoint and table
combination, the translation line, a table entry for an undeclared checkpoint, a damaged table with a `stop` checkpoint, and a
`delegate` on a key that cannot delegate with a table entry.

**Review.** One round by the `reviewer` agent (the second exchange of this run, 2 of 6 across A and B): no blocking findings, four
not blocking, all applied or recorded: (1) the departure above is recorded here; (2) the spec's "Planned" section opened "Not built"
though two paragraphs are built: the opening now says which; (3) `trust-and-approval.md` stated the checkpoint reading without the
table: a clause added; (4) three untested combinations: tests added. The reviewer found no path to unintended delegation and none by
which a damaged file reads less strict. It could not run anything, did not read `docs/development.md`'s long settings row, and did
not diff against HEAD.

**Carried forward.** A new loosening path exists by design: a `stop` checkpoint with a table entry of `delegated` now delegates, where
the old rule gave block. It requires the owner to write `delegated`. Rendering reads the same table, so a table `none` or `ask` on a
key whose version 2 checkpoint says `stop` now renders looser than before; that is the decision.

### Increment C — built, not committed (2026-10-27)

**Owner decision, 2026-10-27.** A damaged or unreadable settings file or table reads every owner-run key as block and leaves the
agent-safe keys, and the declared module arguments that are not owner-run, at their default `none`, so `wb settings` and `wb check`
still run to report the damage (option 1 of the question put at the end of Increment B). An explicit `block` on such a key is not
honored while the file is damaged; the spec and `docs/development.md` say so.

**Done.** `rendering.key_patterns` has patterns for each agent-safe key (`wb check` and the other single words, and `wb preview
<action>`) and for a declared module argument; `rendering.plan` returns the patterns of every key it renders as `deny` in a new
`Plan.deny`; `harnessstage.stage` passes them to `render_permissions` as neutral `deny` rules beside the module rules; `rendering.table_of`
takes the three-element command form and leaves out a key marked `agent` (`levels.Key.agent`) while its level is its default `none`,
so the default table, its digest, the rendering record and the command gate's relaxed list are unchanged for a default clone and for a
clone attached earlier; `settings._level` keeps an `agent` key at its default when the table is blocked. The spec ("Rendering",
"Reading rules", "wb settings") and `docs/development.md` say so. `docs/specs/harness-modules.md` and `workbench/harnessplan.py` need no
change: the first points to `command-permissions.md` for the rendering rules and the second already accepts the extra rules.

**Verification as run.** Tests first: the new tests failed for the right reasons (no patterns, keys missing from the table, damaged
tables still blocking). Then `python3 -B -W error tests/run_all.py`: `Ran 4915 tests in 10 roots`, `OK`; `wb check` and `wb run
code-work check`: no problems. New tests: `tests/test_rendering.py` (the table, the digest, the patterns, the deny in every spelling,
the record, a table changed after attach, the command gate's relaxed list, a module argument in a project that installs one),
`tests/test_settings.py` and `tests/test_settingscmd.py` (damaged files and tables), `tests/test_command_gate.py` (no agent-safe command is blocked).
**Not verified:** this repository's own attached clone has no rendering record, so its stored digest could not be compared with the
one computed now; the tests pin the property for a clone attached in a test.

**Review.** One round by the `reviewer` agent (3 of 6 exchanges this run): no blocking findings, four not blocking, all recorded or
applied. (1) The loss of an explicit `block` while the file is damaged was implied and is now stated in the spec and development.md.
(2) `effective_level` reads `block` for a key missing from the table, and an agent-safe key at its default is missing on purpose;
a docstring now says not to ask it, and **Increments D to J must not call `effective_level` on an agent-safe key**. (3) The deny
patterns of a module argument use the existing `run --provides *` head, whose glob can also match another module's command whose name
and arguments coincide; it is the shape the owner-run deny rules already have, argument names cannot carry a space or a glob, and a
deny never un-denies, so it is accepted. (4) The plan lists `test_command_gate.py`, `harness-modules.md` and `harnessplan.py`: a gate
test was added; the other two needed no change (above). The reviewer read no test bodies and ran nothing.

**Carried forward.** A deny rendered for an agent-safe key takes effect at the next attach, and `wb attach` refuses a clone that
already records a harness, so tightening an agent-safe key in an attached clone needs a new clone (the known limit in "Not built").

### Increment D — built, not committed (2026-10-27)

**Done.** `workbench/wbkit/levels.py` (new, kit, standard library only, `wbkit.API` stays 1): `may_run(level, terminal)` (true at a
terminal; without one only for the string `none`), `is_terminal`, the log's `attempt_line`, `outcome_line`, `append`, `begin`, `finish`
and `finish_refused`, the limits and the errors. `workbench/levellog.py` keeps its reader and its own clock and identifiers and calls
the kit for the formats, the limits and the append; its errors are the kit's, and its existing tests pass unchanged.
`workbench/levelrun.py` (new): `level_now` (the level through `rendering.effective_level`), `route` (a terminal goes on and reads
nothing; otherwise the kit's `may_run` on the verified level, else `Refusal` with the caller's text), `logged` (attempt, change,
outcome; no entry when nothing changes) and `done`. `planapprovals.py` uses `level_now`, `logged` and `done`; its behavior is
unchanged. No other command uses them. The spec ("One way to run at `none`"), `module-boundary.md` (the kit list) and
`docs/development.md` say so. `tests/test_kit.py` lists `datetime` among the standard-library modules the kit may use.

**Verification as run.** Tests written before the modules. `test_wbkit_levels.py` (20), `test_levelrun.py` (22), and the unchanged
`test_approve_levels.py` (34), `test_delegation.py` (87), `test_levellog.py` (26): OK with warnings as errors. Full suite
`python3 -B -W error tests/run_all.py`: `Ran 4957 tests in 10 roots`, `OK`; `wb check`: no problems. The existing helpers load against
the kit as before: the kit's API is asserted to be 1 and the package tests that import the kit pass. **Not verified:** no command
but `approve-plan` runs through `route`.

**Review.** One round by the `reviewer` agent: no blocking findings, five not blocking. Applied: (1) `route` does not check that the
project a command acts on is the one the level was read for; the docstring now requires the command to compare it with
`Route.project_id`, as `approve-plan` does, and increments F to I must do so. (3) `logged` docstring says a `refused` outcome can
follow a change that was made. Rejected with reason: (2) `level_now` catches two exception types; anything else fails closed as a
traceback and never lets a run through. (4) The two writers share the formats and the append through the kit, so the lines cannot
drift; the plan allowed the split. (5) `may_run` trusts a verified level by design; a helper run directly getting no level is the
deferred plan's policy. The reviewer read no test bodies and ran nothing.

**Security review** (the owner asked; `security-reviewer` agent, one run). It could not run experiments (its writes and probe commands were refused) and
compared nothing with HEAD, so it is a read-only review: no Critical, High or Medium finding and four Low. Applied: (1) `may_run`
counted any truthy `terminal`; only `True` counts now. (2) `attempt_line` and `outcome_line` did not check the identifier and
time; they do now (tests for both). (4) the spec's "every run" sentence now says a run that goes on without a terminal, because a run
at a terminal is not logged. Rejected: (3) an interrupt in `level_now` or `done` is not caught in `approve-plan`'s second `try`; I
read HEAD and it was the same there, and it fails closed with the attempt listed as unfinished. Recorded for the plan that lets a
helper run at `none`: the channel by which the launcher passes a level needs its own protection. Limits: no hostile link, FIFO,
hard-link or race probe was run by the reviewer; the unit tests cover link, directory, hard link and full log. After the fixes: full suite `Ran 4959 tests in 10 roots`, `OK`; `wb check` and the plan check: no problems.

### Increment E — built, not committed (2026-10-27)

**Done.** `workbench/command_gate.py` reads a single-word key (`wb <word>`, other than `approve-plan` and `wb run ...`) as a launcher
and then the word (`LAUNCHERS` are the last words of `rules.SPELLINGS`: `wb`, `workbench`), with the folding, skeleton, `$'` decoding
and in-order rules applied to the pair; the exact pair `preview <action>` (`PREVIEW_ACTIONS` = `rules.PREVIEW_ACTIONS`) is removed
before the search, for these keys only. `approve-plan` and `wb run` keys are read as before. The spec ("The command gate") and
`docs/development.md` say so.

**Verification as run.** Tests first: the new class `SingleWordKeys` failed (19 failures) before the change. Then
`test_command_gate.py`: 56 tests OK, the earlier cases unchanged; full suite `python3 -B -W error tests/run_all.py`: `Ran 4974 tests
in 10 roots`, `OK`; `wb check` and the plan check: no problems. **Not verified:** the gate was not run end to end under a harness
with `wb install` at `none`; the rendering and the hook are unchanged and covered by their own tests.

**Review.** One round by the `reviewer` agent: no blocking findings, five not blocking. Applied: (1) the `preview <action>` removal
also applied to a module's `wb run preview install`-style key, so it now applies only to the launcher-and-word keys (test added);
(2) a preview that holds an expansion or glob is still blocked by the pattern rule, which the spec now says and a test pins;
(3) and (4) the exemption and launcher tests were tightened (a call whose arguments hold the words is the exact form and is allowed;
a spliced or expanded launcher alone is blocked). Recorded, not changed: (5) a launcher that does not end in `wb` or `workbench`
(an alias, a symlink under another name, `python3 /store/x/cli.py install`) is no longer seen, which is the drop in coverage the
decision accepts. The reviewer ran nothing and had no diff against the old code.

**Security review** (the owner asked; `security-reviewer` agent, one run). Its Bash and Write calls were refused, so it ran no probe and is a
read-only review. One Medium finding: a literal word before a literal launcher was allowed by the in-order rule where the word-alone
rule blocked it (`echo install | xargs wb`, `for w in install; do wb $w; done`, `set -- install; wb "$@"`, `read a <<< install; wb $a`).
I reproduced it with `judge` (five of the six were allowed), wrote the tests first (11 failures), and changed the gate to count the
launcher and the word in either order; a compound command that holds both (`npm install && wb check`) is blocked and is run as two
calls. A differential probe I ran of the old and the new gate over 5,880 generated spellings (launchers, wrappers, splices of the
word, trailing text) found no command the old gate blocked and the new one allowed. This departs from decision 1 of
`2026-10-27-command-gate-command-position` ("in order"), so a clarification note was added to that record, approved by the owner on 2026-10-27. After the change: `test_command_gate.py` 58 tests OK; full suite `Ran 4976 tests in 10 roots`, `OK`; `wb check` and the
plan check: no problems. Limits: the reviewer did not read `gate_hook.fold`, line continuation or `python3 -c`/`runpy`; my corpus covers
`wb install` only and the launchers and splices listed in the probe.

### Increment F — built, not committed (2026-10-27)

**Done.** `wb install` and `wb adopt` offer `block` and `none` (`levels._OFFERS`). `install.run` takes `cwd` and calls `levelrun.route`
with the key `wb install` or `wb adopt`, read for the project the command is run from: at a terminal it goes on as before and reads
nothing; without one it goes on only at a verified `none`, otherwise it refuses with the terminal-only message (and the reason when the
level could not be read). At `none` it prints the plan and its digest, asks nothing, runs the same checks (including the second build
of the plan, which must give the same digest), and `levelrun.logged` writes the attempt (`digest:<64 hex>`) just before the first write
and the outcome after (`done`/`written`, or `refused` with the exit code when it stopped after writing). An unwritable log refuses
before any write; an outcome that cannot be written, or an interrupt after the writes, exits 3. No flag. The spec, the installer
interface and `docs/development.md` say so.

**Verification as run.** The code was written before the tests, against the test-first rule; I then wrote `tests/test_install_levels.py`
(26 tests) and ran it against the old `install.py` and `levels.py`, where it failed (5 failures, 18 errors), and against the new code,
where it passes. The existing offers tests (`test_levels`, `test_settings`, `test_approve_levels`) were updated for the two keys. Full
suite `python3 -B -W error tests/run_all.py`: `Ran 5004 tests in 10 roots`, `OK`; `wb check` and the plan check: no problems.
**Not verified:** no end-to-end run under a harness with `wb install` at `none` (the owner's trial, completion criterion 4).

**Review.** One round by the `reviewer` agent: no blocking findings, nine not blocking. Applied: (1) an interrupt after the writes
returned 130 and said "cancelled"; it now exits 3 and says the install was written (test added; the `run` docstring says so);
(2) the level is read once, before the fetch and the two plan builds: the spec says so; (3) the compare-the-project requirement of
Increment D does not apply because the target is never the project the level was read for: a comment in `run` and the spec say so,
and a test pins that a new directory inside the project is accepted. Recorded, not changed: (4) the log's reason for exit 3 does not
tell a failed write from a failed attach (the stderr report does); (5) no test for a broken pipe or an adopt exit 3; the two helpers
that print after the writes swallow `BrokenPipeError`. The reviewer ran nothing.

### Increment G — built, not committed (2026-10-27)

**Done.** `wb upgrade` and `wb add` offer `block` and `none` (`levels._OFFERS`). `upgrade.run` takes `cwd` and calls `levelrun.route`
for the key `wb upgrade` or `wb add`; `cli._upgrade` no longer refuses before the store is opened. At `none` the command prints the
plan and its digest, asks nothing, and runs every check it runs at a terminal (the acknowledgement, the approvals, the second build).
The plan's project (the manifest seed) must equal `Route.project_id`, or it refuses and writes nothing. The attempt and outcome are
written by the new `levelrun.apply_logged` (moved out of `install.py`, which now uses it): `done`/`written` for exit 0, `refused` for
any other exit (`refused before writing` for exit 1, `stopped after writing (exit N)` otherwise). Nothing to change writes no entry.

**Verification as run.** `tests/test_upgrade_levels.py` (35 tests) was written first and failed on the terminal refusal against the
old code; it passes now. Full suite `python3 -B -W error tests/run_all.py`: `Ran 5035 tests in 10 roots`, `OK` (before the last two
tests were added; `tests.test_upgrade_levels` alone: 35 OK after); `wb check` and the plan check: no problems. **Not verified:** no
end-to-end run under a harness (criterion 4).

**Review.** One round by the `reviewer` agent: no blocking findings. Applied: tests for a marker that cannot be made (exit 1, `refused
before writing`) and for an unapproved module. Recorded, not changed: (1) a usage error without a terminal now exits 2, not 1, and an
agent's `wb upgrade` at `block` opens the store and writes the launcher wrapper before the refusal, as `install` and `preview` already
do; (2) no test for a changed second digest, an interrupt, a failure in the file stage, a nothing-to-change `add`, or `apply_logged`
alone; (3) a failing `finish_refused` inside `levelrun.logged` can replace the original exception (already so for `approve-plan`).

### Trial in a real harness — F and G (2026-10-27, run by the owner; completion criterion 4, partly)

A throwaway project was installed with the owner's table at `{"wb install": "none", "wb upgrade": "none"}` (settings version 2) and the
Claude harness attached by the install itself; a second clone installed before the table was set served as the control. Observed:

- The rendered `.claude/settings.local.json` of the new clone has no `Bash(wb install…)` or `Bash(wb upgrade…)` `deny`, still has `wb add`
  (at `block`) and every `python3 -m workbench install|upgrade` spelling, and holds the `wb gate-command claude` hook. The control keeps
  all of them.
- In a new session in that clone, `wb install <absolute path> --package … --select groundwork claude` ran with no prompt and no typed
  digest and wrote the project (49 paths). The level log gained `A … wb install none digest:<64 hex>` and then `O … done written`.
- Blocked: `python3 -m workbench install …`; `echo install; wb check` (the accepted compound-command cost); `wb install ~/…` (the gate
  refuses `~` and `$HOME`, as it does every expansion); `wb add …` (denied by the harness, `block`).
- Allowed: `wb preview install …` (printed a plan, wrote nothing), `git add -A`. `npm install` reached the harness's own `ask` rule for
  the `install-dependencies` hard stop, which is unchanged.

Found, not changed: the gate's block message for a key at `none` says the command is "not exactly the simple command the ask rule
matches", though a `none` key has no `ask` rule, and it does not name `~` or `$VAR` as the reason. A wording fix for a later increment.

**Not covered:** `wb upgrade` and `wb add` at `none` were not run by an agent (only `install` was); `approve`, `pin`, `acknowledge`,
`recover`, `release-approvals`, `attach` and `accept-decision` are not built yet. The trial does not repeat for them unless the owner asks.

### Increment H — built, not committed (2026-10-27)

**Done.** `wb approve` and `wb pin` offer `block` and `none` (`levels._OFFERS`). `cli._levelled` reads the level for the project the
working directory is in (`levelrun.route`) and gives `approve.run` and `pins.run` a `log(digest, apply)` at a verified `none` (nothing
at a terminal); these commands cannot import `levelrun` without a cycle, so the command line holds the route. At `none` they print what
the owner would have been shown, ask nothing, run the same checks (verification and the second verification; the helper read and read
again) and the attempt (`digest:` the full tree hash, or the helper's sha256) is written just before the records and the outcome after.
`pin` refuses unless its `<project-id>` and `--root` are the project the level was read for. An approval already on file writes no
entry. The spec says, in `command-permissions.md` and `trust-and-approval.md`, that at `none` an agent can make a package or a helper
trusted. Exit codes and the terminal path are unchanged.

**Verification as run.** `tests/test_approve_pin_levels.py` (30 tests) was written first and failed on the terminal refusal against
the old code; it passes now. The offers tests were updated. Full suite `python3 -B -W error tests/run_all.py`: `Ran 5068 tests in 10
roots`, `OK` (before the `--root` test and fix; the file alone: 30 OK after); `wb check` and the plan check: no problems.
**Not verified:** nothing under a real harness for these two keys.

**Review.** One round by the `reviewer` agent: no blocking findings. Applied: `pin` also compares `--root` with the project root the
level was read for (test added); the stale "no command but approve-plan uses it" sentence in the spec. Recorded, not changed: no test for
`approve --source` at `none`, a terminal-path run with typed confirmation, or `_record` stopping part way (the logged outcome then
reads `refused before writing`, which the spec says is not exact).

**Found, not changed (the command gate).** With any of these single-word keys relaxed, the gate blocks every command that holds the
launcher `wb` and the word, in either order: `wb run safe-git commit --subject 'Add tests'` with `wb add` relaxed, `'Install docs'`
with `wb install`, `'Upgrade the parser'` with `wb upgrade`, and with `wb pin` also `mapping`, `shipping` or `spinner` (the word is
matched inside other words, after the punctuation is removed). With `wb approve` relaxed, `wb approve-plan` is blocked too. Found by
running `judge` on those commands after Increment G; the owner trial did not cover a commit. The owner chose to build H as planned and
to fix the gate separately; a Proposed decision and a plan amendment are needed.

**Security review (H, read only; the reviewer's probes were refused).** No Critical or High finding. Medium: the fetch of `approve
--source` and its cache write happen before the attempt is logged, so a failed or already-approved fetch leaves no entry; the same is
true of `install`, and the spec now says so. Low, applied: `pin --root` spelled through a link and `..` passed the `realpath` check
while `pins.run` read another directory (reproduced by a test that failed, then fixed: the root must name the project with or without
following links). Low, recorded in the spec: the outcome text for a partial approval; the level read once before the fetch;
`approve` is machine-wide but its level is read for the working directory's project. Sound (read only): `route` and the rendering
record, the attempt-before-change order, the `_on_file` shortcut, the digest binding of the pin, `--ref` and source checks, the exact
project-id comparison. Not tested by the reviewer: any experiment. `tests/test_approve_pin_levels.py` is now 31 tests.

### Increment I — built, not committed (2026-10-27)

**Done.** The gate builds the accepted decision `2026-10-27-command-gate-literal-arguments`. For a single-word launcher key, a command
that is exactly one literal `wb run <name> <arguments>` (matched in full on the raw text through `wb` or the store's `bin/wb`; a
name of the pin and command form that is not a launcher, a verb of `rules`, `python` or `python3`; arguments that are plain tokens or
single-quoted strings, newlines included) is not searched for the word, so a commit subject or a path that holds it passes; the exact
token of a command that continues the word (`approve-plan` for `wb approve`, from `rules`) is removed before the search; and `judge`
takes the table, so the reason for a key at `none` does not name an `ask` rule and says that a wrapper, a compound command and a path
with `~` or `$VAR` are read as a call. `approve-plan` and `wb run <command> <argument>` keys are read as before. The skeleton rule was
dropped from the decision's first draft after review. The spec ("The command gate") and `docs/development.md` say so.

**Verification as run.** `LiteralRunCommands` in `tests/test_command_gate.py` was written first and failed on the old code; the file
now has 77 tests, all passing. A differential run of the previous `judge` (from the last commit) against the new one over 11,550
generated spellings (launchers, spliced words, tails, five command shapes, five keys) found 244 commands that the old blocked and the new
allows, all of them literal `wb run` forms. Full suite `python3 -B -W error tests/run_all.py`: `Ran 5084 tests in 10 roots`, `OK`
and again with the five added after the review: `Ran 5089 tests in 10 roots`, `OK`. `wb check` and the plan check: no problems. **Not verified:** nothing
under a real harness; the owner's trial of this increment (a commit through `wb run` with a key relaxed) is still to do.

**Review.** One round by the `reviewer` agent: no blocking findings. Applied: tests for `--provides`, a quote after `=`, a store path
with regex characters, a 64 KiB command (judged in well under a second) and the short word built at run time; the spec says `python`
and `python3` are reserved names, that `--provides` is not exempt, and that the sibling removal widens the accepted run-time limit
only within the in-order window. Recorded, not changed: the reason text for a `wb run <command> <argument>` key reads `wb <words>`
(the same expression as before this increment); the pattern-rule message still says "ask or none"; the docstring bullets read as a
second list.

**Security review (I, read only; the reviewer's probes were refused).** No Critical, High or Medium finding. Low, applied: the sibling
removal took the bare token `approve-plan` out of the text, so with only `wb approve` relaxed and enough padding between
`A=approve-plan` and `wb ${A%-plan}` the new gate allowed a spelling the old one blocked (the short spellings were still caught by
the pattern rule; I ran them to check, and ran the padded one to see it allowed). It now removes a launcher followed by the token,
as `preview <action>` is, so the token alone is still the word. A test pins the short and the padded forms and the allowed exact
forms. This is narrower than the decision's wording ("the exact token ... is removed"), so it blocks more, not less; the decision
is not edited. Sound (read only): the literal regex and its agreement with bash on single quotes, whitespace and prefixes, the
reserved names, the store head with `re.escape`, linear failure on an unbalanced quote, the other keys still judged, the level table
and the one-line reason. Not tested by the reviewer: any experiment. `tests/test_command_gate.py` is 77 tests.

### Trial in a real harness — G and I (2026-10-27, run by the owner; completion criterion 4, further)

A second throwaway project was installed (groundwork and safe-git) with the table at `{"wb add": "none", "wb pin": "none"}`, so its
harness was rendered with those two keys relaxed. Observed:

- The rendered `.claude/settings.local.json` has no `Bash(wb add…)` or `Bash(wb pin…)` `deny`, still denies `wb install`, `wb upgrade`,
  `wb approve` and every `python3 -m workbench` spelling, and holds the `wb gate-command claude` hook.
- In a new session in that project, `wb add <absolute path> --package … --select code-work` ran with no prompt and no typed digest and
  wrote 40 paths. The level log gained `A … wb add none digest:<64 hex>` and then `O … done written` (Increment G, first run under a
  harness).
- `wb run safe-git commit --expected-head none --subject 'Add notes on mapping and padding' -- docs/notes.md` was not blocked by the
  gate with `wb add` relaxed (Increment I: the subject holds `Add` and `padding`). The first attempt failed in git with exit 128 because
  the throwaway repository had no author identity; after the owner set one the same command made the commit.
- Blocked: `echo add; wb check` (the compound-command cost) and `python3 -m workbench add …`. `wb approve-plan` was denied by the
  harness's own rule, with no gate message.

**Not covered:** `wb upgrade`, `wb approve` and `wb pin` at `none` were not run by an agent, and the gate was not tried with
`wb approve` relaxed (`wb approve-plan` alongside it). The commands of Increments J and K are not built.

### Increment J — built, not committed (2026-10-27)

**Done.** The owner answered three questions before the build. (1) `wb acknowledge` at `none` is governed by the checkpoint
`acknowledge-first-tier` alone: every path the command can list has a baseline, so it is first-tier material, and the command has no
notion of a tier. (2) `acknowledge-second-tier` offers `none` and is documented as governing no installer command today. (3) `attach`
and `release-approvals` have no terminal test, so an unattended run at a verified `none` is logged and they go on exactly as before at
any other level, with no new refusal. Built: `levels._OFFERS` gives `acknowledge-first-tier`, `acknowledge-second-tier`, `wb recover`,
`wb attach` and `wb release-approvals` the levels `block` and `none`; `levels.COMMAND_OF_CHECKPOINT` makes the first-tier key stand for
the `acknowledge` command in the rendering (`key_patterns`, so the `deny` of `wb acknowledge` is not rendered at `none`) and in the
command gate (`words`). `acknowledge.run` and `recover.run` take `log`, which `cli._levelled` gives them at a verified `none`; they
print the same list and digest, ask nothing, examine again, and the attempt (`digest:` the digest shown) is written just before the
baselines or the first removal and the outcome after. `acknowledge` compares the project listed with the one the level was read for;
`recover` compares nothing, because the marker of a failed `install` is in a new directory and its record is unauthenticated text.
`attach` and `release-approvals` are wrapped whole by `cli._unattended_call`, so a refusal is logged too, with no evidence. A refused
run without a terminal and without a store no longer creates the store (`cli._refuse_without_store`), for `acknowledge`, `recover` and
also `upgrade` and `add`, where Increment G had lost that guarantee.

**Verification as run.** `tests/test_ack_recover_levels.py` was written first and failed against the old code for the right reasons;
it now has 39 tests, and `LiteralRunCommands`/the gate file has a test for the first-tier key. The full suite found two stale offers
tests, one `test_settings` test that used `wb attach` as its not-offered key, and the guarantee that a refused `acknowledge` creates
no store (a real regression, fixed); after those, `python3 -B -W error tests/run_all.py`: `Ran 5127 tests in 10 roots`, `OK`, and the
final run: `Ran 5129 tests in 10 roots`, `OK`. `wb check` and the plan check: no problems. **Not verified:** nothing under a real harness for these five keys;
`attach` and `release-approvals` are tested with the command mocked.

**Review.** One round by the `reviewer` agent: no blocking findings. Applied: a gate test for the first-tier key, a test that an
undeclared checkpoint leaves no key (the command reads `block`), tidied two weak tests, and the spec now says that `acknowledge` also
moves pins, that an unwritable log refuses these two commands at a verified `none`, that the launcher wrapper is refreshed before the
attempt, and that a read failure adds its reason to the refusal. Recorded, not changed: no test of a real `attach` at `none`.

**Security review (J, read only; the reviewer's probes were refused).** No Critical or High finding. Medium, a consequence of the
owner's answer on logging and left for the owner: an agent can run `attach` or `release-approvals` unlogged at a verified `none` by
choosing a working directory where the level cannot be read (no project, a decoy `.git` with an unreadable manifest, a deleted
directory), because the command then goes on as before; the spec now says so and calls the log a record and not a control. The
owner may ask for these runs to be refused where no level is readable, as a separate change. Low, applied: a `recover` marker that
names a project must name the one the level was read for (a forged marker can name none, so this stops a mistake only); exit 130 is
logged as `interrupted before writing` and not as a write; a test pins that the `deny` of `wb acknowledge` is still rendered when no
module declares the checkpoint (the reviewer doubted it; the static list of every owner-run command covers it). Low, documented: `attach`
compares no target with the project the level was read for, as `install` does not. Sound (read only): `effective_level` and the
rendering record, the second-tier key alone not opening `acknowledge`, a duplicate or foreign declaration of the checkpoint, the
project check and the digest binding of `acknowledge`, the target identity and canonical form of the marker, the removals of
`recover` bounded to the recorded empty directories, `_refuse_without_store` with links, and the clean one-line reasons. Not tested by
the reviewer: any experiment. `tests/test_ack_recover_levels.py` is now 41 tests.

### Increment K — built, not committed (2026-10-27)

**Done.** The checkpoint `accept-decision`, which the process module already declared, now offers `block` and `none` (`levels._OFFERS`)
and defaults to `block`; `wb settings` prints `level accept-decision: <level>` as for every key. The `draft-decision` skill of the
groundwork module tells the agent to run `wb settings` from the project directory and to mark a record it drafted `Accepted` only while
the output holds a line that begins `level accept-decision: none`; on any other line, a missing line or a failing command it stops at
`Proposed`, and a file, a review or a reply is never that level. The skill's one allowed command is `wb settings`; its "Do not run
commands" sentence is relaxed for this skill only, and a test pins the new sentence. `docs/specs/command-permissions.md` no longer says
"Planned": the section is "A level for every command", described as built, with the acceptance criteria P1 to P6 mapped to the tests
that cover them, `docs/specs/code-work.md` lists the built behavior of `accept-decision`, and `docs/development.md` says so. The
repository's own installed copy of the skill is not updated and the shipped approvals are not regenerated: an owner-run `wb upgrade` and
`wb acknowledge` update the first, and `wb release-approvals` at release time the second.

**Verification as run.** The offers tests, the skill test and a `wb settings` test were written first and failed; after the change,
`python3 -B -W error tests/run_all.py`: `Ran 5133 tests in 10 roots`, `OK`, and again after the review changes below:
`Ran 5133 tests in 10 roots`, `OK`. `wb check` and the plan check: no problems. **Not verified:** nothing under a real harness for K; the skill is prose, so
the test pins what it says and not what an agent does.

**Review.** One round by the `reviewer` agent: no blocking findings. Applied: the skill's description and step 6 now carry the
exception, it says to run `wb settings` from the project directory and that a line must begin with `level accept-decision: none`
(a settings note starts with `settings:` and a test pins that), and that the owner's acceptance of a superseding record is matched by
the agent's while the level is `none`; the spec says the managed block that the groundwork module writes into other projects still
says that only the owner accepts, which is stricter and wins there; a stale sentence in the `levels.py` docstring is corrected.

**The Goal and the Completion criteria, honestly.** Criteria 1 to 3, 7 and 8 are met by the tests and checks above. Criterion 4 is met
for every key built by this plan that offers `none`: `block` and `none` are accepted and a level a key does not offer reads as `block`
with a note. Criterion 5 holds for those keys; the keys that still offer `block` only are the owner-run arguments of module commands
(`wb run mempalace init`, `mine`, `wb run remote-runner fetch-overwrite`, and the review engine's `reset`, `archive`, `prune`, `amend`,
`extend`, as the plan's Deferred work says) and four checkpoints that the plan did not list: `push-shared-branch`, `submit-remote-job`,
`fetch-remote-output` and `change-direction`. The accepted decision says no key should be limited to `block`, so the Goal is **not**
fully met: those four checkpoints are not named in "Deferred work" and need the owner's decision, either that `none` has nothing to
change for them (no installer command runs them) or a later plan. Criterion 6 is guidance, not enforcement. The verification step
"a trial in a throwaway project" was run by the owner for `install`, `add` and the gate (see the two trial records above) and not for
`upgrade`, `approve`, `pin`, `acknowledge`, `recover`, `attach`, `release-approvals` or `accept-decision`.
