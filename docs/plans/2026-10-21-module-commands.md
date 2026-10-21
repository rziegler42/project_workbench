# Module commands and `wb run`

Status: In Progress
Created: 2026-10-21

Candidate: workbench-v1#module-commands
Specs: docs/specs/module-boundary.md, docs/specs/module-contract.md

## Goal

A module declares `commands`; the verifier checks them; `wb run <command> [<argument> ...]` runs the pinned
helper by the rules of `module-boundary.md` ("Module commands" and "Declaration schema"), including the
pin-path check. `dispatch.py`, the `code-work` branch in `cli.py` and `"code-work"` in the agent-safe list are
gone, and the `code-work` module offers its helper as a command. The `code-work` tests move into the module.

## Scope

- The `commands` field: parse, shape and refusals, and the command-name uniqueness rule across the selected
  modules.
- A generic resolver that finds a command from the project's committed manifest and the module's installed
  `module.json`, and refuses unless the pin names the declared helper.
- `wb run`, classified agent-safe; `launch.launch(..., kit=N)` is the only way a helper starts.
- Replacing `wb code-work` with `wb run code-work`, in the module's skill text and in the installer.
- Moving `tests/test_codework_*.py` and `tests/test_dispatch.py` into the module or rewriting them on
  synthetic modules.
- A security pass on the resolver and `wb run` (they read a hostile project and start a program).
- Showing a module's commands in the approval request (added as increment G).

## Non-goals

- `checks` and `wb check` changes (`module-checks`), including the check half of the pin-name namespace, the
  `checks` field and the report form. This plan parses no `checks`; a module that declares one is refused as
  an unknown field until that plan adds it.
- Harness paths (`module-harness-paths`), moving `groundwork`'s tests or checks, and the
  `code-work-commit` and `code-work-approval` helper subcommands.
- A change to the helper's behaviour or its subcommands. `code-work` stays a single-file, standard-library
  `exec` helper (`runtime` default), so it needs no `kit`.
- Removing a module, or any new owner-run command. `pin` and `acknowledge` are unchanged.

## Assumptions and constraints

- Python 3.14, standard library only; `python3 -B -W error tests/run_all.py` is the full test command
  (2145 tests in 2 roots at the start).
- A module's `module.json` is installed at `.workbench/<package>/<module>/module.json` and the manifest
  records each module's declaration hash. `wb run` reads the installed declaration, requires its declaration
  hash to equal the manifest's, and only then trusts it. A module the manifest does not record declares
  nothing.
- The pin store, the launcher and the runner are unchanged. The pin check added here compares the pin's
  recorded path with `.workbench/<package>/<module>/<helper>`; the launcher still verifies the bytes.
- `tests/` and `tools/` of a module are hashed and approved, so any increment that edits a first-party
  module's files changes its tree hash and needs the owner to run `python3 -m workbench release-approvals`
  (and to approve the removal of any stale shipped record) before the suite passes. I do not run it.
- Subagents and I use the commit helper per `AGENTS.md`; a commit that includes renames plus deletions may
  need the owner to commit by hand, as in the kit plan.
- Discovery tooling: none in this project (`graphify: skipped — the repository has no graph tooling`).
  Impact was taken from a repository search: `code-work` is named in `workbench/cli.py`, `dispatch.py`,
  `rules.py`, `harnessplan.py` (a comment), the module's skill, and ten test files.

## Completion criteria

1. A module with a valid `commands` field verifies; each refusal in "Declaration schema" is refused naming the
   module and the field; two selected modules (or two entries of one) that declare the same command name are
   refused at install, naming both.
2. `wb run <command>` runs a declared command with a declared first argument and passes the rest unchanged;
   a command with an empty `arguments` list takes no argument and a non-empty one requires a declared first
   argument. It refuses, running nothing, for: an undeclared first argument, an unpinned helper, a helper
   whose bytes changed, a pin under the command's name that records another path, a path outside a project,
   a module the manifest does not record, an installed `module.json` that no longer matches the manifest's
   declaration hash, and a pin that records another `kit` than the declaration (or none where one is declared, or the reverse), and a command that two modules declare.
3. `wb run` is agent-safe and `wb code-work` is gone: the installer names no `code-work` command, helper or
   entry; the module declares `commands.code-work` and its skill says `wb run code-work check`.
4. The `code-work` module's tests are under `packages/workbench/code-work/tests/` and run through
   `tests/run_all.py`; the installer's own routing tests use synthetic modules; every first-party approval
   is current.
5. Two independent security passes find no unfixed Medium or higher issue, or the plan records what was
   accepted.
6. `docs/specs/module-boundary.md`, `docs/specs/module-contract.md` and `docs/development.md` describe what was
   built; the full suite passes.

## Increments

### Increment A — The `commands` field

Outcome: the declaration parser accepts and checks `commands`; nothing runs it yet.
Dependencies: none.
Affected areas: `workbench/declarations.py` (`MODULE_FIELDS`, `Module`, `parse_module`), `tests/test_declarations.py`,
`docs/specs/module-contract.md` (module-field table and "Concrete schema").

1. Write tests first: every accepted shape and every refusal of the `commands` schema (more than 16 entries; a
   bad key; an unknown field; a wrong type; `helper` not in `ships` and not below a `ships` directory; a
   `runtime` other than `python` and `exec`; `kit` missing with `python`, present with `exec`, or below 1 or
   not an integer; a duplicate or malformed `arguments` entry; two entries naming one `helper`).
2. Add the `commands` field to `Module` as a tuple of records, with the defaults of the schema; the
   declaration hash still covers the declaration as written.
3. Update `module-contract.md` for the `commands` field only.

Verification: `python3 -B -m unittest discover -s tests -p 'test_declarations.py'`, then the full suite.
Evidence: the new tests fail before step 2 and pass after; the full suite is green; no first-party module is
changed, so no approval changes.

### Increment B — Command names are unique across the selection

Outcome: the set checks refuse a command name that two selected modules (or two entries of one module)
declare, naming both.
Dependencies: A.
Affected areas: `workbench/verify.py` (`_check_set`), `tests/test_verify.py`, `module-contract.md` ("Set checks").

1. Tests first: two modules in one package, two modules in two packages, and a single module whose two
   entries cannot share a key (the parser already refuses a duplicate key) all refuse; a name declared once
   passes; an unselected module that declares the name does not count.
2. Add the rule to `_check_set`; the message names both modules. The rule is written for command names; the
   check half of the namespace is `module-checks`' to add.
3. Change the "Set checks" sentence in `module-contract.md` from "not built yet" to what is built.

Verification: `test_verify.py`, then the full suite. Evidence: tests fail before and pass after.

### Increment C — The resolver

Outcome: a function that turns a working directory, a command name and the arguments into a launch request,
or a refusal, by the rules of the specification. It runs nothing.
Dependencies: A.
Affected areas: new `workbench/commands.py`; a generic project fixture in the shared test support
(`tests/support_project.py`, derived from the install fixture in `tests/test_codework_fixture.py`);
`tests/test_commands.py`.

1. Tests first, on synthetic modules installed into a real project by the existing install path: each refusal
   in completion criterion 2 that the resolver can decide (not the exit code, the output, or a helper whose
   bytes changed: only the launcher sees the bytes, and that case is tested in D), plus a symlinked or unreadable
   `module.json`, a `module.json` with a hostile declaration, a manifest naming a module whose files are
   missing, and the arguments rules for empty and non-empty `arguments` lists.
2. `commands.resolve(guarded, start, name, args)`: find the root and ID with the kit's finder and reader, read
   the committed manifest with the strict reader, find the modules it records, read each candidate's installed
   `module.json` with the no-follow reader, require its declaration hash to equal the manifest's, parse it with
   `declarations.parse_module`, and take the command. Look up the pin by command name and require its path to
   equal `.workbench/<package>/<module>/<helper>` exactly; return the pin name, the root, the helper's
   arguments and the `kit` number (or `None` for `exec`).
3. The function reads only; it does not call the launcher.

4. Added after the increment's security review, on the owner's instruction (2026-10-21): the pin records how
   the helper runs. A pin gains an optional `kit` (an integer of at least 1, absent for `exec`);
   `pins.set_pin` and the owner-run `pin` command take `--kit N`, show it in the confirmation, and record it.
   `resolve` refuses unless the pin's `kit` equals the declaration's (`None` for `exec`), because the manifest
   and `module.json` are both in the project and a pulled commit can edit both and recompute the declaration
   hash. `arguments` stays a filter against mistakes; the spec says so and says the helper validates its own.
   Affected areas grow by `workbench/pins.py`, `workbench/cli.py` (the `pin` options and usage),
   `tests/test_pins.py`, `tests/test_cli.py` and `module-boundary.md`.

Verification: `test_commands.py`, `test_pins.py`, then the full suite. Evidence: each refusal is a test that
runs nothing (a recording helper proves it).

### Increment D — `wb run`

Outcome: `wb run <command> [<argument> ...]` works from anywhere in a project and is agent-safe.
Dependencies: C.
Affected areas: `workbench/cli.py`, `workbench/rules.py` (`AGENT_SAFE`, and `OWNER_RUN` is unchanged),
`tests/test_cli.py`, `tests/test_permissions.py`, the usage text.

1. Tests first: the exit code of the helper reaches the caller; arguments after the first reach the helper
   unchanged, including ones that look like options; a refusal prints one `refused:` line and exits 1; a usage
   error exits 2; a pinned helper whose bytes are changed after pinning is refused with exit 1 and a
   `refused:` line, and a recording helper proves it did not run; `run` is in the agent-safe list and in the rendered permission rules.
2. Add `run` to the command table and `AGENT_SAFE`; open the guarded store and check the wrapper as `check`
   does; call `commands.resolve` and then `launch.launch(..., kit=N)`; print nothing of its own on success so
   the helper's streams stay clean.
3. Leave `wb code-work` in place in this increment, so there is never a commit where neither works.

Verification: the new tests, `test_cli.py`, `test_permissions.py`, the full suite. Evidence: synthetic modules
for both runtimes (`exec` and `python` with a kit number) run through `wb run`.

### Increment E — `code-work` becomes a command; the old route is removed

Outcome: the `code-work` module declares `commands.code-work`; its skill says `wb run code-work check`;
`dispatch.py`, the `code-work` branch in `cli.py`, its usage line and `"code-work"` in `AGENT_SAFE` are gone.
Dependencies: D.
Affected areas: `packages/workbench/code-work/module.json`, the module's `draft-plan` skill,
`workbench/dispatch.py` (deleted), `workbench/cli.py`, `workbench/rules.py`, `tests/test_dispatch.py`
(deleted; its cases are already covered on synthetic modules in C and D), `docs/development.md`,
`workbench/shipped_approvals/`.

1. Declare `"commands": {"code-work": {"helper": "helper/code-work", "arguments": ["check", "plans", "report"]}}`
   (runtime `exec` by default) and change the skill text.
2. Delete `dispatch.py` and `tests/test_dispatch.py`; remove the branch, the usage line and the list entry.
3. Add a test that fails if the installer's `workbench/` names the `code-work` command (the full boundary test
   is `module-harness-paths`'; this one is for this command only).
4. The owner runs `python3 -m workbench release-approvals` and approves the removal of any stale shipped
   record. I do not run it.
5. Verify the real path end to end: install the package into a scratch project, pin the helper as the owner
   would in a test harness, and run `wb run code-work check`.

Verification: the full suite with the new approvals, and the end-to-end run. Evidence: the suite is green with
no stale-approval skip; the end-to-end output matches the helper's.

### Increment F — The `code-work` tests move into the module

Outcome: `tests/test_codework_*.py` live in `packages/workbench/code-work/tests/` and run through
`tests/run_all.py`.
Dependencies: E.
Affected areas: `tests/test_codework_fixture.py`, `test_codework_helper.py`, `test_codework_module.py`,
`test_codework_reports.py`, `tests/test_groundwork_module.py` (it uses the fixture), the shared test support,
`workbench/shipped_approvals/`.

1. Read the imports of each file. Anything shared with other tests (the install fixture) is already in the
   shared support from C; anything specific to the module moves with it. A module test imports only the
   installer, the kit, the shared support and the module's own files by path.
2. `git mv` the four files; update paths so the tests load `helper/code-work` from the module directory.
3. `tests/test_module_test_imports.py` must pass; the owner runs `release-approvals` again (the module's tree
   hash includes `tests/`).

Verification: `python3 -B -W error tests/run_all.py` reports three roots and the same number of `code-work`
tests as before (record the before and after counts). Evidence: the counts, and the package still verifies
with no `__pycache__` in it.

### Increment G — The approval request lists a module's commands

Added on 2026-10-21 at the owner's direction (the gap was recorded in the Result for A). The declaration is
already inside the approved hashes; this increment makes it readable before the owner approves.
Outcome: `request.render_module` shows each command the module declares, so the owner sees what the module
offers to run before approving it.
Dependencies: F.
Affected areas: `workbench/request.py`, `tests/test_request.py` (or the file that tests `render_module`),
`docs/specs/module-boundary.md` if it describes the request.

1. Add a section "commands it offers" after "ships code or executables": one line per command with its name,
   helper, runtime, kit when present and allowed first arguments (or "no argument"). Every string passes
   `_shown`, so a hostile name or path is cleaned. Add the command count to the `size:` line only if no test
   or record depends on its text; otherwise leave that line alone.
2. Tests: a module with commands lists each one; a module without lists no such section; a hostile command
   name and argument are cleaned; a `python` command shows its kit; the approval record and hashes are
   unchanged (the request text is not hashed).
3. If the request text of a shipped module changes, check whether `release-approvals` output changes; it should
   not, because records hold hashes only.

Verification: the full suite; `git diff --check`. Evidence: the rendered request for the real `code-work`
module, pasted into the Result.

### Increment H — Security pass, specification and result

Outcome: the resolver and `wb run` are reviewed adversarially, the specifications describe what is built, and
the plan's result is recorded.
Dependencies: G.
Affected areas: `docs/specs/module-boundary.md`, `docs/specs/module-contract.md`, `docs/development.md`, this
plan's review record and result.

1. Run the `security-reviewer` agent on `commands.py`, `wb run` and the pin-path check; the brief asks it to
   try: a project whose `.workbench/` holds a hand-written `module.json` (matching hash is impossible, but
   test a hash that matches a different module's), a symlinked `.workbench/<package>`, a pin whose path uses
   a case or Unicode variant of the installed path, argument values that look like options or contain NUL,
   a manifest naming the same module twice, a command name that is another command's prefix, and a helper
   replaced between the hash and the run.
2. Fix each finding test-first; have a second pass try to bypass the fixes (this is the repository's security
   rule, not the owner-requested plan review).
3. Bring the specifications in line (the "not built yet" marks, the inventory table rows for the dispatch and
   the `code-work` tests), record the run command in `docs/development.md`, and write the Result.

Verification: the full suite; both passes recorded. Evidence: the review record lists what was accepted and
not fixed.

## Verification

After every increment: `python3 -B -W error tests/run_all.py`, `git diff --check`, and a check that no
`__pycache__` is under `packages/`. After E and F: the owner's `release-approvals`, then the suite again.

## Risks and sensitive actions

- **A command starts a program from a hostile project.** The command comes only from a module the manifest
  records, whose installed declaration matches the recorded hash; the helper must match an owner-set pin and
  the pin must name the declared path. The security pass in H is aimed at these.
- **A sensitive action for the owner:** `release-approvals` after E and F (it writes first-party approval
  records), and `pin` for the project's own use, which stays owner-run.
- **A broken `wb run` leaves the `code-work` skill without its checker.** Increment D keeps the old route
  until E replaces it in one commit.
- **Not tested in this plan:** Linux and Windows; a venv `sys.executable`; an upgrade of a module that gains
  or loses `commands` (the pin-path check is the guard; an upgrade test is added in C if the fixture allows it,
  otherwise recorded as deferred).

## Review record

Codex review (`ask-codex review-plan`, model gpt-5.6-luna, medium effort), round 1 of 3, outcome
`changes_needed`, one finding:

- **R1-F1 (major), applied.** Increment C listed the changed-bytes refusal among the resolver's tests, but
  the resolver does not call the launcher and cannot see the bytes. Increment C now excludes it, and
  Increment D tests it through `wb run` (exit 1, a `refused:` line, a recording helper proves nothing ran).
  Recorded with `ask-codex decide R1-F1 applied` on the owner's instruction; no decision is pending.

Approved by the owner on 2026-10-21, after the one Codex round; no further round was run.

Amended on 2026-10-21 at the owner's direction: new increment G (commands in the approval request); the
security pass, specifications and result are now H. No other increment changed.

## Deferred work

- **`module-checks`:** `checks`, the report form, `wb check` running them, the check half of the pin-name
  namespace, and the move of `doccheck`, `refcheck` and `refindex` with their tests.
- **`module-harness-paths`:** the harness table and settings path from the module's `layout`, and the boundary
  test over the whole installer.
- **`code-work-plans`:** its increments F to H wait until this plan is complete and are then reconsidered.
- **Decisions index:** `docs/decisions/README.md` lacks rows for the other `2026-10-21-*` decisions.

## Result

### Increment A

`declarations.py` reads `commands` into `Module.commands`, a tuple of `Command(name, helper, runtime, kit,
arguments)`, with every shape and refusal of "Declaration schema" (at most 16 commands and 16 arguments; a
`kit` required with `python` and refused otherwise; a helper that is an item of `ships` or below one; no two
commands naming one helper). `modulefiles.py` also requires each command's helper to be a regular file of the
module, a check the parser cannot make. `module-contract.md` marks the field verified and `wb run` not built.
Two existing tests that build `Module` by hand gained the new field.
Not done, and not in the plan: `request.render_module` does not list a module's commands in the approval
request. The declaration hash covers them and the helper is shown under "ships", but the owner does not see
the command names or arguments there. This is raised with the owner for a decision before D.
Review: one read-only `workflow-reviewer` pass, no Critical, High or Medium finding. Two Low findings were
fixed: two commands naming helpers that differ only in letter case (or Unicode form) are now refused, and the
tests gained the kit, argument, key and helper cases the reviewer listed (a float `kit` or `helper` is refused
earlier, by the strict JSON loader, so those two are not `commands` cases). The third Low finding is the
approval-request gap above. The reviewer ran no adversarial probes; this increment runs nothing.
Verification: `python3 -B -W error tests/run_all.py`: 2155 tests in 2 roots, OK (2145 before). No
first-party module changed, so no approval changed.

### Increment B

`verify._check_set` refuses a command name that more than one selected module declares: rule
`command-name`, subject `command:<name>`, message naming the command and every declaring module as
`<package>/<module>`. A name declared once, several commands in one module, and an unselected module that
declares the same name all pass. (A single module cannot repeat a name; the parser already refuses a
duplicate JSON key.) `module-contract.md` "Set checks" now says command names are enforced and the check half
of the namespace is not built.
Verification: four new tests in `tests/test_verify.py` failed before the rule and pass after;
`python3 -B -W error tests/run_all.py`: 2158 tests in 2 roots, OK (2155 before). No first-party module
changed, so no approval changed. Not reviewed independently; the change is one loop mirroring the slot-owner
check.

### Increment C

`workbench/commands.py` adds `resolve(guarded, start, name, args)`, which returns
`Request(root, project_id, name, arguments, kit)` or raises `CommandError`. It reads only: the kit's finder
and ID reader, the manifest through the strict parser, then the installed `module.json` of every module whose
file the manifest lists, each through the no-follow reader and refused unless its declaration hash equals the
manifest's. It then picks the command, applies the arguments rules, looks up the pin under the command's name,
and requires the pin's path to equal `.workbench/<package>/<module>/<helper>`. Decisions the plan left open:
- A module is "installed" when the manifest's file list names its `module.json`. A harness module writes
  nothing into the project, so it declares no command here; a listed file that is missing, a link,
  unreadable, not JSON or changed refuses the whole lookup (fail closed), not only that module.
- The declaration is parsed with `first_party=True`: that flag only gates which capabilities a module may
  provide, the declaration was approved at install and its hash was just compared, and only `commands` is read.
- The pin store already refuses a pin path with a `.` segment, so there is no dot-segment case for the
  path comparison.
- Two modules declaring one command cannot be installed (increment B); the resolver still refuses it, tested
  by patching `_declared`.
`tests/support_project.py` is the generic fixture (a harness module and a synthetic `tool` module installed
by the existing install path, with a `pin` helper); `tests/test_commands.py` has 21 tests, with `launch.launch`
and `subprocess.run` patched to fail so a test proves nothing was started.
Verification: `python3 -B -W error tests/run_all.py`: 2179 tests in 2 roots, OK (2158 before). No first-party
module changed, so no approval changed. Not yet reviewed independently; the security pass is H.
Review (increment C): one `security-reviewer` pass, no Critical or High finding; it found no way to make the
resolver start a program or run a helper no pin names. Fixed: the manifest was read twice (the ID by the kit's
loose reader, the modules by the strict one), so a rename between the reads could pair one manifest's ID with
another's modules; it is now read once and the ID derived from the parsed seed (test added). Open, for the
owner (Medium): the manifest and `module.json` are both in the project, so a pulled commit that edits both and
recomputes the declaration hash makes them agree. The pin binds the helper's name, path and bytes, not how it
runs, so such a commit can change `runtime` and `kit` (a pinned Python helper declared with a kit could be
run directly as `exec`, without the isolated interpreter and the runner's kit-number check) and widen
`arguments`, which is a filter against mistakes, not a security boundary. Options: record `runtime` and `kit`
in the pin and refuse a mismatch, or check the installed declaration hash against an owner-approved one;
either way the spec should say `arguments` is not a boundary and the helper must validate its own. Also noted
for D: the resolver returns a root path that `launch` reopens, and D must catch `CommandError` and `LaunchError`.
Resolution of the Medium finding (owner chose recording the kit in the pin, 2026-10-21): a pin may record
`kit` (`pins.py`, optional field, a whole number 1 to 999999; absent means direct); `pin --kit N` records it
and the confirmation says how the helper will run; `commands.resolve` refuses unless the pin's `kit` equals
the declaration's, and tells the owner the `pin ... --kit N` command to run. Five tests in `test_commands.py`
(including a hostile commit that rewrites the declaration and the manifest from `python` to `exec`) and seven
in `test_pins.py`. `module-boundary.md`, `trust-and-approval.md`, `installer-interface.md` and `development.md`
describe it, and say `arguments` is not a boundary. The fix is new attack surface and has not been
re-reviewed; H's second pass should try to bypass it. Consequence for E: the owner pins `code-work` without
`--kit`, since it is `exec`.
Verification: `python3 -B -W error tests/run_all.py`: 2189 tests in 2 roots, OK (2158 before C). No
first-party module changed, so no approval changed.
Second security pass on that fix (`security-reviewer`): the kit comparison, the pins parse, `pin --kit`
argument handling and the error text held; two findings. Medium, fixed: `wb launch` passed no kit, so a
helper pinned with a kit ran directly. `launch.launch` now takes the kit from the pin and refuses a caller
that expects another way (`None` accepts the pin's); tests in `test_runner.py` (the pin decides, a mismatch
runs nothing, `launch.run` builds the runner command). Four existing runner tests now pin with a kit.
Low, fixed: a declared `kit` above 999999 could never be pinned; the declaration is now bounded by the same
`MAX_KIT`. The fix to `launch` has not been re-reviewed; H's pass covers it.

### Increment D

`wb run <command> [<argument> ...]` is routed in `cli.py` and implemented as `commands.run(guarded, tokens,
err, *, cwd, stdout)`, which resolves and then calls `launch.launch(..., kit=request.kit)`. It catches
`CommandError` and `LaunchError` and prints one `refused:` line (exit 1); a missing or option-like command
name is a usage error (exit 2); it prints nothing of its own on success. `run` is in `AGENT_SAFE`. `wb
code-work` is unchanged. `tests/test_run.py` has 19 tests (exit code, arguments passed unchanged, a
subdirectory, a python command started with the kit number, a changed helper refused with a recording helper
proving it did not run, unpinned, unknown command, bad argument, outside a project, usage errors, the
command line), and `test_permissions.py` shows no spelling of `run` is denied or asked.
Verification: `python3 -B -W error tests/run_all.py`: 2212 tests in 2 roots, OK (2192 before). No first-party
module changed, so no approval changed. Not reviewed independently; the security pass is H.

### Increment E

`packages/workbench/code-work/module.json` declares `commands.code-work` (helper `helper/code-work`, runtime
`exec`, arguments `check`, `plans`, `report`), so its owner pins it without `--kit`. The `draft-plan` skill says
`wb run code-work check`. `workbench/dispatch.py`, `tests/test_dispatch.py`, the `code-work` branch and usage
line in `cli.py`, and `"code-work"` in `AGENT_SAFE` are gone (removed with `claude-workflow remove`). A test in
`tests/test_run.py` fails if any installer source names `code-work` (the plan name `code-work-module` aside).
The owner ran `release-approvals` (two new records) and approved removing the two stale shipped records
(`1813e02d8908`, `402db98b6ada`). `docs/development.md`, `docs/specs/code-work.md` and
`docs/specs/module-boundary.md` say `wb run code-work ...`.
End to end: a test in `tests/test_codework_module.py` installs the real module into a scratch project,
shows `wb run code-work check` refused while unpinned, pins the shipped helper, and runs it (exit 0, nothing on
standard error); `commit`, which the declaration does not list, is refused.
Verification: `python3 -B -W error tests/run_all.py`: 2189 tests in 2 roots, OK; only the three macOS
filesystem skips remain, so no stale-approval skip. Not reviewed independently; the security pass is H.

### Increment F

`tests/test_codework_fixture.py`, `test_codework_helper.py`, `test_codework_module.py` and
`test_codework_reports.py` moved (`git mv`) to `packages/workbench/code-work/tests/` and run as a third root of
`tests/run_all.py`. They reached four installer test files (`test_attach`, `test_upgrade`, `test_install`,
`test_groundwork_fixture`), which `test_module_test_imports` forbids, and the shared support from C did not
cover them, so a new `tests/support_install.py` names exactly those fixtures (`Base`, `Upgrade`, `InstallBase`,
`Typist`, `correct`, `SEED`, `ROOT`, `HARNESS`, `groundwork`, `GROUNDWORK_AREAS`) and the module tests import
only that. `test_codework_reports.py` imports its sibling by flat name, and the "every file" test skips the
module's own `tests/` directory, which the module does not install. `tests/test_groundwork_module.py` did not
use the code-work fixture, so it is unchanged.
Verification: `python3 -B -W error tests/run_all.py`: 2189 tests in 3 roots (2035, 18 and 136), the same total
as before the move (the 136 `code-work` tests were 136 in `tests/`); no `__pycache__` under `packages/`. The owner
then ran `release-approvals` (two new records) and approved removing the two stale ones (`1c51e4df0acd`,
`ec112778f781`); with them gone only the three macOS filesystem skips remain. Not reviewed independently; H does.

### Increment G

`request.render_module` lists a "commands it offers" section after "ships code or executables": one entry per
command with its helper, how it starts (`exec`, or `python, kit N`) and either "first argument one of ..." or
"takes no argument". Every string goes through `_shown`; more than six commands get a counted header and one
line each. A module with none prints `commands it offers: none`. The `size:` line is unchanged. Hashes and
approval records are unchanged (records hold hashes, not the request text), so no `release-approvals` run was
needed. `docs/specs/trust-and-approval.md` says the request shows the commands. Five tests in
`tests/test_request.py`: none, shown in full, hostile name/helper/argument cleaned to ASCII, a long list, and
the section after the hashes.
The real module renders as: `commands it offers: code-work runs helper/code-work as exec; first argument one of
check, plans, report`.
Verification: `python3 -B -W error tests/run_all.py`: 2194 tests in 3 roots, OK (2189 before); no `__pycache__`
under `packages/`. Not reviewed independently; H covers it.
