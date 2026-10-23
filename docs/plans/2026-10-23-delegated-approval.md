# Delegated plan approval

Status: Completed
Created: 2026-10-23
Candidate: workbench-v1#delegated-approval
Specs: trust-and-approval, code-work, review-engine, module-contract, installer-interface

## Goal

The owner may let a second reviewer give the verdict on a plan. The accepted record
`2026-10-19-mandatory-review-personal-delegation` allows that only when the owner's personal setting for the checkpoint
is `delegate`, a `peer-review` provider is installed and approved, and review converged within the round cap. Before
this plan none of it worked: `delegate` had no effect (every checkpoint stopped), the `review-engine` module gave
findings and no statement of whether a review had converged, and no helper wrote a delegated approval. An agent that
had a converged review of a plan still had to wait for the owner to run `wb approve-plan`.

When this plan is done:

- with `approve-plan` set to `delegate` in the owner's personal settings, an agent can run
  `wb delegate-approve-plan <plan>` and the plan is approved if, and only if, a sealed review of exactly those bytes
  converged inside its round bound, the plan is delegable, and the process module and the provider answer as declared;
- the approval is a record in the guarded store that names its delegate (provider module, bridge, model), the rounds
  used and the review it rests on, and is bound to the same hashed region and checks as an owner approval, so the edit
  gate and `wb plan-status` treat it like one;
- every other checkpoint still stops whatever its setting says, a project cannot turn delegation on, and a teammate
  with no settings gets `stop`;
- the specs say exactly what is built and what is not.

## Scope

- Specification first, read by the owner, and a decision record in `Proposed` status (increment A).
- A read-only convergence argument on the `review-engine` module and the contract field that lets the installer ask
  a `peer-review` provider for it (increment B).
- A read-only delegability argument on the `code-work` module, declared like `approval.active` (increment C).
- The installer's `delegate-approve-plan` command, the approval record's delegate fields, and the reading of the
  `approve-plan` setting for this one checkpoint (increment D).
- The neutral guidance an agent follows, and what `wb settings` says (increment E).
- The security pass, the specs' "as built", the package approvals (owner-run) and this plan's Result (increment F).

## Non-goals

- Delegating any checkpoint other than `approve-plan`: `push-shared-branch`, `submit-remote-job`,
  `fetch-remote-output`, `change-direction`, `accept-decision` and both acknowledgement tiers stay `stop`, whatever the
  setting says. Each needs its own plan.
- Anything that lifts a hard stop. A hard stop stops at the time of the action.
- A reviewer of actions (`action-review-engine`), a second bridge, or any change to how a review round runs.
- A project-level or committed switch for delegation. The setting is personal and only the owner writes it.
- Accepting a decision record, or approving a plan, on the owner's behalf. The owner's `wb approve-plan` stays as built.
- opencode.
- A list of who approved what (a report command); the record holds the facts and a reader can be added later.

## Assumptions and constraints

- `workbench/` and `tests/` hold only mechanism, and `tests/test_boundary.py` must stay green: the installer may name no
  first-party module, helper, command or harness. The installer learns about the provider and the process module
  only from their declarations, as it does for `approval` today.
- A helper is a self-contained script that imports only the standard library and `wbkit`; the installer runs a
  declared, pinned command as `wb run` does and treats its output as data: bounded, strict, validated, never followed.
- The guarded store is the only place the agent's harness denies writes to; the project tree is writable by the
  agent. So everything that decides an approval is read from the guarded store, from a sealed state whose key is in
  the store, or from a pinned helper's validated output.
- The review engine's state is sealed with a key in the guarded store (`review-engine.md`); `status` and a round
  refuse an unsealed or rolled-back state. A delegated approval refuses the same states.
- A model name may be unknown: a bridge that is given no `--model` reports none (found in the hand run of
  2026-10-23). The record then holds null, and the approval says so.
- Editing any file of a package changes its hash and stales its shipped approval. The release is the owner's
  (`release-approvals`, run by me only on "Run it for me"); stale records are removed only after a preview and
  "remove them".
- Discovery: graphify: skipped, not installed here; the scope was enumerated by reading the roadmap candidate, the
  accepted records 2026-10-19 (delegation) and 2026-10-22 (bridges), `trust-and-approval.md` (Plan approval, Delegated
  approval, Plan approval records, Checkpoint and cap settings), `code-work.md`, `review-engine.md` and the
  declaration schema.

### Choices (made by me; the owner decides each at increment A)

1. **The installer writes the delegated record, not a module.** The two specs disagree: `code-work.md` says the
   delegation helper "is implemented with this module", and `trust-and-approval.md` says the helper that writes into
   the guarded store is a component of the workbench that no module ships. I follow the trust spec. The guarded
   store is the installer's, the approval record is the installer's, and a module that wrote it would need write access
   the agent must not have. The installer reads facts through declared, pinned commands (as it does for `region` and
   `active`) and writes the record itself. The new command is `wb delegate-approve-plan <plan>`; it is not owner-run.
   Increment A edits `code-work.md` to match.
2. **The review must be of exactly the bytes being approved.** The reviewer reads the file; the review engine records a
   SHA-256 of those bytes per round. The installer hashes the plan file itself and requires it to equal the last round's
   hash. That needs no knowledge of plan sections in the engine or the installer. The cost is an order: the agent
   approves after the converging round and before it writes the plan's review record, because that record changes the
   file. An approval attempted after the record is written is refused with that reason; the agent reviews once more
   or the owner approves. The approval still binds the hashed region, so the review record, status line and result
   can change later without invalidating it.
3. **Convergence is the engine's own rule, read from a sealed state.** The engine's `converged` already means: the last
   round has no `blocker` or `major` finding and none is pending a decision. The new `convergence` argument prints it
   with the facts the installer records, after the engine's own seal and mark checks. A rejected finding does not
   converge a review, because the last round must itself be clean.
4. **Delegability is the process module's judgement.** `trust-and-approval.md` makes a plan whose risks list a
   hard-stop action not delegable. Only the plan format knows what the Risks section is, so `code-work` answers it
   through an `approval.delegable` argument. A plan declares a hard stop with a line in its Risks section that begins
   `Hard stop:`; a keyword match is not used, because Risks sections routinely say "no push, no install". It is
   defence in depth, as the spec says; the real control is that hard stops stop at the time of the action.
5. **The approvals file moves to `format: 2`.** An entry gains an optional `delegate` object. The reader accepts
   formats 1 and 2 and writes 2; an older workbench refuses a format-2 file, which fails closed. The four values that
   decide `approved` (plan, region hash, declaration hash, helper hash) are unchanged.
6. **`delegate` takes effect for `approve-plan` only.** The effective-values rule changes for that one name and stays
   `stop` for every other. `wb settings` prints `checkpoint <name>: stop` for any other name the owner set to
   `delegate`, with a `settings:` note that delegation of that name has no effect (today it prints `delegate`). This
   changes the output of a built command.
7. **A closed (archived) review still counts**, provided its state is sealed and its last round converged. Archiving is
   the owner's act and says nothing against the verdict.
8. **A delegated entry counts only while the setting stands.** `wb plan-status` and the edit gate treat an entry that
   has a `delegate` object as an approval only while the owner's personal setting for `approve-plan` reads `delegate`
   at that moment; a setting that is `stop`, missing or damaged withdraws it (the plan reads `not approved`, and the
   line says why), and the owner's own `wb approve-plan` is then the way to approve. The record's provider hashes are
   provenance and are not checked when the entry is read: a provider that is changed, replaced or removed afterwards
   leaves the approval valid, because what was approved is bound by the region and the process module's helper and not
   by the reviewer. This is an accepted risk and the spec and the decision record say so. (Added after round 3 of the
   decision record's review, at the owner's choice.)

## Completion criteria

1. A spec section and a decision record state the design above, the record format, the command surface, the order in
   choice 2 and the limits; the owner has read them and has accepted the decision record
   (`docs/decisions/2026-10-23-delegated-plan-approval.md` is `Status: Accepted`). The acceptance is the owner's act
   and is a prerequisite of increments B to F.
2. The `review-engine` module declares and answers `convergence`: sealed and not rolled back, kind `plan`, last round
   converged, rounds within the bound, the round's document hash, bridge and model; it prints nothing it cannot
   verify.
3. The `code-work` module declares and answers `approval.delegable`: delegable or not, with a short reason, from the
   plan's Risks section.
4. `wb delegate-approve-plan <plan>` refuses unless: the personal setting for `approve-plan` is exactly `delegate`; the
   one process module and one `peer-review` provider are installed, approved and pinned and answer as declared; the
   plan is delegable; the file's hash equals the review's last round; the file did not change during the check; and it
   writes one record that holds the delegate, rounds and review pointer. Every refusal writes nothing.
5. `wb plan-status` and the edit gate read a delegated approval as `approved`, and `changed since approval` when the
   region, the process declaration or the helper differs, exactly as for an owner approval, and only while the
   personal setting for `approve-plan` is `delegate` (choice 8). A tampered record is no approval.
6. No other checkpoint is affected by a `delegate` setting; a missing, project-supplied or malformed setting is
   `stop`.
7. A `security-review` pass with adversarial verification has run, its findings are fixed or recorded, and the specs say
   what is built; the full suite passes in every root with no new skip; the package approvals are released by the
   owner.

## Increments

### Increment A — Specification and decision record

**Outcome:** the owner can read, and accept or change, the design before any code is written.
**Dependencies:** none.
**Affected areas:** `docs/specs/trust-and-approval.md` (Delegated approval, Plan approval records, Checkpoint and cap
settings), `docs/specs/code-work.md` (the plan-approval and checkpoints sections), `docs/specs/review-engine.md`
(the `convergence` argument), `docs/specs/module-contract.md` (the two new declaration fields),
`docs/specs/installer-interface.md` (the command), a new `docs/decisions/2026-10-23-delegated-plan-approval.md` with
`Status: Proposed`.
**Steps:**
1. Write the spec text: the command and its refusal order; the facts each declared command reports (name, shape,
   bounds); the record's `delegate` object and format 2; the effective-value rule for `approve-plan`; the order of
   choice 2; what a reviewer steered by the plan can and cannot do; limits.
2. Write the decision record with the alternatives (module writes the record; region-bound review; project-level
   switch) and the consequences, as `Status: Proposed`. Accepting it is the owner's act: I never change it to
   `Accepted`. The owner may change the design, and the plan, before accepting.
3. Run `doccheck`, `refcheck`, `git diff --check`.
4. Stop. Increments B to F do not start until the owner has accepted the record and says "start".
**Verification:** the document checks print nothing; the owner has read the spec and the record. No review unless the
owner asks.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-delegated-approval#A`. The acceptance is shown by the
record's status line when increment B starts; if the owner declines or changes the design, this plan is revised or
`Superseded` and B to F do not run.

### Increment B — The provider's convergence argument

**Outcome:** a `peer-review` provider can state, from its sealed state, whether the last review of a plan converged,
and the installer has the declaration to ask it.
**Dependencies:** A, and the owner's acceptance of the decision record.
**Affected areas:** `packages/workbench/review-engine/` (declaration, helper, tests); `docs/specs/review-engine.md`.
The declaration field (name fixed in A) is added to the contract check in `workbench/`, which names no module.
**Steps:**
1. Tests first: the argument prints one JSON object of exactly the documented fields, within the documented bound;
   it refuses a document that is not a plan, has no review, is unsealed, rolled back or unreadable; it reports
   `converged` false when the last round has a meaningful finding, when a finding is pending, when no round exists
   and when the bound is exhausted without a clean last round; it reports the last round's document hash, bridge,
   model (or null) and the number of rounds; it writes nothing; it is not in the `owner` list (an agent may run it)
   and the drift test pins that; the contract check accepts the field on a `peer-review` provider and refuses it
   elsewhere or naming an unknown command or argument.
2. Implement the argument as a read over the existing load path, and the contract check.
**Verification:** the module tests; the installer's contract tests; `tests.test_boundary`; document checks.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-delegated-approval#B`. The package tree changes, so its
approval is stale until increment F.

### Increment C — The process module's delegability argument

**Outcome:** `code-work` can say whether a plan may be delegated.
**Dependencies:** A, and the owner's acceptance of the decision record.
**Affected areas:** `packages/workbench/code-work/` (declaration `approval.delegable`, helper, tests);
`docs/specs/code-work.md`; the contract check for the field.
**Steps:**
1. Tests first: the argument prints one JSON object (`delegable`, a reason of at most 200 printable characters);
   a plan whose Risks section has a line beginning `Hard stop:` (after any list marker and emphasis, case-sensitive) is
   not delegable, and one whose Risks section says "no push, no install, no secret" is delegable; a plan with no Risks
   section, an unreadable one, a duplicated one or one in an odd place is not delegable (fail closed); text outside the
   Risks section cannot make a plan delegable or not; a link, an oversize file or a path outside `docs/plans/` is refused;
   the field is accepted only as one of the declared command's arguments.
2. Implement over the reader `region` already uses. The marker is the one the spec states (`code-work.md`,
   "Delegability"); a plan that omits it still stops at the action.
**Verification:** the module tests; contract tests; `tests.test_boundary`; document checks.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-delegated-approval#C`. The package tree changes, so its
approval is stale until increment F.

### Increment D — The installer's command and record

**Outcome:** `wb delegate-approve-plan` approves a plan on the conditions of criterion 4 and writes the record.
**Dependencies:** B, C (and so the owner's acceptance of the decision record).
**Affected areas:** `workbench/` (the command, the approvals file reader and writer, the effective-values rule for
`approve-plan`) and `tests/`; `docs/specs/installer-interface.md`.
**Steps:**
1. Tests first, with a fake process module and a fake provider installed as real pinned modules, as the existing
   `approve-plan` and gate tests do: each refusal condition writes nothing and says why (setting not `delegate`, setting
   from anywhere but the personal settings, zero or two process modules, no provider, a provider or process helper
   edited since its pin, an answer of the wrong shape, size, type or exit code, a timeout, not delegable, not
   converged, a hash that differs, a rolled-back or unsealed review, a plan that changes between the first hash and the
   last check, a link or an oversize plan); a delegate record is written once, holds the delegate and the rounds and
   the review pointer, and a second call writes nothing; `plan-status` and the gate read it as `approved`, and as
   `changed since approval` after any change; the same entry reads `not approved` with its reason once the setting is
   `stop`, missing or damaged, and `approved` again when it is `delegate`, while an owner entry is unaffected by the
   setting; a provider changed or removed after the approval does not change the reading; format 1 files are read and a format-2 file is written; a tampered
   or truncated file is no approval; `wb settings` shows `delegate` only for `approve-plan`; the command is not in the
   owner-run list and its rendering is pinned by the drift test; the boundary test passes with no module word.
2. Implement the command, the reader and writer for format 2, and the rule.
**Verification:** the installer suite; `tests.test_boundary`; document checks. The installer approval and any package that
pins the kit number are checked at the suite run; a stale record is the owner's release.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-delegated-approval#D`.

### Increment E — Guidance for the agent

**Outcome:** an agent knows when it may ask for a delegated approval and when it must wait for the owner.
**Dependencies:** D.
**Affected areas:** the neutral skills of `code-work` (the increment loop and plan skills) and their tests;
`docs/specs/code-work.md`.
**Steps:**
1. Tests first: the skill text says to run `wb settings` first and to use the delegated command only when
   `approve-plan` shows `delegate`; to run it after the converging round and before writing the review record; that
   a refusal is reported and not worked around; that every other checkpoint still stops; that the owner's word and
   `wb approve-plan` remain the other way. It names no harness and no vendor.
2. Write the text.
**Verification:** the skill tests; boundary test; document checks.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-delegated-approval#E`. The package tree changes, so its
approval is stale until increment F.

### Increment F — Security pass, record, release and close

**Outcome:** the security pass is done, the specs say what is built, the approvals are released, the plan records it.
**Dependencies:** A to E (and so the owner's acceptance of the decision record).
**Affected areas:** the specs' "as built", the decision record's Verification list, the package approvals (owner-run),
this plan's Result.
**Steps:**
1. With the owner's word, run a `security-review` pass with adversarial verification over B to D (hostile plan text,
   hostile provider and process answers, a swapped file, a replayed or copied review state, a forged or edited
   record, the setting source). Fix findings with a regression test each; the fixes are new surface and want a second
   look if the owner asks.
2. Update the specs. Run the full suite. If it reports an approval stale or absent, stop and ask the owner for
   `release-approvals`; preview any stale record and delete it only after "remove them". Run the suite again.
3. Run `doccheck`, `refcheck`, `git diff --check`. Fill the Result, including what ran against a fake and what ran
   against a real vendor. Set `Status: Completed` only after every criterion has its evidence.
**Verification:** the full suite with no new skip; the document checks print nothing.
**Evidence:** the one local commit (specs, plan, refreshed approval records), trailer
`Plan: 2026-10-23-delegated-approval#F`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots; `git diff --check`, `doccheck` and `refcheck` print
  nothing; `tests.test_boundary` is green.
- This plan moves authority, and touches untrusted input, a record in the guarded store, a model's output as a
  fact and a subprocess hop, so a `security-review` pass with adversarial verification is required before it is
  closed (increment F). I run it only when the owner asks.
- A hand run is possible and not planned: the owner sets `approve-plan` to `delegate`, runs a real review of a throwaway
  plan to convergence, and runs the command. Until then the approval is shown only against a fake provider and a fake
  bridge.

## Risks and sensitive actions

- **This transfers authority from the owner to a second model.** A plan written to steer the reviewer can get a clean
  review; the reviewer and the author can share a blind spot (`trust-and-approval.md`, Residual risk). The controls are
  the owner's personal setting, the clean last round of a sealed review, the delegability check, the hard stops
  that stop at the action, and the gate's reading of the record. None of them makes a delegated approval as strong as
  the owner's. The spec says so.
- **A forged or replayed review.** An agent could edit a state, restore an older one or copy one from a clone. The
  seal key and the rollback mark are in the guarded store, so the engine reports such a state as unsealed or rolled
  back and `convergence` refuses it. The key and mark are protected by the harness's deny rule, which is a mistake
  guard and not a boundary.
- **The file changes between the check and the write.** The installer hashes the plan before and after its checks and
  refuses on a difference; a change after the record is written invalidates it through the region hash.
- **A provider or process module that lies.** Both are approved, pinned modules, their output is validated and
  bounded, and the installer follows nothing in it; a module that misreports defeats the check as far as its
  owner-approved bytes go, as for the region command.
- **The setting.** `delegate` is read from the personal settings in the guarded store only. A committed file, a plan or
  a review cannot supply it. A damaged settings file reads as `stop`.
- **The approvals file format changes.** A format-2 file is refused by an older workbench (fail closed). The reader
  accepts format 1.
- **An installer change.** Increment D changes mechanism shared by every project. It is generic, tested, and the
  boundary test guards the vocabulary.
- **The package trees and approvals.** B, C and E stale three package approvals and D stales the installer's; the owner
  releases them at F.
- No push, no install into a project, no real vendor call, no secret, and no deletion beyond stale approval records.

## Review record

Increment A's own decision record, `2026-10-23-delegated-plan-approval`, was reviewed in three rounds of
`ask-codex review-adr` and accepted by the owner on 2026-10-23; its Review record has the findings. The review of this
plan follows.

Round 1 of 3, 2026-10-23, `ask-codex review-plan`, model `gpt-5.6-luna`, effort medium (asked for by the owner).
Outcome: changes needed; one major finding, applied. No second round was run.

- R1-F1 applied. The plan left the new decision record `Proposed` and asked only that the owner read it, while
  increments B to F build on a design that resolves a disagreement between two specs about who may write delegated
  approvals; a proposed decision cannot authorize that, and accepting a decision is the owner's act. Completion
  criterion 1 now requires the owner's acceptance of `docs/decisions/2026-10-23-delegated-plan-approval.md`; increment A
  stops after writing the record as `Proposed`; B, C, D and F list the acceptance as a dependency; and a declined or
  changed design means the plan is revised or superseded.

The review is not an approval; the plan stays `Proposed` until the owner approves it.

## Deferred work

- Delegating the other checkpoints, one plan each, starting with `push-shared-branch`.
- A read-only report of who approved each plan (the record holds the facts).
- A personal setting for the reviewer's bridge, model and effort (`review-engine` reads the project file only).
- A hand run of the whole path against a real vendor, if the owner wants one recorded.

## Result

### Increment A — Specification and decision record

- Committed as `c73837d`, trailer `Plan: 2026-10-23-delegated-approval#A`. Documents only; no package changed, so no
  approval is stale.
- Written: the decision record `2026-10-23-delegated-plan-approval`, reviewed in three rounds of `ask-codex review-adr`
  (four findings, all applied; the third round's fix was not re-checked, the bound being used) and accepted by the owner
  on 2026-10-23; the spec sections in `trust-and-approval.md` ("Delegated plan approval records"), `code-work.md`
  (delegability, the writer's move to the installer), `review-engine.md` ("Convergence"), `module-contract.md` (the
  fields `approval.delegable` and `convergence`) and `installer-interface.md` (the command); the decisions index.
- Plan edits made at the owner's approval during A: increment C's marker (`Hard stop:`) replaces a keyword list, choice
  6 states the `wb settings` output change, and choice 8, criterion 5 and increment D's tests add the rule that a
  delegated entry counts only while the setting reads `delegate` (the provider-drift risk is accepted).
- Wording found by review and corrected in the specs: the review engine records the reviewer's verdict and its reading
  as data and records no approval; a module writes to the store (the review engine's key, marks and lock) but never a
  plan approval record. The Goal above still says "records no verdict" and was not reworded.
- Not done: any code. The ADR review is not archived (owner's `ask-codex archive`). No security pass yet (increment F).
- Next: increment B (below).

### Increment B — The provider's convergence argument

- One local commit, trailer `Plan: 2026-10-23-delegated-approval#B` (find it with `git log --grep`).
- Built: `review-engine convergence <document>` (helper, read-only, no lock, no write); the `convergence` declaration
  field and its check in `workbench/declarations.py` (refused on a module that does not provide `peer-review`, with a
  command or argument the module does not declare, an unknown key or a wrong type; part of the declaration hash); the
  module's `module.json` (thirteenth argument, not owner-run, and the field); the specs (`review-engine.md`,
  `module-contract.md`, `trust-and-approval.md`).
- Tests: 41 new in `test_review_convergence.py`, one new and two changed in `test_review_module.py`, six new in
  `tests/test_declarations.py`. The full suite passes, 3,515 tests in 7 roots (3,468 before). Document checks print
  nothing. Eight changes to the rules in turn (no pending check, no bound check, no verdict and reading check, no
  meaningful-finding check, the first round instead of the last, all rounds counted as used, an unsealed state
  accepted, no check of a window with no round) each failed a test; the two that first survived led to a better test.
- Differs from the plan's test list: a review with no round, or none in its current window, is refused and does not
  print `converged` false, because the object needs the hash of a file a round read. The stored round files are not
  re-read; the sealed state names each round by hash. The skill `peer-review` does not mention the argument and its
  test excepts it until increment E.
- Not done: the process module's `delegable` (C), the installer (D), guidance (E), any security pass or release (F). The
  package approval of `review-engine` is stale until F, so `wb run review-engine` will not run in an installed project
  until then.

### Increment C — The process module's delegability argument

- One local commit, trailer `Plan: 2026-10-23-delegated-approval#C` (find it with `git log --grep`).
- Built: `code-work delegable <plan>` (helper, read-only; one JSON object `format`, `delegable`, `reason` of at most 200
  ASCII characters; exit 0 for every answer, refused with exit 1 for a path that is not a plan, a link, an unreadable or
  oversize file); the `approval.delegable` field and its check in `workbench/declarations.py` (a string, an argument of
  the command, different from `argument` and `active`; part of the declaration hash); the module's `module.json`; the
  specs (`code-work.md`, `module-contract.md`).
- Tests: 48 new in `test_codework_delegable.py`, one changed in each of `test_codework_module.py` (two assertions), five
  new in `tests/test_declarations.py`. The full suite passes, 3,568 tests in 7 roots (3,515 before), the same skips.
  Document checks print nothing. Thirteen changes to the helper in turn (case-insensitive marker, no emphasis before or
  after the word, no list markers, a section ended by any section start, markers counted in fences, several sections
  allowed, an inexact heading allowed, the marker read from the cut line, an unclosed fence ignored, no setext heading
  counted, no status check, hidden headings counted) each failed a test; a fourteenth (no cut of the reason) cannot
  change any answer, because the only text it shortens is a fixed message. Four of five changes to the declaration check
  failed a test; the fifth (no string check) is the same refusal by another path.
- Differs from the plan: a section runs to the next level-one or level-two heading and a rule, an underline or a
  level-three heading does not end it (more lines are read, which can only withhold delegation); any heading a reader
  could take for the Risks section counts, so a second one in another case or form makes the plan not delegable; a
  header without exactly one `Status:` line is not delegable. All three are in the spec.
- Not done: the installer's command and record (D), guidance (E), the security pass and release (F). The package
  approval of `code-work` is stale until F, as is `review-engine`'s.

### Increment D — The installer's command and record

- One local commit, trailer `Plan: 2026-10-23-delegated-approval#D` (find it with `git log --grep`).
- Built: `wb delegate-approve-plan <plan>` (`workbench/delegation.py`, routed in `cli.py`, in `rules.AGENT_SAFE` and not
  owner-run); in `approvalcmd.py` the resolution of the one `peer-review` provider that declares `convergence` (held to
  the pin rules of `wb run`), the two commands `delegable` and `convergence` and their strict readers (1,024 and 4,096
  bytes); in `planapprovals.py` the format-2 record (formats 1 and 2 read, 2 written, an optional `delegate` object with
  exactly nine fields) and the reading rule (a delegated entry counts only while the personal `approve-plan` setting
  reads `delegate`; otherwise `not approved (delegated approval withdrawn: ...)`, the same reason at the gate); in
  `settings.py` the rule that `delegate` takes effect for `approve-plan` only (any other name stops, with a note in
  `wb settings`); the specs (`trust-and-approval.md`, `installer-interface.md`, `code-work.md`).
- Tests: 74 new in `tests/test_delegation.py` (a fake process module and a fake provider installed as real pinned
  modules, as the existing tests do), one new in `test_settingscmd.py`, two changed there (the checkpoint names) and
  one case changed in `test_planapprovals.py` (format 2 is now valid; formats 0 and 3 are the damaged ones). The full
  suite passes, 3,643 tests in 7 roots (3,568 before), the same skips. Document checks print nothing. Thirty-two
  changes to the rules in turn each failed a test; four first survived and led to better tests (the provider's hashes
  now differ from the process module's, a read-back test, and oversize answers that are otherwise valid).
- Differs from the plan: the installer reads the plan file once, as bytes, for its hash (the provider names the file it
  reviewed by that hash); the setting is checked after the process module is found, since the module declares the
  checkpoints; a project is never given two process modules by the install check, so the test for two uses a patched
  listing; `delegate` for another checkpoint reads `stop` with a note.
- Not done: guidance for the agent (E), the security pass, the release of the approvals and the close (F). The shipped
  approvals of the installer, `code-work` and `review-engine` are stale until F.

### Increment E — Guidance for the agent

- One local commit, trailer `Plan: 2026-10-23-delegated-approval#E` (find it with `git log --grep`).
- Built: the neutral skill `delegate-approval` in `code-work` (run `wb settings` first and go on only when
  `approve-plan` shows `delegate`; ask once with `wb delegate-approve-plan <plan>` after the converging round and
  before writing the review record; report a `refused:` line and stop; every other checkpoint still stops; the
  owner's word and the approve-plan command remain the other way; `Hard stop:` and a missing Risks section are for
  the owner). A one-sentence pointer to it in `draft-plan` and `run-increment`, each still leaving the approval to
  the owner. The specs `code-work.md` and `trust-and-approval.md` say it is built.
- Tests: 12 new in `test_codework_delegateskill.py` (the phrases, the order of the steps, the two commands named,
  no harness or vendor word, the pointers); the item lists in `test_codework_skills.py` and `test_codework_module.py`
  changed. The full suite passes, 3,655 tests in 7 roots (3,643 before), the same skips. Document checks and
  `tests.test_boundary` print nothing or pass. Fourteen changes to the text in turn each failed a test; three first
  survived (the Hard stop sentence, "once", the command limit) and are now pinned by phrases.
- Differs from the plan: the guidance is a new skill rather than text inside the existing ones, because the tests
  of `draft-plan` and of the loop skills allow no command beyond their own; those two skills carry a pointer only.
  The skill is advice: the installer's command is what gives or refuses the approval.
- Not done: the security pass, the release of the approvals, the "as built" updates and the close (F). The shipped
  approvals of the installer, `code-work` and `review-engine` are stale until F.

### Increment F — Security pass, record, release and close

- Not yet committed; the commit will carry the trailer `Plan: 2026-10-23-delegated-approval#F`.
- Security pass (owner's word given in session): an adversarial `security-reviewer` run over B to D on scratch copies.
  It ended partial: the hostile-helper-output experiments, an end-to-end run with fake executables that record what
  they receive, and the forged-record and race experiments did not run beyond the shipped tests (`tests.test_delegation`
  passed, 74 tests). Read-only checks and the shipped tests found the setting source, the pins, the record formats,
  the plan reader (FIFO, symlink, `..`, oversize) and the reading rule sound.
- Fixed, each with a regression test: (Medium) the `delegable` answer was not bound to the bytes it judged, so a plan
  swapped between the checks could be judged on other bytes; the answer now holds `document_sha256` and the installer
  refuses unless it equals the plan's hash; (Low) the `Hard stop:` marker was evaded by case, spacing, a hyphen, a
  heading or checkbox prefix; it now ignores those. Specs `code-work.md` and `trust-and-approval.md` say so; the
  `code-work` status line no longer says the delegation is unbuilt.
- Not fixed, for the owner: (Low) an equal entry is not added again whoever made it (the accepted decision's words), so
  after the setting is withdrawn the owner's own `approve-plan` for a plan with a delegated entry prints "already
  approved" and writes nothing, while the gate reads it as withdrawn; it fails safe, and a change contradicts the
  decision. (Low) a hardlinked plan is read. (Low) a pin made without a recorded declaration leaves the new manifest
  fields uncovered, as for every `wb run` field.
- Verification: the full suite passes, 3,656 tests in 7 roots (3,655 before), the same skips. Document checks and
  `git diff --check` print nothing.
- Second look (owner's word given in session): a second adversarial `security-reviewer` run, one round, on scratch
  copies. It found no bypass of the `document_sha256` binding: 30 hostile answers were refused (hash case and length,
  types, duplicate or extra keys, BOM, bad bytes, trailing data, size, depth, NaN, control and bidi characters), and the
  swap steps and record rules read sound. Two evasions of the `Hard stop:` marker, confirmed by running the helper:
  (Medium) a second Risks heading with emphasis or an entity (`## **Risks and sensitive actions**`) was not counted as
  a section, so a `Hard stop:` under it was missed; (Low) a marker hidden by an invisible or look-alike character, a
  full-width colon, a tag, an entity, a table cell, a heading prefix before a list marker or a split over two lines.
  Fixed with tests that failed first: the heading is compared as a reader sees it (`&` read as "and"), and the Risks
  section fails closed: a line with markup, an entity or any character other than printable ASCII and a tab makes the
  plan not delegable, and the marker also matches a table cell, either order of prefixes and a split over two lines.
  Cost: two of the 27 plans of this repository (`2026-10-19-installer-core-verifier`, `2026-10-20-base-and-manifests`)
  are no longer delegable because their Risks sections hold such text; they go to the owner, as before. The specs
  `code-work.md` and `trust-and-approval.md` say so.
- Not run in the second look: an end-to-end run with a fake executable that records its arguments, a concurrent swap,
  and hardlinked, FIFO and oversize plans beyond the shipped tests.
- Verification after the second look: the full suite passes, 3,661 tests in 7 roots (3,656 before; 333 in `code-work`),
  the same skips.
- Released: the owner had the approvals released after the second look (commit `fd788bc`); the stale records were
  removed after a preview.
- Real-vendor run: not done, and waived by the owner. The plan called it possible and not planned. Every run of
  `wb delegate-approve-plan` used a fake process module and a fake provider installed as real pinned modules, and no
  vendor bridge ran. A hand run, if the owner wants one, is: set `approve-plan` to `delegate`, converge a review of a
  throwaway plan, and run `wb delegate-approve-plan <plan>`.
- Differences from the plan, accepted by the owner:
  - B: a review with no round, or none in its current window, is refused instead of printing `converged` false. The
    stored round files are not re-read.
  - C: the section runs to the next level-one or level-two heading. Any heading a reader could take for the Risks
    section counts. A header without exactly one `Status:` line is not delegable.
  - D: the installer reads the plan once, as bytes. The setting is checked after the process module is found.
    `delegate` for another checkpoint reads `stop` with a note.
  - E: the guidance is a new skill, `delegate-approval`, with a pointer in `draft-plan` and `run-increment`.
  - F: the `delegable` answer gained `document_sha256`, and the Risks section check fails closed on markup and
    non-ASCII text. Two of the 27 plans of this repository are no longer delegable because of it.
- Known limits, accepted: an equal entry is not added again whoever made it, a hardlinked plan is read, a pin made
  without a recorded declaration leaves the new manifest fields uncovered, and the provider may drift after approval.
- Criterion 7 is met: the security pass and the second look ran, their findings are fixed or recorded, the full suite
  passes at 3,661 tests with no new skip, and the owner released the approvals.
- Closed: `Status: Completed`.
