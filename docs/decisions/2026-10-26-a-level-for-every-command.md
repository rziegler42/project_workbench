# Every command has a permission level, and no level is limited to block

Status: Accepted by the owner on 2026-10-26
Date: 2026-10-26

## Context

`2026-10-26-per-command-permission-levels` (accepted) gave the owner a table of levels for the owner-run and checkpointed commands.
`2026-10-26-permission-levels-as-built` (accepted) records what was built: every key ships `block`, only `approve-plan` offers a level
beyond `block`, and `accept-decision` offers `block` only. That leaves three gaps against what the owner asked for, which was a
permission level for all `wb` commands, each with a default that suits the command:

- The agent-safe commands (`verify`, `preview`, `launch`, `check`, `run`, `plan-status`, `settings` and the hook entry points) are
  always allowed and are not keys, so the owner cannot tighten them.
- Every default is `block`, so no default reflects what a command does.
- A key that offers `block` only cannot be loosened, and the owner has said no command should be so limited; the owner's risk
  appetite is theirs to set.

Two rules also stand in the way. The checkpoint reading and the table entry combine as the stricter of the two, so a checkpoint
`stop` (what a version 1 file reads as) keeps a key at `block` however the table is edited. And `AGENTS.md` said that only the owner
accepts a decision; the owner has since changed it so that the `accept-decision` level decides (working-tree change, not yet committed
when this was written).

The compiled hard-stop floor is not touched by this record (`2026-10-19-compiled-hard-stop-floor`). The neutral rule list still
holds only `ask` and `deny` (`2026-10-19-restrictive-only-permissions`, which this record does not change): a level of `none`
renders no rule.

## Decision

Accepted by the owner on 2026-10-26. Nothing here is built; building it needs a plan the owner approves.

1. **Every command has a key.** Every command and subcommand that `cli.py` routes has a key, the agent-safe ones included, except
   the hook entry points `gate`, `agent-gate` and `gate-command`, which the harness runs and the owner does not (the owner's
   decision, 2026-10-26). They are not keys, are always allowed and sit outside the table. A
   subcommand has its own key when it is a different action (`wb preview install`, `wb preview adopt`, `wb run <command>
   <argument>`). A flag that only changes how a command reports, such as `--digest`, belongs to its command's key. Each argument
   a module declares for a command has a key, `wb run <command> <argument>`, derived from the declaration with no new field: an
   owner-run argument defaults to `block`, as now, and any other declared argument defaults to `none`, because an agent may run it
   today. The contract has no read-only declaration, and this record adds none; "read-only" is not used to choose a default. A
   command or argument the module does not declare is refused as now and has no key. A test fails
   when a routed command has no key and is not one of those three.

   **One action reaches one key.** A word that only dispatches to an action is not a key: `wb run` and `wb preview` are not keys,
   and `wb run <command> <argument>`, `wb preview install` and `wb preview adopt` are. A parent therefore cannot tighten or bypass
   an action beneath it, and no command reaches two keys. The agent-safe `delegate-approve-plan` has no key of its own: it reaches
   the key `approve-plan` and runs only while that key reads `delegated`, as the spec already says. The rendering and the log use the
   one key an action reaches. The rule that a command reaching more than one key takes the strictest of them stays unbuilt, because
   this decision keeps it unneeded. A test fails when an action reaches two keys.
2. **A default is what the command does today.** An agent-safe command defaults to `none`; every other key keeps `block`. The default
   of `approve-plan` is not raised. No default loosens a command that an agent cannot run today.
3. **No key is limited to `block`.** Every key offers `block` and `none`. `delegated` is offered only where a command declares a gate
   (still `approve-plan` only). `ask` is offered by a key once that key has a read-only preview whose digest it requires, built as
   `approve-plan`'s is. At `none`, an owner-run command runs without a terminal and without a harness `deny`; its own checks of its
   input and its log entry still apply. `accept-decision` is covered by this rule, and `AGENTS.md` follows it.
4. **There is no master switch.** No profile, command or setting turns every protection off at once. An owner who sets every key to
   `none` has reached that state by their own edits to the table; the system does not offer it as a feature.
5. **The table is the single source of a level.** A table entry wins over the checkpoint reading in either direction. A version 1
   file's `checkpoints` are read as a fallback for a key the table does not mention. This replaces the rule that the stricter of the
   two applies.
6. **One vocabulary.** The four level names, `block`, `ask`, `delegated` and `none`, are used everywhere a level is named. `stop` and
   `delegate` are read from a version 1 file as aliases for `block` and `delegated`; `wb settings` prints only the four names and
   notes a word it translated.
7. **Out of scope.** The floor, the order in which `ask` digests are built, and each digest's content are for the spec and a plan.

## Alternatives considered

- **Key the hook entry points too.** Rejected by the owner. They are the hooks that make the rest work, and whether a `deny` rule
  would stop the harness's own hook call is untested.
- **A master `open` profile that sets every key to `none`.** Rejected by the owner: the state is an outcome of per-key freedom, not a
  feature.
- **Keep `block`-only keys for the trust-changing commands.** Rejected by the owner: the owner decides their risk appetite.
  `2026-10-26-per-command-permission-levels` had already rejected a fixed `block` for them.
- **Keep "the stricter of checkpoint and table".** Rejected: with every key loosenable, a version 1 `stop` would silently pin a key
  at `block` and loosening would need edits in two places. It keeps the property that a checkpoint cannot be overridden, which is
  now the table's job to hold.
- **Loosen the defaults for the trust-changing commands.** Rejected: nothing the owner said asks for it, and it would widen what an
  agent can do on a machine whose owner changed nothing. This is the author's call.
- **Key only the owner-run commands, as now.** Rejected: the owner cannot then tighten an agent-safe command.
- **Supersede `2026-10-19-restrictive-only-permissions`.** Not needed: see Context.
- **Edit the accepted records.** Not allowed. This record refines them, and the owner marks their status lines once it is accepted.

## Consequences

- Good: every command can be set by the owner, and the defaults match what each does today, so a fresh install is no looser than now.
- Good: loosening a key is one edit in one table, and one set of four words describes every level.
- Bad: an owner who sets a trust-changing command (`install`, `upgrade`, `approve`) to `none` removes the only protection on it, and
  an agent steered by hostile text could then change what the workbench trusts. The floor and the log remain. The protection is the
  owner's setting, not the code, and a setting like that should be made on purpose. This follows
  `2026-10-26-per-command-permission-levels`, decision 3.
- Bad: letting an agent accept a decision, at `accept-decision` set to `none`, weakens the rule that an accepted decision outranks
  the code. It is the owner's choice and the default is `block`.
- Bad: the table grows by the agent-safe commands and subcommands, and the keys are longer; `wb settings` output grows with it.
- Bad: the owner cannot tighten the three hook entry points; they remain always allowed.
- Bad: `ask` for the other commands still needs a preview digest each, so until they are built those keys offer `block` and `none`
  and nothing between. An owner who wants a prompt for them cannot have it yet.
- Bad: a command run at `none` by an agent leaves the log as its only record, and the log can be written from a shell (accepted in
  `2026-10-26-ask-level-command-gate`).
- Neutral: the status lines of `2026-10-26-per-command-permission-levels` and `2026-10-26-permission-levels-as-built` change to name
  this record only once the owner accepts it. A security review is owed when it is built (authorization, the guarded store and a
  permission boundary), and runs only when the owner asks.

## Evidence

Read on 2026-10-26 at commit `040798e` plus uncommitted edits to `AGENTS.md`, `docs/specs/command-permissions.md` and
`docs/decisions/README.md` (Python 3.14.4, no other tool version applies): `docs/specs/command-permissions.md` (revised in the same session, its section "Planned: a level for every
command", reviewed by the review engine, one round, one finding applied); `workbench/rules.py` (`OWNER_RUN`, `AGENT_SAFE`); `workbench/cli.py` (the routed commands); `workbench/levels.py` (`_DEFAULTS` empty); and the output of
`wb settings` run from this repository (every `level` line `block`, which shows that no default is looser than `block` today) and
the personal settings file read with `cat` (`version` 1, empty `checkpoints`, which shows that no `levels` table is in force). Nothing was run to test a `deny` on a hook
entry point or a `none` on an owner-run command, and nothing was built. The command lists were read from the code and may be
incomplete.

## Review record

Reviewed by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-26, at the owner's
request: two rounds of the bound of 3, not converged. Round 1 returned a major finding (commands reaching more than one key) and a
minor one (evidence provenance); round 2 returned a major finding (a read-only declaration the module contract does not have). All
three were applied; the round 2 finding was checked against `workbench/declarations.py`. The text added for round 2 was not reviewed
again. The owner accepted the record as written on 2026-10-26, knowing that. The acceptance is the owner's, and a review is not an
acceptance.

## Related files and decisions

- `docs/specs/command-permissions.md`, `docs/specs/trust-and-approval.md`, `AGENTS.md`
- [2026-10-26-per-command-permission-levels](2026-10-26-per-command-permission-levels.md)
- [2026-10-26-permission-levels-as-built](2026-10-26-permission-levels-as-built.md)
- [2026-10-19-compiled-hard-stop-floor](2026-10-19-compiled-hard-stop-floor.md)
- [2026-10-19-restrictive-only-permissions](2026-10-19-restrictive-only-permissions.md)
- [2026-10-19-mandatory-review-personal-delegation](2026-10-19-mandatory-review-personal-delegation.md)
- [2026-10-26-ask-level-command-gate](2026-10-26-ask-level-command-gate.md)
