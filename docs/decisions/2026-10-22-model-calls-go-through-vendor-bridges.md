# Model calls go through thin vendor bridges; review and action review are separate engines

Status: Accepted by the owner on 2026-10-22
Date: 2026-10-22

## Context

The owner's personal tooling calls a second model in two places, both outside any project and both with the
Codex command line:

- `ask-codex` runs a bounded, read-only review of a plan, spec, roadmap or decision record. It owns a round
  counter, a sealed state, a findings schema and the owner-only `extend`, `reset`, `archive` and `prune`.
- The approver hook checks an action (a commit, a deletion, a push, a remote job) before it runs, from facts it
  collects, a rubric and a rule file, and returns a verdict.

Both start `codex exec` themselves, read-only, with a scrubbed environment, the executable found only outside
the repository, and their own handling of sign-in, model and timeout errors. Each repeats that code.

The owner expects other vendors later (a Claude or a Gemini equivalent) with the same behaviour. The roadmap
candidate `peer-review-provider` describes one reviewer module that takes a harness and a model setting. Four
accepted rules bound the design:

- Review is mandatory, and a verdict is an act of authority that a delegate may give only when the owner's
  personal setting is `delegate`, a `peer-review` provider is installed and approved, and review converged
  (`2026-10-19-mandatory-review-personal-delegation`).
- Neutral permission rules are restrictive only: the workbench writes `ask` and `deny`, never `allow`
  (`2026-10-19-restrictive-only-permissions`).
- A module's code lives in the module, and a helper is a self-contained, separately pinned script that cannot
  import another module's (`2026-10-21-module-code-lives-in-modules`).
- Approving a module is the owner's consent to what it does; sending project content to a vendor is such an
  act.

## Decision

1. **Three layers.** Vendor bridges at the bottom, engines above them, consumers on top.

   ```text
   consumers   code-work, any process module, an owner-configured hook
   engines     a review module (capability peer-review)    an action-review module
   bridges     ask-codex        ask-claude        ask-gemini      (each: capability model-bridge)
   ```

2. **A bridge is a thin module for one vendor.** It is named for the vendor (`ask-codex`, `ask-claude`,
   `ask-gemini`), has type `module`, and provides the capability `model-bridge`. It ships one command, run as
   `wb run ask-<vendor> ask`, and has no plans, no state and no policy. It takes a prompt on standard input and the
   options model, effort and timeout, and prints one JSON object: the reply text, the vendor, the model, the token
   counts, or an error class (not signed in, model unavailable, effort unsupported, vendor program not found,
   timeout, vendor error). It promises, and a test shows, that the vendor program runs read-only with a scrubbed
   environment, found only in an absolute `PATH` entry outside the repository, and that the bridge writes nothing
   in the project. Its contract and a conformance checklist are written in a spec, `docs/specs/model-bridge.md`,
   with a contract version, before any bridge is built.

3. **Two engines, each knowing no vendor.**
   - The **review module** provides `peer-review`, the capability the accepted rules already name. It holds the
     rounds, the sealed state, the findings schema (blocker, major, minor, nit), `decide`, and the owner-only
     `extend`, `reset`, `archive` and `prune`. Findings need no delegation.
   - The **action-review module** provides `action-review` (the name is a proposal; it is not
     `code-work-approval`, which is about plans). It holds a rubric and rules, takes facts about an action, and
     returns a verdict with reasons.
   Each requires `model-bridge` (hard). A project may install one engine without the other.

4. **An engine runs a bridge only through the launcher.** The engine's helper runs `wb run ask-<vendor> ask`, never
   an import. The launcher is found on an absolute `PATH` entry outside the repository, as git is found today.
   The bridge named must be an installed module that provides `model-bridge` and whose command is pinned; a name
   that is not refused and nothing runs. The bridge's output is data: the engine validates its shape, bounds its
   size, and follows no instruction in it.

5. **One bridge per setting, and the owner's choice wins.** Each engine reads its own project setting, a file
   named for the engine, `.workbench/<engine module>.json`, with a format number, as `.workbench/safe-git.json`
   is named for `safe-git`: project-owned configuration that the engine's module documents and reads, not a file
   the module installs, so the ownership and upgrade rules treat it like any project file. The setting names the
   bridge, the model and the effort the project would like. It is a default and a request, never an
   authorization:
   - A bridge runs only when it is an installed, pinned module that provides `model-bridge`, and installing it
     is the owner's approval to send content to that vendor. A project setting that names a bridge that is not
     installed and approved is refused, the run stops, and no other vendor is tried in its place.
   - The owner's personal setting is authoritative. It may choose among the installed bridges and may lower the
     effort; where it and the project setting disagree, the personal setting is used. A teammate with no
     personal setting gets the project's bridge, if it is installed and approved, and otherwise gets a refusal.
   - A pulled commit that changes the project setting is a difference `wb acknowledge` lists. At run time the
     setting is accepted only if it names a vendor whose bridge the owner has already approved by installing it.
   - The setting is a single name now; it can become a list later without breaking a reader of a single name.

6. **Authority does not move, and an action verdict is never actionable by itself.** The action-review module
   returns a verdict as data. It writes no `allow` rule and no setting, and it does not provide `peer-review`: it is
   a rubric and rules engine, not a reviewer of documents. Its output authorizes nothing on its own. It can inform
   an enforcement point that the owner configures (the hook, the permission rules, the hard-stop floor), which
   stays in the owner's own configuration and the compiled floor, outside every project's reach. Wherever its
   verdict stands in for the owner at a checkpoint, the accepted delegation rule applies unchanged: the owner's
   personal setting for that checkpoint is `delegate` (the default is `stop`), a plan with a hard stop in its
   risks is not delegable, and hard stops stop at the time of the action whatever any engine says. A verdict that
   is missing, malformed, unavailable, timed out or not a verdict yields no approval, and the action stops.
   Whether the accepted rule should name `action-review` beside `peer-review` is left to a superseding decision.
7. **Facts come from the module that owns the action.** The action-review module asks the module that owns the
   action for the facts, and does not rebuild that module's inspection in a second place. The interface for
   that is not defined here: `safe-git` has a preview for `remove` only, and a way to inspect a commit before it
   is made is a future decision, made when the action-review module is planned.
8. **Nothing is built by this record.** The owner's `ask-codex` and approver keep working as they do until the
   candidates below replace them.

## Alternatives considered

- **One module with an adapter table for every vendor.** One engine and one security pass, but consent to a
  vendor is no longer the module's approval, and every new vendor edits an approved module. Rejected in favour of
  bridges, which keep consent per vendor and make a new vendor a small module.
- **One full module per vendor, each with the whole engine.** Rejected: about 1,600 lines of hostile-input code
  copied per vendor, the same objection that rejected "each domain module writes its own" for git work.
- **Put the engine in the kit.** Rejected: the kit is mechanism every helper needs, and a review loop is policy
  (what counts as converged, what a finding is). It would also make the installer the owner of model-calling code.
- **Keep both tools owner-side only.** Rejected: a teammate cannot have them, and `code-work` needs a
  provider to name.
- **A project-level setting that grants the verdict.** Rejected by the accepted delegation rule.

## Consequences

- A new rule for module boundaries: a helper may start `wb run <command>` for a command that another installed
  module provides and the project has pinned. This is new attack surface and needs a security pass when it is
  built; the specs `module-boundary.md` and `trust-and-approval.md` change with it.
- The roadmap candidate `peer-review-provider` is split to match, and an action-review candidate is added;
  their order and contents belong to the roadmap and the plans.
- Two pinned hops cost a little time, and a bad bridge can lie about being read-only. The conformance checklist and
  each bridge's test with a fake vendor program are the guard, and the owner's approval of a bridge is consent to
  send content to that vendor.
- Choosing a vendor is a visible, acknowledged setting; a pulled commit cannot redirect content silently.
- The sealed review state now lives in a module's engine. Where it is kept is open; today it is in `.debug/`,
  which is untracked scratch, and a module must not depend on that.

## Open questions

- The capability names `model-bridge` and `action-review` are proposals.
- Where the review module keeps its sealed state and ledger.
- How an owner-configured hook obtains a verdict in good time, for example by running the action-review module's
  command.
- Whether more than one bridge per setting is ever wanted (a second opinion from another vendor).
- How an owner-side enforcement point gets the facts of a commit before it is made (see decision 7).

## Review record

Reviewed by Codex (`gpt-5.6-luna`) on 2026-10-22, at the owner's request; four rounds, the bound raised from 3 to 4 by
the owner after round 3. Outcome: converged.

- R1-F1 (major, applied): the project and personal settings did not say which wins. Decision 5 now makes the
  owner's choice authoritative and refuses a bridge that is not installed and approved.
- R2-F1 (major, applied): the setting had no owner or path. It is `.workbench/<engine module>.json`.
- R2-F2 (minor, applied): plan-level detail removed from the consequences.
- R3-F1 (blocker, applied): the record claimed a `safe-git` commit preview that does not exist. Decision 7 no longer
  does.
- R3-F2 (major, applied): decision 6 now says an action verdict is never actionable by itself and fails closed.
- R4-F1 (minor, applied): the control in decision 5 is a run-time refusal, not the acknowledgement alone.

The review is not an acceptance; the owner accepted the record on 2026-10-22, as written.

## Verification

Partly built by plan `2026-10-22-ask-codex-bridge` (increments A to E, 2026-10-22). The plans that carry it out show
a bridge passing the conformance checklist against a fake vendor program, an engine run against a fake bridge, a
refusal for a bridge that is not installed, pinned or a `model-bridge`, and the boundary test passing with the
installer naming no engine or bridge.

- **The contract (decision 2):** done. `docs/specs/model-bridge.md`, contract version 1, with a conformance
  checklist.
- **A bridge (decision 2):** done for one vendor. The module `ask-codex` passes the checklist against a fake `codex`
  program; no test starts a real one. A hand run against a real Codex is not yet done.
- **The launcher rule (decision 4, the consequence):** done. A helper runs another module's pinned command through
  the kit's `wbkit/call.py` and `wb run --provides model-bridge`. A synthetic engine in the bridge's tests treats a
  hostile reply as data and is refused for a command that no installed module provides, a module that does not
  provide the capability, an unpinned command and an edited helper. The security pass is recorded in the plan.
- **The boundary test:** passes with the installer naming no bridge or engine.
- **The review engine (decision 3):** not yet.
- **The action-review engine (decisions 3, 6 and 7):** not yet.
- **The engines' project setting and the owner's personal setting (decision 5):** not yet.
- **A second vendor (`ask-claude`, `ask-gemini`):** not yet.

Note, 2026-10-23 (plan `2026-10-23-review-engine`): the review engine of decision 3 is built as the module
`review-engine` (`docs/specs/review-engine.md`). It passes its checklist against the first-party bridge and a fake
vendor program, and refuses a bridge that is not installed, pinned or a `model-bridge`. It has not been run against a
real vendor or a live session. The entry for the engine above is left as written.

## Related files and decisions

- `docs/specs/code-work.md`, `docs/specs/trust-and-approval.md`, `docs/specs/module-boundary.md`,
  `docs/specs/terms.md`
- `docs/roadmaps/workbench-v1.md`: `peer-review-provider`, `code-work-approval`, `global-config-migration`
- [2026-10-19-mandatory-review-personal-delegation](2026-10-19-mandatory-review-personal-delegation.md)
- [2026-10-19-restrictive-only-permissions](2026-10-19-restrictive-only-permissions.md)
- [2026-10-21-module-code-lives-in-modules](2026-10-21-module-code-lives-in-modules.md)
- [2026-10-22-git-work-in-its-own-module](2026-10-22-git-work-in-its-own-module.md)
