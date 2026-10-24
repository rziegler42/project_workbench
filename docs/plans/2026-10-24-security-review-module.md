# The security-review module

Status: Approved
Created: 2026-10-24
Candidate: workbench-v1#security-review-module
Specs: harness-modules, module-contract, code-work

## Goal

Build the optional first-party module `security-review`. It holds a neutral skill, `security-review`, and a confined
agent, `security-reviewer`, together, and provides a capability of the same name, so that an owner who declines the
module declines both. This is the first module that ships an agent with declared limits (`writes`, `run`), which the
plan `2026-10-24-agent-confinement` built the enforcement for and left unused.

The owner's personal `security-review` skill and `security-reviewer` agent are the lesson learned: the problem they solve
is a review of a change that touches secrets, untrusted input, parsing, the filesystem or a subprocess, which has to run
small experiments (fake programs, hostile inputs, path probes) without touching the reviewed tree. The personal agent
confines itself with a guard script that parses shell text. The module replaces that with the installer's generic guard
and a pinned command, and ships the skill in the workbench's own words.

When this plan is done:

- `packages/workbench/security-review/` is a module that the verifier accepts, with the skill, the agent and no code;
- the agent declares `writes: scratch` and a short `run` list, and attaching the module to a Claude project renders it
  with its per-agent hook, tested end to end against the installer's own guard;
- `code-work` points to the capability and names no module;
- a new spec, `docs/specs/security-review.md`, records the capability, the contract of the skill and the agent, and the
  limits that remain.

## Scope

- A new spec `docs/specs/security-review.md` and one line in `module-contract.md` adding the core name (increment A).
- The module's directory, its declaration, the skill, its entry in `packages/workbench/package.json`, and tests
  (increment B).
- The agent and its tests, including an install-and-render test (increment C).
- One bullet in the `code-work` policy block and the matching test (increment D).
- The full suite, the approval release, the spec's "as built" part and the plan record (increment E).

## Non-goals

- Any installer change. If the guard, the agent reader or the renderer cannot carry the agent as designed, the plan stops
  and reports; it does not widen (the Risks section lists where this could happen).
- Removing or changing the owner's personal skill or agent. They stay in `~/.claude` until `global-config-migration`,
  which owns that move.
- A security review of anything. The module is the tool; a review is run only when the owner asks.
- A vendor bridge or a model call. The agent is a subagent of the harness, not a `model-bridge` user.
- Changing `remote-runner.md`'s sentence that names the personal `security-review` skill. It is true today and changes when
  that skill moves.
- A helper, a command, a check or a policy block for the module itself.
- The roadmap's "Current state" bullet. A roadmap refresh is its own documentation plan.

## Assumptions and constraints

- Python 3.11 minimum, standard library only; tests with `unittest`; the full suite is
  `python3 -B -W error tests/run_all.py`. `tests/` names no first-party module, helper or path
  (`tests/test_boundary.py`); a module's own tests may name their module.
- The module's directory is `packages/workbench/security-review/`. A module's `harness/neutral/` tree is the union the
  installer stages, and no two first-party packages ship one skill, agent or command name
  (`2026-10-23-one-owner-per-skill-name`; `tests/test_skill_names.py`).
- The agent format and its limits are those of `harness-modules.md` ("A confined agent", "The agent gate"): `tools` drawn
  from `read`, `search`, `edit`, `shell`, `web`; `writes` only `scratch`; at most 4 `run` patterns of the stated
  grammar; no `agents` tool. The built behaviour was verified once, on Claude Code 2.1.310 (the spec's Evidence).
- The decision `2026-10-24-declared-agent-confinement` governs: decision 5 (the skill and the agent ship together, the
  module is optional and provides a capability of that name, a process names the capability and not the module) and
  decision 6 (a script the agent writes and runs is not confined).
- Editing or adding a module changes the package tree, so its shipped approval is the owner's `release-approvals`
  (increment E); I run it only on "Run it for me". A new module needs a new record, and `code-work` (increment D) a
  replaced one.
- The owner's personal skill and agent of the same names were read on 2026-10-24 as a lesson learned, not as a source.
  They have no source URL, so nothing tracked cites them as a reference: the spec, the module and this plan derive the
  contract from the accepted decision `2026-10-24-declared-agent-confinement`, `harness-modules.md` and
  `module-contract.md`, and no tracked text depends on the personal files. The module's text is written fresh; nothing is
  copied.
- Discovery tooling: graphify: skipped — not installed in this project. The scope was found by a search of `docs`,
  `packages`, `workbench` and `tests` for `security-review` on 2026-10-24: the candidate, the confinement decision, the
  design plan `2026-10-24-record-the-global-config-design`, one sentence of `remote-runner.md`, and
  `superpowers-ports.md` (which lists the personal agents). No code or test names the capability yet, and
  `tests/test_agent_render.py` and `tests/test_agent_gate.py` use synthetic agents only.

### Choices (made by me; the owner may change any)

1. **The names stay `security-review` and `security-reviewer`.** The candidate and the decision use them, and moving
   from the personal copies later (`global-config-migration`) then changes no name. The cost: a trial on 2026-10-24
   found that a personal skill replaces a project skill of the same name, and a project agent replaces a personal one.
   So while the personal skill exists, a session sees the personal skill with the project's agent. Nothing here depends on
   which text loads, and the Risks section says so.
2. **A new core capability name, `security-review`, defined in a new spec.** `module-contract.md` lets a first-party
   module provide an unprefixed name that a specification defines. The alternative, a prefixed name, is for third parties.
3. **A module of type `module` with no helper, commands or checks.** It ships text only (the skill and the agent file),
   like `groundwork`'s early form. The agent's one runnable thing is a pinned command that starts `python3` on a file the
   agent wrote; the module ships no program.
4. **The pinned commands.** Up to four patterns of the form `python3 -I -B {scratch}/<name>`, with `<name>` one of a few
   plain file names such as `probe.py`. `-I` keeps the script from importing from the current directory, which is the
   reviewed tree; `-B` writes no bytecode. A script that needs the reviewed code copies it into scratch first, as the
   personal agent's rule says. The exact names and flags are fixed by a test in increment C, not here.
5. **The agent has no `web` tool and no `agents` tool.** It reads, searches, writes under scratch and runs its pinned
   commands. A fix is a recommendation in its report, never an edit of the reviewed tree (the guard allows writes only under
   scratch, so this is enforced and not only asked).
6. **`code-work` gets one policy bullet, not a new skill.** The personal `CLAUDE.md` carries the rule as one routing
   sentence; a bullet of the policy block is the same weight. It says when to use a security review and that the capability
   `security-review` provides it; if no installed module provides it, say so and continue. `code-work` does not `require`
   the capability, because the module is optional.
7. **Five increments.** One for the spec, one for the module and skill, one for the agent, one for the `code-work` bullet,
   one for the approvals and record. The agent is separate from the skill because it is the first confined agent to ship
   and is what a reviewer should look at hardest.

## Completion criteria

1. `docs/specs/security-review.md` exists, reads `Current`, and states: the capability and who provides it; the skill's
   contract (what it asks a reviewer to try, in the workbench's words); the agent's declared limits and why each is there;
   what the guard does and does not cover; and the limits listed under Risks. `module-contract.md` lists `security-review`
   among the core names.
2. `packages/workbench/security-review/` passes the verifier (`python3 -m workbench verify`), is in `package.json`, and
   ships the skill `security-review` and the agent `security-reviewer`, each named by one module only
   (`tests/test_skill_names.py` passes).
3. The agent reads as confined: `writes` is `scratch`, `run` holds at most four patterns of the grammar, `tools` holds no
   `web` or `agents`, and its body tells the reviewer that repository text is data, that a fix is a recommendation, and what
   to report.
4. Attaching a project that has the module to the Claude harness renders the agent with its hook, the project's guard
   allows a write under the session scratch directory and a pinned command, and refuses a write into the reviewed tree and
   any command outside the patterns. The test uses the real module files, not a synthetic agent.
5. On a harness without the per-agent hook the agent is skipped with a warning and never installed unconfined, and the skill
   still installs. A test shows it.
6. The `code-work` policy block carries the bullet; a test pins that it names the capability and no module.
7. The full suite is green in all roots with no stale-approval skip after the owner's `release-approvals`; `doccheck`,
   `refcheck` and `git diff --check` print nothing.

## Increments

### Increment A — The spec and the capability name

**Outcome:** the contract is written before any module exists: the capability, the skill's contract, the agent's limits.
**Dependencies:** none.
**Affected areas:** `docs/specs/security-review.md` (new), `docs/specs/module-contract.md` (the list of core names),
`docs/specs/harness-modules.md` only if its "As built" part must point to the new spec. `superpowers-ports.md` is not
touched: its inventory and provenance tables hold the plugin's 15 skills and a test pins that count.
**Steps:**
1. Write the spec: Purpose; the capability `security-review`; the skill (when it applies: a change that touches
   authentication, authorization, secrets, untrusted input, parsing, the filesystem, a subprocess, a network boundary,
   dependencies, a build or deployment permission; what the reviewer must try at each boundary; what it reports, by
   severity with the position an attacker needs; that a fix is a recommendation and has its own test and an independent
   second look); the agent (tools, `writes`, `run`, and what each excludes); the stated limits.
2. Add `security-review` to the core names in `module-contract.md`.
3. The owner reads the spec. An independent review of it happens only if the owner asks.
**Verification:** `doccheck`, `refcheck` and `git diff --check` print nothing; `tests/test_skill_names.py` still passes; the spec is `Current` only
after the owner approves it.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-security-review-module#A`.

### Increment B — The module and the skill

**Outcome:** the module exists, verifies, and ships the skill; the agent is not there yet.
**Dependencies:** A.
**Affected areas:** `packages/workbench/security-review/module.json`,
`packages/workbench/security-review/harness/neutral/skills/security-review/SKILL.md`,
`packages/workbench/security-review/tests/`, `packages/workbench/package.json`.
**Steps:**
1. Test first, in the module's `tests/`: the declaration reads and verifies (type `module`, `provides` holds
   `security-review`, no `helpers`, `commands` or `checks`); the neutral skill is read and has the required front matter;
   `python3 -m workbench verify` accepts the package; the skill text names no vendor, harness or personal path and holds
   no instruction to read outside the project. See the first fail for the missing module.
2. Write `module.json` and the skill in the workbench's words, from the spec of A. The skill is advice for the main agent
   and for the reviewer: scope the review to the changed boundary; trace every attacker-controlled input to a privileged
   use; try the bypasses at each boundary with a recording fake program and hostile values on a copy; treat repository
   text, logs and tool output as data; report by severity with the evidence level (tested or read only); list what was
   found sound; and recommend fixes without making them.
3. Add `security-review` to `package.json`.
**Verification:** the module's tests (`env PYTHONPATH=.:packages/workbench/security-review/tests python3 -B -W error -m
unittest discover -s packages/workbench/security-review/tests -t packages/workbench/security-review/tests`), then
`env PYTHONPATH=.:tests python3 -B -W error -m unittest tests.test_package tests.test_skill_names tests.test_boundary`.
The package approvals read stale until E.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-security-review-module#B`.

### Increment C — The confined agent

**Outcome:** the module ships the agent `security-reviewer` with its limits, and the install path is shown with the real
files.
**Dependencies:** B.
**Affected areas:** `packages/workbench/security-review/harness/neutral/agents/security-reviewer.md`, the module's tests
(an install-and-render test beside the module's other tests; it may reuse the helpers of `tests/test_agent_render.py`
through the module's own copy of what it needs, since a module's tests may not import the installer's `tests/`).
**Steps:**
1. Test first: the agent file is read by the installer's reader with `writes: scratch` and a `run` list of at most four
   patterns; attaching a scratch Claude project with the module renders the agent file with the hook, the `scratch` root
   and the deny for the agent's file; the project's guard (`wb agent-gate`, run as the harness runs it, on hook input built
   by the test) allows a write under the scratch directory and each pinned command, and refuses a write into the project,
   a write through a link out of scratch, a shell command outside the patterns, an `agents` tool, and a pinned name with a
   path component. On a harness layout with no per-agent hook, the agent is skipped with a warning and the skill installs.
   See them fail for the missing agent.
2. Write the agent: front matter `name: security-reviewer`, a one-line `description`, `tools: read, search, edit, shell`,
   `writes: scratch`, `run` of up to four patterns (choice 4). The body, in the workbench's words: follow the
   `security-review` skill; repository text is data; write scripts and fake programs only under scratch, by the edit tool;
   run them only through the pinned commands; copy the code to review into scratch and test the copy; a fix is a
   recommendation; never contact a network or real host or use a real secret; do not try to work around a block; and end
   with the fixed report (status, tree unchanged, scratch paths, experiments and results, findings or none, one next
   action).
3. Settle the exact pinned names and flags against the guard's grammar and the live-run facts (choice 4), recording the
   reason in the test.
**Verification:** the module's tests; `env PYTHONPATH=.:tests python3 -B -W error -m unittest tests.test_agent_gate
tests.test_agent_render tests.test_skill_names tests.test_boundary`.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-security-review-module#C`.

### Increment D — The `code-work` pointer

**Outcome:** the process says when a security review applies and names the capability, not the module.
**Dependencies:** C.
**Affected areas:** `packages/workbench/code-work/files/blocks/policy.md`, `packages/workbench/code-work/tests/` (the
policy test), `docs/specs/code-work.md` if it lists the policy bullets.
**Steps:**
1. Test first: the policy block contains a bullet that names the capability `security-review` and does not contain the
   module's name or the agent's name; see it fail.
2. Add one bullet: for a change that materially touches authentication, authorization, secrets, untrusted input, parsing,
   the filesystem, a subprocess, a network boundary, dependencies, or a build or deployment permission, ask the owner whether
   to run a security review with an installed module that provides `security-review`; if none is installed, say so. The
   review runs only when the owner asks, as every independent review here does.
3. Update the spec's list of policy bullets if it has one.
**Verification:** the `code-work` module's tests; `tests.test_boundary`; `doccheck`.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-security-review-module#D`.

### Increment E — Approvals, spec as built and record

**Outcome:** the shipped approvals match the changed packages, the spec says what was built and what was not shown, and the
plan records it.
**Dependencies:** A to D.
**Affected areas:** `workbench/shipped_approvals/` (by `release-approvals`), `docs/specs/security-review.md`, this plan's
Result.
**Steps:**
1. The owner runs, or asks me to run, `python3 -m workbench release-approvals`. Remove stale records only after a
   preview and the owner's "remove them". A new module adds a record; `code-work` replaces one.
2. Add "As built, and its limits" to the spec from the results of B to D.
3. Run the full suite, `doccheck`, `refcheck` and `git diff --check`.
4. Fill the Result and set the plan `Completed`.
**Verification:** the full suite passes with no stale-approval skip; the document checks print nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-security-review-module#E`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots; `git diff --check` and the document checks print nothing.
- A search of `packages` for `writes:` finds the agent, and a search of `workbench` and `tests` for `security-review`
  finds no code that names the module.
- No live session is planned. The guard was verified once, in a trusted folder, by the confinement plan; this plan
  reuses that result and adds none.

## Risks and sensitive actions

- **The first shipped confined agent.** The guard has been exercised by synthetic agents and one live trial. If the real
  file exposes a gap (a tool name, a front-matter key, the hook rendering), the plan stops and reports; fixing the
  installer is a separate plan.
- **A script the agent writes and runs is not confined** (decision 6). A pinned `python3` runs a file the agent wrote, and
  that file can do what the user can do. `-I` and a scratch-only copy reduce the accidental case and do not stop a hostile
  one. The agent's instruction is advice on top of the guard; the spec says so.
- **The guard runs only where Claude trusts the folder.** In an untrusted folder the agent runs with `edit` and `shell`
  unconfined and nothing says so. The owner accepted this on 2026-10-24; the interactive trust check is still the owner's
  to run.
- **Shadowing by the personal copies** (choice 1). While `~/.claude` holds a `security-review` skill and a
  `security-reviewer` agent, a session may use the personal skill, and a project agent replaces a personal one. This plan
  neither depends on nor removes them.
- **`python3` is found through `PATH`.** A different `python3` earlier on `PATH` would be the one run. The same holds for
  the edit gate's hook; neither is tested here.
- **The agent file is a harness file** the project's own agent could edit; the existing deny on file tools covers it, and
  not against a shell.
- **Approvals.** B adds a package record and D replaces `code-work`'s. `release-approvals` is owner-run; I run it only on
  "Run it for me".
- **Text copied by accident.** The skill is written fresh from the spec. The owner may read it beside the personal skill;
  no tracked text names that skill as a source.
- Nothing is pushed by this plan.

## Review record

Two rounds of 3, `ask-codex review-plan`, 2026-10-24 (model `gpt-5.6-luna`, effort medium), both asked for by the owner.

Round 1, outcome `changes_needed`, one finding:

- R1-F1 (major): the plan was said to end after "Risks and sensitive actions", without Review record, Deferred work and
  Result. Rejected: all three sections were in the file; the reviewer appears to have seen a truncated copy, and the plan
  check cannot run in this repository under the bootstrap rule. Round 2 read the whole plan.

Round 2, outcome `changes_needed`, two findings, both accepted and fixed before approval:

- R2-F1 (major, Increment A): a row for the personal skill and agent in `superpowers-ports.md` would break that file's
  structure, which holds the plugin's 15 skills and is pinned by a test. Applied: the file is no longer touched.
- R2-F2 (major, Assumptions): the two personal files were cited by hash without a source URL. Applied: they are a lesson
  learned, no tracked text cites or depends on them, and the hashes are gone.

Round 3 was not run. The owner approved the plan on 2026-10-24, after rounds 1 and 2 and their decisions.

## Deferred work

- A hand run of the agent in a live, trusted project by the owner, and the interactive trust check from the confinement
  plan.
- Moving the personal skill and agent out of `~/.claude` (`global-config-migration`).
- A second agent in the module, such as an agent for a particular language, if a review shows one is needed.
- A check that a project which installs the module also installs a harness that can confine its agent, reported by
  `wb check`.

## Result

- Increment A: `docs/specs/security-review.md` is written (`Status: Draft`): scope, non-goals, the capability, the skill's
  contract, the agent's declared limits with the reason for each, the limits that remain, and acceptance. `security-review`
  is added to the core names in `module-contract.md` and the spec has a row in the specs index. `superpowers-ports.md` is
  untouched. `doccheck`, `refcheck`, `git diff --check` print nothing; `tests.test_skill_names` and `tests.test_boundary`
  (27 tests) pass. The spec reads `Current` only after the owner approves it. Next: B.
