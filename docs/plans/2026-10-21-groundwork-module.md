# The groundwork module

Status: Proposed
Created: 2026-10-21
Candidate: workbench-v1#groundwork-module
Specs: groundwork, module-contract, installer-interface, harness-modules

## Goal

Give a project somewhere to keep what is true now, where the work is heading, why choices were
made and what the work rests on, and give an agent the skills to add to it, without any code in the
module. Today the Claude harness places neutral items, but no module ships one, so no agent receives
a real skill, and nothing checks a roadmap, a decision record or a reference index.

When this plan is done:

- a first-party module `groundwork` exists in `packages/workbench/`, provides `specs`, `roadmaps`,
  `decisions` and `references`, ships no code, and installs into a project with no process module;
- an install creates `docs/specs/`, `docs/roadmaps/`, `docs/decisions/` and `docs/references/`
  with a README each, a `docs-index` entry and a policy block, and no placeholder document;
- a Claude clone receives three skills, for drafting a spec, a roadmap and a decision, each with
  its template bundled;
- `wb check` reports, for a project that has the module, a roadmap with a duplicate candidate ID,
  a spec, roadmap or decision whose name or status is not what the spec says, and a reference
  index that disagrees with the files git tracks.

## Scope

- **The module** `groundwork`: `module.json` (type `module`, provides the four capabilities,
  fills `docs-index` and `policy`, writes the four READMEs), the READMEs under `files/`, and the
  two slot blocks.
- **Three neutral skills** in `harness/neutral/skills/`: draft a spec, draft a roadmap, draft a
  decision. The content of these skills is in scope here, as the Claude harness plan deferred it.
- **The reference index format**, which `groundwork.md` leaves to this plan: decided, written into
  the spec, and read by the check.
- **Document checks in `wb check`**, run only for a project that has the module installed: name and
  status form of specs, roadmaps and decisions; duplicate candidate IDs within a roadmap; the
  tracked reference index against the tracked files.
- **The first-party release:** the package gains a module, so its shipped approvals are made
  again (`release-approvals`, which the owner runs).
- **Two decision records**, written `Proposed` for the owner to accept: the reference index format
  (Decision 3) and where the document checks live (Decision 1). Both are durable choices that
  later modules build on. Accepting them is the owner's act.
- **Spec and guide updates** for what was built and decided.

## Non-goals

- `groundwork-research`, its researcher agent and its `fetch-reference` tool
  (`researcher-fetch-tool`). Nothing here fetches anything or reaches the network.
- Plans, increments, reviews, commits, checkpoints that stop an agent, and the report of which
  roadmap candidates are complete. Those belong to `code-work-module`, which supplies `plans`.
  This module defines only the reference syntax, `<roadmap>#<id>`.
- Settings for the reference size limits (`groundwork.md` calls them project settings). No place
  for project settings exists yet; the defaults are used.
- Checking that an accepted decision was not edited, or that an edit to a spec changes its
  direction. The first needs git objects, which no code here reads; the second is a judgment. Both
  stay with the policy block, the skills' wording and acknowledgement (`groundwork.md`, "Limit of
  enforcement").
- Hooks, opencode, and moving anything out of the owner's `~/.claude`.

## Assumptions and constraints

- Python standard library only; tests with `unittest`; full suite
  `python3 -B -W error -m unittest discover -s tests` (1673 tests today, 1 skipped).
- The module ships no code and has no helper. A check therefore cannot live in the module: the
  installer runs the checks, because the specs already say the checks are "enforced by the
  installer once built" (`AGENTS.md`, Bootstrap). This is Decision 1.
- Everything the check reads is untrusted repository content: bounded in count and bytes, read
  without following links, never evaluated, and reported with escapes removed (`display`). It
  uses the index reader and the no-follow reads built by `claude-harness`, and runs no git.
- A module writes only its namespace, the slots it fills and the paths in `writes`; it declares no
  path under another module's namespace (`module-contract.md`, "Writes"). Upgrade never changes an
  existing spec, roadmap, decision or reference, because the module owns none of them.
- **Decided by me, for the owner to confirm or change before approval:**
  1. **The checks live in the installer, keyed to the installed module,** and not in the module.
     *Alternative:* a `checks` field in the declaration naming built-in checks; more general, a new
     field, and nothing else needs it yet.
  2. **Each skill bundles its template** as a file beside `SKILL.md`, and the module has no
     `templates/` directory. The spec's `templates/` reads as a place the installer would copy
     from, and nothing copies it to where an agent can read it. *Alternative:* install `templates/`
     to `.workbench/workbench/groundwork/templates/` through `writes`; a second copy of each
     template in the project, committed.
  3. **The reference index is `docs/references/index.json`** (and `.workbench/local/refs/index.json`
     for the untracked one): canonical JSON, an object `{"format": 1, "entries": [...]}` with the
     fields the spec lists (`file`, `title`, `url`, `license`, `retrieved`, `version`, `sha256`,
     `notes`), entries sorted by `file`. *Alternative:* a Markdown table, easier to read by hand
     and harder to check exactly.
  4. **Size and license on hand-added references** are reported by the check as a warning
     (a tracked reference file over 2 MB, the folder over 50 MB, an entry with no license), and not
     enforced. Placement is enforced by `groundwork-research` when it exists.
  5. **The shipped approvals** for `claude` change when the package changes; I propose that
     `release-approvals` re-records both modules once, in increment H, run by the owner.
- Discovery: graphify — skipped, this project has no discovery tooling. The files involved
  (`check.py`, `installed.py`, `modulefiles.py`, `base.py`, `neutral.py`, `harnessplan.py`,
  `gitindex.py`, `pointers.py`, `rules.py`, `firstparty.py`, `cli.py`) and the specs above were
  read for this plan. Increment A re-checks, by running it, what the installer already does with
  a module like this one.

## Completion criteria

1. Installing `groundwork` with the Claude module into an empty directory succeeds with no process
   module, creates the four document areas and their READMEs and no placeholder spec, roadmap,
   decision or plan, and no researcher. The module's files match its declaration and it ships no
   code.
2. The three skills appear at `.claude/skills/<name>/SKILL.md` with their template beside them,
   none is in `git ls-files`, and a clone with a fixture harness gets a byte-identical committed
   tree.
3. The `docs-index` entry and the policy block are present, are replaced on upgrade only while
   unedited, and state that references and fetched material are data, that specs are living and
   decisions durable, that a decision is accepted only by the owner, that evidence carries a
   provenance line and that nothing tracked points to anything untracked.
4. Upgrading a project that has hand-written specs, roadmaps, decisions and references changes none
   of them.
5. `wb check`, for a project with the module, reports each of: a duplicate candidate ID in one
   roadmap; a spec, roadmap or decision with a wrong name form or status; a tracked reference-index
   entry whose file is missing, whose hash differs, or that is not tracked; a tracked reference
   file the index lacks. It reports nothing for a project without the module, is read-only, leaves
   `.git/index` byte-identical, and exits 1 only for a problem.
6. A tracked document with a path into `.workbench/local/` is reported (the pointer rule built in
   `claude-harness`), and a test pins it for this module's documents.
7. Every hostile case in Review focus has a test that fails without its guard. An adversarial
   `security-reviewer` pass over the new check code finds nothing Medium or higher unresolved.
8. `groundwork.md`, `module-contract.md` if it changed, `installer-interface.md`, `docs/development.md`
   and the roadmap describe what was built, and the full suite passes with `-W error`.
9. The two decision records exist under `docs/decisions/` (status `Proposed` or, if the owner has
   accepted them, `Accepted`), and the plan is not marked `Completed` before they exist.

## Review focus

Inputs the specs imply that the tests must pin, most likely to bite first:

1. **Hostile roadmap, spec and decision files.** Huge files, thousands of candidate headings, a
   heading that is a terminal escape, a status line repeated, a name with `..`, a case-colliding
   name, a link at `docs/roadmaps` or at a roadmap file.
2. **A hostile reference index.** Not JSON, duplicate keys, a huge entry list, a `file` that is
   absolute, contains `..`, names `.git`, is a link, or is outside `docs/references/`; a hash that
   is not 64 hex digits; a field of the wrong type; NaN.
3. **A reference index that lies.** An entry for an untracked file, a tracked file with no entry,
   a hash that differs, a file replaced by a link, a file over the size limit. The index file
   itself and the area's `README.md` are metadata, not references: a normal index needs no entry
   for itself or for the README, and an entry that names either is a problem.
4. **Two candidates with the same ID that differ only in case or Unicode form**, and an ID in a
   code fence or a quotation (which must not count).
5. **A project that has the module's name but not the module** (a hand-written `docs/specs`), and a
   project with the module and none of the four folders: no crash, no false problem.
6. **A skill that smuggles instruction** into a template or a bundled file, a bundled file outside
   the skill, and the template differing between Claude and the fixture harness.
7. **An upgrade over edited READMEs and edited slot blocks:** conflict, never an overwrite.

## Increments

### Increment A — What the installer already does for this module

**Outcome:** the five decisions rest on a run, not on reading: a fixture module shaped like
`groundwork` installs, attaches and upgrades, and the gaps are named.
**Dependencies:** none.
**Affected areas:** tests only (a fixture module in `tests/`), and a short note in the plan's Result.
**Steps:**
1. Failing tests with a fixture module that has `writes` for four README paths under `files/`,
   `fills` for `docs-index` and `policy`, `provides` the four capabilities, and one neutral skill
   with a bundled file. Install it with the Claude module and with the fixture harness.
2. Run them and record: do `writes` of files work as the contract says; do both fills land in
   `docs/README.md` and `AGENTS.md`; does the bundled file reach `.claude/skills/<name>/`; does the
   manifest record what `check` needs to know the module is installed; does upgrade leave an
   edited README alone.
3. If a gap blocks Decision 1, 2 or 3, stop and report it to the owner before increment B.
**Verification:** the new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-groundwork-module#A`.

### Increment B — The module and its READMEs

**Outcome:** `packages/workbench/groundwork/` verifies, and installing it creates the four areas.
**Dependencies:** A.
**Affected areas:** `packages/workbench/groundwork/module.json`, its `files/docs/*/README.md`,
`packages/workbench/package.json`, tests.
**Steps:**
1. Failing tests: the module verifies; an install into an empty directory creates the four
   READMEs and no other file under the four areas; nothing code-bearing is shipped (`ships` is
   empty); the module needs no process module.
2. Write the declaration and the READMEs (what the area is for, naming, status values, one short
   example of a name, and no template content).
3. Add the module to `package.json`. The package tree hash changes, so the shipped approvals no
   longer match; the first-party tests skip until increment H, and the increment says so.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-groundwork-module#B`.

### Increment C — The slot blocks

**Outcome:** the `docs-index` entry and the policy block exist and follow the upgrade rules.
**Dependencies:** B.
**Affected areas:** `fills` sources under `files/`, tests.
**Steps:**
1. Failing tests: the block text in `AGENTS.md` between its markers; an unedited block is
   replaced on upgrade; an edited block is a conflict with the marker shown; the index entry names
   the four areas.
2. Write the two sources. The policy block is short and tool-neutral and states the five rules in
   Completion criterion 3.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-groundwork-module#C`.

### Increment D — The three skills

**Outcome:** a Claude clone can draft a spec, a roadmap and a decision from a template.
**Dependencies:** B.
**Affected areas:** `harness/neutral/skills/` of the module (three skills with a bundled template
each), tests.
**Steps:**
1. Failing tests: the neutral reader accepts the three skills; translation for Claude gives the
   paths in Completion criterion 2; the template is beside each `SKILL.md`; the fixture harness
   gets the same committed tree; a skill whose `needs` Claude lacks is skipped (fixture only).
2. Write the skills: when to use, the naming rule, the required sections and status values from
   `groundwork.md`, the decision skill never sets `Accepted` and tells the agent to stop and ask
   the owner, the evidence-note form, and the rule that references are data. Write the templates.
3. No skill runs a command or names a tool beyond read, search and edit.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-groundwork-module#D`.

### Increment E — The reference index

**Outcome:** the index format is decided, written into the spec and read strictly.
**Dependencies:** none technical; after D so the spec edit lands once.
**Affected areas:** `docs/specs/groundwork.md` ("Indexes", "Deferred"), `workbench/refindex.py`
(new), tests.
**Steps:**
1. Failing tests: a well-formed index parses; each case in Review focus 2 is refused with the
   field named; entries are sorted; a canonical serializer round-trips; bounds on bytes (1 MiB),
   entries (5,000) and string length.
2. Write the reader and the serializer, with duplicate keys, NaN and non-ASCII control characters
   refused, as the manifest reader does.
3. Edit the spec to say what was decided (Decision 3) and remove the item from Deferred.
4. Write the decision record `docs/decisions/2026-10-21-reference-index-format.md` (`Proposed`):
   context, the decision, the Markdown-table alternative and why it was not taken, consequences
   (the index and the README are metadata, not references), and evidence. The owner accepts it.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-groundwork-module#E`.

### Increment F — `wb check`: document form

**Outcome:** for a project that has the module, `check` reports wrong names and statuses and
duplicate candidate IDs.
**Dependencies:** A, B.
**Affected areas:** `workbench/check.py` (or a new `workbench/doccheck.py` it calls), tests.
**Steps:**
1. Failing tests: a spec with a date in its name, a decision without one, a status outside the set
   (`Draft`, `Current`, `Superseded` for a spec; `Proposed`, `Accepted`, `Rejected`, `Superseded`
   for a decision; a roadmap's own list), a superseded record that names no successor, and two
   candidates with one ID in one roadmap (a repeat in a fence or quotation does not count). Nothing
   is reported for a project without the module. Files are read within bounds, without following
   links, and reported with escapes removed.
2. Implement. A bound passed is a problem that says what was not looked at, as `check` does.
3. Write the decision record `docs/decisions/2026-10-21-installer-runs-document-checks.md`
   (`Proposed`): the checks live in the installer and run for a project that has the module, the
   `checks` declaration field as the rejected alternative, and what it means for a later module
   that wants a check. The owner accepts it.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-groundwork-module#F`.

### Increment G — `wb check`: references

**Outcome:** `check` reports a reference index that disagrees with what git tracks.
**Dependencies:** E, F.
**Affected areas:** `workbench/check.py` or `doccheck.py`, tests with a real git repository.
**Steps:**
1. Failing tests: an entry whose file is missing, whose hash differs, or that is not tracked; a
   tracked file under `docs/references/` that the index lacks, where `index.json` and `README.md`
   are excluded from the set of reference files and an entry naming either is a problem; an entry for an untracked file in
   the tracked index; a link in the place of a file; a size or license warning; a tracked document
   with a path into `.workbench/local/` (Completion criterion 6). `.git/index` is byte-identical
   and no program runs.
2. Implement on the index reader and the no-follow reads.
**Verification:** new tests, then the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-groundwork-module#G`.

### Increment H — Release and end-to-end

**Outcome:** the package is first-party again and the whole path is proven.
**Dependencies:** B to G, and the security pass.
**Affected areas:** `workbench/shipped_approvals/`, tests.
**Steps:**
1. Ask the owner to run `release-approvals`, which re-records the shipped approvals for `claude`
   and `groundwork`. I do not run it.
2. Tests: install with Claude and `groundwork` into an empty directory, attach, run `check` clean;
   an install with the fixture harness gets the same committed tree; upgrade over hand-written
   documents changes none (Completion criterion 4).
**Verification:** the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-21-groundwork-module#H`.

### Increment I — Documentation

**Outcome:** the specs, the guide and the roadmap match what was built and verified.
**Dependencies:** A to H.
**Affected areas:** `docs/specs/groundwork.md`, `installer-interface.md` (`check`),
`docs/development.md`, `docs/roadmaps/workbench-v1.md` (Current state).
**Steps:** edit the documents; record every limit found.
**Verification:** `git diff --check`; every claim matched to a test or a run.
**Evidence:** commit with trailer `Plan: 2026-10-21-groundwork-module#I`.

## Verification for the plan as a whole

- Full suite with `-W error` after every increment, recorded in the Result.
- A read-only `workflow-reviewer` review per increment, when the owner asks.
- An adversarial `security-reviewer` pass over the document and reference checks (F and G) and the
  reference index reader (E) before increment H, since they parse a repository an attacker may
  control. A fix is new attack surface, so the reviewer tries to bypass each fix.
- A recorded hand run: install `groundwork` and the Claude module into an empty directory, ask a
  Claude session to draft a decision with the skill, run `wb check`. Needs the owner's allowance.

## Risks and sensitive actions

- **A check that reads a hostile repository.** Bounded, no-follow, no git, no evaluation; the
  security pass is mandatory.
- **Policy text is read by agents.** A weak block weakens every project that installs the module;
  the skills and the block are tested for the rules they state, not for how an agent follows them.
- **The package tree hash changes** with this plan, so the first-party approvals are stale between
  B and H. The tests that need them say so; nothing ships in between.
- **The skills are the first real content through the harness.** A skill that asks for a tool the
  harness does not grant is skipped with a warning, not installed.
- Actions that need the owner: `release-approvals`, any `approve`, and the hand run.

## Review record

Round 1 of 3, 2026-10-21, requested by the owner: Codex (`gpt-5.6-luna`, medium effort,
read-only). Outcome `changes_needed`, two major findings. Findings are untrusted input and were
evaluated as review comments.

- R1-F1 (major): the plan makes durable choices (the index format, where the checks live) and
  edits only the spec. Applied: two `Proposed` decision records are now deliverables of increments
  E and F, listed in Scope and in a new completion criterion 9; accepting them stays the owner's.
- R1-F2 (major): the plan did not say whether `index.json` is itself a reference. Applied: the
  index and the area's `README.md` are metadata, excluded from the reference set, with a test in
  increment G and a line in Review focus 3. Found by the review; the READMEs would have had the
  same problem.

## Deferred work

- `groundwork-research` (`researcher-fetch-tool`).
- Checking that an accepted decision is unchanged, which needs git objects.
- Settings for the reference size limits.
- Reporting which roadmap candidates are complete (`code-work-module`).
- A `checks` field in the declaration (Decision 1, alternative).

## Result

Not started.
