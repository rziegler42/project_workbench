# The remote-runner module

Status: In Progress
Created: 2026-10-24
Candidate: workbench-v1#remote-runner-module
Specs: remote-runner (new), code-work, trust-and-approval, module-contract

## Goal

The owner runs long checks on SSH runners with the `remote-runner` program. Today its project contract is
`.claude/remote-runner.toml`, a harness path the workbench never commits, and the agent calls the program directly under
the owner's global rules in `~/.claude/CLAUDE.md`. `code-work.md` already names two checkpoints, `submit-remote-job` and
`fetch-remote-output`, and `trust-and-approval.md` says remote job output is untrusted and that overwriting a tracked or
existing file with it is a hard stop. Nothing in the workbench carries any of that out.

When this plan is done:

- a module `remote-runner` exists in `packages/workbench/`, and a project that installs it keeps its job profiles in the
  committed file `.workbench/remote-runner.toml`, read by `wb run remote-runner profiles` and checked by `wb check`;
- the agent submits, inspects and fetches through `wb run remote-runner <command>`, a guarded wrapper over the
  external program, which allows only the argument shapes the spec lists, never forwards an overwrite, and never
  contacts anything but the program;
- an overwrite of an existing or tracked file is a command only the owner runs (`fetch-overwrite`), so the agent
  cannot reach it;
- a neutral skill `run-remote-job` tells the agent the routine, including the provenance rule for a remote result;
- `docs/specs/remote-runner.md` records the contract, including what the external program must change to read the new
  path, and the module is proven against a fake `remote-runner` program, as `ask-codex` was against a fake `codex`;
- the package approvals are released by the owner.

## Scope

- The spec `docs/specs/remote-runner.md` (increment A).
- The module skeleton, the config reader `profiles`, the check, and a template (increment B).
- The guarded runner and the read-only and submit wrappers (increment C).
- The fetch wrappers (increment D).
- The skill `run-remote-job` (increment E).
- Spec edits elsewhere, approvals and the Result (increment F).

## Non-goals

- A change to the `remote-runner` program. It lives outside this repository. This plan writes down what it must do and
  tests the module against a fake; making the real program read `.workbench/remote-runner.toml` is the owner's work,
  and until it is done the module cannot submit a real job.
- Host details (SSH names, workspace roots, capacity). They stay in the owner's personal `~/.claude/remotes.toml`.
  The module neither reads nor writes that file, and the project config never holds a host.
- Running anything over SSH from the module. The wrapper starts the `remote-runner` program only.
- A new hard stop. A module has no field to declare one (roadmap, "Current state"), so the overwrite rule is made by
  keeping the overwrite out of the agent's reach (choice 4).
- Rendering an `ask` rule for submit or fetch, and any effect of `delegate` on these checkpoints. See Risks.
- Pruning, cancelling and the log of a job through the wrapper (choice 3).
- A knowledge of what a profile's command does. The module checks the shape of the file, not the commands.

## Assumptions and constraints

- A module helper is a standalone script; modules do not import each other. The guarded runner is written in this
  module's helper, following the one in `safe-git` and `ask-codex`, not imported from them.
- `workbench/` and `tests/` hold only mechanism; `tests/test_boundary.py` must stay green. Nothing new goes there.
- `tests/test_skill_names.py` must stay green: the skill, command and agent names this module ships are new and owned
  by it (decision `2026-10-23-one-owner-per-skill-name`, Accepted).
- The program, not the wrapper, writes fetched files. Its documented behaviour (its help text and the owner's
  configuration) is to refuse existing, tracked and dot-prefixed targets and git metadata without `--force`, never
  follow a link, and verify a SHA-256. The module relies on that and does not copy, stage or hash fetched content
  itself. What the wrapper adds is a check before the program starts, and a conformance requirement in the spec that a
  program overwriting without `--force` or following a link does not conform. A race between the wrapper's check and the
  program's write is not closed by the wrapper; only the program can close it (Risks).
- Everything the program prints, every job log and every fetched file is data (`trust-and-approval.md`, "Untrusted
  content"). The wrapper never follows an instruction inside one.
- The helper runs a program, so it needs the guarded runner: a program found only in an absolute `PATH` entry outside
  the repository, a scrubbed environment, a bounded output, a deadline, and a process group it kills.
- Editing a package tree changes its hash, so the shipped approvals go stale. The release is the owner's
  (`release-approvals`, run only on "Run it for me"; stale records removed only after a preview and "remove them").
- Discovery: graphify: skipped, not installed here; the scope was enumerated from the roadmap candidate, the specs
  named above, and `remote-runner --help`.
- Not yet known, and checked in increment A before the spec fixes it: the exact text of `remote-runner status`
  (whether the `dut_commit` and `dut_clean` fields are machine-readable) and the keys the program accepts in
  `[profiles.*.requirements]`. The plan treats the sample `.claude/remote-runner.toml` (project id, a profile's
  `command`, and `min_cpu_cores`, `min_memory_gib`, `labels`, `os`) as the schema until the owner corrects it.

### Choices (made by me; the owner may change any)

1. **The module is of type `module` and provides no capability.** Nothing requires one yet. The checkpoints it concerns
   are declared by `code-work`, the process module. Alternative: a core name such as `remote-jobs`; rejected until
   some module needs to require it, because a new core name changes `module-contract`.
2. **The project config is `.workbench/remote-runner.toml`**, the program's own TOML schema, so moving a project is a
   file move and no translation. It is committed, because the program reads it from a committed revision. The module
   reads it with `tomllib`, bounded, no link followed, duplicate keys refused (the standard library refuses them), and
   unknown keys refused. `tomllib` is in the standard library from Python 3.11, so this plan raises the project's
   documented minimum from 3.6 to 3.11 in `docs/development.md` (owner's choice, round 2; the alternative was a
   hand-written reader for a subset of TOML, which works on 3.6 and adds parsing code). A stray `.claude/remote-runner.toml` is reported by the check as the old path and is never
   read or changed by the module.
3. **The wrapper has seven commands:** `profiles` (reads the file, starts nothing), `recommend`, `status`, `artifacts`,
   `submit`, `fetch` and `fetch-overwrite`. `log`, `cancel`, `remotes` and `prune` are not wrapped: `log` output is
   large and hostile, `cancel` and `prune` change state on the runner and have no checkpoint, and `remotes` shows host
   details. The agent asks the owner for those. Alternative: wrap everything; rejected as a wider surface than the
   candidate's boundary.
4. **Overwrite is owner-only.** `fetch` never passes `--force`, and refuses a `--dest` outside the repository or a name
   starting with a dot or `.git`. `fetch-overwrite` passes `--force` and is listed under `owner` in the module's
   `commands`, so a harness with `permissions` denies it to the agent (`module-boundary.md`). This stands in for an
   added hard stop, which the declaration cannot yet express.
5. **Submit is a checkpoint by instruction and by the harness prompt, not by a new rule.** `submit-remote-job` and
   `fetch-remote-output` stay `stop` and `code-work` owns them. The skill says to wait for the owner's word. What
   prompts in a given harness is the owner's `allow` rules for `wb run`, which the workbench never writes. See Risks.
6. **Submit takes a declared profile only.** The wrapper reads `.workbench/remote-runner.toml`, refuses a profile it
   does not declare, takes `--remote <name>` or `--best` (a name matching the program's own pattern) and `--ref` or
   `--snapshot`, never both. A ref is a branch name, tag name or 40-hex commit under the same name rules as
   `shared-branches.json`; a leading dash, `..` or `@{` is refused. The wrapper cannot check that the revision is
   reachable from the remote; the program does and the wrapper reports its refusal.
7. **A remote result is evidence only with provenance.** The skill, and a `provenance` field in the wrapper's `status`
   output, say a result counts only when the program records `dut_commit` equal to the submitted commit and
   `dut_clean: true`. If increment A finds the program's status is not machine-readable, `status` passes the
   program's bounded text through and the skill tells the agent to read the two fields, and the field is dropped.

## Completion criteria

1. `docs/specs/remote-runner.md` states the module's declaration, the config schema, the seven commands and their
   allowed argument shapes, the guarantees of the wrapper, what the program must change, a conformance checklist and
   the limits. It is reviewed by the owner and reads `Current` only after approval.
2. `packages/workbench/remote-runner/` is a module that the verifier accepts, that installs into a project and
   attaches for the Claude layout, with a shipped approval.
3. `wb run remote-runner profiles` prints `{"format": 1, "project": "<id>", "profiles": [...]}` from
   `.workbench/remote-runner.toml`, an absent file is an error that says so, and a link, an oversize file, a
   malformed or repeated key, an unknown key or a wrong type is refused; it starts no program.
4. `wb check` reports a malformed config and a leftover `.claude/remote-runner.toml`, in bounded lines, and reports
   nothing for a project without the module.
5. `recommend`, `status`, `artifacts` and `submit` start only the `remote-runner` program, only in the argument shapes
   the spec lists, with a scrubbed environment, bounded output and a deadline; a refused shape, an undeclared
   profile, a ref that is not a plain name, a program found inside the repository and a repeated option are each
   refused with the reason, and nothing is started. The program's output is returned bounded and marked untrusted.
6. `fetch` asks the program to copy named files into the repository only, and the guarantees are split as the spec
   states. The wrapper checks before it starts the program: no `--force`, no `--dest` outside the repository or
   through a link, no absolute or traversing job path, no dotted or `.git` target, and no destination that already
   exists. The program provides, and the spec lists as a requirement of it (`trust-and-approval.md`, "Outside
   content"): the SHA-256 check of what it copies, refusal of git metadata, links, and tracked or existing targets
   without `--force`, and the no-follow write. The wrapper returns the program's hash line in its bounded output and
   records no hash itself. `fetch-overwrite` exists, is listed under `owner`, and the rendered Claude settings deny
   it.
7. The skill `run-remote-job` ships in the module, names no other module's skill, uses only the wrapper commands, and
   carries the phrases of choice 7 and the checkpoint rule.
8. The module passes the spec's conformance checklist against a fake `remote-runner` program; no test starts the real
   one, and none contacts a host.
9. The specs say what is built and its limits; the full suite, `doccheck`, `refcheck` and `git diff --check` pass; the
   package approvals are released by the owner and the suite then runs with no Claude skip.

## Increments

### Increment A — The spec and the unknowns

**Outcome:** a draft spec the owner can approve, with the program's two unknowns settled from evidence.
**Dependencies:** none.
**Affected areas:** `docs/specs/remote-runner.md` (new); the specs index if one exists.
**Steps:**
1. Settle the two unknowns without starting a job: read `remote-runner --help` for each command, and ask the owner for
   one redacted `remote-runner status` output and the program's accepted profile keys (or its source, if the owner
   points to it). Cite the program by its name, version and the date; the owner's sample is cited by the date and
   content hash, not by path.
2. Write the spec with the same sections as `model-bridge.md` and `review-engine.md`: purpose and scope, declaration,
   config schema, the commands and their argument shapes, what the wrapper guarantees, untrusted input, what the
   program must change to read `.workbench/remote-runner.toml`, the conformance checklist, acceptance criteria and
   open questions. Status `Draft`.
3. Run `doccheck`, `refcheck` and `git diff --check`.
**Verification:** the document checks print nothing; the spec's checklist items each map to a completion criterion.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-remote-runner-module#A`. The spec stays a draft until
the owner approves it.

### Increment B — The module, the config reader and the check

**Outcome:** a module that installs, and a project config the installer's check understands.
**Dependencies:** A.
**Affected areas:** `packages/workbench/remote-runner/module.json`; `helper/remote-runner` (new, `profiles`);
`checks` helper; `tests/` in the module; the shipped `docs/` template if the spec calls for one;
`docs/development.md` ("Setup": the minimum Python version).
**Steps:**
1. Tests first: the declaration passes the verifier; the config reader accepts a valid file and refuses each case in
   criterion 3; the check reports a malformed config, a leftover `.claude/remote-runner.toml`, and nothing without
   the module; the helper has standard-library imports only and, in this increment, imports no `subprocess`. Run them
   and see them fail.
2. Write `module.json` (type `module`, `ships`, `commands.remote-runner` with `arguments: ["profiles"]`, `checks`),
   the helper's `profiles`, and the check. The helper imports `tomllib` and nothing outside the standard library.
3. Change the minimum in `docs/development.md` to 3.11, naming `tomllib` as the feature that sets it and keeping the
   sentence that the minimum is derived from the features used, not from running older interpreters.
4. Run the module tests and `tests.test_boundary` and `tests.test_skill_names`, and search the docs for a statement of
   the old minimum.
**Verification:** `env PYTHONPATH=. python3 -B -W error -m unittest discover -s packages/workbench/remote-runner/tests
-t packages/workbench/remote-runner/tests`; the two root tests named.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-remote-runner-module#B`.

### Increment C — The guarded runner, `recommend`, `status`, `artifacts`, `submit`

**Outcome:** the agent can ask for runners, check a job and submit a declared profile, with nothing wider.
**Dependencies:** B.
**Affected areas:** the helper (the runner and four commands); `module.json` (`arguments`); the fake program under the
module's `tests/`; new tests.
**Steps:**
1. Tests first, against a fake `remote-runner` that records its argument vector, environment and working directory to
   a file: each command passes only its allowed shapes; every refusal in criterion 5 starts no program (the record is
   absent); the environment is scrubbed to a named list; the program is found only in an absolute `PATH` entry outside
   the repository; output is bounded and a large output sets `truncated`; a deadline kills the process group and a
   child it started is gone; a program name planted inside the repository is never run; text that looks like an
   instruction in the output is returned as data. Run them and see them fail.
2. Write the runner and the four commands. Print one JSON line: the command, the exit status, the bounded output
   (decoded as replacement text), and `truncated`. On a refusal write `refused: <reason>` to standard error and exit 1,
   as `safe-git` does.
3. Run the module tests and the two root tests.
**Verification:** as increment B.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-remote-runner-module#C`.

### Increment D — `fetch` and `fetch-overwrite`

**Outcome:** output of a finished job reaches the repository only inside the rules, and an overwrite is the owner's.
**Dependencies:** C.
**Affected areas:** the helper; `module.json` (`arguments`, `owner`); new tests, including one that renders the Claude
settings for an attached module.
**Steps:**
1. Tests first: `fetch` passes job id and relative paths only; a path that is absolute, has `..`, begins with a dot or
   names `.git` is refused before the program starts; `--dest` is refused unless it resolves inside the repository
   without a link, and a link anywhere on the destination path is refused; a target that already exists (a file, a
   directory or a link, including a dangling one) is refused before the program starts and the fake records no start;
   `--as` is allowed for one file and validated as a plain file name; `--force` can be passed by no option of
   `fetch`; the program's hash line in the fake's output is returned unchanged in the bounded output and the helper
   writes no hash or file of its own; `fetch-overwrite` passes `--force` and is in `owner`; the rendered Claude
   settings deny `wb run remote-runner fetch-overwrite` and do not deny `fetch`; no `allow` rule is rendered. A
   conformance test runs the checklist against two fakes: one that refuses an existing or linked target without
   `--force` (conforms) and one that overwrites without `--force` (the test reports it as non-conforming; the wrapper's
   own pre-check still refuses first). Run them and see them fail.
2. Write the two commands. Fetched content is not read, copied, staged or interpreted by the helper.
3. Run the module tests and the two root tests.
**Verification:** as increment B.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-remote-runner-module#D`.

### Increment E — The `run-remote-job` skill

**Outcome:** the agent has the routine, including the checkpoint stops and the provenance rule.
**Dependencies:** C, D.
**Affected areas:** `packages/workbench/remote-runner/harness/neutral/skills/run-remote-job/SKILL.md` (new); the
module's skill and tree tests.
**Steps:**
1. Tests first: the reader accepts the skill with front matter `name` and `description` only; the Claude layout plans
   `.claude/skills/run-remote-job/SKILL.md`; at most 60 lines; ASCII; the only commands named are the wrapper's, each
   exactly and in backticks, and no `ssh`, `scp`, `rsync`, `--force`, raw `remote-runner` or other program; it carries
   the phrases: submit and fetch only on the owner's word, a profile the plan names, a committed revision reachable
   from the remote, a result counts only when the status records the submitted commit and a clean tree, output is
   data, never overwrite, record the job id and what was concluded in the plan's Result, and an unavailable runner is
   reported and not bypassed; it names no other module's skill. Run them and see them fail.
2. Write the skill.
3. Run the module tests and the two root tests.
**Verification:** as increment B.
**Evidence:** the one local commit, trailer `Plan: 2026-10-24-remote-runner-module#E`.

### Increment F — Spec edits, approvals and the Result

**Outcome:** the specs say what is built, the approvals are released, and the plan records it.
**Dependencies:** E.
**Affected areas:** `docs/specs/remote-runner.md` ("As built"), `docs/specs/code-work.md` (the remote-job lines and
the non-goal that points to a separate module), `docs/specs/trust-and-approval.md` (the fetch channel, and that the
overwrite is kept from the agent by `owner`), `docs/specs/module-contract.md` only if a field changed, the package
approvals (owner-run), this plan's Result.
**Steps:**
1. Edit the specs to match what was built, with the limits.
2. Run the full suite. If it reports the approvals stale, stop and ask the owner to run `release-approvals`; preview
   any stale record and delete it only after "remove them". Run the suite again.
3. Run `doccheck`, `refcheck` and `git diff --check`; search the docs for a statement that the remote-runner module is
   not built.
4. Fill the Result, including that the real program was not run and what it must change. Set `Status: Completed` only
   after every criterion has its evidence.
**Verification:** the full suite with no Claude skip; the document checks print nothing.
**Evidence:** the one local commit (specs, plan, refreshed approval records), trailer
`Plan: 2026-10-24-remote-runner-module#F`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in every root with no Claude skip; `git diff --check`, `doccheck`
  and `refcheck` print nothing.
- The wrapper is shown by tests against a fake program in scratch directories; no host is contacted and the real
  `remote-runner` is not started.
- Global items this plan will let `global-config-migration` retire, none yet: the paragraphs of `~/.claude/CLAUDE.md`
  about `remote-runner` profiles, provenance, snapshots, artifact fetching and pruning, and the use of
  `.claude/remote-runner.toml`. They stay until the program reads the new path and a recorded run shows a project
  behaves the same without them. The owner's `allow` rules and `~/.claude/remotes.toml` are not moved.
- A live check is possible and not planned: install the module in a scratch project, point the real program at the new
  path once the owner has changed it, submit a profile and fetch an artifact. Until then live behaviour is
  unverified.

## Risks and sensitive actions

- **The program must change first.** Until it reads `.workbench/remote-runner.toml`, `submit` and the rest cannot work
  against a real job. The module is verified only against a fake, so a mismatch with the real program's behaviour
  (output text, exit codes, flags) is possible and is found only by the live check.
- **A checkpoint with nothing to enforce it.** The skill is advice, and the module renders no `ask` for submit or
  fetch. What prompts is the owner's `allow` rules for `wb run`, which are the owner's. A permissive rule lets the agent
  submit a job without a prompt. The plan does not add a rule (choice 5); the owner decides whether it should.
- **Spending the owner's runners.** A submitted job uses the owner's machines and time. The profile must be declared in
  a committed file and the skill requires the owner's word; the wrapper cannot see what a profile's command does.
- **Fetched files are untrusted.** A fetched file may hold an instruction or a link, and a tracked file overwritten by
  `fetch-overwrite` loses work. The overwrite is owner-only (choice 4); a security pass on the new surface is part of
  review if the owner asks.
- **The fetch guarantees depend on the program.** The hash check, the refusal of tracked targets (which needs git, and
  the wrapper runs none), the refusal of git metadata and the no-follow write are the program's. The wrapper's own
  check before the start covers an existing target and a link, and a program that does not conform is caught only by
  the spec's checklist, not at run time. A race between the check and the write is not closed. Verified only against
  fakes until the owner runs the real program.
- **Running a program from a hostile repository.** The runner refuses a program found in the repository, scrubs the
  environment and bounds time and bytes; every argument is validated before it reaches the program.
- **The minimum Python version rises to 3.11.** It applies to the project as `docs/development.md` states it, not to
  this module alone, and nothing here is run on an older interpreter. Anyone on Python 3.6 to 3.10 would find the new
  module unusable; the checks have been run only on 3.14 so far.
- **The package tree changes.** Approvals go stale; the release is the owner's and stale records are deleted only after
  a preview and "remove them".
- No push, no job submitted, no host contacted, no install into a project, no secret and no deletion beyond stale
  approval records.

## Review record

Round 1 of 3, 2026-10-24, `ask-codex review-plan`, model `gpt-5.6-luna`, effort medium (asked for by the owner).
Outcome: changes needed; one major finding.

- R1-F1 applied in part (the owner said "apply"). The plan did not say who enforces the trust specification's fetch
  guarantees. Criterion 6, the assumptions, increment D and the risks now split them: the program verifies the hash and
  refuses git metadata, links, and tracked or existing targets without `--force`; the wrapper checks before it starts
  for a destination outside the repository, a link, an existing target and `--force`, returns the program's hash line,
  and records no hash. Not applied as worded: the finding says that omitting `--force` does not prevent an overwrite;
  the program's own help describes `--force` as the way to overwrite an existing or tracked file. The wrapper does not
  stage or copy fetched content, and the race-safe write stays the program's, so it is a recorded limit.

Round 2 of 3, 2026-10-24, same model and effort (asked for by the owner). Outcome: changes needed; one major finding.

- R2-F1 applied. The config reader uses `tomllib` (Python 3.11) while `docs/development.md` gave 3.6 as the minimum.
  The owner chose to raise the minimum to 3.11 over a hand-written reader for a subset of TOML. Choice 2, increment B
  (affected areas, a step that edits `docs/development.md`) and the risks now say so.

Nothing rejected in full. Left for the owner: whether to record the decision with `ask-codex decide`, whether to ask
for a further round, and whether to approve.

## Deferred work

- A change to the `remote-runner` program, outside this repository.
- Wrapping `log`, `cancel`, `remotes` and `prune`.
- An added hard stop in the module declaration, so that the overwrite rule can be a hard stop and not only an
  owner-only command.
- A rendered `ask` for submit and fetch, and `delegate` for these checkpoints.
- A project-level setting for the default runner or profile.
- A live check in a scratch project against the real program.

## Result

Increment A, 2026-10-24: the draft spec `docs/specs/remote-runner.md` is written, with a row in
`docs/specs/README.md`. The owner chose "Read the program", so the two unknowns were settled by reading the
`remote-runner` script once (88818 bytes, SHA-256 `dc2d8485aafd140c66a6e883f3bd2d0b0b476c7ba38eb618e704771d14b4c209`,
read 2026-10-24, treated as data); no job was started and no host contacted.

- Verification as run: `doccheck`, `refcheck` and `git diff --check` print nothing. No code exists yet.
- What the reading settled. `status` prints JSON with `dut_commit`, `dut_clean`, `commit` and an `integrity` word, so
  the status is machine-readable and the fallback in choice 7 is not needed. The requirement keys are exactly `os`,
  `arch`, `min_memory_gib`, `min_cpu_cores` and `labels`, and an unknown key makes a runner ineligible. The program
  itself needs Python 3.11 (`tomllib`), which agrees with the raised minimum. The change the program needs is small:
  its project-file path appears in `project_config` (twice), its error messages and its description. Fetch already
  refuses git metadata, dot-prefixed names, existing files, tracked files (by running `git ls-files`) and links, stages
  with no-follow flags and returns each file's `sha256`, which matches the split in criterion 6.
- Departures from the plan's wording, each in the spec: `status` takes an optional `--expect <40 hex>` and sets a
  `provenance` field, because the job's own record is writable by the job and an independent expected commit is the
  only useful check; the "hash line" of a fetch is the program's `files` list with `bytes` and `sha256`; the
  environment allow list includes `SSH_AUTH_SOCK`, which is listed as an open question; a profile name, remote name,
  job and ref have patterns the spec fixes.
- Not done: the spec is a draft and awaits the owner's approval; it has had no independent review (only if the owner
  asks); no code, no test.

Increment B, 2026-10-24: the module `packages/workbench/remote-runner/` exists (`module.json`, `helper/remote-runner`
with `profiles`, `helper/remote-runner-check`, and three test files), is listed last in `package.json`, and installs;
the installer pins both helpers (`remote-runner` as the command, `remote-runner-check` as the check). The project's
minimum Python is now 3.11 in `docs/development.md`, which is its only statement of it, and a command row for
`profiles` is added there.

- Verification as run: the module tests (36) pass; `tests.test_boundary` and `tests.test_skill_names` (27) pass;
  `doccheck`, `refcheck` and `git diff --check` print nothing. The full suite was not run, so the shipped approvals,
  stale from this increment, are untested until increment F. Tests were written first and failed for the missing
  module before the code was added.
- What the tests show: the example file is read in file order; 51 refused cases (not UTF-8, not TOML, arrays too
  deep for the reader, a repeated key, an unknown key or table at each level, a wrong type, a name, label or id
  outside its pattern, bounds on commands, labels, numbers and the profile count) are each refused, and no reason
  repeats anything of the file; a link, a directory or a file over 65,536 bytes is refused and the tree is unchanged;
  an absent file is `refused: no project file`; `wb check` reports a refused file and a leftover
  `.claude/remote-runner.toml` under the module's name and reports nothing for a project without the module; the helpers
  import only the standard library and the kit, never `subprocess`, and a program of the same name on `PATH` is not
  started.
- Decisions made in this increment (mine; the owner may change any): there are two helper files because a helper may
  not be both a command and a check and helpers do not import each other, so the rules for the project file are one
  fenced text in both, and a test requires the two texts to be equal; `os` and `arch` may be empty strings, as the
  spec's "at most 64" reads (a runner never matches an empty value, so it fails closed); a reason names a profile
  only after its name has passed the pattern.
- Not done: no program is run by either helper; the spec text is unchanged (the "As built" edits are increment F).

Increment C, 2026-10-24: `helper/remote-runner` now has the guarded runner and the commands `recommend`, `status`,
`artifacts` and `submit`; `module.json` lists them as `arguments`. Tests: `support_program.py` (a fake
`remote-runner` that records its argument vector, environment, working directory, process id and whether standard
input is the null device) and `test_remoterunner_run.py`. `docs/development.md` has a row for the four commands.

- Verification as run: the module tests (69) pass; `tests.test_boundary` and `tests.test_skill_names` (27) pass. The
  `doccheck`, `refcheck` and `git diff --check` print nothing. The full suite was not run (approvals stale until F). No real `remote-runner` was started and no host contacted.
- Test order: I wrote the tests and the helper before the first run, so the plan's "see them fail" step did not
  happen for this increment. As a check I changed the environment allow list to pass `PYTHONPATH` and the
  environment test failed on it; I reverted that.
- What the tests show: each command passes exactly its row (nine accepted shapes across the four commands); 41
  refused shapes start nothing and leave the tree unchanged; a missing or invalid project file refuses only
  `recommend` and `submit`; the program runs in the project root with no standard input; the environment is the allow
  list (no `GIT_*`, `LD_*`, `DYLD_*`, `PYTHON*` or token) and `PATH` is the trusted entries only; a program in the
  project, on a relative, empty or `.` entry, behind a link into the project, or in a trusted entry that is itself a
  link into the project is never run; output over 65,536 bytes is cut and marked, output over 1 MiB stops the program;
  a hanging program and its child are gone at the deadline and on SIGTERM to the helper; instruction-like text and
  control characters come back only as cleaned text; `status` returns only the listed fields, drops a bad one, and sets
  `provenance` in each case.
- Departures from the spec's wording, to be written into it in increment F (mine; the owner may change any):
  1. A program stopped at its deadline or for too much output is reported with `exit` 124 or 125 and a `detail`
     (the spec has only "exit: int"); the helper exits 1 in those cases, and in any case where the program's exit is
     not 0.
  2. `provenance` is `false` when the program's exit is not 0, even if it printed a matching view.
  3. A ref is also refused if it holds `/.` or a character git forbids in a ref (`~ ^ : ? * [ \`, by allowing only
     `A-Za-z0-9 . _ / + @ -`); the spec lists only the other rules.
  4. `provenance` does not require `integrity` to be `ok`, as the spec reads. Whether it should is left to the owner
     (a record the job rewrote can pass either way).
- Not done: `fetch` and `fetch-overwrite` (increment D); a security review of the runner (only if the owner asks).

Increment D, 2026-10-24: `fetch` and `fetch-overwrite` are in `helper/remote-runner`; `module.json` lists both as
`arguments` and `fetch-overwrite` under `owner`. New tests: `test_remoterunner_fetch.py` (the fake program in
`support_program.py` gained a fetch mode and a `conformance_problems` function that runs a program directly against
the checklist). `docs/development.md` has a row for the two commands.

- Tests first: written before the code and run: 14 failed and 2 errored for the missing commands. Then, with the
  code, the module tests (85) pass; `tests.test_boundary` and `tests.test_skill_names` (27) pass. Full suite not run
  (approvals stale until F). No real program, no host.
- What the tests show: `fetch` passes the job and the relative paths, then `--dest` and `--as`, and never `--force`;
  44 refused shapes (a path that is absolute, has `..`, an empty part, `.git`, a dotted part, a leading dash, a
  backslash, a control character or is over 512 characters; more than 16 paths; `--dest` outside the project, a dot,
  missing, a file, a link, below a link, `.git`, `.workbench`; a target that exists as a file, folder, link or
  dangling link, or lies below a link or a file; `--as` with two paths, a slash, `..`, a dot or dash start, or an
  existing target) start nothing and leave the tree byte-for-byte as it was; the program's files list with its
  hashes comes back unchanged in `output`; an AST test shows the helper never calls `open` or a call that writes,
  moves or links a file; the rendered `.claude/settings.local.json` of an install denies `run remote-runner
  fetch-overwrite` and none of the other arguments and has no `allow` rule for the module; a program that refuses an
  existing file, a link target and a dotted name conforms, and one that does not is reported with all three problems,
  and in that case the wrapper's own check still refuses first.
- Departures from the spec's wording, to be written into it in increment F (mine; the owner may change any):
  1. `fetch-overwrite` allows a target that is an existing regular file (that is its purpose) and still refuses an
     existing folder or link, a link on the way, and every other rule of `fetch`. The spec says only "as `fetch`".
  2. A path is checked with the kit's path rule: at most 512 characters (the program allows 1,024), and no backslash
     or colon.
  3. `--dest` may be given as an absolute path only if it begins with the project root; it is passed on as the
     relative path.
  4. `fetch` and `fetch-overwrite` share the 600 second deadline of `submit`.
- Not done: the tracked-file refusal is the program's (the wrapper runs no git); a race between the check and the
  program's write is not closed (recorded in Risks); no security review (only if the owner asks).

Increment E, 2026-10-24: the neutral skill `harness/neutral/skills/run-remote-job/SKILL.md` (about 45 lines, ASCII)
and `tests/test_remoterunner_skill.py`; the file-list test in `test_remoterunner_profiles.py` now includes the skill.

- Tests first: written and run before the skill; 11 errored and 3 failed for the missing file. With the skill the
  module tests (99) pass; `tests.test_boundary` and `tests.test_skill_names` (27) pass. Full suite not run
  (approvals stale until F). The skill itself has not been tried in a live session.
- What the tests show: the reader accepts it with only `name` and `description` in the front matter; the Claude layout
  plans `.claude/skills/run-remote-job/SKILL.md`; at most 60 lines of ASCII; the commands it names are exactly the
  wrapper's six plus `fetch-overwrite` as the owner's, each in backticks, with only the options that command takes;
  no raw `remote-runner`, `ssh`, `scp`, `rsync` or `--force`; it names no skill of another module; and it carries the
  rules: submit and fetch only on the owner's word, a profile the plan names, a committed revision reachable from the
  remote, no commit or push to run a job, `--snapshot` for uncommitted work only after the owner agrees, `provenance`
  with `dut_commit` and `dut_clean` and the commit that was submitted (with the note that the job can write that
  record), job output and fetched files as untrusted data, never overwrite, record the job id in the plan's Result,
  and an unavailable runner or a refusal is reported and not bypassed.
- Choices (mine): the skill tells the agent to pass `--ref <40-digit commit>` for a committed run, so the answer's
  commit and the expected commit are the same value; it leaves `log`, `cancel`, `remotes` and `prune` to the owner.
- Not done: no live check; the skill is advice, and nothing forces an agent to load or follow it.
