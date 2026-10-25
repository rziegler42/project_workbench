# model-bridge

Status: Current. Contract version 1. Written by plan `2026-10-22-ask-codex-bridge` (increment A), before any
bridge or engine existed, so that both are built against this text; the first bridge, `ask-codex`, was built and
reviewed by the same plan, and "As built, and its limits" lists what exists. The capability name `model-bridge`
is still a proposal (see "Open questions").

Terms are defined in `terms.md`. The declaration it satisfies is defined in `module-contract.md`; the launcher,
the kit, the pin and the rule for a helper that runs another module's command are in `module-boundary.md`; the
authority rules are in `trust-and-approval.md`. The decision behind it is
`2026-10-22-model-calls-go-through-vendor-bridges`.

## Purpose and scope

A **model bridge** is a thin module for one vendor. It lets a workbench engine ask that vendor's model one
question, read-only, and get back one JSON object. It translates between the workbench's contract and the
vendor's command line program and does nothing else.

Non-goals:

- Review, rounds, findings, verdicts, rubrics or any policy. Those belong to the engines above the bridge.
- State. A bridge keeps no record of a call, no counter and no cache, and writes nothing in the project.
- Choosing a bridge, a model or an effort. The engines' settings choose (decision 5 of the accepted record).
- Signing in. The bridge reports that the vendor program is not signed in and never handles credentials.
- Retrying, falling back to another model or another vendor, or splitting a prompt.

## Declaration

| field | value |
|---|---|
| type | `module` |
| provides | `model-bridge` |
| requires, fills, writes | nothing |
| ships | one helper, `helper/ask-<vendor>` |
| commands | `ask-<vendor>`, with `helper` `helper/ask-<vendor>`, `runtime` `python`, `kit` 1 and `arguments` `["ask"]` |

`<vendor>` is a lowercase name of the vendor's program or family (`codex`, `claude`, `gemini`). The capability
has no prefix, so only the first-party package may provide it (`module-contract.md`). A bridge is run as
`wb run ask-<vendor> ask [options]`. The installer pins the helper when the owner confirms the install, so
installing a bridge is the owner's consent to send content to that vendor. The command and the helper share
one name, which is fine because pins are keyed by command. The prompt reaches the helper on standard input
because the launcher passes the caller's standard input through to the helper it runs (`module-boundary.md`,
"A helper that runs another module's command").

## Input

- **Standard input** is the prompt: UTF-8 text of at most 262,144 bytes. Empty, blank (only whitespace), not UTF-8
  or larger is refused (exit 1, `refused:` line, nothing run).
- **Options**, each at most once, a value as the next argument, and nothing else accepted:

| option | meaning | default |
|---|---|---|
| `--model <name>` | the vendor's model name, at most 64 characters of `A-Za-z0-9._:-`, starting with a letter or digit (so it can never read as an option) | the vendor's default |
| `--effort <level>` | one of `low`, `medium`, `high` | the vendor's default |
| `--timeout <seconds>` | a whole number from 1 to 3600 for the whole call (the range and default are this spec's choice) | 600 |
| `--root <path>` | the directory the vendor program works in | the project root |
| `--schema <path>` | a file holding a JSON Schema for the reply (below) | none |

A name, a level or a number outside these ranges is refused before anything runs. The bridge does not interpret
the prompt.

**Paths.** `--root` and `--schema` are resolved against the project root found as `wb run` finds it, and a
relative path is read that way, not against the caller's directory. Every component of the path must be inside
the project and none may be a link. `--root` must exist, be a directory the program can enter, and not lie inside
`.git` or `.workbench`; `--schema` must be a regular file. A path that breaks any rule is refused before anything
runs.

## What the vendor program can read

The vendor program runs read-only, but read-only is not blind. It reads files itself, starting in `--root`, and
the bridge does not restrict that beyond what the vendor's own read-only mode does. So:

- Anything in the project the vendor program can open can leave the machine, including untracked scratch, a file
  the prompt never named and a secret someone left in the tree. The prompt names the file that matters; it does
  not bound what is read.
- An engine must keep secrets out of what it points a vendor at, and an owner who installs a bridge accepts
  that.
- The bridge itself reads only its prompt, its options, the `--schema` file and the vendor program's output.

## Output

On standard output, one JSON object and a final newline, at most 2,000,000 bytes (enough for a maximal reply
after JSON escaping). All fields are plain JSON values. Every string is display-cleaned: control characters are
removed, except that `reply` keeps newline and tab.

Success, exit 0:

```json
{"contract": 1, "ok": true, "vendor": "codex", "model": "<name reported or requested, or null>",
 "reply": "<text>", "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
```

- `reply` is a string of at most 262,144 bytes, measured as UTF-8 before JSON escaping. A longer reply is an
  error (`vendor_error`, `reply_too_large`), not a cut.
- `usage` has those three fields, each a non-negative whole number of at most 10^12, or `null` when the vendor
  did not report it or reported anything else. The bridge does not derive one from the others.

Failure, exit 1 (the object is still printed):

```json
{"contract": 1, "ok": false, "vendor": "codex", "error": "<class>", "detail": "<code or null>",
 "retryable": false, "message": "<short text>"}
```

- `error` is one of exactly six classes: `not_signed_in`, `model_unavailable`, `effort_unsupported`,
  `program_not_found`, `timeout`, `vendor_error`.
- `detail` is a code of at most 64 characters of `a-z0-9_`, and is never `null` for `vendor_error`. It is `null`
  for the other five classes. Anything the six classes do not name is `vendor_error` with a `detail`. The codes
  defined now: `usage_limit` (the vendor refused for quota), `unusable_reply` (no reply, or not one JSON object
  when a schema was given), `reply_too_large`, `bad_schema` (the vendor program rejected the schema) and
  `bad_exit` (it exited non-zero and its text matches no other class). A bridge may add others; an engine treats
  an unknown code as `vendor_error`.
- `retryable` is a boolean: whether the same call might succeed later. It is `true` for `timeout` and
  `usage_limit` and `false` for the other classes and codes defined here. The bridge reports it and never
  retries.
- `message` is at most 500 characters and holds no more of the vendor's output than is needed to say what
  happened. It is for the owner to read, not for an engine to parse.

A refusal of the options, the paths or the prompt, and a refusal by the launcher, print a `refused:` line to
standard error, nothing to standard output, and exit 1. So exit 1 with a valid object is a failure of the call,
and exit 1 with no object is a refusal. An engine treats a missing, malformed or oversize object, an unknown `contract`, and
any exit code other than 0 with `ok: true`, as a failure with no reply.

## The result shape

An engine may ask for a reply of a given shape. It writes a JSON Schema in a file inside the project and passes
`--schema <path>`. The bridge reads the file without following a link, at most 65,536 bytes, checks that it is a
JSON object (otherwise it refuses, with no vendor program started), and gives it to the vendor program in the
way that program supports. Then:

- With `--schema`, the reply must be one JSON object; the bridge checks that it parses and is an object, and
  otherwise reports `vendor_error` with `unusable_reply`. It does not validate the object against the schema: it
  is a thin translation and holds no validator.
- A vendor program that rejects or cannot take the schema is reported as `vendor_error` with `bad_schema`.
- The reply stays a string in `reply`; it is the engine that parses it.
- The engine validates the reply again, whatever the bridge or the vendor did. Both are untrusted.

## Guarantees

1. **Read-only.** The vendor program is started in its read-only mode, with a fresh session that is not kept,
   and told to ignore the user's own configuration file. That is all "no user configuration" means: the
   program's sign-in state under `HOME` is still used, because the bridge handles no credentials and passes no
   token.
2. **A scrubbed environment.** The vendor program gets exactly these variables of the caller, when set: `HOME`,
   `XDG_CONFIG_HOME`, `USER`, `LOGNAME`, `LANG`, `TZ`, `TERM`, `TMPDIR` and any `LC_*`; and a `PATH` of the
   trusted entries. The bridge adds no other variable. No `GIT_*` variable, token, `LD_*` or `DYLD_*` variable
   and no variable that selects a program or a configuration file is passed.
3. **The program is found outside the repository.** `PATH` is searched only in entries that are absolute, are existing directories and are
   outside the outermost repository that holds the project (the outermost ancestor with a `.git` entry, or the
   project root when there is none); a relative entry, an empty entry or an entry inside that repository is
   skipped, however a link or a letter case spells it; the found file is an executable regular file or a link to
   one that does not resolve into it. If none is found the error is `program_not_found`.
4. **Nothing written in the project.** The vendor program's output goes to a private temporary directory outside
   the project, which the bridge removes. The bridge creates, changes and deletes no file in the project.
5. **Bounded.** The prompt, the schema, the reply and the object are limited as above. The bridge reads the
   vendor program's output file and its standard output and error each to at most 1,048,576 bytes; a program
   that writes more is stopped and reported as `vendor_error` with `reply_too_large`.
6. **A timeout ends the whole call.** At the timeout the vendor program and its children are killed as a
   process group and the error is `timeout`.
7. **No network of its own, no log.** The bridge opens no connection and writes the prompt and the reply to no
   file and no log. Its only file is the vendor program's output file in the private temporary directory.
8. **Output is data.** What the vendor returns is never run, never used as a path or a command, and never
   believed. The bridge only classifies it and copies the reply.

## Conformance checklist

A bridge conforms when a test against a fake vendor program, which records its arguments, environment and
standard input, shows each item. No item needs a real vendor, a sign-in or a network.

1. The declaration is as above: type `module`, provides only `model-bridge`, one helper, command `ask-<vendor>`
   with `runtime` `python`, `kit` 1 and `arguments` `["ask"]`, and no `requires`, `writes` or `fills`.
2. A missing, empty, non-UTF-8 or oversize prompt is refused and nothing runs.
3. An unknown option, a repeated option, a missing value, a `--model` outside its charset or length, an
   `--effort` outside the three levels, and a `--timeout` out of range are each refused and nothing runs.
4. The vendor program is started with the read-only flags, a fresh unsaved session and no user configuration,
   and the fake records exactly that argument list.
5. The environment the fake receives is the allow list and the trusted `PATH` only; a caller's `GIT_*` variable,
   token and `LD_*`/`DYLD_*` variable are absent.
6. A program of the right name inside the project, on a relative entry or on an empty entry is never run; with
   none outside the project the error is `program_not_found`.
7. `--root` or `--schema` that is outside the project, has a link in any component, does not exist, or is the
   wrong kind, is refused and nothing runs; a relative path is read against the project root; the fake starts
   in the root given.
8. A success prints the object above, with `usage` fields `null` where the fake reported none.
9. Each of the six classes is produced from a sample of the vendor's own error text (the samples and their
   mapping are the bridge's own test), with `retryable` as the contract sets it and `detail` `null` outside
   `vendor_error`.
10. A usage limit, an unusable reply, a rejected schema and an unclassified non-zero exit are `vendor_error`
    with `usage_limit`, `unusable_reply`, `bad_schema` and `bad_exit`, and a non-null `detail`.
11. A fake that never exits ends at the timeout with `timeout`, and its children are gone.
12. A fake that writes more than a bound (a reply over 262,144 bytes, or output over 1,048,576) is stopped and
    reported as `reply_too_large`; a maximal reply of characters that escape to six bytes still fits the object
    bound.
13. With `--schema`, a reply that is not one JSON object is `unusable_reply`; without it, any text is accepted.
    The schema file given to the fake is the file read.
14. A reply made of instructions, control characters or markup is returned only as a string in `reply`, cleaned
    (newline and tab kept), and nothing in it changes what the bridge does.
15. The project tree is byte for byte the same before and after every call above, nothing is written outside
    the private temporary directory, and that directory is gone.
16. The output of every case above is exactly one object that obeys the field rules with nothing else on
    standard output, or, for a refusal, a `refused:` line on standard error and nothing on standard output.
    Whether the bridge opens a connection is not tested against a fake; guarantee 7 is shown by reading the
    helper for any network import.

## As built, and its limits

The first bridge is `ask-codex` (`packages/workbench/ask-codex/`, plan `2026-10-22-ask-codex-bridge`). It passes
the checklist against a fake `codex` program, and a synthetic engine in its tests calls it only through
`wb run --provides model-bridge`. An independent security pass and a workflow review of the plan found no Critical
or High finding; the fixes carry regression tests and were not reviewed a second time.

The first engine to call it is the review engine (`review-engine.md`, plan `2026-10-23-review-engine`). It runs a
bridge only through `wbkit.call.run_command` with `provides` `model-bridge`, names the bridge from the project's
setting and tries no other. It was tested against this bridge and a fake vendor program, and then run once by hand
against a real Codex (2026-10-23, `codex-cli 0.163.0`; see the limits below).

How it meets the contract:

- **The command line.** `codex exec --sandbox read-only --ephemeral --ignore-user-config --ignore-rules --color
  never --json --cd <root> --output-last-message <file> [--model <name>] [--config
  model_reasoning_effort="<level>"] [--output-schema <file>] -`, with the prompt on its standard input. The
  `--ignore-rules` flag means the vendor's own rule files are not read.
- **The schema is a copy.** The vendor program is given a copy of the schema in the private temporary directory,
  not the file in the project; it holds the bytes the bridge read.
- **Paths and the temporary directory.** The temporary directory is checked before it is made: a `TMPDIR` inside
  the project is refused. `--root` inside `.git` or `.workbench` is refused (stricter than the contract), as is a
  root the program cannot enter.
- **The trusted-path boundary** is the outermost repository, in the bridge and in the kit's `wb` search alike
  (`module-boundary.md`), compared by file identity, so a project nested in another repository, a link and a
  differently spelled case do not make a `PATH` entry look outside. A home directory that is itself a repository
  would make the guarded store look untrusted; the result is a refusal.
- **Sign-in text.** The text of a failure is classified by patterns; "401" counts only beside "status", "error"
  or "code".
- **Interrupts.** On SIGTERM the bridge stops the vendor program's process group and removes the temporary
  directory.

Limits:

- **Killed from outside.** A SIGKILL of the caller's process group leaves the vendor program running, because it
  is in a session of its own. A grandchild that starts yet another session survives the bridge's group kill and
  can hold the output pipes open until the timeout. An engine's own time limit must therefore exceed the
  bridge's `--timeout`, so that the bridge can report `timeout` and clean up first.
- **Checked against a real Codex once, by hand, on 2026-10-23 (`codex-cli 0.163.0`).** `codex exec --help` lists every
  flag the bridge passes. A prompt of one word returned `ok` with the reply `pong`. An unknown `--model` gave
  `model_unavailable` (not retryable) and a `--timeout` of 2 seconds on a long request gave `timeout` (retryable). A
  review round of the review engine through this bridge, with `--output-schema`, returned a reply of the engine's
  schema that the engine accepted; the model read the document from its working directory. Not tried against a real
  Codex: `--effort`, a sign-in that is missing or expired (`not_signed_in`), `effort_unsupported`, a reply that does not
  match the schema, and a run on another version.
- **The model and the total are not reported.** With no `--model` the success object has `model` null, so a stored
  round says "model unknown", and `total_tokens` is null; the event stream of this version did not give the bridge
  either. Pass `--model` to name the model.
- **The launcher must be on `PATH`.** A caller finds `wb` only in an absolute `PATH` entry outside the project, and
  nothing adds `~/.config/project-workbench/bin` there; without it a round is refused before anything runs, and no
  round is spent.
- **A timeout is shown, not the process tree.** The hand run showed that the bridge reports `timeout`; it did not
  check that no `codex` process was left running afterwards.
- **The vendor reads the repository.** The program may also read the repository's own instruction files (an
  `AGENTS.md`, a `.codex` directory); the bridge does not stop it.
- **No depth limit across `wb run`.** Each hop is an approved, pinned command and each call has a time limit, which
  ends a loop; nothing counts the depth.
- **Linux, and a virtual-environment `sys.executable`,** were not run.
- **No live session.** The hand run above is the only run with a real vendor; no harness session has called a bridge.

## Acceptance criteria

- The spec states contract version 1 and every item above can be tested against a fake vendor program.
- A first bridge passes the checklist (`ask-codex`, plan `2026-10-22-ask-codex-bridge`, increment C).
- A synthetic engine calls a bridge only through `wb run`, accepts it only when it is an installed, pinned module
  that provides `model-bridge`, and treats its output as data.
- Nothing here depends on a file outside the repository.

## Open questions

- The capability name is a proposal.
- Whether `--effort` needs vendor-specific levels beyond `low`, `medium` and `high`.
- Whether a prompt larger than 262,144 bytes is ever wanted (an engine would pass the file name instead).
