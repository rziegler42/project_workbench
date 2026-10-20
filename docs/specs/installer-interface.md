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
- **rule:** git is not run in a directory to classify it. Where possible no git is run at
  all: the installer reads files itself and hashes them with no filters. Where an operation
  must ask git something (for example whether a path is committed, or whether the working
  tree is clean for the affected paths), git must never read the repository's own
  configuration or run anything the repository names. Reviews of this document showed a
  hostile `.git/config` running a program of its choice through a filesystem monitor, and
  through filter drivers named in a committed `.gitattributes`; a fixed list of `-c` options
  cannot name those drivers. The direction is a private git directory the workbench writes
  (a fresh configuration, a copy of the index, the real objects by alternates) used with
  `GIT_DIR` and `GIT_WORK_TREE`, the global and system configuration ignored, optional locks
  off, and a scrubbed `GIT_*` environment. **rule:** a read-only command leaves `.git/index`
  byte-identical. The exact mechanism is a proposal; the build of the first command that asks
  git anything must test it against a hostile configuration, and `attach` needs no git at all
  (see its section).
- **rule:** `.workbench` and `.workbench/local` must be real directories, checked without
  following links. A `.workbench` that is a link makes the target "any other directory", not
  an existing project.
- **rule:** which operation a command can perform is limited by the state. `install` needs a
  new project; `attach`, `check`, `upgrade` and adding a module need an existing one. A
  command used on the wrong state refuses and says which state it found *(my call)*.

## The commands

The roles are rules; the spellings are proposals. "Writes" names the most a command may
write. Every command except a usage error first ensures the guarded store exists and is
seeded and writes the `wb` launcher script (`trust-and-approval.md`), so "nothing" below
means nothing in a project and nothing in the store beyond that. A command that downloads a
package also writes a cache directory in the store and contacts the network; each section
says so.

| command | kind | takes | writes | terminal only | state |
|---|---|---|---|---|---|
| `install` | project | target, a module selection | committed content, manifest, the project's store directory, then per-clone harness files | decided with the approval flow | proposed |
| `attach` | project | target, `--harness` | per-clone harness files, `.git/info/exclude`, the local manifest | no, but owner-run (harness deny rule) | proposed |
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

## Project commands

All spellings in this section are **proposals**; every behavior stated is a **rule** unless
marked. Each command takes the target as above, runs the checks of rule 10 first, and
refuses with nothing written when any fails. **No command here commits, pushes or
publishes, and none edits a living or historical document** (`repository-boundary.md`).

### Rules common to the project commands

- **Write set.** What a command may write is bounded by the approved declarations only: a
  module's own namespace, its declared `writes` and its slot `fills`. Nothing in the
  committed manifest or the lock widens that set. A manifest entry that names a path outside
  it, or a living or historical path, or that claims an owner class the declaration does not
  give, is reported as a conflict and is never written. The manifest is untrusted text.
- **Exclusive creation.** Every file or block a command adds is created exclusively, without
  following links. A path that already exists, tracked or not, is a conflict for the owner;
  the local manifest or any scratch file does not change that. A command never overwrites a
  file except a module-owned file or block that the preview shows as a replacement and whose
  hash still equals the installed hash.
- **The manifest is acknowledged first.** A changed committed manifest, or a changed file
  under `.workbench/`, is first-tier content (`trust-and-approval.md`, Acknowledgement). A
  command that acts on it refuses until the owner has acknowledged the change.
- **Approvals come before a preview.** Every module a command would write must already be
  approved on this machine before a preview is produced. A missing approval refuses and names
  the modules; the owner runs `approve`. No preview is shown for something that cannot be
  applied.
- **A fetch is for what is approved.** `attach`, `upgrade` and `add` contact a source only for
  a package whose declaration and tree hashes already have an approval on this machine, and
  verify the fetched tree against those hashes. A source that only the committed manifest
  names is not contacted until the owner has approved that package here, so an agent-run
  command cannot be made to contact an address a hostile manifest chose. `install` contacts
  the sources the caller gives. A fetch writes a cache directory in the guarded store
  (`trust-and-approval.md`, Inert download).
- **Approval binds the write.** The approval of a preview binds its digest, which covers
  every path, owner class and byte to be written. After the approval and before the first
  write the command verifies again from the bytes it will write, and for each replaced file
  re-checks the hash on the held descriptor. Any difference refuses and writes nothing. The
  details are in the preview section (Increment C).
- **Baselines.** Approving an install or an upgrade preview updates the acknowledgement
  baselines for exactly the files in that preview (`trust-and-approval.md`).

### `install` (proposed)

`wb install [<target> | --dir <path>] --package <source> [--ref <ref>] ... --select <module> ...`

- **Needs:** a new project (the states table). An existing project is refused, and the message
  says to use `upgrade` or add a module.
- **Selection.** The modules to install are named as `verify` names them, `<module>` or
  `<package>/<module>`. Each package comes from a `--package` source: a local package
  directory or a URL, with `--ref` naming the branch, tag or commit of the `--package` before
  it *(proposal; how several packages and refs are written is settled by
  `base-and-manifests`)*. The selection must contain exactly one module of type `harness`, so
  install never offers `--no-harness-required` (`module-contract.md`: a harness is mandatory
  at install).
- **Reads and checks, in this order, before anything is written:** the common checks of rule
  10 (the guarded store first, the target state last); each source, downloaded inertly into
  the store's cache and never into the target; the selection as one install (`verify`,
  including counts, conflicts, requirements and install order); and that every module of the
  selection, the harness first, is approved on this machine (the gate,
  `trust-and-approval.md`). Install never records an approval.
- **Then:** the preview and its approval (see "The preview and approval", written by
  Increment C). Nothing is written to the target before the owner has approved the preview.
- **Writes**, after approval, in the order `module-contract.md` gives: the harness is verified
  and approved first, and its per-clone files are written last; the base, the process module,
  then the other modules; the project seed and ID; the committed manifest and
  `.workbench/.gitignore`; the project's directory in the guarded store with the record of
  where the project was first seen; the acknowledgement baselines for the files written; and
  last, attach for the chosen harness, which writes the per-clone harness files, the
  `.git/info/exclude` entries and the local manifest. Everything is left uncommitted.
- **Refuses** any verification failure, any missing approval, a state other than new, and a
  refused target. After a failure part-way, the report says what was written (Increment C).
- **Contacts the network and writes a cache directory** for each source that is not a local
  directory.
- **Agent may run it:** the command may be run by an agent, but it writes nothing until the
  owner approves the preview; who gives that approval is decided in Increment C.

### `attach` (proposed)

`wb attach [<target> | --dir <path>] --harness <package>/<module> [--package <source> [--ref <ref>]]`

- **Needs:** an existing project.
- **Reads:** the committed manifest and its lock, and the harness module. It requires approval
  of each module it uses, the harness module included, on this machine. A package the
  manifest names is fetched at the recorded commit into the inert cache, only if the owner has
  already approved it here (the common rule above), and its tree hash is verified against the
  lock.
- **The harness is not committed.** The committed manifest never names a harness, so the
  harness is given to attach, and its source, version and tree hash are pinned in the local
  manifest, `.workbench/local/harness.json` (`repository-boundary.md`). A fresh clone gets its
  harness from `--harness` and, where no committed package holds it, `--package`.
- **Writes** only per-clone harness files, created exclusively; adds their paths to
  `.git/info/exclude`; records the local manifest. It writes nothing that git tracks. It runs
  no git. The exclude file is opened with no-follow descriptors as a regular file, entries
  are anchored literal paths, a leading `!` or `#` and glob characters are refused, and an
  entry already present is not added twice. `safefs` refuses `.git` paths today, so this needs
  a primitive of its own *(from the code)*.
- **Refuses** when a local manifest already records a harness (changing harness means a new
  clone); when a harness path already exists (a conflict); a content-hash mismatch between a
  package and the lock; a module not yet approved on this machine. A difference in workbench
  version between the lock and the installed workbench warns and continues.
- **Prints** post-install notes for steps it cannot perform, such as a harness's project trust,
  and warns when a file it wrote changes the agent's permissions.
- **Agent may run it:** no *(owner)*. Attach writes the files that set an agent's own
  permissions, deny rules and instructions. Choosing and attaching a harness is the owner's
  act in setting up a clone, before an agent runs in it; the harness's deny rule on `wb
  attach` is the barrier, as it is for `approve`. It is not terminal-gated, because setting up
  a clone is routinely scripted by the owner.

### `check` (proposed)

`wb check [<target> | --dir <path>]`

- **Needs:** an existing project. It is read-only: it changes nothing in the project, leaves
  `.git/index` byte-identical, and writes nothing to the guarded store beyond the common
  writes.
- **Reports** the things `repository-boundary.md` lists: harness files of a harness other than
  the attached one; generated harness files whose hash has drifted; tracked files that look
  like harness output or scratch; tracked files that link into untracked content; committed
  files that differ from the manifest in a way their owner class does not allow. It also
  reports whether the manifest is committed *(owner's answer: an uncommitted manifest is not an
  error of the state, only a report)*, and "none attached" for a clone with no harness, which
  is valid.
- **The local manifest is not evidence.** The hashes in `.workbench/local/harness.json` are
  scratch, which grants no authority, so "no drift" says the files match the scratch record
  and not that they are safe.
- **Options:** none in this version.
- **Agent may run it:** yes. Any question it asks git is subject to the git rule in the states
  section.
- How it signals a problem is in the exit codes (Increment C).

### `upgrade` and adding a module (proposed)

`wb upgrade [<target> | --dir <path>] [--package <source> [--ref <ref>] ...]`
`wb add [<target> | --dir <path>] --package <source> [--ref <ref>] --select <module> ...`

- **Needs:** an existing project. Adding a module is an upgrade that brings in a new module
  (`repository-boundary.md`), so the two share the preview and approval and differ only in
  where the change comes from: a newer workbench or newer module versions (`upgrade`), or a
  module the project does not have (`add`).
- **Reads:** the committed manifest; the current files and their hashes; the new declarations
  and trees, downloaded inertly; and the approval of every new or changed module, which must
  exist before the preview is produced. A changed declaration or tree is a different subject
  and needs a new `approve`. `add` verifies the new module together with the modules already
  installed, so counts (one harness, at most one process module), conflicts, requirements,
  slot owners and order are checked as for an install.
- **Preview:** every change, classified as replace, skip, conflict or append, with the
  declaration change shown. It writes nothing. A declined append is reported with the marker
  to add and a suggested place. (Its exact shape and approval are in the preview section,
  Increment C.)
- **Writes**, only after the preview is approved: replacements of module-owned files and
  blocks whose hash still equals the installed hash; new files and new blocks; appended blocks
  where the owner approved the append; the updated `.workbench/manifest.json` (hashes, lock and
  workbench version) and the module's files under `.workbench/<package>/<module>/`; and the
  acknowledgement baselines for exactly the files in the preview. It never touches a seeded
  file, a plan, a spec, a decision, a roadmap or a reference, and never an edited module-owned
  file or block, which it reports as a conflict. `add` writes only new files and new blocks.
- **Requires** a clean working tree for the affected paths, and leaves its changes
  uncommitted so the owner can commit them as one revertable change. Cleanliness is decided
  under the git rule in the states section, or by comparing file hashes with the manifest. A
  fresh install is uncommitted by design, so an upgrade straight after it is refused until the
  owner commits; that is intended. It refuses when the installed workbench is older than the
  version recorded in the manifest.
- **Removing a module is not a command** in this version.
- **Contacts the network and writes a cache directory** for each source it fetches.
- **Agent may run it:** the preview, yes; applying it is decided in Increment C.

## The existing commands

Described as `workbench/cli.py` has them *(from the code)*. They are built. Differences from
the rules above are named so a later plan can change them; this plan changes none.

- **`verify [<package> | --dir <path>] [--select <module> ...] [--no-harness-required]`**
  Checks a package, and optionally a selection (`--select` takes one or more names) as one
  install. Prints one line per module with its version and the first 12 characters of its
  declaration and tree hashes, then, only when a selection was given, the install order; or
  `refused:` lines on standard error. Warnings go to standard output when the check is
  accepted and to standard error when it is refused. Writes nothing. Exits 0 accepted, 1
  refused, 2 usage error. The package directory is a positional argument or `--dir`, and
  defaults to `.`; if both are given and name the same directory that is accepted, and
  different directories are a usage error. Agent may run it. Never commits or publishes.
- **`approve (<package> | --source <url> [--ref <ref>]) [--module <name>]`**
  Owner-run, terminal on standard input and output. Shows the approval request, verifies again
  before writing, and records the module records before the package record. Without
  `--module` it approves every module and records the package too; with `--source` it
  downloads over the network into the cache first. Agent may not run it (harness deny rule).
  Differences: it has no `--dir`; the decision above gives it one.
- **`pin <project-id> <name> <helper> --root <dir>`** Owner-run, terminal only. Pins a helper
  file inside the project root by its content hash. `--root` names the project directory and
  stays *(owner)*.
- **`launch <project-id> <name> --root <dir> -- <args>`** Runs a pinned helper if its bytes
  still match the pin, from a private copy that is removed afterwards. The arguments follow the
  first `--` and are never parsed as options; `--` itself is optional and the argument list
  may be empty. Returns the helper's own exit code, or 1 with a `refused:` line if nothing was
  run. Agent may run it.
- **`release-approvals`** Writes the shipped first-party approval records into the workbench
  distribution. Needs no terminal. A maintainer's command at release time. Agent may not run
  it *(my call)*: its records count as approval because the distribution is the trust root
  (`trust-and-approval.md`), so running it in a modified checkout would approve modified
  first-party packages. The harness's deny rule on it is the barrier.
- **Usage text and name.** The usage text and the program name say `python3 -m workbench`;
  the rule above is `wb`. A later plan changes the text.

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
