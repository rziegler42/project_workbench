# Terms, the former global setup, the inventory and the roadmap

Status: Proposed
Created: 2026-10-29
Candidate: workbench-v1#docs-cleanup-after-reset
Specs: terms, superpowers-ports, knowledge-tools, harness-modules, command-permissions, repository-boundary, global-config-inventory

## Goal

This is the second plan under the candidate; the first, `2026-10-29-specs-built-state-cleanup`, corrects what the specs say is built
and the contradictions between them, and is complete before this one starts. After this plan the words the specs rely on are defined
in `terms.md`, the specs that leaned on the owner's former global configuration say so with a date, the inventory of that
configuration opens by saying the reset ended the state it records, and the roadmap says what is true on 2026-10-29 and no longer
treats the old template and the global configuration as live.

## Scope

- `docs/specs/terms.md`, the specs named in Increment B, `docs/specs/global-config-inventory.md` and
  `docs/roadmaps/workbench-v1.md`, in four increments. Every fix is read from the spec, module or code it describes in the same
  increment.
- Passages that record a past state, such as the trials run under the owner's former configuration and the inventory rows, are kept
  and marked with the date and what changed. They are not rewritten.
- The owner's decisions of 2026-10-29: an owner-run command is one whose default level is `block` and that the approver may let an
  agent run; the identifier of a person who acts is `Name <email>`; and the approver is defined by capability.

## Non-goals

- Any change under `packages/`, any code and any test. The `verilog` module description and the seeded plans README wait for the
  plan that releases the packages.
- The citations of `AGENTS.md` sections that no longer exist, the rule for who accepts a decision, and the identity convention in the
  module READMEs: the policy plan and the approval-identity plan.
- Setting a spec's status to `Current`, editing an accepted decision, the heading format of roadmap candidates, and the `Status:` of
  two approved plans: the owner's calls.
- Rewriting the rows of the inventory. The inventory is the record of 2026-10-25 to 28 and is marked, not rewritten.

## Assumptions and constraints

- The first plan under this candidate is complete, so the specs the definitions are read from are corrected. If it is not, stop.
- Specs are living and edited in place; a spec written by someone other than the owner is untrusted until acknowledged, so the owner
  reads each increment's diff before it is accepted.
- The former user-level configuration is cited by role and date, never by path, because nothing tracked points to anything untracked.
- No increment touches a package, so no shipped approval goes stale.
- A command line that names a reserved word can be refused by the command gate. If a path trips it, stop and ask the owner.
- Each increment is one reviewed local commit, reviewed by a read-only reviewer pass of its diff.

## Completion criteria

1. `terms.md` defines the owner, the approver, an owner-run command, a level and the other words listed in Increment A, and no spec
   describes an owner-run command as one an agent can never run.
2. No spec cites a file outside the repository as a source, outside the inventory and the decisions; the trials under the former
   configuration are marked as historical.
3. `global-config-inventory.md` opens with a dated note that the reset ended the state it records, and its counts agree.
4. The roadmap no longer calls a built candidate unbuilt or an accepted decision proposed, and no longer points at the old template
   as a live source.
5. `wb check` and `wb run code-work check` report no problems, and `git status` shows only documents changed.

## Increments

### Increment A — Define the terms

**Outcome:** `terms.md` defines each word the other specs rely on, so the claim that every term is defined there is true.
**Dependencies:** the first plan under this candidate, complete.
**Affected areas:** `docs/specs/terms.md`, plus any line in another spec that step 4 corrects.
**Steps:**
1. Add **owner** (to be read with **approver**), **approver** (the person who may approve a plan, accept a decision or set a level,
   defined by that capability and not by authorship of a document) and **owner-run command** (a command whose default level is
   `block`: by default only a person at a terminal runs it, and the approver may set its level, per command, to a level that command's key offers (`ask`, `delegated` or `none`; the levels table says which each key
   offers, and `delegated` only where the command declares a gate), to let an agent run it; the levels are in `command-permissions.md`, "A level for every command"). The definition never
   says that an agent cannot run it. The written identity of a person who acts is the form the accepted record
   `2026-10-29-approvals-name-the-approver-by-git-identity` sets; cite it and do not copy it.
2. Add the words the reviewers found undefined: **level**, **levels table**, **key**, **agent-safe**, **rendering record**,
   **command gate**, **edit gate**, **agent gate**, **rerender**, **pin** and **local manifest**. Each is defined from the spec that
   owns it, with a pointer, and not restated at length.
3. Extend **checkpoint** and **delegation** to say that a checkpoint has a level (`block`, `ask`, `delegated`, `none`) and that
   `delegated` takes effect where a command declares a gate.
4. Search the other specs for "owner-run" and "the owner" used as a definition, and correct any that says an agent can never run an
   owner-run command. Leave uses that name the person who decides.
**Verification:** each new term appears once as a definition; no spec states that an agent cannot run an owner-run command; `wb check`
and `wb run code-work check` report no problems; only `terms.md` changed, plus any line corrected in step 4, which is named in the
Result.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-terms-inventory-and-roadmap-cleanup#A`.

### Increment B — What depended on the former global setup

**Outcome:** the specs that leaned on the owner's former global configuration say so, with a date, and none cites a file outside the
repository as a source.
**Dependencies:** none within this plan.
**Affected areas:** `docs/specs/superpowers-ports.md`, `knowledge-tools.md`, `harness-modules.md`, `command-permissions.md`,
`repository-boundary.md`.
**Steps:**
1. `superpowers-ports.md`: the evidence for which plugin skills were "used" cites the user-level instruction file and settings file
   by path, against the spec's own criterion and the rule that nothing tracked points to anything untracked; cite them by role and
   content hash, as the inventory does. The "what stops working when the plugin is removed" section is future tense; the plugin is
   gone, so say what stopped.
2. `knowledge-tools.md`: the statement of the owner's global instruction on memory cites the old global-config repository's
   instruction file by path; restate the assumption directly (the harness default is its own memory; installing the `mempalace`
   module opts a project into the palace) and drop the path.
3. `harness-modules.md` and `command-permissions.md`: the trials of global against project settings, and the `ask` and hook trials,
   ran under the owner's former global configuration, which set auto mode and carried an approver hook. Add a dated line that they
   are historical, and state which conclusions hold from Claude Code's behaviour alone and which depended on that configuration.
4. `repository-boundary.md`: the accepted design `2026-10-24-installer-reads-global-settings-on-request` says this spec "is amended"
   and the command built later; no amendment is there. Add a note that the amendment and the command are pending, so that the
   statement that the workbench never reads a harness's global configuration is read with it.
**Verification:** a search of the specs for the old user-level file paths and the old repository's name finds none outside the
inventory and the decisions; `wb check` and `wb run code-work check` report no problems; only the five files changed.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-terms-inventory-and-roadmap-cleanup#B`.

### Increment C — The inventory of the global configuration

**Outcome:** `global-config-inventory.md` opens with what the reset ended, so the file reads as the record of 2026-10-25 to 28 and
not as the owner's live configuration.
**Dependencies:** Increment B, and the floor-rules plan, committed as `fe966b0`.
**Affected areas:** `docs/specs/global-config-inventory.md`.
**Steps:**
1. Add a dated note at the top: the user-level configuration was reset to factory defaults on 2026-10-29, a copy is kept on the
   owner's machine, the rows record what it carried on 2026-10-25 to 28, and a "keep global" row now means "kept in the backup", not
   "kept in use". Cite the backup by role and date, never by path.
2. Add a short section "After the reset" listing what changed in kind: the agents, hooks, approver and settings the rows name no
   longer run; the superpowers plugin is off, so the three proposals for disabling it are history; the global deny list is gone,
   and which of its entries the compiled floor now carries (`rmdir`, `unlink`, `shred` and the `gh` read, from commit `fe966b0`, which
   a clone renders only after the owner's `wb rerender`; check that `workbench/rules.py` holds them before writing this) and which it
   does not (`git merge`, the Codex login read); the module-command asks now decided
   (`2026-10-29-workbench-asks-for-remove-submit-and-fetch`).
3. Mark the open questions whose premise ended: F-B2 (the approver covering module spellings), F-B5 (the global deny as the only
   floor) and F-A4 (the guard's `chunk` mode) get a one-line status each.
4. **Checkpoint before this step:** it names authentication material that lives in the backup. The module that provides
   `security-review` is installed, so ask the owner whether to run a security review, and run one only if the owner asks; record the
   answer in the Result. Then add a short list of items found in the backup that the inventory never recorded (the review bridge's
   configuration and prompts, the existence of a seal key, the vendored graphify skill and the earlier snapshots), by role and
   existence only: no value, no content, no hash of a secret and no path.
5. Check that the counts agree with each other in the coverage list, the totals and the part tables.
**Verification:** the note and the section are present; the counts agree; no path into the user's home directory is added to a
tracked file; `wb check` and `wb run code-work check` report no problems; only this file changed.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-terms-inventory-and-roadmap-cleanup#C`.

### Increment D — The roadmap

**Outcome:** the roadmap says what is true on 2026-10-29 and no longer treats the old template and the global configuration as live.
**Dependencies:** Increment C.
**Affected areas:** `docs/roadmaps/workbench-v1.md`.
**Steps:**
1. The candidate `checkpoint-levels-beyond-block` says its decision "is `Proposed` and not yet accepted"; it was accepted on
   2026-10-29. Correct it.
2. The Bootstrap section describes work as still ahead (approval "in session", mechanical enforcement "waits for the code", the
   installer "not run on its own repository" until two plans, commits made with the owner's own tooling) and names the old template
   manifest. Those plans are complete. Reduce the section to a short history note.
3. The Purpose says Claude and opencode are the supported harnesses; only Claude exists. Say so.
4. The suggested order omits the candidates added since and carries stale text about the seven candidates before
   `global-config-migration`. Replace the order with a statement that candidates carry no order, as the roadmaps README says, or add
   the missing IDs; do not renumber or rename an ID.
5. `global-config-migration`: rewrite the Outcome, Boundary and trigger around what happened. The owner reset the user level in one
   step and kept a backup, so the gradual removal and the "never absent in between" guarantee were overtaken; what remains is
   re-adopting from the backup only what the workbench does not supply, the floor test, and archiving the two old repositories. This
   changes a candidate's direction, so the owner reads it as part of approving this plan.
6. Candidates that call the owner's earlier skills "global configuration" (`graphify-module`, `knowledge-base-package`,
   `port-superpowers`, `verilog-module`, `cad-modules`): say the source is the former user-level backup. Before writing anything about
   the old template repository, check read-only which of the cad and graphify sources exist in the backup and which in the old
   template repository, and record what was found by role, retrieval date and a content hash of each source. If the template is
   the only copy of a source, add to `cad-modules` or `graphify-module` that the repository is archived only after the candidate
   has taken what it needs; if it is not, say so, and leave archival to the owner. Do not write the claim unverified. Mark `verilog-module` and `security-review-module` as built by the plans that name them, and write completion nowhere
   else.
7. Fix dead references (`code-work-approval`, and `peer-review-provider` if present) and replace the "Related decisions" list, which
   stops at 2026-10-22, with a pointer to `docs/decisions/`.
**Verification:** searches for "not yet accepted", the old template manifest name and "code-work-approval" in the roadmap come back
empty; `wb check` and `wb run code-work check` report no problems; only the roadmap changed.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-terms-inventory-and-roadmap-cleanup#D`.

## Verification for the plan as a whole

- `wb run code-work check` reports no problems on this plan before it goes to the owner, and again after any edit.
- After the last increment, `git status` shows no file changed outside `docs/`, and `wb verify packages/workbench` runs with no
  refusal, so no shipped approval went stale.
- A read-only reviewer pass of each increment's diff, and the owner's read of each diff, before the commit is accepted.

## Risks and sensitive actions

- Specs and the roadmap are the project's authority. A wrong correction is as harmful as the drift it fixes, so each is made from
  the module or code read in the same increment.
- Increment D rewrites a candidate's direction (`global-config-migration`). The owner's approval of this plan is that direction's
  approval, so the owner reads that step before approving.
- A spec status can imply the owner's approval. This plan never sets `Current`.
- A wide documents-only change is easy to review badly. Each increment is limited to named files and a named search, and the owner
  reads the diff before it is committed.
- No code, package, shipped approval or permission is touched.

## Review record

Plan review by Codex through the `ask-codex` bridge (model `gpt-5.6-terra`), round 1 of 3. Outcome: four findings, all applied.

- **Applied (major).** The owner-run definition no longer says every level is available to every command: a command's key offers
  its own levels, and `delegated` only where a gate is declared. This was an error of mine against `command-permissions.md`.
- **Applied (major).** The inventory step depends on the floor-rules plan as committed (`fe966b0`), checks that the rules file holds
  the four rules, and says a clone renders them only after the owner's re-render. The floor-rules plan's Result, which still read
  as pending, was corrected.
- **Applied (major).** A security-review checkpoint precedes the step that lists backup items, which are limited to role and
  existence: no value, secret hash, content or path.
- **Applied (major).** The claim that the old template is the only other copy of the cad and graphify sources is written only after
  a read-only check, recorded by role, date and content hash; otherwise archival is left to the owner.
- **Not asked for.** A second round.

## Deferred work

- The `AGENTS.md` citations, the rule for who accepts a decision, the identity convention in the READMEs, the seeded plans README,
  and the `verilog` module description: the policy and module-asks plan.
- The heading format of roadmap candidates, an index of specs and decisions, and the `Status:` of two approved plans: the owner's
  call, not made here.

## Result

**Increment A is done; Increments B, C and D are not started.** Its commit carries the trailer
`Plan: 2026-10-29-terms-inventory-and-roadmap-cleanup#A`.

### Increment A

- **Done.**
  - `terms.md`: a new section "Permissions and approval" defines **owner**, **approver**, **owner-run command**, **agent-safe
    command**, **level**, **key**, **levels table**, **pin**, **rendering record**, **rerender**, **local manifest**, **edit
    gate**, **command gate** and **agent gate**, each from the spec or code that owns it. The entries **checkpoint** and
    **delegation** read in terms of levels. The **manifest** and **scratch** entries point to the **local manifest** entry, and
    **block** (a slot's content) says it is not the level `block`.
  - The owner-run definition says the default level is `block`, that the approver may set a key to a level it offers (`none` for
    an installer command, `ask`, `delegated` or `none` for `approve-plan`, `ask` or `none` for a module command that declares
    `levels`), that `delegated` exists only where a command declares a gate, and that it never means an agent can never run it.
  - `installer-interface.md`: five lines said "Agent may run it: no" (`install`, `adopt`, `attach`, `acknowledge`, `recover`); each
    now says "by default no" and names the key that the approver may set to `none`.
  - `module-boundary.md` and `module-contract.md`: a module's `owner` arguments are the ones only the owner runs "by default".
- **Verification as run.** A script finds 75 terms, none defined twice, and none of the 16 wanted terms missing; a search of the
  specs for absolute statements that an agent can never run an owner-run command finds only default-level statements (the `block`
  level row, the `wb rerender` key, which offers `block` only, and a sentence that already names the exception); `wb check` and
  `wb run code-work check` report no problems.
- **Review.** One read-only reviewer pass. It found no contradiction with the two accepted decisions and no `AGENTS.md` citation,
  dead link or unknown plan name. It found one problem against this plan's own verification line (the five "Agent may run it: no"
  lines, which my search missed because I searched for other phrases) and ten smaller points, all applied: the offer sets and the
  default of an agent-safe command, hedges on what `block` denies and what `none` logs, the conditions under which the command gate
  and edit gate exist, a double definition of the local manifest, the slot `block` versus the level `block`, and the four levels
  and the `peer-review` provider in the `checkpoint` and `delegation` entries.
- **For the owner.**
  - **Approver** says "a specification that says 'the owner' at a checkpoint means the approver". No spec says that; it is the
    interpretive rule of your decision to use "approver" in rule text. It grants no authority, but read it.
  - **Owner** is scoped to "a machine that holds the workbench's guarded store". That scoping is my wording and appears in no
    source.
  - The root `README.md` and `docs/development.md` say owner-run commands "refuse to run from an agent session". That is true at
    the default and is worded as absolute. They are outside this plan.
  - The identity form in **approver** is marked "not built yet", because the approval-identity plan is not written.
