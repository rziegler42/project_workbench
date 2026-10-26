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
  reads are the fixed shapes `push-check` uses *(and, once built, the few more that `describe` adds; see
  "Describe")*. A push is a checkpoint that a process module builds
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
| commands | `safe-git`, whose first argument is `commit`, `remove` or `push-check` (kit 1). *(Specified, not built: `describe`, with `describes: ["commit", "remove"]`; see "Describe".)* |

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

## Describe *(specified, not built)*

`wb run safe-git describe commit ...` and `wb run safe-git describe remove ...` take exactly the arguments of the real
`commit` and `remove` and report what the real command would act on, as the accepted decision
`2026-10-25-describe-interface-for-action-review` requires. This section is what that decision left to the module:
the names and types of the facts, the refusals as error codes, the numeric caps with their sources, and the
counterpart of each check of the owner's approver. Nothing here exists in the helper yet. The plan for `safe-git
describe` builds it and declares `describe` among the command's `arguments` and `describes: ["commit", "remove"]`
(`module-boundary.md`, "Declaration schema").

**What `describe` does.** It runs the same parsing and validation as the real command, in the same order, up to the
last step that changes anything, and then stops. For `commit` it runs everything through `git diff --check` of the
named paths; it stages nothing, runs no `git add`, `git commit` or `_unstage`, and writes no file. For `remove` it
runs `plan_removal`, which is the real preview, and deletes nothing. It runs git only in the fixed argument
shapes of the helper. The shapes it has today do not read a HEAD blob, ask whether a path is ignored, or list the tracked
files below a path, which the facts need (`cat-file -s` and `cat-file blob` of `HEAD:<path>`, `check-ignore -q`, and
`ls-files -z` of a path). The plan for `describe` adds exactly those shapes to the allowlist, and they are new surface
that its security pass covers. A refusal the real command would give is returned as `ok: false` with an error, and the
exit status of `describe` is 0. The only refusal with exit 1 and no object is a `describe` call whose first argument is
not `commit` or `remove`. Everything else, a missing repository included, is an object with `ok: false`.
On such an object `contract` is 1, and every fact the refusal prevented is null (a string, whole number or boolean
fact that could not be found out) or empty (an array); a fact that is simply a copy of an argument (`leave_other_staged`,
`confirm`, `recursive`) keeps the value given, and `path_count` is the number of paths the call named; a total that could
not be counted is omitted and named in `omitted`. The names of the other facts are always present. The one outcome it cannot report is a race after the last check: a path
changed, or HEAD moved, between `describe` and the real command. The real command's own checks (`staging did not give
exactly the named paths`, `HEAD moved`, and the check of the finished commit) stay with it and have no error code in
`describe`.

### Errors (`errors[].code`)

One code for each refusal class of the real command. A `message` is the real refusal text, display-cleaned and cut to
500 characters.

| Action | Code | The real refusal |
|---|---|---|
| both | `usage` | an unknown option, an option given twice, an option without its value, a required option missing, no path after `--`, more than 2,000 paths |
| both | `repository_unreadable` | no repository, a work tree that is not the repository holding its metadata, a working directory outside the repository root, a `.git` that is a link or not a directory, git not found or not runnable, git timed out or exited with an error, or the root cannot be opened safely |
| both | `path_refused` | a path that is empty, too long, not printable, absolute, with a backslash or colon, an empty, `.` or `..` segment, or with a `.git` or `git~N` segment (the shared path check runs first, so these spellings of Git metadata give this code); a glob or an option-like path; a path that cannot be examined (commit); for remove, a path through a link or something that is not a directory |
| both | `path_duplicate` | a path named twice, or two spellings of one file (commit); overlapping targets (remove) |
| commit | `expected_head_invalid` | `--expected-head` that is neither the full 40-digit lower-case hash nor `none` |
| commit | `head_mismatch` | HEAD is not the expected commit; `none` given where a commit exists |
| commit | `head_unreadable` | HEAD names neither a commit nor a branch without commits |
| commit | `subject_invalid` | a subject that is empty, has more than one line (or a NUL or CR) or is over 300 characters |
| commit | `body_invalid` | a body that is empty, holds a NUL or is over 100,000 characters |
| commit | `trailer_invalid` | more than 50 trailers, or a trailer that is not one `Key: value` line (at most 1,000 characters) |
| commit | `message_character_refused` | a control, combining, private-use or invisible character; a look-alike letter; a word that mixes scripts; the real command makes this check only where the attribution setting does not allow attribution, and so does `describe` |
| commit | `attribution_refused` | tool attribution in the message, where `.workbench/safe-git.json` does not allow it |
| commit | `setting_invalid` | the attribution setting cannot be read, is not valid, or has the wrong shape or size |
| commit | `repo_selects_program` | the repository would make git run a program: a hook, a filter, a file system monitor, signing, a gitlink, or an unreadable config, hooks directory or index |
| commit | `operation_in_progress` | a merge, revert, cherry-pick, rebase or sequencer in progress |
| commit | `path_unmerged` | a path with an unresolved merge state |
| commit | `path_in_nested_repository` | a path inside a nested repository |
| commit | `path_not_a_file` | a path that is, or goes through, a link or a directory, or a link under another spelling (for remove, a path through a link gives `path_refused`) |
| commit | `path_unknown` | a path that does not exist and is not tracked |
| commit | `index_unreadable` | git lists the index in a form the helper does not read |
| commit | `index_has_staged_changes` | something is staged and `--leave-other-staged` was not given |
| commit | `path_already_staged` | a named path is already staged |
| commit | `whitespace_errors` | `git diff --check` finds whitespace errors in the named paths |
| remove | `git_metadata_refused` | a target the removal's own check takes for Git metadata after the shared path check passed it (a look-alike spelling of `.git`); a plain `.git` segment gives `path_refused` |
| remove | `target_missing` | a target that does not exist, or a directory on the way that does not exist |
| remove | `recursive_required` | a directory target without `--recursive` |
| remove | `repository_root_refused` | the repository root as a target |
| remove | `nested_repository` | a target that is, lies inside, or holds a nested repository |
| remove | `other_filesystem` | a target, a directory on the way to it, or a directory in it, on another filesystem |
| remove | `tree_too_large` | a tree deeper than 100 levels or with more than 100,000 entries |
| remove | `target_changed` | a directory that changed while it was being checked |

Whether the same code is given for two causes is a choice of this table: a code names the class a rule can act on, and
the `message` keeps the detail. `describe` fails the test of plan 2 if a real refusal has no code here, or maps to a
code that does not describe it.

### Facts of `describe commit`

Types are those the decision allows: a string, a whole number, a boolean, null, or an array of strings. Facts are listed
in the order they are added to the object, which is the order that decides what is omitted at the cap (below).

| Fact | Type | Meaning |
|---|---|---|
| `head` | string or null | the full hash of HEAD; null on a branch with no commit |
| `expected_head` | string or null | the `--expected-head` as given when valid, else null |
| `leave_other_staged` | boolean | whether the option was given |
| `path_count` | whole number | the number of paths named |
| `subject` | string | the subject as given |
| `trailers` | array of strings | the trailers as given |
| `body` | string or null | the body as given, or null when none |
| `attribution_allowed` | boolean | whether the attribution setting allows tool attribution |
| `program_findings` | array of strings | the names, never the values, of the settings, hooks and gitlinks that make git run a program (as `repo_program_findings` returns them) |
| `staged_paths` | array of strings | the paths already staged |
| `requested_paths` | array of strings | the named paths, as given |
| `paths` | array of strings | the same paths after validation; empty when validation refused them |
| `new_paths`, `modified_paths`, `deleted_paths`, `unchanged_paths` | arrays of strings | each path by its change against HEAD, computed from the HEAD blob and the working-tree file without a filter |
| `binary_paths` | array of strings | paths with a NUL byte in the old or new content, whose diff is not given |
| `not_regular_paths` | array of strings | paths that are not a regular file, or that lie under a linked directory |
| `diff` | string | the unified diff of the text paths, `HEAD/<path>` against `work/<path>`, computed by the module without any filter, text conversion or external diff |
| `omitted` | array of strings | the names of facts left out at a cap; empty when `truncated` is false |

The facts are the values the real command acts on: the paths are the ones it would stage, the message is the one it
would write, and HEAD is the one it would compare. The helper does not duplicate the checks it shares with the real
command; it calls them.

### Facts of `describe remove`

| Fact | Type | Meaning |
|---|---|---|
| `confirm` | boolean | whether `--confirm` was given |
| `recursive` | boolean | whether `--recursive` was given |
| `requested_paths` | array of strings | the named paths, as given |
| `target_paths` | array of strings | the paths the real preview lists, in order; empty when validation refused them |
| `file_targets`, `directory_targets`, `link_targets`, `other_targets` | arrays of strings | the targets by kind, the four kinds the real preview reports; a link target is unlinked and its destination is not followed |
| `tracked_targets` | array of strings | targets with at least one tracked file below or at them |
| `ignored_targets` | array of strings | targets that `.gitignore` ignores |
| `ignore_unknown_targets` | array of strings | targets whose ignored status could not be determined (a timeout or an error), never guessed |
| `tracked_file_total` | whole number | the exact number of tracked files at or under all targets |
| `entry_total` | whole number | the number of entries, counting each target and everything below it (files, directories and links), links not followed |
| `size_total` | whole number | the bytes of the regular files under all targets |
| `omitted` | array of strings | as above |

When a tree holds more than 10,000 entries the totals are not complete: `entry_total` and `size_total` are omitted,
named in `omitted`, and `truncated` is true (source: the approver's own bound, `STATS_ENTRY_CAP`). The real command
allows 100,000 entries; a removal between the two always declines and the owner sees the normal prompt.

### Caps and their sources

| Cap | Value | Source and reason |
|---|---|---|
| the serialized object | 196,608 bytes (192 KiB), compact JSON as the module prints it, non-ASCII escaped | the bridge prompt limit less the margin below |
| a string value other than `diff` | 32,768 bytes | the real body limit is 100,000 characters; a body over this is omitted, so a commit with a very long body declines |
| `diff` | 98,304 bytes (96 KiB), measured before escaping | the approver's own cap is 256 KiB in all and 64 KiB for a file, read in pieces; whole-value rule below |
| an array | 200 elements, each at most 1,024 bytes | the approver's outgoing-path cap, 200; the real command allows 2,000 paths |
| a whole number | 0 to 2<sup>53</sup> − 1 | it must survive a JSON reader that uses a double |

The arithmetic. The model bridge accepts a prompt of at most 262,144 bytes (`model-bridge.md`). The facts, the rubric,
the questions and the framing travel in one prompt. Facts: 196,608. Remainder: 262,144 − 196,608 = 65,536. The approver's
rubric file today is 14,166 bytes; twice that is 28,332, which allows the engine's rubric to grow to twice the size of
today's; the check names, the command text and the framing are allowed 8,192. Together 196,608 + 28,332 + 8,192 =
233,132, which leaves 29,012 bytes unused. The object cap, not the sum of the caps of its parts, bounds the prompt: the
parts can add up to more than 196,608 and that is handled by the rule below. The rubric size is the author's estimate
from the approver's file; the engine's plan measures its own and adjusts the cap, not the rule.

**What is left out at a cap.** A value is never cut. Facts are added in the order of the tables. A value that would
exceed a cap above, or that makes the object exceed 196,608 bytes, is not added: its name goes into `omitted`, `truncated`
is true, and later facts are still tried in order. A `diff` that does not fit is therefore omitted in full. The engine
treats `truncated: true` as incomplete and declines (decision 3). In plain words, a very large commit always declines
and the owner then sees the normal prompt. This is the intended price of a complete view: the review never judges a
partial diff.

### Each check of the approver, and where it goes

The checks of today's approver for the rules `claude-workflow-commit`, `safe-git-commit`, `claude-workflow-remove`,
`safe-git-remove` and `git-push` (read on 2026-10-25, role USER, not run). Provenance, role USER, SHA-256: the
approver program `d8b3facdee46432d27547a07865abf024741929ae2d9191e1015ee8280bcd613` (122,474 bytes); its rubric
`49e369d28ee425c66608dcd6540eb9aa945d6ca000a47e48f117ac1a2b172799` (14,166 bytes, the figure used above); the rule files
`claude-workflow-commit` `e7743892a3bb77c034153999478faf131b04446a294accbbb3e5558cc55407c1`, `safe-git-commit`
`dc539ae04d061aa82fb4a494543001d2377525e6f7ff1bafc2a73ee9ce362d4e`, `claude-workflow-remove`
`f7822bfbca84da927bbe04564ff2589ce8df7bd7587fb7eed38b73f2b4ec84e9`, `safe-git-remove`
`560f4edcc281d40f745b9f990cefbff0ba9593166101e55a632696f6dcd4b5b2` and `git-push`
`11a01a007a99bd3e79fe4e9f3ac25da0c3706770478260ee9c1f0288a6f5f3cf`. The caps quoted from the approver (256 KiB in all,
64 KiB for a file, 200 outgoing paths, 10,000 entries) are its constants `DIFF_CAP_TOTAL`, `DIFF_CAP_PER_FILE`,
`OUTGOING_PATH_CAP` and `STATS_ENTRY_CAP` as read. "Engine" is a check the engine makes in code
over facts; "rubric" is a question the model answers over facts. Every check has a counterpart for a commit and a
removal. One bound is narrower: the approver reads a diff up to 256 KiB in all, and `describe` gives one of at most
96 KiB, so a commit whose diff lies between the two is reviewed today and declines under `describe` (the owner sees the
normal prompt). The owner may raise the `diff` cap; the object cap and the rubric margin above are the limit.

| Approver check | Action | Counterpart |
|---|---|---|
| `head_matches` | commit | engine: `head` equals `expected_head`; also error `head_mismatch` |
| `repo_config_safe` | commit | engine: `program_findings` is empty; also error `repo_selects_program` |
| `staging_state_ok` | commit | engine: `staged_paths` and `leave_other_staged`; also errors `index_has_staged_changes`, `path_already_staged` |
| `paths_valid` | commit | `ok` and the path errors |
| `message_valid` | commit | `ok` and the message errors |
| `paths_not_credentials` | commit | engine: its credential-name list over `requested_paths` and `paths` (the list moves from the approver to rule data) |
| `paths_regular` | commit | engine: `not_regular_paths` is empty |
| `facts_complete` | commit | engine: `truncated` is false and `binary_paths` is empty |
| `no_secret_lines` | commit | engine: its secret scan over `diff`, `subject`, `body` and `trailers`, before anything goes to a bridge; a hit withholds the diff |
| `message_matches_change` | commit | rubric over `subject`, `body`, `trailers`, `paths` and `diff` |
| `scope_is_coherent` | commit | rubric over `paths` and `diff` |
| `change_is_safe_in_itself` | commit | rubric over `diff` and the change lists |
| `no_reviewer_directed_text` | commit | rubric over `subject`, `body`, `trailers` and `diff`; the approver's list of reviewer-facing paths is rule data over `paths` |
| (completeness) | remove | engine: `truncated` is false, as for a commit |
| `confirm_present` | remove | engine: `confirm` is true |
| `removal_valid` | remove | `ok` and the removal errors |
| `ignore_status_known` | remove | engine: `ignore_unknown_targets` is empty |
| `preview_matches_arguments` | remove | engine: `target_paths` equals `requested_paths` |
| `no_git_metadata` | remove | engine: no segment of `requested_paths` is `.git`, folded; also errors `path_refused` and `git_metadata_refused` |
| `targets_look_disposable`, `scope_is_narrow`, `no_reviewer_directed_text` | remove | rubric over the target lists, the counts and `requested_paths` |

**The push gap.** `push-check` is the module's read for `git push`. It gives `remote`, `branch`, `target`,
`default_branch`, `base`, `ahead`, `changed_paths`, `findings` and `truncated`. Of the approver's checks for
`git-push`, these have a counterpart today: `facts_complete` (`truncated`), `outgoing_paths_not_credentials`
(engine over `changed_paths`, at most 500), `no_secret_lines` in part (`findings`, six narrow patterns against the
approver's wider scan) and `destination_is_appropriate` (`remote`, `branch`, `default_branch`). These have none:

- `repo_config_safe` for a push: the approver also refuses credential helpers, a git proxy, an askpass program, a
  receive-pack or vcs setting and an ssh variant; `push-check` refuses only what `commit` refuses.
- `remote_is_configured` and `remote_transport_safe`: `push-check` does not report whether the remote is configured, its
  URL scheme, or whether the URL embeds credentials.
- `push_target_known`: it takes the target to be the current branch; it does not read `push.default`, `pushRemote`,
  `remote.<name>.push` or the refspecs of the command.
- `no_force_push`, `no_delete_push`, `no_tag_push`: these depend on the flags and refspecs of the command and on
  `push.followTags` and `remote.<name>.mirror`. The flags are in the command text, which the engine reads itself;
  the configuration is not reported.
- `outgoing_known` in part, and `outgoing_trusted`: `ahead` and `base` are given, but not whether the tracking ref
  looks written by git (the approver reads its reflog).
- `commits_match_the_branch_purpose`, `change_is_safe_in_itself`, `no_reviewer_directed_text` for a push: they need the
  outgoing commit messages and the outgoing diff, which `push-check` does not give.

The gap is not designed here. A later plan extends `push-check`, or adds a `describe push`, to cover it; the split in
`action-review.md` has a step for it (Increment D records it). Until then a push stays with the approver.

### Acceptance criteria for the plan that builds `describe`

- For each action the facts equal what the real command acts on: a test builds one repository state and compares the
  `paths`, the message and `head` of `describe commit` with the commit the real command makes, and `target_paths` of
  `describe remove` with the real preview; `entry_total` is checked against a count made by the test, since the real
  preview reports `entries` only below a directory.
- The repository is byte for byte the same after the call, for every case of the tests: files, index, refs, hooks and
  configuration.
- Every refusal in the "Errors" table has a test that gives it and shows `ok: false` and that code, and the real
  command refuses the same input.
- A value over a cap is omitted whole, named in `omitted`, and `truncated` is true; no string in `facts` is a cut
  string; a diff over 98,304 bytes is omitted in full.
- The output obeys the decision's field rules: the types, the bounds on `code` and `message`, `ok` true only with no
  error, and no extra field.
- A repository whose configuration selects a program (a hook, a filter, a file system monitor, a gitlink with its own configuration), for `describe remove` as well as
`describe commit`, never
  starts that program during `describe`: a test with a program that writes a marker file finds no marker.
- Each overlap named in "Errors" gives the code the table says: a plain `.git` segment gives `path_refused` for both
  actions; a link on the way gives `path_not_a_file` for a commit and `path_refused` for a removal; `contract` is 1.
- An object of exactly 196,608 bytes is accepted and one byte more omits the value that crosses it; `omitted` lists
  names in the order of the tables.

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
