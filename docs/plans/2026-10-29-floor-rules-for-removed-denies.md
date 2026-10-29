# Floor rules for what the global reset removed

Status: Proposed
Created: 2026-10-29
Candidate: workbench-v1#floor-rules-after-reset
Specs: trust-and-approval

## Goal

The owner's former global configuration denied six actions that the project's rendered rules do not cover. Four of them are now
unprotected from outside the project since the reset: `rmdir`, `unlink` and `shred`, and reads of `~/.config/gh/**`. After this plan
the compiled floor renders an `ask` for each, so the agent stops for the owner, in every attached clone whose harness renders
permissions, once the owner re-renders. `git merge` is left out by the owner's direction. Reads of `~/.codex/auth.json` are left
out too: the installer may not name the Codex harness, so that rule belongs to the `ask-codex` module (see Deferred work).

## Scope

- Three more patterns for the stop that deletes files, each bare and with arguments, beside `rm` and `rm *`: `rmdir`, `unlink` and
  `shred`.
- One more read pattern for the stop that touches secrets, beside `~/.ssh/**` and `~/.aws/**`: `~/.config/gh/**`.
- Tests that the four render as `ask` rules in the shell and read spellings the harness uses.
- One sentence in `docs/specs/trust-and-approval.md`, "Hard stops and the floor", that says where the rendered rules are listed and
  that they are a best-effort match on command text.

## Non-goals

- A `deny` for any of them. The owner chose `ask`, as for every floor stop.
- A rule for `git merge`, or any change to the five stops themselves. `workbench/floor.py` is untouched.
- A rule for `~/.codex/auth.json`. The boundary test forbids the installer and its tests from naming a harness, and `codex` is on
  its list (`tests/fixtures/boundary-words.json`), so that rule waits for the `ask-codex` module to declare it.
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
- A read pattern applies to the harness's read tool. A program such as `gh` reading its own file is a separate process and is not
  matched.
- A clone receives a new rule only after `wb rerender`, which is owner-run. Until then its rendered permissions file is stale.
- `workbench/` is not under `packages/`, so editing it does not make a shipped approval stale.

## Completion criteria

1. The four patterns are in `FLOOR_RULES` under the right stops, and the tests that name them pass.
2. The floor tests pass unchanged for the existing patterns, and the whole `tests` root passes.
3. `docs/specs/trust-and-approval.md` carries the sentence, and `wb check` reports no problems.
4. After the owner re-renders this clone, the rendered permissions file lists the four patterns as `ask` rules. This is the owner's
   run.

## Increments

### Increment A — Render the four asks

**Outcome:** the four patterns are in the compiled floor and rendered as `ask` rules, with tests, and the spec says where they live.
**Dependencies:** none.
**Affected areas:** `tests/test_permissions.py`, `workbench/rules.py`, `docs/specs/trust-and-approval.md`.
**Checkpoint before the steps:** this change touches a permission boundary and adds protection for secret paths. The module that
provides `security-review` is installed, so before step 1 I ask the owner whether to run a security review of it, and run one only if
the owner asks. The answer is recorded in the Result.
**Steps:**
1. In `tests/test_permissions.py`, add a test that the floor asks for the four. For the shell patterns it checks that
   `rmdir`, `rmdir build`, `unlink`, `unlink a`, `unlink -- a`, `shred`, `shred a` and `shred -u a` each match a rendered
   `Bash(...)` ask pattern, so that each bare rule and each rule with arguments is covered on its own, using
   the matching helper the install-prompts test already uses, which is moved to module level so both tests share it. It also checks
   that `rmdirs`, `unlinked a` and `shredder` are not matched, so a rule is for the command and not for a longer word. For the read
   it checks that `Read(//Users/tester/.config/gh/**)` is in the rendered ask list, using the fixture home the neighbouring
   assertions use.
2. Run the new test and see it fail for the missing rules.
3. In `FLOOR_RULES` of `workbench/rules.py`, add `("ask", "shell", "rmdir")`, `("ask", "shell", "rmdir *")`,
   `("ask", "shell", "unlink")`, `("ask", "shell", "unlink *")`, `("ask", "shell", "shred")` and `("ask", "shell", "shred *")` to the
   stop that deletes files, and `("ask", "read", "~/.config/gh/**")` to the stop that touches secrets.
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
- `wb preview rerender --package <the workbench package>` shows the permissions file of this clone as changed by the four rules, and
  nothing else of consequence. The owner then runs `wb rerender` with the same package.
- The rendered `.claude/settings.local.json` of this clone lists the four patterns in its `ask` rules.

## Risks and sensitive actions

- This changes the permission rules the agent runs under, which is a permission boundary. Review is the owner's, and the
  documentation asks to consider a security review for a change that touches a permission. The rules only add `ask` entries and
  remove nothing.
- More prompts: `rmdir`, `unlink` and `shred` now ask, as `rm` does, and so would a script the agent runs that calls them directly
  on the command line.
- The rules do not match a command written another way, such as through `env`, a shell `-c` or a path-qualified program. They are a
  first line, as the floor decision says.
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

Scope change at implementation, 2026-10-29. The rule for `~/.codex/auth.json` made the boundary test fail: the installer and its
tests may not name a harness, and `codex` is on the list in `tests/fixtures/boundary-words.json`. The owner chose to drop that
rule from this plan and have the `ask-codex` module declare it later. The plan was edited to four rules and needs the owner's
approval again, because the edit changes its scope; the earlier approval no longer applies.

## Deferred work

- A rule for `git merge`: it fits none of the five stops. A sixth hard stop would be new floor design and needs its own decision.
- A rule that asks before the harness reads `~/.codex/auth.json`, the owner's Codex login. The `ask-codex` module should declare it,
  once the accepted record `2026-10-29-workbench-asks-for-remove-submit-and-fetch` has a mechanism for a module to declare an `ask`
  rule. The policy and module asks plan carries it.
- A deny for the six, if the owner later wants a wall and not a stop.
- The inventory rows that describe the old global denies as `keep global`: the documentation cleanup plan.

## Result

Increment A is implemented and verified; the commit waits for the owner's word.

- **Security review.** The owner answered the checkpoint on 2026-10-29: no security review is needed.
- **Done.** `FLOOR_RULES` in `workbench/rules.py` has `rmdir`, `unlink` and `shred`, each bare and with arguments, under the stop
  that deletes files, and a read ask for `~/.config/gh/**` under the stop that touches secrets. The matching helper in
  `tests/test_permissions.py` moved to module level, and a new test checks the eight command forms, three look-alike words that must
  not match, and the read pattern. `trust-and-approval.md` has one bullet saying where the rendered rules are listed and that they
  are a best-effort match.
- **Scope change.** The `~/.codex/auth.json` rule was in the first draft and made `tests/test_boundary.py` fail, because the
  installer and its tests may not name `codex`. The owner dropped it from this plan and the plan was approved again. The
  `ask-codex` module declares it later (see Deferred work).
- **Verification as run.** The new test failed on `rmdir` before the rules were added, with the other floor tests passing; after the
  rules were added `tests.test_permissions` and `tests.test_boundary` ran 49 tests, OK. The `tests` root ran 3,467 tests, OK, 1
  skipped. The `claude` module's tests ran 34 tests, OK. `wb check` and `wb run code-work check` reported no problems, and
  `wb verify packages/workbench` ran with no refusal, so no shipped approval went stale. The full `tests/run_all.py` across every
  root was not run; no other module's tests depend on `workbench/rules.py` as far as the `claude` module's do, which I did not
  check beyond that.
- **Review.** One read-only reviewer pass of the increment: no blocking finding. It asked that the spec bullet be one sentence, which
  was fixed, and noted that the plan's approval state should be checked before the commit, which it was (`approved`).
- **Not done.** Completion criterion 4: the owner's `wb rerender`, then a read of `.claude/settings.local.json` for the four
  patterns. Until then this clone's rendered permissions file is stale.
- **Noticed, outside this plan.** Many existing floor rules are not guarded by any test: a rule removed from `FLOOR_RULES` would
  pass `test_the_floor_is_rendered_as_ask_rules`, which checks that what the table holds is rendered. Spot assertions cover only a
  few (`git push --force*`, `rm *`, `pip install*`, `.env`, `~/.ssh/**`). A test that pins the whole table would close that.
