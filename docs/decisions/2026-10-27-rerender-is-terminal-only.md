# `wb rerender` offers `block` only and always needs a terminal

Status: Proposed
Date: 2026-10-27

## Context

`2026-10-26-a-level-for-every-command` (accepted), decision 3, says no key is limited to `block`: every key offers `block` and
`none`, and at `none` an owner-run command runs without a terminal and without a harness `deny`. Its dated clarification note of
2026-10-27 records one exception, the owner-run arguments of module commands, whose helpers check their own terminal.

The owner asked for a way to re-render an attached harness after a change to the personal settings (design
`docs/specs/harness-rerender.md`, plan `2026-10-27-rerender-attached-harness`). The command, `wb rerender`, is an owner-run installer
command, so decision 3 would give it `none`. A `none` for it cannot work as the decision describes:

- An owner-run command at `none` runs without a terminal only while the level reads `none` through `rendering.effective_level`
  (`command-permissions.md`, "One way to run at `none`"). That function returns `block` whenever the rendering record's table digest
  differs from the table now, or the permissions file's hash differs from the record's.
- Those are the two ordinary reasons to run a re-render: a changed table, and a rule that "Yes, and don't ask again" wrote into the
  permissions file. So at `none` the command would be refused exactly when it is needed.
- A way round it would let a non-terminal run keep, and record as trusted, `allow` rules in the permissions file that nobody saw.
  The design keeps the live file's `allow` rules and lists them for the owner to read before they confirm the digest.

## Decision

Proposed. Nothing here is built; Increment B of the plan `2026-10-27-rerender-attached-harness` builds it.

1. **`wb rerender` offers `block` only and defaults to `block`.** It always needs a terminal and the preview digest typed by the
   owner. A settings entry of `none` for it reads as `block` with a note, as for any level a key does not offer.
2. **This is a second exception to decision 3** of `2026-10-26-a-level-for-every-command`, for this one key, beside the one its
   clarification note records for the owner-run arguments of module commands. The reason is different: the module arguments wait on
   a module-contract change, and this key cannot use `none` because of what a re-render repairs.
3. **`wb preview rerender` is not an exception.** It writes nothing, is agent-safe, has its own key and defaults to `none`.
4. **Nothing else changes.** The rest of decision 3 and of the earlier decision stands. If a way to authorize a stale rendering
   without a terminal is wanted later, it is a new record that supersedes this one.

## Alternatives considered

- **Offer `none` for `wb rerender` as decision 3 says.** Rejected: the level would never take effect when the command is needed, so
  the setting would be offered and then ignored. That misleads the owner.
- **Offer `none` and let a stale rendering authorize it, narrowly.** The level read would accept a record that is stale only in the
  table digest and the permissions file's hash, and fail closed on everything else. Rejected: a non-terminal run would then keep and
  record `allow` rules nobody saw, and the gate would gain a rule whose only job is this command.
- **A dated clarification note on the accepted decision.** Rejected: the decisions README says a changed decision is a new record, and
  an exception to a numbered decision is a change.
- **Drop the `allow` rules at re-render so `none` is safe.** Rejected by the owner: a re-render keeps them and lists them.
- **No command; attach a new clone after a settings change.** The state of things today. Rejected by the owner's request.

## Consequences

- Good: the setting `wb rerender` offers is one that works, and a re-render is never run on a rendering nobody can vouch for.
- Good: the owner sees the kept `allow` rules before the digest is confirmed, because a person is always at the terminal.
- Bad: an agent can never re-render for the owner, even when the owner would allow it. The owner runs `wb preview rerender` output
  through their own terminal.
- Bad: the rule "every key offers `block` and `none`" now has two exceptions that are listed in two places. `command-permissions.md`
  lists both under "Not built" or its successor, and a test pins the list of keys that offer `block` only.
- Neutral: the plan's Increment B stops until the owner has accepted this record.

## Evidence

Read, not run, on 2026-10-27 at commit `2302778`: `workbench/rendering.py` (`effective_level`, lines 218 to 244), whose conditions
return `block` on a differing table digest or permissions-file hash; `workbench/harnessstage.py` (`stage`), which renders the table into
one file; `docs/specs/command-permissions.md`, "Not built" and "One way to run at `none`"; and the accepted decision and its
clarification note. The review of the spec by Codex (`gpt-5.6-terra`, four rounds, 2026-10-27) raised the `none` problem in round 4
and the conflict with decision 3 was raised in round 2 of the review of the plan. No experiment was run on `effective_level`.

## Related files and decisions

- `docs/specs/harness-rerender.md`
- `docs/plans/2026-10-27-rerender-attached-harness.md`
- [2026-10-26-a-level-for-every-command](2026-10-26-a-level-for-every-command.md)
- [2026-10-26-per-command-permission-levels](2026-10-26-per-command-permission-levels.md)
