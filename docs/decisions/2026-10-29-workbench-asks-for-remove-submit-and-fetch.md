# The workbench renders an ask for safe-git remove and for remote-runner submit and fetch

Status: Proposed
Date: 2026-10-29

## Context

`2026-10-25-module-commands-and-the-approver` (accepted) asked what raises a prompt for the module commands that the owner's
approver was to review, and the owner chose its option 2: the owner adds global `ask` entries at the user level for
`wb run safe-git commit` and `remove` and for `wb run remote-runner submit` and `fetch`. That record says the choice protects the
owner's machine only and is not a guarantee of the project.

The user-level configuration those entries lived in was reset to factory defaults on 2026-10-29, so nothing now prompts for
these commands from outside the project. The decision `2026-10-24-project-guarantees-a-floor` (accepted) says the project's own
`deny` and `ask` rules hold under any global setup. Its decision 3 adds that a rendered setting is "a first line and not the
guarantee", and that a guarantee that matters is enforced in the workbench's own code. The chosen option rendered nothing in the
project, so it had neither property.

What the project renders today (`docs/specs/command-permissions.md`, "A level for every command"): the five hard stops of
`workbench/floor.py` render as `ask` rules in `workbench/rules.py` (`FLOOR_RULES`), and the levels table offers an agent-safe key only
`none`. `wb settings` prints `level wb run safe-git remove: none`, `level wb run remote-runner submit: none` and
`level wb run remote-runner fetch: none`. The floor's `ask` for deleting files matches the command text `rm` and `rm *`, so a
deletion made as `wb run safe-git remove --confirm` does not match it; I reasoned that from the patterns and did not run it against
the harness. Submitting a job and fetching output have only skill text and the agent-side checkpoints `submit-remote-job` and
`fetch-remote-output`, which read `stop` but are rules the agent follows.

## Decision

1. **The workbench renders an `ask` for three commands**: `wb run safe-git remove`, `wb run remote-runner submit` and
   `wb run remote-runner fetch`. This is option 1 of the earlier record's Question 1, for these three only. The rule is rendered in
   every attached project whose harness provides permissions, under any global setting, and the owner confirms it on the harness
   prompt. It is a first line and not a guarantee in the sense of `2026-10-24-project-guarantees-a-floor` (decision 3): settings
   merge across levels, the match is on command text, and a harness that provides no permissions gets the warning the harness spec
   describes and no prompt. The plan may add enforcement in the module's own code; this record does not require it.
2. **`wb run safe-git commit` is not asked.** The helper already checks the expected head, the exact paths and the attribution
   rule, a commit is local and can be reverted, and a push is already asked by the floor.
3. **Where the rule lives** is left to the plan: a rule a module declares for its own argument, or a split of `remove`'s preview and
   `--confirm` into arguments of their own, so that the agent-safe levels table can carry it. Either way the module declares it, as
   a restrictive rule only (`2026-10-19-restrictive-only-permissions`).
4. **This supersedes the earlier record's Question 1 choice for these three commands.** Its Question 2 (the commit is not delegated)
   and its other text stand. After the owner accepts this record, the earlier record's status line gains a clause naming it; its
   text is not touched.

## Alternatives considered

- **Ask for all four, commit included.** Rejected by the owner: a prompt on every commit is constant friction, and the owner would
  approve each commit twice, once by word and once at the prompt.
- **Accept that the workbench prompts for none of them** (option 3 of the earlier record). Rejected by the owner: it leaves
  `safe-git remove` as a way around the floor's `rm` ask and leaves job submission and fetching to skill text alone.
- **The owner adds global `ask` entries by hand again** (option 2 of the earlier record). Rejected by the owner: it protects one
  machine, it is not a project guarantee, and no approver reads those entries now.
- **Wait for the action-review engine.** Not chosen: the engine reviews a command that has already raised a prompt, so it needs an
  `ask` to exist. It may add a review later.

## Consequences

- **Good:** the three commands that delete files, send work to a remote and fetch from one stop for the owner in every attached project whose
  harness renders permissions, without relying on anything in the owner's own configuration. `safe-git remove` no longer sidesteps the `rm` ask.
- **Bad:** more prompts: every removal, submission and fetch. The commit helper keeps working without one.
- **Cost:** edits to the `safe-git` and `remote-runner` modules, their specs and tests. They are under `packages/`, so the shipped
  approvals are released again by the owner, and each clone gets the rule after `wb rerender`.
- **Limit:** like every `ask` rule it is a best-effort match on command text, not a sandbox
  (`2026-10-26-ask-level-spelling-limit`).
- **Not decided:** the rendering mechanism (decision 3), and who may confirm a prompt when several people share a repository.

## Evidence

Read on 2026-10-29 at commit `5ee1ecce8efa83194f118748666a84fab4be6960`, workbench 0.1.0, Python 3.15:
`wb settings` for the three levels above; `workbench/rules.py` for `FLOOR_RULES`; `workbench/levels.py` for `_AGENT_OFFERS`; the
text of `2026-10-25-module-commands-and-the-approver`; and a listing of the user-level configuration directory, which holds no
settings file after the reset. Not run: a deletion through `wb run safe-git remove --confirm` against the harness, so the claim in
Context that it bypasses the `rm` ask is from the patterns, not from a run.
