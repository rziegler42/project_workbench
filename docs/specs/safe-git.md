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
  reads are the fixed shapes `push-check` uses and the few more that `describe` adds (see "Describe"). A push is a checkpoint that a process module builds
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
| commands | `safe-git`, whose first argument is `commit`, `remove`, `push-check` or `describe` (kit 1), with `describes: ["remove", "commit", "push"]` (see "Describe"). |

It is run as `wb run safe-git commit`, `wb run safe-git remove`, `wb run safe-git push-check` and `wb run safe-git
describe commit|remove`. The installer pins the helper when the
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

## Describe *(built by plans `2026-10-25-safe-git-describe` and, for a push, `2026-10-26-safe-git-describe-push`)*

`wb run safe-git describe commit ...` and `wb run safe-git describe remove ...` take exactly the arguments of the real
`commit` and `remove` and report what the real command would act on, as the accepted decision
`2026-10-25-describe-interface-for-action-review` requires. This section is what that decision left to the module:
the names and types of the facts, the refusals as error codes, the numeric caps with their sources, and the
counterpart of each check of the owner's approver. The helper builds it, and the command declares `describe` among its
`arguments` and `describes: ["remove", "commit", "push"]` (`module-boundary.md`, "Declaration schema"). "As built, and its
limits" lists where the helper differs from, or adds to, the text below.

**What `describe` does.** It runs the same parsing and validation as the real command, in the same order, up to the
last step that changes anything, and then stops. For `commit` it runs everything through `git diff --check` of the
named paths; it stages nothing, runs no `git add`, `git commit` or `_unstage`, and writes no file. For `remove` it
runs `plan_removal`, which is the real preview, and deletes nothing. It runs git only in the fixed argument
shapes of the helper. The facts need three reads that `push-check` has no shape for, and the helper adds exactly those
shapes to the allowlist: `cat-file -s` and `cat-file blob` of `HEAD:<path>`, `check-ignore -q`, and `ls-files -z` of a
path. A fourth, `check-attr -z filter ident working-tree-encoding`, is also run by the real `commit` (see
`path_converts_on_add`). They were new surface, and the security pass of the plan covered them. A refusal the real command would give is returned as `ok: false` with an error, and the
exit status of `describe` is 0. The refusals with exit 1 and no object are a `describe` call whose first argument is
not `commit`, `remove` or `push`, and, as built, a refusal that has no code in the table or an `OSError` outside the handled
sites (an unreadable directory under a removal target, for example), which the real `remove` also ends with exit 1.
Everything else, a missing repository included, is an object with `ok: false`.
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
| commit | `path_converts_on_add` | a named path has a `filter`, `ident` or `working-tree-encoding` attribute set to a value (anything but unset or unspecified), so `git add` would store other bytes than the work tree holds; asked of `git check-attr -z` before `git diff --check`, by the real command too; an answer that does not match the paths and attributes asked for gives `repository_unreadable` |
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
the `message` keeps the detail. `describe` failed the test of plan 2 if a real refusal had no code here, or maps to a
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
| `binary_paths` | array of strings | paths with a NUL byte or bytes that are not UTF-8 in the old or new content, whose diff is not given |
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

The checks of the approver's rule `git-push`, and where each goes in `describe push` (below). "Engine" is a
check the engine makes in code over facts; "rubric" is a question the model answers over facts.

| Approver check | Action | Counterpart |
|---|---|---|
| `facts_complete` | push | engine: `truncated` is false and `binary_paths` and `submodule_paths` are empty |
| `outgoing_paths_not_credentials` | push | engine: its credential-name list over `changed_paths`, which includes deleted paths (at most 200; more sets `truncated`) |
| `no_secret_lines` | push | engine: its secret scan over `diff` and `commit_messages`, before anything goes to a bridge; `findings` (the six narrow patterns of `push-check`, rule names, a line and a path, never the matched text, read over each commit as well as the net diff, so a secret added and removed inside the range is seen) is also read by the engine, and a non-empty `findings` declines |
| `destination_is_appropriate` | push | rubric over `remote`, `branch`, `default_branch`, `push_updates` and `push_deletes` |
| `repo_config_safe` | push | engine: `push_config_findings` has no entry of repository scope; also errors `repo_selects_program` and `push_config_refused` |
| `remote_is_configured` | push | error `remote_unconfigured`; the engine reads `ok` |
| `remote_transport_safe` | push | engine: `remote_scheme` is in the rule's list and `remote_url_has_credentials` is false |
| `push_target_known` | push | engine: exactly one of `push_updates` and `push_deletes` is non-empty; also error `target_unresolved` |
| `no_force_push` | push | engine: `force` is false and `push_forced` is empty |
| `no_delete_push` | push | engine: `delete` is false and `push_deletes` is empty |
| `no_tag_push` | push | engine: no destination in `push_updates` or `push_deletes` is under `refs/tags/` |
| `outgoing_known` | push | engine: for an update, `base` is not null and `ahead` is given; a deletion has no range (`base` null, `ahead` 0); also error `base_unresolved` |
| `outgoing_trusted` | push | engine: `tracking_ref_reflog_looks_git_written` is true; a heuristic (below), so a false or null value declines and a true value proves nothing |
| `commits_match_the_branch_purpose`, `change_is_safe_in_itself`, `no_reviewer_directed_text` | push | rubric over `commit_messages`, `branch` and `diff` |

### `describe push`

`wb run safe-git describe push <the arguments that follow git push>` reports what that push would ask the remote to do.
It departs from the accepted `2026-10-25-describe-interface-for-action-review` in one way, which the record
`2026-10-26-describe-push-takes-the-push-arguments` (Accepted) narrows for a push only: `safe-git` does not run `git
push`, so there is no real command in the module to take the arguments of or to share validation with. The arguments are
those of `git push`, and the validation is the parser below. The rest of the interface is as for `commit` and `remove`:
one JSON object (`contract`, `action` equal to `push`, `ok`, `truncated`, `errors`, `facts`), exit 0 for an object, the
types and caps of the decision, and the omission rule below. It reads local refs and configuration only, never contacts
a remote, runs `git push` or any program the repository selects, and changes nothing. It is built by the plan
`2026-10-26-safe-git-describe-push`; "As built, and its limits" says where the helper differs from this text.

**The grammar.** `describe push [<flag>...] [<remote> [<refspec>...]]`, in that order, with no `--`. Anything not listed
is refused with the code `usage` (and no fact), including an option given twice (but `-f` with `--force-with-lease` is accepted, as git accepts it), a value for a flag
that takes none, and a short flag combined with another (`-fu`).

- Flags: `-f` and `--force`; `--force-with-lease` (bare: it applies to the destination, and a form with `=` is refused);
  `-d` and `--delete`; `-u` and `--set-upstream`; `--no-verify`; `-n` and `--dry-run`; `--atomic`; `-q` and `--quiet`;
  `-v` and `--verbose`. Refused with the code `remote_state_required` because what they send depends on the remote's
  refs: `--mirror` and `--follow-tags`. Refused as `usage`: `--all` and `--tags` (each sends more than one source, whose
  outgoing commits this version does not describe), `--prune`, `--repo`, `-o` and `--push-option`, `--receive-pack` and
  `--exec` (they name a program), `--signed`, `--recurse-submodules`, `--porcelain`, `--force-if-includes`, and any other
  option.
- Remote: a name matching `[A-Za-z0-9_][A-Za-z0-9._-]{0,63}` that holds no `..` and does not end in `.` or `.lock` (names git
  would refuse). A URL or a path is `usage`; a valid name with no URL is
  `remote_unconfigured`. With no remote the remote is the one git would use: `branch.<name>.pushRemote`, then
  `remote.pushDefault`, then `branch.<name>.remote`, then `origin`.
- Refspec, so that one range of commits is sent: **one update, or deletions only**. An update is one refspec,
  `[+]<source>:<destination>` or `<name>` (source and destination alike); its source must be `HEAD`, the current branch's
  short name or `refs/heads/<that name>`, and any other source (another branch, a tag, a commit) is `usage` in this
  version, because the outgoing commits would not be `<base>..HEAD`. A deletion is `--delete <destination>...` or
  `:<destination>` refspecs; a deletion is never mixed with an update, and `--delete` with no destination is `usage`. A
  destination is a full ref name under `refs/heads/` or `refs/tags/`, or a bare name that the helper qualifies from the
  source (a branch gives `refs/heads/`); Git also looks on the remote for an unambiguous match, so a bare name can mean
  another ref there, which is a recorded limit. A refspec in `remote.<name>.push` whose source is not the current branch
  is `target_unresolved` (the caller gave no argument to blame). A refspec with `*` (a wildcard), here or in `remote.<name>.push`, is
  `remote_state_required`; one with a leading `^`, a `:` in a destination or a name outside the characters the helper
  reads for a branch is `usage`; a source name that is both a branch and a tag is `target_unresolved`.
- With no refspec, `remote.<name>.push` decides when it holds exactly one refspec (more than one is `target_unresolved`),
  else `push.default`. The helper resolves a case only where it is sure which ref Git would push and gives
  `target_unresolved` wherever Git would refuse or the answer needs the remote. As built, checked against `git push
  --porcelain` to a bare repository: `current` gives the current branch to the same name; `simple` and `upstream` (also
  `tracking`) need the upstream on the push remote, and when the push remote is not the branch's own (its
  `branch.<name>.remote`, else `origin`) `simple` acts as `current` (a triangular workflow) and `upstream` is
  `target_unresolved`; `upstream` gives `branch.<name>.merge` when it is set on this remote; `nothing` and the unset cases
  give `target_unresolved`; `matching` is `remote_state_required`. `push.autoSetupRemote` changes the upstream after a
  push and not the target. A bare name in a deletion (`--delete x`, `:x`) is `target_unresolved`, since the remote could
  read it as a branch or a tag; a bare destination of an update that starts with `heads/`, `tags/` or `remotes/` is too.

**The range.** For an update, `base` is the tracking ref `refs/remotes/<remote>/<destination branch>` when it exists, else
the tracking ref of the remote's default branch, as `push-check` resolves it (a new branch is therefore compared with the
default branch), and the range is `<base>..HEAD`; with neither, `base_unresolved`. For a deletion there is no range: `base`
is null, `ahead` is 0, the lists of commits, paths and findings are empty, and `diff` is the empty string. An update to a
destination under `refs/tags/` uses the same `base` rule, so it is compared with the default branch's tracking ref. The
range is read from local tracking refs, which can be stale or forged, as the fact `base` says. The tracking ref whose
reflog `tracking_ref_reflog_looks_git_written` reads is the one that gave `base`; it is null for a deletion.

**Resolution and the remote.** The facts about a remote come from the effective push URL, the one `git remote get-url
--push --all <remote>` reports after `pushurl` and the rewrite rules, and never the fetch URL. More than one line of
output is `multiple_push_urls`. The URL is read inside the helper and never printed, in a fact or an error message: only
its scheme and a boolean are. No `usage` message quotes an argument either, since a remote argument can be a URL with a
credential; a test covers it. A URL that uses a transport helper (`ext::` or any `<helper>::` form) starts a program and is
`repo_selects_program`, with the finding `remote:helper-transport`. Configuration is read with its scope (`git config
--list --show-scope -z`, which follows `include.path` as git does); the scopes are system, global, local, worktree and
command; the helper's scrubbed environment sets three command-scope keys (`core.fsmonitor`, `maintenance.auto`, `gc.auto`), none of which is read, and worktree counts as repository scope. A setting of
repository scope that would run a program, redirect, intercept or re-route the credentials of the push is refused with
`repo_selects_program` (the settings `commit` already refuses: a hook, `core.sshCommand`, `core.gitProxy`, `core.askPass`, a
credential helper, a file system monitor) or `push_config_refused` (the others): every key of the sections `http`,
`protocol`, `credential` and `transfer` (a header, a cookie file, a certificate, a resolver, a redirect, a user name, a
transport allowed), `url.<base>.insteadOf` and `url.<base>.pushInsteadOf`, `remote.<name>.pushurl`, `remote.<name>.proxy`,
`receivepack`, `vcs` and `pushOption`, `ssh.variant`, `push.gpgSign` (when true), `push.pushOption`, `push.recurseSubmodules` and
`push.negotiate`. The message names `<scope>:<section>.<variable>` and never a value or a host. The same keys at user or
system scope, such as the credential helper of the owner's keychain, are only named in `push_config_findings` with their
scope, because refusing them would decline every push (the scope `unknown` that Apple Git gives its system file is
therefore trusted; the security pass found no way for a repository to produce it, since an include takes the scope of the file that includes it). A key
with a subsection (`credential.<url>.helper`, `http.<url>.proxy`, `url.<base>.insteadOf`) can carry a URL, so it is named
without the subsection (`credential.*.helper`), in a fact and in any message. A repository that sets even a harmless key of
those sections (`http.postBuffer`, `transfer.fsckObjects`) is refused, with the key named: a push URL or a rewrite belongs
in the owner's configuration. A remote that only the owner's configuration defines is not one git reads (`get-url` needs
the remote named in the repository), so such a push URL needs a repository key for the remote too (`remote.<name>.fetch`).
`push.followTags` and `remote.<name>.mirror` are `remote_state_required`.

**The git shapes it adds** to the allowlist, each with fixed arguments, literal pathspecs, and the helper's scrubbed
environment, which sets `GIT_OPTIONAL_LOCKS=0` for every run: `config --list --show-scope -z`, `remote get-url --push --all
<remote>`, `rev-parse` and `show-ref --verify --hash` of the refs named above, `symbolic-ref` as `push-check` runs it,
`reflog show -z --no-show-signature --format=%gs <tracking ref> --`, `rev-list --count` of the range, `log -z --reverse
--topo-order --no-show-signature --encoding=UTF-8 --format=%H%n%B <base>..HEAD` for the commits and their messages,
`cat-file commit <40 hex>` (a NUL check, below), `diff --raw -z --no-renames --no-ext-diff --no-textconv
--ignore-submodules=none <base>..HEAD` for `changed_paths` and `submodule_paths`, and a text patch (`--text --no-ext-diff
--no-textconv --ignore-submodules=all --no-renames --no-color -U3`) for `diff` and `binary_paths`; the scan for credentials
runs the `push-check` patch shapes, which gain `--inter-hunk-context=0`. `--ignore-submodules=none` is allowed only on a
`--raw` diff of a range: `submodule.<name>.ignore` and `diff.ignoreSubmodules` hide a changed gitlink otherwise, and a diff
of the work tree with it would enter a nested repository and read its configuration. The security pass covered them.

**The engine and the command text.** The engine parses the prompted command once under its own grammar and passes the
tokens that follow `git push` to `describe push` unchanged, as it does for `commit` (the rule's key is the spelling `git
push`). A flag or option before `push` (`git -C`, `git -c k=v`, `--git-dir`) or an environment prefix is outside the
rule's declared flags, so the engine refuses to review it (unknown means unreviewed). The facts the helper reports are
what the checks read; the engine's own parse only decides what is passed.

**Facts of `describe push`**, in the order they are added (the order that decides what is omitted at the cap):

| Fact | Type | Meaning |
|---|---|---|
| `head` | string or null | the full hash of HEAD; null where a refusal prevented it |
| `branch` | string or null | the current branch |
| `remote` | string or null | the remote, as resolved |
| `default_branch` | string or null | the remote's default branch, from `refs/remotes/<remote>/HEAD`, else null |
| `force`, `delete`, `set_upstream`, `no_verify`, `dry_run`, `atomic` | boolean | whether the flag was given (`force` is true for `-f`, `--force` and `--force-with-lease`); all false after a `usage` refusal |
| `remote_scheme` | string or null | `https`, `http`, `ssh` (also the scp-like form), `git`, `file` (also a path) or `other`; null when there is no URL. `file` does not tell a path from `file://`, and the host is not reported |
| `remote_url_has_credentials` | boolean | whether the effective push URL has a password, or any user information on `http`, `https` or `ftp`, or user information that matches a pattern of `push-check`; a bare user name on `ssh` or `git` is false. A lower bound: a credential in another form is not seen |
| `push_config_findings` | array of strings | `<scope>:<section>.<variable>` of each setting named above, in any scope, sorted and without repeats, a subsectioned key without its subsection (`credential.*.helper`); never a value |
| `push_updates` | array of strings | one `<source>:<destination>` for each ref the push asks to update, the source a ref name or a commit hash, the destination a full ref |
| `push_deletes` | array of strings | the full refs the push asks to delete, by `--delete` or an empty-source refspec |
| `push_forced` | array of strings | the destinations a force flag or a `+` applies to |
| `base` | string or null | the full hash of the base of the range (see "The range"); null for a deletion |
| `ahead` | whole number or null | the commits in `<base>..HEAD`; 0 for a deletion |
| `tracking_ref_reflog_looks_git_written` | boolean or null | a heuristic: true when every entry of the reflog of the tracking ref has a message beginning `fetch`, `push` or `update by push`; false otherwise; null when there is no reflog or one empty entry (a tracking ref written by `clone` or `pull` is false). A reflog is local and cannot show who wrote a ref, so a true value is untrusted evidence and a forged reflog passes it |
| `commit_hashes`, `commit_messages` | arrays of strings | the commits of the range, oldest first, and their messages in the same order, merges included; at most 200, each message at most 1,024 bytes. Both are left out when a commit object holds a NUL: git's own output stops at it and still ends the record, so bytes after it would be pushed and neither shown nor scanned |
| `changed_paths` | array of strings | the paths the range changes, deleted paths included, at most 200 |
| `binary_paths` | array of strings | changed paths whose patch holds a NUL or bytes that are not UTF-8 (context lines included); their hunks are not in `diff` |
| `submodule_paths` | array of strings | changed paths that are a gitlink (mode 160000); `diff` does not enter a submodule. A gitlink in the index is already `repo_selects_program`, so this is non-empty only where the index no longer holds the link |
| `findings` | array of strings | `<rule> <line> <path>` for each credential-looking added line of `push-check`'s six patterns, read over each commit and over the net change; no matched text |
| `diff` | string | the net unified diff of the two trees (`<base>` against HEAD) with three lines of context, which count toward the cap, `a/<path>` against `b/<path>`, of the text paths, built under the limits of `describe commit` and without a filter, text conversion or external diff; a mode change is a line of it. Empty for a deletion |
| `omitted` | array of strings | as above |

The facts make no claim whether a ref exists on the remote, whether the push would succeed, or what the remote holds.
`errors` holds the refusals under the grammar and the local data; it cannot hold a refusal that Git or the remote makes
at push time (a non-fast-forward update, a remote hook, a permission), which `describe` cannot know.

**New error codes** (in addition to `usage`, `repository_unreadable` and `repo_selects_program`, which apply as above):

| Code | The real refusal |
|---|---|
| `branch_unborn` | the current branch has no commit |
| `head_detached` | HEAD is detached |
| `branch_unreadable` | a branch name outside the characters the helper reads |
| `base_unresolved` | no base to compare with (`push-check`'s message, with the refs tried) |
| `remote_unconfigured` | the remote has no URL |
| `remote_state_required` | `--mirror`, `--follow-tags`, `push.followTags`, `remote.<name>.mirror`, `push.default` `matching`, a wildcard refspec (on the command line or in `remote.<name>.push`), or any form whose targets depend on the remote's refs |
| `multiple_push_urls` | the remote has more than one effective push URL |
| `target_unresolved` | a destination that cannot be qualified or found from local data, a source that is both a branch and a tag, more than one refspec in `remote.<name>.push`, a `push.default` case Git would refuse, or `push.default` `nothing` |
| `push_config_refused` | a setting of repository scope that redirects or intercepts the push and is not already `repo_selects_program` |

**Caps** are those of `describe commit` (object 196,608 bytes, string 32,768, `diff` 98,304 before escaping, array 200
elements of at most 1,024 bytes), with the changed paths at 200 where `push-check` lists 500 and the commits at 200. A
value over a cap is omitted whole, named in `omitted`, and `truncated` is true; a range of more than 200 commits omits
both commit lists. A message over 1,024 bytes omits `commit_messages` whole, so a push of a commit with a long body
declines: the same intended price as a long body in `describe commit`, which the owner may change by raising the element
cap for messages. The engine treats `truncated: true` as incomplete and declines.

**What stays with the approver.** A push that needs `--mirror`, `--follow-tags`, `--all`, `--tags`, a source other than
the current branch, a wildcard refspec, `push.default` `matching`, the remote's own refs or several push URLs cannot be
described and stays at the normal prompt until a later plan adds a defined read of the remote or more than one source.
The engine's rule for a push is a later plan. Not described either, as limits: the host of the remote; a bare destination
that the remote would resolve to another ref; the behaviour of Git for each `push.default` case on other versions than
2.54.0.

**The push gap, as it stood, now closed by `describe push`.** `push-check` gives `remote`, `branch`, `target`, `default_branch`, `base`, `ahead`,
`changed_paths`, `findings` and `truncated`. It never saw the flags and refspecs of the push, the push configuration, the
remote's transport, the outgoing commit messages or the outgoing diff. `describe push` supplies each; the table above
maps every check of the approver's `git-push` rule to a fact. `push-check` is unchanged and stays for the `push-changes`
skill.

### Acceptance criteria of plan `2026-10-25-safe-git-describe`

These were the criteria of the plan; its Result records the tests that meet them.

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
- Built, from plan `2026-10-25-safe-git-describe`: `describe commit` and `describe remove` as specified in "Describe",
  with the 32 error codes of the table (`path_converts_on_add` was added by the security pass), and the launcher rule for a declared
  action. The command declares `describes: ["remove", "commit", "push"]`, in that order. Where the helper differs from the
  draft text or adds to it:
  - Contents are compared byte for byte, without a filter. A side with a NUL or bytes that are not UTF-8 is listed in
    `binary_paths` and its diff is withheld. A side over 262,144 bytes (the approver's whole-diff bound) is not read:
    the path is listed new, deleted or modified without being compared, `diff` is omitted and `truncated` is true; the path is not in `binary_paths`, so that list
    is complete only when `truncated` is false. A change of the
    executable bit is a modification, with a line `mode HEAD/<path> <old|none> -> work/<path> <new|none>` in the diff.
  - A path in the index whose `HEAD:<path>` object cannot be sized is taken as absent from HEAD only for an
    intent-to-add entry (the empty blob); otherwise it gives `repository_unreadable`.
  - The diff is built by the module from `difflib` after the lines both sides share at the start and the end are set
    aside. A side with more than 500 differing lines is not compared, and all the diffs of one call share a budget of
    20 seconds; either limit omits `diff` and sets `truncated`.
  - A value is printed as ASCII with a lone surrogate written as its escape text, so a strict JSON reader accepts it.
  - The size of the object is the printed line, newline included. On a refused `describe remove`, `entry_total` and
    `size_total` are omitted and named, and `tracked_file_total` is null.
  - `expected_head` is the string as given once it is valid (so `none` for `none`) and null before; after a usage
    refusal `subject`, `body`, `trailers` and `expected_head` are null or empty even when given.
  - The real `commit` runs `git diff --check` with `GIT_OPTIONAL_LOCKS=0` (every git run of the helper has it set now).
- Limits of `describe`, recorded by the security pass and the reviews of that plan:
  - Attributes other than the three it refuses are not read: `text`, `eol`, `crlf`, `core.autocrlf` and `core.eol`
    change line endings on `git add`, so `describe` shows the work tree's bytes where the real command stores converted
    ones. The difference is whitespace only; a path can be listed modified or unchanged accordingly. Likewise
    `core.fileMode=false` can make a path modified for `describe` that `git add` would not stage; the real command then
    refuses at staging.
  - `git check-attr` prints a literal value `unspecified` or `unset` as it prints the state, so a repository line
    `filter=unspecified` is not refused; it would run a filter of that name only if the owner's own global configuration
    defines one (a repository's own filter is refused by `repo_selects_program`).
  - A `.gitattributes` or work-tree change between `describe` and the real command is the race already accepted.
  - The time budget is checked between files, so one call can take the budget plus one comparison (about 0.6 s at the
    bound). Each of up to 2,000 paths costs two git runs (about 26 ms each in the pass, so about 52 s for 2,000);
    nothing bounds that total.
  - A `describe remove` target that the `check-ignore` shape refuses (a leading colon or a backslash) can be listed in
    `ignore_unknown_targets`, because its ignore status is not asked.
  - Not checked: a full run of 2,000 paths, `wb launch` through a real pin, a SHA-256 repository, and the engine's use of
    the facts (plan 3 of the split in `action-review.md`). The push gap is closed by `describe push` (see below).
- Built, from plan `2026-10-26-safe-git-describe-push` (increments B to F): `describe push` as specified in "`describe push`",
  with an adversarial security pass (increment F) whose findings were fixed and tested, or recorded below. Where the helper differs from the
  text first written, or adds to it, and what it does not do:
  - The target: a first path component `heads`, `tags` or `remotes` in a bare destination, and a bare name in a deletion, are
    `target_unresolved`; a triangular `simple` acts as `current`; a destination is echoed in the facts (`push_updates`,
    `push_deletes`, `push_forced`), so no `usage` message quotes an argument but a fact does. `--tags` and `--all` are
    `usage`, as the grammar says (the plan's wording of increment D lists them differently).
  - `diff` and `changed_paths` are the net difference of the two trees, with three lines of context that count toward the
    cap; for a diverged branch they also show the reverse of the commits only the remote holds. `rev-list --no-merges` is
    not used, so merges are in the commit lists. The binary test covers the whole patch of a file, context included. A diff
    slower than 20 seconds is `repository_unreadable`, not an omitted diff, and no shared budget spans the calls (up to 200
    `cat-file` calls for the NUL check). No test covers the 8 MB cut of a read or a timeout of the patch.
  - Order and shape of the answer: the checks run in this order and the first refusal is the only error: the grammar
    (`usage`, `remote_state_required` for `--mirror` and `--follow-tags` before the flags are recorded, so `-f --mirror`
    shows `force` false and `origin --mirror` is `usage`), program settings of the repository, branch, remote, settings that
    redirect the push, the URL, `push.followTags` and `remote.<name>.mirror`, the targets, the base. A malformed
    `push.default` or `remote.<name>.push` makes git itself fail, so it is `repository_unreadable`; the `target_unresolved`
    branch for an unknown `push.default` is a guard that cannot be reached. An empty `pushurl` reads as a path (`file`).
    `config --list --show-scope` needs Git 2.26. The names in `push_config_findings` are cut (variable 40, scope 20
    characters). `tracking_ref_reflog_looks_git_written` and the commit lists are left out of the object when their read is
    cut. If the patch cannot be matched to the raw listing, `diff` and `binary_paths` are omitted and `changed_paths` kept.
    The shared `show-ref` shape also reads `refs/tags/<name>` now, so `push-check` can run it (its own `--base` still
    refuses a tag).
  - `findings` is read over each commit and over the net change with `--inter-hunk-context=0`; a token segment longer than
    4,096 characters is not seen by the `jwt-shaped` rule.
  - The reflog fact declines a ref written by `clone` or `pull` and is forgeable by whoever writes the repository.
  - The deny-list of repository settings is by section and is wider than the first text; it refuses harmless keys of those
    sections. `remote.<name>.proxyAuthMethod` is not named. `diff.orderFile` (and any setting naming a file git reads) is not
    refused: a FIFO there stalls a read for the time limit and ends as `repository_unreadable`. Git's own message is no longer
    repeated in a `repository_unreadable` error (it could quote a repository value), so only the command and exit code show.
  - A raw control character in a path or message is JSON-escaped, not removed. `describe` runs in the helper's scrubbed
    environment; a real `git push` runs in the agent's own, so an exported `GIT_DIR`, `GIT_SSH_COMMAND` or `GIT_CONFIG_*`
    makes the two differ (the engine refuses an inline prefix only).
  - An `other` scheme can start `git-remote-<scheme>` from the trusted `PATH`; `git+ssh://` is `other` and `SSH://` is `ssh`;
    a URL with a newline reads as several URLs. `describe commit` shows a subsectioned program key in its
    `repo_selects_program` message as `repo_program_findings` returns it, which `describe push` redacts.
  - `push-check` is unchanged except that it shares the credential scan (now with `--inter-hunk-context=0`) and prints a
    different refusal for a branch name too long to read.
  - Not checked: a repository of another owner (`safe.directory`), a hostile commit-graph or pack index, a case-folding file
    system, the engine's own deadline, and the credential flow of a real push. The owner's remaining step after the plan is
    `wb acknowledge` and `wb upgrade --package packages/workbench`.
- The shipped approvals (`workbench/shipped_approvals/packages/`) are re-written by the owner's `release-approvals`
  after any change under `packages/workbench/`, and the new records are committed with that change. The edit gate
  refuses every edit until the owner has done so, so a change to the package is built and tested in a copy and landed
  with one copy.
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
