# The mempalace module

Status: In Progress
Created: 2026-10-24
Candidate: workbench-v1#mempalace-module
Specs: mempalace, knowledge-tools, module-boundary, module-contract, trust-and-approval

## Goal

Build the first-party module `mempalace`, which lets an agent in a workbench project search the MemPalace the
owner installed with `uv`, and gives the owner commands to build it. It is tooling over a pinned helper and not an
MCP server, and an agent can never write to the palace.

When this plan is done:

- `packages/workbench/mempalace/` is a first-party module of type `module` that provides `memory-recall`, ships
  one helper and one neutral skill, and fills the `policy` and `docs-index` slots;
- `wb run mempalace status` and `wb run mempalace search` return the program's text, bounded and marked as
  recalled data, and `init` and `mine` are owner-run and denied to the agent by the harness's rules;
- every point under "Evidence and open questions" in `docs/specs/mempalace.md` is answered from the real program
  or recorded as unanswerable, and the spec says what was found;
- no test starts a real `mempalace` or reaches a network;
- the shipped approvals match, and the specs, guide and README describe what was built.

## Scope

- **Evidence**, increment A: a retained, untracked run of the real `mempalace` in a scratch `HOME` under
  `/.debug/`, to answer the six open questions in the spec before any code depends on an answer.
- **The module** `packages/workbench/mempalace/`: `module.json`, `helper/mempalace`, the neutral skill
  `recall-memory`, the blocks under `files/blocks/`, and its tests with a fake `mempalace` program. The package
  list `packages/workbench/package.json` gains it.
- **The project setting** `.workbench/mempalace.json` (`{"format": 1, "palace": "<absolute path>"}`), read by
  the helper only.
- **The release** of the shipped approvals (owner-run) and, when the owner asks, a review with a security pass.
- **Docs**: `docs/specs/mempalace.md` ("As built, and its limits"), `docs/development.md` (the commands and what
  a real call needs), `README.md`.

## Non-goals

- Any write an agent can make to a palace, an MCP rendering of `mempalace-mcp`, or wrapping any subcommand beyond
  `status`, `search`, `init` and `mine`.
- Installing, updating or configuring the `mempalace` program, choosing its backend, or running its daemon.
- Mining the project's tree or any other module's store on the owner's behalf (`knowledge-tools.md`).
- `graphify` and the knowledge base (`workbench-v1#graphify-module`, `workbench-v1#knowledge-base-package`), and the
  shared conventions that only two built modules can justify.
- Changing the owner's global configuration, where the instruction not to use MemPalace unless asked stays (this
  module is that ask, for a project that installs it). That belongs to `global-config-migration`.
- A real call to `mempalace` in any test, and a hand run in a live Claude session (see Deferred work).

## Assumptions and constraints

- Python standard library only; tests with `unittest`; the full suite is `python3 -B -W error tests/run_all.py`,
  which gains a root for `packages/workbench/mempalace/tests`.
- The installer and its tests must not name `mempalace`, its helper or its paths (`tests/test_boundary.py`).
- The capability `memory-recall` has no prefix, so only the first-party package may provide it. The name is a
  proposal until the spec is accepted, and the spec is Current.
- Helper file names are unique across modules, and a command name is one pin name (`module-boundary.md`). The helper
  and the command are both named `mempalace`; no other module uses either.
- A skill name has one owner (`2026-10-23-one-owner-per-skill-name`); `recall-memory` is new.
- The installed program is `mempalace` 3.11.0 at `~/.local/bin/mempalace`, found by the helper only in an absolute
  `PATH` entry outside the repository, as `ask-codex` finds `codex`.
- The helper is written new, in the workbench's own words, from `docs/specs/mempalace.md`; it is a single file over
  the kit (`module-boundary.md`), and borrows the program-finding, environment and bounded-read code shapes of
  `packages/workbench/ask-codex/helper/ask-codex` by writing them again, since a helper cannot import another.
- Discovery tooling: graphify: skipped — not installed in this project; the scope was found by reading the specs
  and the `ask-codex`, `safe-git` and `groundwork` modules.

### Choices (made by me; the owner may change any)

1. **Evidence before code.** The spec's six open questions decide whether `search` is read-only, so increment A
   answers them first and may change the later increments (see the stop rule in A).
2. **The text is passed through, not parsed.** Unless increment A finds a machine-readable form, the helper returns
   the program's text inside a data marker and does not interpret it.
3. **The setting file is optional and the default passes nothing.** The helper never chooses a palace itself.
4. **`mine` defaults to a dry run** and refuses the project root unless the owner says otherwise, so the default
   cannot make the project's tree a second index.

## Completion criteria

1. Questions 1 and 4 of the spec's open questions are answered with evidence (`status` and `search` write nothing
   and send nothing out; the palace location is settled), and the other four are answered or recorded as "could
   not be determined" with a stated consequence for the helper. The spec's "Evidence and open questions" section
   says which, with the program version and the date, and the probes ran confined to a scratch directory.
2. `packages/workbench/mempalace/` verifies as a first-party `module`, provides `memory-recall`, requires nothing,
   declares the helper expectation `mempalace`, ships the helper and the skill, and `package.json` lists it.
3. Against a fake `mempalace`, `status` and `search` return its text bounded and marked as data, and a missing
   program, a non-zero exit, a timeout and an oversized output are distinct refusals.
4. `search` refuses an unknown option, `--include-media`, `--backend`, an empty query, an over-long query and
   `--results` over the ceiling, and passes a query beginning with `-` as a query.
5. `init` and `mine` are listed under `owner`; `init` always passes `--no-llm`; `mine` without `--confirm` passes
   `--dry-run`; a project-root target is refused without the explicit flag; neither passes a provider, key,
   endpoint, daemon or background option.
6. The child's environment holds only `HOME`, `PATH`, `LANG`, `LC_*` and what the spec lists, and the helper writes
   nothing in the project.
7. A project setting that is a link, malformed, oversized or holds a relative path is refused; a valid one is
   passed as `--palace`.
8. Installing the module pins its helper; an edited helper is refused; an argument it does not declare is refused.
9. The policy block and the skill carry the routing rule and the data-not-authority rule, and no tracked file of a
   project with the module names a palace path.
10. The full suite passes in every root, the boundary test passes, and no test starts a real `mempalace`.
11. The shipped approvals match the packages and the stale records are gone.
12. The spec, `development.md` and `README.md` say what was built and what its limits are.

## Increments

### Increment A — Run the real program and settle the open questions

**Outcome:** the spec's open questions are answered from evidence, so no later increment relies on a guess.
**Dependencies:** none.
**Affected areas:** `docs/specs/mempalace.md`; untracked `/.debug/2026-10-24-mempalace-evidence/` (excluded in
`.git/info/exclude`, never committed).
**Steps:**
1. Add `/.debug/` to `.git/info/exclude`. Make the scratch directory with a local `README.md` giving the commit
   SHA, the command and tool versions, the purpose and, at the end, the conclusion.
2. **Stop and ask the owner before the first run that could reach a network.** Say that a first `search`, `init`
   or `mine` may download an embedding model, and that `init` is run only with `--no-llm`. Run only with the
   owner's word.
3. **Confine the program before any probe.** Run every probe with `env -i` and a scratch working directory, passing
   only `PATH`, `LANG` and variables that point into the scratch directory: `HOME`, `XDG_CONFIG_HOME`,
   `XDG_DATA_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME`, `TMPDIR`, and, where the program documents or reads them
   (found with its `--help`, its installed source and `strings`-style search for `MEMPALACE_*`), its own location,
   backend and credential variables, each set to a scratch value or left unset. Give `--palace <scratch path>` to
   every command that accepts it. Before the first probe, run `status` under that environment with file-access
   tracing (`strace -f -e trace=file`) and record every path it opens. Sort them into two kinds. **Runtime reads**
   are the program's own installation (the `uv` tool directory), its interpreter and libraries, and system files
   such as certificates and locale data; list them by path and allow them, read-only. **Mutable state** is
   configuration, palace, index, cache, log and temporary files; every one must be inside the scratch directory,
   and no write or create may fall outside it. **Stop and ask the owner, and run no `init` or `mine`, if tracing
   is unavailable (a before and after `find` shows writes, not reads, and is not accepted as confinement
   evidence), if a read of the owner's real configuration or palace appears, or if any write falls outside
   scratch.**
4. Run the probes in that environment, for each of: (a) an absent palace; (b) a palace made by `init <small
   scratch dir> --no-llm --yes`; (c) the same after `mine <that dir>`. Probe `status`, a `search` that has
   results, a `search` that has none, `wake-up`, `mine <dir> --dry-run` and `mine <dir>`. Record the exact
   command, the exit code, the text on each stream, the files created or changed (before and after `find` with
   sizes and times), and any connection attempt (`strace -e trace=network`, or the program's own log).
5. Answer, with the evidence beside each answer: (1) whether `status` or `search` write anything or fetch a
   model; (2) the output form and whether a machine-readable one exists; (3) the exit codes for no palace and
   no results; (4) which palace location is current and what decides it; (5) whether `mine --dry-run` touches the
   palace; (6) whether `wake-up` is read-only and worth offering.
6. Update the spec's "Evidence and open questions" with the answers, the program version and the date.
   **Gate for B.** Increments B and later start only when questions 1 and 4 are answered with evidence: `status`
   and `search` write nothing in the palace and send nothing out of the machine (a model fetch counts as
   network, and is a stop unless the owner allows it), and the helper can leave the palace's location to the
   program or pass it with `--palace`. If either is undetermined, or an answer means `search` or `status` is not
   read-only, the behavior in the spec changes: stop, report both positions, and ask the owner; do not edit
   "Behavior" or continue to B on a guess. Questions 2, 3, 5 and 6 may stay undetermined only with a recorded
   consequence for the helper (for example, an exit code treated as an unclassified failure).
**Verification:** the scratch README states the conclusion and the confinement evidence; `git status` shows only
the spec changed; `git check-ignore .debug` names the exclude entry; the real `~/.mempalace` and
`~/.config/mempalace` are unchanged (listing before and after), and the access traces show only the listed
runtime reads outside the scratch directory and no read of the owner's real configuration or palace.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-24-mempalace-module#A`.

### Increment B — The module and its read-only commands

**Outcome:** `wb run mempalace status` and `search` work against a fake program and are listed in the package.
**Dependencies:** A.
**Affected areas:** `packages/workbench/mempalace/` (new), `packages/workbench/package.json`.
**Steps:**
1. `module.json`: name `mempalace`, version `0.1.0`, type `module`, a one-line description, provides
   `["memory-recall"]`, helpers `["mempalace"]`, ships `["helper/mempalace"]`, command `mempalace` with
   `helper`, `runtime: python`, `kit: 1` and `arguments` `["status", "search"]`. (C adds `init` and `mine`; D
   adds the skill and the fills.) No `requires`, `writes` or `blocks`.
2. `helper/mempalace`: read the arguments; find `mempalace` only in an absolute `PATH` entry outside the
   repository; build the environment from an allow list; run the program with no shell, a fixed argument shape,
   a 60-second limit that kills the process group, and an output cap; return the text inside a data marker.
   `search` passes only `--wing`, `--room`, `--results` (default 5, ceiling 20), `--since` and `--before`, takes
   the query as the one argument after `--` (at most 1000 characters, never read as an option), and never passes
   `--include-media` or `--backend`. Refusals are `refused: <reason>` on standard error with exit 1.
   The behavior follows what A found where A found something different from the spec's assumptions.
3. Tests with a fake `mempalace` that records its arguments, environment and standard input: the exact argument
   list; the scrubbed environment; the program found outside the repository only (one placed inside is not used);
   each refusal of criterion 3 and 4; a hostile reply (instructions, control characters, a huge line) returned as
   data; nothing written in the project.
4. Module tests: it verifies as first-party; the declaration fields of criterion 2; every file is the declaration
   or the helper; the package lists it.
5. Launcher tests: install pins the helper; an edited helper is refused; an argument that is not declared is
   refused.
**Verification:** the new root passes (`python3 -B -W error -m unittest discover -s
packages/workbench/mempalace/tests -t packages/workbench/mempalace/tests`); the boundary test passes; the
full suite passes except the shipped-approval tests that need the release in E.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-24-mempalace-module#B`.

### Increment C — The owner-run commands and the project setting

**Outcome:** the owner can build a palace through the module, safely by default, and a project can name its palace.
**Dependencies:** B.
**Affected areas:** `packages/workbench/mempalace/module.json`, `helper/mempalace`, tests.
**Steps:**
1. Add `init` and `mine` to the command's `arguments` and `"owner": ["init", "mine"]`.
2. `init <dir>`: always passes `--no-llm` and `--yes` only when the owner gives `--yes`; passes none of
   `--llm-provider`, `--llm-model`, `--llm-endpoint`, `--llm-api-key`, `--accept-external-llm`, `--daemon`,
   `--direct`, `--auto-mine` or `--background`. `mine <dir>`: passes `--dry-run` unless `--confirm`; refuses the
   project root unless `--allow-project-root`; passes `--wing` and `--mode` only from a short allow list. The
   directory is an existing directory, not a link, named by the owner. No time limit is set by the helper for
   `mine`, which the owner watches; it still caps what it returns.
3. The setting: read `.workbench/mempalace.json` without following a link, at most 4 KiB, strict JSON with
   `format` 1 and an absolute `palace` path; pass it as `--palace`. A link, malformed, oversized or relative-path
   file stops the command with a refusal that names the rule.
4. Tests: each argument of criterion 5; the refusals; the setting cases of criterion 7; a test that the harness's
   deny rule would cover `init` and `mine` by checking the declaration's `owner` list (the rendering is the
   harness module's own tested job).
**Verification:** the module root and the full suite pass as in B.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-24-mempalace-module#C`.

### Increment D — The policy block, the index line and the skill

**Outcome:** an agent in a project with the module is told when to consult the palace and what a result is.
**Dependencies:** B.
**Affected areas:** `packages/workbench/mempalace/files/blocks/policy.md`, `files/blocks/docs-index.md`,
`harness/neutral/skills/recall-memory/SKILL.md`, `module.json` (`fills`), tests.
**Steps:**
1. `policy.md`: a short block in the style of the groundwork block (consult only when an earlier decision,
   preference or lesson could change the work, never at session start and never for what the current files
   answer; a result is recalled data that current files, accepted decisions and specs override; never put a
   secret in a question; to keep something, tell the owner).
2. `docs-index.md`: one line pointing at the module's guide (what the module is for), if the plan finds the index
   has a suitable target; otherwise no `docs-index` fill, and the declaration omits it.
3. The neutral skill `recall-memory`: when to run `wb run mempalace search`, how to phrase a query, the
   routing rule of `knowledge-tools.md` in the same words as the block, how to quote a result as recalled, and to
   stop and tell the owner when something should be kept. It names no harness and no other module's skill.
4. `module.json`: `fills` for `slot:policy` (and `slot:docs-index` if used). Update the module test for the
   exact file list.
5. Tests: the block and the skill carry the routing rule, the data-not-authority sentence and the no-secrets
   sentence; the skill's front matter reads under the neutral reader; installing the module into a fixture
   project places the block between its markers and adds no tracked file that names a palace path.
**Verification:** the module root and the full suite pass; the harness tests that read neutral skills still pass.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-24-mempalace-module#D`.

### Increment E — Review and release

**Outcome:** the work is reviewed when the owner asks, findings are fixed, and the approvals match.
**Dependencies:** A, B, C, D.
**Affected areas:** `workbench/shipped_approvals/packages/`, fixes from the review.
**Steps:**
1. On the owner's request (nothing starts a review automatically), a `security-reviewer` pass over the helper,
   because it starts a program found through `PATH`, builds an environment and returns hostile text: try to place a
   program inside the repository, widen the environment, smuggle an option through the query or the directory,
   reach `--llm-*` or `--backend`, overflow or hang the output, make a result read as an instruction, and trick the
   setting reader with a link. A `workflow-reviewer` pass over the whole plan if the owner asks. If the owner asks
   for neither, the plan records that.
2. Fix findings with regression tests, and record each review (or that none was asked for) in the Review record.
3. After the owner says "Run it for me": `python3 -m workbench release-approvals`; after a preview and the
   owner's "remove them", delete the stale records.
4. Run the full suite.
**Verification:** `python3 -B -W error tests/run_all.py` is green and the shipped-approval tests pass.
**Evidence:** the review outcome in the Review record, the records added and removed and the suite counts in the
Result, in the one local commit, with the trailer `Plan: 2026-10-24-mempalace-module#E`.

### Increment F — Specs and guide

**Outcome:** the documents describe the system as it is.
**Dependencies:** E.
**Affected areas:** `docs/specs/mempalace.md`, `docs/specs/knowledge-tools.md`, `docs/development.md`, `README.md`.
**Steps:**
1. `mempalace.md`: replace "Nothing here is built" with what is built, and add "As built, and its limits"
   (the answers of A, what the tests cover, and what no test starts). Correct any proposed value the build changed;
   a change of direction stops for the owner.
2. `knowledge-tools.md`: record that `mempalace` is built and which conventions it actually used, as evidence only.
3. `development.md`: add the commands to the table (`wb run mempalace status|search`, and the owner-run `init` and
   `mine`) and a short section: what a real call needs (the `mempalace` program on `PATH`, installed by the
   owner), that the tests use a fake and send nothing, and where the palace comes from.
4. `README.md`: one bullet under "What is built".
**Verification:** the document checks pass (run by the owner in session, as `docs/README.md` states); the full
suite passes; `git diff --check` is clean; a search finds no document describing the module as unbuilt.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-24-mempalace-module#F`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in every root, including the new one.
- The behavior in criteria 3 to 8 is passed by a test, item by item.
- `git diff --check` is clean and `git status` is clean after the last commit.
- A real call through the module in a live project, with a real palace, is **not** part of this plan; it is a hand
  run by the owner (Deferred work). Increment A's run is of the program alone, in a scratch `HOME`.

## Risks and sensitive actions

- **A network and a download.** The real program may fetch an embedding model on first use. Increment A stops for the
  owner before the first run, uses a scratch `HOME`, and runs `init` only with `--no-llm`.
- **Content leaving the machine.** `init` can contact a language-model provider, some of them remote. The module
  never passes a provider option and always passes `--no-llm`; the owner who wants one runs the program directly.
  Mining files content into the palace; `mine` is a dry run by default and refuses the project root by default.
- **A program found through `PATH`, and its hostile text.** The helper finds it only outside the repository,
  scrubs the environment, bounds the output and returns it as data. Increment E gives this an adversarial pass if
  the owner asks.
- **A palace is untracked and persistent.** A drawer filed in error cannot be removed through this module (the
  owner uses the program). The module writes nothing an agent could mis-file, and the skill says never to put a
  secret in a question.
- **A stale recollection read as fact.** Mitigated in text only: the block and the skill say a result is data
  that current files override. No mechanism enforces it.
- `release-approvals` rewrites the shipped approvals; it runs only on the owner's exact words, and the stale records
  are deleted only after a preview and the owner's "remove them".
- Nothing is pushed by this plan.

## Review record

Reviewed by Codex (`gpt-6.1-sol`, effort medium) on 2026-10-24, at the owner's request, with the owner's personal
`ask-codex` tool (`plan-review`). Three rounds of a bound of 3; outcome: converged, with nothing disputed. The
sealed state is untracked, in `/.debug/2026-10-24-plan-review/`.

- R1-F1 (applied, major): changing `HOME` alone does not confine the program. Increment A now runs every probe
  under `env -i` in a scratch working directory, with all location variables pointing into scratch, `--palace`
  given, and a file-access trace taken first.
- R1-F2 (applied, major): the plan let B proceed with the safety of `status` and `search` undetermined. Increment A now
  gates B on open questions 1 and 4, and probes an absent, an initialized and a populated palace, with a successful
  and an empty search.
- R2-F1 (applied, major): "every path inside scratch" could not be met, since the program's own installation is
  outside it. Runtime reads are now listed and allowed read-only; mutable state and all writes must be in scratch.
- Round 3 found nothing. The R2-F1 fix was reviewed in round 3.
- Found afterwards, not by the reviewer: `strace` is not installed on this machine (checked 2026-10-24), and
  increment A's confinement step names it. The owner installed it the same day (`strace` 6.19, `/usr/bin/strace`;
  a test trace ran). This note was added after round 3 and was not reviewed.

## Deferred work

- A hand run in a live Claude session with a real palace and a real install, by the owner.
- An MCP rendering of `mempalace-mcp`, once the workbench has an MCP layer (`module-boundary.md`).
- Any agent-callable write (filing a drawer or a knowledge-graph fact), behind a checkpoint, if the owner wants it.
- A project-level setting for the result limits, and a second program backend, if a need appears.
- The shared conventions of `knowledge-tools.md` revised from what `mempalace` and `graphify` actually share
  (`workbench-v1#graphify-module`).

## Result

### Increment A (2026-10-24)

Ran the real `mempalace` 3.11.0 in a scratch directory, confined as the increment describes (`env -i`, scratch
`HOME` and XDG directories, `--palace` in scratch, `strace` 6.19, a network namespace with no network except for
one run). The findings are in `docs/specs/mempalace.md` ("Evidence"); the retained traces are in the untracked
`/.debug/2026-10-24-mempalace-evidence/`, with a README. Real `~/.mempalace`, `~/.config/mempalace`,
`~/.cache/chroma` and `~/hallways.json` did not exist before or after.

Deviations from the approved text, each made with the owner's word in session:

- Python bytecode (`.pyc`) writes into the program's install directory were allowed as a runtime effect, and
  `PYTHONDONTWRITEBYTECODE=1` was set for the remaining probes (the owner agreed on 2026-10-24). They happened once,
  in the `init` probe, before the variable was set.
- One networked run was allowed by the owner: `mine` of a scratch project, which downloaded the 79.3 MB model into
  the scratch cache. No other probe had a network.
- The gate for B stopped on question 1: `search` rewrites the palace's bookkeeping (not drawer content) on every
  call, so it is not write-free. The owner chose option 1 (accept and document, refuse `search` unless the model is
  already cached). The spec and `knowledge-tools.md` were changed to match, and the roadmap candidate's boundary
  now reads "no change to drawer content" in place of "no write". Increments B and C follow the spec as amended.

Also found, and recorded in the spec: `init` writes `mempalace.yaml` into its target directory, `mine` writes
`$HOME/hallways.json`, `wake-up` creates the palace database (so it is not offered), and a failed `search` or `mine`
prints its error on standard output. Still undetermined: the default palace for a fresh home, whether
`XDG_CACHE_HOME` alone moves the model cache, and behavior on a large palace or another backend.

### Increment B (2026-10-24)

Built `packages/workbench/mempalace/`: `module.json` (command `mempalace`, arguments `status` and `search`, helper
expectation `mempalace`), `helper/mempalace` (one file over the kit) and its tests (61 tests: the declaration, the
helper against a fake `mempalace`, and the pinned helper through the real launcher). The full suite is green
(3744 tests in 8 roots; one skip). Mutation checks on the helper (dropping `--`, passing the caller's environment,
skipping the model gate, trusting relative or in-repo `PATH` entries) each made a test fail; the relative-entry
mutation first survived, which added two tests. A run of the helper against the real program in the scratch `HOME`,
with no network, returned a search and a status between markers and refused a search once the model directory was
moved away.

Choices and departures, none changing a spec behavior:

- A refusal (`refused:`) means nothing was started. A program failure (a non-zero exit, a timeout, output over the
  bound) is `failed:` on standard error, exit 1, with the program's words (cut to 2000 characters) on standard
  output between markers. The marker lines carry a random token per call so that recalled text cannot close the block.
- `mempalace` is last in `package.json`, since `safe-git`'s test requires it directly after `groundwork`. The exact
  module lists in the `claude`, `code-work` and `groundwork` tests were updated.
- **Not done here:** the spec's refusal for a recorded model other than `minilm` needs the palace's location
  (`mempalace_embedder.json` sits in it) and so comes with the project setting in increment C. The refusal text names
  the owner's `mine`, which increment C adds.
- The helper passes no `XDG_*` variable, as the spec says, so a user with a non-default `XDG_CACHE_HOME` or
  `XDG_CONFIG_HOME` gets the program's default places under `HOME`.

### Increment C (2026-10-24)

Added `init` and `mine` (declared under `owner`) and the project's palace setting to the helper and the declaration,
with 44 new tests (105 in the module; full suite 3788 in 8 roots, green) and mutation checks on the properties that
matter (`--no-llm` dropped, `mine` not a dry run, no terminal check, project root allowed, setting not passed, recorded
model not checked, link allowed in the directory, caller's environment passed to an owner command): all eight made a
test fail. Run against the real program in a scratch `HOME` and a throwaway project, from a pseudo-terminal and with no
network: `init --yes` wrote `mempalace.yaml` in the named directory and the setting's palace was the one used, a dry-run
`mine` filed nothing, the project root was refused, and a piped run was refused.

Departures from the approved text, each flagged to the owner when reported:

- **The owner commands run only from a terminal and are handed the terminal; the helper does not capture them.** The
  approved step said the helper "still caps what it returns". The real `init` asks the owner to accept the rooms unless
  given `--yes`, and crashes with a traceback on end of input, so a captured run with no input could not serve it.
  The helper therefore refuses unless standard input and output are terminals (the rule `approve` uses, friction and not
  authentication, and independent of whether a harness renders the deny) and hands the terminal to the program, with no
  time limit and no output cap. A terminate signal stops the program itself (not anything it started) and removes the
  scratch directory; an interrupt at the terminal reaches the program, and the helper waits for it. `docs/specs/mempalace.md`
  is amended to say so.
- `init` also refuses the project root, and a directory that holds it, unless `--allow-project-root` is given (the
  plan named only `mine`); the evidence showed `init` writes `mempalace.yaml` into its target.
- `mine` takes `--wing` and `--mode projects|convos` only; `--mode extract` needs an extra the owner did not install.
- Every command now finds the project and refuses outside one, since the setting lives in it.
- The recorded-model check (deferred from B) is done: with a palace named by the setting, a `mempalace_embedder.json`
  that names a model other than `minilm`, is unreadable, is a link or is oversized refuses the search.

Not covered by a test: a real interrupt at a terminal (`Ctrl-C`) during `mine`, and a program that spawns workers that
outlive a terminate signal.

### Increment D (2026-10-24)

Added the policy block (`files/blocks/policy.md`, 10 lines), the neutral skill `recall-memory`
(`harness/neutral/skills/recall-memory/SKILL.md`) and the `fills` entry for `slot:policy` in `module.json`, with 19 new
tests (124 in the module; full suite 3807 in 8 roots, green). The block and the skill carry the routing rule in the words
of `docs/specs/knowledge-tools.md`, the rule that a result is recalled data that current files override, the no-secrets
rule, and that an agent cannot file a memory. The skill runs only `wb run mempalace search` and `wb run mempalace status`,
tells the agent to stop and report a refusal, never to run `init` or `mine`, and that a low match score means the memory has
nothing on the subject (the real program returns the nearest notes even for an unrelated question, found in increment A).
An install test shows the block between its markers in `AGENTS.md`, Claude receiving the skill, and no installed file outside
the module's namespace naming a palace path.

Choices and departures:

- **No `docs-index` fill.** The only guide to the module is this repository's own spec, which is not shipped to a project,
  and the module writes no file of its own, so the index has nothing to point at. The plan allowed this.
- The block and the skill name `graphify` and "the knowledge base" because the routing rule does, and say a tool that is not
  installed is skipped; neither module exists yet, and the skill names none of their skills.
- Whether Claude loads the skill when it should is not tested, as for the other modules' skills.
