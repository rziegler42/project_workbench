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

- The decision `2026-10-26-a-level-for-every-command` and the spec are accepted and approved by the owner. Where this plan and
  either differs, they win.
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

### Increment E — `install` and `adopt` at `none`

**Outcome:** with `wb install` or `wb adopt` set to `none` and rendered, an agent can install or adopt without a terminal and
without a typed confirmation; at `block` they refuse without a terminal as now.
**Dependencies:** D.
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
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#E`.

### Increment F — `upgrade` and `add` at `none`

**Outcome:** the same for `wb upgrade` and `wb add`, which also refuse until the owner has acknowledged a changed manifest; the
acknowledgement check is not bypassed.
**Dependencies:** D (E is not required).
**Affected areas:** `workbench/upgrade.py`, `workbench/upgradeplan.py`, `workbench/cli.py`, the upgrade tests,
`docs/development.md`, `docs/specs/installer-interface.md`.
**Steps:**
1. Write the tests first: at `none` the commands run only when the acknowledgement baselines hold and refuse, writing nothing,
   when they do not; the log has the attempt and the outcome; at `block` the terminal rules apply as now.
2. Replace the terminal test with the function from D, and keep the acknowledgement check where it is.
3. Update the development table and the spec.
**Verification:** the upgrade tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#F`.

### Increment G — `approve` and `pin` at `none`

**Outcome:** the same for `wb approve` and `wb pin`, the commands that make a package or a helper trusted.
**Dependencies:** D.
**Affected areas:** `workbench/approve.py`, `workbench/pins.py`, `workbench/cli.py`, their tests, `docs/development.md`,
`docs/specs/trust-and-approval.md`.
**Steps:**
1. Write the tests first: at `none` an approval or a pin is recorded for exactly the declaration and tree hashes it computes now,
   and the record equals the one the terminal command writes; the first-party shipped approvals are untouched; an unreadable
   package refuses with nothing written; the log has both lines.
2. Replace the terminal test with the function from D.
3. State in the spec, in the consequences, that `none` here lets an agent make a package trusted, as the decision records.
**Verification:** the approve and pin tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#G`.
**Checkpoint (owner):** this increment lets an agent make code trusted. At its end the agent asks whether to run a security review,
and does not begin H until the owner answers.

### Increment H — `acknowledge`, `recover`, `release-approvals` and `attach` at `none`

**Outcome:** the same for the remaining installer commands. `acknowledge` is set by the checkpoints `acknowledge-first-tier` and
`acknowledge-second-tier`; `attach` only loses its `deny`; `release-approvals` loses its `deny` (it never had a terminal test).
**Dependencies:** D.
**Affected areas:** `workbench/acknowledge.py`, `workbench/recover.py`, `workbench/attach.py`, `workbench/cli.py`,
`workbench/rules.py`, their tests, `docs/development.md`, `docs/specs/trust-and-approval.md`.
**Steps:**
1. Write the tests first: `acknowledge` at the tier's `none` records the baselines exactly as the terminal command does; `recover`
   clears only the marker and the empty directories it clears now; `attach` and `release-approvals` render no `deny` at `none`; the
   log is written for each that changes something.
2. Replace the terminal tests with the function from D where one exists.
3. Update the development table and the specs.
**Verification:** the affected tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#H`.

### Increment I — `accept-decision` at `none`, and the documents

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
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-27-a-level-for-every-command#I`.

## Verification for the plan as a whole

1. `python3 -B -W error tests/run_all.py` passes.
2. `wb check` reports no problems, and `wb run code-work check` reports none.
3. `wb settings` with the default personal settings prints every agent-safe key as `none` and every other key as `block`.
4. A trial in a throwaway project, run by the owner: set `wb install` to `none`, attach, and have the agent run an install with no
   terminal; then set it back to `block` and confirm it refuses. The agent describes the steps and runs none of them.
5. A security review of the permission boundary, run only if the owner asks at the checkpoints in D and G.

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
- Two increments, D and G, are checkpoints for a security review; a review runs only when the owner asks.
- Nothing is pushed, published or installed from outside, and no secret is used.

## Review record

Reviewed by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-27, at the owner's
request: two rounds of the bound of 3, converged. Round 1 returned one major finding: the plan left the owner-run arguments of
module commands at `block` only, against the accepted decision and the spec's P4 and P5. The owner chose to defer them; the spec's
"Levels offered", P4, P5 and "Not built" were narrowed, a clarification note was proposed on the decision, and the finding was
applied. Round 2 returned no meaningful findings and one minor one (the `Specs:` line omitted `module-boundary`), which was applied.
The review is not an approval; the plan stays `Proposed` until the owner approves it.

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

Empty until work starts.
