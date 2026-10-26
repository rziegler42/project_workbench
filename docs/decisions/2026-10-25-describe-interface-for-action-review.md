# A module that owns an action reports what the action would do through a read-only `describe` command

Status: Accepted by the owner on 2026-10-25
Date: 2026-10-25

## Context

Decision 7 of `2026-10-22-model-calls-go-through-vendor-bridges` says the facts for an action review come from the
module that owns the action, and leaves the interface open "until the action-review module is planned". The
design in `docs/specs/action-review.md`, approved by the owner on 2026-10-25, plans that engine and needs the
interface settled.

Today the owner's approver gathers those facts itself. For a commit and a removal it loads the global
`claude-workflow` program as a library (read on 2026-10-25, not run). That keeps the program from being removed
(move M14 of `global-config-inventory`) and keeps two copies of the inspection: the real command's and the
approver's. `safe-git` has a preview for `remove` only, and `push-check` for a push, which already has the right
shape. The interface must work for a commit that has not been made, without making it.

Constraints: a helper may start another module's pinned command only through the launcher (decision 4 of the
vendor-bridges record); the verdict authorizes nothing by itself (decision 6); the enforcement point stays in the
owner's configuration (`2026-10-24-project-guarantees-a-floor`); the module is standard library only.

## Decision

1. **Each module that owns a reviewable action ships a read-only subcommand `describe`.** It sits beside the action,
   takes exactly the arguments of the real command (`wb run safe-git describe commit ...` for `commit ...`), and
   reports what the real command would act on.
2. **It runs the real command's own validation code and nothing else.** It makes no commit, stages nothing, deletes
   nothing, writes nothing in the project and starts no program that the repository selects. A test per command
   shows that the repository is byte for byte the same after the call.
3. **Its output is one JSON object:** `contract` (a whole number), `action`, `ok`, `truncated` (always present, a
   boolean, false when the output is complete), `errors` and `facts`. An object that lacks any of these, or whose
   `truncated` is not a boolean, is malformed and approves nothing. `errors`
   holds the refusals the real command would give, as data: a commit the real helper would refuse is reported as
   `ok: false` with the reason, not as a failed run. `facts` is a flat set of named values. The module documents the
   names in its own spec, and states there a numeric cap on the serialized object in bytes and on each value, as
   `model-bridge.md` states its caps. The rule that this record fixes is the behaviour at the cap: a `describe` that
   would exceed it does not drop facts silently. It sets the top-level `truncated` to true and keeps in `facts` only
   whole values that fit, never a cut value. The engine treats `truncated: true` as incomplete, so its completeness
   check fails and the verdict is a decline. The numbers are the module spec's to choose; no `describe` may be built
   without them.

   **Field types, which the engine validates before it uses anything.** `contract` is a positive whole number the
   engine knows. `action` is a string equal to the action requested, so a response for another action is
   malformed. `ok` and `truncated` are booleans. `errors` is an array of objects, each with `code` (a string of at
   most 64 characters of `a-z0-9_`) and `message` (a string of at most 500 characters); `ok` is true only when
   `errors` is empty, and an object with `ok: true` and a non-empty `errors` is malformed. `facts` is a JSON object
   whose values are strings, whole numbers, booleans, null, or arrays of strings; no nested object and no other
   type. The names and meanings of the facts, and the exact allowed set for each, are the module's spec, which the
   engine's rule checks against. A field of the wrong type, an extra top-level field, a missing field or a response
   that is not one JSON object is malformed and approves nothing.
4. **The output is data.** It can carry text from a hostile repository (a diff, a message). The engine quotes it
   to its checks and to the model and follows nothing in it.
5. **The engine runs `describe` only through the launcher, and only the verb `describe`.** A rule names a module
   and an action, never a whole command line. The engine builds `wb run <module> describe <action> ...` itself, with
   the fixed word `describe`, so no rule can make it run `commit`, `remove` or any other verb. The command must be one
   the installer has pinned for an installed module, the launcher's existing rule for any helper that runs another
   module's command; an unpinned or edited helper is refused. A module's helper refuses a `describe` for an action it
   does not describe. The engine also accepts only a module that declares, in its module declaration, that it provides
   `describe` for that action, as `docs/specs/action-review.md` requires. The form of that declaration is not set
   here: it is settled in `module-contract.md` by the plan of the first increment, before any `describe` is built.
   Until then the fixed verb and the pin are the enforceable parts and are tested on their own. The engine writes no `allow` rule and no setting, and its verdict stands for the owner only as
   decision 6 allows.
6. **First users:** `safe-git describe commit` and `describe remove`. `remote-runner describe submit` and `fetch`
   follow once the remote-runner paragraphs move (M16). A push uses `push-check`, extended for the outgoing
   commits it does not yet report.

This record sets the interface and does not build it. The engine, the checks, the rules and the accuracy method
are in the spec.

## Alternatives considered

- **The engine inspects the action itself.** Rejected by decision 7: it rebuilds the owner module's inspection in a
  second place, which is the approver's present dependence on `claude-workflow` made permanent.
- **A `--preview` or `--dry-run` flag on the real command.** Rejected: a mistaken or dropped flag runs the action,
  and the preview shares the real command's code path, side effects included. A separate subcommand has no path to
  the action's effect.
- **The action reports its facts as it runs.** Rejected: the review must precede the action, and a report from the
  run is too late to stop it.
- **A generic `wb run describe <command>` in the launcher.** Rejected: the launcher would have to understand each
  module's arguments and facts, which is module content, not mechanism (`module-boundary.md`).
- **The hook calls each module's `describe` and passes the facts to the engine.** Not chosen: it puts the choice of
  facts in the owner's hook program, the place we want thin.

## Consequences

- Good: one copy of each action's validation, in the module that owns it. The approver's reading of the global
  `claude-workflow` program can end, so M14 can follow. A refusal is a fact the review sees.
- Good: the call is free of side effects by construction and testable by comparing the repository before and after.
- Bad: each action-owning module gains a subcommand, a spec section and tests. A `describe` that drifts from the real
  command would mislead the review. The mitigation is shared validation code and a test that the facts equal what the
  real command acts on.
- Bad: new surface. A helper starts another module's pinned command, and its output carries untrusted repository
  text to a model. A security pass is owed when it is built (decision 4, consequences).
- Bad: the facts for a commit contain diffs, which the model bridge sends to the vendor. That is the consent the
  owner gives by installing the bridge.
- Bad: two hops (the hook, the engine, then `describe` and the bridge) add time before a prompt can be answered.
  How long a review may take is open in the vendor-bridges record.
- Neutral: the form of the module's declaration that it provides `describe` for an action is not settled here. It
  is a question for `module-contract.md` and the plan of the first increment, and it blocks building any `describe`.

## Evidence

Read on 2026-10-25: the approver program's collectors for a commit and a removal (`load_helper`,
`collect_commit`, `collect_remove`), which call the global `claude-workflow` program as a library; `safe-git.md`
(`commit`, `remove`, `push-check`); `model-bridge.md`; the vendor-bridges record. Nothing was run. The interface
and the claim that it can reuse the real command's validation are proposals; no `describe` command exists.

## Review record

Reviewed by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-25, at
the owner's request: four rounds, the bound raised from 3 to 4 by the owner. Outcome: not converged. Each round
returned one to two major findings and all five were applied. They concerned the cap at the limit (R1-F1), the
launcher admission rule (R1-F2), the undefined `truncated` field (R2-F1), the disagreement with the action-review
spec over a declared provider (R3-F1) and the types of the remaining fields (R4-F1). The text added for R4-F1 was
not reviewed again. The owner accepted the record as written on 2026-10-25, knowing both facts. The acceptance is the
owner's, and a review is not an acceptance.

## Related files and decisions

- `docs/specs/action-review.md`, `docs/specs/safe-git.md`, `docs/specs/global-config-inventory.md` (M1, M14, M16, F-A1)
- [2026-10-22-model-calls-go-through-vendor-bridges](2026-10-22-model-calls-go-through-vendor-bridges.md)
- [2026-10-25-approver-coverage-for-the-module-commands](2026-10-25-approver-coverage-for-the-module-commands.md)
- [2026-10-24-project-guarantees-a-floor](2026-10-24-project-guarantees-a-floor.md)

2026-10-25 (clarification): the form of the declaration is settled in `module-contract.md`, by plan `2026-10-25-describe-interface-documented`.
