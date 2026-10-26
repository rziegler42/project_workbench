# Build `safe-git describe` for `commit` and `remove`

Status: Completed
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

Done and committed as `ef1f159`. Changed: `workbench/declarations.py` (`Command` gains `describes` after
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

Committed as `8c64008`. Changed, all in `packages/workbench/safe-git/`: `helper/safe-git`
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

### Increment D — Share the commit validation and give the commit refusals and scalar facts

Done and committed as `35052ec`. Changed, in `packages/workbench/safe-git/`: `helper/safe-git` (every
refusal on the commit path through `git diff --check` carries a code by class; `command_commit` is split into `Checked`
and `check_commit(argv, cwd, note=None)`, which the real command calls with no `note` and continues from unchanged;
`describe_commit` calls it with a `note` that records each fact as it becomes known, so a refusal still reports what was
found before it; `_given_commit` reads a refused command line as `parse_commit` reads it; `DESCRIBERS["commit"]`) and the
new `tests/test_safegit_describe_commit.py` (43 tests). `commit` is not yet in `describes`, as the plan says. The same
landing procedure as C was used (scratch copy, one `cp`, the owner's `release-approvals`), so
`workbench/shipped_approvals/packages/` holds the new records, which the commit includes.

Verification as run: the 93 commit tests passed before the change and pass after, with the same count (the guard); the new
tests failed first (`describe commit` unknown), then passed; `python3 -B -W error tests/run_all.py` ran 4357 tests OK
(4314 before, 43 added); `git diff --check`, `doccheck`, `refcheck` and `wb check` clean. The marker test (a repository with
hooks, filters and many program-selecting settings) finds no marker for `describe commit`.

Choices where the spec is open, for the owner: `expected_head` is the string as given once it is valid, so the string `none`
for `none` (and `head` is null on a branch with no commit), and null before it is valid; after a usage refusal `subject`,
`body`, `trailers` and `expected_head` stay null or empty even when given, and only `leave_other_staged`, `path_count` and
`requested_paths` are copies (the spec names those); `diff --check` runs with `GIT_OPTIONAL_LOCKS=0`, in the shared
function, so the real `commit` runs it that way too, which cannot matter because `git add` follows and takes its own lock.

Review: the `reviewer` agent, two exchanges. The first found one blocking problem and three smaller ones, all applied: the
facts `path_count` and `leave_other_staged` were read by splitting at the first `--`, but a value such as `--subject --`
is legal, so an `ok: true` object could disagree with the request (now taken from the parsed request, and from a scan that
mirrors the parser only for a usage refusal); a failure to open the root was coded `setting_invalid` (now
`repository_unreadable`); any nonzero exit of `git diff --check` was coded `whitespace_errors` (now only exit 1 or 2);
`git diff` could refresh the index (now `GIT_OPTIONAL_LOCKS=0`). The second found no blocking finding and confirmed each
fix. Left open, not blocking: the message of the whitespace refusal still says "whitespace errors" for a git failure (the
real command's text, kept unchanged); `_given_commit` is a second copy of the `parse_commit` loop and could drift (a test
guards it; a comment in `parse_commit` would help); the test for the index checks the variable is set and not that git
leaves the file alone (the snapshot test covers the file). Not checked by the reviewer: it ran nothing.

### Increment E — The change lists, the diff and the cap, and the commit declaration

Done and committed as `985692e`. Changed, in `packages/workbench/safe-git/`: `helper/safe-git` (the
`cat-file` shape, only `-s` or `blob` of `HEAD:<path>` with a path that has no empty, `.` or `..` segment; `Checked`
gains `entries`; `_read_work` opens the work-tree path from the root descriptor with no link followed and reads at most
`MAX_SIDE` (262,144 bytes, the approver's whole-diff bound); `_head_side` asks `cat-file -s` first and reads the blob
through `run_capped` only below the bound; `_text_diff` is `difflib` over lines split on the line feed only, named
`HEAD/<path>` and `work/<path>`; `_change_facts` sets the six lists and `diff` only when all of them are found),
`module.json` (`describes` is `["remove", "commit"]`, the order of the plan; the spec text has the other order), the new
`tests/test_safegit_describe_changes.py` (46 tests), and small edits to four existing test files (the facts list, the
omitted names for 201 paths, the allowed git commands, the `cat-file` shape, the declaration). The landing procedure was
that of C and D, twice (the review fix needed a second landing), so `workbench/shipped_approvals/packages/` holds the new
records.

Verification as run: the new tests failed first (the facts and the attribute did not exist), then passed; the 414 tests
of the `safe-git` root pass (366 before, 48 added); `python3 -B -W error tests/run_all.py` ran 4405 tests OK in 10
roots; `git diff --check`, `wb check`, `wb run code-work check` (48 plans), `doccheck` and `refcheck` clean. Tests cover
each change kind, binary content in the old or new side, five kinds of path swapped after the last check (a link to a
file, a link on the way, a FIFO, a directory, a file where a directory was), an attribute-driven filter, text conversion
and external diff (no marker), the diff at 98,304 bytes and one byte over, a blob and a work file over the read bound
(never read), and the before and after snapshot for every kind.

Choices where the spec is open, for the owner: contents are compared byte for byte, so a repository that converts line
endings (`eol=crlf`) or sets `core.fileMode=false` can have a path `describe` calls modified that the real `git add` would
not stage (the real command then refuses at staging); a change of the executable bit is a modification, with a line
`mode HEAD/<path> <old|none> -> work/<path> <new|none>` in the diff (none for a plain new or deleted 100644 file); a side
over `MAX_SIDE` is not read, the path is listed new, deleted or modified (not compared), and the whole diff is omitted;
a byte that is not UTF-8 is shown as its escape (`\xe9`); a path in the index for which `cat-file -s HEAD:<path>` fails is
taken as absent from HEAD (an intent-to-add entry), which would also hide a corrupt object as a new file; a read error
after the checks gives `repository_unreadable` or `path_refused` and sets no list.

Review: the `reviewer` agent, one exchange, no blocking finding. Applied: non-UTF-8 text was decoded with replacement
characters, so two different bytes could leave a path modified with an empty diff (now escapes, with a test); a comment on
the character count. Left open: the two choices above that the reviewer also named (the byte-for-byte comparison and the
failed `cat-file -s`); `binary_paths` is not complete for a file over the bound (`truncated` is true then). Found while
answering one of its questions, for F: `git diff --check` of a tracked path with a `filter=` attribute starts the owner's
clean filter if it is defined in the global configuration (a repository's own filter is refused earlier). That is the real
`commit`'s existing check, shared by `describe`; the contents read for the lists and the diff never start a program.

Superseded by F, which is now done: the non-UTF-8 choice above (shown as an escape) became "listed as binary", and the
failed `cat-file -s` reading became "absent only for an intent-to-add path".

### Increment F — Security pass and its fixes

Done and committed as `42945e1`. The owner approved the new error code `path_converts_on_add` and the
narrower attribute list (`filter`, `ident`, `working-tree-encoding`; not `text` or `eol`) after the pass. Changed, in
`packages/workbench/safe-git/`: `helper/safe-git`, the new `tests/test_safegit_describe_pass.py` (30 tests, one group for
each finding), and small edits to three test files (two lists of allowed git commands gain `check-attr`; the test that
named a filter attribute names a diff driver instead; the non-UTF-8 test expects `binary_paths`). The landing procedure
was that of C to E, twice (the review of the fixes needed a second landing), so `workbench/shipped_approvals/packages/`
holds the new records.

The pass: the `security-reviewer` agent, on a scratch copy, with fake programs, throwaway hostile repositories and
`python3 -I -B`. It tried 38 git argument forms against the allowlist; a repository with a textconv, an external diff, a
filter, a file system monitor, a hooks path, six hooks and a gitlink (no program started for `describe remove` or
`describe commit`); links, a FIFO, a 300 MiB sparse file, case and Unicode spellings, `.git` look-alikes and 60 and 120
levels of depth; a 300-trial fuzz of the printed object; 21 launcher-rule cases; and `core.fileMode=false`. It disclosed
that it ran three stale probe scripts of an earlier task before overwriting them, and that it did not read the tests or
the verifier. Found sound by test: the allowlist, the paths, no program started by a repository's own configuration, the
object bound and its JSON, the launcher rule, and `describe remove --confirm` deleting nothing.

Found and fixed, each with a test that failed first:
- High, H1: a repository's attributes (`working-tree-encoding`, `ident`, `filter`; from an untracked `.gitattributes`, a
  directory's own file or `.git/info/attributes`) make `git add` store other bytes than the work tree holds, so the diff
  and a scan over it could be blind to what is committed (a token in UTF-7 showed as `+AGc-hp_…`).
- Medium, M1: `git diff --check` starts a filter from the owner's own global configuration (for example the one
  `git lfs install` writes) when such an attribute names it, and a filter that writes into `.git/` changes the repository.
  Both are closed by one change: `check_commit`, which the real `commit` runs too, asks `git check-attr -z filter ident
  working-tree-encoding -- <paths>` first and refuses with the new code `path_converts_on_add` for any value other than
  unset or unspecified. The output must be exactly one answer for each path and attribute, in order, else
  `repository_unreadable`.
- Medium, M2: `difflib` took 3.6 to 6.8 s for one file of 262 KB of repeated short lines, and the diff cap never stopped
  the work. Now the lines both sides share at the start and the end are set aside before the comparison, a side with more
  than `MAX_MIDDLE` (500) differing lines is not compared, and the diffs of one `describe` have a budget of 20 s
  (`DIFF_BUDGET`); either limit omits `diff` and sets `truncated`. The hand-built unified diff equals `difflib`'s on 300
  random cases with distinct lines.
- Low: a side that is not UTF-8 is listed in `binary_paths` and its diff is withheld (two different bad bytes, or a literal
  `\xe9` against a raw byte, no longer read alike); a failed `cat-file -s` is "absent from HEAD" only for an intent-to-add
  path (an index entry with the empty blob), else `repository_unreadable`; the `check-ignore` shape itself refuses a
  leading colon, a glob character, a backslash and a leading dash; a lone surrogate is printed as its escape text so a strict
  JSON reader accepts the object.

Verification as run: the first 23 new tests failed before the fixes (a partial run showed failures and errors; no count was kept), then passed; the
`safe-git` root runs 444 tests OK (414 before); `python3 -B -W error tests/run_all.py` ran 4435 tests OK in 10 roots;
`git diff --check`, `wb check`, `wb run code-work check` (48 plans), `doccheck` and `refcheck` clean. Stray Finder
`.DS_Store` files made `release-approvals` and `tests/test_boundary` refuse twice; they were removed with the owner's
approval and are not part of the work.

Review of the fixes: the `reviewer` agent, one exchange, no blocking finding; it ran nothing. Applied: the `check-attr`
output must match the paths and attributes asked for (it only had to be a multiple of three fields); `MAX_MIDDLE` from 1,000
to 500 after the reviewer's input (1,000 alternating lines) took 2.5 s for one file, 500 about 0.6 s; the `check-ignore`
shape refuses a leading colon only, not any colon, and a wrong comment about it is corrected; tests for an empty
`filter=`, a macro, one converted path among several, a `check-attr` output that is short or out of order, and the
`difflib` equality. The tests of that second round were written with the fix, not before it.

Limits left open, to be written down in G:
- `text`, `eol` and the old `crlf` attribute, `core.autocrlf` and `core.eol` (and, as the owner chose, no refusal for
  them) change line endings on `git add`: `describe` shows the bytes of the work tree where the real command stores
  converted ones. The difference is whitespace only; a path can be listed modified or unchanged accordingly.
- `check-attr` prints a literal value `unspecified` or `unset` as it prints the state; a repository line
  `filter=unspecified` is therefore not refused, and would run a filter of that name only if the owner's own global
  configuration defines one (a repository cannot, `repo_selects_program` refuses it).
- A `.gitattributes` or work-tree change between `describe` and the real command is the race the spec already accepts.
- The budget is checked between files, not inside one comparison, so one `describe` can take the budget plus one
  comparison (about 0.6 s at the bound). Each of up to 2,000 paths costs two git runs (about 26 ms each in the pass, 52 s
  in all for 2,000); nothing bounds that total.
- A `describe remove` target the `check-ignore` shape refuses (a leading colon, or a backslash) can be listed in
  `ignore_unknown_targets`, because the ignore status is not asked, not refused; the reviewer read this, it was not run.
- Not checked by the reviewer or the pass: a full run of 2,000 paths (extrapolated from 1,000), `wb launch` through a real
  pin, the repository's own tests and the verifier by the pass, and timings by the reviewer. A SHA-256 repository has no
  test.

### Increment G — The specs say what is built

Done and committed as `3db2b98`. Documents only; nothing under `packages/workbench/` changed. Changed:
`docs/specs/safe-git.md` (the declaration row, the "Describe" section marked built, the errors table gains
`path_converts_on_add`, `binary_paths` covers bytes that are not UTF-8, the exit-1 cases are stated, the acceptance
criteria are marked as the plan's, and "As built, and its limits" records the departures from the draft, the limits of
F and the shipped-approvals practice), `docs/specs/module-boundary.md`, `docs/specs/module-contract.md` and
`docs/specs/action-review.md` (the "not built" wording for `describes` and the launcher rule, plan 2 of the split marked
done, the status line and the evidence line made exact), and `docs/development.md` (a row for `describe`).
`docs/specs/README.md` lists no status and is unchanged. `workbench/shipped_approvals/` was not added to the affected
areas; the practice is written in `safe-git.md`.

Verification as run: `git diff --check`, `wb check`, `wb run code-work check` (48 plans), `doccheck` and `refcheck`
clean; a search of `docs/specs` and `docs/development.md` for "specified, not built", "once built" and "decided, not
built" finds nothing. `describe` itself was not run through `wb run` here: this project's installed pin predates it, and
upgrading is the owner's. The keys of the output were read in the helper.

Review: the `reviewer` agent, one exchange. Two blocking findings, both applied: I had written 34 error codes where the
table and the helper have 32 (counted again with a search of the helper), and `action-review.md` still said nothing in
it was built and that no plan existed. Also applied: the acceptance-criteria heading and a future-tense sentence, and a
note that `binary_paths` is complete only when `truncated` is false. Not changed: the diff cap is measured in bytes at
the final gate and in characters in a running counter, which does not change the result. Not checked by the reviewer: it
ran nothing, and did not open `docs/specs/README.md`.

Not done: nothing in this plan remains except the owner's verdict. Open for the owner, outside the plan: the push gap,
the engine (plan 3 of the split), and the old tracked approval records.
