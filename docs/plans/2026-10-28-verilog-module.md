# The verilog module

Status: Proposed
Created: 2026-10-28
Candidate: workbench-v1#verilog-module
Specs: module-contract, global-config-inventory

## Goal

Build the optional first-party module `verilog`. It holds two neutral, text-only skills for plain Verilog-2001: one for
simulation verification with Verilator and one for formal verification with SymbiYosys. The skills are written in the
workbench's words after a read of the owner's source text for accuracy; nothing is copied.

When this plan is done:

- `packages/workbench/verilog/` is a module that the verifier accepts, with the two skills, no code and no helper;
- each skill says, in its own text, that it is for plain Verilog-2001 and that SystemVerilog is out of scope;
- the skills are named by this module only (`tests/test_skill_names.py` passes);
- the inventory spec records that the blocker of its step M18 is built, and what the owner still has to do.

## Scope

- The module's declaration, the skill `verilog-verilator-sim` and its tests, and the module's entry in
  `packages/workbench/package.json` (increment A).
- The skill `verilog-sby-formal` and its tests (increment B).
- The shipped approvals, the inventory's M18 text and the plan record (increment C).

## Non-goals

- Running or installing Verilator, Yosys, SymbiYosys or any other program. The module ships text; no test runs a tool.
- SystemVerilog or VHDL. A module for either is a separate candidate with its own tools (the candidate's boundary).
- A confined agent, a helper, a command, a check or a policy block. The roadmap's outcome is two skills.
- A new capability name. The module provides nothing (choice 2).
- Removing the owner's personal skill or the routing paragraph from the personal instructions. That is step M18 of
  `global-config-migration`, which is the owner's, and it follows this plan.
- A roadmap edit. Completion of the candidate is derived from this plan's `Completed` status.
- A claim that the skills' technical advice is correct. Their structure is tested; their accuracy is read, not run
  (Risks).

## Assumptions and constraints

- Python 3.11 minimum, standard library only; tests use `unittest`; the full suite is
  `python3 -B -W error tests/run_all.py`. `tests/` names no first-party module, helper or path
  (`tests/test_boundary.py`); the module's own tests may name their module.
- The module's directory is `packages/workbench/verilog/`; its skills live under `harness/neutral/skills/<name>/SKILL.md`,
  as in `packages/workbench/security-review/`. No two first-party packages ship one skill name
  (`2026-10-23-one-owner-per-skill-name`; `tests/test_skill_names.py`).
- The dependencies of the candidate, `claude-harness` and `code-work-plans`, are complete: plans
  `2026-10-20-claude-harness` and `2026-10-21-code-work-plans` have status `Completed`.
- The source text is the owner's, in the owner's global configuration, and is not in this repository, so no tracked text
  cites a path to it. The owner said on 2026-10-28 where it is, and that both skills exist, each with a `reference.md`
  beside `SKILL.md` (the simulation skill's is the worked testbench). On that date `verilog-sby-formal/SKILL.md` has
  sha-256 `d1ed4793befb9607abfc70a6329ede265a605205040eb43ec5005d03966a92db` (9950 bytes) and
  `verilog-verilator-sim/SKILL.md` has `e7f8546221e53d650936c8b17ddc99f523940fcdcfbafc749b49e55342860165` (6280 bytes).
  The inventory recorded `18ded3133fbbc1d8891bc15ebdc84b1c115e09202dcf0fb17a44436724bac452` for the second on
  2026-10-24, so that file has changed since the inventory was written, and the inventory lists no `verilog-sby-formal`
  skill at all. Increment C corrects the inventory; the sources read are the files with the hashes above, and a different
  hash at the start of an increment means the source changed and the owner is told before it is used.
- The owner said on 2026-10-28 that a skill may ship reference files. Increment A still confirms, with the verifier and a
  test, that a `reference.md` beside `SKILL.md` is accepted and staged before relying on it; the candidate says "text only",
  so a reference file is text.
- Editing or adding a module changes the package tree, so its shipped approval is the owner's `release-approvals`
  (increment C). I run it only on "Run it for me"; the owner's level for it is `ask`, so the harness prompts.
- Discovery: found by a search of `docs`, `packages`, `workbench` and `tests` for `verilog` and `yosys` on 2026-10-28:
  the roadmap candidate, the design plan `2026-10-24-record-the-global-config-design`, the migration plan
  `2026-10-25-global-config-migration`, and the inventory. No code, test or module names either skill. No other tool
  was consulted.

### Choices (made by me; the owner may change any)

1. **Names stay `verilog-verilator-sim` and `verilog-sby-formal`.** The candidate and the inventory use them, so moving from
   the personal copies later changes no name. A personal skill of the same name replaces a project skill (observed
   2026-10-24, plan `2026-10-24-security-review-module`), so while the personal one exists a session may load it instead of
   the module's. Nothing here depends on which text loads.
2. **The module provides no capability.** A module that provides nothing is valid (`module-contract.md`), and a new core
   name is added only when a module needs it. No process needs to find these skills by capability.
3. **Three increments.** One per skill, because each needs the owner's source and its own read for accuracy, and one for
   approvals and record. The simulation skill goes first because the inventory holds its source.
4. **The skills say what to do and what not to do, not how a tool works.** Each is advice for the agent in a project that
   uses the tool: when to use it, the order of the steps, the checks that count as evidence, what to report and what not
   to claim. Tool flags the source gives are kept only where the source states them as fact; each is marked as read, not
   run (Risks).
5. **A skill states its scope first.** Its opening says it is for plain Verilog-2001, that SystemVerilog constructs are out
   of scope and what to do on meeting one (stop and tell the owner), so a user of another language is not misled.

### Questions answered by the owner on 2026-10-28

1. A source exists for `verilog-sby-formal`, with a reference file. Increment B uses it.
2. A skill may ship reference files. Each skill ships its `reference.md`, rewritten like the skill; if the verifier or the
   installer does not stage it, increment A stops and reports.

## Completion criteria

1. `packages/workbench/verilog/` passes the verifier (`python3 -m workbench verify`), is listed in `package.json`, has type
   `module`, provides nothing and ships no helper, command or check.
2. The module ships the skills `verilog-verilator-sim` and `verilog-sby-formal`, each with valid front matter, each
   beginning with its scope (plain Verilog-2001; SystemVerilog is out of scope), and `tests/test_skill_names.py` passes.
3. Neither skill's text names a vendor harness, a personal path or a harness-specific file, holds an instruction to read
   outside the project, or tells the agent to install a program.
4. The shipped approvals are released by the owner and the full suite is green in all roots with no stale-approval skip;
   `doccheck`, `refcheck` and `git diff --check` print nothing.
5. The inventory's M18 entry says its blocker is built and keeps the owner's step (remove the personal skill and the
   paragraph) as the owner's.
6. The Result says what was read and what was not run.

## Increments

### Increment A — The module and the simulation skill

**Outcome:** the module exists, verifies and ships `verilog-verilator-sim`; the formal skill is not there yet.
**Dependencies:** none; the owner's source for this skill (located, see Assumptions).
**Affected areas:** `packages/workbench/verilog/module.json`,
`packages/workbench/verilog/harness/neutral/skills/verilog-verilator-sim/SKILL.md` (and a reference file, if question 2
allows one), `packages/workbench/verilog/tests/`, `packages/workbench/package.json`.
**Steps:**
1. Read the source `SKILL.md` and `reference.md`; stop if a hash differs from the one in Assumptions and tell the owner.
   Check the skill format and the verifier for a reference file beside `SKILL.md`, and report the answer.
2. Test first, in the module's `tests/`: the declaration reads and verifies (type `module`, no `provides`, `helpers`,
   `commands` or `checks`); the skill has the required front matter and begins with its scope; its text names no vendor,
   harness or personal path, holds no instruction to read outside the project and none to install a program. See the first
   fail for the missing module.
3. Read the source for accuracy and note, in the Result, each claim that was changed or dropped and why. Write
   `module.json` and the skill in the workbench's words; copy no text.
4. Add `verilog` to `package.json`.
**Verification:** the module's tests (`env PYTHONPATH=.:packages/workbench/verilog/tests python3 -B -W error -m unittest
discover -s packages/workbench/verilog/tests -t packages/workbench/verilog/tests`), then `env PYTHONPATH=.:tests python3 -B
-W error -m unittest tests.test_package tests.test_skill_names tests.test_boundary`. The package approvals read stale until C.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-verilog-module#A`.

### Increment B — The formal-verification skill

**Outcome:** the module also ships `verilog-sby-formal`.
**Dependencies:** A; the owner's source for this skill (located, see Assumptions).
**Affected areas:** `packages/workbench/verilog/harness/neutral/skills/verilog-sby-formal/SKILL.md` and its `reference.md`,
the module's tests.
**Steps:**
1. Read the source `SKILL.md` and `reference.md`; stop if a hash differs from the one in Assumptions and tell the owner.
2. Test first: the skill has the required front matter, begins with its scope, and passes the same text checks as the
   first skill; the module now ships exactly two skills. See it fail for the missing skill.
3. Write the skill in the workbench's words. It covers the practice the source gives for SymbiYosys harnesses, induction
   failures, covers and the rule on adding an `assume` (the matter of the routing line SA6), each marked as read, not run.
**Verification:** the module's tests; `env PYTHONPATH=.:tests python3 -B -W error -m unittest tests.test_package
tests.test_skill_names tests.test_boundary`.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-verilog-module#B`.

### Increment C — Approvals, inventory and record

**Outcome:** the shipped approvals match the new package, the inventory says its M18 blocker is built, and the plan records
what was done.
**Dependencies:** A and B.
**Affected areas:** `workbench/shipped_approvals/` (by `release-approvals`),
`docs/specs/global-config-inventory.md` (the M18 and skill-row text only), this plan's Result.
**Steps:**
1. The owner runs `wb release-approvals`, or asks me to run it. A new module adds a record. Remove stale records only after
   a preview and the owner's "remove them".
2. Update the inventory: the rows for the simulation skill and its reference no longer say "blocked on that candidate";
   they say the module is built and that the owner's removal remains. Add the rows the inventory lacks for
   `verilog-sby-formal` and its reference, with the hashes read on 2026-10-28, and correct the recorded hash of the
   simulation skill, each with a provenance line (what was read, when). The M18 blocker line and its item list say the
   same, and SA6's "the workbench has none yet" is updated to name the module. Do not state a gate as met: the "recorded
   run in a project that installed the module" is the owner's (Deferred).
3. Run the full suite, `doccheck`, `refcheck` and `git diff --check`.
4. Fill the Result and set the plan `Completed`.
**Verification:** `python3 -B -W error tests/run_all.py` is green with no stale-approval skip; the document checks print
nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-verilog-module#C`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` green in all roots; `wb check` and `wb run code-work check` report no problems;
  `git diff --check` prints nothing.
- A search of `workbench` and `tests` for `verilog` finds no code that names the module (`tests/test_boundary.py`).
- No tool is run against any design. No live session is planned.

## Risks and sensitive actions

- **Source changed or missing.** The sources are the owner's personal files and one has changed since the inventory
  recorded it. If a hash differs at the start of an increment, or a file is missing, the plan stops; it does not invent
  practice.
- **Technical accuracy is not run.** No increment runs Verilator or SymbiYosys. A claim about a tool's flags or behaviour
  is read from the owner's text and marked as read; tests prove structure and scope only. The owner judges the content.
- **Shadowing by the personal copies** (choice 1). While a personal skill of the same name exists, a session may load it;
  this plan neither depends on nor removes it.
- **Text copied by accident.** The skills are written fresh. The owner may read them beside the personal text; no tracked
  text cites the personal files by path, and the hashes cited are the inventory's.
- **Approvals.** The new module needs a shipped record; `release-approvals` is owner-run, and the owner's level for it is
  `ask`. I run it only on "Run it for me".
- Nothing is pushed by this plan.

## Review record

Empty until a review is asked for.

## Deferred work

- The owner's removal of the personal skill, its reference and the routing paragraph (inventory step M18), and the
  recorded run in a project that installed the module, which the inventory names as that step's gate.
- A VHDL or SystemVerilog module, if the owner writes one.
- A confined Verilog agent: none is in the candidate.

## Result

### Increment A

- **Read:** the source `SKILL.md` and `reference.md` of the simulation skill, read 2026-10-28. Hashes at the start matched the
  plan: `SKILL.md` `e7f8546221e53d650936c8b17ddc99f523940fcdcfbafc749b49e55342860165`, `reference.md`
  `d367e0031204321d44de74fefc534fbb64860ffaee2819c7cd3d7f75ec7f19db`. The skill is rewritten; no text is copied, and the
  testbench in `reference.md` is a new one of the same shape (a counter, a wider model cut to width, a check on the falling
  edge, reset released on a falling edge).
- **Reference file:** `workbench/neutral.py` takes bundled files anywhere below `skills/<name>/`, and `workbench/harnessplan.py`
  stages them with the item. A test reads both files through `neutral.read_items` and finds `reference.md` bundled.
- **Changed or dropped from the source:** the source's claim that the testbench "builds cleanly under `verilator --binary
  --timing -Wall` and passes 40/40 checked cycles" is dropped, because nothing was run here; every tool behaviour is marked
  as read, not run. The source's list of three web pages is dropped, because the module's text carries no link. The source
  description (over the 300-character limit of the neutral reader) is shortened. The source's `--threads` and
  `--x-assign fast` remarks are kept as read advice; the "fast" remark is reworded as a trade of speed against reset-bug
  detection.
- **Written:** `packages/workbench/verilog/module.json`, the skill and its `reference.md`, the module's tests (11), and
  `"verilog"` in `packages/workbench/package.json`.
- **Verification as run:** the module's tests, 11, OK; `tests.test_package tests.test_skill_names tests.test_boundary`, 29, OK.
  Test first: before the skill files existed the module tests failed (1 failure, 7 errors).
- **Incident:** adding any file under `packages/workbench/` made the package tree differ from its shipped approval, so the
  workbench stopped treating the clone's `claude` harness as known and the command and edit gates refused every call. The
  owner ran `wb release-approvals` twice (once before the skill files, once after) to open the gate. Increment C still runs it
  once more for the final tree. Five stale shipped records are reported as not part of the release; none was removed.
- **Not done:** no independent review (AGENTS.md: only when the owner asks); no tool was run against any design.

### Increment B

- **Read (2026-10-28):** the formal skill's `SKILL.md` (sha-256 `d1ed4793befb9607abfc70a6329ede265a605205040eb43ec5005d03966a92db`, as in Assumptions) and its `reference.md`
  (sha-256 `b4dd053746e245bb512a1d4e4c951b3f7143412bc6ea91cc52c01f0731ced559`, 11037 bytes; the plan recorded no hash for it).
- **Rewritten, not copied.** Both files open with their scope (plain Verilog-2001, SystemVerilog out of scope, stop and
  tell the owner), point to each other and to the simulation skill, and mark the advice as read, not run.
- **Changed or dropped:** the web links under "Sources" are dropped (no URLs in shipped text), with the remarks that only
  they carried (`-noverific`, the `:default` task tag). The claim that `bmc`, `prove` and `cover` all pass on a toy
  responder is kept only as "read to pass, not run here", and the same for the broken-fixture result. The description is
  shortened to fit 300 characters. Added by me: the skill says that raising the depth to change a result is also to be put
  to the owner first, the same rule as for a new `assume`; the source only warns against the depth bump.
- **Assume rule (routing line SA6):** kept as a written-source requirement, a separately named conditional task, an
  unweakened unconditional task, and results reported as conditional.
- **Written:** `verilog-sby-formal/SKILL.md` and `reference.md` under the module's neutral skills; the module's tests now
  cover both skills (13 tests), assert exactly two skills, and check the assume rule's phrases.
- **Verification as run:** test first, 2 failures and 8 errors before the skill existed; then the module's tests, 13, OK;
  `tests.test_package tests.test_skill_names tests.test_boundary`, 29, OK; `wb run code-work check` no problems;
  `git diff --check` clean. The first attempt found a 312-character description (limit 300); shortened.
- **Incident:** the gate lockout recurred as predicted; the owner ran `wb release-approvals` twice more (after the copy and
  after the description fix). Four more records are reported stale; none removed. C reruns it once for the final tree.
- **Not done:** no independent review (only when the owner asks); no tool was run against any design.
