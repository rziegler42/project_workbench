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

### Increment A — written, awaiting the owner's reading (not committed)

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
