# The review engine

Status: Completed
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

Increment A, 2026-10-23: `docs/specs/review-engine.md` is written (Status: Draft), indexed in `docs/specs/README.md` and
pointed to from `terms.md` and `code-work.md`.

- Verification as run: `doccheck`, `refcheck` and `git diff --check` print nothing. No test applies to a spec. The owner
  has not yet read it, and no review was run.
- Facts checked in the source while writing it, which the plan had assumed: a pinned helper is Python run as the owner
  and the kit passes `HOME` so a helper can reach the guarded store, but the kit has no store accessor, so the helper
  builds the path itself and depends on the store's `projects/<id>/` layout (the spec records this and a kit accessor
  as deferred). `wbkit.call.run_command` needs a command name and the kit cannot list installed bridges.
- Two places where the spec is narrower than the plan's wording, for the owner to accept or overturn: (1) increment F's
  test "a missing file means the one installed bridge" cannot hold, so the spec makes a missing or bridge-less
  `.workbench/review.json` a refusal that names the file, with no default bridge; (2) the prompt names the document by
  path, kind and hash and the vendor reads the files itself, so the prompt stays under 65,536 bytes and the document
  bound is 1,048,576 bytes.
- Not done: the owner's reading of the spec; no review.

Increment B, 2026-10-23: a module command may declare `owner`, the arguments only the owner runs, and an attached harness
that provides permissions denies the agent each one.

- Changes: `workbench/declarations.py` (the `owner` field, a subset of `arguments`, and `Command.owner` defaulting to
  empty so existing constructors still work), `workbench/rules.py` (`command_owner_patterns`: each argument bare, with
  more arguments and through `--provides`, in the five spellings), `workbench/harnessstage.py` (`owner_rules`, passed to
  `render_permissions`, which until now got an empty module rule list), `tests/test_owner_run_arguments.py` (23 tests),
  and the specs `module-boundary.md`, `module-contract.md` and `trust-and-approval.md`.
- Verification as run: the new tests failed first (unknown key `owner`, no `command_owner_patterns`), then passed. The
  full suite `python3 -B -W error tests/run_all.py` ran 3185 tests in 6 roots, OK (installer 2360 with 1 skip, ask-codex
  90, claude 32, code-work 268 with 2 skips, groundwork 178, safe-git 257); `tests.test_boundary` is green so
  `workbench/` names no module; `doccheck`, `refcheck` and `git diff --check` print nothing. No package tree changed,
  so no approval went stale.
- Facts found: the rendered rules depend on the modules installed when the harness was attached, so a module added
  later needs `wb attach` again; a harness without permissions enforces the arguments by instruction only; the
  patterns match command text and are a mistake guard, not a boundary.
- Not done: no review of this increment (only if the owner asks); no security pass yet (planned before close).

Increment C, 2026-10-23: the module `review-engine` exists with `init` and `status`, a sealed state, the key and the
rollback mark in the guarded store, a lock, atomic writes and a ledger. No bridge is called.

- Owner decision in session: the module, command and helper are named `review-engine`, not `review` (Choice 5 and the
  paths in the increments above say `review`; read them as `review-engine`). The boundary test refuses any module,
  command or helper name as a substring in `workbench/` and `tests/`, and `review` appears about 190 times there. The
  owner chose `review-engine`; the spec is edited in place, and one docstring in `tests/test_owner_run_arguments.py` was
  reworded because it named the plan stem.
- Changes: new `packages/workbench/review-engine/` (`module.json`, `helper/review-engine`, five test files, 73 tests),
  `packages/workbench/package.json` (the module is listed last, so the safe-git test "after groundwork" still holds), the
  module-list assertions in the claude, code-work and groundwork tests, and `docs/specs/review-engine.md` ("State",
  "The seal" and "As built, and its limits").
- Verification as run: the module tests passed on the first run, so five deliberate weakenings of the helper were tried
  (a seal that always matches, no rollback check, a lowered mark, a lock that follows links, a bad key replaced) and
  each made tests fail. The full suite `python3 -B -W error tests/run_all.py` ran 3258 tests in 7 roots, OK. Skips:
  installer 1, code-work 2, and 12 in the claude root because the shipped approvals are stale until the release in
  increment G (the package list changed, so the package hash did). `tests.test_boundary` is green; `doccheck`,
  `refcheck` and `git diff --check` print nothing.
- Decisions made in the code: `init` refuses a review that exists (a state file that is a link counts as existing);
  `status` of a document with no review is a refusal and never writes; a damaged or linked key is never replaced; the
  state is written before the mark; entries of `rounds` and `decisions` are checked only generically until D and E
  write them; the lock is one file per project, held without waiting.
- Not done: no review of this increment and no security pass (planned before close; this increment holds the seal key
  and mark code, the riskiest in the plan). Whether an upgrade or `wb check` leaves the review directory inside the
  module's namespace alone is not yet tested; it is checked in G with a real install. The approval for the new package
  is absent until G.

Increment D, 2026-10-23: `review-plan`, `review-spec`, `review-roadmap` and `review-adr` run one bounded round through the
bridge the project names and store the findings. Read together with Choice 5 as renamed in C (`review-engine`).

- Changes: `packages/workbench/review-engine/helper/review-engine` (the setting reader, the bridge-answer and reply
  validation, the prompt, the round, per-entry checks of `rounds`, a size check on save, `Failed`),
  `module.json` (the four arguments), the module tests (`support_bridge.py` and `test_review_round.py`,
  `test_review_findings.py`, `test_review_setting.py`, `test_review_prompt.py`, round-entry tests added to
  `test_review_state.py`, and C's tests moved to valid round entries), `tests/support_helpers.py` (registers the kit's
  `call` module so a helper under test and the test see one module), and `docs/specs/review-engine.md` ("The round",
  "State" and "As built, and its limits").
- Verification as run: the module tests, 188 in all, pass; they start the real `wb` launcher and the real first-party
  `ask-codex` bridge, installed and pinned from a copy of the package, against a fake `codex`. The full suite
  `python3 -B -W error tests/run_all.py` ran 3373 tests in 7 roots, OK (installer 2360 with 1 skip, ask-codex 90, claude
  32 with 12 skips for the stale shipped approvals until G, code-work 268 with 2 skips, groundwork 178, review-engine
  188, safe-git 257). `tests.test_boundary` is green; `doccheck`, `refcheck` and `git diff --check` print nothing.
  Eleven deliberate weakenings of the helper were tried (capability dropped, verdict unchecked, engine limit shorter
  than the bridge's, pending findings ignored, round-file hash unchecked, exit code unchecked, closed review ignored,
  bound off by one, no cleaning, unsealed state allowed to run, no lock) and each made tests fail. The round-file hash
  one first survived, because its test failed for another reason; the test was changed to alter a finding and keep the
  ids, and then failed under the weakening. I wrote the tests before the helper but did not run them red before
  writing it.
- Decisions made in the code, for the owner to accept or overturn: (1) the setting reader is built here, not in F,
  because a round cannot name its bridge without it; F keeps the skill and whatever the owner's review of D adds. (2) A
  round on a document with no review makes the review, as the spec says a round may make the key. (3) A failure is
  printed as a `refused:` line ending `no round was spent`, not as an object. (4) `schema.json` is written into the
  review's directory before the call and stays there after a failure (the bridge reads a schema only from inside the
  project); it holds no model output. (5) An undecided meaningful finding blocks the next round only inside the
  current window, so `reset` clears the way. (6) The lock is held for the whole round, up to 11 minutes, so another
  run of the engine is refused meanwhile; `status` takes no lock. (7) Decisions are read by the keys `finding`,
  `choice` and `reason`, which increment E must write. (8) A bridge-reported model is cleaned and cut to 200
  characters; a usage count above 2,147,483,647 is stored as null. (9) Earlier findings reach the next prompt cut to
  300 characters, and the oldest are left out when 65,536 bytes would be passed. (10) `status` still shows counts, not
  findings.
- Not done: no review and no security pass of D (planned before close); no run against a real Codex, so whether a real
  vendor accepts the schema file (which sets no length bounds) is untested; `decide` and the owner-run commands.

### Security pass over C and D

Two read-only reviewers ran experiments on scratch copies with a temporary home (the state, seal and filesystem; the
round, the bridge call and untrusted input). Their reports are untrusted input and were weighed one by one. No critical
or high finding. At the owner's word ("fix findings 1 to 4") four were fixed:

- A deleted `state.json` after sealed rounds read as "no review", so one more round could run and overwrote
  `round-1.json`. `load` now reports it as rolled back when the mark holds a round or a decision.
- A replayed older state with the same counts passed as sealed, which would reopen a closed review and undo a `reset`.
  The state now has a `generation` (raised by every save) that the mark keeps; a state below the mark's is rolled back.
  The state format gained a field and the mark one; no review exists outside the tests yet.
- The case or Unicode form of a path made another review (nine rounds for one file at a bound of three, found by both
  reviewers). The key and the path check now use a folded spelling. On a case-sensitive disk two files that differ only
  in case share a review; I judged that the smaller cost.
- A decision's `choice` reached the next prompt unbounded. It is now one of `applied` or `rejected`, anything else is
  read as `recorded`; `decide` (E) must also refuse any other choice when it writes.

Tests: 8 added (196 in the module); four deliberate weakenings (an absent state read as no review, the generation
ignored, the key not folded, any choice accepted) each made a test fail. Not fixed, recorded as limits in the spec: a
clone that copies the project's seed shares its store entries; a deleted mark file reads as no mark; a file swapped
during the bridge call; a bridge's grandchild in its own session surviving a timeout; and `wbkit.call` treating a
`PATH` entry that does not exist yet as outside the project (a kit change, not made). Not reviewed: `decide`, `amend`,
`extend`, `reset`, `archive`, `prune`, the real bridge and the deny-rule text against a real permission matcher.
Increment E must check decision entries one by one and refuse a second `decide`, and the owner-run list does not exist
until E.

### Increment E — Decisions, extension, archive and prune

- Changes: `packages/workbench/review-engine/helper/review-engine` (`decide`, `amend`, `extend`, `reset`, `archive`,
  `prune`, per-record checks of decisions, a richer ledger, `Guarded.remove_mark`, `save(override=)`),
  `module.json` (twelve arguments and the `owner` list `amend`, `extend`, `reset`, `archive`, `prune`), the module tests
  (`test_review_decisions.py`, `test_review_owner.py`, `test_review_prune.py`, and the declaration, state, command and
  round tests moved to valid decision records), and `docs/specs/review-engine.md` ("The commands" and "As built, and
  its limits"). The installer is unchanged: increment B's rule generation renders the deny rules.
- Verification as run: the module tests, 261 in all, pass. The full suite `python3 -B -W error tests/run_all.py` ran
  3446 tests in 7 roots, OK (installer 2360 with 1 skip, ask-codex 90, claude 32 with 12 skips for the stale shipped
  approvals until G, code-work 268 with 2 skips, groundwork 178, review-engine 261, safe-git 257). `doccheck`,
  `refcheck` and `git diff --check` print nothing. Sixteen deliberate weakenings of the helper were tried (a second
  `decide` allowed, an unknown finding allowed, `amend` dropping the earlier value, `extend` past the ceiling, `reset`
  keeping the old window, `archive` setting no time, a closed review changeable, an unsealed one changeable, `reset`
  not setting the mark, `prune` ignoring the retention, the seal, a foreign file or the key of the name, `prune`
  leaving the mark, a preview that applies, decision records unchecked) and each made tests fail. This time I wrote
  the helper before most of its tests; the mutation run is the check that the tests bite.
- Decisions made in the code, for the owner to accept or overturn: (1) the forms are `decide|amend <document>
  <finding> applied|rejected [--reason <text>]`, `extend <document> <n>` and `reset|archive <document>`; the spec's
  table had left the document out of them. (2) A decision is one record per finding with `earlier` values; `amend`
  rewrites it, so `decisions_total` counts findings, and at most 20 earlier values are kept. (3) A closed review takes
  no round, `decide`, `amend`, `extend` or `reset`; `archive` is final. (4) `reset` is also the way out of a state that
  is unsealed or rolled back or gone: it seals the state as it is (or an empty one) and sets the mark to its counts,
  lowering it, which is why it is the owner's; a state that cannot be read at all is not reset. (5) The closed summary
  is the ledger, which now lists every round and decision; there is no separate summary file. (6) Retention is 90 days
  after closing, and `prune` removes the review's mark with its directory so the document can be reviewed again.
  (7) `decide` takes a finding of any round of the review, not only the window's. (8) A reason is at most 2,000
  characters with no control character, and the ledger shows it without markup characters.
- Not done: the skill and the changed-request display (F); no review of E, and the security pass was before E, so the
  new commands (`reset` lowering the mark, `prune` deleting files) have had no independent look; no run against a real
  Codex.

### Increment F — The setting, the refusals and the skill

- Most of F's first step was already built and tested in D: the strict, bounded `.workbench/review.json`, the refusal
  of a bridge that is not installed, not pinned, not a `model-bridge` or edited since the pin, no other vendor tried,
  and the model and effort reaching the bridge only as its options (`test_review_setting.py`, `test_review_round.py`).
  F added what was missing.
- Changes: `status` prints a `request` field when the state could be used: `none` (no round yet), `same`, `changed`
  (the bridge, model or effort differs from the last round's request) or `unreadable` (the setting is refused; `status`
  does not refuse). Tests: `ChangedRequest` in `test_review_commands.py` (6 tests). The neutral skill `peer-review`
  (`harness/neutral/skills/peer-review/SKILL.md`) and its tests in `test_review_module.py` (a `Skill` class of 7
  tests: the reader accepts exactly the skill, the front matter, Claude's harness plan, no harness, vendor or tool
  named, exactly the four commands it runs and no other `wb` use, the rules, and every declared argument mentioned).
  The spec's status line and "As built" were updated.
- Verification as run: the module tests, 274 in all, pass. The full suite `python3 -B -W error tests/run_all.py` ran
  3459 tests in 7 roots, OK on the second run (installer 2360 with 1 skip, ask-codex 90, claude 32 with 12 skips for
  the stale shipped approvals until G, code-work 268 with 2 skips, groundwork 178, review-engine 274, safe-git 257).
  The first run had one failure in the installer root, `test_gate_hook.Tools.test_the_other_tools_field_is_not_read`
  ("the active command's report is not one line"); the whole `tests.test_gate_hook` module passed alone and the second
  full run passed, so it was not reproduced and its cause is not known. `doccheck`, `refcheck` and `git diff --check`
  print nothing. Five weakenings of `request_standing` and its use in `status` were tried and each made a test fail.
- Decisions made in the code, for the owner to accept or overturn: (1) the changed request is a field of `status` only,
  not of `init` or the owner commands, with four values. (2) The plan's "a missing file means the one installed
  `model-bridge`" was not built: there is no default bridge, as D decided and the spec says, since the kit cannot list
  installed bridges. (3) The skill lets the agent run `init`, `status`, a round and `decide`, and names the five owner
  commands only as the owner's.
- Not done: no review of E or F, and no security pass after C and D; no run against a real vendor.

### Security pass over E and F

- Two read-only `security-reviewer` subagents ran experiments on scratch copies of `b0211d5`: one on the owner commands
  and `prune`, one on untrusted text and increment F. Both stopped at their turn limit and were asked to finish, so
  not everything was checked: the real-launcher refusal tests, the launcher's handling of `--provides=` and `--`,
  multi-process races, case-insensitive disks, the harness translation of the skill, and a few size cases. No critical
  or high finding. Seven low items were reported.
- Fixed, each with a regression test that failed first (the module tests went from 274 to 283): `reset` of a state
  that was rolled back, unsealed or gone now prints `replaced` (the seal it had, what its file claimed, its counts,
  the mark lowered), because it can undo an archive and drop decisions (the spec had said it could not); `prune`
  skips a directory whose state cannot be read instead of refusing the whole run; the ledger heading passes the
  document path through the markup filter; the refusal for a damaged round file no longer names a `reset` that does
  not help; a generation at its largest says how the owner gets out; the skill no longer treats a plan's say-so as the
  owner's request, tells the agent not to paste model text into a reason, and not to edit the review's files.
- Not fixed, by choice: a bare web address in a decision reason is kept in the ledger as text (cosmetic). Recorded in
  the spec's limits: `reset`'s reach, the generation limit, the round-file refusal, the unreported skip in `prune`,
  and the markup replacement in the ledger.
- Verification as run: the full suite ran 3468 tests in 7 roots, OK (installer 2360 with 1 skip, ask-codex 90, claude
  32 with 12 skips, code-work 268 with 2 skips, groundwork 178, review-engine 283, safe-git 257); `doccheck`,
  `refcheck` and `git diff --check` print nothing (see the run below).

### Increment G — Record, release and close

- Specs: `review-engine.md` (status line, "As built" through G, the approval shipped, the result of the install check),
  `trust-and-approval.md` (`peer-review` is provided and gives findings only; the delegated record is not built),
  `code-work.md` (two lines), `model-bridge.md` (the review engine is the first engine to call the bridge), and a dated
  note in the decision record's Verification list, leaving its body as written.
- Approval: the owner said "Run it for me" and I ran `release-approvals`: 7 approvals for the package. Four stale
  records were previewed and removed on "remove them". The suite then found one test in the `claude` package that
  pinned the install order to five modules; I added `review-engine` to it, which changed the package hash, so
  `release-approvals` ran a second time (on "run it for me") and two more stale records were removed on "remove them".
  The `claude` root now runs its 12 tests that were skipped while its approvals were stale.
- Full suite after the last change: 3468 tests in 7 roots, OK (installer 2360 with 1 skip, ask-codex 90, claude 32
  with no skip, code-work 268 with 2 skips, groundwork 178, review-engine 283, safe-git 257). `doccheck`, `refcheck`
  and `git diff --check` print nothing.
- Real install, run by the owner in a scratch project (modules `review-engine`, `ask-codex`, `claude`): `install`,
  `init` and `status` of a review, `check`, `preview upgrade`, `upgrade`. The review stayed `ok` and its `state.json`
  kept the same hash. Finding: the installer treats the review's two files as changes made by others, so
  `preview upgrade` was refused until `wb acknowledge`; this is recorded in the spec's limits. The upgrade was a no-op
  (the package had not changed), so a changed package version over an existing review was not tried.
- No real vendor, sign-in or live session was used anywhere: every round ran against a fake vendor program. A hand run
  against a real Codex is not done. The engine's package approval and the installer's plan checks are shown; the
  security pass of C and D and the one of E and F found nothing critical or high, and their fixes have had no
  independent review.
- Open for the owner: push (the commits are local), `ask-codex archive` for this plan's review, whether `decide` should
  be owner-run, and the places where the spec is narrower than the plan (no default bridge; the prompt names the
  document and does not embed it).

### After close — hand run against a real Codex (2026-10-23)

Run by the owner in a terminal, step by step, in a scratch project; nothing here changed a package or an approval.

- `codex exec --help` (`codex-cli 0.163.0`) lists every flag the bridge passes. The bridge returned `ok` for a one-word
  prompt, `model_unavailable` for an unknown model and `timeout` for a 2-second limit.
- A `review-plan` round through `wb run`, the launcher and the bridge returned four findings on a plan with planted
  flaws, in the engine's schema, with matching line numbers; the seal stayed `ok`, the second round was refused until
  the findings were decided, and two `decide` calls and `status` behaved as specified. The ledger shows the decisions.
- The first attempt was refused because `wb` was not on `PATH`; the refusal named the cause and spent no round. The
  documented fix (`~/.config/project-workbench/bin` on `PATH`) worked.
- Findings, recorded in the specs: the bridge reports no model name and no token total with this version when no
  `--model` is given; the process tree after a timeout was not checked; `--effort`, a missing sign-in and a malformed
  real reply were not tried. No code or test changed.
- This replaces "a hand run against a real Codex is not done" above. The other open items for the owner stand, except
  the push, which was done.
