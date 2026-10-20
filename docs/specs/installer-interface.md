# The installer's commands and options

Status: Draft. Being written by the plan `2026-10-20-installer-interface`; not yet approved by
the owner. Only the commands marked built exist; the rest are proposals until their
candidates are built. Rules are marked **rule**; option and command spellings are
**proposals** and may change when the code that uses them exists. A statement the owner has
decided is marked *(owner)*; a statement that is the author's choice and not the owner's is
marked *(my call)*; a statement read from the current code and not from a spec is marked
*(from the code)*.

Terms are defined in `terms.md`. What each operation does to a project is in
`repository-boundary.md`; who may approve what is in `trust-and-approval.md`.

## Purpose and scope

This specification defines the installer's command line: which commands there are, what
each takes, how the directory a command works on (the target) is chosen and checked, and
what each command reads, writes and refuses. The preview and approval flow, the output and
the exit codes are defined in later sections of this document.

Non-goals:

- What an operation writes into a project, and the order. That is `repository-boundary.md`
  and `module-contract.md`.
- Approval records, hard stops and settings. That is `trust-and-approval.md`.
- Anything that commits, pushes or publishes. No command does (`repository-boundary.md`).

## Words used here

`terms.md` defines project, clone, package and project ID. This specification adds three
words for its own use:

- **target**: the project directory a project command works on.
- **project command**: a command that acts on the state of a project: `install`, `attach`,
  `check`, `upgrade` and adding a module.
- **package command**: a command that acts on a package directory, a download or a helper
  and not on a project's state: `verify`, `approve`, `pin`, `launch` and
  `release-approvals`.

## Invoking the workbench

- **rule:** an agent and any script call the `wb` launcher, not `python3 -m workbench`. The
  `-m` form puts the current directory first on the module search path, so a project's own
  code could run in its place (decision `2026-10-20-isolated-launcher-invocation`).
- **rule:** the usage text and every message that names a command say `wb`. *(From the code:
  they say `python3 -m workbench` today; a later plan changes that and this one does not.)*

## The target

These are **rules** and apply to every project command. The roadmap candidate settles
rules 1 to 3, the one-time resolution in rule 6, rule 8's printing, rule 9, and the refusal of
the root, the home directory and the guarded store. The rest were added by this plan and by
review: rules 4, 5 and 7, the identity and descriptor parts of rule 6, the cleaning in rule 8
and the order in rule 10. They are *(my call)* until the owner approves this document, except
where marked *(owner)*.

1. The target is one value with two spellings: a positional `<target>` or `--dir <path>`.
2. If neither is given, the target is `.`.
3. If both are given and name the same directory, that is accepted. If they differ, the
   command refuses and writes nothing.
4. An empty string is not a spelling. It is a usage error *(from the code)*.
5. A spelling is inspected before it is resolved. Trailing separators and `.` components are
   removed, and if the final component is a symbolic link, whether it points to a directory
   or nowhere, the command refuses *(owner)*. Each given spelling is inspected, so a link
   and its destination are never "the same directory". A link in a parent directory is not
   refused; it is resolved by rule 6.
6. The target is then resolved to an absolute path once, opened without following links, and
   the open descriptor and its device and inode are kept. Every later check and write works
   from that resolved path and descriptor, never from the typed spelling. Before anything is
   written, and again after any approval, the path is checked against the kept identity, and
   the command refuses if it changed. A directory that does not exist is made by a
   directory-relative create inside its held parent.
7. "The same directory" in rule 3 is judged by file identity when both exist, and by the
   resolved path when neither does.
8. A command that writes prints the resolved absolute target before it prints a preview. The
   printed path is cleaned of control and direction characters first (`display.clean`).
9. Whether a command creates a new project or works on an existing one is decided from the
   state of the target and not from the spelling, as the table below says.
10. The checks run in this order, and the first failure ends the command: usage errors (exit
    2, before the guarded store is touched); the guarded store is ensured and seeded, as
    every command does first; rule 5; rule 3; rule 6; the refused places; the state.

A refusal writes nothing in the project and adds no entry for the project to the guarded
store. It does not undo the ensure-and-seed of the store itself, which every command does.

### Refused places

A project command refuses a target that is, or whose nearest existing ancestor is:

- the filesystem root;
- the current user's home directory, whether it is named by `HOME` or by the account
  database;
- the guarded store or any path inside it;
- a directory that contains the guarded store *(my call: a target such as `~/.config` would
  place a project around the store; subdirectories of the home directory are fine)*.

Places are compared by file identity (device and inode), not by comparing path strings, so a
case variant or a different Unicode spelling of the same directory on a case-insensitive
volume is the same place *(my call)*. A target that does not exist has no identity; its
parent is compared for "is or is inside the store". The comparison is the one `safefs.is_within`
already makes *(from the code)*.

### States of a target

| state of the resolved target | outcome |
|---|---|
| does not exist, and its parent is an existing directory | new project; `install` creates the directory |
| does not exist, and its parent does not exist | refused; the installer does not create a chain of directories *(my call)* |
| an empty directory | new project |
| a directory that holds only `.git`, and `.git` is a real directory (not a link, not a file) | new project |
| a directory with its own `.git` that is a real directory, and `.workbench/manifest.json` that is a regular file (not a link, not a directory) | existing project *(owner)* |
| any other directory | refused |
| a file, or any other non-directory | refused |
| a symbolic link, as the typed final component | refused by rule 5 |
| a refused place | refused |

- **rule:** an existing project is recognized without running any git command. The manifest
  does not have to be committed: the installer never commits, so a project is existing
  straight after `install` *(owner)*. `check` reports whether the manifest is committed.
- **rule:** a project must have its own `.git` directory. A directory inside a larger
  repository, a `.git` file (a worktree or submodule) and a `.git` link are refused. This
  narrows the roadmap's "a lone `.git` is allowed" to a real directory *(my call)*.
- **rule:** git is not run in a directory to classify it. An operation that must run git in a
  project (for example attach, which adds to `.git/info/exclude`, and `check`) runs it with
  the repository's configuration unable to execute anything: no filesystem monitor, hooks,
  pager, external diff, text conversion or alias, and the global and system configuration
  ignored. A hostile `.git/config` can otherwise run a program of its choice, which a review
  of this document demonstrated. The exact options are a proposal, and the build of the first
  command that runs git must test them against a hostile configuration.
- **rule:** which operation a command can perform is limited by the state. `install` needs a
  new project; `attach`, `check`, `upgrade` and adding a module need an existing one. A
  command used on the wrong state refuses and says which state it found *(my call)*.

## The commands

The roles are rules; the spellings are proposals. "Writes" names the most a command may
write. Every command except a usage error first ensures the guarded store exists and is
seeded (`trust-and-approval.md`), so "nothing" below means nothing in a project and nothing
in the store beyond that ensure and seed.

| command | kind | takes | writes | terminal only | state |
|---|---|---|---|---|---|
| `install` | project | target, a module selection | committed content, manifest, the project's store directory, then per-clone harness files | decided with the approval flow | proposed |
| `attach` | project | target | per-clone harness files, `.git/info/exclude`, the local manifest | no | proposed |
| `check` | project | target | nothing | no | proposed |
| `upgrade` | project | target | after an approved preview, new content, left uncommitted | decided with the approval flow | proposed |
| add a module | project | target, a module | the same as `upgrade`, new files and blocks only | decided with the approval flow | proposed |
| `verify` | package | a package directory (`<package>` or `--dir`), `--select`, `--no-harness-required` | nothing | no | built |
| `approve` | package | a package directory, or `--source` with an optional `--ref`; `--module` | the guarded store: approval records, the cache | yes | built; `--dir` proposed |
| `pin` | package | a project id, a name, a helper, `--root` | the guarded store: a pin | yes | built |
| `launch` | package | a project id, a name, `--root`, arguments after `--` | a private copy of the pinned helper under `bin/run/` while it runs, removed afterwards | no | built |
| `release-approvals` | package | nothing | the shipped first-party records in the workbench distribution | no | built |

- `verify --no-harness-required` turns off the rule that a selection needs a harness module
  (`module-contract.md`). It is a check option and installs nothing, so it does not weaken a
  project; an install never offers it *(my call)*.
- `approve` and `pin` record an owner's approval or pin in the guarded store and each need a
  terminal on both standard input and standard output. **rule:** no command an agent is
  meant to run records an owner approval or a pin. The terminal test is friction and not
  authentication; what stops an agent is the harness's deny rule on these commands and on the
  store (`trust-and-approval.md`, "Residual risk").
- `release-approvals` is a maintainer's release-time command. It needs no terminal and
  writes only the shipped records in the workbench distribution, never an owner approval in
  the guarded store.
- `launch` returns the helper's own exit code, so a helper that exits 1 looks like a refusal
  by code alone; the refusal text on standard error tells them apart.

## Decisions on the package and helper commands

Answered by the owner on 2026-10-20.

1. **Package argument.** `verify` and `approve` share the two spellings for their package
   argument: a positional `<package>` or `--dir <path>`, which must agree or the command
   refuses, with the same-directory test above. The meaning is a package directory, not a
   project, and no project state is classified. `verify` does this today; `approve` gains
   `--dir` in a later plan. Neither gains a default of `.` for `approve`; it still needs a
   package or `--source` *(my call)*.
2. **`pin` and `launch` keep `--root`.** It names a project directory that is not a target in
   the sense above, since no state is classified, and renaming it would change commands that
   already have users. They do not accept `--dir`.
3. **A symbolic link as the target is refused** (rule 5). The user typed one place and the
   installer would act on another. The user gives the real path to proceed.
4. **A project is existing by its files and not by git** (the states table). A fresh install
   is an existing project before it is committed.

## Departures from the roadmap's wording

For the owner to see in one place:

- "Accepted by every command" is read as every project command. Package commands keep their
  own arguments (decisions 1 and 2).
- "A directory with a committed manifest" becomes "its own real `.git` and a regular-file
  manifest", decided without git, because a fresh install is uncommitted and because running
  git in an untrusted directory can run its code *(owner)*.
- "A lone `.git` is allowed" requires a real directory.

## Deferred

- The preview, approval flow, output contract and exit codes: later sections of this
  document, written by the same plan.
- Whether a target must be owned by the current user, or not a mount point. An empty
  directory such as a shared or system one is a new project today *(noted by review)*.
- Removing a module, format migration and three-way merge, which no command performs in
  this version.
- Changing the existing parser, usage text and option names.
