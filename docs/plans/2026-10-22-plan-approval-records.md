# Plan approval as a recorded approval, and the gate that reads it

Status: Approved
Created: 2026-10-22
Candidate: none — the first slice of the roadmap candidate `code-work-approval`, which is too large for one plan; the roadmap split is increment F, so completion is not derived
Specs: code-work, trust-and-approval, module-contract, installer-interface

## Goal

Make "a plan is approved" a fact the agent can check and cannot write. Today approval is the owner's statement in
session and a `Status:` line is informational. When this plan is done, the owner approves a plan with an owner-run
command that records a hash of the plan's hashed region in the guarded store; an agent-safe command says whether a
plan's current text matches a record; editing only the status line, the review record or the result leaves the
approval valid, and editing anything else invalidates it. Nothing here delegates an approval to a reviewer: every
approval is the owner's.

When this plan is done:

- `trust-and-approval.md` and `code-work.md` state the formats this plan fixes (the record, the declaration field,
  the two commands), and the open "Formats still proposals" item for plan approvals is closed;
- a process module can declare the pinned command that computes the hashed region of its plans, and the installer,
  which names no module and reads no plan, records and compares what that command reports;
- `wb approve-plan <plan>` (owner-run, terminal only) records an approval, and `wb plan-status <plan>` (read-only,
  agent-safe) reports `approved`, `changed since approval`, or `not approved`, with a reason;
- the Claude harness denies `approve-plan` to the agent like every other owner-run command;
- `code-work` ships the region command, declares it, its policy block says approval is a record, and the shipped
  approvals match.

## Scope

- **The formats and the rule**, written first as spec text and a Proposed decision (increment A).
- **The declaration field** a process module uses to name its region command, the verifier's check of it, and the
  installer's resolution and bounded run of that pinned command (increment B).
- **The record and the two commands**, their classification in `workbench/rules.py`, and the rendered `deny`.
- **The `code-work` side**: the `region` subcommand of its helper (which reuses the helper's own plan reader, so
  there is one reader), the declaration, the README and policy text, the `draft-plan` skill's wording.
- **A security pass and the release** of the shipped approvals (owner-run), then the specs, roadmap and decision.

## Non-goals

- **Delegated approval.** A reviewer giving the verdict needs a `peer-review` provider, which is the later
  `review-engine` candidate. Every checkpoint stays `stop`; the record has no delegate field yet.
- The checkpoint settings, the loop caps, the increment-loop and review skills, the reviewer agent, the push
  checkpoint and the compaction guidance. They are separate candidates (increment F).
- Making an agent unable to start an increment. The gate is a command and a rule, not a hook; see Risks.
- Approval of anything but a plan (a spec's direction, a decision, a remote job).
- Any change to the owner's global Claude configuration or to a real model call.

## Assumptions and constraints

- Python standard library only; tests with `unittest`; the full suite is `python3 -B -W error tests/run_all.py`.
- The installer and its tests name no first-party module, helper or path (`tests/test_boundary.py`), and, by the
  accepted decision `2026-10-22-plan-check-in-the-shipped-helper`, the installer knows nothing of plans: it never
  reads a plan and has no list of section names. What is inside the hashed region is decided by the process
  module's pinned helper, which already holds the plan reader and its fence and quotation handling.
- Records live in the guarded store under the project ID, as pins and baselines do
  (`trust-and-approval.md`, "Concrete formats"). The store is not writable by an agent command; only an owner-run
  command writes it.
- A plan is read as hostile text by the helper, which is bounded and does not follow links, as `check` already is.
  The installer treats the helper's output as data: it bounds it, validates its shape and follows nothing in it.
- Discovery tooling: graphify: skipped — not installed in this project; the scope was found by reading
  `docs/specs/code-work.md`, `docs/specs/trust-and-approval.md`, `docs/specs/module-boundary.md`,
  `workbench/rules.py`, `workbench/cli.py` and the accepted decisions
  `2026-10-19-mandatory-review-personal-delegation` and `2026-10-22-plan-check-in-the-shipped-helper`.

### Choices (made by me; the owner may change any)

1. **The installer owns the record and the commands; the module's pinned helper owns what the hashed region is.**
   This follows `trust-and-approval.md` ("this specification defines the rule and the process module defines the
   section names") and the accepted plan-check decision. A helper that also wrote the record was rejected: a module
   command is agent-safe by design, so an agent could run it, and nothing could deny it per module. A parser in the
   installer was rejected (review R2-F1): it would put the plan format in `workbench/` and create a second reader to
   keep in step.
2. **A new declaration field, not a new module type.** A `process` module may declare an `approval` command: the
   name of one of its own commands and the first argument that computes the region (for `code-work`, `region`).
   The exact field, and whether it needs `module-contract.md` to bump a version, are fixed in increment A.
3. **Two commands, named for the subject:** `approve-plan` (owner-run) and `plan-status` (agent-safe). Names are
   proposals until the code exists.
4. **A plan is named by its path in the project**, relative to the root, and the record binds the path and the
   region hash. A copy of the same text at another path is not approved.
5. **The command is resolved and bound, not assumed.** Both commands run in an installed project. Each resolves
   exactly one process module that declares `approval` from the committed manifest (none, or more than one, is a
   refusal) and runs its command only as `wb run` does: the module installed and approved, its declaration and tree
   hashes equal to the manifest's, the helper pinned for that command and unchanged. The record stores the
   process module's declaration hash and the helper's pinned SHA-256 with the path and the region hash, and
   `plan-status` reports `changed since approval` when either differs, so a pulled edit of the helper or the
   declaration cannot widen what an old approval covers.
6. **The command's contract is small.** Given the plan's path it prints one JSON object `{"format": 1,
   "region_hash": "<64 lowercase hex>", "unhashed": ["<section>", ...]}` or refuses with a `refused:` line and
   exit 1. The installer shows `unhashed` to the owner at approval, bounds the output, accepts no other shape, and
   treats a missing or malformed object as no approval. An ambiguous plan (a duplicated excluded heading, no
   `Status:` line before the first heading) is the helper's refusal, not a guess.
7. **The commands' grammar and the path rules.** `wb approve-plan <plan>` and `wb plan-status <plan>` take exactly one
   argument and no option, and run from anywhere inside the project: the root and ID come from the project finder
   that `wb run` uses, with the same refusals, and a target option is not accepted. `<plan>` is a path relative to
   the current directory or absolute; it is converted to a path relative to the project root and refused if it is
   outside the root, absolute outside it, empty, holds a NUL or a `..`, or has a link in any component, the last
   included. The installer opens nothing in the plan itself: it hands the helper the root-relative path, and the
   helper reads it bounded and without following a link. The record names the plan by that root-relative path.
   `approve-plan` runs the command twice, once to show the hash and once after the typed answer, and writes the
   record only if both reports are equal; a plan swapped between the two runs therefore yields no record, and a
   swap after the second run is the same as an edit after approval, which `plan-status` reports.

## Completion criteria

1. The specs state the record, the declaration field, the command contract and the two commands, and a Proposed
   decision records who owns what (it is accepted only by the owner).
2. A synthetic process module's declaration with the field verifies; a malformed field, one naming a command the
   module does not declare, or the field on any other module type is refused.
3. The `code-work` `region` command ignores the status line, the review record and the result, and normalizes line
   endings, trailing whitespace and the final newline. A test shows every other section's change changes the hash,
   and that a spoofed heading (inside a fence, in a quote, indented, in another case, duplicated) cannot hide a
   hashed section.
4. `approve-plan` refuses without a terminal, shows the plan's path, the process module, the `unhashed` list and the
   region hash, records only when the typed prefix matches, runs the command again before writing, and writes a
   record (path, region hash, process declaration hash, helper SHA-256) that `plan-status` reads back as `approved`.
5. `plan-status` reports `not approved` for a plan with no record, `changed since approval` for an edited one,
   and `approved` after a status, review-record or result edit; a committed `Status: Approved` line alone is
   `not approved`.
6. A `<plan>` that breaks a rule of choice 7 (outside the project, absolute outside it, a `..`, a NUL, a link in any
   component, a missing file or a directory) is refused by both commands with nothing written, from the project root
   and from a subdirectory alike, and the same plan named two ways gets one record. A plan through a link,
   oversize, with a duplicated excluded heading or without a status line
   is refused by both commands and nothing is written. So is a project with no process module that declares
   `approval`, with two, or whose process module is missing, unapproved or differs from the manifest, or whose
   helper is unpinned or changed. An edit of the process declaration or of the helper after approval turns
   `approved` into `changed since approval`. A helper that prints anything but the contract's object is no approval.
7. The Claude module renders a `deny` for `approve-plan` in every spelling of the owner-run commands; `plan-status`
   is not denied.
8. The full suite passes; the boundary test passes; the installer's text contains no plan heading name; the shipped
   approvals match and the stale records are gone.

## Increments

### Increment A — The formats and the rule

**Outcome:** the spec text and a Proposed decision say exactly what is recorded, where, and who may write it.
**Dependencies:** none.
**Affected areas:** `docs/specs/trust-and-approval.md`, `docs/specs/code-work.md`, `docs/specs/module-contract.md`,
`docs/specs/installer-interface.md`, `docs/decisions/` (one new Proposed record).
**Steps:**
1. Fix the record (path in the store, fields, key), the declaration field, the command's contract (choice 6), the
   resolution and binding of the command (choice 5), the grammar and path rules of the two commands (choice 7),
   their output and exit codes, and what each refusal says.
2. State in `code-work.md` that its hashed region excludes the status line, the review record and the result and is
   computed by its `region` subcommand, and in `trust-and-approval.md` that the installer records what the declared
   command reports and reads no plan.
3. Write the decision record (Proposed): the installer owns the record and the gate, the module's pinned helper owns
   the region, and why neither a module command that writes the record nor a parser in the installer.
**Verification:** the document checks pass; the boundary rule is restated and no spec puts a plan heading name in
the installer's text.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-22-plan-approval-records#A`. Increment B waits
for the owner's word on the decision.

### Increment B — The declaration field and the command runner

**Outcome:** the installer can resolve a project's approval command and run it bounded, with no module named.
**Dependencies:** A.
**Affected areas:** `workbench/declarations.py`, a new `workbench/approvalcmd.py`, `tests/`.
**Steps:**
1. Test first, with synthetic modules and a synthetic helper: the field verifies on a process module; a missing,
   repeated or malformed entry, a command the module does not declare, and the field on another type are refused.
2. Write the resolver of choice 5 (one declaring process module from the manifest, verified as installed and
   approved, the helper pinned and unchanged), reusing the launcher path that `wb run` and the module checks use,
   and the reader of choice 6 (bounded output, one JSON object of the stated shape, nothing else). Tests: none, two,
   an unapproved module, a declaration that differs from the manifest, an unpinned or changed helper, oversize
   output, a malformed object and a helper that prints instructions.
**Verification:** the new test files pass and the boundary test passes.
**Evidence:** the one local commit, trailer `#B`.

### Increment C — The record and the two commands

**Outcome:** the owner can approve a plan and an agent can read whether it is approved.
**Dependencies:** B.
**Affected areas:** a new `workbench/planapprovals.py`, `workbench/cli.py`, `workbench/rules.py`,
`docs/specs/installer-interface.md`, `docs/development.md` (the command entries), `tests/`.
**Steps:**
1. Test first, with a temporary store and a fully installed synthetic project: each criterion 4 to 6, run from the
   root and from a subdirectory, every path refusal of choice 7, a plan swapped between the two runs of
   `approve-plan`, a store that is damaged, a record that differs in path, region, declaration hash or helper hash, and a record for
   the right text at the wrong path.
2. Write the path conversion of choice 7 over the project finder, the record (strict JSON, atomic write, first
   record kept), `approve-plan` (owner-run: terminal test, the shown hash prefix typed back, the command run again
   before writing and the two reports compared) and `plan-status` (read-only, agent-safe).
3. Add `approve-plan` to `OWNER_RUN` and `plan-status` to `AGENT_SAFE`; the existing rule tests then cover every
   spelling.
**Verification:** the new tests and the rules tests pass; `python3 -m workbench plan-status` on a plan with no
record prints `not approved` and exits non-zero.
**Evidence:** the one local commit, trailer `#C`.

### Increment D — The `code-work` side

**Outcome:** the process module computes its region, declares it, and says approval is a record.
**Dependencies:** C.
**Affected areas:** `packages/workbench/code-work/` (`helper/code-work`, `module.json`, the policy block, the plans
README text, the `draft-plan` skill and the helper's tests), `packages/workbench/claude/tests/`.
**Steps:**
1. Test first: `region` on this repository's own plans and on a hostile corpus (criterion 3), its agreement with
   `check` on the sections of the hashed region, and its refusals (link, oversize, duplicate excluded heading, no
   status line). Then add the subcommand over the helper's existing reader, add `region` to the command's
   `arguments`, and declare `approval`.
2. Update the policy block and README to say approval is a record made with `wb approve-plan` and read with
   `wb plan-status`, and that a `Status:` line is informational.
3. Test that the declaration verifies, that an end-to-end `approve-plan` then `plan-status` works in a temporary
   installed project, and that the Claude module denies `approve-plan` and allows `plan-status`.
**Verification:** the code-work and claude roots pass.
**Evidence:** the one local commit, trailer `#D`.

### Increment E — Review and release

**Outcome:** the work is reviewed, findings are fixed, and the approvals match.
**Dependencies:** A to D.
**Affected areas:** fixes from the review, `workbench/shipped_approvals/packages/`.
**Steps:**
1. On the owner's request, a `security-reviewer` pass over the `region` subcommand, the command runner and the two commands
   (hostile plan text, links, oversize input, a helper that prints a forged object, a forged record, a swapped file
   between the shown hash and the write), and a
   `workflow-reviewer` pass over the plan. If the owner asks for neither, the plan records that.
2. Fix findings with regression tests, and record each review in the Review record.
3. After the owner says "Run it for me": `python3 -m workbench release-approvals`; after a preview and the owner's
   "remove them", delete the stale records.
4. Run the full suite.
**Verification:** `python3 -B -W error tests/run_all.py` is green and the shipped-approval tests pass.
**Evidence:** the review outcome in the Review record, the records added and removed and the suite counts in the
Result, trailer `#E`.

### Increment F — Specs, roadmap and decision

**Outcome:** the documents describe the system as it is.
**Dependencies:** E.
**Affected areas:** `docs/specs/code-work.md`, `docs/specs/trust-and-approval.md`, `docs/development.md`,
`docs/roadmaps/workbench-v1.md`, the Proposed decision of increment A.
**Steps:**
1. The specs' "As built, and its limits" say what exists; "Formats still proposals" drops plan approvals.
2. Roadmap: split `code-work-approval` into the remaining candidates (proposed: `delegated-approval`, which needs
   `review-engine`; `checkpoint-settings-and-caps`; `increment-loop-and-review-skills`, with the reviewer agent;
   `push-checkpoint`; `compaction-guidance`), and record this plan's outcome in Current state. This is a direction
   edit and needs the owner's approval of this plan.
3. The decision's Verification lists what is built. It stays Proposed until the owner accepts it.
**Verification:** the document checks pass; the full suite passes; a search finds no document naming
`code-work-approval` as a single remaining outcome.
**Evidence:** the one local commit, trailer `#F`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots.
- `git diff --check` is clean and `git status` is clean after the last commit.
- An owner-run check in a temporary, fully installed synthetic project (a process module supplying the field): run
  `wb approve-plan <plan>` from inside that project (any directory in it), edit its status line and see `approved`, edit its scope and see `changed since
  approval`. This repository is not an installed project, so approving its own plans with the command waits for
  `self-hosting` (the roadmap keeps the installer off its own repository until then); until that, approval of this
  repository's plans stays the owner's statement in session.

## Risks and sensitive actions

- **A new owner-run command that writes the guarded store.** It is classified like `approve` and `pin`, denied to
  the agent by the harness, and its typed confirmation is friction, not authentication, as the spec already says
  for those commands.
- **The `region` subcommand reads hostile text and decides what an approval covers.** A heading that hides a
  section from the hash would let a plan change after approval. Its rule is fixed and tested against spoofed
  headings, and ambiguity is refused; the security pass tries to bypass it.
- **The installer runs a module's helper at approval time and trusts its answer.** The helper is the owner's
  approved, pinned code, run only as `wb run` runs it, and its output is bounded and validated as data. A helper
  that lies about the region defeats the approval, as any approved module could defeat what it is trusted for; the
  record binds the helper's hash, so a pulled edit of it invalidates old approvals.
- **The gate is not enforced by the harness.** `plan-status` answers, and the skills of a later candidate tell the
  agent to ask it; nothing here stops an agent that ignores the rule. Hard stops still stop at the time of the
  action, whatever any approval says.
- **A forged or stale record.** Only an owner-run command writes the store; a record is valid only while the path,
  the region hash, the process declaration hash and the helper hash all match.
- `release-approvals` and the deletion of stale records run only on the owner's exact words, as before.
- Nothing is pushed by this plan.

## Review record

Reviewed by Codex (`gpt-5.6-luna`, effort medium) on 2026-10-22, at the owner's request. Round 1 of a bound of 3;
outcome: changes needed, two major findings, both applied. Round 2 of 3 (same model and effort): one major finding,
applied. Round 3 of 3: one major finding, applied. The bound was reached, so the round 3 fix has not been
reviewed.

- R1-F1 (applied): the plan did not say how the process declaration is resolved or authenticated. Choice 5 now
  resolves exactly one process module from the manifest, verifies it as installed and approved, and stores its
  declaration hash in the record; increments B and C and criteria 4 and 6 carry the tests.
- R1-F2 (applied): the whole-plan hand run needed this repository to be an installed project, which it is not
  until `self-hosting`. The check is now an owner-run run in a temporary installed synthetic project, and approving
  this repository's plans with the command is deferred.
- R2-F1 (applied): the plan put a plan-section parser in the installer, against the accepted decision
  `2026-10-22-plan-check-in-the-shipped-helper` ("the installer knows nothing of plans") and the module-boundary
  spec. The design is revised: the process module's pinned helper computes the region (`code-work region`, over the
  helper's existing reader, so no second reader and no parity test), the installer records and compares what a
  declared `approval` command reports, and the record also binds the helper's hash. This took the reviewer's first
  suggestion, so no superseding decision is needed. Increments B, C and D, choices 1, 2, 5 and 6, and criteria 2 to 8
  changed.
- R3-F1 (applied): the plan never defined how the commands find the project root or turn `<plan>` into a path. Choice
  7 now fixes the grammar (one argument, no option, from anywhere in the project), the root-relative path rules and
  the two-run check against a swap; increments A and C and criterion 6 carry the tests and the spec text.

The review is not an approval. The owner approved the plan on 2026-10-22, after the third round, knowing that the
round 3 fix was not reviewed.

## Deferred work

- Delegated approval, its helper and its record fields (needs `review-engine`).
- The checkpoint settings, the loop caps, the increment-loop and review skills, the reviewer agent, the push
  checkpoint and the compaction guidance, as the split in increment F names them.
- A way for an enforcement point (the commit helper or a hook) to refuse work on an unapproved plan.
- Approval of things other than plans.
- Approving this repository's own plans with the command (needs `self-hosting`).

## Result

In progress. Increments A and B are done.

- **A** (`aad363f`): the specs and the Proposed decision `2026-10-22-installer-records-plan-approval-module-computes-region`.
- **B**: the `approval` declaration field (`workbench/declarations.py`; `Module.approval`, refused on any
  type but `process` and for a command or argument the module does not declare), the shared pin check
  `commands.check_pin` (`wb run` now uses it too), and `workbench/approvalcmd.py` (`resolve`, `region`,
  `parse_report`). Tests: `tests/test_declarations.py` and the new `tests/test_approvalcmd.py`, with synthetic
  modules only.
  - The installer already refuses a second process module at install (`process-count`), so a project that
    records two cannot be made by install; the resolver still refuses it, and its test simulates the second.
  - The plan path handed to the helper must pass the path validator and may not start with `-`; this is an
    addition to choice 7's rules, made because the helper takes the path as an argument.
  - "Approved" in choice 5 is what `wb run` checks: the manifest records the module and its declaration hash
    matches. The tree hash is not compared at run time, as for `wb run`; the helper's bytes are, through the pin.
- **Next:** increment C (the record and the two commands).
