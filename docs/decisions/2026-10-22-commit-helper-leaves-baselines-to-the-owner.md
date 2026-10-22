# The commit helper leaves the acknowledgement baselines to the owner

Status: Proposed
Date: 2026-10-22

Refined 2026-10-22: the helper, its tests and its setting follow the move to the `safe-git` module
(`2026-10-22-git-work-in-its-own-module`). The decision is unchanged.

## Context

The roadmap outcome of `code-work-commit` and a line of `docs/specs/trust-and-approval.md` said that a
deliberate change made through the commit helper updates the acknowledgement baselines of the files it
changed. The helper now exists (`wb run safe-git commit`, first built in `code-work`), and it is run by an agent with the owner's
privileges. A baseline is the owner's acceptance of a change that someone else made
(`2026-10-20-acknowledge-before-upgrade`). If the helper wrote baselines, an agent could edit `AGENTS.md`
or a file under `.workbench/` (an instruction-bearing, first-tier path), commit it through the helper, and
have its own edit accepted without the owner seeing it in `wb acknowledge`: the attack that decision exists
to stop.

## Decision

- The commit helper never reads or writes the guarded store. A change to a baselined path that is made and
  committed through it is listed by the next `wb acknowledge`, and the owner accepts it there.
- The statement in `trust-and-approval.md` and the outcome in the roadmap are corrected to say so.
- The helper runs only `git`, found outside the repository, with a scrubbed environment and in fixed argument
  shapes, and refuses a repository whose configuration or hooks select a program. There is no override
  flag, because through `wb run` the caller is an agent and the override would be the agent's.

## Alternatives considered

- **Write baselines for the paths a commit changes.** Rejected for the attack above. Writing them only for
  paths outside the first tier would write nothing today, since every baselined path is in it.
- **Let the owner pass a flag that accepts the change.** Rejected: the same agent that runs the helper
  would pass it. The owner already has `wb acknowledge`, run from a terminal.
- **Keep the owner's private commit helper for this.** Rejected: it lives outside any project, so a
  teammate cannot have it, and it is the helper this decision replaces.

## Consequences

- After the agent commits an edit to a baselined file, the owner runs `wb acknowledge` once to accept it,
  as for any other change made by someone else. This is a step the old behaviour would have skipped.
- A repository that selects programs (a hook, a filter, a file system monitor, signing) is committed to by
  hand.
- The attribution setting in `.workbench/safe-git.json` is itself a difference `wb acknowledge` lists, so a
  pulled edit that switches it to `allow` is seen before it is accepted.

## Verification

- `packages/workbench/safe-git/tests/`: `test_safegit_git.py`, `test_safegit_commit.py`,
  `test_safegit_remove.py` and `test_safegit_module.py`. None touches a store.
- Security pass, three rounds, in plan `2026-10-22-code-work-commit`, increment F.

## Related files and decisions

- `docs/specs/trust-and-approval.md`, `docs/specs/safe-git.md`, `docs/roadmaps/workbench-v1.md`
- `packages/workbench/safe-git/helper/safe-git`
- [2026-10-20-acknowledge-before-upgrade](2026-10-20-acknowledge-before-upgrade.md)
- [2026-10-22-installer-pins-declared-helpers](2026-10-22-installer-pins-declared-helpers.md)
