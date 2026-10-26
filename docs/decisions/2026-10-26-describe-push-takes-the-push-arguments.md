# A push is described by `safe-git describe push`, which takes the arguments of `git push` and validates them itself

Status: Accepted
Date: 2026-10-26

## Context

The accepted decision `2026-10-25-describe-interface-for-action-review` sets the interface by which the engine
learns what an action would do. Three of its items assume the action is a command of the module that describes it:

- Item 1: `describe` "takes exactly the arguments of the real command" (`wb run safe-git describe commit ...` for
  `commit ...`).
- Item 2: it "runs the real command's own validation code and nothing else", so the validation lives in one place.
- Item 6: the first users are `safe-git describe commit` and `describe remove`, and "a push uses `push-check`,
  extended for the outgoing commits it does not yet report".

A push is not a command of `safe-git`. The module never runs `git push` (`safe-git.md`, "Purpose and scope": there is
no push in it), so there is no real command in the helper whose arguments `describe` could take or whose validation it
could run. The only real command is Git's. `push-check` reports what a push of the current branch would send for a
person, and takes `--remote` and `--base`; it does not see the flags and refspecs of the push, which several checks of
the owner's approver depend on (force, delete, tags, the target).

The owner chose on 2026-10-26 to add `describe push` instead of extending `push-check` alone, and to close the whole gap
that `safe-git.md` ("The push gap") lists. `action-review.md` already names both options. This record settles the part of
the accepted decision that the choice departs from. An accepted decision is superseded, never edited, and a clarification
note cannot override it.

## Decision

For a push only, items 1, 2, 3 (the meaning of `errors`) and 6 of `2026-10-25-describe-interface-for-action-review` are
narrowed as follows. Every other item of that record stands as written, and so do items 1, 2, 3 and 6 for `commit`,
`remove` and any other action that is a command of its module.

1. **`wb run safe-git describe push` takes the arguments that follow `git push`** (flags, then an optional remote, then
   refspecs), not the arguments of a `safe-git` command. It reports what that push would ask the remote to do. It never
   runs `git push`, contacts a remote, or writes anything.
2. **Its validation is its own parser, over a fixed grammar,** because there is no real command in the module to share
   validation with. The grammar accepts a stated set of flags, a remote that is a name (not a URL or a path; an unconfigured name gives `remote_unconfigured`)
   and refspecs of stated forms; everything else is refused with the code `usage` and no fact is given. A form whose
   meaning depends on what the remote holds (`--mirror`, `--follow-tags`, the settings that imply them, a wildcard
   refspec on the command line or in `remote.<name>.push`, `push.default` set to `matching`) is refused with the named
   code `remote_state_required` instead of being reported with a partial answer, and so is a remote with more than one
   effective push URL (`multiple_push_urls`). A push is described only when one range of commits is sent: one update
   whose source is the current branch, or deletions only; `--all`, `--tags` and any other source are `usage` in this
   version. The grammar is written in `safe-git.md`.
3. **The engine uses `describe push`, and `push-check` is not extended for it.** `push-check` keeps its fields and its
   meaning for the `push-changes` skill. The module declares `push` in `describes` when the facts are complete, and the
   launcher's rule for a declared action applies as for `commit` and `remove`.
4. **The parser is held to the same equivalence test as the others.** The facts must equal what a real `git push` of the
   same arguments asks for, tested against a bare local repository used as the remote; the facts claim nothing about
   whether a ref exists on the remote or whether the push would succeed.
5. **`errors` means the refusals under the grammar and the local data.** Item 3 of the accepted record has `errors` hold
   what the real command would refuse; for a push it holds only what the parser and local data can refuse, and never a
   refusal that Git or the remote makes at push time (a non-fast-forward update, a remote hook, a permission).

## Alternatives considered

- **Extend `push-check` only.** Rejected: the engine runs only the verb `describe` for a declared action (item 5 of the
  accepted decision), so it could not call `push-check` without an exception to that rule and to the `describes`
  admission test. `push-check` also never sees the flags and refspecs.
- **A real `safe-git push` command with `describe push` sharing its validation.** Rejected: it would give the agent a way
  to push, which the owner keeps as a checkpoint (`code-work.md`, "Push"), to obtain a validation function. The module
  does not push.
- **The engine parses `git push` itself.** Rejected for the reason item 7 of the vendor-bridges record gives: it rebuilds
  the owner module's inspection in a second place.
- **Describe only what `push-check` can see and leave the rest to the approver.** Rejected by the owner on 2026-10-26: the
  cutover cannot retire the approver while a push depends on it.
- **Accept more of Git's grammar (`--mirror`, `--follow-tags`, several push URLs).** Rejected for now: each depends on
  state the module does not read, and a partial fact looks like a complete one. A later plan may add them with a defined
  remote-state read.

## Consequences

- Good: a push gets the same review as a commit and a removal, and the approver's last collector can go.
- Good: nothing the parser does not understand is ever approved; the refusal is `usage` or a named code.
- Bad: the parser is new code that must agree with Git, with no real command to test it against except Git itself. Mitigated
  by the tests against a real push to a local bare repository and by a security pass owed to the new reads.
- Bad: a push that uses `--mirror`, `--follow-tags`, `--all`, `--tags`, a source other than the current branch,
  `push.followTags`, `remote.<name>.mirror`, a wildcard refspec, `push.default` `matching` or several push URLs cannot be
  described, so it stays at the normal prompt. This is the price of not guessing.
- Bad: item 1 of the accepted record now has a second form (the arguments after `git push`); readers must find both.
- Neutral: the facts, error codes and caps are in `safe-git.md`, and the engine's rule for a push is a later plan.

## Evidence

Read on 2026-10-26 at commit `282e4f9` of this repository: `2026-10-25-describe-interface-for-action-review`,
`docs/specs/safe-git.md` ("The push gap" and `push-check`), `docs/specs/action-review.md`, and the helper's
`command_push_check` and `parse_push_check`. Nothing was run to test a push parser, and nothing was built. The list of
approver checks for a push is quoted from `safe-git.md`, which read the approver on 2026-10-25 (role USER, not run).

## Related files and decisions

- `docs/specs/safe-git.md` ("`describe push`"), `docs/specs/action-review.md`, `docs/plans/2026-10-26-safe-git-describe-push.md`
- [2026-10-25-describe-interface-for-action-review](2026-10-25-describe-interface-for-action-review.md) (items 1, 2, 3 and 6 are narrowed for a push)
- [2026-10-22-model-calls-go-through-vendor-bridges](2026-10-22-model-calls-go-through-vendor-bridges.md) (item 7: facts come from the module that owns the action)
