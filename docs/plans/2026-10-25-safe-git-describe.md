# Build `safe-git describe` for `commit` and `remove`

Status: In Progress
Created: 2026-10-25
Candidate: none (plan 2 of the five in the split of `docs/specs/action-review.md` for `workbench-v1#action-review-engine`; it builds the facts side only, and the candidate is complete only when the engine is built, so the plan that builds the engine names the candidate)
Specs: safe-git, module-boundary, module-contract, action-review

## Goal

Build the read-only `describe` command that the accepted decision `2026-10-25-describe-interface-for-action-review`
requires, for the two actions of `safe-git` that the owner's approver reviews today: `commit` and `remove`. The facts,
error codes, caps and omission rule are already written in `docs/specs/safe-git.md` ("Describe"); the declaration form
in `module-boundary.md` and `module-contract.md`; the launcher rule in `action-review.md` ("Decided by the owner").
This plan builds them. Nothing here is a judgement about a commit: the engine (plan 3) judges.

When the plan is done:

- a module may declare `describes` on a command, and the verifier refuses the malformed forms;
- `wb run` refuses `<command> describe <action>` for an action the command does not declare;
- `wb run safe-git describe commit ...` and `describe remove ...` print one JSON object with the specified fields, facts
  and error codes, take exactly the arguments of the real command, and change nothing in the repository;
- the facts equal what the real command acts on, tested against the real command;
- a security pass has covered the new git shapes, the launcher rule and the diff computation, and its findings are fixed
  or reported;
- the specs say "built" where they said "specified, not built".

## Scope

- `workbench/declarations.py` (the `describes` field), `workbench/commands.py` (the launcher rule) and their tests.
- `packages/workbench/safe-git/helper/safe-git`: the `describe` subcommand, a split of the real commands' validation so
  that both call it, and the new git shapes (`cat-file`, `check-ignore -q`, `ls-files -z` in fixed arguments).
- `packages/workbench/safe-git/module.json` (the `describe` argument and `describes`) and the module's tests.
- The specs named above and `docs/development.md`, changed from "specified, not built" to what is built.

## Non-goals

- The engine, the rule schema, the rubric, the log, the hook, the shadow period (plans 3 to 5).
- `describe push` or any extension of `push-check` (the push gap). `describes` lists `commit` and `remove` only.
- `remote-runner describe` (M16).
- Any change to what `commit` or `remove` accept or refuse. The refactor that shares validation must leave their
  behaviour and their existing tests unchanged.
- Raising or lowering a cap in `safe-git.md`; this plan builds the numbers as written. A measured reason to change one
  goes to the owner.
- The owner's own steps: running `wb upgrade` / re-confirming the changed declaration in this repository and in any
  installed project. The agent does not run them.

## Assumptions and constraints

- **The design is settled.** The specs fix the facts, types, caps, error table, exit statuses and the launcher rule. If
  building shows one is wrong, stop and ask; do not change the spec to fit the code without the owner.
- **Standard library only**, Python helper through kit 1, as the module is today.
- **`describe` runs the real command's own validation functions** (decision, item 2). The real command is refactored so
  that its validation, up to and including `git diff --check`, is one function that `command_commit` and `describe`
  both call. `command_remove` already uses `plan_removal`, which `describe` calls too.
- **No new surface that runs a repository's program.** The three new git shapes are listed in the allowlist with fixed
  arguments, literal pathspecs and the helper's scrubbed environment; the repository is refused first if it selects a
  program, as `commit` does. The diff is computed in Python from the HEAD blob and the working-tree file, with no git
  filter, text conversion or external diff.
- **A changed declaration needs the owner.** Editing `module.json` changes the declaration hash and the helper bytes,
  so in this self-hosted repository the installed pin of `safe-git` no longer matches the source until the owner
  upgrades. Commits made during this plan use the installed copy, which stays as it is until then.
- **Tests that run git need it**, and skip with a reason without it, as the module's tests do.
- **Each increment is one reviewed local commit** made with `wb run safe-git commit`, with the `Plan:` trailer and no
  attribution. Review is the `reviewer` agent. A second-model review happens only if the owner asks.
- Discovery: graphify: skipped, no discovery tooling installed. The scope is two named Python modules, one helper and
  their tests, all read for this plan (`declarations.py` `_commands`, `commands.py` `_arguments`, `resolve` and
  `launch_refusal`, and the helper's `command_commit`, `command_remove`, `plan_removal` and `git_shape_ok`).

## Completion criteria

1. `describes` is accepted and refused as `module-boundary.md` says, and the declaration hash covers it; tests show
   each refusal and the pass.
2. `wb run` and `wb launch` refuse `describe` with a missing action, an action not in `describes`, and any `describe`
   on a command that declares none; they run a declared action; a command with no `describe` argument is unaffected.
3. For `commit` and `remove` each refusal in the "Errors" table of `safe-git.md` has a test showing `ok: false` and that
   code, and showing that the real command refuses the same input.
4. The facts equal what the real command acts on: a test makes one repository state and compares `paths`, the message
   and `head` with the real commit, and `target_paths` with the real preview.
5. The repository is byte for byte the same after every `describe` case (files, index, refs, hooks, configuration).
6. A repository that selects a program never starts it during `describe commit` or `describe remove` (marker test).
7. A value over a cap is omitted whole, named in `omitted`, with `truncated: true`; no string is cut; an object of
   exactly 196,608 bytes is accepted and one byte more omits the value that crosses it.
8. The output obeys the decision's field rules (types, bounds on `code` and `message`, `ok` true only with no error, no
   extra field), and an unknown first argument exits 1 with no object.
9. The security pass has run, its findings are recorded and each is fixed with a test or reported to the owner.
10. `python3 -B -W error tests/run_all.py`, `wb check`, `wb run code-work check`, `doccheck` and `refcheck` pass, and the
    specs no longer call the built parts "specified, not built".

## Increments

### Increment A — Verifier support for `describes`

**Outcome:** a `commands` entry may carry `describes`; the verifier accepts the valid form and refuses the malformed
ones, naming the module and field; `Command` carries the value; the declaration hash covers it as written.
**Dependencies:** none.
**Affected areas:** `workbench/declarations.py` (`Command`, `_commands`, the optional keys), tests beside
`tests/test_declarations.py` and `tests/test_owner_run_arguments.py`; the places that render or compare a `Command`
(`tests/test_request.py` constructs it positionally, so the new field takes a default).
**Steps:**
1. Write failing tests: a valid `describes`; an entry that is not a string, a duplicate, a malformed action, more than
   16 entries, one over 32 characters; a non-empty list on a command whose `arguments` lack `describe`; `describe` in
   `owner`; an empty list allowed; the field is not a pass-through for an unknown key; a changed `describes` changes
   the declaration hash.
2. Add `describes` to the optional keys and to `Command` (default empty, after `owner`), and validate it in `_commands`
   with the same helper checks `arguments` uses.
3. Run the new tests, then the declaration, request and installer tests that build a `Command`.
**Verification:** the new tests fail first for the right reason, then pass; `python3 -B -W error tests/run_all.py`
passes; `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-safe-git-describe#A`.

### Increment B — The launcher rule for a declared action

**Outcome:** `wb run <command> describe <action>` runs only when `<action>` is in the command's `describes`; `wb launch`
applies the same rule to a pinned helper of a project declaration. The rule is generic and names no module.
**Dependencies:** A.
**Affected areas:** `workbench/commands.py` (`_arguments`, which `resolve` and `launch_refusal` both call), tests in
`tests/test_run.py` / `tests/test_launch.py` style files, `module-boundary.md` ("Declaration schema", the rule).
**Steps:**
1. Write failing tests: `describe` with no action; with an action not listed; with an action listed; `describe` on a
   command whose `describes` is empty (every action refused); the same through `launch_refusal`; a typed pin with no
   declaration is left alone as today; arguments other than `describe` are unchanged.
2. In `_arguments`, after the first argument passes the existing check, when it is `describe` require a second
   argument in `command.describes`; refuse with a message that lists the declared actions.
3. Write the rule into `module-boundary.md` where it now says "when built".
**Verification:** new tests fail then pass; the existing `wb run` and launcher tests pass; `python3 -B -W error
tests/run_all.py`; `doccheck`; `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-safe-git-describe#B`.

### Increment C — The output builder and `describe remove`

**Outcome:** `wb run safe-git describe remove ...` prints the specified object. The builder (`contract`, `action`, `ok`,
`truncated`, `errors`, `facts`, the caps, the whole-value omission rule, the field checks) exists and is shared by the
next increments. `module.json` declares the `describe` argument and `describes: ["remove"]`.
**Dependencies:** A, B.
**Affected areas:** `packages/workbench/safe-git/helper/safe-git` (a `describe` dispatch, the builder, the error
mapping for the removal refusals, the new git shape `check-ignore -q`, `ls-files -z` of a path), `module.json`,
`packages/workbench/safe-git/tests/` (a new `test_safegit_describe_remove.py` and a builder test file).
**Steps:**
1. Write failing builder tests: exactly 196,608 bytes accepted, one more byte omits the value that crosses it; a string
   over 32,768 bytes, an array over 200 elements or an element over 1,024 bytes is omitted whole and named in
   `omitted` in table order; a whole number outside 0 to 2^53 − 1 is refused by the builder; `ok` is true only with no
   error; an unknown first argument exits 1 with no stdout.
2. Write failing `describe remove` tests: one test per code of the removal rows and the "both" rows of the errors table,
   each also run against the real `remove` to show it refuses; the facts of a valid removal against `plan_removal`
   and a count made by the test (`entry_total`, `size_total`, `tracked_file_total`); a tree over 10,000 entries omits
   the totals; ignored, tracked and ignore-unknown targets; a before and after snapshot of the whole repository is equal.
3. Implement the builder, the mapping of `Refused` and `Stopped` to codes (the class, never the message), and
   `describe remove` over `plan_removal`. Add the two new git shapes to the allowlist in fixed form and test that no
   other argument form passes `git_shape_ok`.
4. Declare the argument and `describes: ["remove"]` in `module.json`; the module declaration test follows.
**Verification:** the new tests fail first, then pass; the existing `remove` tests pass unchanged; a marker test with a
repository that selects a program finds no marker; `python3 -B -W error tests/run_all.py`; `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-safe-git-describe#C`.

### Increment D — Share the commit validation and give the commit refusals and scalar facts

**Outcome:** the real `commit` validates through one function that `describe commit` also calls, with no change of
behaviour; `describe commit` reports every refusal of the errors table as `ok: false` with its code, and the scalar and
list facts that need no diff (`head`, `expected_head`, `leave_other_staged`, `path_count`, `subject`, `trailers`,
`body`, `attribution_allowed`, `program_findings`, `staged_paths`, `requested_paths`, `paths`).
**Dependencies:** C.
**Affected areas:** the helper (`command_commit` split at the end of `git diff --check`; the commit part of `describe`),
`packages/workbench/safe-git/tests/` (a new `test_safegit_describe_commit.py`).
**Steps:**
1. Run the existing commit tests first and record the count; they are the guard on the refactor.
2. Write failing tests: one per commit code of the table (and the shared "both" codes), each with the real command
   refusing the same input; `ok: true` for a valid commit; the scalar facts for a valid one; an invalid path set gives an
   empty `paths` and keeps `requested_paths`; on a refusal the facts the refusal prevented are null or empty and the
   copies of arguments keep their value, and `path_count` is the number named; before and after snapshots are equal.
3. Split `command_commit`: the part through `git diff --check` becomes a function returning the checked state; the real
   command continues from it unchanged; `describe commit` calls it, catches `Refused` into a code, and stops. The
   `Refused` text is mapped to a code by the class of the check that raised it, not by matching message text (give each
   raise a code argument).
4. Do not yet add `commit` to `describes`: the change lists and the diff arrive in E.
**Verification:** the guard tests pass unchanged and with the same count; the new tests fail first, then pass; the
marker test passes for `describe commit`; `python3 -B -W error tests/run_all.py`; `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-safe-git-describe#D`.

### Increment E — The change lists, the diff and the cap, and the commit declaration

**Outcome:** `describe commit` also reports `new_paths`, `modified_paths`, `deleted_paths`, `unchanged_paths`,
`binary_paths`, `not_regular_paths` and `diff`, computed without any filter; `omitted` and `truncated` follow the cap
rule; `module.json` declares `describes: ["remove", "commit"]`.
**Dependencies:** D.
**Affected areas:** the helper (HEAD blob read through `cat-file -s` and `cat-file blob` in fixed shapes; a Python
unified diff of `HEAD/<path>` against `work/<path>`), the declaration, the module's tests.
**Steps:**
1. Write failing tests: each change kind; a binary file (NUL in old or new content) is listed and its diff withheld; a
   path that is not a regular file or lies under a link is in `not_regular_paths`; a repository whose `.gitattributes`
   names a filter, an attribute for text conversion or an external diff gets the unfiltered diff and starts no program
   (marker test); a diff of 98,304 bytes is given, one byte more is omitted whole with `truncated: true` and the name in
   `omitted`; a blob over a read bound is not read into memory whole; the test of criterion 4 against a real commit.
2. Implement the lists and the diff, with the read bound on blob sizes checked before `cat-file blob`.
3. Add `commit` to `describes` and update the module declaration test.
**Verification:** new tests fail first, then pass; all earlier `safe-git` tests pass; the before and after snapshot test
runs for every case; `python3 -B -W error tests/run_all.py`; `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-safe-git-describe#E`.

### Increment F — Security pass and its fixes

**Outcome:** an adversarial pass over the new surface has run on a scratch copy, its findings are recorded in this plan's
Result, and each is fixed with a regression test or reported to the owner as open.
**Dependencies:** E. The owner's approval of this plan is the owner's yes to the security review (`AGENTS.md` asks the
owner whether to run one). An owner who wants no pass strikes F before approving; the plan then does not meet
criterion 9 and is closed with that stated.
**Affected areas:** the `security-reviewer` agent's scratch copy; fixes to the helper, the verifier or the launcher rule
and their tests.
**Steps:**
1. Give the `security-reviewer` the plan, the changed paths and the questions: the three new git shapes and the
   allowlist; a hostile repository (a hook, a filter, a file system monitor, a gitlink, a crafted config, an
   attribute-driven diff or textconv driver); path tricks (links, case, Unicode look-alikes, `.git~1`, very deep trees,
   a path that changes between checks); output bounds (a huge blob, a huge directory, output at the cap, a message
   with control characters or text that looks like an instruction); the launcher rule (missing action, case variants,
   `--`, an action that is an option, a second argument on an `owner` argument); and that the facts cannot be made to
   disagree with the real command.
2. Judge each finding; fix with a test that fails before and passes after; run the guard tests again.
3. Have the reviewer agent check the fixes, as the security skill asks for a fix to be tried by someone who did not write it.
**Verification:** the regression tests; `python3 -B -W error tests/run_all.py`; `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-safe-git-describe#F`. It always has content:
the fixes and tests, and the pass recorded in this plan's Result (what was tried, what was found, what is open), also
when the pass finds nothing to fix.

### Increment G — The specs say what is built

**Outcome:** `safe-git.md`, `module-boundary.md`, `module-contract.md` and `action-review.md` no longer call the built
parts "specified, not built"; `docs/development.md` records the new command; limits found in F are written down.
**Dependencies:** F.
**Affected areas:** those four specs, `docs/development.md`, `docs/specs/README.md` if it lists status; the split in
`action-review.md` marks plan 2 done.
**Steps:**
1. List every "specified, not built" and "once built" mention of `describe` and `describes`; change each to the built
   form or to what remains (the push gap stays open).
2. Record in `safe-git.md` the limits F found and the as-built facts that differ from the draft, if any.
3. Run the document checks.
**Verification:** `wb check`, `wb run code-work check`, `doccheck`, `refcheck`, `git diff --check`; a search for the
phrase returns only the push gap and remote-runner mentions.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-25-safe-git-describe#G`.

## Verification for the plan as a whole

`python3 -B -W error tests/run_all.py` (all tests), `wb check`, `wb run code-work check`, `doccheck` and `refcheck`
(`env PYTHONPATH=workbench python3 -B packages/workbench/groundwork/helper/{doccheck,refcheck}`), `git diff --check`, and
the before and after repository comparison in every `describe` test.

## Risks and sensitive actions

- **Security-sensitive new surface.** The helper runs git on a repository that may be hostile; `describe` adds three
  git shapes and reads file contents. Mitigation: fixed argument shapes, the existing refusal of a repository that
  selects a program before any read, no filter or external diff, size bounds before reads, marker tests, and
  Increment F.
- **Core change.** The launcher rule is in `wb run`, which every module command uses. A mistake could refuse a legitimate
  command or admit an undeclared action. Tests in B cover both directions; F re-tries the rule.
- **Drift between `describe` and the real command.** The refactor in D is the mitigation, with the guard tests and the
  equality tests of criterion 4. A real refusal with no code, or a wrong code, fails a test.
- **Refactor of `commit`.** `command_commit` is security-relevant and in use by this repository's own commits. The
  existing commit tests must pass unchanged and with the same count; D stops if they do not.
- **Self-hosting.** The source helper and declaration change while the installed copy does not; the owner upgrades. The
  agent runs no `wb upgrade`, `acknowledge`, `attach` or `install`.
- **Facts carry hostile text** (a diff, a message) to a future model call. This plan only produces them; the engine
  treats them as data (decision, item 4).
- **Nothing is committed, pushed or deleted** except by the owner's word at each increment.

## Review record

Reviewed by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-25, at
the owner's request: two rounds, bound 3. Round 1 returned two major findings, both applied: R1-F1 (criterion 9 could
not be met if the owner declined the security pass; approval of the plan now stands for the owner's yes to it, and
striking Increment F before approval is the stated way out) and R1-F2 (Increment F could end with no commit; it now
always ends in one commit that records the pass in the Result). Round 2 returned no meaningful finding. The review is
not an approval; the plan stays `Proposed` for the owner.

## Deferred work

- The push gap: extend `push-check` or add `describe push` (see "The push gap" in `safe-git.md`). Placed between this
  plan and the engine, or alongside it; needs its own plan.
- The engine, the rule schema, the log, the shadow hook and cutover (plans 3 to 5).
- `remote-runner describe submit` and `fetch` (after M16).
- A lower or higher `diff` cap, if the shadow period shows the 96 KiB bound declines too many commits.

## Result

### Increment A — Verifier support for `describes`

Done, not yet committed at the time of writing. Changed: `workbench/declarations.py` (`Command` gains `describes` after
`owner`, default empty; `MAX_DESCRIBES = 16`; validation in `_commands`; the module docstring) and the new
`tests/test_describes_declaration.py` (14 tests). Refused: a non-list or non-string entry, more than 16, a duplicate, an
action of the wrong form or over 32 characters, a non-empty list without `describe` among the `arguments`, and
`describe` in `owner` (whatever `describes` holds); an empty list is allowed. The declaration hash changes with the field.

Verification as run: the new tests failed first (7 errors, 1 failure), then passed; `python3 -B -W error
tests/run_all.py` ran 4239 tests OK (4225 before, 14 added; one run failed first because a test docstring named a
module, which `test_boundary` forbids, and was reworded); `git diff --check` clean.

Review: the `reviewer` agent, one exchange, no blocking finding. Not blocking and left open for the owner: the
install-time request text (`workbench/request.py`, `_command`) lists a command's name, helper, runtime and first
arguments but not `owner` or `describes`, so the admitted actions are covered by the confirmed declaration hash but are
not in the text the owner reads. This follows the precedent of `owner` and no spec requires it; a change would be a
later increment. The spec wording "specified, not built" is left for Increment G, as planned. Not checked by the
reviewer: the hashing path itself (the test shows the hash changes).

Committed as `ef1f159`.

### Increment B — The launcher rule for a declared action

Committed as `3a67058`. Changed: `workbench/commands.py` (`_arguments` calls the new
`_described` when the first argument is `describe`; both `resolve` and `launch_refusal` reach it through `_arguments`),
the new `tests/test_describe_launch.py` (14 tests, on the synthetic `tool` module) and the `describes` bullet and the
refused-list wording in `docs/specs/module-boundary.md`. `describe` with no action, with an unlisted action or with
any action on an empty list is refused and nothing runs; other arguments are unchanged. The rule names no module.

Verification as run: the new tests failed first (21 failures, an unlisted action ran), then passed; `python3 -B -W
error tests/run_all.py` ran 4253 tests OK; `git diff --check`, `doccheck` and `refcheck` clean.

Review: the `reviewer` agent, one exchange, no blocking finding. Applied: the `--provides` test did not reach the rule
(the module provided nothing), so it now declares `provides` and asserts the refusal and a listed action running.
Accepted limit, for the security pass: a pin the owner typed under another name is left alone, so `describe push`
launches there; `describes` is a filter there, as the spec says. Left for Increment G: `action-review.md` (lines
~193-199) and `module-contract.md` (lines ~297, ~411) still say "not built". Not checked by the reviewer: it ran nothing.

### Increment C — The output builder and `describe remove`

Done, not yet committed at the time of writing. Changed, all in `packages/workbench/safe-git/`: `helper/safe-git`
(`Refused` takes an optional `code`, and every refusal on the removal path carries one, by class and never read from the
message; `Target` gains `size` and `_scan` counts bytes; the shapes `ls-files -z -- <paths>` and `check-ignore -q -- <path>`;
a "describe" section with `build_description`, `render_description`, `describe_remove` and `command_describe`),
`module.json` (the argument `describe` and `describes: ["remove"]`), `tests/test_safegit_module.py` and the new
`tests/test_safegit_describe_builder.py` (25 tests) and `tests/test_safegit_describe_remove.py` (35 tests). The real
`remove` messages and output are unchanged by reading and by the existing 58 tests, which pass unchanged.

How it was done, as a departure from the plan's wording: every edit to a file under `packages/workbench/` changes the package
tree hash, and the edit gate (`wb gate claude`) then refuses all edits until `release-approvals` is run again, which is the
owner's step here. With the owner's agreement the change was built and tested in a copy in the scratch directory and landed
with one `cp` of five files. `workbench/shipped_approvals/packages/` therefore holds new records, which the commit must
include, and stale untracked ones left by interim runs, which the owner is asked to approve deleting. Neither is in the
plan's affected areas.

Verification as run: the new tests failed first (no `describe`), then passed; `python3 -B -W error tests/run_all.py` ran
4314 tests OK in the real tree (4253 before, 61 added); `git diff --check`, `doccheck`, `refcheck` and `wb check` clean.
A test found a defect: the helper's environment sets `GIT_LITERAL_PATHSPECS=1`, under which `git check-ignore` exits 128,
so every target would have been reported as ignore-unknown; `describe` now sets it to 0 for that one call, which is safe
because a validated target has no glob character, colon, backslash or leading dash.

Choices where the spec is open, for the owner: the size of the object is the printed line including its newline; on a
refused call `entry_total` and `size_total` are omitted and named (so `truncated` is true) and `tracked_file_total` is null;
a `Refused` with no code, or an `OSError` such as an unreadable directory, stops `describe` with exit 1 and no object (the
real `remove` also exits 1 there), because the errors table has no code for it; a refusal after planning (`ls-files`
failing) keeps the facts already found.

Review: the `reviewer` agent, one exchange, no blocking finding. Not blocking, left open: the exit-1 stop above is not in
the spec's list of exit-1 cases (Increment G should state it or the spec should name a code); `_remove_facts` treats an
uncoded `Refused` from `check-ignore` as ignore-unknown, which cannot happen with the fixed shapes; the premise that
validation removed pathspec magic is commented at the call and not enforced by the `check-ignore` shape; the generic usage
line now lists `describe`, which no test pins; the marker test covers some config keys and hooks but not a
`.gitattributes` filter or `diff.external`, and the two new calls start no program by reading. Not checked by the reviewer:
it ran nothing and did not read the builder tests.

Not done: D to G.
