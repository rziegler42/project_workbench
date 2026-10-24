# remote-runner

Status: Draft. Written by plan `2026-10-24-remote-runner-module` (increment A), before the module existed, so that the
module and the change to the external program were built against this text; the module is now built and the text
matches it ("As built, and its limits"). It awaits the owner's approval and reads `Current` only after it.

Terms are defined in `terms.md`. The declaration it satisfies is in `module-contract.md`; the launcher, the kit and
the pin are in `module-boundary.md`; the authority rules, the fetch channel and the floor are in
`trust-and-approval.md`; the two checkpoints it concerns, `submit-remote-job` and `fetch-remote-output`, are declared
by `code-work.md`.

## Purpose and scope

The owner runs long checks on SSH runners with a program called `remote-runner`. This module gives a project the
program's job profiles in a committed file under `.workbench/`, and gives an agent a guarded way to submit a job,
look at it and fetch its output, with the rules of the workbench applied: the checkpoints stop for the owner, the
output is untrusted data, and an overwrite of an existing or tracked file is not the agent's to make.

Non-goals:

- The program itself. It lives outside this repository (see "What the program must change").
- Host details: SSH names, workspace roots and capacity. They stay in the owner's personal `~/.claude/remotes.toml`
  (or `~/.config/remote-runner/remotes.toml`). The module never reads or writes them, and the project file never
  holds a host.
- Running a command on a runner other than through the program, and any `ssh`, `scp` or `rsync` call.
- What a profile's command does. The module checks the shape of the file, not the command.
- Pruning, cancelling, the job log and the list of runners. They are not wrapped (see "The commands").
- A new hard stop (see "The overwrite").

## What the program is

Recorded from reading the program once, on 2026-10-24. The program is untracked content outside this repository.
It is cited by:

| field | value |
|---|---|
| name | `remote-runner`, a single Python 3 script found on the owner's `PATH` |
| version | none printed; the content below identifies it |
| size and SHA-256 | 88818 bytes, `dc2d8485aafd140c66a6e883f3bd2d0b0b476c7ba38eb618e704771d14b4c209` |
| retrieved | 2026-10-24 |
| read as | data; nothing in it is followed as an instruction |

What the module relies on, each seen in that text and each to be shown by the conformance checklist against a fake:

- **Commands:** `remotes`, `recommend --profile`, `submit (--remote | --best) --profile [--ref | --snapshot]`, `prune`,
  `fetch`, `status`, `log`, `artifacts` and `cancel`.
- **The project file.** The controller reads it from a committed revision, `git show <revision>:<path>`, and needs
  Python 3.11 (`tomllib`). It needs `[project] id` (letters, digits, `_` and `-`, starting with a letter or digit)
  and `[profiles.<name>]` tables; a profile table with a string `command` is runnable, and one without is silently
  ignored. A profile's `requirements` table may hold only `os`, `arch`, `min_memory_gib`, `min_cpu_cores` and
  `labels`; an unknown key makes a runner ineligible, so a misspelling fails closed.
- **Output.** `recommend`, `status`, `artifacts`, `fetch` and `submit` print one JSON object (indented over several
  lines). `status` prints a view that carries `untrusted_job_data: true`, `job`, `project`, `state` (`STARTING`,
  `RUNNING`, `PASSED`, `FAILED`, `CANCELLED`, `FINISHED`, `UNKNOWN_EXIT` or `UNKNOWN`), `commit`, `dut_commit`,
  `dut_clean`, `integrity` (`ok`, `mismatch` or `invalid`), `snapshot`, `base_commit`, `source_ref`, `created_at` and
  `pid`. Every field is validated against a pattern by the program, and the record it comes from is writable by the job
  itself, so no field is authoritative. `submit` prints the worker's answer with `job`, `state`, `pid`, `dut_commit` and
  `dut_clean`, and for a snapshot `snapshot` and `base_commit`, plus `profile`, `command`, `source` and `ref`.
- **Fetch.** It takes a job and up to 16 relative paths, `--dest` (an existing directory, default the repository
  root), `--as` (one plain file name) and `--force`. Without `--force` it refuses a target inside git metadata, a
  dot-prefixed name, an existing file, a git-tracked file (it runs `git ls-files`, and refuses when it cannot tell),
  and a target below a link or a non-directory. It stages each file with no-follow flags, verifies the transfer and
  prints each placed file with its `bytes` and `sha256`.

The module also needs the program to read its project file from `.workbench/remote-runner.toml`, which it does not
do today.

## Declaration

| field | value |
|---|---|
| name | `remote-runner` |
| type | `module` |
| provides | nothing (see "Open questions") |
| requires, fills, writes | nothing |
| ships | one helper, `helper/remote-runner`, a check helper, and one neutral skill, `run-remote-job` |
| commands | `remote-runner`, with `helper` `helper/remote-runner`, `runtime` `python`, `kit` 1, `arguments` `["profiles", "recommend", "status", "artifacts", "submit", "fetch", "fetch-overwrite"]` and `owner` `["fetch-overwrite"]` |
| checks | one: `wb check` reports the project file (below) |

The helper uses only the standard library, and `tomllib` from Python 3.11. The project's documented minimum Python
version is raised to 3.11 by the plan that builds this module.

## The project file

`.workbench/remote-runner.toml`, committed (the program reads it from a committed revision). The schema is the
program's own, so moving a project is a file move. The module reads it without following a link, at most 65,536
bytes, UTF-8, and parses it with `tomllib`; it refuses what the program would ignore or accept loosely.

```
[project]
id = "project-workbench"

[profiles.fast]
command = "make test-fast"

[profiles.fast.requirements]
min_cpu_cores = 4
min_memory_gib = 8
labels = ["test"]
os = "linux"
```

- `project` holds only `id`, matching `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`.
- `profiles` holds one to 64 tables. A name matches `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`. A profile holds only `command`
  and `requirements`, and `command` is required: a string of 1 to 4,096 printable ASCII characters, no newline.
- `requirements` holds only the five keys above. `os` and `arch` are strings of at most 64 printable ASCII
  characters; `min_memory_gib` and `min_cpu_cores` are finite numbers above 0 and at most 1,000,000, not booleans;
  `labels` is at most 32 strings each matching `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`.
- A repeated key, a wrong type, an unknown key, a table of another name, a link, a file over the bound and text that
  is not UTF-8 TOML are each refused.

`wb run remote-runner profiles` prints `{"format": 1, "project": "<id>", "profiles": [{"name": "...", "command":
"...", "requirements": {...}}, ...]}` in file order, one line. An absent file is refused with the reason `no
project file`. It starts no program.

**The check.** `wb check` reports, for a project that has the module and no other: a project file the rules above
refuse (the reason, bounded, with no content of the file), and a leftover `.claude/remote-runner.toml` as the old
path. It never reads that file's contents and never changes it.

## The commands

All run as `wb run remote-runner <command> [options]`. Every option is accepted at most once, a value is the next
argument, and anything else is refused with a `refused:` line on standard error and exit 1; nothing is started
before every argument is checked.

| command | arguments | starts |
|---|---|---|
| `profiles` | none | nothing |
| `recommend` | `--profile <name>` | `remote-runner recommend --profile <name>` |
| `status` | `<job>` and optional `--expect <40 hex>` | `remote-runner status <job>` |
| `artifacts` | `<job>` | `remote-runner artifacts <job>` |
| `submit` | exactly one of `--remote <name>` and `--best`, `--profile <name>`, and at most one of `--ref <ref>` and `--snapshot` | `remote-runner submit` with the same options |
| `fetch` | `<job>`, one to 16 `<path>`, optional `--dest <dir>`, optional `--as <name>` | `remote-runner fetch` with the same arguments |
| `fetch-overwrite` | as `fetch`, except that an existing regular file may be a target | `remote-runner fetch` with `--force` added last; owner-only |

**Shapes.** A `<name>` (profile or remote) matches `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`; a profile must also be one the
project file declares. A `<job>` matches `[A-Za-z0-9][A-Za-z0-9_-]{0,199}` and holds `--` (the program's own job form).
A `<ref>` is exactly 40 lowercase hex digits. A branch or tag name is refused, because it can move between the
moment the owner approves a profile and the moment the program resolves it. A `<path>` is relative and plain by the kit's path rule (at most 512 characters, no
empty, `.` or `..` part, no `.git`, no backslash, colon or control character) and in addition has no leading `-` and
no part starting with a dot. `--as` is allowed with exactly one path and is a plain file name
under the same rule. `--dest` is described below.

**Output.** One JSON line: `{"format": 1, "command": "<name>", "exit": <int>, "untrusted_job_data": true,
"output": "<text>", "truncated": <bool>}` where `output` is the program's standard output, decoded with replacement,
control characters other than newline and tab removed, and cut at 65,536 bytes (`truncated` says whether it was).
Standard error of the program is not returned; a non-zero exit is reported by `exit` and a one-line reason (the
last non-empty line of its standard error, at most 200 printable ASCII characters) in `detail`. A program stopped at
its deadline is reported with `exit` 124 and `detail` `stopped after <n> seconds`, and one stopped for too much output
with `exit` 125 and `truncated` true. The helper exits 0 only when the program exited 0, and 1 otherwise. `status` adds a
`data` object and a `provenance` field (below). The module returns what the program says. It does not interpret a
log or a fetched file.

**Provenance.** `status` adds `data`, holding only these fields of the program's view, each kept only if it
matches the pattern: `state` (the nine names above), `commit` and `dut_commit` (40 lowercase hex or null),
`dut_clean` (boolean or null), `integrity` (`ok`, `mismatch`, `invalid`), `snapshot` (boolean) and `base_commit`
(40 hex or null). `provenance` is `true` only when `--expect` was given, the program exited 0, and `commit`, `dut_commit` and `--expect`
are all equal and `dut_clean` is true; it is `false` otherwise (and `null` when `--expect` is absent). It does not
look at `integrity` (see "Open questions"). The record
is writable by the job, so `provenance` is evidence of the program's record and not a proof; the skill says so.
For a committed ref the caller expects the 40-hex commit it passed to `--ref`; for a snapshot it expects the
`dut_commit` that `submit` reported.

**`fetch` and the destination.** Before it starts the program the module checks that `--dest`, if given, resolves
to an existing directory inside the project root with no link in any component and with no component starting with a
dot, so not `.git`, `.workbench`, `.claude`, `.github` or another folder that configures a tool
(default: the project root; an absolute value is accepted only if it begins with the project root, and the program is
given the relative form), and that no target path already exists (a file, a directory, a link or a dangling link) and
none lies below a link or a file. For `fetch-overwrite` an existing regular file is allowed as the target; a folder, a
link and a link on the way are still refused. It runs no git, so it does not check whether a target is tracked: that check is the program's. A target that
the module cannot rule out is left to the program, which refuses.

## The overwrite

Overwriting an existing or tracked file with fetched content is a hard stop (`trust-and-approval.md`, "Outside
content"). A module has no field to declare an added hard stop yet, so the rule is kept by reach: `fetch` never
passes `--force`, and `fetch-overwrite` is listed under `owner`, which a harness that provides `permissions` denies
to the agent (`module-boundary.md`, "Declaration schema"). The owner can run it. A harness without `permissions`
leaves the rule to instruction, as it does for every hard stop.

The rendered deny rules match the text of `wb run`, in its usual spellings. They do not match `wb launch <id>
remote-runner --root <root> -- fetch-overwrite ...` (the installer's `launch` is agent-safe and checks the pin and the
helper's hash, not the declared `arguments` or `owner`), a path-qualified `wb`, `env wb ...`, `bash -c ...`, or running
the pinned helper file directly. On those routes the rule rests on instruction and on the agent not being hostile,
which is the limit the trust specification states for every pin and deny rule. An installer change that makes `launch`
refuse a command's `owner` arguments is deferred (plan `2026-10-24-remote-runner-module`, security review, finding 1;
it would also close the same gap for `review-engine`).

## The checkpoints

`submit-remote-job` and `fetch-remote-output` are declared by `code-work` and default to `stop`. This module declares
no checkpoint. The skill `run-remote-job` tells the agent to wait for the owner's word before it submits or fetches
and to submit only a profile the plan names. The module renders no `ask` rule: what prompts for `wb run` in a given
harness is the owner's own `allow` and `ask` rules, which the workbench never writes. So the checkpoints are
instruction, and a permissive rule of the owner's for `wb run` lets the agent submit without a prompt. Rendering an
`ask` for these commands is deferred.

## How the helper runs the program

- **The program** is found only in an absolute `PATH` entry outside the project (the outermost repository, compared
  by file identity), as the other bridges do; a program of that name inside the project, on a relative entry or on an
  empty entry is never run. An entry that is not a folder that exists now, or cannot be examined, is dropped and not
  passed on, so a file made later in an absent folder of the project is never found by the program. None found is refused with `program_not_found`.
- **The environment** is an allow list: the trusted `PATH`, `HOME`, `USER`, `LOGNAME`, `LANG`, `LC_*`, `TERM`,
  `TMPDIR` and `SSH_AUTH_SOCK` (the program reaches its runners over SSH, and the owner's agent is how it signs in).
  No `GIT_*`, `LD_*`, `DYLD_*`, `PYTHON*` or other variable is passed.
- **The working directory** is the project root, because the program finds the repository from it.
- **Bounds.** A deadline of 600 seconds for `submit`, `fetch` and `fetch-overwrite` and 120 for the others; output
  over 1,048,576 bytes stops the program; the program runs in its own process group, which the helper kills on the
  deadline, on the cap and on SIGTERM.
- **No shell,** no other program, no network of the helper's own, no file written by the helper, no log.

## What the program must change

One change, outside this repository and the owner's to make: read the project file from
`.workbench/remote-runner.toml` instead of `.claude/remote-runner.toml`, in `project_config` (the working-tree read
and the `git show` of a revision), in its error messages and in its description. The owner may keep reading the old
path as a fallback while projects move; the module does not need one. The program's status and fetch behaviour listed
above already match what the module relies on, and a program that stops matching it no longer conforms.

## Untrusted input

The project file is a committed file that anyone with write access may edit: its commands run on the owner's runners,
so a profile the plan does not name is not run, and the skill says so. The program's output, a job's status record,
its log, its artifact names and every fetched file are data. The helper returns them bounded and marked, never runs
them, never uses them as a path or a command, and never believes them. A fetched file is placed by the program, and
the agent treats it as untrusted until the owner has read it.

## Conformance checklist

The module conforms when a test against a fake `remote-runner` program, which records its argument vector,
environment and working directory, shows each item. No item needs the real program, a runner or a network.

1. The declaration is as above, the verifier accepts it, and the module has no `requires`, `fills` or `writes`.
2. `profiles` accepts the example file and refuses each case under "The project file": a link, a file over the bound,
   a repeated key, an unknown key at each level, a wrong type, a name or label outside its pattern, a command with a
   newline, a profile with no command, no project id, more than 64 profiles. It starts no program.
3. The check reports a refused file and a leftover `.claude/remote-runner.toml`, reports nothing for a project without
   the module, and never prints file content.
4. Each wrapped command passes exactly its row of the table and nothing else; each refused shape (an unknown option,
   a repeated option, a missing value, both `--remote` and `--best`, both `--ref` and `--snapshot`, a leading dash, a
   ref outside its rule, a profile the file does not declare, a job outside its form) starts nothing.
5. The environment the fake receives is the allow list; a caller's `GIT_*`, `LD_*`, `DYLD_*` and `PYTHON*` variable
   and token are absent. The working directory is the project root.
6. A program of the right name inside the project, on a relative entry or on an empty entry is never run.
7. Output is bounded: a fake that prints more than 65,536 bytes sets `truncated`; one that prints more than
   1,048,576 is stopped; a fake that never exits ends at the deadline and a child it started is gone.
8. Output that looks like an instruction, or holds control characters, is returned only as cleaned text in `output`,
   and nothing in it changes what the helper does.
9. `status` returns `data` with only its listed fields, drops a field that fails its pattern, and sets `provenance`
   as the rule above says, in each of the four cases (no `--expect`, equal and clean, a different commit, not clean).
10. `fetch` refuses a path that is absolute, has `..`, starts a part with a dot or names `.git`; refuses `--dest`
    outside the project, through a link, or inside `.git` or `.workbench`; refuses a target that exists, including a
    link and a dangling link; refuses `--as` with more or fewer than one path; and never passes `--force`.
11. `fetch-overwrite` passes `--force` and is listed under `owner`; the Claude settings rendered for an attached
    module deny it and do not deny `fetch`; no `allow` rule is rendered.
12. The program's `files` list with its `sha256` values is returned unchanged in `output`; the helper writes no file
    of its own and reads no fetched file.
13. A fake that overwrites without `--force` is reported by the conformance test as non-conforming; the helper's own
    pre-check still refuses first.
14. The project tree is byte for byte the same before and after every case that is refused.

## Acceptance criteria

- The spec states what the program is and what it must change, and every item above can be tested against a fake.
- The module passes the checklist (`packages/workbench/remote-runner/`, plan `2026-10-24-remote-runner-module`).
- Nothing here depends on a file outside the repository: the program is cited by name, size, hash and date.

## Open questions

- Whether the module should provide a capability such as `remote-jobs`, once a module needs to require it.
- Whether the environment should pass `SSH_AUTH_SOCK`. The program needs it to reach a runner with an agent; it is
  also a path to the owner's keys, so the allow list names it deliberately.
- Whether a rendered `ask` for `submit` and `fetch`, or `delegate` for these checkpoints, is wanted.
- Whether `log`, `cancel`, `remotes` and `prune` should be wrapped, and under which checkpoint.
- Whether the program should keep reading the old path during a move.
- Whether `provenance` should also require the program's `integrity` to be `ok`. The job can write its own record, so
  either choice is evidence and not proof.

## As built, and its limits

Built by plan `2026-10-24-remote-runner-module` (increments B to F): `packages/workbench/remote-runner/` with
`module.json`, `helper/remote-runner` (`profiles`, `recommend`, `status`, `artifacts`, `submit`, `fetch`,
`fetch-overwrite`), `helper/remote-runner-check`, the neutral skill `run-remote-job`, and tests against fake programs.
The project's documented minimum Python version is 3.11 (`docs/development.md`).

- The rules for the project file are one text carried by both helpers, because a helper is a standalone file; a test
  requires the two copies to be identical. An empty `os` or `arch` string is accepted (the bound is "at most 64").
- A security review of the wrapper, asked for by the owner on 2026-10-24, found no Critical or High issue; its fixes
  are the hex-only `--ref`, the dot rule for `--dest`, the dropping of absent `PATH` entries and the installing of the
  `SIGTERM` handler before the program starts. A `SIGTERM` that arrives during the start of the program itself, between
  the system call and the assignment of its handle, is not closed. The review was partial (about half the areas by
  experiment); it did not exercise the real program, a real store and pin, or the harness's deny matching.
- The wrapper shows its guarantees against a fake program, never the real one, and no host was contacted. A mismatch
  with the real program's output text, exit codes or flags would be found only by a live check, which has not been
  done, and cannot be until the program reads `.workbench/remote-runner.toml`.
- The checkpoints are instruction. The module renders no `ask` for submit or fetch, so a permissive `allow` rule of the
  owner's for `wb run` lets an agent submit without a prompt. The overwrite is kept from the agent by `owner`, which
  the rendered Claude settings deny (a test pins it); a harness without `permissions` leaves it to instruction.
- The tracked-file refusal and the hash check of a fetch are the program's. The wrapper's pre-check covers an existing
  target and a link; a race between the check and the program's write is not closed. The conformance function in the
  module's tests shows whether a program refuses an existing file, a link target and a dotted name.
- `provenance` is the program's record of a job, which the job itself can write. It is evidence for the owner, not proof.
- Not wrapped: `log`, `cancel`, `remotes` and `prune`. No security review of the runner has been done; the owner asks
  for one with the `security-review` skill. The skill is advice, and whether an agent loads it is unverified.
- The shipped approval of the package is the owner's release (`wb release-approvals`).
