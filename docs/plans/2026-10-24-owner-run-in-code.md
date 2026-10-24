# Owner-run arguments enforced in code

Status: Approved
Created: 2026-10-24
Candidate: none (closes a gap recorded in the remote-runner plan's Deferred work and in finding 1 of its 2026-10-24 security review; no roadmap candidate names it)
Specs: trust-and-approval, module-boundary, remote-runner, installer-interface

## Goal

A module command can declare arguments only the owner runs (`owner`, built for `review-engine`). Today that is kept only
by `deny` rules that match the text of `wb run <command> <argument>` in five spellings. `wb launch`, a path-qualified
`wb`, `env wb` and `bash -c` reach the same argument unmatched, so `remote-runner fetch-overwrite` and the five
`review-engine` owner commands are instruction only on those routes (`trust-and-approval.md`, "Outside content").

When this plan is done:

- `wb run` and `wb launch` refuse an owner-run argument of a declared command unless standard input and standard output
  are both terminals, the test `approve` and `pin` already use. The refusal does not depend on how the agent spelled the
  command, so the unmatched routes above are closed in the workbench's own code;
- `wb launch` cannot be pointed at a copy of the project whose declaration drops the `owner` list: for a pin the
  installer made, it requires the declaration at `--root` to equal the declaration hash the owner confirmed;
- the deny rules stay as the first line, and the specs say what is now enforced and what is still not.

## Scope

- The check for `wb run` (increment A).
- The check and the declaration match for `wb launch` (increment B).
- The tests of the two modules that run owner arguments, the spec and development edits, the full suite and the
  approvals (increment C).

## Non-goals

- A sandbox. An agent that allocates its own pseudo-terminal passes the terminal test, as it does for `approve`
  (`approve.py`, header). What stops it there is the deny rule and the owner's review; this plan removes the
  unmatched spellings, not that.
- Running the pinned helper file directly. It is not a workbench route; it needs the kit runner to do anything and is
  a residual, recorded in the spec.
- A new hard stop a module can declare. Out of scope, as in the remote-runner plan.
- Changing which arguments are owner-run in any module.
- A change to the pin file format.

## Assumptions and constraints

- `workbench/` and `tests/` hold only mechanism; `tests/test_boundary.py` stays green, so the tests use the synthetic
  `tool` module of `tests/test_owner_run_arguments.py`, not a first-party name.
- `launch.launch` is the shared launcher of `wb run`, `wb check` and `wb launch`; the check goes in the two entry points
  (`commands.run`, the CLI `launch` route), not in `launch.launch`, so `wb check` and the helper-to-helper call
  (`wbkit.call`) keep their behaviour. `wbkit.call` goes through `wb run`, so a helper that calls another module's owner
  argument is refused too; that is intended.
- Editing a module's tests changes its tree hash, so its shipped approval goes stale; the release is the owner's.
- graphify: skipped, not installed in this repository. The scope was verified by reading `workbench/launch.py`,
  `workbench/commands.py`, `workbench/rules.py`, `workbench/cli.py` and `tests/test_owner_run_arguments.py` on
  2026-10-24; the callers of `launch.launch` are `commands.run`, `launch.run` and the check runner.

## Choices (made by me, for the owner to accept or overturn)

1. **Enforce in code, with the terminal test.** The alternative, more deny patterns (`wb launch * <command> * -- <argument>*`),
   is still a text match and still misses `env`, a path-qualified `wb` and `bash -c`. The terminal test does not read the
   spelling.
2. **The owner uses a real terminal.** `! wb run review extend` typed into the agent's own prompt may not have a
   terminal on both ends, and would be refused as `approve` is. Increment C has the owner try it once and records what
   happens; if it is refused, the owner runs these from a terminal window, as for `approve` and `pin` today.
3. **`wb launch` verifies the declaration, not just the pin.** A pin the installer made records the hash of the
   `module.json` the owner confirmed. `launch` reads the declaration at `--root`, requires it to match that hash, and
   only then reads the `owner` list from it, so a crafted root cannot remove the list. A pin the owner typed has no
   declaration and no owner list, so it is unchanged.
4. **One shared function.** `commands.py` gets the check; `cli` calls it for `launch`. Nothing is duplicated.

## Completion criteria

1. `wb run <command> <owner argument>` and `wb launch ... <command> -- <owner argument>` exit 1 with one `refused:`
   line and run nothing when either stream is not a terminal; with both faked as terminals they run as before.
2. Every other argument of the same command, a command with no `owner` list, an owner-typed pin, `wb check` and
   `wbkit.call` of a non-owner argument behave as before.
3. A `launch` whose root holds a declaration different from the pin's confirmed one is refused for a pin the installer
   made.
4. Each new behaviour has a test that failed before the change.
5. The specs state the rule and the residual routes; `doccheck`, `refcheck` and `git diff --check` print nothing.
6. The full suite passes, and the owner has released the approvals the module test edits stale.

## Increments

### Increment A — refuse an owner-run argument in `wb run` unless the streams are terminals

**Outcome:** `wb run` runs an owner-run argument of a declared command only from a terminal.

**Dependencies:** none.

**Affected areas:** `workbench/commands.py`, `tests/test_owner_run_arguments.py` (or a new `tests/test_owner_run_code.py`).

**Steps:**

1. Tests first, with the synthetic `tool` module (arguments `check`, `report`, `wipe`; owner `wipe`): `wipe` through
   `commands.run` is refused with one `refused:` line naming the argument and the command and saying to run it from a
   terminal; nothing is launched (a spy on `launch.launch`). `wipe` with a fake stdin and stdout that report
   `isatty` true runs. `check` and `report` run with no terminal. A command with no `owner` list runs. `--provides`
   form is refused the same way. Both streams are required: one terminal and one pipe is refused.
2. Run them and see them fail.
3. `commands.owner_refusal(command, args, stdin, stdout)` returns the reason or None, using `approve.is_terminal`.
   `commands.run` takes `stdin=None` and `stdout=None` (today only `stdout`), defaulting to `sys.stdin` and
   `sys.stdout`, and calls it after `resolve` and before `launch.launch`.
4. Run the new tests, then the whole `tests/test_run.py`, `tests/test_owner_run_arguments.py` and
   `tests/test_commands*` files.

**Verification:** the tests above pass; `tests/test_boundary.py` passes.

**Evidence of completion:** the test names and the before/after result in the Result.

### Increment B — `wb launch` applies the same rule and checks the declaration

**Outcome:** `wb launch` cannot run an owner-run argument of an installer-made pin without a terminal, and cannot be
pointed at a crafted root to avoid the list.

**Dependencies:** A.

**Affected areas:** `workbench/cli.py` (the `launch` route), `workbench/launch.py` (`run`), `workbench/commands.py`
(a function that finds the declared command for a pin), `tests/`.

**Steps:**

1. Tests first: a pin the installer made for `tool`, `launch ... tool -- wipe` is refused without a terminal and runs
   with faked terminals; `-- check` runs. A root whose `module.json` has the `owner` list removed is refused because its
   declaration hash differs from the pin's. A root with no manifest, or an unreadable one, is refused for an installer-made
   pin and unchanged for an owner-typed pin. An owner-typed pin runs any argument. The existing `tests/test_runner.py`
   and `tests/test_launch.py` stay green.
2. Run them and see them fail.
3. Before `launch.launch`, when `pins.lookup` returns a pin with a `declaration`, find the declared command at `--root`
   with the code `resolve` uses, require `found.declaration == pin.declaration`, and apply `owner_refusal` to the
   arguments. Failures are `refused:` lines. Pins without a declaration are not looked up.
4. Run the new tests and the two existing files above.

**Verification:** as above; a short experiment with a fake launcher shows that a path-qualified `wb`, `env wb launch` and
`bash -c` forms are refused by the code, not matched by a rule.

**Evidence of completion:** the test names, the experiment's result, and the failing-first record.

### Increment C — consumers, specs and approvals

**Outcome:** the specs and development notes say what is enforced; the two modules that run owner arguments in their
tests still pass; the owner has released the approvals.

**Dependencies:** B.

**Affected areas:** `packages/workbench/review-engine/tests/`, `packages/workbench/remote-runner/tests/` (only where a test
runs an owner argument through the real `wb run` or `wb launch`), `docs/specs/trust-and-approval.md`,
`docs/specs/module-boundary.md`, `docs/specs/remote-runner.md`, `docs/specs/installer-interface.md`,
`docs/development.md`.

**Steps:**

1. List the tests that reach an owner argument through the real launcher: `grep` for `extend`, `reset`, `archive`,
   `prune`, `amend` and `fetch-overwrite` in those two test trees. Where one does, give it the terminal through the
   test support's seam or run the helper through the kit as the module tests already do; do not weaken the check.
2. Edit the specs: the sentence that says the rendered deny rules match `wb run` only and that other routes are
   instruction becomes "refused in the workbench's code unless both streams are terminals; the deny rules remain the
   first line; an agent with its own pseudo-terminal, and the pinned helper file run directly, are not covered".
   `module-boundary.md` and `installer-interface.md` say the same where they describe `owner` and `launch`.
   `remote-runner.md` "The overwrite" loses its list of unmatched routes except the two residuals.
   `docs/development.md` gets the new refusal in the command table.
3. Run the narrow tests, then the full suite in the background and read it with the `grep` filter.
4. Ask the owner for `release-approvals` (the edited module test trees stale two shipped approvals); preview and remove
   stale records only on the owner's word.
5. Ask the owner to run `wb run review extend` or the like once from the agent prompt with `!`, and once from a terminal
   window, and record what each did (choice 2).
6. Fill the Result.

**Verification:** `doccheck`, `refcheck`, `git diff --check` print nothing; the full suite passes; `release-approvals`
reports no stale record for the two modules.

**Evidence of completion:** the suite's totals, the grep result of step 1, the owner's two trials.

## Verification for the plan as a whole

The full suite (`python3 -B -W error tests/run_all.py`, in the background) and the document checks. Reading alone does
not prove a boundary; each refusal has a test that failed first.

## Risks and sensitive actions

- **The owner's `!` route may stop working** (choice 2). Mitigation: found and recorded in increment C before the
  plan is closed; the owner has a terminal route today for `approve` and `pin`.
- **A behaviour change in a shared path.** `commands.run` and the `launch` route are used by every module command.
  Mitigation: the check applies only to a command with a non-empty `owner` list, and the existing launcher and runner
  tests must stay green.
- **A false sense of safety.** The terminal test is a mistake guard, not a sandbox. The spec says so, as `approve.py`
  does.
- Sensitive actions: `release-approvals` and removal of stale records are the owner's; I run them only on "Run it for me"
  and "remove them". No push or commit without the owner's word.
- A security pass with an adversarial verification of this change is wanted before the plan is closed; I run it only when
  the owner asks.

## Review record

Round 1 of 3, 2026-10-24, `ask-codex review-plan`, model `gpt-5.6-luna`, effort medium (asked for by the owner).
Outcome: converged with no findings. The reviewer found the plan consistent with the current implementation, specs, tests
and repository instructions. No decision to record. Further rounds only on the owner's word.

## Deferred work

- Running the pinned helper file directly (a residual of the whole approach).
- A module-declared hard stop.
- The harness-side half of the rules for a harness that provides no `permissions`: those stay instruction only.

## Result

Increment A, 2026-10-24: `wb run` runs an owner-run argument of a declared command only when standard input and standard
output are both terminals.

- Changes: `workbench/commands.py` (`owner_refusal(name, owner, args, stdin, stdout)`; `Request` gains an `owner` field
  with an empty default; `run` takes `stdin` and defaults both streams to `sys.stdin` and `sys.stdout`, and refuses
  after `resolve` and before `launch.launch`), `tests/test_owner_run_code.py` (10 tests, synthetic `tool` module).
- Verification as run: the new tests failed first (5 failures where `wipe` ran with no terminal, and an error for the
  missing `stdin` parameter), then passed. `tests.test_run`, `test_commands`, `test_owner_run_arguments`,
  `test_boundary`, `test_launch` and `test_runner` pass. The `review-engine` module tests (325) pass unchanged, so none of
  them reaches an owner argument through `commands.run`; the `remote-runner` module tests are checked in increment C.
  `git diff --check` prints nothing.
- Decision made in the code, for the owner to accept or overturn: the terminal test reads the `stdout` the caller gave
  `run`, not only `sys.stdout`, because that is where the helper's output goes; the CLI passes none, so it reads the real
  streams.
- Not done: `wb launch` (increment B), the specs and the full suite (C); no review or security pass.

Increment B, 2026-10-24: `wb launch` applies the same rule, and for a pin the installer made it requires the
declaration at `--root` to be the one the owner confirmed.

- Changes: `workbench/commands.py` (`launch_refusal`: no check for a missing pin, which the launcher reports, or for a
  pin the owner typed; otherwise the manifest and declarations at the root are read as `resolve` reads them, the
  command's declaration must equal `pin.declaration`, then `owner_refusal` applies), `workbench/cli.py` (the `launch`
  route calls it and writes one `refused:` line, exit 1), `tests/test_owner_run_code.py` (6 more tests, 16 in all).
- Verification as run: the three refusal tests failed first (exit 0, the helper would have run), the three tests for
  unchanged behaviour passed before and after; then all 16 pass. `test_run`, `test_commands`,
  `test_owner_run_arguments`, `test_boundary`, `test_launch`, `test_runner` and `test_skill_names` pass (224 tests), as do
  the `remote-runner` module tests (104). `git diff --check` prints nothing.
- Not run: a real process under `env`, a path-qualified `wb` or `bash -c`. The refusal sits in the code every one of them
  reaches, and the unit tests drive that code; a real-process trial is left to increment C with the owner's two trials.
- Decision made in the code, for the owner to accept or overturn: an installer-made pin whose command is no longer
  declared at the root is now refused by `wb launch`, where before it ran if the hash matched. The plan says the
  declaration must match; this is the same rule with nothing to match.
- Not done: the specs, the full suite and the approvals (C); no review or security pass.
