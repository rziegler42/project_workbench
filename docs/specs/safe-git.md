# safe-git

Status: Current. Built by plan `2026-10-22-safe-git-module`, which moved the code from `code-work`
(`2026-10-22-git-work-in-its-own-module`). The rules are the substance; "As built, and its limits" lists
what exists.

Terms are defined in `terms.md`. The declaration it satisfies is defined in `module-contract.md`; the
launcher, the kit and the pin in `module-boundary.md`; the authority rules in `trust-and-approval.md`.

## Purpose and scope

`safe-git` is a module of type `module` that lets an agent change a repository in two bounded ways: make
one local commit of exactly the named files, and delete exact paths the owner has approved. It has no
process of its own. A project with a process module (`code-work`) gets it as a hard requirement; a project
with none (a CAD or electronics project that uses `groundwork` and domain modules) can install it alone.

Non-goals:

- Any other git operation. There is no push, branch, worktree, merge, rebase, reset or tag. A push is a
  checkpoint that a process module builds (`code-work.md`, "Push"); merging into a shared branch is outside
  the agent.
- Review, plans or approval. The module commits what it is told to commit; whether the work was reviewed is
  the process's business.
- Writing the acknowledgement baselines (`2026-10-22-commit-helper-leaves-baselines-to-the-owner`).

## Declaration (summary)

| field | value |
|---|---|
| type | `module` |
| provides | `commit` |
| requires | nothing |
| fills, writes | nothing |
| ships | one helper, `helper/safe-git`, and one neutral skill, `commit-changes` |
| commands | `safe-git`, whose first argument is `commit` or `remove` (kit 1) |

It is run as `wb run safe-git commit` and `wb run safe-git remove`. The installer pins the helper when the
owner confirms the install; an edited helper is not run until the change is acknowledged. `code-work`
requires the capability `commit`, so installing it without this module stops with the hard-requirement
message.

## Commit

- The agent commits through this helper and never by composing raw git commands. A commit is local and
  lists exact paths.
- `commit` takes `--expected-head <full hash | none>`, `--subject`, optional `--body`, `--trailer 'Key:
  value'` and `--leave-other-staged`, then `--` and exact repository-relative paths. It stages and commits
  only those paths. It refuses when HEAD is not the expected commit (`none` is accepted only on a branch
  that has no commit yet), when anything else is staged (without `--leave-other-staged`), when a path is a
  directory, a glob, a link, in a nested repository or Git metadata, or when the repository selects a
  program to run (a hook, a filter, a file system monitor, signing).
- After the commit it checks the message, the parent and the changed paths, and says so when they differ.
  The expected-HEAD guarantee is detection and not atomicity: a writer that moves HEAD after the last check
  produces a commit the helper reports as failed.
- On success it prints one JSON line (`committed`, `subject`, `paths`). On a refusal it writes `refused:
  <reason>` to standard error and exits 1.
- A commit never authorizes a push.

## Remove

`remove` previews, then with `--confirm` deletes exact paths, and with `--recursive` the directories among
them. It refuses Git metadata, nested repositories, the repository root, links and overlapping targets, and
follows no link. A deletion needs the owner's approval of the previewed list; the skill tells the agent to
stop for it.

## The attribution setting

The message carries no tool attribution unless `.workbench/safe-git.json`
(`{"format": 1, "attribution": "refuse" | "allow"}`) says `allow`; absent means refuse. The check is a
guard against a mistake and a heuristic: it is not a control against an agent that writes the setting or
spells the name with a look-alike the check does not know. The file is read without following a link, and a
link, a malformed file or one of the wrong size stops the commit. The file is a difference `wb acknowledge`
lists, so a pulled edit that switches it to `allow` is seen before it is accepted. The setting file
that `code-work` once read is read by nothing.

## How it runs git

The helper runs `git` found only in an absolute `PATH` entry outside the repository, with a scrubbed
environment, literal pathspecs, no editor, pager, lazy fetch, file system monitor or automatic maintenance,
and only in the argument shapes it uses. It never reads or writes the guarded store.

## The skill

The module ships one neutral skill, `commit-changes`. It tells an agent to commit only when the owner has
asked, to run the verification first, to name exact paths and the full HEAD hash, to describe the change
only, to use `--trailer` when the project's process asks for one, to run `remove` as a preview and
`--confirm` only after the owner approves, to stop and report a refusal rather than work around it, and
never to push. It names no tool but the two commands.

## What was and was not taken from the superpowers skills

`port-superpowers` (roadmap) inventories the superpowers skills the owner uses. The two that concern git were
looked at here:

- `using-git-worktrees`: not ported. A worktree needs git subcommands this helper deliberately does not run.
- `finishing-a-development-branch`: not ported. Merging, pushing and cleanup are outside the agent or are a
  push checkpoint that `push-checkpoint` builds.
- The commit rules (exact paths, no attribution, one commit per request) were already the owner's own and
  are written new in `commit-changes`; no superpowers text is copied.

`port-superpowers` starts from this list and does not revisit git.

## As built, and its limits

- The code is the code of plan `2026-10-22-code-work-commit`, moved unchanged with its tests; the security
  pass of that plan (increment F, three rounds) still stands for it. A diff of the moved region against the
  original shows four edits: the setting path and three strings that named `code-work`.
- Recorded limits: the caller's `HOME` and `PATH` are trusted; a `git` in an absolute `PATH` entry outside
  the repository is run; the look-alike letters of the attribution check are a list that cannot be
  complete; a repository that selects a program (a hook, a filter, a file system monitor, signing) is
  committed to by hand.
- Tests that run git need it and skip with a reason without it.
- No end-to-end run in a live session has been done.

## Acceptance criteria

- The module verifies as a first-party `module`, provides `commit`, and ships only its helper and skill.
- Through the launcher, `commit` makes a first and a next commit, refuses an unborn-branch claim and an
  attribution message, and `remove` previews then removes; an edited helper is refused.
- The attribution setting is read from `.workbench/safe-git.json`; absent means refuse; the old name is read
  by nothing.
- Installing `code-work` without `safe-git` stops with the hard-requirement message; installing both works.
- The `code-work` helper contains no git code and starts no program.
- A pin recorded for one command lets no other command run.
- The skill is accepted by the neutral reader and names no tool beyond the two commands.
