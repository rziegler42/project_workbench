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
| Owner-run: pin a helper's content (terminal only) | `python3 -m workbench pin <project-id> <name> <helper> --root <project-dir>` |
| Run a pinned helper | `python3 -m workbench launch <project-id> <name> --root <project-dir> -- <args>` |
| Release time: write the approvals shipped with first-party packages | `python3 -m workbench release-approvals` |
| Verify the sample package | `python3 -m workbench verify tests/fixtures/sample-package --select sample-harness sample-notes` |
| One focused test file | `python3 -m unittest discover -s tests -p 'test_approvals.py'` (a test module that imports `support` only loads under `discover -s tests`) |
| Full tests | `python3 -m unittest discover -s tests` |
| Format | not applicable (no code yet) |
| Lint or static analysis | not applicable (no code yet) |
| Type check | not applicable (no code yet) |
| Build | not applicable (no code yet) |
| All required checks | `python3 -m unittest discover -s tests`; document checks are run by the owner in session, as `docs/README.md` states |

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
owner can read its declaration before approving anything. No command calls it yet; the next
increment wires it into `approve`. `fetch.fetch(store, source, ref)` returns the new
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
  get mode 0644, or 0755 when git recorded the execute bit.
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

## Pins and the launcher

A helper such as the commit helper is a file of a module, so a pulled edit could replace it. The
owner pins it, and the launcher runs it only while its bytes still match the pin
(`workbench/pins.py`, `workbench/launch.py`). A pull that edits the helper changes its hash, so
it is not run until the owner pins it again.

- **Pin** (owner-run, from a terminal, like `approve`):
  `python3 -m workbench pin <project-id> <name> <helper> --root <project-dir>`. The project id
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
packages in `packages/` (none yet), and the approvals made for them in
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

`workbench/display.py` has the two cleaners. `clean` (used for the command's own messages)
keeps ordinary letters in any script and escapes control, invisible, combining, format,
separator and filler characters. `ascii_text` (used for the request) escapes everything
outside printable ASCII.

## The approval gate

`workbench/gate.py` answers whether a verified selection is fully approved on this machine.
No command calls it yet; the installer that writes a project will call it first, and it
only reads. It takes the result of `verify_packages` for a selection and reports each
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

Run `python3 -m unittest discover -s tests -v` for per-test output. Run all
commands from the repository root.

## Tool-specific guidance

Use the repository's documented command interface. Add guidance for a build
system, language server, generated files, or other tool only when the project
uses it. Keep project-wide tool configuration committed and distinguish each
tool's exclusions from other tools' input filters.
