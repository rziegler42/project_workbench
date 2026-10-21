# Development

## Setup

There is nothing to set up and no dependency is installed. The code is Python 3 using
only the standard library, and the repository assumes git, a POSIX shell and `python3`,
as `docs/specs/repository-boundary.md` states.

Minimum Python version: 3.6, the lowest minor version that has every language feature
written so far (f-strings are the newest). The checks have been run only on 3.14; the
minimum is derived from the features used, not from running older interpreters. Raise
it here whenever a later increment uses a newer feature.

## Commands

**Where to run them.** `python3 -m workbench ...` puts the current directory first on Python's
module search path. Run from inside a project you do not trust, a `workbench/` directory or a
`json.py` in that project would run instead of this code, with your privileges, whatever the
command (`approve` included). Run the commands below from a directory you trust, such as this
repository's root, or use the `wb` launcher (see "Pins and the launcher"), which does not have
this weakness. The examples keep the `python3 -m workbench` form because that is how the
checkout is run during development.

Keep this table accurate. Use `not applicable` rather than leaving an
ambiguous blank.

| Purpose | Command |
|---|---|
| Setup | not applicable (standard library only; nothing to install) |
| Run locally | `python3 -m workbench verify [<package> \| --dir <path>] [--select <module> ...] [--no-harness-required]` |
| Owner-run: approve a package or one module (terminal only) | `python3 -m workbench approve (<package> \| --source <url> [--ref <ref>]) [--module <name>]` |
| Owner-run: pin a helper's content (terminal only) | `python3 -m workbench pin <project-id> <name> <helper> --root <project-dir> [--kit N]` |
| Preview an install (read-only) | `python3 -m workbench preview install [<target> \| --dir <path>] --package <source> [--ref <ref>] ... --select <module> ...` |
| Owner-run: install a new project (terminal only) | `python3 -m workbench install [<target> \| --dir <path>] --package <source> [--ref <ref>] ... --select <module> ...` |
| Owner-run: accept changes made to a project (terminal only) | `python3 -m workbench acknowledge [<target> \| --dir <path>]` |
| Owner-run: clear the marker of an unfinished write (terminal only) | `python3 -m workbench recover [<target> \| --dir <path>]` |
| Owner-run: attach the harness to a clone (terminal only) | `python3 -m workbench attach [<target> \| --dir <path>] --harness <package>/<module>` |
| Check a clone (read-only) | `python3 -m workbench check [<target> \| --dir <path>]` |
| Preview an upgrade (read-only) | `python3 -m workbench preview upgrade [<target> \| --dir <path>] [--package <source> [--ref <ref>]] ...` |
| Owner-run: upgrade a project (terminal only) | `python3 -m workbench upgrade [<target> \| --dir <path>] [--package <source> [--ref <ref>]] ...` |
| Preview adding a module (read-only) | `python3 -m workbench preview add [<target> \| --dir <path>] --package <source> [--ref <ref>] ... --select <module> ...` |
| Owner-run: add a module (terminal only) | `python3 -m workbench add [<target> \| --dir <path>] --package <source> [--ref <ref>] ... --select <module> ...` |
| Run a pinned helper | `python3 -m workbench launch <project-id> <name> --root <project-dir> -- <args>` |
| Run a module command | `python3 -m workbench run <command> [<argument> ...]` from anywhere in the project (agent-safe; the command must be installed and pinned; the arguments after the first reach the helper unchanged) |
| Release time: write the approvals shipped with first-party packages | `python3 -m workbench release-approvals` |
| Verify the sample package | `python3 -m workbench verify tests/fixtures/sample-package --select sample-harness sample-notes` |
| One focused test file | `python3 -m unittest discover -s tests -p 'test_approvals.py'` (a test module that imports `support` only loads under `discover -s tests`); for a module's own tests, `python3 -B -m unittest discover -s packages/<package>/<module>/tests -t packages/<package>/<module>/tests` from the repository root |
| Full tests | `python3 -B -W error tests/run_all.py` (runs `tests/` and every `packages/*/*/tests/`, each as its own root) |
| Format | not applicable (none configured) |
| Lint or static analysis | not applicable (none configured) |
| Type check | not applicable (none configured) |
| Build | not applicable (none configured) |
| All required checks | `python3 -B -W error tests/run_all.py`; document checks are run by the owner in session, as `docs/README.md` states |

## The verify command

`verify` reads a package and writes nothing into it or anywhere else except the guarded
store (see below). The package is the positional argument or
`--dir`, defaulting to `.`; the same path given both ways is accepted, two different
paths are a usage error. Without `--select` it checks every module on its own; with it,
it also checks the named modules as one install (`<module>` or `<package>/<module>`),
and prints the install order. A harness module is required in a selection unless
`--no-harness-required` is given.

| Exit code | Meaning |
|---|---|
| 0 | accepted; one line per module with its version and the first twelve characters of the declaration and tree hashes, then warnings |
| 1 | refused; one `refused:` line per problem on stderr, naming the package or module and the rule |
| 2 | usage error |

`release-approvals` uses the same codes: 0 done (or nothing to do), 1 refused, 2 usage.

## Inert download

`workbench/fetch.py` brings a package into the guarded store's cache as data only, so the
owner can read its declaration before approving anything. `approve --source` and `install` call it. `fetch.fetch(store, source, ref)` returns the new
directory `cache/<id>/package/` (and `cache/<id>/fetch.json` beside it, with the source, ref,
resolved commit and counts) or raises `FetchError` and leaves nothing in the cache.

- **Sources:** an `https://` URL without credentials, an `ssh://` URL, a `file://` URL, or a
  local directory. Other transports (`ext::`, `git://`, plain `http://`), scp-style
  `host:path`, and anything starting with `-` or holding whitespace are refused. A ref is a
  branch, tag or commit name of letters, digits and `._/@+-`, not starting with `-`.
- **Nothing runs and nothing is checked out.** The ref is fetched into a private bare
  repository in a temporary directory outside the store, made with an empty template and with
  `core.hooksPath` pointed at an empty directory. Every `GIT_*` variable is dropped, the
  user's and system git configuration are ignored, prompts are off, only the `file`, `https`
  and `ssh` transports are allowed, incoming objects are checked, and tags and submodules are
  not fetched. Files are read with `git ls-tree` and `git cat-file`; there is no `checkout`,
  `clone` or shell.
- **The whole listing is checked before any content is read.** Every entry must be a regular
  file (a symbolic link or a submodule refuses the download), every path must pass the path
  validator, names that collide ignoring case are refused, and the limits are 2048 files,
  16 MiB per file and 64 MiB in total. Only the owner execute bit is kept.
- **Resource limits.** Every git command runs in its own process group, with its output read
  in chunks and capped, a timeout (300 s for the fetch and for reading the files, 60 s for the
  rest), and a limit on the size of any file it writes (four times the total limit, 256 MiB).
  On a timeout or an excess, git and everything it started are killed. A tree can share
  subtrees, so a tiny repository can list millions of files; the listing is read incrementally
  and git is stopped once it passes what 2048 files allow. The fetch uses `--depth 1` and
  needs git 2.32 or newer (for `GIT_CONFIG_GLOBAL`); fetching a commit id the server does not
  advertise can fail on servers that refuse it. ssh runs with `BatchMode`, and agent and other
  forwarding turned off.
- **The cache holds data and no repository.** Files are written into a staging directory and
  moved into place with one rename; the temporary repository is removed. A failure removes the
  staging directory. A cache directory is never reused, so every fetch makes a new one. Files
  get the default mode (0644 under the usual umask), or 0755 when git recorded the execute bit.
- **Limits:** this does not defend against a flaw in git's own handling of objects or in the
  network transport, and it does not verify who runs the server. An `ssh` source uses your ssh
  configuration and keys; an `https` source may use your credential helpers. A process killed
  outright (`kill -9`) can leave a `workbench-fetch-*` directory in the temporary directory
  or a `.incoming-*` directory in the cache. The code removes only the temporary and staging
  directories it made, with the standard library's `shutil.rmtree`. Tests use local `file://`
  repositories and never the network.

## Approving a package

`python3 -m workbench approve (<package> | --source <url> [--ref <ref>]) [--module <name>]` is how
the owner records an approval. Run it yourself, from your own terminal; the agent's command permissions will deny
it once a harness renders that rule (`claude-harness`). The checks in the command are
friction, not the barrier: a process that allocates its own pseudo-terminal passes the
terminal test, and the 12 characters are not a secret, because the request and `verify` both
print them. The typed text guards against a mistaken approval, and it is not authentication.

1. It refuses unless standard input and standard output are both terminals (tested on the
   file descriptors, not on an environment variable). There is no `--yes` or similar option.
2. It verifies the package and refuses on any problem, recording nothing. A package given as
   a symbolic link is refused.
3. It prints the request (see below), rendered from that one verification, and asks you to
   type the first 12 characters of the tree hash shown: the package's, or with `--module`
   that module's. Anything else cancels and records nothing.
4. Just before writing it verifies the package again and compares every hash with what it
   showed. A package that changed while you were reading is refused.
5. It records a `module` record for each module and then a `package` record, or only the one
   `module` record with `--module`. A harness or process module is approved on its own
   record (`--module`, or as part of the package). It writes only into the guarded store.
   If an approval is already on file the first record is kept, and the command says so.
   Module records are written before the package record, so a package that is approved has
   all its modules approved. If a write fails part way, the earlier records stay (they are
   valid) and the error lists the records written by that run.

The recorded approver is the account name from the operating system's user database, not
from an environment variable; it is text and grants nothing. Exit codes: 0 recorded, 1
refused or cancelled, 2 usage error.

**Approving from a source.** `--source` takes an `https://`, `ssh://` or `file://` URL or a
local repository, and `--ref` a branch, tag or commit (default `HEAD`). Give either a package
directory or `--source`, not both. The terminal test runs first, so nothing is downloaded when
it fails. The package is then downloaded inertly into the cache (see "Inert download"),
verified there, and the request, the hash you type and the records all come from that cached
copy; the request names the source, the resolved commit and where the copy is. The first
package approval stores the resolved commit as the pin.

- What is approved is the content, bound by the package tree hash. A ref that later moves to
  different content is a different tree hash and is not approved, and fetching the pinned
  commit again gives the approved content. The same content reached by another commit is the
  same approval: the first record, and its pin, is kept, and the command says so and names
  both commits when they differ.
- A module approved with `--module` has no package record and so no pin.
- A fetch that fails, or a copy that fails verification, records nothing. A copy that you
  decline or that fails stays in the cache so it can be read again; the command prints where.
  Nothing removes cache copies yet.
- A later install fetches the pinned commit and compares the tree hash with the approved one.

## Previewing and installing a project

`python3 -m workbench preview install [<target> | --dir <path>] --package <source> [--ref <ref>] ...
--select <module> ...` shows what an install would do and writes nothing. `python3 -m workbench
install` takes the same arguments and writes the project. `upgrade`, `add` and `acknowledge` are
in "Acknowledging, upgrading and adding" below, and `recover` in "Recovering from an unfinished
write".
The target goes before `--select`, or use `--dir`; `--package` may repeat and a `--ref` binds to
the `--package` before it. Options are not abbreviated.

- **A target** is a missing directory whose parent exists, an empty directory, or a directory
  holding only a real `.git`. A symbolic link, the root, a home directory, the guarded store
  or anything containing it, a directory with other content, an existing project and a
  directory holding `.workbench/local/incomplete` (an unfinished install or upgrade) are refused, before
  any source is read (`docs/specs/installer-interface.md`, "The target").
- **A source** is a local package directory (it holds `package.json`; a link is refused and a
  `--ref` cannot apply) or a URL. `preview` never fetches: a URL must already be in the cache
  from `approve --source`, and the newest matching copy is used. `install` downloads each URL
  source into the cache, inertly, after the target is accepted and before it prints the plan.
  Every module must be approved on this machine (the gate); neither command records an approval.
- **The preview** lists the target and its state, each module with its hashes, every action
  (directories, files with class, mode, size and hash, the `.git`) and the two store entries,
  and ends `preview only: nothing was written`. It uses a fresh seed each time, so its digest is
  not shown and differs from one run to the next.
- **`install`** is owner-run: it refuses unless standard input and output are terminals. It
  prints the same plan with its digest and asks for the first 12 characters of the digest.
  Anything else, an empty answer included, prints `cancelled: nothing was written` and exits 1.
  Input typed ahead is discarded and the answer is read to at most 200 characters. The typed
  text is friction and not authentication; the barrier is the harness's deny rule.
- **After the answer** it checks the target again (same directory, same contents), rebuilds the
  plan from the packages as they are now and refuses a different digest. The bytes written are
  those of the plan that was shown.
- **The write** creates `.workbench/local/incomplete` first, then the `.git` when there is none,
  the directories and files (the manifest last), the two store entries and last removes the
  marker. Git is not run: the empty `.git` is made with `mkdir` and a fixed skeleton written
  through held descriptors. Nothing is overwritten, and files get 0644 (0755 when
  executable), directories 0755, narrowed by the umask. It then prints the count of paths and
  `nothing was committed`.
- **The attach** is the last step, after the marker is gone: the plan lists the harness files, the
  `.git/info/exclude` lines and `.workbench/local/harness.json`, and the digest covers them. They
  are written as `wb attach` writes them (exclude lines, files, local manifest last) and the
  unfinished-write record does not list them. If the attach fails, `install` prints `failed:`,
  says the install is complete, names `wb attach --harness <package>/<module>` and exits 3;
  `wb attach` finishes it.
- **A failure after the first write** prints `failed:` with the cause, the paths written and not
  written, and that the marker is left, and names `wb recover`; the directory is then refused as
  an existing project until the marker is cleared. Nothing is cleaned up.

| Exit code | Meaning |
|---|---|
| 0 | done (`install`) or previewed (`preview install`) |
| 1 | refused or cancelled; nothing was written |
| 2 | usage error |
| 3 | stopped after writing; the marker is left |
| 130 | interrupted before anything was written |

## Acknowledging, upgrading and adding

Four commands work on an existing project, and each refuses a target that is not one (use
`install` for a new one).

```
python3 -m workbench acknowledge [<target> | --dir <path>]                    (owner-run)
python3 -m workbench preview upgrade [<target> | --dir <path>] [--package <source> [--ref <ref>]] ...
python3 -m workbench upgrade         <the same arguments>                     (owner-run)
python3 -m workbench preview add [<target> | --dir <path>] --package <source> [--ref <ref>] ...
                                 --select <module> ...
python3 -m workbench add             <the same arguments>                     (owner-run)
```

- **Before any of them acts.** The project must be known on this machine: the guarded store holds
  `projects/<id>/baselines` and a `seen` record at this resolved path. A copied or moved project is
  treated as new and refused. The manifest, every file under `.workbench/` outside `local/` (a
  file added or removed counts) and every file the command would write into must equal the
  baselines; any difference is refused, naming the paths, and the owner runs `acknowledge`. A
  project written by a higher workbench version than the running one is refused.
- **Packages.** Nothing is fetched. Each package the manifest records comes from `--package` when
  given, else from the newest cached download of its recorded source and ref (filled by `approve
  --source`); a package recorded as `local:<name>` must be given with `--package <directory>`.
  Every installed module is verified again and must be approved on this machine, even one whose
  files do not change; the harness-required rule is off, because the manifest names no harness. A module
  the package no longer declares is left in place.
- **The preview** classifies every path as `create`, `append`, `replace`, `skip` or `conflict`
  and shows each module with its declaration change, the directories and file writes with hashes,
  the store write, and `git: not run; nothing is committed`. A module-owned file is replaced only
  if it still equals what was installed; an edited, removed or retagged one is a conflict and is
  left alone. A seeded file's own text is never changed; only the blocks in the plan are written
  into it. A slot block is replaced only if its text is as
  installed, appended with its marker where the slot marker is missing, and skipped as "slot gone"
  where the owner removed the markers. Nothing is ever deleted. A preview ends `preview only:
  nothing was written`, or `nothing to change`.
- **`upgrade`** (owner-run) refuses unless standard input and output are terminals, prints the
  same plan with its digest and asks for the first 12 characters. It then re-reads the project
  and the packages, rebuilds the plan and refuses a different digest. It writes
  `.workbench/local/incomplete`, the new directories, the created files, the replaced files (each
  a hash-checked whole-file replace that keeps the original's narrower mode, never setuid, and
  0755 only for an executable), the manifest, the store's baselines, reads every written file
  back against the plan, and last removes the marker. It ends with the count of paths written, the
  conflicts and notes left as they are, and `nothing was committed; committing the result as one
  change makes it revertable`. Git is not run and no clean-tree check is made.
- **`add`** is the same pipeline with the modules named by `--select` added to those the project
  has. A selected module must be new (`<module>` or `<package>/<module>`; a harness cannot be
  added), the installed ones are verified and approved with it, and counts, conflicts,
  requirements, slot owners and order are checked together. It writes only new files, new blocks
  and the manifest: a change to an installed module, a replaced file, or a package given from
  another source, ref or commit than the recorded one is refused and `upgrade` is named.
- **`acknowledge`** (owner-run) lists every difference (path, kind, baseline hash, current hash)
  for the manifest, every file under `.workbench/` outside `local/`, and every other path with a
  baseline, with a summary of the manifest (packages, sources, refs, commits, module hashes and
  every file entry). It asks for the first 12 characters of the digest, re-reads, and replaces
  the baselines of exactly the listed paths in one atomic store write. It writes nothing in the
  project. A link, a directory or another non-regular file where a file is expected, and a name
  under `.workbench/` that fails the path rules (a control character, bytes that are not UTF-8,
  a colon or a backslash), cannot be acknowledged: it is listed with its reason and nothing is
  written, and `upgrade` and `add` refuse with it listed. More than 500 differences are refused.
  With none it prints `nothing to acknowledge`.
- **Failure.** A failure after the marker was made prints `failed:` with the cause, the paths
  written and not written, and a hint naming `wb recover`, leaves the marker, and exits 3; the
  directory is then not an existing project until the marker is cleared. `wb recover` clears it
  only where that is safe; there is no automatic repair of files: put them back from version
  control or a copy (see "Recovering from an unfinished write"). A marker that cannot be made
  exits 1 with nothing written. An interrupt after writing began exits 3.

| Exit code | Meaning |
|---|---|
| 0 | done, previewed, or nothing to change or acknowledge |
| 1 | refused or cancelled; nothing was written |
| 2 | usage error |
| 3 | stopped after writing began; the marker is left |
| 130 | interrupted before anything was written |

**Limits.** A file with more than one hard link is refused, since its other name may be outside the
project. The check of a file's hash and the rename that replaces it are not one operation, so
a write by another process in between is lost; the typed text is friction, not authentication,
and the harness's deny rule is the barrier. The comparison of a project with its baselines reads
at most 256 MiB of file content in one scan (each file at most 16 MiB, 20000 entries under
`.workbench/`, 32 levels deep) and refuses beyond it; `acknowledge` compares every baselined file
in the project, not only those under `.workbench/`, and `upgrade` scans twice, each time with a
fresh budget. After a reinstall at the same path, a manifest carrying an old seed
from git history is checked against the baselines kept for that seed, and `acknowledge` shows
the project id but does not highlight a change in it. A manifest source with
credentials stripped may not match the cache record.

`wb check` reads a clone and writes nothing. It reports harness files (drift against the local
manifest, files of another harness, strays) and what git tracks: tracked files that look like harness
output or scratch (`CLAUDE.md`, `.claude/`, `.debug/`, `.workbench/local/` and the files of the other
harnesses it knows), tracked Markdown documents that link or import (`[x](path)`, `[x]: path`, `href`,
`src`, `@path`) into content git does not track or out of the project (code, plain mentions of a path
and source files are ignored), committed files that differ from the manifest beyond their owner class (the working tree is compared)
(a module-owned file or a slot block that was edited; a seeded file may change), and whether the
manifest is tracked. For a project that has the `groundwork` module it also checks the form of
`docs/specs`, `docs/roadmaps` and `docs/decisions` (names, status, successor, candidate IDs) and the
reference index `docs/references/index.json` against the tracked files (`workbench/doccheck.py`,
`workbench/refcheck.py`, `workbench/refindex.py`); a project without the module gets none of this.
It never runs git: a repository can name programs git would run (a
filesystem monitor, a filter, an included file), so the paths come from `.git/index` itself, version
2, 3 or 4 with SHA-1 or SHA-256 names, in at most 16 MiB and 1,000,000 entries, paths of at most 4,096 bytes and 64 MiB in all. "Tracked" means in
the index, so a staged file counts. A split or sparse index is reported as a problem. At most 5,000
documents, 4 MiB of them and 5,000 existing-path lookups are examined, and a larger project is
reported as not fully looked at. The document checks add their own bounds: 2,000 documents, 4 MiB in
all, 1 MiB per document, 200 findings and 128 MiB of references (`groundwork.md`, "As built, and
its limits").

## Recovering from an unfinished write

`install`, `upgrade` and `add` write `.workbench/local/incomplete` first and remove it last. The
marker holds a record of the plan being written (`workbench/unfinished.py`, format 1): the
command, the project id when known, the workbench version, each file write (path, operation, the
hash before, the hash after), each directory the plan creates, the files of the `.git` skeleton
with their hashes, and each guarded-store write with its hash. It is canonical JSON, at most
1 MiB and 10000 entries, with the manifest's path rules; no path may be at or under
`.workbench/local`. The record is untrusted text and grants nothing: a marker that is empty (made
by an earlier version), truncated, oversized or malformed reads as "no record", and `recover` then
cannot help. A plan too large to record (about 5000 files) is refused before anything is written.

```
python3 -m workbench recover [<target> | --dir <path>]                    (owner-run)
```

- **Every other command that meets a marker** (`preview`, `install`, `upgrade`, `add`,
  `acknowledge`) refuses with the same report, and `recover` shows it without the last line: the
  command and version recorded, how many recorded files and store entries hold the state before
  the plan, the state after it, or something else, the paths to deal with, and that `wb
  recover` is the way forward. Reading is
  bounded (256 MiB in all), never follows a link and reads regular files only.
- **`recover`** is owner-run and terminal-only. It examines the project, shows the report and
  what it would remove, and asks for the first 12 characters of the digest, which covers the
  marker's bytes, the examination, the removals and the target's identity. After the answer it
  examines again and refuses a different digest.
- **It clears the marker only in these states** and refuses every other with the paths to deal
  with, writing nothing:
  - recorded files all in the state before the plan and the store entries all absent or old
    (nothing happened, or the owner put the files back): the marker goes, and so does each
    recorded directory that is empty, deepest first, with `rmdir` only; a failed `install` then
    leaves the target as it was and `install` can be run again;
  - files all in the state after the plan and every store entry written: only the marker was
    left, and it goes;
  - `upgrade` and `add` only, files after and no store entry written: the marker goes and
    `acknowledge` then lists exactly the written paths for the owner to accept. An `install` in
    that state, or with a partial store, is refused with the advice to put the project back,
    run `recover` again and install again. The workbench does not repair a store.
- **It never** writes or restores a file, removes a file other than the marker, removes a
  directory that holds anything, touches the store, or removes the target directory. More than
  500 removals, or `.workbench/local` holding more than the marker, are refused. The typed text
  is friction, not authentication.
- **Known limits.** The marker is unlinked by name a moment after the second examination, so a
  marker swapped in that window is removed instead of the one shown. A forged record can make
  `recover` remove empty directories the owner made, since `rmdir` refuses only non-empty ones;
  they are listed before the digest is typed.

| Exit code | Meaning |
|---|---|
| 0 | the marker was cleared, or there is none |
| 1 | refused or cancelled; nothing was removed |
| 2 | usage error |
| 3 | a removal failed or was interrupted after removal began; the message says whether the marker is still there |
| 130 | interrupted at the prompt |

## The distribution layout

The repository root is the distribution: `workbench/` (the code and `shipped_approvals/`),
`base/` (the content every project gets before any module: `AGENTS.md` and `docs/README.md`,
each holding a slot marker), the first-party packages, `docs/` and `tests/`. `base/` is trusted as
the code is and has no approval record; its tree hash is recorded in each project's manifest.

## Pins and the launcher

A helper such as the commit helper is a file of a module, so a pulled edit could replace it. The
owner pins it, and the launcher runs it only while its bytes still match the pin
(`workbench/pins.py`, `workbench/launch.py`). A pull that edits the helper changes its hash, so
it is not run until the owner pins it again.

- **Pin** (owner-run, from a terminal, like `approve`):
  `python3 -m workbench pin <project-id> <name> <helper> --root <project-dir> [--kit N]`. `--kit N`
  records that the helper runs through the kit runner with kit API number N; without it the helper
  runs directly. A module command is refused unless this equals what its declaration says. The project id
  is 64 lowercase hex digits (the hash of the project's seed, once projects exist). The helper
  must be a regular file inside the root; a symbolic link, a directory, a FIFO or a path
  outside the root is refused. The command shows the path, size, SHA-256 and the start of the
  file, says if it replaces an earlier pin, and records nothing unless you type the first 12
  characters of the SHA-256. It checks again just before writing. The pin is stored in the
  guarded store as `projects/<id>/pins`, with the path relative to the root so that clones at
  different locations share it.
- **Launch**: `python3 -m workbench launch <project-id> <name> --root <project-dir> -- <args>`.
  The helper's location comes only from the pin; the caller cannot name another file. The
  launcher reads `<root>/<pinned path>` through the safe reader (a real root directory, no
  symbolic link on the way, a regular file), hashes it, and compares it with the pin. If they
  match it writes those exact bytes to a new file in a private directory under `bin/run/` in
  the store (mode 0700) and runs that file with the arguments, with no shell, so a file
  swapped after the check changes nothing. The copy is removed afterwards. The helper's own
  exit code is returned. Anything that stops it from running exits 1 with a line starting
  `refused:` on standard error: no pin, a damaged pins file, a missing or unreadable helper, a
  symbolic link, or a hash that no longer matches (the message says to review it and pin it
  again).
- **Limits.** This is a pin check and not a sandbox: the helper runs with your privileges and
  environment, and the copy lives in a store directory that your own account can write. A
  helper should be a single self-contained file, because it runs from a copy in a different
  directory. A helper that exits 1 looks the same as a refusal by exit code alone, and one that exits 2 looks like a
  usage error; the `refused:` line on standard error tells them apart.
- **Example.** With a helper at `tools/commit.sh` in a project:
  `python3 -m workbench pin <id> commit tools/commit.sh --root .` (type the 12 characters),
  then `python3 -m workbench launch <id> commit --root . -- -m "message"` runs it. After
  someone edits `tools/commit.sh`, the same `launch` exits 1 with
  `refused: the helper commit has changed since it was pinned`, until you pin it again.
- **The `wb` launcher.** Every command makes sure the store has `bin/wb`, a short script that
  runs this workbench under `python3 -I` (isolated mode) with the workbench directory added by
  hand. It is fixed text apart from that one path, and is rewritten if the path changes.
  Isolated mode keeps the current directory and `PYTHONPATH` off the module search path, so a
  project that ships its own `workbench` package, a `json.py` or a `sitecustomize.py` cannot
  run in place of the real ones. The name `wb` is kept as
  the specs state it. When the script is written and another command named `wb` is already on
  your `PATH`, a warning names it; the warning never stops a command. Nothing is added to your
  `PATH`: to use it, put `~/.config/project-workbench/bin` there yourself. How the workbench
  itself is installed is not decided yet, so the script assumes the workbench is a directory on
  this machine.

## First-party packages and shipped approvals

The workbench distribution is the repository root: code in `workbench/`, first-party
packages in `packages/` (`workbench`, whose module `claude` is the Claude harness), and the approvals made for them in
`workbench/shipped_approvals/`. Shipping with the workbench counts as explicit approval, and
the records are read from the installed workbench, never copied into the guarded store.

- A package is first-party only if its directory is directly inside `packages/` (and is not
  a symbolic link), its declared name equals the directory name, and a shipped package
  record for that name matches the package's current declaration and tree hashes. Otherwise
  it is third-party. `verify` sets the verifier's `first_party` flag from this, so only an
  unchanged released package may provide an unprefixed capability name.
- The shipped records are trusted because the distribution is. Anything that can write the
  repository can add a package and run `release-approvals`, and the records it writes count
  as approval, so review what a release changes in `workbench/shipped_approvals/` (its git
  diff) before accepting it. The command does not need a terminal, because releases may run
  unattended.
- `python3 -m workbench release-approvals` is a release-time command, not one for users of a
  project. It verifies every package under `packages/` as first-party, writes nothing if
  any module fails verification (exit 1; a write that fails part way can leave the earlier
  records of that run, which are valid and a rerun is idempotent), and otherwise writes one record per module and per package with
  a fixed approver (`workbench-release`) and time, so a second run changes nothing. Records
  of an earlier release are left in place and reported with a warning, because deletion is
  not provided; remove them by hand. With no packages it prints `no first-party packages`
  and exits 0.
- A first-party package changed since release has no shipped approval for its new hashes,
  so its modules are checked against the guarded store like any other package.

## The approval request

`workbench/request.py` builds the text the owner reads before approving. No command prints
it yet; the `approve` command will. For a module it shows, in this order: a `HIGH RISK` line
when it applies, the identity (package, name, version, type, description, source), both
hashes in full, a size line with the count of each kind of entry, and then the details, one
section each: what it provides, requires (soft ones marked) and blocks (core capabilities
marked), the slots it owns and fills, the paths it writes into the project, every item it
ships (`[executable]` when a file under it has the owner execute bit, otherwise
`[code-bearing]`), any other executable file in the module (for example under `harness/` or
`files/`), the helpers it expects, and a harness module's layout, one line per leaf.

- A `harness` or `process` module, or one that blocks a core capability (an unprefixed name),
  is flagged `HIGH RISK`. A package request lists every module and which need an explicit
  approval of their own.
- Nothing a package controls is shortened: paths, layout values and lists are shown in full.
  A list of more than six entries gets a count and one line per entry, and the hashes and
  counts come before any list, so a long list cannot push them out of sight.
- Every package-supplied string is shown as ASCII. A non-ASCII character appears as an
  escape such as `\u0443`, so a lookalike letter cannot pass for a Latin one, and control,
  invisible and bidirectional characters become visible escapes.
- The text is built from the verification result: the parsed module, its hashes, and the
  files with the execute bit, all from the one tree walk that was hashed
  (`Verified.module`, `Verified.executable`). Nothing is read again, so what is shown cannot
  differ from what is recorded because a file changed between two reads.

`workbench/wbkit/display.py` (part of the kit) has the two cleaners. `clean` (used for the command's own messages)
keeps ordinary letters in any script and escapes control, invisible, combining, format,
separator and filler characters. `ascii_text` (used for the request) escapes everything
outside printable ASCII.

## The approval gate

`workbench/gate.py` answers whether a verified selection is fully approved on this machine.
`preview install` and `install` call it first, and it only reads. It takes the result of `verify_packages` for a selection and reports each
module in install order:

- A module is approved by a `module` record for its `<package>/<module>`, declaration hash
  and tree hash, or, for a plain module only, by a `package` record that matches the
  package's current hashes and lists the module with exactly its two hashes. A `harness` or
  `process` module always needs a record of its own.
- A first-party package is looked up in the shipped approvals first, then the guarded
  store; any other package only in the store. Each result says which supplied it.
- Only a module of type exactly `module` may use a package record. Any other type needs a
  record of its own.
- It fails closed: a refused verification, an empty selection, a malformed result, or a
  module the result does not describe is not approved, and a refused result looks nothing up.

Limits: the gate approves what `verify` hashed, not what an installer reads later, so an
installer must write from the exact bytes that were verified, or verify and gate again from
the same snapshot just before writing. The gate also takes each package's `first_party` flag
as given; the installer must set it from `firstparty.is_first_party`. A shipped record
matches only the exact subject and hashes it was made for, so a wrong claim gains nothing.

`verify`'s result now carries each module's type and, per package, the declaration hash and
whole-package tree hash (`Result.packages`), which the gate needs.

## The guarded store

Every command first makes sure the guarded store, `~/.config/project-workbench/`, exists.
It creates the directory and `packages/`, `cache/`, `projects/` and `bin/` with mode
`0700` when they are missing, and does nothing when they are there. The command line then
seeds the personal settings if they are missing (`Store.ensure` itself only makes the
directories, so settings depend on the store and not the reverse). A failure to seed ends
the command with exit code 1. Notes about the settings are printed with the verify
warnings and start with `settings:`. A store or one of
those directories that is a symbolic link, is owned by another user, or has any mode
other than `0700` (group or other access, setgid, sticky) is refused with exit code 1, and nothing is repaired. A usage error or
`-h` does not create it.

- The personal settings are the file `settings` in the store: strict JSON with a
  `version`, a `checkpoints` object (`stop` or `delegate` per checkpoint name) and a
  copy of the hard-stop floor's ids. A missing file is created. With no settings, or with
  any entry that is missing or not exactly `delegate`, a checkpoint stops. A damaged file
  is never overwritten: the command prints a `settings:` warning and everything stops
  until the owner repairs it.
- The hard-stop floor is compiled into `workbench/floor.py`. The copy in `settings` is for
  reading and rendering only; editing or deleting it changes nothing. `effective_stops`
  can combine added stops with the floor and refuses any removal; no module declares an
  added stop yet.
- The location is fixed. No workbench environment variable moves it; `HOME` decides it,
  as for any program run by the same account.
- The store is a mechanical barrier, not an operating-system one, and it shares the
  owner's account. Until `claude-harness` renders a deny rule on writes to it, it is
  protected by instruction only.
- Tests never touch the real store. They pass a temporary root, or set `HOME` for a child
  process, and `tests/support.py` fails a test that asks for the real location. After a
  full test run, `~/.config/project-workbench` should not have been created by the suite.

## Verification workflow

1. Run the narrowest check covering the change.
2. Inspect the complete useful failure output and correct the root cause.
3. Rerun the failed check.
4. Run the broader required check when practical.

Document checks that intentionally update snapshots, fixtures, generated code,
or tracked artifacts.

## Local debug artifacts

Keep retained, untracked diagnostics in
`/.debug/<YYYY-MM-DD>-<topic>/`. Opt in locally; do not add this directory to
the tracked `.gitignore`:

```sh
printf '/.debug/\n' >> .git/info/exclude
mkdir -p .debug
```

Include a local README with the source commit, command and tool versions,
purpose, and conclusion. These artifacts are not portable to fresh clones or
worktrees. Record durable findings in tracked documentation, decisions, or
tests instead.

## Debugging

Run `python3 -m unittest discover -s tests -v` for per-test output of the repository's tests, or
the focused module form above with `-v`. Run all commands from the repository root.

## Tool-specific guidance

Use the repository's documented command interface. Add guidance for a build
system, language server, generated files, or other tool only when the project
uses it. Keep project-wide tool configuration committed and distinguish each
tool's exclusions from other tools' input filters.
