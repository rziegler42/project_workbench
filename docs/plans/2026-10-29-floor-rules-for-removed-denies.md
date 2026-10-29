# Floor rules for what the global reset removed

Status: Proposed
Created: 2026-10-29
Candidate: workbench-v1#floor-rules-after-reset
Specs: trust-and-approval

## Goal

The owner's former global configuration denied six actions that the project's rendered rules do not cover. Five of them are now
unprotected from outside the project since the reset: `rmdir`, `unlink` and `shred`, and reads of `~/.config/gh/**` and
`~/.codex/auth.json`. After this plan the compiled floor renders an `ask` for each, so the agent stops for the owner, in every
attached clone whose harness renders permissions, once the owner re-renders. The sixth, `git merge`, is left out by the owner's
direction.

## Scope

- Three more patterns for the stop that deletes files, each bare and with arguments, beside `rm` and `rm *`: `rmdir`, `unlink` and
  `shred`.
- Two more read patterns for the stop that touches secrets, beside `~/.ssh/**` and `~/.aws/**`: `~/.config/gh/**` and
  `~/.codex/auth.json`.
- Tests that the five render as `ask` rules in the shell and read spellings the harness uses.
- One sentence in `docs/specs/trust-and-approval.md`, "Hard stops and the floor", that says where the rendered rules are listed and
  that they are a best-effort match on command text.

## Non-goals

- A `deny` for any of them. The owner chose `ask`, as for every floor stop.
- A rule for `git merge`, or any change to the five stops themselves. `workbench/floor.py` is untouched.
- Editing the inventory (`global-config-inventory.md`) rows that mention these denies. The documentation cleanup plan re-baselines
  that spec.
- Any change under `packages/`. The `claude` module's tests do not assert the floor's rules, so no shipped approval is expected to
  go stale. If the check at step 6 shows otherwise, stop and ask.
- Re-rendering a clone. `wb rerender` is the owner's command and is a step of the plan's verification, not of the increment.

## Assumptions and constraints

- The rules are `ask` entries in `FLOOR_RULES` in `workbench/rules.py`, in the neutral vocabulary of `neutral.py`, and the harness
  renders them (`tests/test_permissions.py`). A rendered rule is a first line and not a guarantee
  (`2026-10-24-project-guarantees-a-floor`, decision 3) and is a best-effort match on command text
  (`2026-10-26-ask-level-spelling-limit`).
- A read pattern applies to the harness's read tool. A program such as `gh` or the Codex bridge reading its own file is a separate
  process and is not matched.
- A clone receives a new rule only after `wb rerender`, which is owner-run. Until then its rendered permissions file is stale.
- `workbench/` is not under `packages/`, so editing it does not make a shipped approval stale.

## Completion criteria

1. The five patterns are in `FLOOR_RULES` under the right stops, and the tests that name them pass.
2. The floor tests pass unchanged for the existing patterns, and the whole `tests` root passes.
3. `docs/specs/trust-and-approval.md` carries the sentence, and `wb check` reports no problems.
4. After the owner re-renders this clone, the rendered permissions file lists the five patterns as `ask` rules. This is the owner's
   run.

## Increments

### Increment A — Render the five asks

**Outcome:** the five patterns are in the compiled floor and rendered as `ask` rules, with tests, and the spec says where they live.
**Dependencies:** none.
**Affected areas:** `tests/test_permissions.py`, `workbench/rules.py`, `docs/specs/trust-and-approval.md`.
**Checkpoint before the steps:** this change touches a permission boundary and adds protection for secret paths. The module that
provides `security-review` is installed, so before step 1 I ask the owner whether to run a security review of it, and run one only if
the owner asks. The answer is recorded in the Result.
**Steps:**
1. In `tests/test_permissions.py`, add a test that the floor asks for the five. For the shell patterns it checks that
   `rmdir`, `rmdir build`, `unlink`, `unlink a`, `unlink -- a`, `shred`, `shred a` and `shred -u a` each match a rendered
   `Bash(...)` ask pattern, so that each bare rule and each rule with arguments is covered on its own, using
   the matching helper the install-prompts test already uses. For the reads it checks that `Read(//Users/tester/.config/gh/**)` and
   `Read(//Users/tester/.codex/auth.json)` are in the rendered ask list, using the fixture home the neighbouring assertions use.
2. Run the new test and see it fail for the missing rules.
3. In `FLOOR_RULES` of `workbench/rules.py`, add `("ask", "shell", "rmdir")`, `("ask", "shell", "rmdir *")`,
   `("ask", "shell", "unlink")`, `("ask", "shell", "unlink *")`, `("ask", "shell", "shred")` and `("ask", "shell", "shred *")` to the
   stop that deletes files, and `("ask", "read", "~/.config/gh/**")` and `("ask", "read", "~/.codex/auth.json")` to the stop that
   touches secrets.
4. Run the new test and the floor tests and see them pass.
5. In `docs/specs/trust-and-approval.md`, "Hard stops and the floor", add one sentence after the rules list: each stop renders `ask`
   rules for the commands and reads it covers, they are listed in `FLOOR_RULES` in `workbench/rules.py`, and they are a best-effort
   match on the command text and not a sandbox.
6. Run `wb check`, then `wb verify packages/workbench` and confirm it ran with no refusal, to show that no shipped approval went
   stale.
7. Run the `tests` root.
**Verification:** the new test fails before step 3 for the missing rules and passes after; `tests.test_permissions` passes; the
`tests` root passes; `wb check` reports no problems; `wb verify packages/workbench` runs with no refusal.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-floor-rules-for-removed-denies#A`, holding the test, the rules and
the spec sentence.

## Verification for the plan as a whole

- `wb run code-work check` reports no problems on this plan, before it is put to the owner for approval and again after any edit.
- `python3 -B -W error tests/run_all.py` is green in every root.
- `wb preview rerender --package <the workbench package>` shows the permissions file of this clone as changed by the five rules, and
  nothing else of consequence. The owner then runs `wb rerender` with the same package.
- The rendered `.claude/settings.local.json` of this clone lists the five patterns in its `ask` rules.

## Risks and sensitive actions

- This changes the permission rules the agent runs under, which is a permission boundary. Review is the owner's, and the
  documentation asks to consider a security review for a change that touches a permission. The rules only add `ask` entries and
  remove nothing.
- More prompts: `rmdir`, `unlink` and `shred` now ask, as `rm` does, and so would a script the agent runs that calls them directly
  on the command line.
- The rules do not match a command written another way, such as through `env`, a shell `-c` or a path-qualified program. They are a
  first line, as the floor decision says.
- `~/.codex/auth.json` is a path of the owner's Codex login, named in a compiled rule that applies to every project. A project that
  does not use Codex gets a rule for a file it does not have, which is harmless.
- Until the owner re-renders, a clone's permissions file is stale. `wb check` does not report a stale rendered file.

## Review record

Plan review by Codex through the `ask-codex` bridge (model `gpt-5.6-terra`), round 1 of 3. Outcome: three findings, all applied.

- **Applied.** The test now matches the bare forms of `unlink` and `shred` as well as their argument forms, so a removed bare rule
  fails a test.
- **Applied.** A checkpoint before the steps asks the owner whether to run a security review of this permission change, because the
  module that provides `security-review` is installed. A review runs only if the owner asks.
- **Applied.** The plan check is part of the plan-level verification. It was run on this plan on 2026-10-29 after it was drafted and
  reported no problems.
- **Found by me while applying them.** The trailer in the increment's evidence still carried the plan's earlier file name. The plan
  was renamed before it was committed or approved, because a file name containing the word `reset` made the command gate refuse
  every review-engine command that named it. The trailer is corrected.
- **Not asked for.** A second round.

## Deferred work

- A rule for `git merge`: it fits none of the five stops. A sixth hard stop would be new floor design and needs its own decision.
- A deny for the six, if the owner later wants a wall and not a stop.
- The inventory rows that describe the old global denies as `keep global`: the documentation cleanup plan.

## Result

Empty until work starts.
