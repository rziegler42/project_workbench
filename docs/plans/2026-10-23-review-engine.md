# The review engine

Status: Approved
Created: 2026-10-23
Candidate: workbench-v1#review-engine
Specs: review-engine, model-bridge, module-contract, trust-and-approval, code-work

## Goal

`code-work` names a `peer-review` capability as a soft requirement, and `trust-and-approval.md` says a delegate may give
a verdict only when an installed, approved module provides it. No module does. The owner's second-opinion tool
(`ask-codex review-plan` and its siblings) lives outside every project, is tied to one vendor, keeps its sealed state in
untracked scratch, and so cannot be had by a teammate, cannot be depended on by a module, and cannot be built on by
`delegated-approval`.

The accepted record `2026-10-22-model-calls-go-through-vendor-bridges` (decisions 3 to 5) fixed the shape: a **review
module** that provides `peer-review`, requires `model-bridge`, holds the rounds, the sealed state, the findings schema,
`decide` and the owner-only `extend`, `reset`, `archive` and `prune`, knows no vendor, and runs a bridge only through
`wb run --provides model-bridge`. The first bridge, `ask-codex`, is built (plan `2026-10-22-ask-codex-bridge`).

When this plan is done:

- a first-party module `review` is installable, passes its own tests against a fake bridge, and provides `peer-review`;
- `wb run review review-plan|review-spec|review-roadmap|review-adr <document>` runs one bounded, read-only review round
  through the project's bridge and records the findings, and `status`, `decide`, `extend`, `reset`, `archive` and
  `prune` work as the owner's tool's do, with the owner-only ones refused to an agent by a rendered rule;
- a review's rounds, findings and decisions are kept in the project, sealed, and survive a clone;
- the specs say exactly what is built and what is not, and `delegated-approval` can be planned against them.

## Scope

- A new spec `docs/specs/review-engine.md`, written first and read by the owner (increment A).
- A generic way for a module's command to declare arguments that only the owner runs, rendered as `deny` rules in the
  agent's harness (increment B). It names no module.
- The module `packages/workbench/review/` with its declaration, helper, neutral skill and tests: document resolution,
  state, seal, ledger, the round, `decide`, `extend`, `reset`, `archive`, `prune`, the project setting
  `.workbench/review.json` (increments C to F).
- The specs' "as built" records, the package approval (owner-run) and this plan's Result (increment G).

## Non-goals

- Delegated approval. The engine gives findings and a recommendation only; it records no approval and no verdict
  (`delegated-approval`).
- A second bridge, a vendor name anywhere in the engine, or a model catalogue. The engine cannot list a vendor's models;
  the owner's `models` command is not carried over.
- The action-review engine, and any reviewer of actions.
- A personal setting for the bridge, model and effort (decision 5 of the accepted record). No helper can yet read the
  owner's personal settings; until one can, the project setting is the only source. This is a stated limit.
- Replacing the owner's `ask-codex` or removing it from `~/.claude`. That is `global-config-migration`.
- Any change to the loop caps `code-work` declares, or enforcement of them.
- Reviewing a document type the owner's tool does not review. The four kinds are plan, spec, roadmap and ADR.
- opencode.

## Assumptions and constraints

- A helper is a self-contained script, separately pinned, that imports only the standard library and `wbkit`, and
  starts another module's command only through `wbkit.call.run_command` with `provides="model-bridge"`
  (`module-boundary.md`). It cannot import `ask-codex`.
- `workbench/` and `tests/` hold only mechanism, and `tests/test_boundary.py` must stay green: the installer changes in
  increment B may name no first-party module, helper, command or harness.
- The bridge contract is `model-bridge.md`, contract version 1: one prompt on standard input, one JSON object back, the
  reply at most 262,144 bytes, the engine's own time limit larger than the bridge's `--timeout`, the reply untrusted.
  A bridge may read any file the vendor can open, so what is sent to a vendor can leave the machine; the engine keeps
  secrets out of what it points a vendor at, and the owner's install of the bridge is the consent.
- The owner's tool is the reference for behaviour, not for code: round bound 3 with ceiling 5, findings of four
  severities, `blocker` and `major` as meaningful, a `decide` record per finding, state sealed so an agent cannot lower
  a round count, and owner-only `extend`, `reset`, `archive` and `prune`. Nothing tracked cites its path; this plan
  describes the behaviour in its own words.
- Editing any file of a package tree changes its hash and stales its shipped approval. The release is the owner's
  (`release-approvals`, run by me only on "Run it for me"); stale records are removed only after a preview and
  "remove them".
- The guarded store (`~/.config/project-workbench/`) is the only place the agent's harness denies writes to
  (`trust-and-approval.md`). The project tree is writable by the agent, so a sealed state in the project is
  tamper-evident only if its seal key is outside the project.
- Discovery: graphify: skipped, not installed here; the scope was enumerated by reading the roadmap candidate, the
  accepted record, `model-bridge.md`, the bridge module and its synthetic engine test, the trust spec's delegation
  rules and the owner's tool's command surface.

### Choices (made by me; choice 1 was the owner's)

1. **State is kept in the project, sealed.** The owner chose this over the guarded store and over untracked scratch. A
   review lives in its own directory under `.workbench/workbench/review/` (the module's namespace), committed with the
   project, so a teammate and a fresh clone keep the history and a plan may cite a review by its closed summary.
2. **The seal is a keyed hash, with the key and a high-water mark in the guarded store.** The helper keeps a random key
   at `projects/<id>/review-seal-key` in the guarded store, made on first use with mode 0600, and seals each state file
   with an HMAC-SHA256 over its canonical JSON. The seal detects modification, not replay: an older state is still
   validly sealed. So the helper also keeps, beside the key, a mark per review of the highest count of rounds and of
   recorded decisions it has sealed, and a state below the mark is reported as rolled back and cannot run a round or
   be extended. A machine that has not seen the later state has no mark, so a rollback there is not detected. A state whose seal does not verify, or that has no key to verify with
   (a fresh machine), is reported as unsealed and cannot run a round or be extended; it can be read, and the owner may
   `reset` it. This catches an agent that edits a round count or restores an older state on the same machine; it does not
   stop an agent that can read the key or the mark, which are outside the project and under the harness's deny rule. A teammate's first run on another machine sees
   the committed state as unsealed: that is the price of choice 1, and the spec states it.
3. **A command declares owner-run arguments.** The module declaration gains an optional field on a command naming
   the arguments only the owner runs; the installer renders a `deny` rule for `wb run <command> <argument>` in every
   harness that provides `permissions`, the way it already denies `wb approve-plan`. The declaration authorizes the
   first argument only, so every owner-run form is a first argument of its own. `extend`, `reset`, `archive`, `prune`
   and `amend` are declared owner-run; `status`, the four review commands and `decide` are not. `decide` records a
   decision once and refuses a second call on the same finding; changing a recorded decision is `amend`, the owner's. The rule is restrictive only, is not a security boundary against a hostile agent (a spelling the
   pattern does not match), and the spec says so.
4. **The engine's settings are the project file only.** `.workbench/review.json` names the bridge command (one name),
   the model and the effort, with a format number. It is a request, never an authorization: the run is refused unless
   the named bridge is an installed, pinned module that provides `model-bridge` (decision 5 of the accepted record).
   No vendor is tried in place of a refused one.
5. **The module is named `review`**, its command `review`, its helper `helper/review`. The owner's tool keeps its own
   name; the two coexist.
6. **The state is data an agent may read.** Findings are model output, display-cleaned and bounded, and are never run
   or used as a path. An agent evaluates them as review comments (`evaluate-findings`).

## Completion criteria

1. `docs/specs/review-engine.md` exists, is read by the owner, and states the command surface, the findings schema,
   the round and cap rules, the state layout and seal, the setting, the owner-run arguments, the authority rules and a
   conformance checklist.
2. A command may declare owner-run arguments; the rendered Claude settings deny each, a drift test pins them, and the
   boundary test passes with no module word in `workbench/`.
3. The module `review` installs, provides `peer-review`, hard-requires `model-bridge`, and its helper passes the
   checklist against a fake bridge installed as a real pinned module: a round, `status`, `decide`, `amend`, `extend`,
   `reset`, `archive` and `prune`, with the bound, the ceiling, the seal, the rollback mark and the refusals tested.
4. A bridge that is not installed, not pinned, not a `model-bridge`, or an edited helper is refused and no other vendor
   is tried; a hostile reply (instructions, control characters, oversize, wrong shape) is data and changes nothing.
5. The specs ("As built") say what exists and its limits, the full suite passes in every root with no skip beyond
   today's, and the package approval is released by the owner.

## Increments

### Increment A — The review engine specification

**Outcome:** a spec the owner can read and approve before any code, as `model-bridge.md` was written before its bridge.
**Dependencies:** none.
**Affected areas:** new `docs/specs/review-engine.md`; one-line pointers in `terms.md`, `code-work.md` and
`trust-and-approval.md` where they promise or name `peer-review`; `docs/specs/README.md` if it lists specs.
**Steps:**
1. Write the spec: purpose and non-goals; the declaration (`provides` `peer-review`, `requires` `model-bridge` hard, one
   command with its arguments, the neutral skill); the findings schema (severity, location, claim, evidence, suggested
   change, bounds on each); the round (what is sent, what the reply must be, bounds, what counts as converged, how a
   failure is classified and whether it spends a round); the bound, ceiling and `extend`; the state layout, the seal and
   the key (choice 2) with the unsealed case; `decide`, `archive` and `prune`; the project setting (choice 4); the
   owner-run arguments (choice 3); what is sent to a vendor and how secrets are kept out; the authority rules (findings
   are advice; no verdict); a conformance checklist testable against a fake bridge; as-built limits.
2. Add the pointers; run `doccheck`, `refcheck`, `git diff --check`.
**Verification:** the document checks print nothing; the owner has read the spec. No review unless the owner asks.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-review-engine#A`.

### Increment B — Owner-run arguments

**Outcome:** a module command can name arguments only the owner runs, and the agent's harness denies them.
**Dependencies:** A.
**Affected areas:** `docs/specs/module-contract.md`, `trust-and-approval.md`; `workbench/` (the command declaration check,
the neutral rules, the Claude rendering) and their tests under `tests/`; `tests/test_boundary.py` unchanged.
**Steps:**
1. Tests first: a declaration with an `owner` list that is a subset of the command's `arguments` is accepted; a name
   outside it, a duplicate, a non-string or a non-list is refused; the rules for such a declaration are `deny`
   patterns for `wb run <command> <argument>` in each spelling of `wb` that the existing owner-run rules cover; a
   command with no `owner` list renders nothing new; a drift test pins the rule set; the boundary test stays green.
2. Implement the check and the rule generation. No module word may appear in `workbench/`.
3. Update the two specs. Run the installer suite and the boundary test.
**Verification:** the installer tests; `tests.test_boundary`; document checks.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-review-engine#B`. This increment changes the installer, so
the installer approval and every package that pins the kit number are checked at the suite run; any stale record is the
owner's release.

### Increment C — The module, the state and the seal

**Outcome:** `review` installs and can `init` and `status` a review; its state is sealed and read back safely.
**Dependencies:** A, B.
**Affected areas:** new `packages/workbench/review/` (`module.json`, `helper/review`, tests); the first-party
package list and distribution tests that enumerate modules.
**Steps:**
1. Tests first (against the real helper, run through the launcher as the bridge tests are): the declaration; document
   resolution for the four kinds (inside the project, a regular file, no link, bounded size, the right directory); the
   state directory name and layout; the seal key made once with mode 0600 in the guarded store; a state with a good
   seal read; with a bad seal, a missing key or a missing file reported unsealed; atomic writes; a lock against two
   runs at once; display-cleaning of every stored string; bounds on every field.
2. Write the helper's state layer and `init`, `status`. No bridge is called yet.
**Verification:** the module tests; `tests.test_boundary`; document checks.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-review-engine#C`. The package is new, so its approval is
absent until increment G.

### Increment D — The round

**Outcome:** one bounded review round runs through a bridge and records its findings.
**Dependencies:** C.
**Affected areas:** `packages/workbench/review/helper/review` and tests.
**Steps:**
1. Tests first, with a fake bridge installed as a pinned `model-bridge` module, as the bridge tests do: the prompt is
   built from the document and the instructions with the document marked as data; the bridge is run only through
   `wbkit.call.run_command` with `provides="model-bridge"` and an engine time limit larger than the bridge's; the reply
   must be one JSON object of the findings schema, validated again by the engine; each bound; a failure class
   (`not_signed_in`, `timeout`, `usage_limit`, an unusable reply) is reported and spends no round; a valid reply
   spends one and is stored; the bound of three rounds and the ceiling of five; a hostile reply (instruction text,
   control characters, oversize, wrong types, duplicate or out-of-range finding numbers) is data and changes nothing
   but the stored, cleaned findings.
2. Implement `review-plan`, `review-spec`, `review-roadmap` and `review-adr`, and the ledger the next round's prompt
   carries (what was applied or rejected, so a repeated finding is recognised).
**Verification:** the module tests; boundary test; document checks.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-review-engine#D`.

### Increment E — Decisions, extension, archive and prune

**Outcome:** the rest of the owner's command surface works, with the owner-run ones declared as such.
**Dependencies:** D.
**Affected areas:** `packages/workbench/review/module.json` (`owner` list), helper and tests.
**Steps:**
1. Tests first: `decide` records applied or rejected with a bounded reason for an existing, undecided finding and
   refuses an unknown one and a second call on a decided one; `amend` changes a recorded decision, keeps the earlier
   one in the ledger, and is declared owner-run while `decide` is not (the installer renders a deny rule for `amend`
   and none for `decide`); a state restored to an older sealed copy is reported as rolled back and runs no round; a pending finding blocks the next round until decided; `extend` grants one to five rounds and never
   beyond the ceiling; `reset` opens a fresh window; `archive` writes a closed summary and refuses a second round;
   `prune` previews and deletes closed reviews past retention only with `--apply`, and touches nothing it did not
   create; each owner-run argument is listed in the declaration and rendered as a deny rule by the installer.
2. Implement the six commands and the mark.
**Verification:** the module tests; the installer's drift test; boundary test; document checks.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-review-engine#E`.

### Increment F — The setting, the refusals and the skill

**Outcome:** the project names its bridge, a wrong one is refused, and an agent is told how to ask for a review.
**Dependencies:** D, E.
**Affected areas:** the helper and tests; `packages/workbench/review/harness/neutral/skills/peer-review/SKILL.md` and its
test.
**Steps:**
1. Tests first: `.workbench/review.json` is strict JSON with a format number, one bridge name, a model and an effort,
   bounded; a missing file means the one installed `model-bridge` if there is exactly one and a refusal otherwise; a
   named bridge that is not installed, not pinned, not a `model-bridge` or edited since the pin is refused and nothing
   runs; no other vendor is tried; the model and effort reach the bridge only as its documented options; a changed
   setting is shown by the state as a changed request.
2. Implement the setting. Write the neutral skill: when to ask for a review, the commands, that findings are advice, that
   `decide` records each, that `extend`, `reset`, `archive` and `prune` are the owner's, that secrets are kept out of
   what a vendor can read, and that the owner's word is the verdict. It names no harness and no vendor.
**Verification:** the module tests; the skill tests; boundary test; document checks.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-review-engine#F`.

### Increment G — Record, release and close

**Outcome:** the specs say what is built, the approval is released, the plan records it.
**Dependencies:** A to F.
**Affected areas:** `review-engine.md`, `model-bridge.md`, `code-work.md`, `trust-and-approval.md`, the decision record's
Verification list (a dated note, no change to its body); the roadmap candidate is not edited; the package approval
(owner-run); this plan's Result.
**Steps:**
1. Update the specs' "as built" and limits; state in `trust-and-approval.md` that `peer-review` is now provided.
2. Run the full suite. If it reports an approval stale or absent, stop and ask the owner for `release-approvals`; preview
   any stale record and delete it only after "remove them". Run the suite again.
3. Run `doccheck`, `refcheck`, `git diff --check`. Fill the Result, including that no real vendor and no live session
   was used. Set `Status: Completed` only after every criterion has its evidence.
**Verification:** the full suite with no new skip; the document checks print nothing.
**Evidence:** the one local commit (specs, plan, refreshed approval records), trailer `Plan: 2026-10-23-review-engine#G`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots; `git diff --check`, `doccheck` and `refcheck` print
  nothing; `tests.test_boundary` is green.
- This plan touches untrusted input, a model's reply, the filesystem, a key and a subprocess hop, so a `security-review`
  pass with adversarial verification is wanted before the plan is closed. I run it only when the owner asks.
- A hand run against a real Codex bridge is possible and not planned; until the owner runs it, the engine is shown only
  against a fake bridge.
- Global items this plan will let `global-config-migration` retire: the owner's `ask-codex` once a recorded run shows a
  project gets the same review from the module.

## Risks and sensitive actions

- **Content leaves the machine.** A review sends a document, and the vendor program may read more. The engine refuses a
  document outside the project or beyond its bound, tells the agent to keep secrets out, and relies on the owner's
  install of the bridge as the consent.
- **A reviewed document is hostile input.** It can try to steer the reviewer. The prompt marks it as data, the reply is
  validated, and nothing in a reply is run, followed or used as a path.
- **A bridge or a reply can lie.** A bridge is pinned and approved by the owner; the engine validates every field and
  trusts no claim of read-only behaviour. A forged verdict is impossible because the engine gives none.
- **The seal key and the mark.** They sit in the guarded store under the harness's deny rule, which is not a boundary
  against an agent that finds another way to read them. A leaked key lets a state be forged; the spec says so. The seal
  does not stop replay on its own: the mark catches a rollback only on a machine that has seen the later state. A fresh
  machine reports a committed state as unsealed (choice 2).
- **Committed state.** Findings text is model output committed to the repository: display-cleaned, bounded, and merge
  conflicts on a state directory are possible when two people review one document. The spec says how a conflict is
  resolved (the owner `reset`s).
- **Owner-run arguments are a rule, not a boundary.** A spelling the deny pattern does not match runs. The edit gate
  and the rendered rules are a mistake guard, as for the other owner-run commands.
- **An installer change.** Increment B changes mechanism shared by every module. It is small, generic and tested, and the
  boundary test guards the vocabulary.
- **The package tree and approvals.** The new package has no approval until the owner releases it; the installer change
  stales others.
- No push, no install into a project, no real vendor call, no secret, and no deletion beyond stale approval records.

## Review record

Round 1 of 3, 2026-10-23, `ask-codex review-plan`, model `gpt-5.6-luna`, effort medium (asked for by the owner).
Outcome: changes needed; two major findings, both applied.

- R1-F1 applied. The command contract authorizes the first argument only, so an owner list could not separate a new
  decision from an overwrite. `decide` now records once and refuses a second call on a decided finding; changing a
  decision is `amend`, a first argument of its own and owner-run. Choice 3 and increments B and E say so, and E tests
  that `decide` is allowed and `amend` denied. The owner's own practice treats `decide` as owner-only too; the accepted
  record lists only `extend`, `reset`, `archive` and `prune`, and I followed the record.
- R1-F2 applied. A keyed hash detects modification and not replay of an older valid state. Choice 2 now keeps a
  high-water mark per review in the guarded store, a state below it is reported as rolled back, and the plan states
  that a machine without the mark cannot detect a rollback. Increment E tests the restore case.

Left for the owner: whether `decide` should itself be owner-only (a one-word change to the owner list); approval; whether the plan should be split (the spec and the installer change are separable from the
module); whether the missing personal setting is acceptable as a limit; whether a decision record is wanted for the
owner-run declaration (choice 3) or the sealed state in the project (choice 2), which are the two choices a later plan
would be bound by.

## Deferred work

- A personal setting for bridge, model and effort, once a helper can read personal settings.
- A second bridge, and a second opinion from another vendor on one document.
- `delegated-approval`, built on this module's recorded convergence.
- An engine-side model catalogue, if a bridge ever offers one.
- Enforcement of the loop caps by the review loop.
- A hand run against a real vendor, and a live session check.
- Retiring the owner's `ask-codex` (`global-config-migration`).

## Result

Not started.
