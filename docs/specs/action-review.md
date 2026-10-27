# action-review

Status: Draft. A design for the engine of roadmap candidate `action-review-engine`, written on 2026-10-25 from a
brainstorm in which the owner chose to skip the questions. The owner approved the design as written on 2026-10-25,
after settling the accuracy method, the false-decline bound, the name `describe`, and the fate of `safe-committer`
and `amend-message`. A call marked **(default)** was the author's and is approved with the design but was not
separately chosen; the owner may still change it. The approval is of the design only and approves no plan. The
`describe` interface is a decision record of its own, accepted by the owner on 2026-10-25
(`2026-10-25-describe-interface-for-action-review`). The rule schema, the module's layout and declaration, the bridge setting and the checks for `commit` and `remove` were
written on 2026-10-26 by Increment A of plan `2026-10-26-action-review-engine` and wait for the owner's reading
("The rule schema, the module and the checks"). The status stays `Draft` because the engine, its hook and its log are not built; the `describe` side of `safe-git` (for `commit`, `remove` and `push`) and the launcher rule are (plans `2026-10-25-safe-git-describe` and `2026-10-26-safe-git-describe-push`).

Terms are defined in `terms.md`. The engine sits above the bridge of `model-bridge.md` and beside the engine of
`review-engine.md`. The decision behind it is `2026-10-22-model-calls-go-through-vendor-bridges` (decisions 3, 6, 7
and 8); the authority rules are in `trust-and-approval.md`.

## Purpose and reason

The owner's approver is a program in the user level (item `codex_approver.py` of `global-config-inventory.md`,
role USER). A hook calls it when a command that an `ask` rule prompted for is about to run. It collects facts
about the action, runs fixed checks, asks a model for a verdict against a rubric, logs the verdict and, for two
delegated rules, can allow the command.

It cannot be moved or removed in pieces. Its facts for a commit and a removal come from the global
`claude-workflow` program, loaded as a library (`load_helper`, `collect_commit`, `collect_remove`, read on
2026-10-25, not run). So the program cannot be removed (move M14) without silencing review of every commit, and
the module spellings were added only by a narrow patch that keeps that dependence (accepted option 1a of
`2026-10-25-approver-coverage-for-the-module-commands`). Decision 7 of the vendor-bridges record says facts come
from the module that owns the action and leaves the interface open until this engine is planned. This spec
proposes that interface and the engine around it.

## Goals

1. An engine, `action-review`, that takes facts about one action and returns a verdict with reasons as data,
   from a rubric, fixed checks and rules, calling a model only through a `model-bridge`.
2. A `describe` interface by which the module that owns an action reports the facts, read-only, before the action is
   made. No second copy of the owner's inspection code.
3. The approver's program can be replaced by a thin hook that asks the engine, so M1 stage 2 and M14 can happen
   and the global `claude-workflow` program can go.
4. The review is accurate against the owner's own judgment, not against the approver's verdicts. The owner reports
   that the approver gave many false declines (commands the owner would approve), so agreeing with it is not the
   target. Both errors are counted: a false decline (a safe action stopped) and a false approve (an unsafe action
   let through). A false approve is the worse one. Every kind of command the approver reviews is still reviewed.

## Non-goals and anti-goals

- The engine writes no `allow` rule, no setting and no hook entry, and its verdict authorizes nothing by itself
  (decision 6). A verdict that is missing, malformed, unavailable, timed out or not a verdict approves nothing.
- It is not a reviewer of documents (that is `review-engine`), and it names no vendor.
- It does not move the enforcement point. The hook stays in the owner's own configuration, outside a project's
  reach (`2026-10-24-project-guarantees-a-floor`). The agent does not write the user level.
- It does not widen delegation. Which actions a verdict may stand in for is the owner's personal setting and a
  code constant of the enforcement point, as `DELEGABLE` is today.
- Anti-goals: an engine that approves more than the approver does; a `describe` command that changes anything; facts
  trusted as instructions; a typo in a rule file that silently turns the review off for every command (the
  approver does this today, measured on 2026-10-25).

## The design

### The `describe` interface (default)

A module that owns an action ships a read-only subcommand `describe` beside the action. `wb run safe-git describe
commit <the arguments of commit>` takes exactly the arguments of the real command and prints one JSON object of
the facts that the real command would act on, running the same validation code the real command runs. It makes no
commit, stages nothing, writes nothing and runs no program the repository selects. `describe remove` does the same for
`remove`, extending the `remove` preview it has. `push-check` has part of this shape for a push, and `describe push` the whole of it.

- The object has `contract` (a whole number), `action` (`commit`), `ok`, `truncated` (always present, a boolean),
  `errors` (the refusals the real command would give, as data, not as a failed run) and `facts` (a flat set of named
  values with a size cap). A module documents the names of its facts and its numeric caps in its own spec, and the
  engine's rules name them. A truncated object is incomplete and the verdict is a decline. The field rules and the
  behaviour at the cap are fixed by the accepted decision `2026-10-25-describe-interface-for-action-review`.
- A refusal is a fact: a commit the real helper would refuse is reported as `ok: false` with the reason, and the
  engine's check for it fails the verdict.
- The engine runs `describe` only through the launcher (`wb run`), the same rule decision 4 sets for bridges, and
  only for a command that an installed, pinned module declares as a `describe` provider. Its output is data.
- **Why this shape (default):** the real validation lives in one place and cannot drift; the call is free of side
  effects by construction; it needs no new capability of the launcher beyond running a pinned command. The
  alternative of a `--preview` flag on the action itself was rejected as default because a mistaken flag would run
  the action.

### The engine (default)

A module `action-review` providing the capability of that name (still a proposal), requiring `model-bridge`. One
command, `wb run action-review review`, takes the line of the command to be reviewed and, by that line, finds the
rule, runs the module's `describe`, applies the rule's checks, and only if the checks pass asks the bridge for a
verdict against the rubric. It prints one verdict object: `verdict` (`approve` or `decline`), `failed_checks` and
`reason`, the shape of today's verdict schema. It keeps a log of verdicts as hashes, not command text.

- **Rule properties fixed here; the schema is in "The rule schema, the module and the checks" below.** A rule file has
  a `format` number, and a rule is keyed by one spelling and one subcommand, matched on whole tokens (never a text
  prefix). Two rules with the same key are both refused, and neither reviews anything. A rule that does not load, or
  is ambiguous, refuses only the commands of its own key. Each flag it declares has a type (value, multi, boolean),
  and positionals are declared as exactly one named group. The versioned schema, its field types and bounds and the
  precedence rule were written by Increment A of plan `2026-10-26-action-review-engine`; the tests for malformed and
  overlapping rules are written by that plan's later increments, before the code they test.
- **Rules are data** (a JSON file per rule: the command spelling, the module and the action that `describe`
  reports on, the checks, the rubric section, the review questions). The module and the action are identifiers
  only: a rule holds no command text and no verb. The engine builds the launcher argument list itself, `wb run
  <module> describe <action> <the parsed arguments>`, with the fixed word `describe`. A rule format that can carry
  command text, an extra verb or a path to run is rejected, and a rule that names such a field does not load. **The checks are code in the module** and are fixed: a pure function of the facts.
  A rule can only name a check that exists. This keeps the owner's finding that a rule file is not a place to put
  logic.
- **Fail closed, and loudly.** A rule file that does not load makes `review` refuse that rule with a message the
  hook can show. It never disables the review of other commands. This is a change from the approver.
- **The prompt holds the facts and the rubric; the vendor can still read the project.** Content from a hostile
  repository (a diff, a message) is quoted as data and the rubric keeps the check that refuses text addressed to the
  reviewer (`no_reviewer_directed_text`). That is not an isolation boundary. The bridge starts the vendor program in
  the project, and `model-bridge.md` ("What the vendor program can read") says it can open any file there, including
  untracked scratch and the repository's own instruction files, so repository text can reach the model by that
  route as well. The spec therefore claims only this: the engine puts nothing sensitive in the project for the
  vendor to find (the labelled set is stored outside any project, see below), and it does not rely on the model
  ignoring what it reads. A bridge option for a scratch root with no project content would be a change to
  `model-bridge.md`, which the engine's plan may propose; none exists today.

### The rule schema, the module and the checks (specified by plan `2026-10-26-action-review-engine`, Increment A; not built)

Everything here is the author's text for the owner to read; it is a default until the owner has read it and said to go
on. Marked calls are the author's. Nothing in this section is built.

**The module.** `packages/workbench/action-review/` declares `type` `module`, `provides` `["action-review"]` and
`requires` `["model-bridge"]`. It ships `helper/action-review`, `rules` (a directory of rule files), `rubric` (a
directory holding `rubric.md`) and `reply-schema.json`, so they install at `.workbench/<package>/action-review/<path>`
(`module-contract.md`). It declares one command, `action-review`, with `helper` `helper/action-review`, `runtime`
`python`, `kit` 1 and `arguments` `["review"]`, and no `owner` list: `review` reads and prints and writes nothing, and
the owner's hook calls it. The helper finds its rules, rubric and schema beside itself and never takes a path from the
caller or from a rule. The schema is passed to the bridge as its project-relative installed path, because the bridge
reads `--schema` from inside the project and the engine writes no file.

**The call.** `wb run action-review review [--log-row] <command text>`. The command text is exactly one argument, the
raw text the harness is about to run; the launcher allows at most 4,096 characters, so a longer command is
unreviewable. `--log-row`, if given, comes first. Any other option, a second text, or none is a refusal (exit 1).

**The rule file.** One file per rule in `rules/`, named `<module>-<action>.json` (for example `safe-git-commit.json`),
UTF-8, strict JSON (a duplicate key, `NaN` or a non-object is an error, as for `.workbench/review.json`), at most 16,384
bytes; at most 64 files and 262,144 bytes in all, and a file that is not a regular file is an error. The object has
these fields and no others; a missing required field, an unknown field or a wrong type means the rule does not load.

| Field | Required | Type and bounds |
|---|---|---|
| `format` | yes | the whole number 1 |
| `spelling` | yes | a list of 1 to 4 words, each of the bare-word alphabet of the grammar below, not beginning with `-`, at most 64 characters: the leading words of the prompted command |
| `subcommand` | yes | `^[a-z][a-z0-9-]*$`, at most 32 characters: the word that follows the spelling |
| `module` | yes | the name of the command `describe` is asked of: `^[A-Za-z0-9][A-Za-z0-9._+-]*$`, at most 64 characters. `wb run` takes a command name, so this is that name; for a first-party module whose command carries its name (`safe-git`) it is also the module's name. The engine does not look it up: the launcher decides whether an installed, pinned command of that name exists. |
| `action` | yes | `^[a-z][a-z0-9-]*$`, at most 32 characters: the action `describe` is asked about |
| `flags` | yes (may be empty) | an object of at most 32 entries; a key is `--` and `^[a-z][a-z0-9-]*$` (at most 32 characters after the dashes); a value is `{"type": "value" \| "multi" \| "boolean", "required": true \| false}` with `required` defaulting to false; nothing else |
| `positionals` | yes | exactly one group, `{"name": <form of an action>, "separator": true \| false, "min": 0 to 61, "max": 0 to 61}`, `min` at most `max`; `separator` true means the group follows a lone `--` word that is itself required. The 61 is the kit's ceiling of 64 arguments to `run_command` less the fixed `describe` call's three (`<module> describe <action>`); a command whose parsed arguments pass 61 is unreviewable (exit 1), so a commit of more than about 50 paths is never reviewed |
| `checks` | yes | a list of at most 32 distinct names, each in the engine's fixed list (below); a name not in it means the rule does not load |
| `rubric` | yes | the name of a section of `rubric.md`, `^[a-z][a-z0-9_]*$`, at most 64 characters; the section must exist |
| `questions` | yes (may be empty) | a list of at most 16 distinct names, each `^[a-z][a-z0-9_]*$` and at most 64 characters, each a question defined in the named rubric section; a name not defined there means the rule does not load |
| `lists` | no | an object whose keys are in the engine's fixed list of list names (`credential_names`, `reviewer_facing_paths`) and whose values are lists of at most 256 distinct printable ASCII strings of at most 256 characters; data for the checks that name them, and it is where the approver's credential-name list and its list of reviewer-facing paths move |

A rule holds no command text, no verb and no path to run, and no field has a place for one: the engine builds
`wb run <module> describe <action> <the parsed arguments>` itself, with the fixed word `describe`, and `spelling` is
only what the prompted command is matched against and is never executed or passed on. Two loader rules keep the
reviewed command equal to the one that runs. The `subcommand` must equal the `action` or the rule does not load. And
where `spelling` begins `wb run`, its last word must equal `module` or the rule does not load. For another spelling
(`git push`, when a push rule is added) the equivalence is the module's own `describe` contract, which takes the
arguments of the real command (`describe push` takes those of `git push`, as `safe-git.md` says); that is why a later
push rule needs no change of this format. The file name must equal `<module>-<action>.json` or the rule does not load.

Example, `rules/safe-git-commit.json` (the checks are those of "The checks", below; the lists are abbreviated here):

```json
{"format": 1, "spelling": ["wb", "run", "safe-git"], "subcommand": "commit", "module": "safe-git", "action": "commit",
 "flags": {"--expected-head": {"type": "value", "required": true}, "--subject": {"type": "value", "required": true},
           "--body": {"type": "value"}, "--trailer": {"type": "multi"}, "--leave-other-staged": {"type": "boolean"}},
 "positionals": {"name": "paths", "separator": true, "min": 1, "max": 61},
 "checks": ["head_matches", "repo_config_safe", "staging_state_ok", "paths_valid", "message_valid",
            "paths_not_credentials", "paths_regular", "facts_complete", "no_secret_lines"],
 "rubric": "commit", "questions": ["message_matches_change", "scope_is_coherent", "change_is_safe_in_itself",
                                   "no_reviewer_directed_text"],
 "lists": {"credential_names": [".env", "id_rsa"], "reviewer_facing_paths": ["AGENTS.md", "CLAUDE.md"]}}
```

and `rules/safe-git-remove.json`: `subcommand` and `action` `remove`; `flags` `--confirm` and `--recursive`, both
boolean; `positionals` `paths` with `separator` true, `min` 1 and `max` 61; `checks` `facts_complete`,
`confirm_present`, `removal_valid`, `ignore_status_known`, `preview_matches_arguments` and `no_git_metadata`; `rubric`
`remove`; `questions` `targets_look_disposable`, `scope_is_narrow` and `no_reviewer_directed_text`. The flags of both
rules are those of the real commands in `safe-git.md`; the build checks them against the helper. (The flag names above
are the author's reading and are confirmed against `safe-git` by Increment D.)

Cases that must not load, each with a test: a field outside the table; a missing required field; a `format` other than
1; a `module`, `action` or `spelling` word outside its form; a `subcommand` unequal to `action`; a `wb run` spelling
whose last word is not `module`; a file name that is not `<module>-<action>.json`; a check or list name that is not in
the engine's list; a question the rubric section does not define; a flag of an unknown type; two positional groups or
none; `min` over `max`; an over-long value, list or file; and any field that carries a command line, a verb, a path or
a program name (there is no field for one, so it is an unknown field).

**Matching and precedence.** The prompted command is parsed once under the grammar below into words. A rule matches
when the command's leading words equal `spelling` and the next word equals `subcommand`, whole word against whole word.
There is no precedence and no order among rules. If exactly one rule matches and it loads, it reviews. If no rule
matches, the command is not reviewed: a refusal (exit 1) that names no rule, which is also how a retired action
(`ask-codex archive`, `safe-committer`, `amend-message`) is refused, with no `describe` and no bridge call. If two or
more rules match, or two files carry one key, every one of them is refused and nothing is reviewed under that key. A
rule that does not load refuses only the commands of its own key: its key is read from its `spelling` and `subcommand`
when both are valid, and otherwise from its file name, where a command is refused when two adjacent words among its
first five, joined with a `-`, equal the file's name without `.json`. A rule error is reported with the file name on
standard error, never as a verdict, and does not disturb the review of any other key.

**Flags and positionals.** After the subcommand, a word beginning with `--` is a flag and must be declared by the rule.
A single-quoted word that begins with `-` is refused outright, so a quoted word is never a flag in the engine and a
flag in the real command; `--name=value` is refused as an undeclared flag. A `value` flag takes the next word as its value; a
`multi` flag may repeat and gathers its values in order; a `boolean` flag takes no value; a `value` or `boolean` flag
given twice is a refusal, and so is a `required` flag that is absent, an undeclared flag, a flag with no value, a
second `--` word, and a count of positional words outside `min` and `max`. A bare word that begins with `-` and is not
a declared flag is a refusal. Positional words are those after the lone `--` when `separator` is true, and the bare
words that follow the last flag when it is false. The result is an argument list in the order given, which is passed to
`describe` unchanged; the parse only decides whether the shape fits, and the real validation is `describe`'s.

**The checks.** The engine has a fixed list of code checks, each a pure function of the `describe` object (and, for two,
of a named list), run in the order of the list and not of the rule. A rule may name only checks in the list. `ok:
false` is a fact: each error code maps to the check that would have caught it, and that check fails (a code with no
mapping fails `facts_complete`). The checks for the two actions this plan covers, from `safe-git.md` ("Each check of the
approver, and where it goes"):

| Check | Action | Reads | Fails when | Error codes it also fails on |
|---|---|---|---|---|
| `head_matches` | commit | `head`, `expected_head` | they differ; a null `head` passes only with `expected_head` `none`, and any other null fails | `expected_head_invalid`, `head_mismatch`, `head_unreadable` |
| `repo_config_safe` | commit | `program_findings` | it is not empty | `repo_selects_program`, `operation_in_progress` |
| `staging_state_ok` | commit | `staged_paths`, `leave_other_staged` | something is staged without `leave_other_staged` | `index_has_staged_changes`, `path_already_staged` |
| `paths_valid` | commit | `ok` | a path error | `usage`, `path_refused`, `path_duplicate`, `path_unmerged`, `path_in_nested_repository`, `path_not_a_file`, `path_unknown`, `path_converts_on_add`, `whitespace_errors` |
| `message_valid` | commit | `ok` | a message error | `subject_invalid`, `body_invalid`, `trailer_invalid`, `message_character_refused`, `attribution_refused`, `setting_invalid` |
| `paths_not_credentials` | commit | `requested_paths`, `paths`, list `credential_names` | the final segment of a path, case-folded, equals a listed name, or ends with a listed name that begins with `.` (an extension such as `.pem`) | none |
| `paths_regular` | commit | `not_regular_paths` | it is not empty | none |
| `facts_complete` | commit, remove | `truncated`, and for a commit `binary_paths` | `truncated` is true, or a commit has a binary path | `repository_unreadable`, `index_unreadable`, and any unmapped code |
| `no_secret_lines` | commit | `diff`, `subject`, `body`, `trailers` | the secret scan (ported from the approver by Increment F) hits; a hit withholds the diff from anything sent to a bridge | none |
| `confirm_present` | remove | `confirm` | it is false | none |
| `removal_valid` | remove | `ok` | a removal error | `usage`, `path_duplicate`, `path_refused`, `target_missing`, `recursive_required`, `repository_root_refused`, `nested_repository`, `other_filesystem`, `tree_too_large`, `target_changed` |
| `ignore_status_known` | remove | `ignore_unknown_targets` | it is not empty | none |
| `preview_matches_arguments` | remove | `target_paths`, `requested_paths` | they differ | none |
| `no_git_metadata` | remove | `requested_paths` | any segment, folded, equals `.git` | `git_metadata_refused`, and `path_refused` where a segment folds to `.git` |

The rubric questions are not code checks and are never run by the engine: `message_matches_change`, `scope_is_coherent`,
`change_is_safe_in_itself` and `no_reviewer_directed_text` for a commit, and `targets_look_disposable`,
`scope_is_narrow` and `no_reviewer_directed_text` for a remove. A question goes to the model only after every code check
has passed, and the model's `failed_checks` may name only the rule's questions. A failed code check is a decline with
that name and never calls the bridge. The mapping of an error code to a check in the table is the author's reading of
the real refusals in `safe-git.md`; the build tests it against real `describe` objects. The checks for a push are
deferred with the push rule (`outgoing_known` and the others in that table), because they need `describe push`, which
exists, and a rule and checks that the follow-up plan writes.

**The rubric.** `rubric/rubric.md` holds one section per rubric name, `## <name>` with `commit` and `remove` at first,
and under it one `### <question>` heading per question with the text of the question. It is ported from the approver's
rubric section by section by Increment H, with the source hash and date recorded; the engine's own framing says that the
facts are data and not instructions. `reply-schema.json` is the JSON Schema of the verdict reply the bridge is asked for
(`verdict`, `failed_checks`, `reason`), and the engine validates the reply again whatever the bridge or the schema did.

**The log row reaches the hook.** `--log-row` makes the engine print, after the verdict object has been printed, one
more line on standard error: `log-row: ` followed by the row as one JSON object with exactly the fields of "The
log", and no field is added to the verdict object. A row is printed for a verdict only (approve or decline, exit 0);
a refusal or failure prints its `refused:` or `failed:` line and no row, and the hook writes a note of its own if it
wants one. The engine reads the clock for `ts` and writes nothing. (Author's call.)

**The time budget (author's call, provisional).** The engine's 25 seconds are one deadline for the whole review. `describe`
may use up to 5 of them and the bridge call gets the rest; the bridge is always passed `--timeout 20` and the engine's
time limit on the call is the deadline's remainder, so the two add to no more than 25. A `describe` that is not done in
5 seconds is a refusal (exit 1, as for any failed `describe` run in the plan). The 5 seconds are a guess and are
revisited with the other figures once the shadow period has logged the engine's own durations.

**A fact that is absent or of the wrong type.** A check reads only the facts named in its row. If an `ok: true` object
lacks one of them, or it has the wrong type, that check fails (it never passes by default), and `facts_complete` fails
with it. An `ok: false` object keeps the names the module always gives it (`safe-git.md`), so the same rule applies.

**Where `describe` runs.** The engine runs `describe` from the working directory it was started in, and the hook
starts `review` in the directory where the harness will run the command. The spec does not make the engine check this;
a hook that starts it elsewhere gets facts about another repository. That is a requirement on the owner's hook.

**A rules directory that cannot be read, or is too large.** If `rules/` cannot be read, has more than 64 files or
holds more than 262,144 bytes, no rule is trusted to match: every review is refused (exit 1) with that reason. Within
the limits, a single bad file refuses only its own key, as above.

**A code-check decline has no bridge.** The log row's `bridge`, `model` and `effort` are null when the bridge was not
called.

**What the loader does not check.** For a spelling that does not begin `wb run`, nothing ties `spelling` to `module`;
that rests on the owner's review of the shipped rule data and on the module's `describe` contract. A later push rule
is the intended case (`["git"]`).

### The reviewed command is the command that runs (default)

A review is useless if it examines something other than what executes. The engine takes the prompted command as the
raw text the harness is about to run, and as one canonical form from the hook to `describe`:

- **Accepted grammar (a restricted subset, so that every shell reads it alike).** The text is a sequence of words
  separated by exactly one space each, with no leading or trailing space. A word is either a bare word made only of
  `A-Z a-z 0-9 . _ / : = @ % + , -` (not beginning with `-` unless it is a flag the rule declares), or a single-quoted
  string: `'`, any characters except `'` and newline, `'`. Nothing else is accepted: no double quote, backslash,
  `$`, backtick, `*`, `?`, `[`, `~`, `{`, `#`, `;`, `&`, `|`, `<`, `>`, `(`, `)`, newline or tab outside a
  single-quoted string, and no environment prefix. Inside single quotes every character is literal in POSIX shells
  and in zsh, so the word means the same to all of them. A command that does not fit is unreviewable and approves
  nothing; the owner then sees the normal prompt. A commit message that needs a single quote is written without one
  or in a body file the helper takes, which the plan of `describe` may add.
- **The corpus is a test of a stated grammar.** The grammar above is exact, so the equivalence test is a property
  test over generated command text and not a sample: every accepted text parses to the same argument list in the
  engine and in `sh` and `zsh`, and every other text is refused.
- **One parse.** The rule's declared flags parse the arguments once. The result is an argument list, never a shell
  string, and `describe` receives that list through the launcher, with the fixed verb `describe`, so the facts are of
  the arguments the real command will receive.
- **Unknown means unreviewed.** A flag the rule does not declare, a repeated single-valued flag and a missing
  required flag refuse the review.
- **Tested.** A corpus of quoting, spacing, wrapper and shell-metacharacter forms shows that the argument list the
  engine reviews equals the argument list the real command parses from the same text, or that the review is refused.

### The verdict, the output and the log (default)

These are the author's proposals, settled by plan `2026-10-25-describe-interface-documented` for the plan that
builds the engine. The rule schema is not here: it is that plan's first deliverable.

**The verdict object.** `wb run action-review review` prints exactly these fields and no other:

- `verdict`: the string `approve` or `decline`.
- `failed_checks`: an array of distinct strings, each a check name (`^[a-z][a-z0-9_]*$`, at most 64 characters) from the
  rule's checks, whether code checks or rubric questions. It is empty when the verdict is `approve` and not empty when
  it is `decline`; any other combination is malformed. At most 32 entries.
- `reason`: a string of at most 300 characters, display-cleaned (no control character, ASCII only). The bound is the
  length the approver already logs (`LOGGED_REASON`, read 2026-10-25).

A response from the bridge that does not fit this, once the engine has applied it, is not passed on: the engine's own
verdict is a decline or a failure, never a malformed object.

**Output and exit status.** One JSON object and a final newline on standard output, or nothing on standard output.

| Outcome | Standard output | Exit |
|---|---|---|
| a verdict, approve or decline | the verdict object | 0 |
| a refusal: a rule that does not load or is ambiguous, an unpinned or undeclared module or bridge, an unreviewable command, a `describe` object that is malformed (a `truncated: true` object is well formed and is a decline, not a refusal) | nothing; `refused: <reason>` on standard error | 1 |
| an engine failure: the bridge fails, times out or returns something unusable; an internal error | nothing; `failed: <reason>` on standard error | 2 |

The reason is at most 500 characters and is display-cleaned, for the hook to show. A decline caused by `truncated:
true` or by `ok: false` is a verdict (exit 0, `decline`), because the review ran and the checks said no. Only an
object on standard output, with exit 0 and `verdict` equal to `approve`, can lead the hook to allow anything; every
other outcome leaves the owner at the normal prompt. The hook reads the object, never the exit status alone, and
applies the same field rules to it (an approve with a non-empty `failed_checks`, an extra field or a wrong type allows
nothing). A decline also exits 0, so a hook that tested the status alone would read a decline as an approval; the
spec rules that out and the hook's tests show it. This contract differs from the bridge's (`model-bridge.md`), where
exit 1 with a valid object is a failure; the engine's exit 1 and 2 print no object.

**The log.** One JSON line per review, append-only, with these fields and no others: `ts`; `rule` (the rule's key);
`verdict`; `failed_checks`; `reason` (as above); `command_sha256` (of the canonical argument list the engine built,
not of the raw text); `facts_sha256` (of the canonical serialization of the `describe` object as received);
`rubric_sha256` (of the rubric text sent); `bridge`, `model` and `effort` (as used); and `format` (the engine's log
format number). It holds no command text, no fact and no diff, with two residual exposures: `reason` is bounded,
display-cleaned model output that could quote a path or a line it was shown, and a hash of a short argument list can be
guessed by dictionary, so "hashes, never text" is not secrecy. It lives outside every project, in the owner's own data
directory beside the approver's verdict log, so a vendor program that opens files in the project cannot find it. The owner
decided on 2026-10-25 that the owner's thin hook writes it, from the row the engine hands back, and that a failed write
never withholds an approve (below, "Decided by the owner"). The engine writes nothing outside the project; the row
reaches the hook through the `--log-row` flag, which prints it as one `log-row:` line on standard error, without
adding a field to the verdict object (see "The rule schema, the module and the checks").

**How the engine learns that a command is pinned and declared.** Only part of this is settled today:

- *Pinned: settled.* The engine does not look pins up. It starts the command with `wb run`, and the launcher refuses a
  command that no installed module declares, whose pin is absent or names another helper, or whose helper changed since the owner pinned it, and, for a pin the installer made, whose declaration changed
  (`module-boundary.md`, "A helper that runs another module's command"; a hand pin records no declaration hash). The
  engine treats any refusal as a refusal of its own (exit 1) and approves nothing. `wb run` takes a command name, not
  a module name, so a rule's module and action must map to a command name; the engine's plan fixes that mapping.
- *Declared: built.* The engine reading `module.json` itself would be a second check of a declaration the launcher
  already hash-checks, with a different trust. The owner decided on 2026-10-25 that the launcher enforces it: when a
  command's first argument is `describe`, `wb run` refuses unless the second argument is in the command's `describes`
  (`module-boundary.md`, "Declaration schema"). The rule is generic and names no module or action. The engine then
  needs no knowledge of declarations, and a refusal is a refusal of the engine (exit 1). Plan
  `2026-10-25-safe-git-describe` built the rule and `safe-git` declares it.

**The timeout.** Decided by the owner on 2026-10-25, as provisional figures: the bridge's `--timeout` is 20 seconds,
the engine's own limit is 25 seconds, and the hook's limit is 30 seconds, so each layer reports before the one outside
it ends it (`model-bridge.md` requires the engine's limit to exceed the bridge's). The source is the approver's log,
read on 2026-10-25: 876 reviews, the median model call 7.5 seconds, the 95th percentile 13.4 seconds, and 20 reviews
(about 2%) ended at the approver's 15-second limit with no verdict; the approver's hook limit is 25 seconds. The engine
adds the launcher, `describe` and a larger fact set, so the margin is wider. The figures are revisited when the shadow
period has logged about 30 of the engine's own reviews. A review that times out leaves the owner at the normal prompt.

### Settings and the bridge

Decision 5 of `2026-10-22-model-calls-go-through-vendor-bridges` applies except for the file name. **This departs from
decision 5.** The decision says each engine reads "a file named for the engine, `.workbench/<engine module>.json`";
the owner chose on 2026-10-26, as the plan `2026-10-26-action-review-engine` records, that this engine reads the
project file `.workbench/review.json`, the file the review engine already reads, and not `.workbench/action-review.json`.
A decision outranks a spec and an accepted decision is superseded, never edited, so **a record that narrows or
supersedes decision 5 for this file name is owed**; it is the owner's to accept, and until it is accepted this section
contradicts the decision on that one point. The file holds a format number and the bridge, the model and the effort the
project would like. It is a request and never an authorization.

- **The reader is that of `review-engine`.** The file is at most 4,096 bytes, strict JSON, an object with `format` equal
  to 1, `bridge` (a command name, required), and optionally `model` (letters, digits and `._:-`, at most 64 characters,
  starting with a letter or digit) and `effort` (`low`, `medium` or `high`). An unknown field, a wrong type, a
  duplicate key or a missing file is a refusal (exit 1); there is no default bridge, and the engine never guesses a
  vendor to send content to. The engine passes `--model` and `--effort` to the bridge only when the file has them.
- The bridge must be an installed, pinned module that provides `model-bridge`; the engine starts it through the kit's
  `run_command` with `--provides model-bridge`, and the launcher refuses one that is not. A name that is refused ends
  the review (exit 1) and no other vendor is tried.
- **Recorded limit: the personal setting is not built.** The owner's personal setting would be authoritative over the
  project's request. No helper can read the guarded store, as for the review engine, so the engine reads the project file
  only; a project file is not the owner's personal setting, and a project could name another installed bridge. Only an
  installed, pinned bridge that provides `model-bridge` can run. The precedence rule of the earlier text is deferred
  with the personal setting.
- **Recorded limit: one file for two engines.** Both engines refuse an unknown field, so a field added for one is
  refused by the other until both readers change together.
- A pulled change to the file is a difference `wb acknowledge` lists, and at run time the file is accepted only if it
  names a bridge the owner already approved by installing it.
- The timeout the engine passes to the bridge (20 seconds) is shorter than its own limit (25), as `model-bridge.md`
  requires.
- A missing or unreadable setting, or a bridge failure of any class, yields no approval.

### The enforcement point (default)

The owner's hook becomes a thin program: match the prompted command to a spelling, run `wb run action-review
review`, and turn the verdict into the hook's answer. What the hook allows without the owner (`DELEGABLE`, the
mode setting) stays a code constant there. The hook is the owner's to write and install; the agent prepares and
tests it on a scratch copy, as it did for the patch of option 1a.

### Accuracy and cutover (default)

The approver is not the standard, because the owner finds it wrongly declines. So the engine is judged against a
labelled set, not against the approver.

1. **Find where the approver goes wrong.** Its verdict log holds the rule, the verdict, the failed checks and a
   command hash, never command text. Counting declines by failed check shows which checks cause them. This needs
   no new data and is read-only. Plan 1 does it first, so that the engine is not built to repeat those checks. The
   count is in the Evidence section ("The approver's declines by failed check").
2. **Build a labelled set.** A collector records, for each prompted command from now on, the `describe` output (the
   command text, the facts, the engine's verdict) in a local, untracked file, and the owner marks each one right
   or wrong. A new file is needed because the old log has no text to label. The facts can contain diffs, and a
   vendor program can open any file inside the project, so the file lives outside every project, in the owner's
   own data directory beside the verdict log, and is never tracked. The owner-side collector writes it; the agent
   does not. A project path for it would be readable by the vendor and is not allowed.
3. **Shadow.** The thin hook runs the engine beside the approver. The approver's answer still decides; the
   engine's is logged. Nothing the engine says takes effect.
4. **Measure.** The report gives false declines and false approves of both programs against the owner's labels. A
   disagreement is settled by the owner's label, not by assuming either is right.
5. **Cut over only when the owner says.** The engine replaces the approver when its false-approve count on the
   test set and the labelled set is zero and its false declines are below a bound the owner sets. The old program and `claude-workflow` stay
   installed until then (rule 6 of `global-config-inventory.md`).

The cost is the owner's time to label, and two model calls per prompted command during the shadow.

**Decided by the owner (2026-10-25):** both. The owner labels real commands, and the author also writes a small test
set of dangerous cases, which the owner reviews and corrects. The two answer different questions. Real commands
seldom include an unsafe one, so a count of zero false approves on them is weak evidence that the engine stops
unsafe actions. The test set covers the stops: a secret in a diff, a HEAD that does not match, a repository that
selects a program, a message addressed to the reviewer, a removal of Git metadata. The labels measure the
everyday false-decline rate. The cutover bound applies to both: no false approve on the test set or the labels,
and false declines on the labels under the owner's bound.

**The bound (the owner chose the author's recommendation, 2026-10-25).** At most 10% of the labelled real commands
are false declines, on at least 30 labelled commands, and strictly below the approver's rate on the same commands.
The 10% is provisional and the owner may tighten it once plan 1 has counted the approver's declines by failed check.
A false decline costs the owner a prompt (under `delegate` a decline falls back to the normal prompt); a false
approve is the harm, so it has no bound: any false approve on either set blocks cutover. The report groups false
declines by check, so a few fixable checks are not hidden in a count. The 10% and the 30 are the author's judgment,
not measured.

### What moves, and what does not

| today | after |
|---|---|
| collectors for commit and remove, via the global program | `safe-git describe commit`, `safe-git describe remove` |
| collector for a remote job | `remote-runner describe submit`, `describe fetch` of the module, which wraps the owner's global program (M16 and F-C6 apply) |
| collector for a push | `safe-git describe push` (built by plan `2026-10-26-safe-git-describe-push`; see `safe-git.md`); `push-check` stays for the `push-changes` skill |
| the rubric, schema and rule files | ported into the engine as data, section by section |
| `ask-codex-archive` rule | none: the module's `archive` is owner-run and denied (M15) |
| `safe-committer` agent and the guard's `committer` mode | go with the program (decided by the owner, 2026-10-25): the agent and the mode are removed in the owner's step that removes `claude-workflow`; the guard program stays for its other modes. No module counterpart. |
| `claude-workflow amend-message` | lost with the program (the owner's decision is recorded under "Decisions on the two leftovers") |

## Proposed split into plans (default)

Each is a plan of its own, in this order. Plans 3 to 5 do not exist yet, and the owner approves each.

1. **The interface, documented. Done by plan `2026-10-25-describe-interface-documented`.** The `describe` decision
   is accepted. The plan settled what it left open: the form of a module's declaration in `module-contract.md` and
   `module-boundary.md`, the numeric caps and the fact names for `commit` and `remove` in `safe-git.md`, and the
   engine's contract in this spec, and the owner's three decisions on 2026-10-25 (the launcher rule for a declared action, who writes the log, the timeout; see "Decided by the owner"). It also holds the
   read-only count of the approver's declines by failed check, so the rubric is written knowing where the approver
   goes wrong.
2. **`safe-git describe`. Done by plan `2026-10-25-safe-git-describe`** (see `safe-git.md`, "As built, and its limits",
   for what differs from the draft). It is for `commit` and `remove`, with tests that the facts equal what the real command acts on and
   that the call changes nothing. Its first increment is the verifier support for the `describes` field; the launcher rule that refuses
   `describe <action>` for an action not in `describes` follows it; its security pass covers the new git shapes and
   that rule.
   Between 2 and 3, or alongside 3: **the push gap**, closed by adding `safe-git describe push` (the owner chose this over
   extending `push-check` on 2026-10-26; plan `2026-10-26-safe-git-describe-push`; the design is in `safe-git.md`,
   "`describe push`", and the narrowing of the accepted `describe` decision is the accepted record
   `2026-10-26-describe-push-takes-the-push-arguments`). Built, so the engine's rule for a push has its facts; until that
   rule exists a push stays with the approver.
3. **The engine** with its checks, rules, rubric, log and bridge call, tested with a fake bridge. No hook.
4. **The shadow hook, the labelled set, the test set and the report**, prepared on a scratch copy; the owner installs
   the hook, labels the commands and reviews the test set. The test set is written in plan 3 with the checks.
5. **Cutover and M14**: the thin hook replaces the approver, the global `claude-workflow` program goes, and the
   paragraphs OP5 and OP7 are repointed. Facts for remote jobs follow M16.

## Decisions on the two leftovers

- **`safe-committer` and the guard's `committer` mode (F-A7): the owner chose the author's recommendation on
  2026-10-25.** They go with `claude-workflow`. The workbench's `commit-changes` skill has the main agent run
  `wb run safe-git commit` directly, and the helper enforces the limits. A confined commit agent for the module would
  need the agent gate's grammar extended, for a convenience. If the owner turns out to use the agent, a module
  version is planned later.
- **`claude-workflow amend-message`: lost with the program. The owner accepted the author's recommendation on
  2026-10-25 and said it can be added later if it is needed.** Read on 2026-10-25 (the
  installed program, read, not run): it rewrites the message of the HEAD commit only. It refuses when HEAD is not the
  expected hash, when anything is staged, and when HEAD is on a known remote branch unless `--allow-pushed` is
  passed. Evidence for losing it: (1) the plan `2026-10-22-code-work-commit` left it out on purpose ("the owner amends
  with git by hand"); (2) the module's `commit-changes` skill already says never to amend; (3) the approver has no
  rule for it (F-B4), so it has never been reviewed and no review is lost; (4) this repository's reflog holds no amend
  operation; (5) a new `describe` command, rule, checks and test cases would be built for a history-rewriting command
  that is otherwise refused by policy. Limits of that evidence: the reflog covers this repository only, and the
  owner's other repositories were not examined. A bad message is fixed by a new commit or by the owner's own `git
  commit --amend` in a terminal. When the program goes, its `ask` and `allow` entries for `amend-message` are dead and
  the owner removes them (rule 6 of `global-config-inventory.md`).

## Constraints and assumptions

- Standard library only, a helper per command, pinned by the installer (`module-boundary.md`).
- The engine runs a `describe` command and a bridge only through `wb run`, as decision 4 requires. A security review is
  owed because a helper starts another module's pinned command (decision 4, consequences).
- Assumes a hook can run `wb run` in good time. The provisional limits are under "The verdict, the output and the log".
- The approver's rubric text is read and ported by the plan that builds the engine; this spec does not restate it.

## Decided by the owner (2026-10-25)

The owner took the author's recommendation on each of three questions the plan `2026-10-25-describe-interface-documented`
left open.

- **How the engine knows a command is declared for an action: the launcher enforces it (option (a)).** `wb run` refuses
  `describe <action>` unless the action is in the command's `describes`. Rejected: (b), a read-only `wb` command that
  lists declared (module, command, action) triples for the engine to check first, because it leaves two places to
  enforce. The cost accepted: the launcher knows one verb and one argument position, although `module-boundary.md` says
  the installer knows no command by name and the decision rejected a launcher `describe` as module content. The rule is
  generic and names no module. `module-boundary.md` is updated when the rule is built.
- **Who writes the engine's log: the owner's thin hook, and a failed write never withholds an approve.** The engine runs
  as an agent-reachable pinned command and the floor decision (`2026-10-24-project-guarantees-a-floor`) says the agent
  writes nothing at the user level, so the engine writes nothing outside the project. The hook notes a failed write and
  goes on. The cost accepted: a review can be approved with no log row, so the log is a record and not a gate.
- **The timeout: 20 seconds for the bridge, 25 for the engine, 30 for the hook, provisional.** The source and the
  reason for the order are under "The verdict, the output and the log". They are revisited with the shadow period's
  own durations.

## Open questions for the owner

- Is a separate `describe` subcommand the right shape, or should the interface be something else?
- Decided: you label real commands and review a test set, with the bound above. Open: whether 10% stays after
  plan 1's count.
- `safe-committer` (F-A7) and `amend-message`: decided, see "Decisions on the two leftovers".
- The capability name `action-review` is a proposal.

## Acceptance criteria

- For each action that stays a reviewable module action (commit, remove, a push through `describe push`, and later the
  remote actions), a module `describe` command prints an object that obeys the rules above, runs the real command's
  validation, and changes nothing (a test compares the repository before and after).
- The retired actions have no `describe` provider and no rule: `ask-codex archive`, `safe-committer` and
  `amend-message`. A test shows the engine refuses a command line that names one.
- A rule that carries command text, an extra verb or a path does not load, and the engine builds only `wb run <module>
  describe <action> ...`.
- A synthetic action with a fake module and a fake bridge gets a verdict only through `wb run`; a `describe` command or a
  bridge that is not installed, pinned and declared is refused and nothing runs.
- A missing, malformed, oversize or unavailable bridge reply, facts object or rule file yields no approval.
- Over generated command text, every text the stated grammar accepts parses to the same argument list in the engine
  and in `sh` and `zsh`, and every other text is refused.
- Two rules with one key, a malformed rule and a rule with an unknown field each refuse only their own key; other
  commands are still reviewed.
- Bridge selection: an absent setting, an invalid one, a bridge that is not installed and one that is not pinned each
  behave as the settings section says, and no other vendor is tried. (A project request that the owner's personal
  setting overrides is not testable until that setting is built.)
- No file holding labelled data or command text lies inside a project tree.
- A corrupt rule file does not stop the review of any other command.
- Every check of today's approver for commit, remove and push has a named counterpart or a recorded reason it does
  not (the plan of the engine lists them).
- On the test set of dangerous cases (reviewed by the owner) and on the labelled set of the owner's real commands,
  the engine has no false approve; on the labelled set its false-decline count is below the owner's bound; and the
  report shows the approver's counts on the same sets for comparison.
- The count of the approver's declines by failed check exists before the engine's rubric is written.
- `review` prints only the verdict object described above and exits 0, 1 or 2 as the table says; an approve with a
  non-empty `failed_checks`, a decline with an empty one, an extra field or a `reason` over 300 characters is never
  printed; and a test shows that every refusal and failure prints nothing on standard output.
- The log line holds exactly the fields listed, and a test shows that no command text, fact or diff reaches any field
  other than the bounded `reason`; the residual exposure of `reason` is recorded above.

## Evidence

- The approver's collectors were read on 2026-10-25 in the program the inventory records (baseline SHA-256
  `94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b`, then patched to
  `d8b3facdee46432d27547a07865abf024741929ae2d9191e1015ee8280bcd613`); `load_helper`, `collect_commit` and
  `collect_remove` call the global `claude-workflow` program as a library. Read, not run.
- The module sides were read in `safe-git.md` (`commit`, `remove`, `push-check`) and `model-bridge.md`.
- Not run when this spec was written (2026-10-25): any `describe` command, any engine, any hook. The proposals are the author's.

### The approver's declines by failed check

Provenance: role USER, item the approver's verdict log (`verdicts.jsonl`), retrieved 2026-10-25, 668,545 bytes, SHA-256
`2a8e8ce7988de449be738a46b876436f8b9343955f953574364cd4a67dd3e095`, recomputed after the read and equal. A scratch
script ran with Python 3.15.0 (`-I -B`), read the file in binary mode and printed counts only; no command digest and no
free text was printed or copied. Plan `2026-10-25-describe-interface-documented`, Increment A.

The log has 1,019 rows (none unparsed), first dated 2026-10-16 and last 2026-10-26 (timestamps as logged; their timezone was not checked). By verdict:
662 approve, 336 decline, 21 no verdict (20 Codex timeouts, 1 collector error). Every decline carries a non-empty list
of failed checks. A decline has one of two reasons: 146 failed a deterministic check before Codex was asked, and 190
were Codex declines.

| Rule | Approve | Decline | No verdict |
|---|---|---|---|
| `claude-workflow-commit` | 420 | 194 | 12 |
| `git-push` | 107 | 58 | 6 |
| `claude-workflow-remove` | 27 | 49 | 1 |
| `ask-codex-archive` (retired) | 72 | 10 | 2 |
| `remote-runner-submit` | 24 | 8 | 0 |
| `safe-git-commit` | 7 | 9 | 0 |
| `remote-runner-fetch` | 3 | 8 | 0 |
| `remote-runner-cancel` | 2 | 0 | 0 |

Failed checks over all declines (a decline can fail several, so the counts add up to more than 336):
`no_secret_lines` 102, `no_reviewer_directed_text` 102, `targets_look_disposable` 48, `change_is_safe_in_itself` 44,
`facts_complete` 26, `message_matches_change` 10, `status_ok` 9, `paths_valid` 9, `fetch_targets_safe` 8,
`head_matches` 7, `profile_command_is_expected` 5, and 11 more checks with 3 or fewer each.

By the actions this design keeps:

- Commit (`claude-workflow-commit` and `safe-git-commit`): `no_reviewer_directed_text` 99, `no_secret_lines` 52,
  `change_is_safe_in_itself` 42, `facts_complete` 11, `message_matches_change` 10, `paths_valid` 9, `head_matches` 7,
  `scope_is_coherent` 3, `staging_state_ok` 2.
- Remove (`claude-workflow-remove`): `targets_look_disposable` 48, `scope_is_narrow` 3,
  `preview_matches_arguments` 1.
- Push (`git-push`): `no_secret_lines` 47, `facts_complete` 15, `no_reviewer_directed_text` 3, `outgoing_trusted` 3,
  `change_is_safe_in_itself` 2, and `outgoing_known`, `push_target_known`, `remote_is_configured`,
  `remote_transport_safe` 2 each, `destination_is_appropriate` 1.

Limits. A decline in the log is not a false decline: no label exists, so the count says which checks cause declines
and not which were wrong. The log grows, so these figures hold as of the retrieval date. The `ask-codex-archive` rows
belong to an action this design retires. A command whose rule does not load is not reviewed at all, so the log cannot
show it (see "Non-goals and anti-goals"). The `reason_text` field was not read.

Durations for the timeout decision: a second read of the same log (role USER, `verdicts.jsonl`), later on 2026-10-25,
by a scratch script (`python3 -I -B`, binary read, counts only) over the `codex_seconds` field. Measured immediately
afterwards, the log was 672,275 bytes with SHA-256 `796046453f59e0ffb09ce28401b133e6c6c0443c8de43d13d832c9a8c3fc7f48`
(it had grown since the first read, so the two sets of counts differ by the rows added). Result: 876 rows with a
duration, median 7.5 s, 90th percentile 11.7 s, 95th 13.4 s, 168 over 10 s, 20 at the 15 s limit.

What it shows: `no_reviewer_directed_text` (99) and `no_secret_lines` (52) lead the commit declines;
`no_secret_lines` (47) leads the push declines, with `facts_complete` (15) second; and `targets_look_disposable` (48)
is nearly all of the removal declines. They are the first to label in the shadow period. It does not bear on the provisional 10% bound, because the bound concerns false declines, which only the
owner's labels measure; the bound is unchanged and remains the owner's to tighten.
