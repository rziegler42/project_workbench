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

Keep this table accurate. Use `not applicable` rather than leaving an
ambiguous blank.

| Purpose | Command |
|---|---|
| Setup | not applicable (standard library only; nothing to install) |
| Run locally | `python3 -m workbench verify [<package> \| --dir <path>] [--select <module> ...] [--no-harness-required]` |
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
- The text is built from a verified declaration and the verifier's hashes. The only thing
  read again is `executable_items(module_path)`, which lists files with the execute bit; the
  tree hash covers that bit.

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
