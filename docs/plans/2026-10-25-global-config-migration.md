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

Empty until work starts.
