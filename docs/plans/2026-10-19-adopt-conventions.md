# Adopt the new document conventions in this repository

Status: Completed
Created: 2026-10-19
Completed: 2026-10-19
Candidate: workbench-v1#adopt-conventions
Specs: groundwork, code-work, repository-boundary

## Goal

This repository's own documents follow the conventions the approved specs define, and
harness files and the old template manifest are kept out of git before the first
commit exists, so every later plan is written, recorded and archived the way the specs
say.

## Scope

- Exclude the per-clone harness files and the old template manifest through
  `.git/info/exclude`, and remove the harness-specific block and the old template
  markers from the tracked `.gitignore`.
- Rewrite `AGENTS.md`, `docs/README.md`, and the plans, decisions, roadmaps and specs
  READMEs to the new conventions: dated plan and decision names, the `Candidate:` and
  `Specs:` lines, candidate slug IDs, derived completion, no fixed `next.md`, several
  active plans, and a statement of which checks the installer will enforce and that the
  owner enforces them in session until then.
- Replace the template placeholders in `README.md`, `docs/architecture.md` and
  `docs/development.md`, so the first commit holds no `REPLACE_WITH_*` text.
- Add a `LICENSE` file with the MIT License, as the owner chose, and name it in the
  README.
- Move this plan to its dated name, rename the first archived plan (`0001-…`) to the
  dated form, and remove the emptied `docs/plans/next.md`.

## Non-goals

- Any code, installer behavior, mechanical check or test. The checks are described, not
  built.
- Moving scratch from `.debug/` to `.workbench/local/debug/`, creating `.workbench/`, or
  generating any file with the installer. Those belong to `base-and-manifests` and
  `self-hosting`.
- Moving `.claude/remote-runner.toml` under `.workbench/`. That is
  `remote-runner-module`.
- Writing the Claude root file's Compact Instructions section. That is `claude-harness`.
- Editing the content of the archived plan `0001-approve-the-workbench-specifications.md`
  (Increment D only renames it and drops the number from its heading), or of any
  accepted decision record.
- Committing, pushing or publishing anything.

## Assumptions and constraints

- The owner is the only developer and approves in session. Hash-bound approval does not
  exist yet, so the `Status:` line of this plan is informational and approval is the
  owner's explicit statement.
- The old conventions govern this plan until it completes, so it is drafted in
  `docs/plans/next.md` and approved the old way. **Three departures are requested;
  approving this plan approves them:**
  1. At completion the plan is archived under its dated name,
     `docs/plans/2026-10-19-adopt-conventions.md`, and not as a numbered file. The
     existing archived plan is renamed once, at the same time, from
     `0001-approve-the-workbench-specifications.md` to
     `2026-10-19-approve-the-workbench-specifications.md`, and its heading loses the
     number. This is a one-time exception to "never renamed": nothing is committed,
     so nothing outside this repository refers to the old name, and afterwards the
     directory has one naming style.
  2. `docs/plans/next.md` is then removed, with the approved removal helper, and no file
     of that name replaces it. Exactly that one path is covered.
  3. `.git/info/exclude` is appended to with the exclude entries below. No other file
     under `.git/` is touched.
- The user's global instructions name `docs/plans/next.md` as the default plan location
  and let repository-owned instructions name another. The rewritten `AGENTS.md` is
  that instruction.
- No commit exists, so no history is rewritten and nothing needs migrating.
- `.debug/` stays the scratch location for this repository during the bootstrap. Moving
  it needs `.workbench/` and a change to the owner's global configuration.
- The documents rewritten here say what the specs say and cite them. They do not copy a
  spec's rules at length.

Discovery: skipped. This is a documents-only plan with an enumerated file list, and the
project has no discovery tooling installed.

## Completion criteria

- `git status --short` shows no harness file (`CLAUDE.md`, `.claude/`), no
  `.template-manifest` and no `.debug/`, and `git check-ignore -v` names
  `.git/info/exclude` for each of them.
- No file that will be committed names a harness's files or directories, outside the
  specs and decision records that describe harnesses.
- No rewritten document refers to `next.md` as the active plan, to numbered plan or
  decision names, or to roadmap candidates by number, and none carries an old template
  slot marker.
- The convention documents state which checks are enforced by the installer once built
  and, until then, by the owner in session.
- No `REPLACE_WITH_*` text remains in files that will be committed.
- `LICENSE` holds the MIT License text with the copyright line
  `Copyright (c) 2026 Robert Ziegler`, and the README names it.
- This plan is archived under its dated name, with status `Completed`, the first
  archived plan has its dated name, no numbered plan file remains, and
  `docs/plans/next.md` no longer exists.
- Nothing has been committed or pushed.

## Increments

### Increment A — Keep harness files and the old manifest out of git

Dependencies: None
Affected areas: `.git/info/exclude`, `.gitignore`

1. Append these entries to `.git/info/exclude`, after the existing `/.debug/` line:
   `/CLAUDE.md`, `/.claude/` and `/.template-manifest`.
2. In `.gitignore`, delete the `# BEGIN harness:claude` block (it holds
   `/.claude/settings.local.json`, which names the harness in a committed file; the
   `/.claude/` exclude covers it) and the `# @module-slot: gitignore` line. Keep every
   other entry.
3. Verify with `git check-ignore -v CLAUDE.md .claude/remote-runner.toml
   .template-manifest .debug` and `git status --short`.

Completion: the four paths are reported as excluded by `.git/info/exclude`, `git status`
lists none of them, and `.gitignore` names no harness and has no slot marker.

### Increment B — Rewrite the convention documents

Dependencies: Increment A
Affected areas: `AGENTS.md`, `docs/README.md`, `docs/plans/README.md`,
`docs/decisions/README.md`, `docs/roadmaps/README.md`, `docs/specs/README.md`

1. `AGENTS.md`: add the specs to the source-of-truth order beside the architecture
   documents; replace the single-`next.md` rule with the dated-plan rule (several plans
   may be active, none is named `next.md`, a plan has `Candidate:` and `Specs:` lines,
   archiving changes its status only); rename "Second opinion" to "Review record"; and
   add a short "Bootstrap" section stating that the workbench's own tooling does not
   exist yet, that approval is the owner's explicit statement in session, that a
   `Status:` line is informational, and that each check the specs define is "enforced
   by the installer once built; until then by the owner in session". The file stays
   tool-neutral and names no harness.
2. `docs/plans/README.md`: describe `YYYY-MM-DD-<topic>.md` names (creation date, never
   renamed), the `Candidate:` and `Specs:` lines, increments (size, labels, `B-A`
   insertion, heading form, citation), statuses, approval and revision, the review
   record, and that active plans are found by listing plans by status. Remove the
   numbered-archive scheme and the archive table, including the row for the first
   archived plan, which Increment D renames. Remove the old `plan-review` block and its
   slot marker.
3. `docs/decisions/README.md`: describe `YYYY-MM-DD-<topic>.md` names with the filename
   stem as the stable ID, the statuses, the rule that an accepted record is superseded
   and never edited, the format (no number in the heading), and that accepting a record
   is the owner's act. Keep the index.
4. `docs/roadmaps/README.md`: describe candidates with slug IDs written
   `<roadmap>#<id>`, an optional suggested order, completion derived from work records,
   dropped candidates kept with a reason, and no promotion into a single `next.md`.
   Replace the format block (`### 1. <title>`) with the slug form the active roadmap uses.
5. `docs/specs/README.md`: describe topic names with no date, the `Status:` values
   (`Draft`, `Current`, `Superseded`) and that a spec is edited in place. Replace the
   CAD example file names with this project's.
6. `docs/README.md`: remove the `next.md` sentence and the `docs-index` slot marker,
   point to the specs for the design, and add a short list of the checks, each marked
   "enforced by the installer once built; until then by the owner in session": the plan
   check (one `Candidate:` line, increment headings, no repeated labels), duplicate
   candidate slugs, the tracked-pointer rule and the tracked reference index.
7. Verify by search: no `next.md`, numbered-name or `@module-slot` text remains in these
   six files.

Completion: the six documents describe one consistent convention that matches the
specs, and the bootstrap statement appears in `AGENTS.md` and `docs/README.md`.

### Increment C — Replace the template placeholders

Dependencies: Increment B
Affected areas: `README.md`, `LICENSE`, `docs/architecture.md`, `docs/development.md`

1. `README.md`: replace the template note, status, quick start and license
   placeholders. State the purpose (a vendor-neutral workbench that creates and
   maintains projects from packages of modules), the status (design stage; specs
   approved; no code), and a documentation list that points to `docs/specs/` and
   `docs/roadmaps/workbench-v1.md`. The license line reads "MIT. See
   [LICENSE](LICENSE)."
   Add `LICENSE` with the standard MIT License text and the copyright line
   `Copyright (c) 2026 Robert Ziegler`, the owner's chosen name. It covers the whole
   repository, documents included.
2. `docs/architecture.md`: replace the empty template sections with a short statement
   that the architecture is specified in `docs/specs/`, linking each spec and the
   accepted decisions, and that no implementation exists.
3. `docs/development.md`: fill the commands table with `not applicable (no code yet)`,
   keep the debug-artifact section, and remove the unused slot marker.
4. Verify that `grep -rn "REPLACE_WITH" README.md docs` finds nothing outside this plan.

Completion: the three files hold no placeholder, and each statement in them is true of
the repository today.

### Increment D — Move the plan to its dated name and verify

Dependencies: Increment C
Affected areas: `docs/plans/next.md`, `docs/plans/2026-10-19-adopt-conventions.md`,
`docs/plans/0001-approve-the-workbench-specifications.md`

1. Complete the Result section of this plan and set its status to `Completed`, with a
   `Completed:` date, once the verification below passes.
2. Create `docs/plans/2026-10-19-adopt-conventions.md` as a copy of the final plan.
3. Rename `docs/plans/0001-approve-the-workbench-specifications.md` to
   `docs/plans/2026-10-19-approve-the-workbench-specifications.md` with `mv`, change its
   first heading from `# 0001: Approve the workbench specifications` to
   `# Approve the workbench specifications`, and change nothing else in it. Then search
   all files that will be committed for the old name and fix any reference.
4. Preview the removal of the old path with `claude-workflow remove docs/plans/next.md`,
   show the preview to the owner, and only then run the identical command with
   `--confirm`. The helper refuses anything else.
5. Run every command in the Verification section.

Completion: both plans have dated names, `docs/plans/next.md` does not exist, and the
verification results are recorded in the Result.

## Verification

- `git check-ignore -v CLAUDE.md .claude/remote-runner.toml .template-manifest .debug`
  names `.git/info/exclude` for all four, and `git status --short` lists none of them.
- `grep -n -i "claude\|opencode" .gitignore AGENTS.md README.md docs/README.md
  docs/plans/README.md docs/decisions/README.md docs/roadmaps/README.md
  docs/specs/README.md docs/architecture.md docs/development.md` finds nothing.
- `grep -rn "next\.md\|@module-slot\|BEGIN module" AGENTS.md README.md docs/README.md
  docs/plans/README.md docs/decisions/README.md docs/roadmaps/README.md
  docs/specs/README.md docs/architecture.md docs/development.md` finds nothing.
- `grep -rn "REPLACE_WITH" README.md docs` finds nothing outside the plan files.
- `head -3 LICENSE` shows "MIT License" and the copyright line, and the README's license
  line links to it.
- `grep -rn "\.debug" docs/specs docs/roadmaps docs/decisions` still finds nothing.
- `ls docs/plans` shows `2026-10-19-approve-the-workbench-specifications.md`,
  `2026-10-19-adopt-conventions.md` and `README.md`, and no `next.md` and no numbered
  file.
- `grep -rn "0001-" AGENTS.md README.md docs` finds nothing outside the two plans'
  own descriptions of the rename.
- `git status --short` shows only the intended documents, and `git log` still shows no
  commit.

## Risks and sensitive actions

- **Removing `docs/plans/next.md` (Increment D).** It is a deletion. The path is the
  empty placeholder left after the plan is copied, the removal helper previews it before
  it runs, and approving this plan covers only that path.
- **Editing `.git/info/exclude` (Increment A).** It is git metadata. The edit appends
  three lines to the file the owner's own debug rule already uses, and changes no
  history or configuration.
- **Excluding `.claude/remote-runner.toml`.** `remote-runner` reads that file from a
  committed revision, so while it is excluded no remote job can be submitted from this
  repository. No profile is active, so nothing is lost today. `remote-runner-module`
  moves the file; if remote jobs are wanted sooner, the owner decides then.
- **Renaming the first archived plan (Increment D).** It is the one exception to
  "never renamed". It is untracked and uncommitted, so no history is lost and nothing
  outside the repository points to the old name. Its content is unchanged except the
  number in its heading.
- **The license** grants rights to the repository's content once it is published. Adding
  the file publishes nothing. The copyright holder is the owner's name, as chosen.
- **Editing `AGENTS.md`** changes repository policy. The edits are the conventions the
  approved specs already state, and the owner reviews them before approving the result.
- No commit, push, publication, dependency installation or secret use is part of this
  plan.

## Review record

Not requested.

## Deferred work

- Moving scratch from `.debug/` to `.workbench/local/debug/`, and the tracked
  `.workbench/.gitignore`: `base-and-manifests`.
- The Claude root file's generated Compact Instructions section: `claude-harness`.
- Moving the remote-runner configuration under `.workbench/`: `remote-runner-module`.
- Agreement between these hand-maintained files and installer output: `self-hosting`.

## Result

Completed 2026-10-19.

- Increment A: `.git/info/exclude` now excludes `/CLAUDE.md`, `/.claude/` and
  `/.template-manifest` besides `/.debug/`. The tracked `.gitignore` no longer names a
  harness and has no slot marker.
- Increment B: `AGENTS.md` and the docs, plans, decisions, roadmaps and specs READMEs
  now describe the new conventions and state that each check is enforced by the
  installer once built, and by the owner in session until then.
- Increment C: the template placeholders are replaced. `LICENSE` holds the MIT text with
  `Copyright (c) 2026 Robert Ziegler`, and the README links to it. Two prose mentions of the
  harness names in the README and architecture file were reworded so the approved
  verification search finds nothing.
- Increment D: this plan is archived under its dated name, the first archived plan was
  renamed to `2026-10-19-approve-the-workbench-specifications.md` with the number
  removed from its heading, and `docs/plans/next.md` was removed with the approved
  removal helper.
- Verification: the four paths are excluded by `.git/info/exclude`; the harness-name,
  old-convention, placeholder and `.debug` searches find nothing; `LICENSE` and the
  README line are right; `git status` shows only the intended documents and `git log`
  shows no commit.
- Remaining: scratch stays at `.debug/` until `base-and-manifests`, the Claude root
  file's Compact Instructions are for `claude-harness`, the remote-runner configuration
  is for `remote-runner-module`, and agreement with installer output is for
  `self-hosting`. Nothing is committed.
