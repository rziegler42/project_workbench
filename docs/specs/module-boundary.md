# Module boundary

Status: Current. Approved by the owner on 2026-10-21. It directs the work but changes no other document by
itself: `module-contract.md`, `trust-and-approval.md` and the accepted decisions stay as they are until they
are updated, and the decision `2026-10-21-installer-runs-document-checks` stays in force until the owner
accepts a decision that supersedes it. No code follows from it until a plan is approved.

Terms are defined in `terms.md`. The terms this specification adds (the **kit**, a **module command**, a
**module check**, a **maintainer directory**) are added there with the first plan that builds them.

## Purpose and scope

The workbench is an installer plus packages of modules. This specification fixes where the line between
them falls, so that the installer stays small and vendor-neutral and a module can be added, changed or
removed without touching it.

**The rule.** The installer's code (`workbench/`) and the installer's tests (`tests/`) contain mechanism
only. Anything that is specific to one module lives inside that module's directory: its code, its tests,
its tooling and its documents. A module is specific when its behaviour, rules, names, paths or output
would be meaningless if the module were absent.

The specification also defines the three mechanisms a module needs in order to keep that rule: a place
for its tests and tooling, a way to give the user a command, and a way to contribute to `wb check`. All
three need one shared library, because a pinned helper is a single file and cannot reuse the installer's
careful file-reading code.

Non-goals:

- The content of any module. `groundwork`, `code-work`, `safe-git` and `claude` keep the specifications they have.
- How a module is approved, pinned or acknowledged. That stays in `trust-and-approval.md`.
- A plugin system. A module still declares data and ships files; it still gets no way to run at install,
  or to change what the installer does to another module.
- Sandboxing a helper. A pinned helper still runs with the caller's privileges (`trust-and-approval.md`,
  "Pinned helpers").

## What is mechanism and what is module content

| mechanism, stays in the installer | module content, lives in the module |
|---|---|
| declaration schema, verification, hashes, ordering | the rules a module's documents follow (names, statuses, indexes) |
| approvals, first-party records, the gate, acknowledgement | the checks that enforce those rules |
| the guarded store, pins, the launcher, the `wb` wrapper | the commands a module offers its users |
| ownership classes, baselines, upgrade, recovery | the plan check, the report and every other helper |
| the neutral item format and the translation engine | the text of skills, agents, commands and blocks |
| reading a harness's layout from its declaration | the layout itself: paths, tool names, rule syntax, import form |
| the no-follow reader, budgets, display cleaning | nothing: these are the kit, below |

A change to a module that touches `workbench/` or `tests/` is a sign that mechanism is missing, and the
missing mechanism is specified here, not worked around.

## The kit

The **kit** is a small library of the workbench, not of any module. It holds what every module helper
needs in order to read untrusted repository content safely and to report:

- the no-follow, bounded reader (`safefs`): a root, a relative path, never a followed link, a size and
  count budget, a regular-file test;
- finding a project from a directory: a `.git` directory, a real `.workbench` directory and a regular
  manifest, with `lstat` only and a depth limit;
- reading the committed manifest and the project's ID;
- reading what a check needs of a hostile project, all without following a link: a file that may be
  absent (`Root.read_if_present`, which also refuses a file with more than one hard link), a directory
  listing with the kind of each entry (`Root.list_dir`), a file below `.git` (`Root.git_bytes`), the
  paths git tracks read from `.git/index` (`wbkit/gitindex.py`) and strict JSON (`wbkit/jsonstrict.py`);
- cleaning text for a terminal (`display.clean`) and decoding bytes with `replace`;
- running another module's command through the launcher (`wbkit/call.py`, below);
- the report form of a module check (below) and the exit-code convention.

Rules for the kit:

1. **Standard library only, and itself.** The kit imports nothing from the rest of the workbench and no
   module. The installer imports the kit too, so there is one implementation of the careful code and not a
   copy in each helper.
2. **No module content.** The kit knows no module name, no document kind and no harness.
3. **Versioned.** The kit exposes its integer API version as `wbkit.API`. A Python helper's declaration
   names the version it needs (`kit`, below), and the runner, not the helper, enforces it (see "How a
   helper reaches the kit"). A change to the kit that can break a helper raises the number; the
   first-party modules are released against the kit they ship with.
4. **Part of the workbench, not of the module.** It is installed with the workbench, and its integrity is
   the workbench's, the same as the launcher's. A module cannot ship, replace or shadow it.
5. **Small.** It is reviewed as security-sensitive code. A function enters it only when two helpers (or a
   helper and the installer) need it.

### How a helper reaches the kit

A helper that declares itself a Python helper (below) is run by the launcher through a fixed runner:
the isolated interpreter (`python3 -I <runner> <kit> <copy> <arguments>`, so neither the project's
directory, nor the helper's, nor `PYTHONPATH` is on the search path). The runner loads the kit by file
location: it executes `wbkit/__init__.py`, found beside the runner, as the module `wbkit`, with the kit's
directory as the package's location, and registers it in `sys.modules`. No directory is added to the search
path, so the rest of the workbench cannot be imported by name and a `wbkit.py` anywhere else is never read.
After the version check below, the runner executes the private copy of the pinned helper as `__main__`,
by reading it once and compiling those bytes as UTF-8 text in a fresh `__main__` module, and `sys.argv` set to the copy's path followed by the
arguments, as for any script. The runner does not catch `SystemExit` or any other exception from the
helper: the helper's exit code, and a traceback if it fails, reach the caller as they would from the helper
run alone. A helper that is not a regular file, is not UTF-8 text, contains a NUL byte, or begins with
the bytecode magic number is refused, so an archive, compiled code or a coding cookie cannot make what runs
differ from the bytes that were read (`runpy.run_path` is not used, because it would run a zip archive's
`__main__.py`). The helper does `import wbkit` (and `import wbkit.safefs`). A helper of any other kind is run as
it is today and gets nothing.

**The kit comes only from the workbench.** The kit is the `wbkit` directory inside the workbench
distribution that holds the launcher's own code, found from the runner's own file location and never from
the current directory, the project, the environment or the guarded store's project data. The runner is a
fixed file of the workbench too, not a module's. If the kit is not there, or cannot be loaded, the runner
runs nothing and refuses with a `refused:` line and exit 1. A module cannot ship, name or shadow the kit,
and the runner adds nothing to the search path.

**The runner enforces the version.** The launcher passes the declaration's `kit` number to the runner.
Before it imports the helper's code, the runner compares that number with `wbkit.API`. If they differ, it
runs nothing, prints `refused: this helper needs kit API <n>; this workbench has <m>` to standard error
and exits 1, the launcher's refusal form. A helper cannot skip the check by not making it, and a kit
whose API is not an integer, or a helper declaration with no `kit`, is refused the same way. The
number is an exact match, not a minimum: a kit change that raises it needs each helper's declaration
(and so its approval) updated with it.

The pin still covers the helper's bytes and only those. The kit is not pinned per project: it is the
workbench, and changes with a workbench upgrade the owner runs. A kit change that breaks a helper
stops it with a refusal, as above, instead of letting it run wrongly.

## Module directories

The reserved directories of a module become `harness/`, `templates/`, `files/`, and two **maintainer
directories**:

| directory | holds | installed | run by the installer |
|---|---|---|---|
| `tests/` | the module's tests | no | never |
| `tools/` | scripts for the module's maintainers (building, regenerating, measuring) | no | never |

- A maintainer directory is accounted for by the verifier, covered by the module's tree hash and by its
  approval, and never copied into a project. Content nobody installs is still content the owner
  approved: an unhashed directory in an approved package would be a place to put anything.
- `ships` is unchanged: it names what is installed and runs at use time. A script a user runs belongs in
  `ships`, not in `tools/`.
- A module's tests may import the installer and the kit, the repository's shared test support
  (`tests/support.py` and `tests/support_*.py`), and load the module's own files by path. They may not import another module's
  tests.
- **One command runs everything.** The repository's full test command becomes
  `python3 -B -W error tests/run_all.py`, recorded in `docs/development.md` in place of the `unittest
  discover -s tests` form. `tests/run_all.py` is installer mechanism. It sets `sys.dont_write_bytecode`
  before importing anything, then discovers the root `tests/` and each directory matching
  `packages/*/*/tests/` in turn, each as its own unittest discovery with that directory as both start and
  top-level directory (module directories have hyphens and are not import packages). Between roots it
  removes the previous root's test modules from `sys.modules`, so two modules may each have a
  `test_helper.py`. It runs them all, reports each root by name, and exits non-zero if any fails. A new
  module is tested by adding its `tests/` directory and nothing else.
- The command passes `-B` and the script also sets the flag itself, because a `__pycache__` in a module
  fails verification as an unaccounted file.

### What the installer's own tests may use

The installer's tests prove mechanism, so they run on **synthetic modules** they build in a temporary
directory, with made-up names. They name no first-party module, package file or helper. The one
exception is the test that the shipped package verifies and installs, which belongs to the release
mechanism (`firstparty.py`) and may name the package directory.

## Module commands

A module may offer commands to the people and agents working in a project that has it. A **module
command** is a pinned helper plus a declared set of first arguments.

Declaration, in `module.json` (a new field):

```json
"commands": {
  "code-work": {"helper": "helper/code-work", "runtime": "python", "kit": 1,
                "arguments": ["check", "plans", "report"]}
}
```

- The key is the command's name, a name in the existing helper-name form. The helper is an item of
  `ships`.
- `runtime` is `python` (run through the runner, with the kit) or `exec` (run as the launcher runs a
  helper today). The default is `exec`.
- `arguments` is the list of accepted first arguments. The installer refuses any other first argument
  before it runs anything; the helper checks its own arguments as well. A command with no `arguments`
  accepts none and is run as `wb run <command>`.
- `kit` is the kit API number, required when `runtime` is `python` and refused otherwise.

Invocation: `wb run [--provides <capability>] <command> [<argument> [more arguments]]` from anywhere inside a
project. The one option, `--provides`, is read only before the command: it makes the installer refuse,
running nothing, unless the module that declares the command provides that capability. The check uses the
declaration whose hash was just compared with the manifest, and the installer names no capability. A command whose
`arguments` list is empty accepts no argument at all: `wb run <command>` runs it and any argument is
refused. A command whose list is not empty requires a first argument that is in the list; the arguments
after it are passed to the helper unchanged. The installer
finds the project root and ID (the kit's finder, the same refusals as today), takes the command from the
declaration of a module that the project's committed manifest records, looks up the pin for the command's
name, and hands the launcher the helper. It adds no behaviour of its own. `wb run` is classified
the way `launch` is: agent-safe, because it can run only a helper whose bytes match an owner-set pin, and
because the owner, not the module, decides what is pinned.

A command name that two installed modules declare is refused at install. A command whose helper is not
pinned is refused with a message that says so. The installer pins the helper of a declared command or check
in the step where the owner confirms the install, add or upgrade by digest (`trust-and-approval.md`,
"Pinned helpers"), so a command is unpinned only when its pin is absent, as in a project installed
before the installer pinned.

**The pin must name the declared helper.** Before it launches, the installer computes the helper's
installed path from the declaration, `.workbench/<package>/<module>/<helper path>`, and requires the
pin's recorded path to equal it exactly. A pin under the right name that records any other path, such as
another module's helper or a file the owner pinned for something else, is refused and nothing runs. The
same rule applies to a check. The launcher still verifies the bytes against the pin; this rule makes the
pin answer the question "is this the declared helper", which the hash alone does not.

**The pin also records how the helper runs.** The project holds both the manifest and each `module.json`, so
a pulled commit can edit a declaration and recompute its hash in the manifest; the two then agree. The pin
lives in the guarded store, so it records the `kit` number the helper was pinned with: the installer takes it
from the declaration the owner confirmed, `pin ... --kit N` from the owner (none for an `exec` helper). The launcher takes the kit from the pin, never from its caller, so `launch` and
`wb run` run a pinned helper the same way, and `wb run` also refuses unless the pin equals the declaration's. What a project can
still change is the `arguments` list: it filters mistakes and is not a security boundary, so a helper must
validate its own arguments. Whoever can write the project can rewrite a declaration together with its recorded
hash, so the owner who pins a command's helper with `pin` approves how it handles any first argument, not a
closed set. A pin the installer makes also records the declaration hash the owner confirmed, and `wb run` and
`wb check` refuse when the manifest holds another, so a pull cannot widen `arguments` for it.

### A helper that runs another module's command

A helper may run a command that another installed module declares, and only through the kit's
`wbkit/call.py`, whose `run_command` starts `wb run [--provides <capability>] <command> <arguments>` and
nothing else. The kit decides nothing about whether the command may run; the launcher does, so each of
these refuses and runs nothing: a command no installed module declares, a module that does not provide the
capability asked for, a pin that is absent or names another helper, a helper or declaration that changed
since it was pinned, and a first argument the declaration does not list. What the kit does:

- It finds `wb` only in an absolute `PATH` entry that is an existing directory and is outside the outermost repository that holds the project (the
  outermost ancestor with a `.git` entry, or the project root when there is none), compared by file identity so
  that a link or another case spelling does not pass, and rejects a file that resolves into it. If there is
  none it raises and runs nothing.
- It builds the environment itself: `HOME`, `XDG_CONFIG_HOME`, `USER`, `LOGNAME`, `LANG`, `TZ`, `TERM`,
  `TMPDIR`, any `LC_*`, and a `PATH` of the trusted entries. No `GIT_*`, `LD_*`, `DYLD_*` or other variable of
  the caller is passed.
- It passes the command and each argument as one literal argument with no shell: a command name is a plain
  name, at most 64 arguments of at most 4,096 characters without a NUL.
- It writes at most 1 MiB to standard input, reads standard output to a bound the caller sets and keeps the
  last 4,096 bytes of standard error. The command runs in its own process group, and at the time limit, or
  when the output passes the bound, the whole group is killed. The result says which happened.
- It returns the exit code, the output and the error text as data. A refusal by the launcher is exit 1 and a
  `refused:` line in the error text; the helper's own exit code is returned as it is.

Output of another module's command is data to the caller: it is bounded, validated by the caller and never run
or followed. The rule adds no authority. The caller's module being approved is not approval of the callee,
which runs only because the owner confirmed its module and so its pin; and a pin check is not a sandbox, so the
callee runs with the caller's privileges (`trust-and-approval.md`, "Pinned helpers"). There is no depth limit
beyond each call's time limit; a module that calls a module that calls it is a design error the owner's
approval of both is meant to catch.

The installer knows no command by name. The `code-work` entry in the agent-safe list, `dispatch.py`
and the `code-work` branch in `cli.py` were replaced by this, and `code-work` declares its own command.

## Module checks

A module may contribute to `wb check` for a project that has it. A **module check** is a pinned helper
that reads the project and reports.

Declaration (a new field): `"checks": [{"helper": "helper/doccheck", "kit": 1}]`. Each helper is an item of
`ships`. A check is always a Python helper run through the runner with the kit, so it declares no
`runtime` and must declare `kit`, and it takes no arguments.

Behaviour of `wb check`:

1. After its own checks, it runs the checks of each module the committed manifest records, through the
   launcher, from the project root. The order is the manifest's own: modules sorted by package name and
   then module name, by code point, and within a module the order of its `checks` list. It does not
   depend on the order in which modules were installed, added or upgraded, which the manifest does not
   record.
2. A check helper writes **report lines** to standard output, one per line: `problem: <text>` or
   `warning: <text>`, and nothing else. It exits 0 when it ran, with or without lines; any other exit, or
   a line in another form, is a problem of `wb check` itself: "the check <name> failed", with the cleaned
   start of its output.
3. `wb check` cleans every line, bounds the number and length of lines it takes (a bound that is passed
   is reported, as the existing budgets are), and prints them under the module's name. The launcher reads a check's
   standard output itself, at most 256 KiB and for at most 120 seconds; a helper that passes either is
   stopped, with the processes it started, and that is a problem of `wb check`. Standard input is closed,
   and only the last 4 KiB of standard error is kept, to say why a helper failed. A helper cannot
   write a line that looks like the installer's own.
4. A check helper that is not pinned, or whose bytes no longer match the pin, is a **problem**, not a
   skip: a silent skip would let a damaged module look clean. The other checks still run.
5. `wb check` stays read-only and agent-safe. The helper runs with the caller's privileges and is
   trusted to be read-only exactly as far as its owner-approved bytes are; the kit makes the reading safe
   and cannot make the helper write nothing.

Once this specification is approved and built, `doccheck`, `refcheck` and `refindex` leave the installer.
That contradicts the accepted decision `2026-10-21-installer-runs-document-checks`, which stays in force
until the owner accepts a decision that supersedes it. Nothing in this draft changes it, and no
implementation follows from the draft before that decision is accepted.

## Declaration schema

These are the exact shapes and refusals for the two new fields, in the style of `module-contract.md`
("Concrete schema"). Every refusal names the module and the field. A module's `commands` and `checks` are
checked with the rest of its declaration, before anything is written.

**`commands`.** An object with at most 16 entries.

- A key is a command name in the helper-name form (letters, digits and `._+-`, at most 64 characters,
  starting with a letter or digit).
- A value is an object with these fields and no others:
  - `helper` (required): a path in the path form of `module-contract.md`, equal to an item of `ships` or
    to a file below an item that is a directory. It names a regular file of the module.
  - `runtime` (optional): `"python"` or `"exec"`, default `"exec"`.
  - `kit` (an integer from 1; required with `"runtime": "python"`, refused with `"exec"`).
  - `arguments` (optional): a list of at most 16 distinct strings, each `^[a-z][a-z0-9-]*$` and at most 32
    characters, default empty.
  - `owner` (optional, built by plan `2026-10-23-review-engine`): a list of distinct strings, each one of this
    command's `arguments`, default empty. These are the arguments only the owner runs. A harness that provides
    `permissions` denies the agent each of them (`trust-and-approval.md`, "Rendering rules"), and `wb run` and
    `wb launch` run one only when standard input and output are both terminals (plan
    `2026-10-24-owner-run-in-code`). The declaration authorizes the first argument only, so a form that must be allowed to the agent and a form that must not
    are two arguments of the command.
  - `describes` (optional; *the verifier and the launcher rule are built by the plan for `safe-git describe`; the
    engine's use of it is not*): a list of at most 16 distinct strings, each `^[a-z][a-z0-9-]*$` and at most 32
    characters, default empty. These are the actions the command's `describe` argument answers, in the sense of the
    decision `2026-10-25-describe-interface-for-action-review`. It is allowed only when `describe` is one of the
    command's `arguments`, and `describe` may not be listed in `owner`: the engine runs `describe` for the agent's
    command and it is read-only by contract. *Built (verifier, increment A; launcher, increment B of that plan):*
    `wb run` and `wb launch` run `describe <action>` only when the second argument is in the command's `describes`,
    and refuse `describe` with no action, with an action not listed, and with any action when the list is empty. The
    rule is generic and names no module.
- Refused: an unknown field, a wrong type, a duplicate key (the parser already refuses it), a `helper` that
  is not in `ships`, a `runtime` other than the two, a duplicate `arguments` entry, an `owner` entry that is not a
  string, is repeated or is not one of the command's `arguments`, and two entries of one
  module that name the same `helper`. For `describes`: an entry that is not a string, a
  duplicate action, an action that fails the form, a non-empty `describes` on a command whose `arguments` lack `describe` (an empty list is allowed, as the default), and
  `describe` in `owner`.

**The engine's admission rule for `describe`.** The action-review engine accepts a (module, action) only when the
command is pinned for an installed module, `describe` is among its `arguments`, and the action is in its `describes`.
Anything else is refused and nothing runs. This is the test "the module provides `describe` for that action" in the
accepted decision (record 5). The `describes` list is part of the declaration, so it is covered by the declaration
hash as written, like the other optional fields; for a pin the installer made, a pull cannot add an action without
the owner re-confirming the declaration. A pin the owner made by hand records no declaration hash, so there
`describes` is a filter like `arguments`, not a security boundary. The field is additive, so no contract version bump is needed.

*Alternatives that lose.* A capability per action: capabilities are one project-wide namespace of names with no action
argument, so `describe` for an action cannot be named as one. A module-level list: it would not say which command's
`describe` answers, and the pin is per command.

**`checks`.** A list of at most 16 objects with exactly the fields `helper` (as above, required) and `kit`
(an integer from 1, required). No two entries name the same `helper`, and a helper may not be both a
command's and a check's. An unknown field or a wrong type is refused.

**Pin names.** A command is pinned under its command name. A check is pinned under the last segment of its
helper path, which must itself be in the helper-name form. Pin names are one namespace for the project.
Across the selected modules, a pin name given twice (by a command or a check, in one module or two) is
refused at install, and the message names both modules.

**Accounting.** A helper named by `commands` or `checks` is already accounted for by `ships`. The module
verifier also accounts for the two maintainer directories (`tests/`, `tools/`) as reserved directories,
exactly as it does `harness/`, `templates/` and `files/`, and counts them in the tree hash. No other
accounting rule changes.

**Changes to `module-contract.md` on approval.** Add `commands` and `checks` to the module-field table and
to "Concrete schema"; add `tests/` and `tools/` to the reserved directories and to "Module files"; state
that the installer does not copy a maintainer directory; add the pin-name uniqueness rule to "Set
checks"; and correct the sentence that says the installer never runs a helper to say that it never runs
one at install and may run a pinned one at use time through `wb run` and `wb check`.

## Harness paths come from the harness module

The installer reads a harness's paths from that module's `layout` and from nowhere else. The roots, the
generated directories and the tolerated paths that `wb check` uses come from the layouts of the harness
modules of the running workbench's distribution (`workbench/harnesses.py`, `layout.facts`), and the settings
path is checked by a rule that names no harness: exactly two segments, a dot-directory then a name ending
`.json`, covered by the layout's `exclude`. A harness no module describes (`opencode` and `codex` today) is
not recognised until a module for it exists; its table entries were removed and not kept as data.

One residual stays in the installer: the tool-name guards `RULE_NAMES`, `TOOL_NAMES` and
`INERT_TEMPLATE_NAMES` in `layout.py` list the names of the harness's own tools (for example the names a
rule may use). They are a guard on what a module may render, not a path, and the boundary test does not
flag them. They move into the harness layout with the second harness (`opencode-harness`), when a second
set of tool names makes the shape of that declaration known.

## Where the module-specific code goes

This is the inventory the move plans start from.

| now | goes to |
|---|---|
| `workbench/doccheck.py` | *(done)* `groundwork`'s `helper/doccheck`, a check helper over the kit |
| `workbench/refcheck.py`, `refindex.py` | *(done)* `groundwork`'s `helper/refcheck`, one check helper over the kit |
| `workbench/dispatch.py`, the `code-work` branch in `cli.py`, `"code-work"` in the agent-safe list | *(done)* the generic `wb run`, driven by `code-work`'s `commands` |
| `HARNESSES` in `check.py`, `SETTINGS_PATHS` in `layout.py` | *(done)* read from the `claude` module's `layout`; the tool-name guards stay until `opencode-harness` |
| `tests/test_codework_*.py`, `test_dispatch.py` | *(done)* `packages/workbench/code-work/tests/` (installer-side routing tests are rewritten on synthetic modules) |
| `tests/test_groundwork_module.py`, `test_doccheck.py` | *(done)* `packages/workbench/groundwork/tests/` (`test_docset_fixture.py` stays: `support_install` imports it) |
| `tests/test_refcheck.py`, `test_refindex.py` | *(done)* `packages/workbench/groundwork/tests/` |
| `tests/test_claude_module.py` | *(done)* `packages/workbench/claude/tests/` |

`safefs`, `display`, project finding and manifest reading move into the kit and are imported by the
installer from there.

## Acceptance criteria

- The verifier accepts `tests/` and `tools/` in a module, counts them in the tree hash and the approval,
  and the installer copies neither into a project. A module with an unlisted directory is still refused.
- `python3 -B -W error tests/run_all.py` runs the tests in `tests/` and in every `packages/*/*/tests/`,
  and a test in a package-local directory that records its own execution shows it ran. Two modules with a
  same-named test file both run. The package still verifies after the run, with no `__pycache__` in it.
- A boundary test (`tests/test_boundary.py`) fails if any file name, directory name or line of a file of
  `workbench/` or `tests/` names a first-party module, a helper, a command, a harness name or a harness path.
  The words are derived from the `module.json` files under `packages/` and a short list of harnesses that
  have no module yet (`tests/fixtures/boundary-words.json`), so a new module widens the rule without editing
  the test. It skips `tests/fixtures`, `workbench/shipped_approvals` and `__pycache__`, and fails on an
  unreadable or oversized file and on a symlinked directory. It cannot see a name built at run time or split
  across lines, and it ignores words of fewer than three characters.
- With `packages/` emptied, the installer's own tests pass and none is skipped for want of a package.
- A Python helper run by the launcher gets `sys.argv` as above, its exit code reaches the caller
  unchanged, and a helper that raises is not hidden by the runner. A `wbkit.py` in the project, in the
  current directory, beside the helper or on `PYTHONPATH` is never imported in place of the workbench's
  kit, and no directory is added to the search path.
- The kit imports only the standard library and itself, names no module, and exposes `wbkit.API`. A
  Python helper whose declared `kit` differs from it, or has none, is refused by the runner with exit 1
  and the `refused:` line, and the helper's code is not imported.
- A Python helper run by the launcher reaches the kit, and a project directory containing a hostile
  `wbkit.py`, `json.py` or `sitecustomize.py`, or a hostile `PYTHONPATH`, is not read.
- The verifier accepts `commands` and `checks` of the shapes above and refuses each refusal listed there,
  naming the module and the field.
- `wb run <command>` runs a command whose `arguments` list is empty and refuses any argument to it. A
  command with a non-empty list refuses `wb run <command>` with no argument.
- `wb run` runs a declared command with a declared first argument; refuses an undeclared first argument,
  an unpinned helper, a helper with a changed hash, a path outside a project, and a command name two
  modules declare; and runs nothing in each of those cases.
- `wb run --provides <capability> <command>` runs the command only when the module that declares it provides
  the capability, and refuses, running nothing, for another module, an unknown command, a malformed
  capability name, and (as without the option) an unpinned or changed helper. The option is read only before
  the command.
- `wbkit.call.run_command` runs a pinned command through the real launcher with standard input passed
  through, and, with a fake launcher, shows: the literal argument list, the environment holding only the
  listed variables, a `wb` inside the project (also through a link, a relative entry or an empty entry) never
  run, output cut at the bound, a time limit that kills the command and its children, a command that never
  reads its input not hanging the caller, and every malformed argument refused before anything starts.
- `wb check` runs a module's checks, prints their cleaned and bounded lines, and reports an unpinned,
  edited, failing or malformed check as a problem while the other checks still run.
- A pin recorded under a command's or check's name but for a different path is refused and nothing runs,
  for a command and for a check.
- Modules installed in different orders give the same check order, the manifest's.
- Commands and checks come only from modules the committed manifest records. A module absent from the
  manifest declares none, so its leftover pin or files run nothing.
- After the move, the installer's tests pass on synthetic modules with every first-party module absent
  from the distribution.

## Deferred

- **Removing a module.** The repository-boundary rules make removal a non-command, and an upgrade does not
  shrink the manifest. This specification neither adds removal nor changes that. If removal is ever
  specified, it must say what happens to the manifest entry, the installed files and the pins; until then
  a module's commands and checks exist exactly when the manifest records the module.

- **An MCP adapter.** A server that exposes the agent-safe commands (`verify`, `preview`, `check`,
  `run`) as tools is possible once `wb run` and `wb check` are generic, and is out of scope until a
  harness needs it: one that has no usable shell, or an agent that needs typed results. If built, it is a
  separate optional module started through the launcher so its bytes are pinned, it calls the same code
  paths as the command line and adds no logic of its own, its tool list is fixed from declarations and
  never from repository content, and it exposes no owner-run command and no write tool. Its permission
  rules are rendered by the harness module, as the `Bash` rules are.

## Choices made

The owner agreed to these on 2026-10-21. They are part of the draft and become binding when the owner
approves the specification.

1. **Contract version.** The new fields (`commands`, `checks`) and the maintainer directories are added to
   contract 1, because nothing has been released. `module-contract.md` is changed to match when this
   specification is approved.
2. **`runtime`.** It is a value declared on the command, `python` or `exec`. It is not inferred from a
   file's first line.
3. **Installer tests.** They use synthetic modules only. The cost is a fixture builder that module tests
   can reuse.
4. **Module check output.** Plain `problem:` and `warning:` lines, not a structured form, to keep a
   single-file helper simple.
5. **Order of work.** The kit and the maintainer directories first (no behaviour change), then `wb run`
   with `code-work`, then module checks with `groundwork`, then the harness paths. Each is its own plan,
   and the open `code-work-plans` plan is reconsidered after the second.

## Related files and decisions

- `module-contract.md`, `trust-and-approval.md` ("Pinned helpers"), `installer-interface.md`,
  `harness-modules.md`, `groundwork.md`, `code-work.md`
- [2026-10-21-installer-runs-document-checks](../decisions/2026-10-21-installer-runs-document-checks.md)
  (to be superseded)
- [2026-10-20-isolated-launcher-invocation](../decisions/2026-10-20-isolated-launcher-invocation.md)
- [2026-10-20-first-party-by-location-and-shipped-record](../decisions/2026-10-20-first-party-by-location-and-shipped-record.md)
