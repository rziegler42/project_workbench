# Global configuration migration: the inventory and the move list

Status: Proposed
Created: 2026-10-25
Candidate: workbench-v1#global-config-migration
Specs: global-config-inventory (new)

## Goal

Complete the first step the roadmap gives `global-config-migration`: a line-by-line comparison of the
owner's global Claude configuration against the specs and modules, so every item has a recorded
disposition and the later moves can be planned one item at a time. When the plan is done, a tracked
document says what was and was not inspected, gives every item found a disposition (move, redesign,
drop or keep global), and lists the moves in an order that never leaves a hard stop, deny rule or
approver absent. No global item is moved by this plan.

## Scope

- Read `~/.claude/agents/`, `~/.claude/skills/`, `~/.claude/hooks/`, `~/.claude/settings.json` and
  `~/.claude/CLAUDE.md` in full, and the helper programs the settings and instructions name
  (`claude-workflow`, `ask-codex`, `remote-runner`, `graphify`, `mempalace` and the others on the owner's `PATH`
  that those files call).
- Compare each item with the specs, the shipped modules and the plans that list the global items they replace.
- Write one new spec, `docs/specs/global-config-inventory.md` (my call: the roadmap asks for the record to be
  tracked; a spec is edited in place, so the dispositions can be updated as items move). It holds what was
  inspected, what was not, and a disposition for every item.
- Propose dispositions for the items the roadmap names: the superpowers dependencies (the agents' `skills:` lists, the
  routing in `CLAUDE.md`, the session-start rule, the gaps in `superpowers-ports.md`) and whether the settings
  file's own path is denied for edits (`harness-modules.md`, "As built, and its limits"). These are proposals in the
  spec. A durable choice among them is drafted as a `Proposed` decision only if the owner asks, and is accepted by
  the owner alone; this plan does not settle one.
- Draft the move list: for each `move` or `redesign` item, the test or recorded run that must show a project
  behaves the same without the global copy, and the owner step that removes it.

## Non-goals

- Editing `~/.claude`, the owner's `allow` rules, or any machine-level setting. The agent does not write the
  user level (`2026-10-24-project-guarantees-a-floor`); removals are the owner's, in a terminal.
- Moving any item. Each move is its own later plan, after this record exists.
- Building `action-review-engine`, `verilog-module` or `cad-modules`; this plan records them as blockers for the
  moves they gate.
- Changing the installer or any shipped module. If the comparison finds a defect, it is recorded as a finding and
  planned separately.
- Retiring the `claude_global_config` or `claude_project_template` repositories.

## Assumptions and constraints

- The promotion trigger in the roadmap is not fully met: `action-review-engine` is not complete and has no plan.
  This plan is read-only with respect to everything but one new spec, so it does not depend on that engine; the
  owner decides whether to begin before it. The moves that depend on it wait.
- `~/.claude/settings.json` may hold host names, paths or tokens. The spec records item names, counts and
  dispositions, never values. A value that looks like a credential is reported to the owner in the session and is
  not written to any tracked file.
- Reading the user level is the owner's request for this work. The installer itself still never reads it.
- The global files change while the work runs (this session's tools write there). Each increment records the date
  and the hash of each file it inspected at its start and again at its end. A difference is reported in the spec
  and the Result as a change by something else, with the file and the times, and the affected part of the
  inventory is re-read. A difference does not fail the plan; a write by this work would.
- The first-pass inventory behind the seven earlier candidates is a starting point and is not trusted as complete.
- The global files are untracked and have no source URL. Repository policy cites untracked content by source URL,
  retrieval date and content hash, never by path. The spec therefore identifies each global file by its role
  (for example "the owner's user-level settings file"), the retrieval date and the content hash, and states that
  the source is owner-local and has no URL. It writes no path to a global file. Items inside a file (an agent, a
  skill, a rule, a section) are named by their own name or heading, which is not a path. Anything that could
  not be given this form is left out of the tracked spec and reported to the owner in the session.

## Completion criteria

1. `docs/specs/global-config-inventory.md` exists, lists every file under the inspected global directories, every
   top-level key of `settings.json`, every individual `allow`, `ask` and `deny` rule entry and every hook and
   plugin, and every section and paragraph group of `CLAUDE.md`, each with a disposition and a reason. A rule
   entry may share a line only with entries that have the same disposition and reason, and the spec says so;
   group counts are summaries and not dispositions.
2. The spec states what was not inspected and why, and identifies each global file read by role, retrieval date
   and content hash with an "owner-local, no URL" note, and contains no path to a global file.
3. Each superpowers dependency and the settings-path question the roadmap names has a proposed disposition, and
   the spec says that none is a settled decision.
4. The move list names, for every `move` or `redesign` item, the test or recorded run that gates it, the plan that
   will carry it, and its blockers.
5. `wb check`, `doccheck` and `refcheck` pass; no secret value appears in any tracked file; this work wrote
   nothing under `~/.claude`.

## Increments

### Increment A — Inventory agents, skills, hooks and helpers

**Outcome:** the spec exists with the part for the files under `~/.claude/agents/`, `skills/`, `hooks/` and the
helper programs, each with a disposition and the module, spec or plan that already covers it (or "no cover").
**Dependencies:** none.
**Affected areas:** `docs/specs/global-config-inventory.md` (new), `docs/specs/README.md` (index entry).
**Steps:**
1. List and hash every file under the four locations, and read each in full. Identify each in the spec by role,
   retrieval date and hash, not by path.
2. For each item, find what the workbench already provides (module, skill, agent, spec, plan) by search, and quote
   the plan's own "global items this plan will let `global-config-migration` retire" lists.
3. Record a disposition and reason per item; mark an item `no cover` where the workbench has none.
4. Record what was not read and why.
**Verification:** `doccheck` and `refcheck`; every file listed by the shell appears in the spec once; `git diff --check`.
**Evidence:** one local commit with the trailer `Plan: 2026-10-25-global-config-migration#A`.

### Increment B — Inventory `settings.json`

**Outcome:** every top-level key, every `allow`, `ask` and `deny` rule group, each hook and each enabled plugin has
a disposition, and the permission rules are compared with what the Claude harness module renders.
**Dependencies:** A.
**Affected areas:** `docs/specs/global-config-inventory.md`.
**Steps:**
1. Read the file in full; record keys by name and every rule entry individually, never values that could be
   credentials or host details.
2. Compare each `deny` and `ask` rule entry with the rendered project rules and with `safe-git`, `code-work` and
   `remote-runner`; give each entry its own disposition (entries with the same disposition and reason may share a
   line), marking those the project now supplies as `move` and the rest as `keep global`.
3. Record each `allow` rule entry as `keep global` (the workbench never writes `allow`), with the reason.
4. Record each hook (event, the program it runs, the project hook that replaces it, if any) and each plugin.
5. Answer the settings-path-denied question from `harness-modules.md` by reading the rendered rules and, if a
   practical test exists, naming it for the move list.
**Verification:** `doccheck`, `refcheck`, `git diff --check`; a search of the diff for the owner's host names and
for token-like strings finds none.
**Evidence:** one local commit with the trailer `Plan: 2026-10-25-global-config-migration#B`.

### Increment C — Inventory `CLAUDE.md` and the superpowers dependencies

**Outcome:** every section of the global instruction file has a disposition, and the superpowers dependencies have
proposed dispositions.
**Dependencies:** A, B.
**Affected areas:** `docs/specs/global-config-inventory.md`.
**Steps:**
1. Split the file into paragraph groups and give each a disposition: a module policy block or skill that carries
   it, a rule the installer enforces in code, an instruction that stays global, or a drop.
2. Propose a disposition (not a settled decision) for the three agents' `skills:` lists that name plugin skills, the routing section, the session-start rule
   and the gaps in `superpowers-ports.md` (parallel agents, writing skills, a fresh implementer per increment).
3. Where text in this file contradicts a module (for example the retired single-plan file, the mirror rule and the
   old template), record it as a finding with the file it conflicts with.
**Verification:** `doccheck`, `refcheck`, `git diff --check`; every heading of the file appears in the spec.
**Evidence:** one local commit with the trailer `Plan: 2026-10-25-global-config-migration#C`.

### Increment D — The move list and the record of the result

**Outcome:** the spec ends with the ordered move list, and the roadmap candidate's remaining work is stated.
**Dependencies:** A, B, C.
**Affected areas:** `docs/specs/global-config-inventory.md`; this plan's Result.
**Steps:**
1. Group the `move` and `redesign` items into moves of one item (or one tightly coupled set), in an order that never
   leaves a hard stop, deny rule or approver absent in between.
2. For each move, state the gating test or recorded run, the blocker (including `action-review-engine`,
   `verilog-module`, `cad-modules`), and that the owner performs the removal.
3. List the findings that need their own plan (defects, contradictions).
4. Fill the plan's Result with what was inspected, what was not, and the counts per disposition.
**Verification:** `doccheck`, `refcheck`, `wb check`, `git diff --check`; every item of A to C appears in exactly one
move or in a `keep global` or `drop` line.
**Evidence:** one local commit with the trailer `Plan: 2026-10-25-global-config-migration#D`.

## Verification for the plan as a whole

`wb check`, `doccheck`, `refcheck` and `git diff --check`; a count showing every inspected global item has one
disposition; a search of tracked files for credential-like strings and host names; the start and end hashes of each
increment compared, with every difference reported as a change by something else (this work runs no command that
writes under `~/.claude`). The full suite is not needed: no code changes.

## Risks and sensitive actions

- **A secret or host detail copied into a tracked file.** Mitigated by the names-only rule and the diff search; any
  such value found is reported in the session only.
- **A stale inventory.** The global files are live. Mitigated by recorded hashes and dates.
- **A wrong disposition leads to a later removal that drops a guard.** Mitigated by making every move gated by a test
  or recorded run and by the floor decision; this plan removes nothing.
- **Reading outside the repository.** Read-only, limited to the files named in Scope, at the owner's request.

## Review record

Asked for by the owner on 2026-10-25, through the review engine (bridge `ask-codex`, model `gpt-5.6-terra`, effort
medium, bound 3 rounds). Findings are advice and were judged by the author; the review is not an approval.

- **Round 1** (`changes_needed`, three major findings, all applied):
  - R1-F1: settings rules were inventoried by group. Now one disposition per rule entry.
  - R1-F2: the plan appeared to settle durable choices without a decision record. Now it only proposes
    dispositions and leaves any decision record to the owner.
  - R1-F3: "`~/.claude` unchanged" conflicted with outside changes. Now "this work wrote nothing there", with
    start and end hashes per increment.
- **Round 2** (`changes_needed`, one major and one minor finding, both applied):
  - R2-F1: the spec would cite untracked global files by path and hash, against the provenance rule. Now it
    identifies them by role, retrieval date and hash, notes the source is owner-local, and writes no path.
  - R2-F2: this section was empty. Now it records the rounds.

## Deferred work

- Each move out of `~/.claude`, one plan per item or coupled set.
- Any decision record for a durable choice the inventory proposes, which the owner asks for and accepts.
- `action-review-engine`, `verilog-module` and `cad-modules`, which gate some moves.
- Archiving `claude_global_config` and `claude_project_template` once the workbench runs without them.

## Result

### Increment A (done, uncommitted until the owner says commit)

- Wrote `docs/specs/global-config-inventory.md` (Draft) and its index row in `docs/specs/README.md`. It lists 30 global
  files with their SHA-256 hashes: 5 agents, 2 hook programs, 11 approver data files, 4 authored skills with 3 reference
  files, the synced bundle's manifest and 4 helper programs, each with one disposition and a reason. Counts of dispositions
  are given with the move list in increment D.
- Seven findings (F-A1 to F-A7). The one that shapes the move order: the approver matches only the global helpers' spellings,
  so a helper moved into a project is no longer reviewed unless the approver's rules change first.
- Verification as run: `doccheck`, `refcheck` and `git diff --check` exit 0. `wb check` reports one problem, the README row
  pointing at the not yet tracked spec; it clears once the spec is committed. The 30 hashes were re-taken at the end and all
  match the start values, so nothing changed at the user level and this work wrote nothing there. A search of the spec found
  no global path, host name, token or credential.
- Step 1 was met only in part, as the spec states: the three large helper programs (`ask-codex`, `claude-workflow`,
  `remote-runner`) were hashed and compared with the shipped helpers by role and size, not read line by line;
  `opencode-workflow` was read for 60 lines and the approver rubric by headings; the synced bundle is recorded as a group
  (manifest hash only, 227 other files not hashed).
- Review: one round with the `reviewer` agent (read and search only). Blocking: the skill count (five named, four authored)
  was wrong; fixed. Not blocking, applied: the rubric count (four remote-runner sections, not three); three compound
  dispositions reduced to one; the security-reviewer blocker reworded; the other plans' retire lists quoted. Not blocking,
  accepted as disclosed: partial reads and the synced bundle as a group. The reviewer could not check the global files; the
  claims about them (including F-A1 to F-A5 and F-A7) rest on this author's reading and are unreviewed.
- Committed as `0bc3f94`.

### Increment B (done, uncommitted until the owner says commit)

- Extended `docs/specs/global-config-inventory.md` with the user-level settings file (34,228 bytes, read in full): every
  top-level key; all 46 `allow`, 84 `ask` and 18 `deny` entries, each with a disposition against the project's render (58
  `ask`, 281 `deny`, one `PreToolUse` hook, read on 2026-10-25); the 73 hook entries (all the approver); four plugins; and the
  settings-path question. Dispositions: all 46 `allow`, all 18 `deny` and all 73 hook entries `keep global`; of the 84 `ask`
  entries, 34 `move` (20 `ask-codex` spellings tied to the program, `git push`, 13 installs) and 50 `keep global` (35
  helper spellings, 12 plain entries, 3 `Edit`); of the plugins, `superpowers` is `redesign` and the rest `keep global`. The spec is the source for the exact rows.
- Answer to the settings-path question: the user-level settings file is neither denied nor asked for edits; the only `Edit`
  rules are three `ask` entries on approver and helper files (F-B3). Proposal only: the owner adds a rule. The named test
  runs on a copy under a scratch configuration directory and was not run here, because running it on the real file would
  write the user level.
- Findings F-B1 to F-B5. The ones that shape the move list: the approver looks only where an `ask` prompts (F-B1), and the
  module commands that replace the gated helpers render no `ask` (F-B2), so moving `claude-workflow` or `remote-runner` into
  a project removes a prompt and the approver's review unless that is addressed first.
- Verification as run: `doccheck`, `refcheck`, `git diff --check` exit 0. A script classified every `allow`, `ask`, `deny`
  and hook entry (it asserts none is left over); the settings file hash is the same at start and end and the 30 files of
  increment A still match, so this work wrote nothing at the user level. A search of the spec for global paths finds none.
- Review: one round with the `reviewer` agent, no blocking findings. Applied: the claim that the approver "still looks" at a
  project `ask` is now an untested inference (the trial ran a different hook type under `-p`); a note that a `move` of an
  `ask` removes the prompt in a project without the workbench; four rows that named credential-file patterns are described by
  role; two top-level key rows now say they are split; F-B5 says the other six denies are the only floor; a stale non-goal
  line. The reviewer could not read the settings file or the approver, so the counts and the approver claims rest on this
  author and the generating script.
- Not done: the settings-path test, and any interactive check of how `ask` and the approver behave.
- Committed as `8a3080d`.

### Increment C (done, uncommitted until the owner says commit)

- Extended `docs/specs/global-config-inventory.md` with the owner's user-level instruction file (281 lines, read in full): every
  heading and 70 paragraph-group rows, each with one disposition against the module policy blocks, skills and specs: 21 `move`,
  16 `redesign`, 33 `keep global`, none `drop` (CS1 becomes `drop` when the mirror repository is archived). Three rows
  (CS1, RP1, RP3) are two-part and are to be split in increment D.
- Proposals (not decisions) for the superpowers dependencies: repoint or drop the plugin skills in three agents' `skills:`
  lists; rewrite the routing to name the workbench skills; test the session-start rule once with the plugin off in a scratch
  configuration before disabling it; leave `dispatching-parallel-agents` and `writing-skills` as gaps; the plugin stays
  `redesign`. The session-start test was not run.
- Findings F-C1 to F-C7: the retired single-plan fallback, plan edits, the discovery gate and receipt, who decides a security
  review, the mirror rule, the project file and branch form of the remote paragraphs, and the compaction recommendation.
- Verification as run: `doccheck`, `refcheck` and `git diff --check` exit 0 (re-run after the review edits, below). A script
  counted the rows and confirmed each has a leading disposition; every heading of the file appears in the spec. The
  instruction file, the settings file and the 30 earlier files have the same hashes at the end as at the start, so this work
  wrote nothing at the user level. A search of the spec finds no global path, host name or credential.
- Review: one round with the `reviewer` agent, no blocking findings. Applied: F-C5 now cites the roadmap sentence and no
  longer says the owner updates a mirror; the F-C3 date is credited to the roadmap; F-C7 added for the compaction rule that
  `code-work.md` does not carry; RP3's cover corrected (`groundwork.md` policy block carries none of it; the renumbering rule is in
  `code-work.md`); two citations renamed; the hashes section and a stale commit reference fixed; the conflict between the agents'
  rows ("repointed") and proposal 1 stated. Noted for D: the compound rows. The reviewer could not read the instruction file,
  so the group splits and the quoted paraphrases rest on this author; the gates for the `move` rows were not run.
