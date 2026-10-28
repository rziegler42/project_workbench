# The owner-run arguments of a module's commands take a level, and the launcher enforces it

Status: Accepted by the owner on 2026-10-27
Date: 2026-10-27

## Context

`2026-10-26-a-level-for-every-command` (accepted) says in decision 3 that every key offers `block` and `none`, and that `ask` is offered
once a key has a preview digest. Its clarification note of 2026-10-27 says this does not yet hold for the owner-run arguments of module
commands (`wb run <command> <argument>` where the declaration lists the argument under `owner`): "their helpers check their own
terminal, and the module contract has no field through which the installer can pass a helper a level", and that giving it one is a
change to the module contract that needs a decision of its own. This is that decision.

What the code does today, read on 2026-10-27:

- The terminal test is in the launcher, not in the helper. `commands.owner_refusal` refuses an owner-run argument unless standard input
  and output are both terminals, and `wb run` and `wb launch` (through `launch_refusal`) both call it. The review engine's helper has
  no terminal test of its own. `docs/specs/command-permissions.md` says the helper checks its terminal; the code does not.
- The declaration lists `owner` as a list of argument names. The schema rejects an unknown field (`declarations._commands` uses
  exact keys), and the declaration hash covers the declaration as written, so a declaration without a new field hashes as before.
- `levels.registry` already makes the key `wb run <command> <argument>` for each owner-run argument, default `block`, and
  `rendering.key_patterns` already gives it patterns, so the rendering would produce an `ask` rule for it if the key offered `ask`.
  What is missing is the offer: `levels._OFFERS` is a fixed table and the installer may not name a module's command
  (`2026-10-21-module-code-lives-in-modules`).
- `levelrun` and the kit's `wbkit/levels.py` give installer commands `route`, `logged` and `done`; `apply_logged` writes an attempt
  line before a change and an outcome after it. Nothing of this reaches a module's command.
- The review engine changes a review under its own lock (`mutate` in its helper): it loads the state, checks it, makes the change and
  saves, all inside the lock. A check of a digest of that state is only sound inside the same lock.

The review engine's `extend`, `reset`, `archive`, `amend` and `prune` are the arguments that block the planning workflow when the
owner has no terminal (`command-permissions.md`, "The planning workflow without a terminal").

## Decision

Proposed. Nothing here is built; building it needs the plan `2026-10-27-levels-for-the-review-workflow` (Increments C to G), and
those increments wait for this record to be `Accepted`. **(call)** marks a choice the author made and the owner has not.

1. **The launcher stays the one place that reads the level and the terminal.** A module's helper is not told the level and does not
   test a terminal. The text of `command-permissions.md` is corrected to say so. **(call)**
2. **A declaration may give a command a `levels` field.** It is an object: each key is one of the command's `owner` arguments and
   each value is a list of the levels that argument offers beyond `block`, drawn from `ask` and `none`. `delegated` is refused: it needs
   a declared gate, and only `approve-plan` has one. A key that is not an owner-run argument of that command, a level that is not
   `ask` or `none`, a repeated level and an empty list are refused by `verify`. The field is optional, and a command without it offers
   `block` only, exactly as now. **(call: the field and its shape)**
3. **`ask` needs a preview the declaration names.** A command that offers `ask` for any argument also gives a `preview` field: the
   name of one of its declared arguments that is not owner-run, and not `describe`. `verify` refuses `ask` without it and `preview`
   without `ask`. That argument is the read-only preview. It takes the owner-run argument's name and that argument's own
   arguments (`preview extend <document> <n>`), changes nothing, prints what the argument would change and ends with a line
   `digest: <32 lowercase hex>`, the first 32 characters of the SHA-256 of that canonical text, as `wb plan-status --digest` does.
   Its key is `wb run <command> <preview>`, an ordinary declared argument that is not owner-run, so it defaults to `none`. **(call)**
4. **The helper checks the digest; the launcher requires it.** At `ask` and without a terminal, the launcher runs the argument only
   when its last two arguments are `--digest` and 32 lowercase hex characters, and it passes the arguments to the helper unchanged.
   It does not compute or compare the digest. The helper, inside the lock that guards the change, recomputes the digest of what the
   argument would change now and refuses, changing nothing, unless it equals the one given. A `--digest` given at a terminal is
   checked the same way; a run at a terminal without one works as before. **(call)**
5. **The level is read as `approve-plan`'s is.** Without a terminal, `ask` or `none` holds only while `rendering.effective_level`
   says so: the record, the table, the permissions file and the command gate agree and the key is listed. Anything else reads
   `block` and the launcher refuses with today's message. A level in the table that the declaration does not offer reads `block`
   with a note, as for any key.
6. **The launcher logs the run.** For a run without a terminal at `ask` or `none`, after every check and just before the helper is
   started, it writes an attempt line (key, level, `digest:<hex>` when there is one), and after the helper ends an outcome line:
   `done` for exit 0, and otherwise `refused` with the exit code. If the attempt cannot be written, the helper is not started. An
   interrupt after the attempt writes a `refused` outcome. A run at a terminal writes no entry, as for the other owner-run commands.
   The attempt must come after the pin and hash checks and before the helper starts. `launch.launch` does both in one function
   (`_prepare`, then `subprocess.run`), so building this changes `workbench/launch.py` (a callback or a split into prepare and
   start). Increment D of the plan already lists `workbench/launch.py` among its affected areas. **(call)**
7. **`wb launch` stays terminal-only for an owner-run argument, at every level.** The `ask` rule is rendered only for the
   `wb run` spelling (`rules.command_owner_patterns` has the heads `run` and `run --provides *`), and `launch` is an agent-safe
   word with no rule. If `launch_refusal` let a digest through, an agent could run the argument with no prompt, since it can read
   the true digest from the preview. So `launch_refusal` keeps refusing an owner-run argument without a terminal, as now, and only
   `wb run` reads a level. **(call)** The alternative, ask patterns for `wb launch`, is rejected below.
8. **What the digest binds, and how it is parsed.** The digest covers the review or object the argument changes and the argument's
    own operands (for `extend`, the number; for `amend`, the finding, the choice and the reason), so a digest for `extend <doc> 1`
    refuses `extend <doc> 5`. The preview takes the argument's name and operands (`preview prune --apply` for `prune`). The helper
    removes a trailing `--digest <hex>` before it counts its other arguments.
9. **The `ask` prompt inherits the spelling limit.** The rule is a best-effort text match (`2026-10-26-ask-level-spelling-limit`), and
    the agent can compute the digest itself, so a spelling the rule does not match is no longer stopped by the terminal test and is
    stopped only by the digest. The author recommends the owner keep `prune` and `reset` at `block` until the owner is content with
    that limit for them. The engine declares `ask` for them, and the owner sets the level per key.
10. **`none` is offered** by every argument whose declaration names it, for consistency with decision 3 of
   `2026-10-26-a-level-for-every-command`. At `none` no digest is required, the helper's own checks of its input apply, and the run
   is logged. The review engine declares `ask` and `none` for all five arguments, and the shipped default stays `block`. **(call:
   that the engine declares `none` too)**
11. **Nothing else changes.** No key other than the review engine's is given a level by this record. `mempalace init` and `mine` and
   `remote-runner fetch-overwrite` can declare the field later. The existing levels, defaults, the floor, and the rule that an
   unknown or stale rendering reads `block` are untouched. Setting a level and rendering it stay the owner's act at a terminal.

## Alternatives considered

- **Pass the level to the helper and let the helper use the kit's `may_run`.** This is what the clarification note and the spec
  assumed. Rejected: the helper would need the rendering record and the guarded store to read the level truthfully, which the kit
  does not read; and the check would be repeated in every module, so one flawed helper would silently defeat the gate for its
  arguments. The launcher already holds the test and the level logic.
- **The launcher runs `preview` itself and compares digests before launching the helper.** Rejected as the only check: the compare would
  be outside the helper's lock, so the state could change between the compare and the change. It stays possible as an extra check; this
  record does not require it.
- **Derive the offer from the presence of a `preview` argument, with no `levels` field.** Rejected: a change in what an agent may run
  should be a visible, hashed line of the declaration the owner confirms, not an inference from a name.
- **Turn `owner` into an object that carries the levels.** Rejected: every installed declaration and every parser of `owner` would
  break, where an additional optional field breaks none.
- **A table in the installer naming the review engine's arguments.** Rejected: the installer may not name a module's command
  (`2026-10-21-module-code-lives-in-modules`).
- **Ask patterns for `wb launch` as well.** Rejected: it widens the rendered rules and the command gate for a route nobody needs
  remotely. Keeping `wb launch` terminal-only costs nothing.
- **Offer `ask` with no digest.** Rejected: an `ask` for a destructive argument such as `prune` would then confirm only the command
  text, not what it deletes. The digest binds the prompt to the state.
- **Build `ask` for `upgrade`, `add`, `acknowledge`, accept-decision, `submit-remote-job` and `push-shared-branch` here.** Not part of
  this record; each needs a digest of its own and is listed under Deferred in the plan.

## Consequences

- Good: the owner can run the review engine's bound extension and its other owner-run arguments from a remote channel without
  setting them to `none`, with a prompt that carries a digest of what will change; and a second module can use the same field.
- Good: a declaration without the new fields hashes and behaves exactly as before, so an installed project is unaffected until a
  module that uses them is upgraded.
- Bad: the field is a change to the module contract. An older workbench rejects a package whose declaration has it (the schema
  rejects an unknown field), so it refuses to install such a package. That fails closed but is a compatibility break for any
  mixed-version use.
- Bad: nothing takes effect without terminal steps. The module's change alters its declaration hash, so the owner runs
  `release-approvals` (a first-party package), `wb acknowledge` and `wb upgrade`, edits the personal settings and runs
  `wb rerender`. None of these can be done remotely, so the work must be finished at a terminal.
- Bad: the helper's check is the one that counts. A helper that ignores `--digest` turns `ask` into a prompt that confirms only the
  command text. The helper is a pinned, owner-confirmed file and the review engine's tests must show the refusal, but the launcher
  cannot verify it.
- Bad: the prompt shows the command and the digest, not the preview, as for `approve-plan`. The agent shows the preview in the
  conversation first; no code enforces that, so an `ask` proves the owner saw a digest and not that they read what it binds.
- Bad: at `none`, `reset`, `archive`, `prune` and `amend` lose their only protection, and `prune` deletes reviews. That is the owner's
  setting, made on purpose, and the default stays `block`.
- Bad: the digest binds the state of one review; the log can be written from a shell (`2026-10-26-ask-level-command-gate`).
- Neutral: the change reaches a trust boundary (who may run what the owner reserved, and how a digest binds it), so a security review
  is owed after the launcher is built, and runs only when the owner asks. The text of `command-permissions.md` and `module-contract.md`
  changes in the increments that build this, not in this record.

## Evidence

Read on 2026-10-27 at commit `32ac02187224f035e6f713ddc9ab52df91ee0d03`, with no uncommitted change to the files read. Nothing was
run beyond `wb plan-status`, which printed `approved` for the plan; the decision is from reading, no test was run and nothing was
built, so no tool version applies. Read: `workbench/commands.py` (`owner_refusal`, `launch_refusal`, `run`),
`workbench/declarations.py` (the `owner` handling and the exact-keys check of a command), `workbench/levels.py` (`_OFFERS`, `registry`),
`workbench/levelrun.py` (`route`, `logged`, `done`, `apply_logged`), `workbench/rendering.py` (`key_patterns`, `plan`),
`workbench/rules.py` (`command_owner_patterns`), the review engine's helper (`mutate`, `extend`, `reset`, `archive`, `decide`, and a
search for a terminal test, which found none), `docs/specs/command-permissions.md`, `docs/specs/module-contract.md`,
`docs/specs/module-boundary.md` and `docs/specs/review-engine.md`. A `reviewer` read of `launch.launch` found that it prepares and
starts the helper in one function, hence decision 6's note. **Not read or not run:** `prune`'s and `amend`'s own argument handling
beyond what a reviewer quoted, the command gate's treatment of `wb run` with a digest, and any caller of `launch_captured`. Each is
for the plan's Increment D or E to read before it builds.

## Related files and decisions

- `docs/specs/command-permissions.md`, `docs/specs/module-contract.md`, `docs/specs/module-boundary.md`, `docs/specs/review-engine.md`
- `docs/plans/2026-10-27-levels-for-the-review-workflow.md`
- [2026-10-26-a-level-for-every-command](2026-10-26-a-level-for-every-command.md)
- [2026-10-26-permission-levels-as-built](2026-10-26-permission-levels-as-built.md)
- [2026-10-26-ask-level-command-gate](2026-10-26-ask-level-command-gate.md)
- [2026-10-26-ask-level-spelling-limit](2026-10-26-ask-level-spelling-limit.md)
- [2026-10-21-module-code-lives-in-modules](2026-10-21-module-code-lives-in-modules.md)
- [2026-10-27-rerender-is-terminal-only](2026-10-27-rerender-is-terminal-only.md)
