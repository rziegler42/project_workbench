# Build the action-review engine for commit and remove

Status: Proposed
Created: 2026-10-26
Candidate: workbench-v1#action-review-engine
Specs: action-review, safe-git, model-bridge, module-contract, module-boundary

## Goal

Build `action-review`, the module that takes the facts a module's `describe` reports about one action and returns a
verdict with reasons as data, as `docs/specs/action-review.md` designs it (plan 3 of the five in its split). The owner's
approver is a program in the user level that collects facts through the global `claude-workflow` program and cannot be
removed in pieces; this engine is the replacement that later plans put behind a thin hook. This plan builds the engine
and nothing around it: no hook, no labelled set, no shadow period, no cutover.

The owner chose on 2026-10-26: the engine covers `commit` and `remove` now, and the rule for a push is added by a
follow-up plan once `describe push` exists (plan `2026-10-26-safe-git-describe-push`); and the engine reads its bridge,
model and effort from `.workbench/review.json`, the file the review engine already uses.

That second choice changes a default of the spec. "Settings and the bridge" in `action-review.md` is marked a default
and designs a file of the engine's own, `.workbench/action-review.json`, with the owner's personal setting
authoritative over the project's request. The owner may change a default, so Increment A edits that section to name
`.workbench/review.json`. The personal setting stays unbuilt, as it is for the review engine (no helper can read the
guarded store): the engine reads the project file only, that is a recorded limit, and the personal-setting precedence is
deferred. Approving this plan is the owner's word on the file; the owner may reverse it at Increment A.

When the plan is done:

- `wb run action-review review '<the prompted command>'` takes the raw text of a command the harness is about to run,
  parses it under the stated grammar, finds its rule, runs `wb run safe-git describe <action> <arguments>` through the
  launcher, applies the rule's fixed checks to the facts, and only if they pass asks the bridge for a verdict against the
  rubric;
- it prints one verdict object (`verdict`, `failed_checks`, `reason`) and exits 0, 1 or 2 as the spec's table says, and it
  prints nothing on standard output for a refusal or a failure;
- a rule that does not load, is ambiguous or carries command text refuses only its own key, and a command that does not
  fit the grammar is unreviewable and approves nothing;
- every check of the approver for `commit` and `remove` has a counterpart in the engine or a recorded reason it has
  none, and the dangerous cases the spec names are declined by a test;
- a security pass has covered the command parser, the launcher call and the prompt assembly;
- the specs say "built" for what is built.

## Scope

- A new first-party module, `packages/workbench/action-review/`: `module.json`, `helper/action-review`, the rule files and
  rubric as data it ships, and its tests. It provides the capability `action-review` and requires `model-bridge`.
- `packages/workbench/package.json` (the module list) and `workbench/shipped_approvals/packages/` (the approval records
  the owner's `release-approvals` writes for each package change, which the commit includes).
- `docs/specs/action-review.md` (the rule schema, the engine's as-built facts and limits), `docs/specs/safe-git.md` where
  its counterpart table names a check, `docs/specs/module-contract.md` for the new capability name if it needs a line,
  and `docs/development.md`.

## Non-goals

- The hook, its installation, the log file and who writes it (the owner's thin hook writes the log; the engine only hands
  back the row), the labelled set, the test set's use against the approver, the shadow period, the report and the
  cutover (plans 4 and 5). The hook is the owner's to write in the user level.
- The rule and checks for a push, and anything that needs `describe push`. The engine's rule format must allow a push rule
  later without change.
- Rules for `remote-runner` actions (after M16), `ask-codex archive`, `safe-committer` and `amend-message` (retired).
- Any change to `safe-git`, to the launcher or to the bridge. A need found for one stops the plan and goes to the owner.
- Writing any `allow` rule, setting, hook entry or file outside the project. The engine's verdict authorizes nothing by
  itself.
- Installing the module into this repository (`wb add`) and any `wb upgrade`, `acknowledge`, `attach`, `install`. These
  are the owner's.
- A personal (guarded-store) setting for the bridge. The engine reads the project file, as the review engine does, with
  the same recorded limit that a project file is not the owner's personal setting.

## Assumptions and constraints

- **The design is settled in the spec.** The spec fixes the goals, the `describe` contract, the grammar of the prompted
  command, the verdict object, the exit table, the log row, the timeouts (bridge 20 s, engine 25 s, hook 30 s,
  provisional) and the rule properties. It leaves the rule schema to this plan's first deliverable. If building shows a
  fixed part is wrong, stop and ask; do not change the spec to fit the code.
- **Rules are data and the checks are code.** A rule names a module and an action as identifiers, the checks, a rubric
  section and the questions. It holds no command text, no verb and no path; a rule that tries does not load. The engine
  builds the launcher arguments itself with the fixed word `describe`.
- **The prompted command is parsed once.** A restricted grammar (single-spaced words of a small bare alphabet, or
  single-quoted strings) is accepted; anything else is unreviewable. The equivalence with `sh` and `zsh` is a property
  test over generated text, and skips with a reason for a shell that is not installed.
- **The engine runs other modules' commands only through the kit's `run_command`.** `module-boundary.md` ("A helper that
  runs another module's command") allows a helper to start another module's command only through `wbkit/call.py`, which
  starts `wb run [--provides <capability>] <command> <arguments>` and nothing else, with no shell, a bound on output read
  and a time limit that kills the process group. The engine runs `describe` for the action and the bridge for the verdict
  that way (the bridge with `--provides model-bridge`), each pinned and declared (`describes` for `describe`). The
  launcher already refuses an unpinned, edited or undeclared command, and the engine treats any refusal as its own
  (exit 1). It starts no process any other way.
- **Facts are data, not instructions.** A diff or message can address the reviewer. The rubric keeps the check for that
  text; the vendor program can still read the project (`model-bridge.md`), so the engine claims no isolation and puts
  nothing sensitive in the project.
- **The prompt budget is arithmetic.** At most 262,144 bytes reach the bridge; the facts take at most 196,608
  (`safe-git.md`, "Caps and their sources"). The engine measures its rubric and adjusts the object cap's remainder, not
  the rule, as that section says.
- **Where the approver's content comes from.** The approver's rubric, rule files and secret scan are in the user level
  (role USER). They are read, not run, for the port (hashes recorded in `safe-git.md`); the port is data and code in this
  repository, and nothing tracked points to the user-level files.
- **Standard library only**, Python through kit 1, one helper, as the other modules.
- **Self-hosting.** The module is a new first-party package member; this repository installs it only when the owner runs
  `wb add`. Tests use a scratch project with fakes, and no live vendor is called.
- **The edit gate and the shipped approvals** apply to every increment that edits `packages/workbench/`: build and test in
  a copy in the scratch directory, land with one `cp`, and the owner runs `release-approvals`. Stray Finder files inside
  the package trees make that command refuse; the owner keeps Finder windows off the repository.
- **Each increment is one reviewed local commit** made with `wb run safe-git commit`, with the `Plan:` trailer and no
  attribution. Review is the `reviewer` agent. A second-model review happens only if the owner asks.
- Discovery: graphify: skipped, no discovery tooling installed. The scope is a new module that reads `describe` objects,
  `.workbench/review.json` and the bridge contract; the spec, `model-bridge.md`, `safe-git.md` and the `review-engine`
  helper's setting reader were read for this plan.

## Completion criteria

1. The rule schema is written in `action-review.md` with its field types, bounds and precedence, the owner has read it,
   and the tests for a malformed, overlapping and over-long rule pass (a stop after Increment A).
2. A rule with command text, an extra verb or a path does not load; two rules with one key each refuse only that key; a
   corrupt rule does not stop the review of another command. A command line that names a retired action
   (`ask-codex archive`, `safe-committer`, `amend-message`) is refused with no `describe` and no bridge call.
3. Over generated command text, every text the grammar accepts parses to the same argument list in the engine and in `sh`
   and `zsh`, and every other text is refused; a test shows the argument list the engine reviews equals the one the real
   `safe-git` parses from the same text.
4. The engine runs `describe` and the bridge only through the kit's `run_command`, so only as `wb run [--provides
   <capability>] <command> ...`; a command that is not installed, pinned and declared is refused and nothing runs (a fake
   module and a fake bridge in a scratch project). A test finds no other way the helper starts a process.
5. A missing, malformed, oversize or unavailable `describe` object, rule file or bridge reply yields no approval; a
   `truncated: true` or `ok: false` object is a decline with exit 0, not a refusal.
6. `review` prints only the verdict object and exits 0, 1 or 2 as the spec's table says; an approve with a non-empty
   `failed_checks`, a decline with an empty one, an extra field or a `reason` over 300 characters is never printed; every
   refusal and failure prints nothing on standard output.
7. Every check of the approver for `commit` and `remove` named in `safe-git.md` has a counterpart in the engine or a
   recorded reason it has none, and a test per code check gives a pass and a fail. The checks for a push are recorded as
   deferred to the plan that adds the push rule, with the reason (no `describe push` yet).
8. The dangerous cases that a code check decides (a secret in a diff or message, a HEAD that does not match, a repository
   that selects a program, a removal of Git metadata, a truncated object, a path that is a credential file) are each
   declined with a fake bridge that would otherwise approve. The cases only a rubric question decides (a message addressed
   to the reviewer) are tested with a fake bridge that declines, which shows that the engine sends the text as data and
   passes the decline through; whether a real model declines them is plan 4's labelled run and is not claimed.
9. The handed-back log row holds exactly the listed fields, and a test shows no command text, fact or diff reaches any
   field but the bounded `reason`. The engine writes no file: the project and the scratch project are byte for byte the
   same after every `review`, whatever its outcome.
10. The bridge selection reads `.workbench/review.json` strictly: an absent file, an invalid one, a bridge that is not
    installed or not pinned each behave as the spec says, and no other vendor is tried.
11. The security pass was run if the owner said yes, its findings are fixed with tests or reported, and the Result
    records either.
12. `python3 -B -W error tests/run_all.py`, `wb check`, `wb run code-work check`, `doccheck` and `refcheck` pass, and the
    specs say "built" and keep the limits.

## Increments

### Increment A — Specify the rule schema and the module

**Outcome:** `docs/specs/action-review.md` holds the versioned rule schema (the file, its `format`, the fields, their
types and bounds, how a rule's key is matched on whole tokens, the precedence and ambiguity rules, the checks a rule may
name, how a rubric section and its questions are named), the module's declaration and files, how bridge selection reads
`.workbench/review.json` (the edit to the spec's "Settings and the bridge" described under Goal), and how the log row
reaches the hook (a flag that prints the row as one JSON line on standard error, with no field added to the verdict
object). The owner has read it.
**Dependencies:** none.
**Affected areas:** `docs/specs/action-review.md` only. Documents only.
**Steps:**
1. Read the spec's "The engine", "The reviewed command is the command that runs", "The verdict, the output and the log"
   and "Decided by the owner", `model-bridge.md` (input, output, result shape), and the `review-engine` helper's setting
   reader.
2. Write the schema, with an example rule for `commit` and one for `remove` and the cases that must not load.
3. Write the module's layout, its declaration (`provides: action-review`, `requires: model-bridge`, one command
   `action-review` whose argument is `review`), and the bridge selection.
4. Write the list of checks the engine has for `commit` and `remove` with the facts each reads, from the table in
   `safe-git.md` ("Each check of the approver, and where it goes"), and say which are code checks and which are rubric
   questions.
5. Run the document checks and ask the `reviewer` agent to read it for drift against the accepted decisions.
6. Stop. The owner reads the schema and says to go on, or changes it. B does not start before then.
**Verification:** `wb check`, `wb run code-work check`, `doccheck`, `refcheck`, `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-action-review-engine#A`.

### Increment B — The module skeleton and its declaration

**Outcome:** `packages/workbench/action-review/` exists with `module.json` and a helper that refuses every call with a
usage line; the verifier accepts the package, the module is listed in `package.json`, and a test shows the declaration.
**Dependencies:** A, accepted by the owner.
**Affected areas:** `packages/workbench/action-review/` (new), `packages/workbench/package.json`,
`workbench/shipped_approvals/packages/`.
**Steps:**
1. Write failing tests: the declaration verifies as a first-party module providing `action-review` and requiring
   `model-bridge`; `review` is its only argument; the helper refuses a missing or unknown argument; the package lists it.
2. Add the files. The helper takes the command line and the project root as the other helpers do and does nothing else yet.
3. Build and test in the scratch copy; land with one `cp`; the owner runs `release-approvals`.
**Verification:** new tests fail first, then pass; `python3 -B -W error tests/run_all.py`; `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-action-review-engine#B`.

### Increment C — The command grammar and the one parse

**Outcome:** the helper turns the raw text of a prompted command into a spelling, a subcommand and an argument list, or
refuses it as unreviewable. The stated grammar is the only one accepted.
**Dependencies:** B.
**Affected areas:** the helper, its tests, `workbench/shipped_approvals/packages/`.
**Steps:**
1. Write failing tests: each accepted form; each refused character class (double quote, backslash, `$`, backtick, glob
   characters, `~`, braces, `#`, `;`, `&`, `|`, redirections, parentheses, newline, tab, an environment prefix, a leading,
   trailing or doubled space); single quotes with every other character literal; a word beginning with `-` that no rule
   declares.
2. Write the property test: generated text over the grammar's alphabet and the quote forms, parsed by the engine and by
   `sh -c` and `zsh -c` printing their argument lists (through a fixed printing program, never the command itself),
   with a skip and a reason for a missing shell. Every accepted text agrees; every other is refused.
3. Write the parser. It declares nothing about rules yet: flags are typed by the rule in D.
4. Land as in B.
**Verification:** as in B, plus the property test with the shells present.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-action-review-engine#C`.

### Increment D — Rules: the loader, the key and the ambiguity rules

**Outcome:** rule files in the module's data directory load under the schema from A; a rule is keyed by one spelling and
one subcommand matched on whole tokens; the declared flags (value, multi, boolean) and exactly one positional group
parse the argument list from C once; an unknown flag, a repeated single-valued flag and a missing required flag refuse the
review. A rule with command text, an extra verb or a path does not load.
**Dependencies:** C.
**Affected areas:** the helper, the shipped rule files for `commit` and `remove` (data), tests,
`workbench/shipped_approvals/packages/`.
**Steps:**
1. Write failing tests: a valid rule; a missing field, a wrong type, an over-long value, an unknown field, a `format` the
   engine does not know; two rules with one key (both refuse, neither reviews anything, other keys still review); a rule
   that names a check that does not exist; a corrupt file next to a good one; a rule that carries a command line, a verb
   or a path; the key never matching on a text prefix; a command line for each retired action (`ask-codex archive`,
   `safe-committer`, `amend-message`) refused with the fake `describe` and the fake bridge recording no call.
2. Write the loader and the matcher. A rule error is reported with the rule's file name and refuses only its key.
3. Add the two shipped rules (`safe-git commit`, `safe-git remove`) naming the module, the action and the checks.
4. Land as in B.
**Verification:** as in B; the corrupt-neighbour test passes.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-action-review-engine#D`.

### Increment E — Running `describe` and reading its object

**Outcome:** the engine builds `wb run <module> describe <action> <the parsed arguments>` itself, runs it through the
kit's `run_command` (and so the launcher) with a time limit and a bound on the output read, and reads the object under the decision's field rules: the types, the bounds on `code` and
`message`, `ok` true only with no error, no extra field, `action` equal to the one requested. A malformed object, a
launcher refusal or a failed run is a refusal (exit 1); a well-formed `truncated: true` or `ok: false` object is carried
forward to become a decline.
**Dependencies:** D.
**Affected areas:** the helper, tests with a fake module and a fake `wb`-pinned command in a scratch project,
`workbench/shipped_approvals/packages/`.
**Steps:**
1. Write failing tests with a fake `describe` command: a valid object; each malformed shape (a missing field, an extra
   field, a nested value, a wrong type, `ok` true with errors, a wrong `action`, not JSON, two lines, a very large
   output); a command that is not installed, pinned or declared; a launcher refusal; a timeout; the engine never builds a
   command line from rule text.
2. Write the call and the validator. Output is read through a cap; the arguments are passed as a list.
3. Land as in B.
**Verification:** as in B; every malformed case approves nothing and prints nothing on standard output.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-action-review-engine#E`.

### Increment F — The code checks for `commit`

**Outcome:** the engine checks, as pure functions of the facts, what the approver checked in code for a commit:
`head_matches`, `repo_config_safe`, `staging_state_ok`, `paths_valid`, `message_valid`, `paths_not_credentials`,
`paths_regular`, `facts_complete` and `no_secret_lines`. A failed check names itself in `failed_checks`.
**Dependencies:** E.
**Affected areas:** the helper (the checks and the secret scan), the shipped rule data (the credential-name list moved
from the approver), tests, `workbench/shipped_approvals/packages/`.
**Steps:**
1. Write failing tests for each check, a pass and a fail, from `describe commit` objects built by hand and by a real
   `safe-git describe commit` against a scratch repository: a HEAD that does not match; a program-selecting repository; a
   staged path without `--leave-other-staged`; a refused path or message; a credential file name; a non-regular path; a
   `truncated` object or a non-empty `binary_paths`; and a secret in the diff, the subject, the body or a trailer.
2. Port the approver's secret scan and credential-name list as code and data, reading them from the user level for the
   port only and recording the source hashes in `safe-git.md`. A hit withholds the diff from anything sent to a bridge.
3. Write the checks. Land as in B.
**Verification:** as in B; the secret and credential tests never print matched text.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-action-review-engine#F`.

### Increment G — The code checks for `remove`

**Outcome:** the engine checks `confirm_present`, `removal_valid`, `ignore_status_known`, `preview_matches_arguments`,
`no_git_metadata` and completeness for a removal, from `describe remove`.
**Dependencies:** F.
**Affected areas:** the helper, tests, `workbench/shipped_approvals/packages/`.
**Steps:**
1. Write failing tests for each check, a pass and a fail, with real `safe-git describe remove` objects: no `--confirm`, a
   refusal code, an ignore-unknown target, a preview that differs from the arguments, a `.git` segment in any case or
   spelling, a truncated object.
2. Write the checks. Land as in B.
**Verification:** as in B.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-action-review-engine#G`.

### Increment H — The rubric, the prompt and the bridge call

**Outcome:** when every code check passes, the engine builds the prompt (the facts quoted as data, the rubric section and
the questions, the framing), calls the bridge selected by `.workbench/review.json`, through the kit's `run_command` with `--provides model-bridge`,
as exactly `wb run --provides model-bridge <bridge> ask --timeout 20 --schema <the shipped reply schema> [--model <m>] [--effort <e>]` with the prompt on standard input (the
`--model` and `--effort` only when the setting has them), validates the bridge's result object as `model-bridge.md`
defines it (a success object or one of its failure objects; a malformed envelope is a failure) before it parses the
`reply` as the verdict JSON and checks that against the verdict rules, and turns the reply into a verdict. A reply that does not fit, an unavailable or unpinned
bridge, a timeout (25 seconds for the engine) and any internal error approve nothing.
**Dependencies:** G.
**Affected areas:** the helper (the prompt builder, the bridge call, the setting reader), the shipped rubric (data, ported
from the approver's section by section), a reply schema file, tests with a fake bridge,
`workbench/shipped_approvals/packages/`.
**Steps:**
1. Write failing tests with a fake bridge that records its argv and standard input: the exact argv above, in that
   order, with the prompt on standard input; each bridge failure object; a success envelope with a missing, extra or
   mistyped field; an approving reply, a declining reply with reasons, a reply that is not valid
   JSON, one with an extra or missing field, an approve with failed checks, a decline with none, a reason over 300
   characters (display-cleaned and cut by the engine, never passed on raw), an exit 1 with an object (a failure for a
   bridge), a timeout, a bridge that is absent or not pinned, a request that names another vendor (never tried); the
   prompt stays inside 262,144 bytes and the facts cap leaves the room `safe-git.md` computes; the rubric measured, with
   its size recorded.
2. Port the rubric and the questions as data, recording the source hash and the date. The questions are the engine's;
   the code checks above never go to the model.
3. Write the prompt builder and the call. A code-check failure never calls the bridge.
4. Land as in B.
**Verification:** as in B; with the bridge removed from the fake project, no verdict is `approve`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-action-review-engine#H`.

### Increment I — The output, the exit table and the log row

**Outcome:** `review` prints exactly the verdict object and exits 0, 1 or 2 as the spec's table says, and with a flag
prints the log row as one JSON line on standard error. The row has exactly the listed fields (`ts`, `rule`, `verdict`,
`failed_checks`, `reason`, `command_sha256`, `facts_sha256`, `rubric_sha256`, `bridge`, `model`, `effort`, `format`) and
holds no command text, fact or diff.
**Dependencies:** H.
**Affected areas:** the helper, tests, `workbench/shipped_approvals/packages/`.
**Steps:**
1. Write failing tests: each outcome row of the table (verdict, refusal, failure) with its standard output and exit
   status; the object never printed when malformed; a decline from `truncated` or `ok: false` is exit 0; the row's fields
   and a search of it for the command text and a planted diff line.
2. Write the printing and the hashes (over the canonical argument list, the facts as received, and the rubric text sent).
3. Land as in B.
**Verification:** as in B.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-action-review-engine#I`.

### Increment J — The dangerous cases, end to end

**Outcome:** a test set of the dangerous cases the spec names runs end to end, with the real `safe-git describe` through
the launcher in a scratch project. A fake bridge that approves everything it is asked is used for the cases a code check
decides, and each is declined by that check; a fake bridge that declines is used for the cases only a rubric question
decides, and each shows the text sent as data and the decline passed through. The set is kept as a data file the owner
reviews and plan 4 reuses.
**Dependencies:** I.
**Affected areas:** the tests and the data file in the module, `workbench/shipped_approvals/packages/`.
**Steps:**
1. Write the cases: a secret in a diff, in a subject and in a trailer; a HEAD that does not match; a repository with a
   program-selecting setting; a message addressed to the reviewer; a removal of `.git` in each spelling; a truncated
   object; a credential file; a path through a link; an unreviewable command line; a rule that does not load.
2. For each case, record the check or question that declines it. Where only the model could decline it, say so; those
   cases use the declining fake as above, are listed for plan 4's labelled run, and are not claimed as covered here.
3. Land as in B. Stop for the owner to review the set.
**Verification:** as in B.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-action-review-engine#J`.

### Increment K — Security pass and its fixes

**Outcome:** the owner has been asked whether to run a security review; if yes, the pass over the engine has run and each
finding is fixed with a test that failed first or reported to the owner; if no, that is recorded. The increment always
ends in one commit.
**Dependencies:** J.
**Affected areas:** the helper and its tests, `workbench/shipped_approvals/packages/` if fixes land; the plan's Result.
**Steps:**
1. Stop and ask the owner whether to run a security review (approval of this plan is not that answer). The
   `security-review` module is installed in this repository. On yes, use the `security-reviewer` agent: give it the
   command parser and the property test, the rule loader, the launcher calls, the prompt assembly and the log row, and
   tell it to use scratch copies and fake programs only. On no, skip to step 3.
2. Evaluate each finding as a review comment. For each one that holds, write the failing test, fix it, and land as in B.
3. Ask the `reviewer` agent to read the fixes (or the increment, if the pass was declined). Record the pass or the
   refusal, the findings, the fixes, what was found sound by test and what was not checked.
**Verification:** the new tests fail first, then pass; `python3 -B -W error tests/run_all.py`; `wb check`;
`git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-action-review-engine#K`.

### Increment L — The specs say what is built

**Outcome:** `action-review.md` (status and sections), `safe-git.md` (the counterpart table), `module-contract.md` if it
names the capability, and `docs/development.md` (the command and the owner's steps) say what is built and what remains,
including the push rule, the hook, the labelled set and the shadow period.
**Dependencies:** K.
**Affected areas:** those documents only; no file under `packages/workbench/` changes.
**Steps:**
1. List every "not built" mention of the engine and the rule schema; change each to the built form or to what remains.
2. Record the limits found, any departure from A's text, the checks that have no counterpart and why, and the owner's
   steps (`wb add` for this repository; the hook).
3. Run the document checks and the reviewer.
**Verification:** `wb check`, `wb run code-work check`, `doccheck`, `refcheck`, `git diff --check`; a search for the
phrases returns only the open limits.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-action-review-engine#L`.

## Verification for the plan as a whole

`python3 -B -W error tests/run_all.py` (all tests, including the module's own root), `wb check`,
`wb run code-work check`, `doccheck` and `refcheck`
(`env PYTHONPATH=workbench python3 -B packages/workbench/groundwork/helper/{doccheck,refcheck}`), `git diff --check`, the
property test of the grammar with `sh` and `zsh` present, and the dangerous cases of Increment J.

## Risks and sensitive actions

- **A wrong approval is the harm.** The engine's verdict stands in for the owner's prompt once a hook uses it. A false
  approve is worse than a false decline. Mitigation: code checks first and never overridden by the model; fail closed in
  every unclear case; the dangerous-case set with a fake bridge that approves everything; the engine writes no `allow`
  rule and the hook, not this plan, decides what an approve may do.
- **The reviewed command must be the command that runs.** A grammar mismatch between the engine and the shell would
  review something else. Mitigation: the restricted grammar, the property test against `sh` and `zsh`, and the rule that
  anything outside it is unreviewable.
- **Hostile text reaches a model.** A diff or message can address the reviewer, and the vendor program can read the
  project. Mitigation: facts are quoted as data, the secret scan withholds the diff, the rubric keeps the reviewer-text
  check; no isolation is claimed (`model-bridge.md`).
- **Security-sensitive surface.** A helper starts another module's pinned command and a bridge, parses command text and
  assembles a prompt from repository content. Increment K asks the owner for the security pass.
- **A typo in a rule must not turn review off.** The loader refuses only that rule's key and reports it; the approver
  failed this way. Tests cover the corrupt-neighbour case.
- **Reading the approver's rubric and scan from the user level.** They are read only, and only for the port; the result is
  data in this repository with its source hashes recorded in the spec. No user-level file is written.
- **The setting is a project file.** `.workbench/review.json` is not the owner's personal setting, and the spec's
  rule that the personal setting overrides the project's request is not built, so a project could name another installed
  bridge. Mitigation: only an installed, pinned bridge that provides `model-bridge` runs, and the limit
  is recorded.
- **Self-hosting.** A new module in the package does not change the installed project until the owner runs `wb add`. The
  agent runs no `wb add`, `upgrade`, `acknowledge`, `attach` or `install`.
- **Overlap with other work.** The per-command permission levels (another session) and the push-gap plan touch the same
  module and rule vocabulary. This plan edits neither `safe-git` nor `workbench/rules.py`.
- **Nothing is committed, pushed or deleted** except by the owner's word at each increment.

## Review record

Reviewed by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-26, at the
owner's request: three rounds, which is the bound of 3. Every finding was judged on the evidence and applied.
- Round 1 (two major): R1-F1, the plan reads `.workbench/review.json` where the spec designs
  `.workbench/action-review.json`; the owner chose the shared file, so the plan now says it changes a default of the spec,
  Increment A edits that section, and the personal-setting precedence is recorded as unbuilt. R1-F2, an always-approving
  fake bridge cannot decline a rubric-only case such as reviewer-directed text; the dangerous cases are split between code
  checks and a declining fake.
- Round 2 (one major): R2-F1, the spec's test that retired actions are refused was missing; added to the criteria and the
  rules increment.
- Round 3 (one major): R3-F1, the bridge call was not exact; Increment H now gives the argv and requires the bridge's
  result envelope to be validated before the reply is parsed.
All four were applied. Round 3 was the last within the bound, so its fix was not read by the engine. More rounds need the
owner's `extend`.

The author then checked the plan against the spec's acceptance criteria and against `module-boundary.md`, without the
engine, and found three more gaps, all applied: the engine must start other modules' commands only through the kit's
`run_command` (it said only `wb run`), the bridge call uses `--provides model-bridge`, and a criterion that `review` writes
no file. Those three edits have been read by no reviewer.

The review is not an approval; the plan stays `Proposed` for the owner.

## Deferred work

- The rule and checks for a push, after `describe push` exists.
- The thin hook, the log file and its writer, the labelled set, the report and the shadow period (plan 4); the cutover and
  M14 (plan 5).
- `remote-runner describe` and its rules (after M16).
- A personal (guarded-store) setting for the bridge, model and effort, and an option for a scratch root with no project
  content (a change to `model-bridge.md`).
- Raising or lowering the timeouts or the object cap, if the shadow period's durations or the measured rubric size show
  a reason.

## Result

### Increment A — committed as `8369cba`

Changed: `docs/specs/action-review.md` only. Added "The rule schema, the module and the checks" (module layout and
declaration, the call, the rule file and its fields, matching and precedence, flags and positionals, the checks for
`commit` and `remove` with their error-code mapping, the rubric, the `--log-row` flag, the time budget) and rewrote
"Settings and the bridge" to name `.workbench/review.json`.

Verification as run on 2026-10-26: `wb check`, `wb run code-work check` (51 plans), `doccheck`, `refcheck` and
`git diff --check` all clean, before and after the review fixes. Nothing else was run; no code exists yet.

Review: the `reviewer` agent, one exchange, eleven findings, all judged on the evidence.
- F1 (blocking, applied): decision 5 of `2026-10-22-model-calls-go-through-vendor-bridges` names
  `.workbench/<engine module>.json`, so the file name is not only a default of the spec. The spec now says it departs
  from decision 5. **A record that narrows or supersedes decision 5 for this file name is owed and is the owner's to
  accept; I have not drafted one.**
- F2 (applied): the kit allows 64 arguments, so positionals are bounded at 61, not 2000. A commit of more than about 50
  paths is unreviewable.
- F3, F5, F6, F7, F8, F9, F10, F11 (applied): the null-HEAD rule, the credential-name match, an absent or mistyped
  fact failing its check, quoted words that begin with `-` refused, the working directory as a requirement on the hook,
  the unreadable rules directory, null bridge fields for a code-check decline, and the wording of the approval.
- F4 (applied): a `describe` timeout is a refusal (exit 1) as in Increment E, and the bridge `--timeout` is always 20.
  The 5-second `describe` budget is the author's guess and is open for the owner.

Not done: B does not start before the owner reads the schema. The error-code-to-check mapping, the flag lists and the
quoted-word behaviour of the real `safe-git` parser are untested until Increments D to G. No second-model review ran.

### Increment B — committed as `8078763`

Changed: `packages/workbench/action-review/` (new: `module.json`, `helper/action-review`, `tests/test_actionreview_module.py`)
and `packages/workbench/package.json` (`action-review` after `review-engine`). The declaration is the spec's: `provides`
`action-review`, `requires` `model-bridge`, one command `action-review` with `review` as its only argument and no owner
list. The helper imports `os` and `sys`, starts no process, and refuses every call with one `refused:` line on standard
error, nothing on standard output, exit 1. The module ships only the helper for now; `rules`, `rubric` and
`reply-schema.json` arrive with their increments, and the file-list and import tests change then.

Also changed, outside the plan's list of affected areas: the hard-coded package-list assertions in
`claude/tests/test_claude_module.py`, `code-work/tests/test_codework_module.py` and
`groundwork/tests/test_groundwork_module.py` now include `action-review`. Adding a module to `package.json` breaks them,
so the change follows from the step.

Built and tested in a scratch copy, landed with one `cp`. The owner ran `release-approvals` (11 approvals written for 1
package); it warned that four old shipped records are not part of this release and must be removed by hand, which is the
owner's.

Verification as run on 2026-10-26: the new tests failed first (module absent, not listed), then 11 passed. The first full
`python3 -B -W error tests/run_all.py` in the scratch copy ran 4867 tests; only the three package-list assertions failed.
After updating them, those three roots and the new one passed. `wb check`, `wb run code-work check` (51 plans), `doccheck`,
`refcheck` and `git diff --check` were clean. A second full run in the scratch copy after the edits passed: 4867 tests in 11 roots, OK.

Review: the `reviewer` agent, one exchange, no blocking findings. Non-blocking, noted: the file-list and import tests
fail by design when later increments add files; no test covers `review --log-row` without text, which belongs to the
parser increment; the full suite had not been rerun after the three edits (the second run above). No second-model review
ran.

Not done: the grammar, rules, checks and bridge call (C to J); committing; removing the four stale shipped records.

(Increment B is committed as `8078763`, and the decision `2026-10-26-action-review-reads-the-review-setting` as `9d7cec6`.)

### Increment C — committed as `caf7518`

Changed: `packages/workbench/action-review/helper/action-review` (`parse_words`, `split_command`, `Unreviewable`, and
`review` now refuses unreviewable text before its "not built" refusal), `tests/test_actionreview_parse.py` (new) and
`tests/test_actionreview_module.py` (the import list).

The parser reads the spec's grammar: single-spaced words, each a bare word of `A-Za-z0-9._/:=@%+,-` or a single-quoted
string; a text of at most 4,096 characters. It also refuses, as the author's additions to the spec text: a bare word that
begins with `=` (zsh expands `=cmd` to a path), a bare first word that holds an `=` (an environment prefix, `A=1` and
`A+=1` alike), NUL inside quotes, and a character that cannot be encoded as UTF-8. A bare word beginning with `-` must be
one the caller declares, and a quoted word beginning with `-` is always refused. `split_command` matches the spelling and
subcommand whole word to whole word by value. Reserved shell words as a first word (`time`, `if`) are left to rule
matching in D, which only matches a spelling beginning `wb` or `git`.

Verification as run on 2026-10-27, in a scratch copy and landed with one `cp`: the tests failed first (no parser), then
52 module tests passed. They include a differential test of the engine against an independent regular-expression reading
of the grammar (about 9,000 generated and random texts, and every pair of characters), and generated text run through real
`sh`, `zsh` and `bash` with a fake program that prints its arguments: the engine's words equal the shells' arguments in all
three, none skipped. Two further shell tests show that `V=1 cmd` and `V+=1 cmd` set the environment and that zsh expands a
word beginning with `=`, which the parser refuses. A deliberate mutation (adding `$` to the alphabet) made six tests fail
and was reverted. Full `python3 -B -W error tests/run_all.py` in the scratch copy, three runs: the second passed in full
(4906 tests); the first and third (4908 tests) had every module root passing and one failure in the root `tests`,
`test_levellog` `test_parallel_appends_keep_every_line` (200 != 150), which passed alone three times. It is a thread-race
test in code this increment does not touch; the cause is not found. `wb check`, `wb run code-work check` (51 plans),
`doccheck`, `refcheck` and `git diff --check` were clean after landing.

Review: the `reviewer` agent, one exchange.
- Finding 1 (blocking, applied): `x+=1` is an append-assignment prefix in bash and zsh and the first pattern missed it.
  The parser now refuses any bare first word holding `=`; the unit tests, the reference reading and two shell tests were
  added with the fix (not run against the unfixed parser). The fix had no second review round.
- Finding 2 (applied): the shell tests now show the first-word and leading-`=` hazards on the real shells.
- Finding 3 (applied): the quoted alphabet in the shell tests now includes U+00A0, U+2028, ESC, DEL and the C1 bytes 0x80,
  0x83 and 0x9f.
- Finding 4 (recorded): only `/bin/sh`, `zsh -f` and `bash` without rc files were tested, so aliases, global aliases and
  zsh options from an rc file are not covered. **The grammar cannot defend against them: it is a requirement on the hook
  that the shell reading the command runs without them.** `LC_ALL=en_US.UTF-8` may not exist on every machine.
- Finding 5 (owed to Increment L): the spec's grammar bullet does not list the leading `=`, the first-word `=` or NUL
  rules; and whether the launcher's 4,096 limit counts characters or bytes is unchecked.
- Finding 6 (for D): `review` parses with no declared flags, so a flag word reports "not declared" until D; the test
  asserting the "not built" text changes then.

Not done: rules, the command's flag typing, checks and the bridge call (D to J). With the owner's approval the six stale
shipped records `release-approvals` listed were removed with `claude-workflow remove`, after a preview, and are in this
commit (it had warned about `0dde3b333a54`, `51d13076423d`, `63d178d2836c`,
`6d02998747b2`, `77a1f5745fae` and `ffe787e0fa3f`; the third and fourth are approvals Increment B added for a tree that
has since changed).

### Increment D — built, verified and reviewed (not committed)

Changed: `packages/workbench/action-review/helper/action-review` (the loader `load_rules`, `build_rule`, `find_rule`,
`parse_arguments`, `read_command`; `run` now loads the rules and reads the command before its "not built" refusal),
`module.json` (`ships` now lists the two rule files), `rules/safe-git-commit.json` and `rules/safe-git-remove.json` (new),
`tests/test_actionreview_rules.py` (new, 63 tests) and edits to `tests/test_actionreview_module.py` and
`tests/test_actionreview_parse.py` (file list, ships, imports, and the two tests that asserted the "not built" text).
The helper now imports `re` and the kit (`jsonstrict`, `project`, `safefs`).

What it does: a rule file under `.workbench/workbench/action-review/rules/` loads only if it fits the schema of Increment A
(format 1, the fixed fields and forms, a `subcommand` equal to the `action`, a `wb run` spelling ending in the module, the
file name `<module>-<action>.json`, only checks from the engine's fixed list of 14). A rule error is reported on standard
error as `rule error: <file name>: <fixed reason>` and never quotes the file; it refuses only its own key (read from the
spelling and subcommand, else from the file name against the first five words). Two files with one key, and two rules that
both match one command, refuse every file involved. The command is parsed twice: once letting dash words through to find
the rule, once with only the rule's flags (and `--`) declared. Flags follow their types; an undeclared flag, a repeated
single-valued flag, a missing required flag, a flag with no value or a flag as a value, a missing or second `--`, a flag
word after `--`, a count outside `min`/`max` and more than 61 arguments are refused. A directory that cannot be read, has
more than 64 entries or holds more than 262,144 bytes refuses every review. The shipped flags match `parse_commit` and
`parse_remove` of `safe-git` (read, not run against them).

Deviations from the spec, to be written into it by Increment L:
- The helper runs as a private copy with nothing beside it, so it cannot read its rules "beside itself". It reads them from
  the installed path below the project root found with `project.find_root(cwd)`, like the review setting. The package name
  `workbench` is fixed in that path.
- `ships` lists the two rule files, not a `rules` directory: a shipped item named `rules` is a word the installer's boundary
  test forbids it to use (`tests/test_boundary.py`, with the words read from the module declarations). Adding a shipped rule
  therefore means adding it to `ships`.
- A rule's `rubric` and `questions` are checked for form only. That a question is defined in its rubric section waits for
  Increment H, when `rubric.md` exists. The shipped rules carry no `lists`; the credential-name list arrives with F.
- A rule file read through a second hard link, a link, or a non-regular file is a rule error for its own key.

Verification as run on 2026-10-27, in a scratch copy and landed with one `cp`: the new tests failed first (41 errors, no
`load_rules`), then passed. Full `python3 -B -W error tests/run_all.py` in the scratch copy, two runs. The first (started before
the review fixes) failed twice: `test_boundary` (the `rules` word above, a real failure of this increment, fixed by listing
the files) and the known `test_levellog` flake. The last run, on the final tree, passed in every root and exited 0: 2942 root tests
(4 skipped), and 115 in `action-review`. After landing, in the real tree: `wb check`,
`wb run code-work check` (51 plans), `doccheck`, `refcheck` and `git diff --check` clean; the 115 module tests, `test_boundary`,
`test_run` and `test_firstparty` pass. The tests were not run against the real `safe-git describe` (that is Increment E),
and the new regression tests for the review fixes below were not run against the unfixed code.

Review: the `reviewer` agent, one exchange, seven findings.
- Finding 1 (blocking, applied): a `lists` entry that is not hashable (`[[1]]`, `[{}]`) raised `TypeError` in the loader and
  ended the whole run, so one bad file disturbed every key. Entries are now checked before the distinctness test; a test
  loads such a file next to a good rule. The fix had no second review round.
- Finding 2 (applied): a rule file with a second hard link was read; it is now read with the kit's no-hard-link reader and
  is a rule error. Tested.
- Finding 3 (applied): file names were echoed raw, so a name with a newline could forge a stderr line. Names are now
  printed with `ascii()`. Tested.
- Finding 4 (applied): the module and action form tests were refused by other checks, so they could not fail. They now use
  a matching file name and spelling, and the size limits are tested at the limit as well as over it.
- Finding 5 (applied): two assertions that accepted almost any message now name "separator".
- Finding 6 (recorded): the rubric and question check, and the `lists` for `commit`, belong to H and F (above). A rule that
  names `paths_not_credentials` with no `credential_names` list must fail that check, never pass it; F must test that.
- Finding 7 (recorded): `find_root(cwd)` takes the nearest project, so a nested project under the working directory would
  supply its own rules. Whether `wb check` drift or `acknowledge` covers the installed rule files was not checked and is for
  the security pass (K). The hook must start `review` in the directory where the command will run.

Not done: `describe`, the checks, the rubric and the bridge call (E to J); a second-model review; committing. `release-approvals`
was run by the owner (11 approvals written); it warned that the two records added in Increment C (`3aa496ba0dba` and
`f7b67a17cd4e`) are not part of this release. They are tracked and stale, and removing them needs the owner's word. Two new
untracked approval directories (`715ab071…`, `ac14b22f…`) belong in this commit.
