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
with none (a CAD or electronics project that uses `groundwork` and domain modules) can install it alone. Its
one read of the repository is the credential check before a push (`push-check`).

Non-goals:

- Any other git operation. There is no push, branch, worktree, merge, rebase, reset or tag, and the only
  reads are the fixed shapes `push-check` uses. A push is a checkpoint that a process module builds
  (`code-work.md`, "Push") and the owner decides; merging into a shared branch is outside the agent.
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
| commands | `safe-git`, whose first argument is `commit`, `remove` or `push-check` (kit 1) |

It is run as `wb run safe-git commit`, `wb run safe-git remove` and `wb run safe-git push-check`. The installer pins the helper when the
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

## Push check

`wb run safe-git push-check [--remote <name>] [--base <40 hex>]` reads the repository and prints one JSON line:
`remote`, `branch`, `target`, `default_branch`, `base`, `ahead`, `changed_paths`, `findings` and `truncated`. It
does not push and never contacts the remote: every ref it reads is local. It is read-only and changes nothing.

- The branch is the current one, read with `symbolic-ref`; a detached HEAD and an unborn branch are refused.
  `target` is the branch a push of HEAD would update, taken to be the current branch. The default branch comes
  from `refs/remotes/<remote>/HEAD` and is null when that is not set.
- The base is `--base` if given, else `refs/remotes/<remote>/<branch>`, else `refs/remotes/<remote>/<default
  branch>`, else a refusal that names what was tried. The range is `<base>..HEAD`.
- The scan reads the patch of each commit in the range (merges excluded) and the net diff, added lines only, so a
  secret added and removed inside the range is still reported. It treats every file as text and ignores
  submodules (`--ignore-submodules=all`), with external diff and text conversion off. Patterns: a private-key
  header, an AWS access key id, `ghp_` and `github_pat_` tokens, an `sk-` key, `xoxb-` and `xoxp-` Slack tokens
  and a JWT-shaped string; and the file names `.env`, `*.pem` and `id_rsa`.
- A finding is `{path, line, rule}`; `line` is the line in the new file, or null for a file-name finding. No
  matched text is printed, so a finding is not itself a leak. Output is read through a cap of 8 MiB and a
  deadline, with git in its own process group; at most 500 changed paths and 100 findings are listed, and
  either cut sets `truncated`.
- It refuses a repository that selects a program (as `commit` does), a base it cannot resolve, and any argument
  it does not allow.

Limits: the patterns are a narrow list and miss encoded, split or unlisted secrets and flag false positives, such
as the pattern names written in documents; a stale or forged tracking ref, a `push.default` or `pushRemote`
setting can make the report differ from a real push; the contents of a changed submodule are not read.

`commit` does not share the submodule exposure that `push-check` had to close, as far as one run showed
(2026-10-23, Git as installed on the owner's machine). `commit` refuses a repository whose index holds a gitlink
before it reads anything else, and a gitlink that only HEAD holds was not entered by its reads, with a nested
repository whose own configuration named a program for a filter, a file system monitor, an external diff and a
hooks path. A bare `git diff --name-only -z` on a gitlink in the index did start that program in the same setup.
This is one nested-repository shape and one Git version, not a security review of `commit`, and no test pins
the case that only HEAD holds.

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
never to push. It names no tool but the two commands. The push routine is not this module's skill: it is
`code-work`'s `push-changes`, which composes `push-check` with `wb run code-work shared`.

## What was and was not taken from the superpowers skills

`port-superpowers` (roadmap) inventories the superpowers skills the owner uses. The two that concern git were
looked at here:

- `using-git-worktrees`: not ported. A worktree needs git subcommands this helper deliberately does not run.
- `finishing-a-development-branch`: not ported. Merging and cleanup are outside the agent; pushing is the
  checkpoint that `push-checkpoint` built, with `push-check` here and the `push-changes` skill in `code-work`.
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
- Built, from plan `2026-10-23-push-checkpoint`: `push-check` and its git shapes, with an adversarial security
  pass whose findings were fixed and tested. See "Push check" for its limits.
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
- `push-check` prints the fields above, never contacts the remote, prints no matched text and refuses a
  repository that selects a program, a detached HEAD, an unborn branch and an unresolved base.
