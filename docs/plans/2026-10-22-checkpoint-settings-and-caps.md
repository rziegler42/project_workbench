# The checkpoint settings, the loop caps and the gate that refuses work on an unapproved plan

Status: Completed
Created: 2026-10-22
Candidate: workbench-v1#checkpoint-settings-and-caps
Specs: code-work, trust-and-approval, module-contract, harness-modules, installer-interface

## Goal

Give the process module's two limits a home the owner controls, and give the harness a reason to stop. Today
`plan-status` answers whether a plan is approved, but nothing makes an agent ask, and the loop caps are only words
in a spec. When this plan is done, a process module declares its checkpoints and its caps, the owner sets the caps
in the personal settings within the ceilings the module declares, an agent-safe command reports the effective
values, and a hook that the Claude harness renders refuses an edit while a plan that is under way is not approved.

When this plan is done:

- `module-contract.md`, `trust-and-approval.md`, `code-work.md`, `harness-modules.md` and `installer-interface.md`
  state the formats this plan fixes (the declaration fields, the `caps` setting, `wb settings`, `wb gate`, the
  rendered hook), and the open "setting names for checkpoints" item is closed;
- a process module can declare `checkpoints`, `caps` and the `active` argument of its approval command, and the
  verifier refuses a malformed one;
- `wb settings` (read-only, agent-safe) prints the effective checkpoint and cap values of the project's process
  module, with a note for every problem in the owner's settings;
- `wb gate claude` (the hook's command) allows an edit unless a plan the module lists as under way does not read
  `approved`, and refuses on any doubt;
- the Claude harness module provides `hooks` and renders the gate into the per-clone settings file;
- `code-work` declares its eight checkpoints and three caps, ships the `active` subcommand, and the shipped
  approvals match.

## Scope

- **The formats and the rule**, written first as spec text and a Proposed decision (increment A).
- **The declaration fields and the `caps` setting** with their verifier and loader (increment B), and the
  `wb settings` command (increment C).
- **The `code-work` side**: the checkpoint and cap declarations and the read-only `active` subcommand (increment D).
- **The gate**: `wb gate claude`, its bounded stdin reader, its path rules, and its use of `active` and the plan
  records (increment E).
- **The hook rendering**: the layout's `hooks`, the Claude module's `hooks` capability, attach, `wb check`, and a
  deny on edits to the rendered settings file (increment F).
- **Review and the release** of the shipped approvals, owner-run (increment G), then the specs, roadmap and
  decision (increment H).

## Non-goals

- **The skills, the reviewer agent and the review loop.** The caps are declared, set and readable here; what reads
  them is `increment-loop-and-review-skills` and, mechanically, `review-engine`.
- **The `delegate` value having an effect.** Every checkpoint still stops. The names are declared and readable so
  that `delegated-approval` and `push-checkpoint` have something to read; nothing here lets a reviewer give a verdict.
- **The push rule, the shared-branch list and the compaction guidance.** Separate candidates.
- **A project-level setting that lowers a cap** (`code-work.md` says a project may lower and not raise). It needs a
  generic project setting that the installer can read without naming a module; see Deferred work.
- **A hook for opencode, a gate on shell commands, and a check at commit time.** See Risks.
- A command that writes the personal settings. The owner edits the file by hand, as the checkpoints already are.
- Any change to the owner's global Claude configuration or to a real model call.

## Assumptions and constraints

- Python standard library only; tests with `unittest`; the full suite is `python3 -B -W error tests/run_all.py`.
- The installer and its tests name no first-party module, helper or path (`tests/test_boundary.py`), and, by the
  accepted decision `2026-10-22-plan-check-in-the-shipped-helper`, the installer knows nothing of plans: it never
  reads a plan and has no list of section names. The gate therefore asks the process module's pinned helper which
  paths are under way, and asks the plan records whether each is approved. It reads no plan.
- The personal settings are strict JSON in the guarded store, `{"checkpoints", "floor", "version": 1}`
  (`workbench/settings.py`); a damaged file is reported and never overwritten, and every checkpoint then stops.
  Adding a key to a version 1 file is additive: an older workbench reports an unknown entry and ignores it.
- A hook is a command the harness runs at every matching tool call. Claude Code runs a hook's command through a
  shell and treats exit code 2 as a block and any other non-zero exit as a non-blocking error, so a hook that fails
  to start does not stop the call. Both statements come from the documentation read on 2026-10-20 and must be
  re-checked against the installed version in increment A (`harness-modules.md`, "Evidence").
- **The bootstrap.** Every command, `plan-status` included, first makes sure the guarded store exists and seeds a missing
  `settings` file (`workbench/cli.py`, `_open_store`; `trust-and-approval.md`, "Initialization"). "Writes nothing" for
  `settings` and `gate` means nothing in the project and nothing in the store beyond that bootstrap. They add no other
  write, and increment A states this exception so the spec does not claim more. A strictly non-writing opener for the
  hook is not built: the first edit of a session may seed the settings, which is the same as any other command.
- The gate runs on every file edit, so it is quick in the usual case (no plan under way) and bounded in the worst.
- Discovery tooling: graphify: skipped — not installed in this project; the scope was found by reading
  `docs/specs/code-work.md`, `docs/specs/trust-and-approval.md`, `docs/specs/harness-modules.md`,
  `docs/specs/module-contract.md`, `workbench/settings.py`, `workbench/layout.py`, `workbench/harnessplan.py`,
  `workbench/planapprovals.py`, `workbench/declarations.py`, `workbench/rules.py` and the claude and code-work
  `module.json`.

### Choices (made by me; the owner may change any)

1. **The gate is the installer's, not a hook a module ships.** `wb gate claude` is an installer command, and the
   harness layout renders one fixed hook that runs it, as the layout already renders the deny rules. A module-shipped
   hook was rejected: a hook is code that runs at every tool call, and a module that could name any command there
   would widen what approval of that module covers. The installer's gate knows no plan format: it asks the process
   module which paths are under way and asks the plan records whether each is approved, the same split that
   `approve-plan` uses.
2. **The module names what is under way; the installer decides what that means.** The `approval` field gains an
   optional `active` argument (for `code-work`, `active`). `wb run`'s bounded runner runs it, with the same limits as
   `region`, and accepts one JSON line `{"format": 1, "plans": ["<root-relative path>", ...]}` of at most 32 paths.
   `code-work active` lists plans whose `Status:` is `Approved` or `In Progress`, using the helper's own reader.
3. **What the gate refuses.** The hook covers the file-editing tools (`Edit`, `Write`, `MultiEdit`, `NotebookEdit`). A
   call is allowed when the target is outside the project root, when no plan is under way, when every plan under way
   reads `approved`, or when the target is one of the plans under way (so that a status, review record or result can
   still be written). The target fields per tool are the closed table that increment A records; a tool outside the table,
   a shape that yields no target, and a shape that yields several are handled by the same rule: every target is placed
   and judged, and the call is allowed only when all of them pass. Otherwise it is refused with a message naming the plan, its state and `wb approve-plan`. Any
   doubt is a refusal: unparsable input, a target the gate cannot place, a helper that fails or times out.
4. **A total deadline of 10 seconds, then refusal.** A hook that runs past the harness's own timeout is a
   non-blocking error, which would let the call through. The gate stops itself first.
5. **The rendered command is `wb gate claude || exit 2`.** A hook whose program is missing from `PATH` exits 127,
   which Claude treats as non-blocking; the `|| exit 2` turns that into a block. The text is fixed by the layout, not
   by a module.
6. **Edits to the rendered settings file are denied to the agent.** Without this an agent that may edit
   `.claude/settings.local.json` can delete the hook. The deny covers that file and `.git/info/exclude`, which
   `harness-modules.md` already names as unprotected. The owner edits both by hand. This is the one rule beyond the
   hook and the owner may strike it (increment F is arranged so that it can be dropped alone).
7. **Declared names and values.**
   - Checkpoints (`code-work.md`, "Checkpoints"): `approve-plan`, `push-shared-branch`, `submit-remote-job`,
     `fetch-remote-output`, `change-direction`, `accept-decision`, `acknowledge-first-tier`,
     `acknowledge-second-tier`. All default to `stop`.
   - Caps: `review-rounds` (default 3, ceiling 5), `same-failure-retries` (default 1, ceiling 2),
     `reviewer-exchanges` (default 6, ceiling 12). The spec fixes the first default and ceiling and the other two
     defaults; **the ceilings 2 and 12 are my proposal.** There is no cap on increments inside an approved plan.
8. **The personal setting and the effective value.** The settings file gains `caps`: `{"<name>": <integer>}`. A cap
   the module declares is effective at the owner's value when that is an integer from 1 to the ceiling, and at the
   module's default otherwise, with a `settings:` note saying why. A cap the module does not declare is ignored with
   a note. A boolean, a float, zero and a negative number are not integers here.
9. **`wb settings` takes no argument and runs from anywhere inside a project.** The project finder is the one that
   `wb run` and `wb plan-status` use. It resolves exactly one process module (none, or more than one, is a refusal),
   reads its verified declaration and prints one line per checkpoint (`checkpoint <name>: stop`) and per cap
   (`cap <name>: <n>`), then one `settings:` line per problem. It is read-only and agent-safe.
10. **The gate is advice for a hostile agent and a stop for a mistaken one.** A `Status:` line is informational and an
    agent can change it; an agent can write through the shell. The gate stops the common failure, an agent that goes on
    after a plan was edited, and says so. The security pass tries to defeat it and the limits are recorded.

## Completion criteria

1. The five specs state the declaration fields, the `caps` setting, the two commands and the rendered hook, and
   record the Claude hook facts with the version and date they were checked; a Proposed decision records who owns what.
2. A synthetic process module's declaration with `checkpoints`, `caps` and `approval.active` verifies. A repeated or
   malformed name, a default outside 1 to the ceiling, a ceiling over 100, more than 16 checkpoints or caps, an `active`
   argument the command does not declare, and any of the three fields on another module type are refused.
3. With no `caps` in the settings, `wb settings` prints every declared default; with a valid owner value it prints that
   value; with a value of a wrong type, zero, a negative number or above the ceiling it prints the default and a
   `settings:` note; a damaged settings file prints every default and the existing damage note. It writes nothing but the bootstrap below.
4. `code-work active` lists exactly the plans whose status is `Approved` or `In Progress`, refuses what `region`
   refuses, and is read-only. Its output never exceeds the stated bound.
5. `wb gate claude` allows an edit when no plan is under way, when every plan under way is `approved`, when the target
   is outside the root, and when the target is a plan under way; it refuses with exit 2 when a plan under way is
   `not approved` or `changed since approval`. It refuses on input that is not one JSON object within the bound, a
   missing or non-string path, a path with a NUL, a link in any component that exists, a helper that fails, prints
   anything but the stated object, or exceeds the deadline, and a project with no process module that declares `approval`
   is allowed with no output. Nothing is written but the bootstrap below.
6. The Claude module renders the hook under the layout's `hooks` key exactly as the layout states it, in the same file
   as the permission rules, creates nothing a layout without `hooks` would not, and `wb check` reports a rendered hook
   that was edited. A harness layout with `hooks: none` receives no hook and attach says so.
7. The rendered deny list includes edits to the local settings file and `.git/info/exclude` (unless the owner struck
   choice 6); `plan-status` and `settings` are not denied; every spelling of the owner-run commands is still denied.
8. The full suite passes; the boundary test passes; the installer's text names no plan heading; the shipped approvals
   match and the stale records are gone.
9. An owner-run check in a scratch project with the installed Claude shows the hook refusing an edit while a plan is
   `not approved` and allowing it after `wb approve-plan`, and the result is recorded with the Claude version.

## Increments

### Increment A — The formats, the hook facts and the rule

**Outcome:** the spec text and a Proposed decision say exactly what is declared, set, reported and refused, and the
Claude hook behavior is recorded from evidence.
**Dependencies:** none.
**Affected areas:** `docs/specs/module-contract.md`, `docs/specs/trust-and-approval.md`, `docs/specs/code-work.md`,
`docs/specs/harness-modules.md`, `docs/specs/installer-interface.md`, `docs/decisions/` (one new Proposed record).
**Steps:**
1. Fetch the Claude Code hook documentation (the `technical-researcher` agent, on the owner's word, or the owner's own
   check) and record in `harness-modules.md`, "Evidence": the hook input fields for `PreToolUse`, the tool names of
   the editing tools and, for each of `Edit`, `Write`, `MultiEdit` and `NotebookEdit`, which `tool_input` field names the
   target (or targets), the meaning of exit code 2 and of every other non-zero code, the matcher syntax, the settings key
   and shape, and the hook timeout. Anything not found stays "not verified" and is not relied on.
2. Fix the declaration fields (names, bounds, defaults, the `approval.active` argument and its output object), the `caps`
   setting and its effective-value rule (choice 8), `wb settings` (choice 9), `wb gate claude` (choices 2 to 4, the
   deadline, the path rules, every refusal and what it says) and the rendered hook (choice 5), including whether
   `module-contract.md` needs a version bump.
3. State the eight checkpoint names and three caps in `code-work.md`, and mark `delegate` as having no effect until
   `delegated-approval`.
4. Write the decision record (Proposed): the installer owns the gate and the hook, the module names what is under way,
   and why neither a module-shipped hook nor a check inside `safe-git`.
**Verification:** the document checks pass; the boundary rule is restated; no spec puts a plan heading name in the
installer's text.
**Evidence:** the one local commit, trailer `Plan: 2026-10-22-checkpoint-settings-and-caps#A`. Increment B waits for
the owner's word on the decision.

### Increment B — The declaration fields and the `caps` setting

**Outcome:** the installer reads and verifies the three new declaration fields and loads the caps setting, naming no module.
**Dependencies:** A.
**Affected areas:** `workbench/declarations.py`, `workbench/settings.py`, `tests/`.
**Steps:**
1. Test first, with synthetic declarations: criterion 2 (every refusal), the fields on a process module verify, the same
   fields on a module of another type are refused, and the declaration hash changes when a field changes.
2. Test first, with a temporary store: criterion 3's loader cases (absent, valid, wrong type, zero, negative, above the
   ceiling, undeclared name, a damaged file) and that a version 1 file without `caps` still loads.
3. Add the fields to the declaration reader and the `caps` key to the settings loader and its effective-value function.
**Verification:** the new tests and `tests/test_declarations.py`, `tests/test_settings.py` pass; the boundary test passes.
**Evidence:** the one local commit, trailer `#B`.

### Increment C — `wb settings`

**Outcome:** an agent can read the effective checkpoint and cap values of the project.
**Dependencies:** B.
**Affected areas:** a new `workbench/settingscmd.py`, `workbench/cli.py`, `workbench/rules.py`,
`docs/specs/installer-interface.md`, `docs/development.md`, `tests/`.
**Steps:**
1. Test first, in a fully installed synthetic project: criterion 3, run from the root and from a subdirectory, a project
   with no process module and one with two (both refused), a damaged store, and that the project and the store are byte-identical before and after on an initialized store, and that a store with no `settings` file gains only the seeded one.
2. Write the command over the project finder and the verified declaration that `approvalcmd` already resolves; share its
   resolution rather than copy it.
3. Add `settings` to `AGENT_SAFE`; the rules tests then cover every spelling.
**Verification:** the new tests and the rules tests pass; `python3 -m workbench settings` in a synthetic project prints
the defaults and exits 0.
**Evidence:** the one local commit, trailer `#C`.

### Increment D — The `code-work` side

**Outcome:** the process module declares its checkpoints and caps and lists the plans under way.
**Dependencies:** C.
**Affected areas:** `packages/workbench/code-work/` (`helper/code-work`, `module.json`, the policy block, the plans README
text and the helper's tests), `packages/workbench/claude/tests/`.
**Steps:**
1. Test first: `active` on this repository's own plans (none are under way now) and on a corpus of plans with each status,
   a hostile corpus (a status in a fence or a quote, two status lines, no status line), the bound on the number of paths,
   its refusals, and that it changes nothing.
2. Add the `active` subcommand over the helper's existing reader and add it to the command's `arguments`; declare
   `approval.active`, the eight checkpoints and the three caps in `module.json`.
3. Policy block and README: the caps and the checkpoints as behavior, with the commands to read them (`wb settings`),
   and no harness or command name beyond what the block already uses.
**Verification:** the code-work and claude roots pass; the document checks pass.
**Evidence:** the one local commit, trailer `#D`. The shipped approvals are stale after this and wait for increment G.

### Increment E — The gate

**Outcome:** `wb gate claude` decides, from a hook's input, whether an edit may go ahead.
**Dependencies:** D.
**Affected areas:** a new `workbench/gate_hook.py` (not `gate.py`, which is the module gate), `workbench/cli.py`,
`workbench/rules.py`, `docs/specs/installer-interface.md`, `docs/development.md`, `tests/`.
**Steps:**
1. Test first, in a fully installed synthetic project with a synthetic `active` command: every case of criterion 5,
   one accepted and one malformed input for each of the four tools, a multi-target call where one target fails,
   and hostile input (invalid JSON, trailing data, an array, a huge value, a nested object, a path of the wrong type, a
   NUL, an overlong path, `..`, a symbolic link to a plan and to the outside, a path that differs only by case, a
   relative path with a different `cwd`), a helper that prints a forged object or too many paths or hangs, a store that
   is damaged, that the project and an initialized store are byte-identical before and after every case (a store with no
   `settings` gains only the seeded one), and that exit code 2 and a message are the only outputs on refusal.
2. Write the bounded stdin reader, the path placement (lexical, then `lstat` of each existing component; a target that
   cannot be placed inside or outside the root with certainty is refused), the call to `active` through the runner that
   `region` uses, the status of each plan from the records, and the 10 second deadline over the whole.
3. Classify `gate` in `workbench/rules.py` with the other read-only commands.
**Verification:** the new tests pass; the boundary test passes; a recording stand-in for the helper shows it is run once
per call and only with the declared argument.
**Evidence:** the one local commit, trailer `#E`.

### Increment F — The hook rendering

**Outcome:** attaching the Claude harness to a project with a process module renders the gate where the harness will run it.
**Dependencies:** E.
**Affected areas:** `workbench/layout.py`, `workbench/harnessplan.py`, `workbench/harnessstage.py` (where `stage` builds the
settings file from `render_permissions`), `workbench/attach.py`, `workbench/check.py` as needed,
`packages/workbench/claude/module.json` and its tests, `tests/`.
**Steps:**
1. Test first: a layout with `hooks` verifies (the event, the matcher, the settings key and the exit code come from the
   layout and are checked as data), `hooks: none` renders nothing and attach says so, the rendered file holds the hook and
   the rules together and is byte-identical on a second attach, a hook is never rendered for a project with no process
   module that declares `approval`, and `wb check` reports an edited hook.
2. Extend the layout with the hook description (replacing "No hook is built yet"), and render it: `harnessplan` builds the
   hook entry, and `harnessstage.stage` combines it with the rendered permissions into the one settings file it already
   stages (the no-hook path stays as it is). Add the Claude layout's
   `hooks` and the `hooks` capability to the Claude module. Write the command text exactly as choice 5.
3. Add the deny of choice 6 for the rendered settings file and `.git/info/exclude`, as a separate commit-sized change
   inside this increment so that the owner can drop it by reverting one hunk before the commit.
4. The owner-run check of criterion 9, in a scratch project, is listed in the Result with the Claude version.
**Verification:** the new tests, the layout, harness and attach tests pass; the owner-run check or its recorded absence.
**Evidence:** the one local commit, trailer `#F`.

### Increment G — Review and release

**Outcome:** the work is reviewed, findings are fixed, and the approvals match.
**Dependencies:** A to F.
**Affected areas:** fixes from the review, `workbench/shipped_approvals/packages/`.
**Steps:**
1. On the owner's request, a `security-reviewer` pass over the gate (hostile hook input, paths and links, a helper that
   lies, the deadline, every way to make it allow) and over the rendering (can a module or the project influence the hook's
   text), a bypass attempt by a second reviewer, and a `workflow-reviewer` pass over the plan. If the owner asks for none,
   the plan records that.
2. Fix findings with regression tests, and record each review in the Review record.
3. After the owner says "Run it for me": `python3 -m workbench release-approvals`; after a preview and the owner's
   "remove them", delete the stale records.
4. Run the full suite.
**Verification:** `python3 -B -W error tests/run_all.py` is green and the shipped-approval tests pass.
**Evidence:** the review outcome in the Review record, the records added and removed and the suite counts in the Result,
trailer `#G`.

### Increment H — Specs, roadmap and decision

**Outcome:** the documents describe the system as it is.
**Dependencies:** G.
**Affected areas:** the five specs, `docs/development.md`, `docs/roadmaps/workbench-v1.md`, the Proposed decision of A.
**Steps:**
1. "As built, and its limits" in `code-work.md`, `harness-modules.md` and `trust-and-approval.md` say what exists and
   what does not (no effect of `delegate`, no project-level lowering, the gate's limits); markers of "proposed" or "not
   built" are removed where code now exists.
2. Roadmap: record this plan's outcome in Current state, update the dependents' text if their boundary moved, and add
   the candidate for a project-level setting that the installer can read generically if the owner wants it.
3. The decision's Verification lists what is built. It stays Proposed until the owner accepts it.
**Verification:** the document checks pass; the full suite passes; a search finds no spec that still lists the gate or the
caps as unbuilt.
**Evidence:** the one local commit, trailer `#H`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots.
- `git diff --check` is clean and `git status` is clean after the last commit.
- The document checks (`doccheck`, `refcheck`) print nothing.
- The owner-run check of criterion 9, with the Claude version and the date. This repository is not an installed project,
  so the check runs in a scratch project until `self-hosting`; until then approval of this repository's own plans stays
  the owner's statement in session and this repository has no gate.

## Risks and sensitive actions

- **The gate runs at every file edit and decides on text an agent chose.** The path in the hook's input is
  attacker-controlled. The gate reads it bounded, places it without trusting a link, and refuses on doubt; the security
  pass tries a path that makes it allow.
- **A hook that fails open.** A hook that does not start, runs too long or crashes is a non-blocking error in Claude.
  Choices 4 and 5 and the tests close the cases the workbench controls; a harness version that changes the meaning of exit
  code 2 would reopen them, which is why the facts are recorded with the version (increment A) and checked by hand
  (criterion 9).
- **A lock-out.** A plan left `In Progress` with a stale record blocks every edit outside that plan until the owner runs
  `wb approve-plan` or changes the status. The refusal says so. The owner can always edit by hand and detach the harness.
- **The gate is not a boundary against a hostile agent.** The status line is writable, shell commands are not covered,
  and an agent allowed to edit the settings file could remove the hook unless choice 6 is kept. The gate stops a mistaken
  agent, and `trust-and-approval.md` keeps saying that hard stops stop at the time of the action.
- **A new field changes the declaration hash of `code-work`.** The shipped approvals are stale until increment G; the
  installer refuses to install the module from a distribution whose approvals do not match, so G is not optional.
- **A deny on the settings file the owner also edits.** The deny is for the agent's tools only; the owner's own editor
  and `!` shell are unaffected. If the owner prefers, choice 6 is dropped and the limit is recorded.
- **Hand checks need a live Claude session.** Criterion 9 is the owner's to allow and run; nothing here starts one.
- `release-approvals` and the deletion of stale records run only on the owner's exact words, as before. Reviews run only
  when the owner asks. Nothing is pushed by this plan.

## Review record

Reviewed by Codex (`gpt-5.6-luna`, effort medium) on 2026-10-22, at the owner's request. Round 1 of a bound of 3;
outcome: changes needed, two major findings, both applied. Round 2 of 3 (same model and effort): changes needed, one
major finding, applied. No finding was rejected. The round 2 fix has not been reviewed.

- R1-F1 (major, applied): increment F did not name `workbench/harnessstage.py`, where `stage` builds the settings file
  from `render_permissions`. F now lists it and says the hook is combined with the permissions there.
- R1-F2 (major, applied): the gate did not say which `tool_input` field names the target of each editing tool or how a
  call with several targets is judged. Choice 3 now says every target is judged and all must pass; increment A records
  the closed table of fields; increment E tests one accepted and one malformed input per tool and a multi-target call.
- R2-F1 (major, applied): "writes nothing" for `settings` and `gate` conflicted with `_open_store`, which every command
  runs and which creates the store and seeds a missing `settings` file. The assumptions now name that bootstrap as the one
  exception, criteria 3 and 5 say "nothing but the bootstrap", and increments C and E compare the project and the store
  before and after, including a store with no `settings`.

Security review of the gate and the hook rendering (`security-reviewer` subagent, at the owner's request, 2026-10-22,
against commits `7888314` and `23e33ad`). It stopped at its turn limit once and was resumed once for its report, so
the review is partial: it did not run the real subprocess with closed streams, NFC/NFD on a case-insensitive volume,
two process modules, damaged settings or records, a helper with non-UTF-8 or over-long output, or a `setsid`
grandchild. Its findings are untrusted input; each was reproduced or checked before it was acted on.

- S1 (medium, applied): a target spelled through a link to the project root (or `/var` for `/private/var`) was judged
  outside by its spelling and allowed. A target that is outside as spelled is now followed through its links and
  judged where it lands, the root is compared with its links followed, and a loop or an unresolvable path is a refusal
  (`os.path.ALLOW_MISSING`, which fails on a loop). Regression tests in `tests/test_gate_hook.py`, class `Placing`.
- S2 (low, applied): a harness that provides `hooks` but not `permissions` rendered no hook and said nothing about it.
  Attach now warns. Test in `tests/test_hook_render.py`.
- S3 (low, partly applied): the layout check compared the hook's `settings_key` with the permission key by exact
  case; it now folds case (test in `tests/test_layout.py`). Not applied: tying the event to `PreToolUse` and the code
  to 2 in the validator. The layout is part of the harness module the owner approves, and the validator names no
  harness; the owner's live check (criterion 9) is what shows that Claude blocks on the rendered pair.
- Observations kept: each gate run may rewrite the launcher under the store's `bin` (the documented bootstrap); whether
  a project `.claude/settings.json` can turn hooks off, and whether a re-attach renders the hook after a process
  module is added later, were not tested (the first is within the stated limit).
- The fixes have not been tried against a second reviewer. Sound and tested by the reviewer: hostile JSON of every
  shape it tried, a working directory that is not plain, links and `..` inside the root, case and Unicode spellings of
  the root and the plan, forged or malformed helper output, the 1 second deadline, and `wb gate claude || exit 2` under
  `sh` for exits 0, 1, 2, 3, 127, SIGKILL, SIGTERM and a missing `wb`.

## Deferred work

- A project-level setting that lowers a cap (and, later, adds a shared branch), read by the installer without naming a
  module, so that "a project may lower but not raise" holds.
- The effect of `delegate` and a delegate's record (`delegated-approval`, which needs `review-engine`).
- The skills and the reviewer agent that read the caps (`increment-loop-and-review-skills`).
- A hook for opencode (`verify-opencode`), and a gate over shell commands or at commit time if the security pass finds
  the file-edit gate too weak to be worth its cost.
- Approving this repository's own plans with the command, and so gating its own edits (`self-hosting`).

## Result

Increments A to H are implemented as local commits, none pushed. The full suite after G and again after H (H changes
documents only): 3069 tests in 6 roots, all passing (installer 2319 with 1 skipped, ask-codex 90, claude 32,
code-work 220 with 2 skipped, groundwork 178, safe-git 230). The document checks and `git diff --check` print
nothing.

**What was built.**

- A process module declares `checkpoints`, `caps` and `approval.active`; the verifier refuses a malformed one
  (increment B). The personal settings gain `caps` (B). `wb settings` is read-only and agent-safe (C).
- `code-work` declares its eight checkpoints (all `stop`) and three caps (`review-rounds` 3 of 5,
  `same-failure-retries` 1 of 2, `reviewer-exchanges` 6 of 12) and ships `active` (D). The shipped approvals were
  released again and the three stale records removed (G).
- `wb gate <harness>` is the installer's command, in `workbench/gate_hook.py` (E). The Claude layout renders it as a
  `PreToolUse` hook, `wb gate claude || exit 2`, with a deny on edits to `.claude/settings.local.json` and
  `.git/info/exclude` (F). The Claude module now provides `hooks`.
- The security review (G) found one Medium finding, an alias of the project root that bypassed the gate; it is
  fixed with regression tests.

**Departures from the plan's wording** (owner decision, recorded in the Proposed decision
`2026-10-22-installer-owns-the-edit-gate`):

- The gate is `wb gate <harness>` and the tool-to-field table is the harness layout's `hooks.targets`; the
  installer holds no tool name. The plan and the first spec text said `wb gate claude` with a table in the installer.
- The hook is rendered only when the harness provides `hooks`, its layout describes a whole hook (`event`,
  `timeout`, `block_code` and `targets`), and an installed process module declares `approval.active`; the plan said
  "declares `approval`". Attach warns when an `active` module is installed and no hook can be rendered.
- The same plan spelled in another case is refused and not passed. A target outside the root as spelled is followed
  through its links before it is judged.
- The specs were corrected to match (`trust-and-approval.md`, `harness-modules.md`, `module-contract.md`,
  `code-work.md`, `installer-interface.md`).

**Limits and open items.**

- **The live check (criterion 9) was made by the owner on 2026-10-22, with Claude Code 2.1.307 in auto mode,** in a
  scratch project installed with `claude`, `code-work`, `safe-git` and `groundwork` and a plan of status
  `In Progress`. Seen: with the plan not approved, `Write`, `Edit` and `NotebookEdit` of other files were each refused
  by the hook (`PreToolUse:<tool> hook error: [wb gate claude || exit 2]: refused: the plan ... is not approved; the
  owner approves it with `wb approve-plan ...``), so exit 2 blocks, and `notebook_path` is the key a `NotebookEdit`
  hook receives. An `Edit` of the plan itself was allowed. The hook ran, and the gate found the project, when Claude
  was started in a subdirectory. After `wb approve-plan` the same `Write` was allowed. `wb` was found because the shell
  that started Claude had its launcher directory on `PATH`. Not verified: `MultiEdit`, `CLAUDE_PROJECT_DIR`, the
  `PATH` of a hook when Claude is started another way, and precedence against a committed project settings file.
- **Found by the check: the rendered `Edit(...)` deny does not hold from a subdirectory.** With Claude started at
  the project root, an `Edit` of `.claude/settings.local.json` was denied by the permission rule. Started in a
  subdirectory and aimed at `../.claude/settings.local.json`, the same edit was not stopped by the rule: the hook
  ran first and, once the plan was approved, only the auto mode classifier ("Self-Modification") stopped it. The
  relative patterns are matched from the directory Claude started in. Without that classifier an agent started in a
  subdirectory could edit the hook out, and the same holds for `.git/info/exclude`. The smallest correction is to
  render the two patterns as absolute paths of the project (`//<root>/.claude/settings.local.json`) as the store's
  deny already is. It is not made; it is a new change after this plan was archived and needs the owner's direction.
- Input over 65,536 bytes is refused, so with the hook installed a `Write` of more than about 64 KiB is refused
  even when no plan is under way. Skipping the bound when no plan is under way would change the approved spec and is
  the owner's call.
- The security fixes had no second reviewer's bypass attempt, and the plan has had no `workflow-reviewer` pass;
  both were offered and not requested. The review of G was partial (see the Review record).
- The decision `2026-10-22-installer-owns-the-edit-gate` is Proposed; accepting it is the owner's act.
- `delegate` has no effect, nothing reads a cap, and a project cannot lower one (Deferred work).
- This repository is not an installed project, so its own edits are not gated until `self-hosting`; the owner's
  `~/.claude` rules still match the old tools (`global-config-migration`).
- `docs/specs/repository-boundary.md` still says plan approvals "are not built yet" in a store listing; that is an
  older plan's text and was left alone.
- The owner archived the plan (status `Completed`) on 2026-10-23, after `ask-codex archive` closed the Codex review:
  2 of 3 rounds, 3 decisions applied, 0 rejected, outcome "not converged" because round 2's major finding was applied
  and round 3 was not run. The owner's live check (criterion 9) was made after the plan was archived, on the same day (above).
