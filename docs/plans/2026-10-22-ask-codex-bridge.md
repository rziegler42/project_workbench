# The model bridge: its contract, the module-to-module call, and the ask-codex bridge

Status: Completed
Created: 2026-10-22
Candidate: none — carries out the first part of the accepted decision `2026-10-22-model-calls-go-through-vendor-bridges`; the roadmap candidate `peer-review-provider` is split by increment E, so completion is not derived
Specs: model-bridge, module-boundary, trust-and-approval, terms, module-contract

## Goal

Build the bottom layer of the accepted decision: a written contract for a model bridge, the one new rule the
engines need (a helper may run another installed module's pinned command through the launcher), and the first
bridge, `ask-codex`, a first-party module that lets a workbench engine ask Codex a question read-only. The review
engine and the action-review engine are separate, later plans. This plan stops when a synthetic engine can call
the bridge end to end against a fake vendor program.

When this plan is done:

- `docs/specs/model-bridge.md` states contract version 1: the command, the input, the output, the error classes,
  what the vendor program may read, the guarantees, and a conformance checklist;
- a helper can run `wb run <command>` for a command another installed module provides, with the output bounded,
  the program found outside the repository, and the output treated as data, as `docs/specs/module-boundary.md`
  says;
- `packages/workbench/ask-codex/` is a first-party module that provides the capability `model-bridge` and the
  command `ask-codex ask`, and passes the conformance checklist against a fake `codex` program;
- no test starts a real `codex`, signs in, or reaches a network;
- the shipped approvals match, and the specs, roadmap and decision text say where this stands.

## Scope

- **The spec** `docs/specs/model-bridge.md`, indexed in `docs/specs/README.md`.
- **The call rule**: text in `docs/specs/module-boundary.md` and `trust-and-approval.md`, and the mechanism the
  rule needs (a kit function if the review of increment B chooses one, and whatever the launcher needs so that a
  helper's standard input reaches a helper it runs).
- **The module** `packages/workbench/ask-codex/`: `module.json` (type `module`, provides `model-bridge`, command
  `ask-codex` with the argument `ask`), the helper `helper/ask-codex`, and its tests.
- **A synthetic engine** in the tests only: a helper in a test fixture that calls the bridge through the launcher.
- **The release** of the shipped approvals (owner-run) and a review, including a security pass.
- **Docs**: the roadmap split of `peer-review-provider` (a direction edit), the term `model-bridge`, the guide, and
  the decision's Verification.

## Non-goals

- The review engine, the action-review engine, their settings files, or any review state. Those are later plans.
- Replacing or changing the owner's personal `ask-codex` tool, its state in `.debug/`, the approver hook, or
  anything in the owner's global Claude configuration. That belongs to `global-config-migration`.
- A second vendor. `ask-claude` and `ask-gemini` are later modules that pass the same checklist.
- A real call to Codex in any test, and any sign-in handling beyond reporting the error class.
- Choosing which bridge a project uses. That is the engines' setting (decision 5 of the accepted record).

## Assumptions and constraints

- Python standard library only; tests with `unittest`; the full suite is `python3 -B -W error tests/run_all.py`.
  It gains a sixth root, `packages/workbench/ask-codex/tests`.
- The installer and its tests must not name `ask-codex`, its helper or its paths (`tests/test_boundary.py`). The
  call rule is written for any command; the bridge is only named in the module's own files and tests.
- The capability name `model-bridge` has no prefix, so only the first-party package may provide it. A name is a
  proposal until the spec is accepted.
- Helper file names must be unique across modules (`tests/support_helpers.py` finds `packages/*/*/helper/<name>`).
- The bridge is written new, in the workbench's own words, from the contract in `docs/specs/model-bridge.md` and
  the accepted decision; those are the authority, and the plan depends on no file outside the repository. As
  background only, and not as an input anyone must read, the owner's personal review tool was seen on 2026-10-22 to
  start `codex exec` read-only with an ephemeral session, no user configuration, JSON output, a model and effort,
  an output schema and file, and the working root; to build a small allow-listed environment; to find `codex`
  only on a `PATH` entry outside the repository; and to sort failures into a few classes. The contract is
  written to say what the bridge must do, so a reader needs none of that.
- The vendor program reads the repository itself in the read-only sandbox; the prompt names the file. The
  contract must say so plainly, because the engines' safety rests on it.
- Discovery tooling: graphify: skipped — not installed in this project; the scope was found by reading
  `workbench/commands.py`, `workbench/launch.py`, the specs and the owner's tool.

### Choices (made by me; the owner may change any)

1. **Candidate: none.** The roadmap has no candidate for this exact slice, and splitting `peer-review-provider`
   is a direction edit that waits for the owner's approval of this plan (increment E).
2. **Spec first.** Increment A writes the contract before any code, as the accepted record says, so the bridge
   and the engines are built against the same text.
3. **The call mechanism is a kit function if it can be one.** Running a pinned command and bounding its output is
   mechanism every engine needs, not policy, so it belongs in the kit (additive, same API number) if that holds
   up in review. If it needs an API bump, the plan stops at increment B and asks the owner.
4. **The bridge takes its input on standard input and its options as flags**, and prints one JSON object. Which
   flags, and how a result shape is requested from the vendor, are fixed in increment A.
5. **The bridge is a thin translation.** It holds no round counter, no state and no policy, and writes nothing
   in the project.

## Completion criteria

1. `docs/specs/model-bridge.md` exists, is indexed, and states contract version 1 with a conformance checklist.
2. `docs/specs/module-boundary.md` and `trust-and-approval.md` state the rule for a helper that runs another
   module's command; a test shows that the command must be installed, declared and pinned, that the program is
   found outside the repository, that the output is bounded, and that a refusal runs nothing.
3. `packages/workbench/ask-codex/` verifies as a first-party `module`, provides `model-bridge`, ships only its
   helper, and `package.json` lists it.
4. Against a fake `codex` program, the bridge passes every item of the conformance checklist: read-only flags, a
   scrubbed environment, the program found only outside the repository, each error class, a timeout, an output
   that is too large, and an output that is not the declared shape.
5. A synthetic engine in the tests calls the bridge through the launcher and treats a hostile reply as data.
6. Installing the bridge pins its helper; an edited helper is refused; a command that no installed module
   provides is refused and nothing runs.
7. The full suite passes; the boundary test passes; no test starts a real `codex`.
8. The shipped approvals match the packages and the stale records are gone.
9. The specs, roadmap and decision text name where the bridge and the call rule live, and the roadmap shows
   `peer-review-provider` split to match the accepted record.

## Increments

### Increment A — The model-bridge contract

**Outcome:** the contract exists as a spec, so the bridge and the engines are built against the same text.
**Dependencies:** none.
**Affected areas:** `docs/specs/model-bridge.md` (new), `docs/specs/README.md`, `docs/specs/terms.md`.
**Steps:**
1. Write `model-bridge.md` with status `Draft`: purpose and non-goals; the declaration (type `module`, provides
   `model-bridge`, one command `ask-<vendor>` with the argument `ask`); the input (the prompt on standard input;
   the model, the effort, the timeout, the working root and a requested result shape as flags); the output (one
   JSON object with the reply, the vendor, the model, the usage, or an error class); the error classes, exactly
   the six the accepted decision names (not signed in, model unavailable, effort unsupported, vendor program not
   found, timeout, vendor error), with an optional `detail` code and a `retryable` flag, so a usage limit and an
   unusable reply are `vendor error` with a `detail` and need no class of their own; the guarantees (read-only, scrubbed environment, program found outside the repository, nothing
   written in the project, bounded output); what the vendor program can read; the contract version; the
   conformance checklist; acceptance criteria.
2. Say in the spec how a result shape is requested and checked, and that the engine validates the reply again.
3. Add the term `model bridge` to `terms.md` and the spec to the index.
**Verification:** the document checks (`doccheck`, `refcheck`) and `git diff --check` pass; the spec depends on no
file outside the repository, and every item of the checklist can be tested against a fake vendor program.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-22-ask-codex-bridge#A`.

### Increment B — A helper may run another module's command

**Outcome:** the rule is written and built, with tests on synthetic modules.
**Dependencies:** A.
**Affected areas:** `docs/specs/module-boundary.md`, `docs/specs/trust-and-approval.md`, `workbench/` (the
launcher path only if input must reach the helper), `workbench/wbkit/` (an additive function if chosen), tests.
**Steps:**
1. Check in the code whether standard input reaches a helper started by `wb run`, and whether its exit code and
   output come back; record the answer.
2. Write the rule: the program is `wb`, found on an absolute `PATH` entry outside the repository; the command name
   is checked against the pin store through the launcher, not by the caller; the arguments are literal; the
   output is read to a bound; a timeout kills the whole process group; the environment is scrubbed; the output
   is data.
3. Build it as a kit function if it fits the API number, else stop and ask the owner. Add the launcher change
   only if step 1 shows input does not reach the helper.
4. Tests on synthetic modules: the command runs; an uninstalled, undeclared or unpinned name is refused and
   nothing runs; a wrong argument is refused; output over the bound is cut and reported; a timeout is killed
   with its children; a `wb` placed inside the repository is not used; the environment holds no `GIT_*` or
   secret variable of the caller.
**Verification:** the new tests pass; the full suite passes; the boundary test passes.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-22-ask-codex-bridge#B`.

### Increment C — The ask-codex bridge module

**Outcome:** `wb run ask-codex ask` works against a fake vendor program and passes the checklist.
**Dependencies:** A, B.
**Affected areas:** `packages/workbench/ask-codex/` (new), `packages/workbench/package.json`.
**Steps:**
1. `module.json`: name `ask-codex`, version `0.1.0`, type `module`, provides `["model-bridge"]`, ships
   `["helper/ask-codex"]`, command `ask-codex` with `helper`, `runtime: python`, `kit: 1`, arguments `["ask"]`.
   No `requires`, `writes` or `fills`.
2. `helper/ask-codex`: read the options and the prompt; find `codex` only on an absolute `PATH` entry outside the
   repository; build the environment from an allow list; run `codex exec` read-only with the model, effort and
   result shape; read the output file to a bound; classify a failure into the contract's classes; print one
   JSON object. It writes nothing in the project.
3. Tests with a fake `codex` executable that records its arguments, environment and standard input: the exact
   argument list; the scrubbed environment; the program found outside the repository only; each error class from
   a sample error line; a timeout; an oversize output; an output not of the declared shape; an unexpected exit.
4. Launcher tests: install pins the helper; an edited helper is refused; another argument is refused; a
   synthetic engine helper calls the bridge through the increment B mechanism and treats a hostile reply
   (instructions, control characters, a huge field) as data.
5. Add `ask-codex` to `package.json`.
**Verification:** the new root passes (`PYTHONPATH=.:packages/workbench/ask-codex/tests python3 -B -W error -m
unittest discover -s packages/workbench/ask-codex/tests`); the full suite passes except shipped-approval tests that
need the release in D.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-22-ask-codex-bridge#C`.

### Increment D — Review and release

**Outcome:** the work is reviewed, findings are fixed, and the approvals match.
**Dependencies:** A, B, C.
**Affected areas:** `workbench/shipped_approvals/packages/`, fixes from the review.
**Steps:**
1. On the owner's request for a review (nothing starts one automatically), a `security-reviewer` pass over the call
   mechanism and the bridge, because they run a subprocess on a path the environment chooses and read a vendor's
   output: try to place a program inside the repository, widen the
   environment, overflow or hang the output, and make the engine follow an instruction in a reply. Likewise a
   `workflow-reviewer` pass over the whole plan. If the owner asks for neither, the plan records that, and the
   checks of A to C and the full suite are the verification.
2. Fix findings with regression tests; a fix is new attack surface, so when the owner asks, an independent reviewer
   tries to bypass it; if the owner does not ask, the regression tests and the checks of A to C are the
   verification. Record each review, or that none was asked for, in the Review record (the reviewer, the rounds, the findings applied or rejected with the
   reason, and anything left for the owner), and the implementation evidence in the Result.
3. After the owner says "Run it for me": `python3 -m workbench release-approvals`; after a preview and the owner's
   "remove them", delete the stale records.
4. Run the full suite.
**Verification:** `python3 -B -W error tests/run_all.py` is green and the shipped-approval tests pass.
**Evidence:** the review outcome in the Review record, the records added and removed and the suite counts in the
Result, in the one local commit, with the trailer `Plan: 2026-10-22-ask-codex-bridge#D`.

### Increment E — Specs, roadmap and decisions

**Outcome:** the documents describe the system as it is.
**Dependencies:** D.
**Affected areas:** `docs/specs/model-bridge.md`, `docs/specs/module-boundary.md`, `docs/development.md`,
`docs/roadmaps/workbench-v1.md`, `docs/decisions/2026-10-22-model-calls-go-through-vendor-bridges.md`.
**Steps:**
1. `model-bridge.md`: status `Current`, with an "As built, and its limits" section.
2. `development.md`: the command `wb run ask-codex ask` and what it needs (a `codex` program and a sign-in, which
   the tests never use).
3. Roadmap: split `peer-review-provider` into the review engine and the action-review engine, as the accepted
   record says, leave the bridge out of the candidates (done by this plan), and add this plan's outcome to the
   Current state. This is a direction edit and needs the owner's approval of this plan.
4. Decision: as `docs/decisions/README.md` provides for implementation evidence, fill only the Verification
   section of the accepted record for the parts this plan built, and leave the rest "not yet". No other part of
   the record changes; a change to what it decides would be a superseding record.
**Verification:** the document checks pass; the full suite passes; a search finds no document naming the old
single-module `peer-review-provider` outcome as current.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-22-ask-codex-bridge#E`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all six roots.
- The conformance checklist is passed by a test, item by item.
- `git diff --check` is clean and `git status` is clean after the last commit.
- A real call to Codex is **not** part of this plan; it is a hand run by the owner, after the engines exist.

## Risks and sensitive actions

- The bridge starts a subprocess on a path derived from the environment, and reads a vendor's reply. Both are
  boundaries: the program is found only outside the repository, the environment is an allow list, the reply is
  bounded and treated as data, and increment D gives them an adversarial pass.
- The call rule lets one helper run another module's command. That widens what an engine can reach, so the rule
  allows only a declared, installed, pinned command through the launcher.
- Sending project content to a vendor is the consent that installing a bridge gives. This plan builds only the
  bridge, and its tests use a fake program and send nothing.
- `release-approvals` rewrites the shipped approvals; it runs only on the owner's exact words, and the stale
  records are deleted only after a preview and the owner's "remove them".
- Nothing is pushed by this plan.

## Review record

Reviewed by Codex (`gpt-5.6-luna`, effort medium) on 2026-10-22, at the owner's request. Three rounds of a bound of
3; outcome: stopped at the bound, with nothing disputed. The last round's one finding was applied after the bound
was reached, so that fix has not been reviewed.

- R1-F1 (applied): the plan cited the owner's personal tool by a path outside the repository. The contract and the
  accepted decision are now the authority, and the tool's behaviour is background only, with no path.
- R1-F2 (rejected): filling the Verification section of an accepted decision. `docs/decisions/README.md` provides for
  implementation evidence there, and the accepted git-work decision was filled the same way. The step now says
  only that section changes and that a changed decision needs a superseding record.
- R1-F3 (applied): the contract added error classes beyond the six in the accepted decision. It now keeps the six
  and carries a usage limit and an unusable reply as `vendor error` with a `detail` and a `retryable` flag.
- R2-F1 (applied): independent reviews in increment D are run only when the owner asks.
- R2-F2 (applied): a review's outcome is recorded in the Review record, the implementation evidence in the Result.
- R3-F1 (applied): the follow-up review of a fix in increment D is also conditional on the owner's request.

The review is not an approval. The owner approved the plan on 2026-10-22, including the roadmap split in increment E.

Increment D reviews of increments A to C (commits `08d9d62`, `3969ddf`, `1d0db6c`), run on the owner's "start next
increment" on 2026-10-22: one round each, by a `security-reviewer` (with scratch experiments against fake programs)
and a `workflow-reviewer` (read-only). No Critical or High finding from either. Their findings are untrusted input
and were each checked against the code.

- S-L1 and W-2 (applied): the kit's search for `wb` used the project root as its boundary and string prefixes, so a
  project inside another repository, or a PATH entry spelled in another case, could be accepted. `call.py` now uses
  the outermost-`.git` boundary and the same-file walk that the bridge uses. A home directory that is itself a
  repository would make the guarded store look untrusted; nothing here has one, and the failure is a refusal.
- S-L2 (applied, stricter than the contract): `--root` inside `.git` or `.workbench` is refused.
- S-L3 and W-3 (applied): the temporary directory is checked before the scratch directory is made.
- W-4 (applied): a stdout past the bound is no longer forgotten when stderr speaks in the same moment.
- W-5 (applied): a `--root` the program cannot enter is refused, instead of reporting `program_not_found`.
- W-6 (applied): "401" counts as a sign-in problem only beside "status", "error" or "code", not in a path.
- S-I2 (applied): a count over 10^12 is null.
- W-1 (partly applied): the bridge now stops the program on SIGTERM. An outer SIGKILL of the caller's process group
  still leaves the program running, because the program is in its own session. S-I1 (a grandchild that starts its
  own session survives the group kill) is the same kind of limit. Both are to be written into "As built, and its
  limits" in increment E, with the rule that an engine's time limit exceeds the bridge's `--timeout`.
- Left for increment E as spec corrections: `--model` starts with a letter or digit; the schema is passed as a copy in
  the scratch directory; `--ignore-rules` is in the argument list; the trusted-path boundary is the outermost
  repository; the prompt may not be blank; the stale sentence that the launcher does not yet pass standard input.
- Left for the owner (W-7, S, not testable here): the Codex flags and error texts were checked against a fake only.
  The hand run should first run `codex exec --help`. Codex may also read the repository's own instruction files.
- Not acted on: S-I3 (no depth limit across `wb run`: every link is an approved pinned command, and the time limit
  ends a loop).

Regression tests for each applied finding are in `packages/workbench/ask-codex/tests/test_askcodex_run.py` (class
`Reviewed`) and `tests/test_kit_call.py`. The fixes have not been reviewed again, because the owner has not asked.

## Deferred work

- The review engine and the action-review engine, their settings files, and where the review state lives.
- `ask-claude` and `ask-gemini`.
- Retiring the owner's personal `ask-codex` and approver (`global-config-migration`).
- The hand run of a real Codex call through the bridge.
- A way for an enforcement point to obtain a commit's facts before it is made (open in the accepted record).

## Result

Increment D (2026-10-22): the reviews and their findings are in the Review record. After the fixes,
`python3 -B -W error tests/run_all.py` passes with 2785 tests in 6 roots (the ask-codex root has 90 tests). The owner
ran `python3 -m workbench release-approvals` on "Run it for me": it wrote 6 approvals for the first-party package, 5 of
them new directories under `workbench/shipped_approvals/packages/`, and reported 4 records that are no longer part of
the release; the owner then said "remove them" and those 4 directories were removed after a preview. Three tests in
the claude root that took the first module of the package for `claude` now pick it by name.

Increment E (2026-10-22): `docs/specs/model-bridge.md` is `Current` and has "As built, and its limits" (the spec
corrections, the SIGKILL and `setsid` limits, the rule that an engine's time limit exceeds `--timeout`, and the
flags and error texts not yet checked against a real Codex). `module-boundary.md` names the outermost repository as
the kit's boundary. `docs/development.md` has the `wb run --provides model-bridge ask-codex ask` row and a section on
what a real call needs. The roadmap splits `peer-review-provider` into `review-engine` and `action-review-engine`,
leaves the bridge out of the candidates, and records this plan's outcome in Current state. The decision's
Verification lists what is built and what is not yet. A search finds `peer-review-provider` only in this plan and in
the accepted decision's own words (its context, consequences and related files), which are not edited.

Left for the owner and for later plans: the hand run of a real Codex call (start with `codex exec --help`), the review
of the increment D fixes if wanted, the review engine, the action-review engine, a second vendor, and pushing the
commits (none of this plan is pushed).
