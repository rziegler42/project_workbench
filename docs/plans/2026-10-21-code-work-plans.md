# The code-work module: plans and its read-only helper

Status: In Progress
Created: 2026-10-21
Candidate: workbench-v1#code-work-plans
Specs: code-work, module-contract, trust-and-approval, installer-interface, harness-modules

## Goal

Give a project the plan format and the means to read its plans, and prove the path every later
`code-work` helper subcommand will use: a module that ships code, a launcher that runs only the bytes
the owner pinned, and a helper that reads a repository anyone may have written. Today the installer
has the launcher and the pins but no module ships a helper, nothing installs `docs/plans/`, and no
tool knows what a plan is.

When this plan is done:

- a first-party process module `code-work` exists in `packages/workbench/`. It provides `plans`,
  requires `specs`, `roadmaps` and `decisions`, and installs `docs/plans/README.md`, a `docs-index`
  entry, a policy block, one skill for drafting a plan and one shipped helper;
- `wb code-work check`, `wb code-work plans` and `wb code-work report` run that helper through the
  launcher, change nothing, and say what is wrong with a plan, which plans are active and which
  roadmap candidates have a completed plan;
- the helper is pinned when the owner installs, upgrades or adds the module, and is not run after
  its bytes change until the owner acknowledges the change.

## Scope

- **The module** `code-work`: `module.json` (type `process`), the README for `docs/plans/`, the two
  slot blocks, the drafting skill with its template bundled, and the helper.
- **The helper**: one self-contained Python file with the read-only subcommands `check`, `plans` and
  `report`. It reads plans and roadmaps itself, within bounds and without following links.
- **The plan format** as the spec states it: title, `Status:`, `Created:`, one `Candidate:`, `Specs:`,
  increment headings `### Increment <label> — <title>`, unique labels, the insertion form `B-A`,
  and a warning past 15 increments.
- **`wb code-work <subcommand>`**: the installer command that finds the project, finds the pin and
  launches the helper, so an agent need not know a project ID.
- **Pinning**: install, upgrade and add pin the shipped helper; acknowledge pins it again.
- **The first-party release**: the package gains a module, so its shipped approvals are made again
  (`release-approvals`, which the owner runs).
- **Decision records**, written `Proposed` for the owner to accept (see "Decided by me").
- **Spec and guide updates** for what was built and decided.

## Non-goals

- `commit` and `remove` (`code-work-commit`), and everything after: plan approval, the delegation
  helper, the gate on starting an increment, checkpoint settings, review, the reviewer agent, loop
  caps, push rules and the compaction guidance (`code-work-approval`).
- Any write by the helper. `check`, `plans` and `report` change no file.
- Checking that a plan that records a decision has the decision file (spec: completeness against
  repository state). The plan check here is the shape of one plan; `report` reads a plan's
  `Candidate:` and `Status:` only.
- Hooks, opencode, and moving anything out of the owner's `~/.claude`.

## Assumptions and constraints

- Python standard library only; tests with `unittest`; full suite
  `python3 -B -W error -m unittest discover -s tests` (1878 tests today, 1 skipped on macOS).
- A helper is run by the launcher from a private copy in the guarded store, so it is one file that
  imports nothing from `workbench/`. It must not trust its working directory or `sys.path`.
- Everything the helper reads is untrusted repository content: bounded in count and bytes, read
  without following links, never evaluated, reported with escapes removed. It runs no program.
- The installer never runs a module's code at install (`trust-and-approval.md`); the launcher runs the
  helper only when someone invokes it.
- The approval record for a plan does not exist yet. Until `code-work-approval` it is the owner's
  explicit statement in session, so the policy block says that and not "recorded approval", and
  `check` does not claim to verify an approval.
- Upgrade never changes an existing plan: the module owns none.
- **Decided by me, for the owner to confirm or change before approval:**
  1. **The plan check lives in the shipped helper**, as `code-work.md` says, and not in the
     installer as the groundwork checks do. This module already ships code, so the argument of
     `2026-10-21-installer-runs-document-checks` (a module with no code needs the installer) does
     not apply. *Alternative:* a `wb check` addition that reuses `doccheck.py`, which gives one
     tested reader and no pin step, but makes the installer know the plan format and leaves the
     helper with nothing to prove. The helper repeats the fence and quotation handling of
     `doccheck.py`; a parity test on a hostile corpus keeps the two in step.
  2. **`wb code-work <subcommand>` is dispatch in the installer**: it resolves the project root by
     walking up to a directory with `.git` and `.workbench/manifest.json`, reads the project ID, looks
     up the pin named `code-work` and calls the launcher. *Alternative:* the agent runs
     `wb launch <id> code-work --root . -- check`, which works today but needs the 64-digit ID.
  3. **The shipped file `helper/<module-name>` is the module's helper and is pinned by name.** No new
     declaration field. *Alternative:* a `helper` field in the declaration; clearer, and a change to
     the module contract that nothing else needs yet.
  4. **Install, upgrade and add pin the helper; acknowledge pins it again.** The owner has just
     confirmed a digest over exactly those bytes, so a separate `wb pin` adds friction and no
     information. *Alternative:* print the `wb pin` line and let the owner run it; nothing new in the
     installer, one extra step per release and per acknowledged edit. A pin made by the installer is
     recorded as made by it.
  5. **The policy block says approval is the owner's explicit statement** until `code-work-approval`
     replaces it; it names no checkpoint the module cannot yet enforce.
- Discovery: graphify — skipped, this project has no discovery tooling. The files read for this plan:
  `launch.py`, `pins.py`, `cli.py`, `declarations.py`, `modulefiles.py`, `doccheck.py`, `installed.py`,
  `docs/specs/code-work.md`, `trust-and-approval.md`, `module-contract.md` and the old `claude-workflow`
  helper. Increment A re-checks, by running it, what the installer does with a process module that
  ships a file.

## Completion criteria

1. Installing `code-work` with `groundwork` and the Claude module into an empty directory succeeds,
   creates `docs/plans/README.md` and no placeholder plan, and fills the `docs-index` and `policy`
   slots. Installing it without `groundwork` stops with a hard-requirement message. Two process
   modules are refused (the one-process rule).
2. The helper is the one shipped file named in `ships`, imports only the standard library, and a
   pin for it exists after the install. `wb code-work check` runs it; after the file is edited the
   same command refuses with a reason and runs nothing, and after `wb acknowledge` it runs again.
3. `check` reports each of: no `Candidate:` line, two, `Candidate: none` with no reason, no `Specs:`
   line, no `Created:` date, a status outside the five, an increment heading of the wrong form, a
   repeated label, a label out of order, and a plan name that is not `YYYY-MM-DD-<topic>.md`. A plan
   with more than 15 increments gives a warning and one with more than 26 a problem. Exit 0 means no
   problem; a warning alone exits 0.
4. `plans` lists the plans whose status is `Proposed`, `Approved` or `In Progress`, sorted by name.
   `report` lists each roadmap candidate that has at least one `Completed` plan naming it, and each
   plan whose `Candidate:` names a roadmap or candidate that does not exist. Without `groundwork`'s
   roadmaps both report nothing and do not fail.
5. No subcommand writes a file, takes a lock, runs a program or follows a link, and `.git/index` is
   byte-identical after each. A bound passed is a problem that says what was not looked at.
6. Every hostile case in Review focus has a test that fails without its guard, and an adversarial
   `security-reviewer` pass over the helper and the dispatch finds nothing Medium or higher unresolved.
7. Upgrading a project that has plans changes none of them, and an edited README or slot block is a
   conflict and not an overwrite.
8. `code-work.md`, `module-contract.md`, `trust-and-approval.md`, `installer-interface.md`,
   `docs/development.md` and the roadmap describe what was built, and the full suite passes with
   `-W error`.
9. The decision records exist under `docs/decisions/`, and the plan is not marked `Completed` before
   they do.

## Review focus

Inputs the specs imply that the tests must pin, most likely to bite first:

1. **Hostile plans.** A huge file, thousands of headings, a heading that is a terminal escape, a
   `Candidate:` line or an `### Increment` heading inside a code fence, a quotation or an HTML
   comment (a fenced one must not count), a `Candidate:` line after the first `##`, a name with
   `..`, a case-colliding name, a link at `docs/plans` or at one plan, a plan that is a directory.
2. **A helper that is not what was pinned.** An edited helper, a helper replaced by a link, a pin
   for another project, a missing pin, a helper that reads next to itself (the private copy has no
   neighbours), and the working directory holding a `json.py` or `os.py` (it must not be imported).
3. **Dispatch from the wrong place.** Run from a subdirectory, from outside any project, from a
   project with the manifest but no `code-work`, from a directory with a forged `.workbench/manifest.json`
   but no `.git`, with a symbolic link at `.workbench`, and with arguments that start with `-` or
   contain `--`.
4. **Increment labels.** `A` to `Z`, `AA`, `B-A`, `B-A-A`, a lowercase or non-ASCII label, a label that
   differs from another only by Unicode form, a duplicate, and a gap or reorder. The 15 and 26 limits.
5. **Candidate references that lie.** `Candidate:` naming a roadmap that is not there, a candidate not
   in the roadmap, two roadmaps with one candidate ID, a dropped candidate, and an ID that matches
   only after case folding (it does not match; IDs are exact).
6. **Two plans, one day.** Different topics do not collide, and no subcommand reads or writes an
   index or a "next" file.
7. **A project with the name but not the module**, and one with the module and no `docs/plans/`: no
   crash and no false problem.
8. **An upgrade over edited files.** An edited README, an edited slot block, an edited helper (a
   conflict, and the pin is not moved until acknowledged).

## Increments

### Increment A — What the installer already does for a process module that ships code

**Outcome:** the five decisions rest on a run, not on reading: a fixture module shaped like
`code-work` installs, is pinned by hand, launches, and upgrades, and the gaps are named.
**Dependencies:** none.
**Affected areas:** tests only (a fixture module in `tests/`), and a short note in the plan's Result.
**Steps:**
1. Failing tests with a fixture `process` module that provides `plans`, requires `specs`, `roadmaps`
   and `decisions`, writes one README, fills `docs-index` and `policy`, and ships `helper/fixture`.
   Install it with the Claude module and `groundwork`.
2. Run them and record: where the shipped file lands and whether it is executable; whether the
   manifest and the baselines cover it; whether the module's approval request lists it as code; what
   `wb pin` and `wb launch` need from that file; whether `wb acknowledge` lists a changed helper; and
   whether a second process module is refused.
3. If a gap blocks Decision 1, 3 or 4, stop and report it to the owner before increment B.
**Verification:** the new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-code-work-plans#A`.

### Increment B — The helper: bounded reading and `check`

**Outcome:** a single file that reads a project's plans safely and reports the shape of each.
**Dependencies:** A.
**Affected areas:** `packages/workbench/code-work/helper/code-work` (new), tests.
**Steps:**
1. Failing tests, loading the file by path: each case of Completion criterion 3 and Review focus 1
   and 4; the bounds (2,000 files, 4 MiB in all, 1 MiB per plan, 200 findings, as `doccheck.py`);
   escapes removed from anything printed; no import outside the standard library (checked by parsing
   the file); output on standard output and `problem:` and `warning:` lines on standard error.
2. Write the reader: open the project with no-follow, descriptor-relative reads, one pass over
   `docs/plans/`, and a line scanner that tracks fences, quotations and HTML comments the way
   `doccheck.py` does. The helper decides the project root from its working directory and refuses
   outside one.
3. Write the plan parser and `check`. A bound passed is a problem naming what was not examined.
4. A parity test: on a corpus of hostile Markdown, the helper and `workbench.doccheck` agree on which
   lines are in a fence or quotation.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-code-work-plans#B`.

### Increment C — `plans` and `report`

**Outcome:** the other two read-only subcommands.
**Dependencies:** B.
**Affected areas:** the helper, tests.
**Steps:**
1. Failing tests: Completion criterion 4 and Review focus 5 and 6, on real git repositories with
   roadmaps from the groundwork format. Candidate IDs are read as `doccheck.py` reads them.
2. Implement. `report` prints nothing, and succeeds, when there is no `docs/roadmaps/`.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-code-work-plans#C`.

### Increment D — The module, its blocks and its skill

**Outcome:** `packages/workbench/code-work/` verifies, installs, and gives a Claude clone a skill for
drafting a plan.
**Dependencies:** A, B.
**Affected areas:** `packages/workbench/code-work/` (`module.json`, `files/`, `harness/neutral/skills/draft-plan`
with `template.md`), `packages/workbench/package.json`, tests.
**Steps:**
1. Failing tests: the module verifies; the install creates `docs/plans/README.md` and no other file
   under `docs/plans/`; it needs `groundwork` and refuses a second process module; the blocks are
   replaced on upgrade only while unedited; the skill reaches `.claude/skills/draft-plan/` with its
   template and is not in `git ls-files`; no skill runs a command beyond `wb code-work check`.
2. Write the declaration, the README (the format, the increment labels, status values, what is not
   a plan), the policy block (Decision 5, in neutral behaviour terms), the index entry and the skill.
3. Add the module to `package.json`. The package tree hash changes, so the first-party tests skip until
   increment G, and this increment says so.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-code-work-plans#D`.

### Increment E — `wb code-work`

**Outcome:** one command runs a pinned helper without the caller knowing the project ID.
**Dependencies:** A, D.
**Affected areas:** `workbench/cli.py`, a small new `workbench/dispatch.py`, tests.
**Steps:**
1. Failing tests: Review focus 3 and 2. Exit codes and `refused:` text follow `launch`; the helper's
   own exit code is returned; arguments after the subcommand are passed through unchanged; with no
   pin the message names the pin and the owner's step.
2. Implement: find the project root without running git; read the committed manifest through the
   existing reader; call `launch.run` with the module's name. Only `check`, `plans` and `report`
   are accepted as subcommands; anything else is refused before launching.
3. `wb code-work` is not an owner-run command and is not denied by the Claude rules; a test pins the
   rendered deny list unchanged.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-code-work-plans#E`.

### Increment F — Pin on install, upgrade and add; pin again on acknowledge

**Outcome:** the owner never types a pin for a first-party helper, and an unacknowledged edit stops it.
**Dependencies:** A, D, E.
**Affected areas:** `workbench/install.py`, `upgrade.py`, `acknowledge.py`, `pins.py`, tests.
**Steps:**
1. Failing tests: after install the pin names the shipped path and its hash; an upgrade that changes
   the helper moves the pin only when the owner-confirmed plan includes it; a pulled edit leaves the pin
   and `wb code-work` refuses; `wb acknowledge` of that path moves the pin; the pin file is strict and
   a helper outside the module's namespace is never pinned.
2. Implement. A pin made here records the installer as the pinner. The preview of each command lists
   the pin it will make, so the digest the owner types covers it.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-code-work-plans#F`.

### Increment G — Security pass, release and end-to-end

**Outcome:** the package is first-party again and the whole path is proven.
**Dependencies:** B to F, and the security pass.
**Affected areas:** `workbench/shipped_approvals/`, tests.
**Steps:**
1. An adversarial `security-reviewer` pass over the helper, the dispatch and the pinning; fix, add
   regression tests, and have a second reviewer try to bypass each fix.
2. Ask the owner to run `release-approvals`, which re-records the shipped approvals. I do not run it.
3. Tests: install `claude`, `groundwork` and `code-work` into an empty directory, attach, commit,
   write plans by hand, run `wb code-work check`, `plans` and `report`; an upgrade changes no plan.
**Verification:** the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-code-work-plans#G`.

### Increment H — Documentation and decisions

**Outcome:** the specs, the guide, the roadmap and the decision records match what was built.
**Dependencies:** A to G.
**Affected areas:** `docs/specs/code-work.md`, `module-contract.md` (the helper convention),
`trust-and-approval.md`, `installer-interface.md`, `harness-modules.md`, `docs/development.md`,
`docs/roadmaps/workbench-v1.md`, `AGENTS.md` (the Bootstrap reference to `code-work-module`),
`workbench/harnessplan.py` (a comment that names it), `docs/decisions/` (two records, `Proposed`).
**Steps:**
1. Edit the documents; record every limit found. Replace remaining uses of `code-work-module` with
   the candidate that now owns each item.
2. Write `docs/decisions/2026-10-21-plan-check-in-the-shipped-helper.md` (Decision 1, with the
   installer-check alternative) and `docs/decisions/2026-10-21-pinned-helper-by-convention.md`
   (Decisions 2 to 4: dispatch, the shipped-helper convention and pinning by the installer).
**Verification:** `git diff --check`; every claim matched to a test or a run.
**Evidence:** commit with trailer `Plan: 2026-10-21-code-work-plans#H`.

## Verification for the plan as a whole

- Full suite with `-W error` after every increment, recorded in the Result.
- A read-only `workflow-reviewer` review per increment, when the owner asks.
- The security pass in increment G, with a bypass attempt on each fix.
- A recorded hand run on a second machine: install the three modules into an empty directory, commit,
  draft a plan with the skill in a live `claude` session, run `wb code-work check`, `plans` and
  `report`, then edit the helper and see the launch refuse. Needs the owner's allowance.

## Risks and sensitive actions

- **The first module that ships code the launcher runs.** The launcher is a pin check and not a sandbox
  (`launch.py`). A flaw in the helper or in pinning is a flaw in every later subcommand, including the
  commit helper. The security pass is mandatory and runs before the release.
- **A helper that repeats a reader.** It cannot import the installer's reader, so the fence and
  quotation handling exists twice. The parity test is the control, and a drift is a finding.
- **Pinning by the installer widens what install does.** It writes one more record in the store, for
  bytes the owner confirmed by digest. The preview lists it. Decision 4 is the owner's to change.
- **Policy text is read by agents.** A block that claims a recorded approval before one exists would
  mislead; the block states what is true now and is tested for what it says.
- **The package tree hash changes** with this plan, so first-party approvals are stale between D and G.
  The tests that need them say so; nothing ships in between.
- Actions that need the owner: `release-approvals`, any `approve`, accepting the two decisions, and
  the hand run.

## Review record

Round 1 of 3, 2026-10-21, requested by the owner: Codex (`gpt-5.6-luna`, medium effort, read-only).
Outcome `converged`, no findings. The reviewer checked the plan against the specs, the decisions, the
roadmap candidate and the current code. The review is still open (not archived).

## Deferred work

- `commit`, `remove` and the first-commit fix (`code-work-commit`).
- Plan approval, delegation, the gate, checkpoints, review, caps, push and compaction guidance
  (`code-work-approval`).
- Checking that a completed plan that lists a decision has the decision file.
- A `helper` field in the module declaration, if a second module needs to ship a helper.

## Result

### Increment A — what the installer already does (2026-10-21)

`tests/test_codework_fixture.py` (15 tests) runs a fixture `process` module that provides `plans`,
requires the three groundwork capabilities, writes a README, fills both slots and ships
`helper/codework`. Full suite: 1893 tests, 1 skipped, passing with `-W error`. Nothing in the
installer changed. Recorded:

- It verifies, as a first-party package too. The approval request lists the shipped path.
- The shipped file lands at `.workbench/<package>/<module>/helper/<name>` (for the real module
  `.workbench/workbench/code-work/helper/code-work`), class `module-owned`, hash in the manifest and
  a baseline in the store. It has no executable bit, and the launcher does not need one.
- `docs/plans/README.md` is `seeded`: written once, then the project's. Both slot blocks land between
  markers. The manifest records the module by package, name, version and hashes only.
- A missing provider of a required capability stops the install, and a second `process` module is
  refused.
- **Gap for increment F:** install records no pin, and an upgrade that replaces an unedited helper
  moves no pin, so the new bytes are refused by `launch` until pinned again.
- An edited helper is refused by `launch`, and `upgrade` refuses until it is acknowledged, naming the
  path. Existing plans are never changed by an upgrade.
- No gap blocks Decisions 1, 3 or 4. Decision 2 (dispatch) needs the project ID, which the committed
  manifest holds; increment E reads it from there.

### Increment B — the helper: bounded reading and `check` (2026-10-21)

`packages/workbench/code-work/helper/code-work` (one file, standard library only) and
`tests/test_codework_helper.py` (46 tests, 2 skipped on macOS: a non-UTF-8 name and a case-variant
name). Full suite: 1939 tests, 108 skipped, passing with `-W error`. The helper reads
`docs/plans/` through descriptors opened with `O_NOFOLLOW`, never writes or runs a program (a test
reads the source for the calls), finds the project from its working directory (a `.git` directory and
a regular `.workbench/manifest.json`), and bounds what it reads as `doccheck.py` does.

- **The 108 skips are new.** The package gained a directory, so its tree hash no longer matches the
  shipped approvals and the tests that need them skip, as the plan said they would from D. They begin
  at B and not D because the helper is written in its final place. Nothing in B or C touches what
  those tests cover; the owner's `release-approvals` in G ends it.
- **Found by the repository test:** this repository's own plans repeat a heading of the form
  `### Increment A — ...` in their Result notes. Only headings under `## Increments` are therefore
  increments, and a plan with no such section is a problem that says how many headings were not
  checked. Other rules fixed by the test: `Created` must equal the date in the name; a missing
  `Specs:` line is a problem (its value may be empty); the status may be followed by text (`Superseded
  by <plan>`).
- **Agreement with the installer:** a test compares the helper's fence and quotation reader with
  `doccheck._lines` on a corpus. The helper goes one step further than the installer: a comment that
  starts a line hides its lines (header fields, headings and the `## Increments` section), and an
  unclosed comment is a problem. Setext `Increments` headings are not modelled.
- **Review (workflow-reviewer, read-only, 2026-10-21):** no Critical or High finding. Applied: HTML
  comments (above); a heading close to the form (any case, any level, `## Increment`) is a problem and
  not silence; a link at `.workbench` is not a project; a valid name longer than 120 characters is
  judged whole and cut only for display; reaching the findings bound says which plans were not
  looked at and keeps that line when others are dropped; a status must be followed by a space or
  punctuation, and a `none` reason needs a letter or digit; the tests now pin the header-field guards,
  a byte-identical `.git/index`, and more write calls absent from the source. Not changed, by
  decision: a folder named `*.md` in `docs/plans/` is not a plan and is not reported (the installer's
  checks do the same). The reviewer could run only the test file, so the hostile inputs are covered by
  the tests and by the security pass in increment G.
- Run as a program from a directory holding `json.py`, `os.py` and `re.py`, it imports none of them.
- Only `check` exists; `plans` and `report` are increment C.

### Increment C — `plans` and `report` (2026-10-21)

The helper gains `plans` and `report`; `tests/test_codework_reports.py` (40 tests) covers both and
`tests/test_codework_helper.py` is adjusted for two changed messages. Full suite: 1986 tests, 108
skipped, passing with `-W error`. The skips are the stale shipped approvals (see B).

- **Output.** `plans` prints `<name>: <status>` for each plan that is Proposed, Approved or In
  Progress, in name order. `report` prints `complete <roadmap>#<id>` for each candidate that a
  Completed plan names, sorted, then `unresolved <plan> names <ref>: no such roadmap|candidate` in
  plan order. Both write only to standard output, and `problem:` lines on standard error with exit 1
  when something could not be read (a link, a bound, an unclosed fence). Unresolved references are
  information and exit 0. With no `docs/roadmaps/` (or no readable one), `report` prints nothing and
  succeeds, even if plans name candidates; a roadmap folder that cannot be listed is a problem and
  produces no `unresolved` lines, because nothing was looked at.
- **One reader.** The folder reading that `check` did is now `collect`, used by all three, so the
  file, byte, size and link rules are the same. Moving the size notice there means it is also given by
  `plans` and `report`. The `not looked at` message now says "files" and not "plans", because roadmaps
  are read too. The bounds of `report` are shared between roadmaps and plans.
- **Facts a plan states.** The status is the first `Status:` line in the header (words followed by a
  note count: `Approved (by the owner)`; `Approvedish` and lowercase do not). The candidate is the
  one `Candidate:` line when exactly one is present and it has the form `<slug>#<slug>`; `none` and a
  second line name nothing (`check` reports those). IDs are exact: a different case never matches.
- **Candidates as `doccheck` reads them.** `roadmap_candidates` follows `doccheck._candidates`: the
  `###` headings under `## Candidates`, with decorated, entity-written and setext headings, and a
  five-text corpus test agrees with it. One known difference: the helper hides a heading inside an HTML
  comment and `doccheck` does not, so the helper may report fewer candidates, never more. A dropped
  candidate stays in the file and so stays resolvable. The same ID in two roadmaps is two candidates.
- **Real data.** Run on a scratch copy of this repository's `docs/`: `check` found no problems in 11
  plans; `plans` listed this plan; `report` listed nine candidates complete, matching the plans. The
  unfinished-write-recovery plan has `Candidate: none`, so it names nothing.
- **Found while testing:** reaching the candidate cap returned before the generator finished, so the
  "fence never closed" state was missing and the run crashed with a `KeyError`; the scan now carries
  on without recording more and says what was cut.
- **Review (workflow-reviewer, read-only, 2026-10-21):** no Critical or High finding; it could run
  only the two test files. Applied: (Medium) the rest of the line that closes an HTML comment, and the
  whole of a one-line comment, is hidden, as a renderer reads it, so `--> ### forged` is not a
  candidate and `--> Status: Approved` is not a field (this also corrects the claim above that the
  helper never reports more candidates than `doccheck`: `doccheck` has no comment handling at all, so
  it reads a heading inside a comment and the helper does not, but the forged-heading case went the
  other way until now); (Low) `report` makes no `unresolved` claim when any roadmap was not read in
  full (a link, a bound, an unclosed fence), and keeps its `complete` lines; (Low) `plans` and
  `report` give a problem, and exit 1, for a plan whose status could not be found because a fence or
  comment was never closed. Not changed, by decision: a Completed plan with a bad name or a malformed
  `Candidate:` is counted by `plans` and ignored by `report`; `check` reports it. The new tests were
  not run against the old code to see them fail. The hostile-input experiments the reviewer could not
  run are for the security pass in increment G.
- `html` joins the helper's standard-library imports (entity decoding, as `doccheck` does).

### Increment D — the module, its blocks and its skill (2026-10-21)

`packages/workbench/code-work/` is now a module: `module.json` (type `process`, provides `plans`,
requires `specs`, `roadmaps` and `decisions`, writes `docs/plans/README.md`, ships
`helper/code-work`, fills `docs-index` and `policy`), the README for `docs/plans/`, the two blocks,
and the `draft-plan` skill with its `template.md`. `package.json` lists `claude`, `code-work`,
`groundwork`. `tests/test_codework_module.py` (27 tests) covers the declaration, README, blocks, skill
and an install and upgrade against a copy of the package released in a temporary distribution. Full
suite: 2013 tests, 108 skipped, passing with `-W error`. The skips are still the stale shipped
approvals; they end when the owner runs `release-approvals` in G. Two existing tests that listed the
package's modules (`test_claude_module`, `test_groundwork_module`) now expect `code-work` too.

- **README.** The repository's own plans README, made tool-neutral and without this repository's
  specifics: names, content, increments and labels, approval and revision, completion. It says the
  increment headings sit under `## Increments`, which is how the check counts them.
- **Policy block (Decision 5).** Six rules in eleven lines: others' plans are untrusted until acknowledged; the
  roadmap-to-plan-to-increment path with one reviewed local commit per increment; approval is the
  owner's explicit statement and a `Status:` line is never one; a later edit needs new approval; run
  the plan check before asking; report only verification that was run. It says nothing about
  recorded approval, checkpoints, loop caps, push, compaction or attribution; a test pins that.
- **Skill.** Reading, searching and editing, plus one command, `wb code-work check`, which does not
  exist until E; a test allows exactly that string, and no other `wb`, `launch`, `pin` or `git`. The skill
  instructs no other command; whether it can run one depends on harness permissions, not on the skill.
  It stops at `Proposed` and asks the owner.
- **Review (workflow-reviewer, read-only, 2026-10-21):** no Critical or High finding. Applied: (Medium)
  the README and skill now state the 26-increment hard limit; (Medium) the "no command" claim is
  reworded as above and the brittle `pin`/`commit ` substring bans became a word-boundary check on
  `pin` and `launch`; (Low) the skill and README say `Created:` is the date in the file name, which the
  check enforces; (Low) the policy-block size is stated correctly. Not changed: the skill's required
  `wb code-work check` step fails until E lands, which is accepted because D and E are one release.
- **A stray file.** A `__pycache__` in `helper/`, left by a helper run without `-B` and ignored by
  git, made the package fail verification (`unaccounted-file`) because the package tree covers it. It
  is not in a clone; the owner approved deleting it and it was removed with `claude-workflow remove`.
  Any run that imports the helper by path needs `-B`; the real-package tests fail loudly if not.
- **Not exercised.** The Claude clone's skill was checked through `harnessplan.translate` and an
  install into a scratch directory, not in a live Claude session. The first-party status of the new
  module needs the real release (G).

### Increment E — `wb code-work` (2026-10-21)

`workbench/dispatch.py` (new) and a route in `workbench/cli.py` add `wb code-work <subcommand>
[arguments]`. `tests/test_dispatch.py` has 25 tests. `rules.AGENT_SAFE` now lists `code-work`, which
`test_permissions` requires of any routed command. Full suite: 2038 tests, 108 skipped, passing with
`-W error`; the skips are the stale shipped approvals.

- **Flow.** Only `check`, `plans` and `report` are accepted; anything else, or nothing, prints the
  usage line and exits 2 before the store is opened or any project is looked for. The project is the nearest directory at or
  above the working directory (at most 64 levels) with a `.git` directory, a real `.workbench`
  directory and a regular `.workbench/manifest.json`, found with `lstat` only and no git. Its ID is
  derived from the manifest's seed by the existing parser. The pin named `code-work` is looked up, and
  the launcher runs it. Everything after the subcommand is passed through unchanged; the command line
  is not parsed as options, so `--`, `-n`, `--help` and an empty argument reach the helper. The shipped helper takes no
  arguments and refuses any, so for the real helper this is the helper's refusal; the usage text
  therefore shows none.
- **Results.** The helper's exit code is returned. Not inside a project, a manifest that does not parse,
  no pin, an edited helper, or a launcher refusal exit 1 with a `refused:` line and run nothing. With
  no pin the message says the `code-work` helper is not pinned, that the owner pins it with `pin` (or
  `acknowledge` after a change), and that nothing was run. Text taken from the filesystem is cleaned
  before it is printed.
- **Refused as a project:** a forged manifest with no `.git`; a `.git` file, as in a linked worktree
  (the helper refuses it too, so a worktree is not supported yet); a link at `.workbench` or at the
  manifest; a start directory deeper than the search limit.
- **Permissions.** `code-work` is classified agent-safe, so the Claude module's rendered deny and ask
  lists are unchanged; a test checks that no rule mentions it.
- **Not exercised.** A successful run through the real command line (`cli.main` tests cover routing and
  refusals only, because a successful helper writes to the process's standard output); the real helper
  through this dispatch is for the end-to-end tests in G. The project ID is read from a manifest that a
  hostile repository could forge, but a pin applies only to the exact bytes the owner pinned for that
  ID, so a forged ID can at most run a helper the owner already pinned.
- **Found while testing:** a test helper that logged to its working directory wrote a stray `ran.log`
  into the repository root, because the launcher does not change directory. The log now goes to a
  temporary directory and the stray file was removed with the owner's approval.
- **Review (workflow-reviewer, read-only, 2026-10-21):** no Critical or High finding. Applied: (Medium) a
  working directory that cannot be read (`os.getcwd` raising) is a `refused:` line and not a traceback;
  (Medium) the usage text no longer advertises arguments the shipped helper rejects, and the Result
  says so; (Low) the usage check happens before the store is opened, as claimed; (Low) the missing-pin
  test is a membership check on the loaded pins and no longer matches message text; (Low) tests
  strengthened: the usage test proves no search is made, the escape test proves the refusal came from
  the start-path branch, and the depth limit is pinned at 64 levels searched and 65 refused. Wording:
  the dispatch writes nothing of its own, but the launcher keeps a transient copy of the helper in the
  guarded store while it runs, and `bin/wb` is written when missing. Agreed with the reviewer: the
  dispatch and the helper find the same root by the same rules and the same working directory (a
  rename of an ancestor between the two is the only way they could differ, and the pin bounds what
  runs). Left for G: a fake helper through the real `cli.main` with hostile arguments, a deleted or
  renamed working directory under a running process, a damaged or oversized pins file through the
  command line, bind mounts and case-insensitive layouts, and the real helper through the dispatch.
